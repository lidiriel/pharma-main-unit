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
    
    queue = queue.Queue()
        
    #ip = InterfaceProcessor.InterfaceProcessor(config)
    #ip.start()
   
    bd = BeatDetector.BeatDetector(config, queue)
    bd.start()

    cp = CommunicationProcessor.CommunicationProcessor(config, queue)
    cp.start()
    
    #wc = WebControl 
   
