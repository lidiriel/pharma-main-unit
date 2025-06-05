import threading
import Pins
import time
import logging
import json
from collections import deque
import random
from Pins import PINS
import minimalmodbus

REGISTER_LED = 0

class CommunicationProcessorMinimal(threading.Thread):
    def __init__(self, config, queue):
        super().__init__()
        self.config = config
        self.queue = queue
        if self.config.com_modbus_debug:
            self.logger = logging.getLogger('CommunicationProcessorMinimal').setLevel(logging.DEBUG)
        self.logger = logging.getLogger('CommunicationProcessorMinimal').setLevel(logging.ERROR)

        self.instrument = minimalmodbus.Instrument(port='/dev/ttyAMA0', slaveaddress=0)
        self.instrument.serial.baudrate = config.com_serial_baudrate
        self.instrument.serial.bytesize = 8
        self.instrument.serial.parity = minimalmodbus.serial.PARITY_NONE
        self.instrument.serial.stopbits = 1
        self.instrument.serial.timeout = 0
        self.instrument.mode = minimalmodbus.MODE_RTU
        self.instrument.clear_buffers_before_each_transaction = True

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
        sequence = deque(["RAND"])

        while True:
            (cmd, value) = self.queue.get(block=True)
            try:
                if cmd == "BEAT":
                    sequence.rotate(-1) # rotate left
                    element = sequence[0]
                    code = 0
                    if element == "RAND":
                        code = random.randint(0,255)
                        # duplicate code for two cross
                        code = (code << 8) | code
                    else:
                        code = int(element,0) # first element
                    self.instrument.write_register(REGISTER_LED, code)
                    self.logger.debug(f"sended code {code:4x}")
                elif cmd == "CHG_SEQ":
                    try:
                        self.logger.info(f"Change sequence to {value}")
                        sequence = deque(data[value])
                        self.logger.debug(f"Sequence is now : {sequence}")
                    except KeyError as e:
                        self.logger.error(f"ERROR invalid sequence name {value}")
                        sequence = deque(["RAND"])
            except Exception as e:
                self.logger.error(f"ERROR when processing patern {e}")
