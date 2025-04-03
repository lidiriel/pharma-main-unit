#!/bin/python
import os, os.path
import random
import string
import cherrypy
import json



class StringGenerator(object):
    @cherrypy.expose
    def index(self):
        return open('index.html')



@cherrypy.expose
class StringGeneratorWebService(object):

    @cherrypy.tools.accept(media='text/plain')
    def GET(self):
        return cherrypy.session['mystring']

    def POST(self, length=8):
        some_string = ''.join(random.sample(string.hexdigits, int(length)))
        cherrypy.session['mystring'] = some_string
        return some_string

    def PUT(self, another_string):
        cherrypy.session['mystring'] = another_string

    def DELETE(self):
        cherrypy.session.pop('mystring', None)


@cherrypy.expose
class ProgrammationWebService(object):
    
    def load_sequences(self, fname="../config/cross.json"):
        sequences = {}
        try:
            config_file = open(fname, 'rb')
        except OSError:
            print(f"Could not open/read file:{fname}")
        with config_file:
            sequences = json.load(config_file)
        return sequences
    
    @cherrypy.tools.json_out()
    def POST(self, sequence_name=""):
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

        # '/generator': {
        #     'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        #     'tools.response_headers.on': True,
        #     'tools.response_headers.headers': [('Content-Type', 'text/plain')],
        # },
        
        '/load': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'text/plain')],
        },

        '/static': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': './public'
        }
    }

    webapp = StringGenerator()
    # webapp.generator = StringGeneratorWebService()
    webapp.load = ProgrammationWebService()

    cherrypy.quickstart(webapp, '/', conf)