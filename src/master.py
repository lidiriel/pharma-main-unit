import logging
import queue
import datetime

import Config
import CommunicationProcessor
import BeatDetector


import Pins


if __name__ == "__main__":
    config = Config.Config()

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(config.logFile)
    fh.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    Pins.pinsInit()
    
    """ queue use tuple (CMD, VALUE)
        CMD are : 
            BEAT new beat with timestamp
            CHG_SEQ change sequence with sequence name        
    """
    queue = queue.Queue()

    queue.put(("CHG_SEQ","sequence1"))
        
    #ip = InterfaceProcessor.InterfaceProcessor(config)
    #ip.start()
    #logger.info('InterfaceProcessor started')
   
    bd = BeatDetector.BeatDetector(config, queue)
    bd.start()
    logger.info('beatDetector started')

    cp = CommunicationProcessor.CommunicationProcessor(config, queue)
    cp.start()
    logger.info('CommunicationProcessor started')
    
   
