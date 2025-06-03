import threading
import datetime
from pymodbus.client.sync import ModbusSerialClient
import Pins
import RPiRS485
import time
import logging
import json
from collections import deque
import random


ERROR_PIN = 29
REGISTER_LED = 0
RS485_DE_PIN = 17

class CommunicationProcessor(threading.Thread):
    def __init__(self, config, queue):
        super().__init__()
        self.config = config
        self.queue = queue
        if self.config.com_modbus_debug:
            logging.getLogger('pymodbus').setLevel(logging.DEBUG)
        else:
            logging.getLogger('pymodbus').setLevel(logging.ERROR)
        self.logger = logging.getLogger('CommunicationProcessor')

    def __getSerial(self):
        return RPiRS485.RPiRS485(port=self.config.com_serial_port, 
                                 baudrate=self.config.com_serial_baudrate, 
                                 stopbits=1,
                                 timeout=1,
                                 de_pin=RS485_DE_PIN)

    def run(self):
        client = ModbusSerialClient(method='rtu')
        client.socket = self.__getSerial()
        client.connect()
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
                    #Pins.pinsWrite('ERROR', False)
                    sequence.rotate(-1) # rotate left
                    element = sequence[0]
                    code = 0
                    if element == "RAND":
                        code = random.randint(0,255)
                        # duplicate code for two cross
                        code = (code << 8) | code
                    else:
                        code = int(element,0) # first element
                    self.logger.debug(f"send code {code}")
                    response = client.write_register(REGISTER_LED, code, unit=0)
                elif cmd == "CHG_SEQ":
                    try:
                        self.logger.info(f"Change sequence to {value}")
                        sequence = deque(data[value])
                        self.logger.debug(f"Sequence is now : {sequence}")
                    except KeyError as e:
                        self.logger.error(f"ERROR invalid sequence name {value}")
                        sequence = deque(["RAND"])
            except Exception as e:
                #Pins.pinsWrite('ERROR', True)
                Pins.pinsWrite('ERROR', True)
                self.logger.error("ERROR when processing patern")
                if client.socket is None:
                    self.logger.error("renew socket")
                    client.socket = self.__getSerial()
            finally:
                time.sleep(1)
