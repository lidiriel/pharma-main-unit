import threading

from waveshare_2_CH_RS485_HAT import RS485

# 
# DMX512 include maximum 512 channel bytes
# Each cross has : 8 channel (on/off) and 1 byte to adjust the luminosity
# that imply the usage of 2 bytes per cross
# <dimA><channelsA><dimB><channelsB>
MAX_CHANNEL = 512

class DmxProcessor(threading.Thread):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self._running = True
        RS485 = RS485.RS485()
        RS485.RS485_CH1_begin(115200)

    def terminate(self):
        self._running = False

    def run(self):
        while self._running:
            pass
