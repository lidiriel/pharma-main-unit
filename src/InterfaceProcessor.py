import threading
import logging
import socket
import fcntl
import struct
import lgpio as sbc
import json
import os
import pickle
import I2C_LCD_driver
from Config import SEQUENCE_PATTERN, IPC_COMMAND, QUEUE_CMD
from Pins import PINS


class InterfaceProcessor(threading.Thread):
    def __init__(self, config, queue, gpiochip=None):
        super().__init__()
        self._running = True
        self.status = QUEUE_CMD.PLAY
        self.config = config
        self.queue = queue
        self.gpiochip = gpiochip
        # start playing
        self.queue.put((QUEUE_CMD.PLAY, None))
        self.lcd_status = False
        try:
            self.lcd = I2C_LCD_driver.lcd()
            self.lcd_status = True
        except Exception as e:
            logging.error(f"LCD error {e}")
        
        
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
        
        self.set_playing_sequence(data.get('default', "sequence1"))
        
        # Setup socket
        try:
            if os.path.exists(self.config.sock_file):
                os.remove(self.config.sock_file)
 
            self.ipc_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)   
            self.ipc_socket.bind(self.config.sock_file)
            self.ipc_socket.settimeout(3)
            self.ipc_socket.listen(0)
        except Exception as e:
            logging.error(f"Socket for IPC error {e}")

        self.myip = self.get_ip("eth0")
        self.update_lcd()
        logging.info("Interface processor initialized")
    
    def terminate(self):
        self._running = False
    
    def get_playing_sequence(self):
        return self.playing_seq_name
        
    def set_playing_sequence(self, value):
        """ value is only <sequenceX> where X [0..9]
        """
        if SEQUENCE_PATTERN.match(value):
            self.playing_seq_name = value
            self.queue.put((QUEUE_CMD.CHG_SEQ, value))
        else:
            logging.error(f"Invalid sequence {value}")
    
    def get_ip(self, ifname):
        """ if not connected to network
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ip = socket.inet_ntoa(
                fcntl.ioctl(
                    s.fileno(),
                    0x8915,  # SIOCGIFADDR
                    struct.pack('256s', ifname[:15].encode('utf-8'))
                )[20:24]
            )
            logging.info(f"my ip is {ip}")
            return ip
        except Exception as e:
            logging.error(f"ERROR to get ip : {e}")
            return None
    
    def update_lcd(self, shutdown=False):
        if self.lcd_status:
            if shutdown:
                self.lcd.lcd_clear()
                self.lcd.lcd_display_string(f"shutdown", 1)
            else:
                self.lcd.lcd_clear()
                self.lcd.lcd_display_string(f"IP:{self.myip}", 1)
                self.lcd.lcd_display_string(f"{self.status} {self.playing_seq_name}", 2)
            
    
    def run(self):
        try:
            # self.pwm.start(50)  # Start duty cycle 50% for heartbeat
            sbc.tx_pwm(self.gpiochip, PINS['HEART'], 1, 50)
        except Exception as e:
            logging.error(f"ERROR to start pwm heart led : {e}")

        while self._running:
            try:
                # Accept 'request'
                logging.info("wait socket connexion")
                conn, addr = self.ipc_socket.accept()
                # Process 'request'
                with conn:
                    logging.info(f'Connection by client {addr}')
                    while self._running:
                        data = conn.recv(1024)
                        if not data:
                            break
                        ipc_string = pickle.loads(data)
                        ipc_list = ipc_string.split(':')
                        if ipc_list[0] == IPC_COMMAND.GET_PLAYING:
                            data = self.get_playing_sequence()
                        elif ipc_list[0] == IPC_COMMAND.SET_PLAYING:
                            value = None
                            try:
                                value = ipc_list[1]
                                self.set_playing_sequence(value)
                                data = True
                            except IndexError:
                                logging.error("No value with set_playing command")
                            data = False
                        elif ipc_list[0] == IPC_COMMAND.IS_PLAYING:
                            data = self.status == QUEUE_CMD.PLAY 
                        elif ipc_list[0] == IPC_COMMAND.DO_PAUSE:
                            self.status = QUEUE_CMD.PAUSE
                            self.queue.put((QUEUE_CMD.PAUSE,None))
                        elif ipc_list[0] == IPC_COMMAND.DO_PLAY:
                            self.status = QUEUE_CMD.PLAY
                            self.queue.put((QUEUE_CMD.PLAY,None))
                        serialized = pickle.dumps(data)
                        conn.sendall(serialized)
                        self.update_lcd()
            except TimeoutError:
                pass
        self.update_lcd(shutdown=True)
        
            
    
