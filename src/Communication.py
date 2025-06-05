import threading
import Pins
import time
import logging
import json
import random
from Pins import PINS
import serial

REGISTER_LED = 0

class Communication(threading.Thread):
    def __init__(self, config, queue):
        super().__init__()
        self.config = config
        self.queue = queue
        self.logger = logging.getLogger('Communication')
        if self.config.com_debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.ERROR)

        self.com_serial = serial.Serial(self.config.com_serial_port, baudrate=self.config.com_serial_baudrate)

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
                self.logger.info(f"JSON patterns file content : {data}")
        except FileNotFoundError:
            self.logger.error(f"Error: File not found {self.config.patterns_file}")
        except json.JSONDecodeError:
            self.logger.error(f"Error Invalid JSON content {self.config.patterns_file}")
        except Exception as e:
            self.logger.error(f"Unexpected error : {e}")
            
        # default sequence if not loaded at startup
        self.sequence = ["RAND"]
        self.sequence_idx = 0
        self.sequence_len = len(self.sequence)
        clk_id = time.CLOCK_REALTIME
        while True:
            (cmd, value) = self.queue.get(block=True)
            try:
                if cmd == "BEAT":
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
                    my_time = time.clock_gettime(clk_id) - value
                    self.logger.debug(f"sended code {code:#04x} sending latency {my_time}")
                    self.sequence_idx = (self.sequence_idx + 1) % self.sequence_len
                elif cmd == "CHG_SEQ":
                    try:
                        self.logger.info(f"Change sequence to {value}")
                        self.sequence = data[value]
                        self.sequence_idx = 0
                        self.sequence_len = len(self.sequence)
                        self.logger.debug(f"Sequence is now : {self.sequence}")
                    except KeyError as e:
                        self.logger.error(f"ERROR invalid sequence name {value}")
                        self.sequence = ["RAND"]
                        self.sequence_idx = 0
                        self.sequence_len = len(self.sequence)
            except Exception as e:
                self.logger.error(f"ERROR when processing pattern {e}")
