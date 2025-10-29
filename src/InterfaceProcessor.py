import threading
import logging
import socket
import fcntl
import struct
from Pins import PINS
import RPi.GPIO as GPIO
import time
import I2C_LCD_driver
import json


class InterfaceProcessor(threading.Thread):
    def __init__(self, config, queue):
        super().__init__()
        self.config = config
        self.queue = queue
        self.logger = logging.getLogger('InterfaceProcessor')
        # Create PWM object on GPIO12 with frequency 1 Hz
        # Pin init is doing into master.py
        self.pwm = GPIO.PWM(PINS['HEART'], 0.5)
        self.lcd_status = False
        try:
            self.lcd = I2C_LCD_driver.lcd()
            self.lcd_status = True
        except Exception as e:
            self.logger.error(f"LCD error {e}")
        
        
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
        
        self.seq_name = data.get('default', "sequence1")
        
        self.queue.put(("CHG_SEQ",self.seq_name))
    
    def get_ip_address(self):
        """ if connected to network : dyanmic ip
        """
        try:
            # Connexion fictive à une IP publique pour obtenir l'IP locale utilisée
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            self.logger.info(f"my ip is {ip}")
            return ip
        except Exception as e:
            self.logger.error(f"ERROR to get ip : {e}")
            
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
            self.logger.info(f"my ip is {ip}")
            return ip
        except Exception as e:
            self.logger.error(f"ERROR to get ip : {e}")
            return None
    
    
    def run(self):
        self.myip = self.get_ip("eth0")
        try:
            self.pwm.start(50)  # Start duty cycle 50% for heartbeat
        except Exception as e:
            self.logger.error(f"ERROR to start pwm heart led : {e}")
             
        while True:
            if self.lcd_status:
                self.lcd.lcd_clear()
                self.lcd.lcd_display_string(u"Compost Collaps", 1)
                time.sleep(3)
                self.lcd.lcd_clear()
                self.lcd.lcd_display_string(f"IP {self.myip}", 1)
                self.lcd.lcd_display_string(f"PLAY {self.seq_name}", 2)
            time.sleep(3)
            
            
    
