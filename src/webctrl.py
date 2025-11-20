#!/bin/python
import os, os.path
import cherrypy
import json
import logging
import socket
import sys
import pickle
import subprocess
import select
from logging.handlers import RotatingFileHandler
from Config import Config
from Config import IPC_COMMAND
from jaraco.functools import except_

class Webctrl(object):
    command_list = ['RAND']
    
    def __init__(self):
        self.config = Config()
        
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        fileHandler = RotatingFileHandler(self.config.weblogFile, maxBytes=102400, backupCount=2)
        logger.addHandler(fileHandler)
        consoleHandler = logging.StreamHandler()
        logger.addHandler(consoleHandler)
        logging.info("Webservice Pharma started")
    
    def load_cross_config(self, fname="../config/cross.json"):
        cross_config = {}
        try:
            config_file = open(fname, 'rb')
        except OSError:
            logging.error(f"Could not open/read file:{fname}")
        with config_file:
            cross_config = json.load(config_file)
        return cross_config
    
    
    @cherrypy.expose
    def index(self):
        return open('index.html')


    def update_cherrypy_session(self):
        if 'cross_config' not in cherrypy.session:
            cross_config = self.load_cross_config(self.config.patterns_file)
            cherrypy.session['cross_config'] = cross_config
        else:
            cross_config = cherrypy.session['cross_config']
        logging.info(f"{cross_config}")
        return cross_config

    @cherrypy.expose
    def save(self, sequence_name="", sequence_value=""):
        logging.info(f" prog-list {sequence_name}  hex_list {sequence_value}")
        cross_config = self.update_cherrypy_session()
        new_sequence = sequence_value.split(',')
        def convert(item):
            if item not in self.command_list:
                try:
                    item = hex(int(item, 16))
                except ValueError as error:
                    logging.error(f"Invalid value for hex conversion {item}")
                    item = '0x0000'
            return item
        new_sequence = [convert(item) for item in new_sequence]
        cross_config['sequences'][sequence_name] = new_sequence
        cherrypy.session['cross_config'] = cross_config
        logging.info(f"new sequence {new_sequence}")
        try:
            json_cross_config = json.dumps(cross_config)
            f = open(self.config.patterns_file, "w")
            f.write(json_cross_config)
            f.close()
        except OSError:
            logging.error(f"Could not open/read file:{self.config.patterns_file}")
    
    """ ipc communication function
        force retry on error
        close socket after each call
    """
    def ipc_communication(self, value, mytype):
        # Init socket object
        if not os.path.exists(self.config.sock_file):
            logging.error(f"File {self.config.sock_file} doesn't exists -> exit")
            sys.exit(-1)
        
        retry = 1
        while retry >= 0:
            s = None
            try:
                received_object = None
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.settimeout(2)
                s.connect(self.config.sock_file)
                serialized = pickle.dumps(value)
                s.sendall(serialized)
                data = s.recv(1024)
                received_object = pickle.loads(data)
                if type(received_object) != mytype:
                    logging.error(f"Invalid type for received object {type(received_object)}")
                s.close()
                return received_object
            except socket.error as e:
                logging.error(f"IPC communication ERROR {e}")
                s.close()
                retry = retry - 1
        logging.error("IPC failed -> exit")
        sys.exit(-1)
        
    
    @cherrypy.tools.json_out()
    @cherrypy.expose
    def get_playing(self):
        value = self.ipc_communication(IPC_COMMAND.GET_PLAYING, str)
        logging.debug(f"get_playing receive {value}")
        return {"name" : value}
    
    @cherrypy.expose
    def set_playing(self, sequence_name=""):
        value = self.ipc_communication(f'{IPC_COMMAND.SET_PLAYING}:{sequence_name}', bool)
        if not value:
            logging.error("Error on set playing")
    
    @cherrypy.expose     
    def set_default(self, sequence_name=""):
        logging.info(f"set sequence {sequence_name} to default")
        cross_config = self.update_cherrypy_session()
        cross_config["default"] = sequence_name
        try:
            json_sequences = json.dumps(cross_config)
            f = open(self.config.patterns_file, "w")
            f.write(json_sequences)
            f.close()
        except OSError:
            logging.error(f"Could not open/read file:{self.config.patterns_file}")
    
    @cherrypy.expose
    def communication_change(self):
        logging.info(f"play/pause command transmission")
        if self.ipc_communication(IPC_COMMAND.IS_PLAYING, bool):
            logging.info(f"command processor is running -> pause")
            self.ipc_communication(IPC_COMMAND.DO_PAUSE, type(None))
        else:
            logging.info(f"command processor is not running -> playing")
            self.ipc_communication(IPC_COMMAND.DO_PLAY, type(None))
            
    @cherrypy.expose
    def service_restart(self):
        logging.info(f"restart pharma main thread")
        try:
            subprocess.run(["sudo", "systemctl", "restart", self.config.service_name])
        except Exception as e:
            logging.error(f"restart exception {e}")
        logging.info("main service restarted")
    
    @cherrypy.expose 
    def reload_config(self):
        logging.info(f"Reload config")
        self.ipc_communication(IPC_COMMAND.RELOAD_CONFIG, type(None))
            
    @cherrypy.tools.json_out()
    @cherrypy.expose
    def communication_status(self):
        value = self.ipc_communication(IPC_COMMAND.IS_PLAYING, bool)
        logging.info(f"Is communication playing mode ? {value}")
        return {"status" : value}


    @cherrypy.tools.json_out()
    @cherrypy.expose
    def get_default_sequence_name(self):
        cross_config = self.update_cherrypy_session()
        value = cross_config['default']
        logging.info(f"get default sequence name {value}")
        return {"name" : value}

    
    @cherrypy.tools.json_out()
    @cherrypy.expose
    def load(self, sequence_name=""):
        out = ["0x0000"]
        cross_config = self.update_cherrypy_session()
        if sequence_name == "":
            out = cross_config['sequences']
        elif len(sequence_name) != 0:
            out = cross_config['sequences'].get(sequence_name, ["0x0000"])
            
        logging.info(f"json out {out}")
        return out
    


if __name__ == '__main__':
    conf = {
        '/': {
            'tools.sessions.on': True,
            'tools.staticdir.root': os.path.abspath(os.getcwd())
        },

        '/static': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': './public'
        }
    }
    cherrypy.server.socket_host = '0.0.0.0'
    cherrypy.quickstart(Webctrl(), '/', conf)
