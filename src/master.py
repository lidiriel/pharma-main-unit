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


if __name__ == "__main__":
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
    
   
