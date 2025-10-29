#!/bin/python
import os, os.path
import random
import string
import cherrypy
import json
import subprocess
import logging
import Config
from logging.handlers import RotatingFileHandler

""" for restarting service after config update
    wee need the name PHARMA_SERVICE
"""
PHARMA_SERVICE = "pharma"

class Programmation(object):
    fname="../config/cross.json"
    command_list = ['RAND']
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        fh = RotatingFileHandler(config.weblogFile, maxBytes=102400, backupCount=2)
        fh.setLevel(logging.DEBUG)
        self.logger.addHandler(fh)
        self.logger.info("Webservice Pharma started")
    
    def load_cross_config(self, fname="../config/cross.json"):
        cross_config = {}
        try:
            config_file = open(fname, 'rb')
        except OSError:
            cherrypy.log(f"Could not open/read file:{fname}")
        with config_file:
            cross_config = json.load(config_file)
        return cross_config
    
    def control_service(self, service_name, cmd="restart"):
        try:
            # Redémarrer le service avec systemctl
            completed = subprocess.run(["/bin/systemctl", cmd, service_name], capture_output=True)
            self.logger.debug(f"Service {service_name} CMD {cmd} completed={completed}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error on {cmd} for service {service_name} : {e}")
            
    def service_is_active(self, service_name):
        """Return True if systemd service is running"""
        try:
            completed = subprocess.run(["/bin/systemctl", "status", service_name], capture_output=True)
        except subprocess.CalledProcessError as err:
            self.logger.error( f"Error on service is active {err}" )
        else:
            self.logger.debug(f"COMPLETED {completed}")
            for line in completed.stdout.decode('utf-8').splitlines():
                if 'Active:' in line:
                    self.logger.debug("Active line {line}")
                    if '(running)' in line:
                        self.logger.debug(f"service {service_name} is running")
                        return True
            self.logger.info(f"service {service_name} stopped")        
            return False
    
    @cherrypy.expose
    def index(self):
        return open('index.html')


    def update_cherrypy_session(self):
        if 'cross_config' not in cherrypy.session:
            cross_config = self.load_cross_config(self.fname)
            cherrypy.session['cross_config'] = cross_config
        else:
            cross_config = cherrypy.session['cross_config']
        cherrypy.log(f"{cross_config}")
        return cross_config

    @cherrypy.expose
    def save(self, sequence_name="", sequence_value=""):
        cherrypy.log(f" prog-list {sequence_name}  hex_list {sequence_value}")
        cross_config = self.update_cherrypy_session()
        new_sequence = sequence_value.split(',')
        def convert(item):
            if item not in self.command_list:
                try:
                    item = hex(int(item, 16))
                except ValueError as error:
                    cherrypy.log(f"Invalid value for hex conversion {item}")
                    item = '0x0000'
            return item
        new_sequence = [convert(item) for item in new_sequence]
        cross_config['sequences'][sequence_name] = new_sequence
        cherrypy.session['cross_config'] = cross_config
        cherrypy.log(f"new sequence {new_sequence}")
        try:
            json_cross_config = json.dumps(cross_config)
            f = open(self.fname, "w")
            f.write(json_cross_config)
            f.close()
        except OSError:
            cherrypy.log(f"Could not open/read file:{self.fname}")
        self.control_service(PHARMA_SERVICE)
    
    @cherrypy.expose     
    def set_default(self, sequence_name=""):
        cherrypy.log(f"set sequence {sequence_name} to default")
        cross_config = self.update_cherrypy_session()
        cross_config["default"] = sequence_name
        try:
            json_sequences = json.dumps(cross_config)
            f = open(self.fname, "w")
            f.write(json_sequences)
            f.close()
        except OSError:
            cherrypy.log(f"Could not open/read file:{self.fname}")
    
    @cherrypy.expose
    def service_start_stop(self):
        cherrypy.log(f"start/stop pharma service")
        if self.service_is_active(PHARMA_SERVICE):
            cherrypy.log(f"pharma service is started -> stop")
            self.control_service(PHARMA_SERVICE, "stop")
        else:
            cherrypy.log(f"pharma service is stoped -> start")
            self.control_service(PHARMA_SERVICE, "start")
            
    @cherrypy.expose
    def service_restart(self):
        cherrypy.log(f"restart pharma service")
        self.control_service(PHARMA_SERVICE, "restart")
            
    @cherrypy.tools.json_out()
    @cherrypy.expose
    def service_status(self):
        cherrypy.log(f"status pharma service")
        value = self.service_is_active(PHARMA_SERVICE)
        return {"status" : value}

    @cherrypy.tools.json_out()
    @cherrypy.expose
    def get_default_sequence_name(self):
        cherrypy.log(f"get default sequence name")
        cross_config = self.update_cherrypy_session()
        value = cross_config['default']
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
            
        cherrypy.log(f"json out {out}")
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
    config = Config.Config()
    webapp = Programmation(config)
    cherrypy.server.socket_host = '0.0.0.0'
    cherrypy.quickstart(webapp, '/', conf)
