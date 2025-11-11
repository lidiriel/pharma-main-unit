""" In production do not use debug mode
"""
import re
from enum import StrEnum

SEQUENCE_PATTERN = re.compile(r'sequence\d')

class Config(object):
    def __init__(self):
        self.logFile = '/tmp/pharma.log'
        self.weblogFile = '/tmp/pharma-web.log'
        self.patterns_file = '/home/compost/pharma-main-unit/config/cross.json'
        self.beat_device_name = 'adc_hw'
        self.beat_min_freq = 50
        self.beat_max_freq = 4000
        self.beat_min_energy = 1e17
        self.beat_c_factor = 5
        self.beat_interval = 0.33
        self.beat_debug = False
        self.beat_full_debug = False
        self.com_debug = False
        self.com_serial_port = '/dev/ttyAMA0'
        self.com_serial_baudrate = 57600
        self.sock_file = '/tmp/pharma-ipc.socket'
        self.service_name = 'pharma.service'
        

class IPC_COMMAND(StrEnum):
    GET_PAYING = 'get_playing'
    SET_PLAYING = 'set_playing'
    IS_PLAYING = 'is_playing'
    DO_PAUSE = 'do_pause'
    DO_PLAY = 'do_play'
    
    
        

