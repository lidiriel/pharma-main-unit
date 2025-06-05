
class Config(object):
    def __init__(self):
        self.logFile = '/tmp/pharma.log'
        self.beatslogFile = '/tmp/pharma_beats.log'
        self.patterns_file = '/home/compost/pharma-main-unit/config/cross.json'
        self.beat_device_name = 'adc_sv'
        self.beat_min_freq = 50
        self.beat_max_freq = 4000
        self.beat_min_energy = 1e15
        self.beat_c_factor = 5
        self.beat_interval = 0.66
        self.beat_debug = False
        self.com_modbus_debug = True
        self.com_serial_port = '/dev/ttyAMA0'
        self.com_serial_baudrate = 57600
