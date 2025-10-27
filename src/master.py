import logging
import queue
import Config
import CommandProcessor
import InterfaceProcessor
import BeatDetector
import Pins
from logging.handlers import RotatingFileHandler

if __name__ == "__main__":
    config = Config.Config()

    logger = logging.getLogger()
    #logger.setLevel(logging.DEBUG)
    fh = RotatingFileHandler(config.logFile, maxBytes=102400, backupCount=2)
    fh.setLevel(logging.DEBUG)
    # ch = logging.StreamHandler()
    #ch.setLevel(logging.ERROR)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    #ch.setFormatter(formatter)
    logger.addHandler(fh)
    #logger.addHandler(ch)
    
    # init pin to output
    Pins.pinsInit()
    
    """ queue use tuple (CMD, VALUE)
        CMD are : 
            BEAT new beat with timestamp
            CHG_SEQ change sequence with sequence name        
    """
    queue = queue.Queue()
        
    ip = InterfaceProcessor.InterfaceProcessor(config, queue)
    ip.start()
    logger.info('InterfaceProcessor started')
   
    bd = BeatDetector.BeatDetector(config, queue)
    bd.start()
    logger.info('BeatDetector started')

    cp = CommandProcessor.CommandProcessor(config, queue)
    cp.start()
    logger.info('CommandProcessor started')
    
   
