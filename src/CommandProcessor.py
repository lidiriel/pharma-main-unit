import threading
import time
import logging
import json
import random
import serial
import lgpio as sbc
from Pins import PINS
from Config import QUEUE_CMD

REGISTER_LED = 0

class CommandProcessor(threading.Thread):
    def __init__(self, config, queue, gpiochip=None):
        super().__init__()
        self.config = config
        self.queue = queue
        self._running = True

        # set RS485 to transmission mode
        sbc.gpio_write(gpiochip, PINS['RS485_DE'], 1)
        self.com_serial = serial.Serial(self.config.com_serial_port, baudrate=self.config.com_serial_baudrate)
        logging.info("Command processor initialized")
        
    def terminate(self):
        self._running = False
        self.queue.shutdown()

    def crc8(self, data: bytes) -> int:
        crc = 0x00
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = ((crc << 1) ^ 0x07) & 0xFF
                else:
                    crc = (crc << 1) & 0xFF
        return crc
    
    def send_data(self, data1, data2):
        payload = bytes([data1, data2])
        crc = self.crc8(payload)
        frame = bytes([0xAA]) + payload + bytes([crc, 0x55])
        self.com_serial.write(frame)

    def run(self):
        data = None
        try:
            with open(self.config.patterns_file) as f:
                data = json.load(f)
                logging.info(f"JSON patterns file content : {data}")
        except FileNotFoundError:
            logging.error(f"Error: File not found {self.config.patterns_file}")
        except json.JSONDecodeError:
            logging.error(f"Error Invalid JSON content {self.config.patterns_file}")
        except Exception as e:
            logging.error(f"Unexpected error : {e}")
            
        # default sequence if not loaded at startup
        self.sequence = ["RAND"]
        self.sequence_idx = 0
        self.sequence_len = len(self.sequence)
        clk_id = time.CLOCK_REALTIME
        while self._running:
            try:
                (cmd, value) = self.queue.get(block=True)
                logging.debug(f" queue cmd {cmd} {value}")
                try:
                    if not self._running:
                        if cmd == QUEUE_CMD.PLAY:
                            self._running = True
                        continue
                    elif cmd == QUEUE_CMD.PAUSE:
                        self._running = False
                    elif cmd == QUEUE_CMD.BEAT:
                        element = self.sequence[self.sequence_idx]
                        code = 0
                        if element == "RAND":
                            code = random.randint(0,255)
                            # duplicate code for two cross
                            code = (code << 8) | code
                        else:
                            code = int(element,0) # first element
                        codeA = code & 0x00FF
                        codeB = (code >> 8) & 0x00FF
                        self.send_data(codeA, codeB)
                        my_time = time.clock_gettime(clk_id) - float(value)
                        logging.debug(f"sended code {code:#04x} sending latency {my_time}")
                        self.sequence_idx = (self.sequence_idx + 1) % self.sequence_len
                    elif cmd == QUEUE_CMD.CHG_SEQ:
                        try:
                            logging.info(f"Change sequence to {value}")
                            self.sequence = data['sequences'][value]
                            self.sequence_idx = 0
                            self.sequence_len = len(self.sequence)
                            logging.debug(f"Sequence is now : {self.sequence}")
                        except KeyError as e:
                            logging.error(f"ERROR invalid sequence name {value}")
                            self.sequence = ["RAND"]
                            self.sequence_idx = 0
                            self.sequence_len = len(self.sequence)
                except Exception as e:
                    logging.error(f"ERROR when processing pattern {e}")
            except ShutDown:
                logging.warning("Shutdown queue")
                break
