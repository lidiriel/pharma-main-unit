import logging
import queue
import Config
import Pins
import os
from logging.handlers import RotatingFileHandler
import signal
import time
import CommandProcessor
import InterfaceProcessor
import BeatDetector



if __name__ == "__main__":
    config = Config.Config()

    logger = logging.getLogger()
    fh = RotatingFileHandler(config.logFile, maxBytes=102400, backupCount=2)
    logger.setLevel(config.log_level)
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
   
    bd = BeatDetector.BeatDetector(config, queue, gpiochip)
    bd.start()

    cp = CommandProcessor.CommandProcessor(config, queue, gpiochip)
    cp.start()
   
    def robust_signal_handler(signum, frame):
        # Ignore subsequent SIGINT signals to prevent interruption during cleanup
        signal.signal(signum, signal.SIG_IGN)
        perform_cleanup()

    def perform_cleanup():
        logging.warning("terminate all threads")
        cp.terminate()
        bd.terminate()
        ip.terminate()

    signal.signal(signal.SIGINT, robust_signal_handler)

    ip.join()
    bd.join()
    cp.join()
    
    
    
   
