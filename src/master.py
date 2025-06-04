import logging
import queue
import datetime
import Config
import CommunicationProcessor
import InterfaceProcessor
import BeatDetector
import Pins
from logging.handlers import RotatingFileHandler


if __name__ == "__main__":
    config = Config.Config()

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    fh = RotatingFileHandler(config.logFile, maxBytes=102400, backupCount=2)
    fh.setLevel(logging.INFO)
    #ch = logging.StreamHandler()
    #ch.setLevel(logging.ERROR)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    #ch.setFormatter(formatter)
    logger.addHandler(fh)
    #logger.addHandler(ch)
    
    beatlogger = logging.getLogger("beats")
    beatlogger.setLevel(logging.INFO)
    bfh = RotatingFileHandler(config.beatlogFile, maxBytes=102400, backupCount=1)
    beatlogger.addhandler(bfh)
    
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
    logger.info('beatDetector started')

    #cp = CommunicationProcessor.CommunicationProcessor(config, queue)
    #cp.start()
    #logger.info('CommunicationProcessor started')
    
   
