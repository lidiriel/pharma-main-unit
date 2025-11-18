import logging
import queue
import Config
import CommandProcessor
import InterfaceProcessor
import BeatDetector
import webctrl
import Pins
import cherrypy
import os
from logging.handlers import RotatingFileHandler
import signal
import time

# set clean signal killer
class GracefulKiller:
    kill_now = False
    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

def exit_gracefully(self, signum, frame):
    self.kill_now = True

if __name__ == "__main__":
    killer = GracefulKiller()
    config = Config.Config()

    logger = logging.getLogger()
    fh = RotatingFileHandler(config.logFile, maxBytes=102400, backupCount=2)
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    # init pin to output
    gpiochip = Pins.pinsInit()
    
    """ queue use tuple (CMD, VALUE)
        CMD are : 
            BEAT new beat with timestamp
            CHG_SEQ change sequence with sequence name        
    """
    queue = queue.Queue()
        
    ip = InterfaceProcessor.InterfaceProcessor(config, queue, gpiochip)
    ip.start()
    logger.info('InterfaceProcessor started')
   
    bd = BeatDetector.BeatDetector(config, queue, gpiochip)
    bd.start()
    logger.info('BeatDetector started')

    cp = CommandProcessor.CommandProcessor(config, queue, gpiochip)
    cp.start()
    logger.info('CommandProcessor started')
    
    while not killer.kill_now:
        time.sleep(1)
    
    ip.terminate()
    bd.terminate()
    cp.terminate()
    ip.join(1)
    bd.join(1)
    cp.join(1)
    logger.info("bye bye")
    
    
    
   
