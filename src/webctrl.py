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
        self.logger.setLevel(logging.INFO)
        fh = RotatingFileHandler(config.logFile, maxBytes=102400, backupCount=2)
        fh.setLevel(logging.INFO)
        self.logger.addHandler(fh)
        self.logger.info("Webservice Pharma started")
    
    def load_sequences(self, fname="../config/cross.json"):
        sequences = {}
        try:
            config_file = open(fname, 'rb')
        except OSError:
            cherrypy.log(f"Could not open/read file:{fname}")
        with config_file:
            sequences = json.load(config_file)
        return sequences
    
    def restart_service(self, service_name):
        try:
            # Redémarrer le service avec systemctl
            subprocess.run(["systemctl", "restart", service_name], check=True)
            self.logger.info(f"Service {service_name} restarted.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error on restart service {service_name} : {e}")
    
    @cherrypy.expose
    def index(self):
        return open('index.html')

    @cherrypy.expose
    def save(self, sequence_name="", sequence_value=""):
        cherrypy.log(f" prog-list {sequence_name}  hex_list {sequence_value}")
        all_sequences = {}
        if 'sequences' not in cherrypy.session:
            all_sequences = self.load_sequences(self.fname)
            cherrypy.session['sequences'] = all_sequences
        else:
            all_sequences = cherrypy.session['sequences']
        cherrypy.log(f"{all_sequences}")
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
        all_sequences[sequence_name] = new_sequence
        cherrypy.session['sequences'] = all_sequences
        cherrypy.log(f"new sequence {new_sequence}")
        try:
            json_sequences = json.dumps(all_sequences)
            f = open(self.fname, "w")
            f.write(json_sequences)
            f.close()
        except OSError:
            cherrypy.log(f"Could not open/read file:{fname}")
        self.restart_service(PHARMA_SERVICE)
            

    
    @cherrypy.tools.json_out()
    @cherrypy.expose
    def load(self, sequence_name=""):
        out = ["0x0000"]
        if sequence_name == "":
            all_sequences = self.load_sequences()
            cherrypy.session['sequences'] = all_sequences
            out =  all_sequences
        elif len(sequence_name) != 0:
            if 'sequences' not in cherrypy.session:
                all_sequences = self.load_sequences()
                cherrypy.session['sequences'] = all_sequences
            out = cherrypy.session['sequences'].get(sequence_name, ["0x0000"])
            
        cherrypy.log(f"json out {out}")
        return out
    


if __name__ == '__main__':

    conf = {
        '/': {
            'tools.sessions.on': True,
            'tools.staticdir.root': os.path.abspath(os.getcwd())
        },

        # '/save': {
        #      'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        #      'tools.response_headers.on': True,
        #      'tools.response_headers.headers': [('Content-Type', 'text/plain')],
        # },
        #

        # '/load': {
        #     'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        #     'tools.response_headers.on': True,
        #     'tools.response_headers.headers': [('Content-Type', 'text/plain')],
        # },

        '/static': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': './public'
        }
    }
    config = Config.Config()
    webapp = Programmation(config)
    cherrypy.server.socket_host = '0.0.0.0'
    cherrypy.quickstart(webapp, '/', conf)
