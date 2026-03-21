import threading
import logging
import time
import sys
import os

import RPi.GPIO as GPIO  # type: ignore

# Add the Waveshare HAT library to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib', 'waveshare_2_CH_RS485_HAT'))

import RS485    # type: ignore
import SC16IS752  # type: ignore

# ---------------------------------------------------------------------------
# DMX512 protocol constants
# ---------------------------------------------------------------------------
DMX_START_CODE = 0x00   # standard dimmer start code
MAX_CHANNEL    = 512    # maximum DMX512 channel count

# The SC16IS752 with a 14.7456 MHz crystal cannot divide exactly to 250 000 baud.
#   divisor = 14 745 600 / 16 / 250 000 = 3.6864  (non-integer → not achievable)
# Closest supported rate is 230 400 baud (≈ 8 % error).
# TODO: replace crystal with 16.000 MHz (div=4 → exact 250 000 baud) or
#       20.000 MHz (div=5 → exact 250 000 baud) for reliable DMX reception.
DMX_BAUD = 230400

# SC16IS752 LSR register bit masks (datasheet §8.7)
_LSR_DATA_READY      = 0x01   # data waiting in RX FIFO
_LSR_BREAK_INTERRUPT = 0x10   # break condition detected

# Frame-reception state machine
_IDLE  = 0   # waiting for break
_BREAK = 1   # break received — next byte is the start code
_DATA  = 2   # accumulating channel bytes


class DmxProcessor(threading.Thread):
    """
    Receives DMX512 frames via the Waveshare 2-CH RS485 HAT (SC16IS752
    SPI UART bridge) on CH1 and processes channel data.

    DMX512 frame structure
    ----------------------
    BREAK       : ≥ 88 µs low — detected via SC16IS752 LSR bit 4 (BI)
    MAB         : ≥ 8 µs high (Mark After Break — consumed by hardware)
    Start code  : 1 byte (0x00 = standard dimmer data)
    Channel data: 1 - 512 bytes  (frame may be shorter than 512)

    Cross layout (2 bytes per cross, starting at config.dmx_channels_start)
    -------------------------------------------------------------------------
    byte 0 : dimming  - brightness 0-255
    byte 1 : segments - 8 on/off bits for the pharmacy-cross channels
    Full layout: <dimA><segA> <dimB><segB> …
    """

    def __init__(self, config):
        super().__init__()
        self.config = config
        self._running = True
        self._rs485 = None
        self._ch1 = None        # SC16IS752 CH1 instance (shortcut)
        self._buf = []
        self._state = _IDLE
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Thread lifecycle
    # ------------------------------------------------------------------

    def terminate(self):
        self._running = False

    def run(self):
        self._init_rs485()
        try:
            while self._running:
                frame = self._receive_frame()
                if frame is not None:
                    self.process_frame(frame)
                else:
                    time.sleep(0.001)
        finally:
            self._rs485 = None
            self._ch1 = None

    # ------------------------------------------------------------------
    # RS485 / SC16IS752 initialisation
    # ------------------------------------------------------------------

    def _init_rs485(self):
        """
        Initialise the Waveshare RS485 HAT CH1 for DMX reception.

        RS485_CH1_begin() leaves TXDEN_1 HIGH (TX mode); we pull it LOW
        immediately after to switch to receive mode.
        """
        try:
            self._rs485 = RS485.RS485()
            self._rs485.RS485_CH1_begin(DMX_BAUD)
            # Switch CH1 to receive mode (driver disabled, receiver active)
            GPIO.output(self._rs485.config.TXDEN_1, GPIO.LOW)
            self._ch1 = self._rs485.SC16IS752_CH1
            self.logger.info(
                f"DMX RS485 CH1 ready at {DMX_BAUD} baud "
                f"(DMX512 standard is 250000 — see crystal TODO)"
            )
        except Exception as e:
            self.logger.error(f"Failed to init RS485 for DMX: {e}")
            self._rs485 = None
            self._ch1 = None

    # ------------------------------------------------------------------
    # Low-level SC16IS752 register helpers
    # ------------------------------------------------------------------

    def _read_lsr(self):
        """Read Line Status Register for CH1."""
        result = self._ch1.WR_REG(
            SC16IS752.CMD_READ | SC16IS752.REG(SC16IS752.LSR) | SC16IS752.CHANNEL_1,
            0xff
        )
        return result[0] if result else 0x00

    def _read_rhr(self):
        """Read one byte from the Receiver Holding Register for CH1."""
        result = self._ch1.WR_REG(
            SC16IS752.CMD_READ | SC16IS752.REG(SC16IS752.RHR) | SC16IS752.CHANNEL_1,
            0xff
        )
        return result[0] if result else None

    # ------------------------------------------------------------------
    # Frame reception state machine
    # ------------------------------------------------------------------

    def _receive_frame(self):
        """
        Poll the SC16IS752 LSR and read one byte per call to advance the
        DMX frame state machine.

        Returns a list of channel bytes when a complete frame is assembled,
        otherwise None.

        Break detection
        ---------------
        The SC16IS752 sets LSR bit 4 (Break Interrupt) when a break condition
        is detected; the corresponding RHR byte is 0x00 and should be discarded.
        A framing error without BI (LSR bit 3) on the first byte of a frame may
        also indicate a late-detected break — treat identically.
        """
        if not self._ch1:
            return None

        lsr = self._read_lsr()

        if not (lsr & (_LSR_DATA_READY | _LSR_BREAK_INTERRUPT)):
            return None  # nothing to read

        byte = self._read_rhr()
        if byte is None:
            return None

        # --- Break condition ---
        if lsr & _LSR_BREAK_INTERRUPT:
            self._buf = []
            self._state = _BREAK
            return None

        # --- State machine ---
        if self._state == _IDLE:
            # No break seen yet — discard
            return None

        if self._state == _BREAK:
            # This byte is the start code
            if byte == DMX_START_CODE:
                self._buf = []
                self._state = _DATA
            else:
                self.logger.debug(f"Unsupported DMX start code {byte:#04x} — frame skipped")
                self._state = _IDLE
            return None

        if self._state == _DATA:
            self._buf.append(byte)
            if len(self._buf) >= MAX_CHANNEL:
                frame = list(self._buf)
                self._buf = []
                self._state = _IDLE
                return frame

        return None

    # ------------------------------------------------------------------
    # Frame processing
    # ------------------------------------------------------------------

    def process_frame(self, channels):
        """
        Process one received DMX512 frame.

        Parameters
        ----------
        channels : list[int]
            Raw channel values, 1 - 512 bytes.  Frames shorter than 512
            bytes are valid; every access is bounds-checked.

        The first relevant channel is at index (config.dmx_channels_start - 1).
        Each cross consumes 2 consecutive bytes (dimming, segments).
        """
        if not channels:
            return

        offset = self.config.dmx_channels_start - 1  # convert 1-based → 0-based

        if offset >= len(channels):
            self.logger.warning(
                f"DMX frame too short ({len(channels)} ch) "
                f"for channel start {self.config.dmx_channels_start}"
            )
            return

        self.logger.debug(f"DMX frame: {len(channels)} channels, processing from offset {offset}")

        idx = offset
        cross_index = 0
        while idx + 1 < len(channels):
            dimming  = channels[idx]
            segments = channels[idx + 1]
            self._apply_cross(cross_index, dimming, segments)
            idx += 2
            cross_index += 1

    def _apply_cross(self, cross_index, dimming, segments):
        """
        Apply dimming and segment mask to one physical cross.

        Parameters
        ----------
        cross_index : int   zero-based cross number
        dimming     : int   brightness 0-255
        segments    : int   bitmask for the 8 on/off channels of the cross

        TODO: forward to the cross controller output (e.g. via the shared
              queue using QUEUE_CMD, or a direct RS485 CH2 write).
        """
        self.logger.debug(
            f"Cross {cross_index}: dim={dimming:#04x}  seg={segments:08b}"
        )
        # TODO: implement cross control
