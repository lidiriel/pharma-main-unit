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
        self.ipc_init()
        logging.info("Webservice Pharma started")

    def ipc_init(self):
        # Init socket object
        if not os.path.exists(self.config.sock_file):
            logging.error(f"File {self.config.sock_file} doesn't exists")
            sys.exit(-1)
 
        self.ipc = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.ipc.settimeout(2)
        self.ipc.connect(self.config.sock_file)
    
    
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
    
    def is_socket_alive(self):
        readable, _, exceptional = select.select([self.ipc], [], [self.ipc], 1)
        if self.ipc in exceptional:
            logging.warning("Connection has been reset by the peer.")
            return False
        return bool(readable)
    

    def ipc_communication(self, value, mytype):
        if not self.is_socket_alive():
            self.ipc.close()
            self.ipc_init()
        received_object = None
        try:
            serialized = pickle.dumps(value)
            self.ipc.sendall(serialized)
            data = self.ipc.recv(1024)
            received_object = pickle.loads(data)
        except Exception as e:
            logging.error(f"Error on IPC communication : {e}")
        if type(received_object) != mytype:
            logging.error(f"Invalid type for received object {type(received_object)}") 
        return received_object
    
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
        found = False
        try:
            subprocess.run(["sudo", "systemctl", "restart", self.config.service_name])
        except Exception as e:
            logging.error(f"restart exception {e}")
        logging.info("main service restarted")
        return
        #for proc in psutil.process_iter():
        #    try:
        #        pname = proc.name()
        #        logging.debug(f"proc name {pname}")
        #        if pname == self.config.service_name:
        #            found = True
        #            try:
        #                proc.terminate()
        #                print(f"{self.config.service_name} service has been stopped")
        #                subprocess.run(["systemctl", "start", self.config.service_name])
        #                print(f"{self.config.service_name} service has been started")
        #            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
        #                logging.error(f"service restart error {e}")
        #    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        #        pass
        #if not found:
        #    logging.error(f"service not found : {self.config.service_name}")
            
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
