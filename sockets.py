#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, request, render_template, make_response
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__, template_folder='static')
sockets = Sockets(app)
app.debug = True

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        #self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            try:
                listener(entity, self.get(entity))
            except:
                self.listeners.remove(listener)

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

myWorld = World()        

def set_listener(socket, entity, data ):
    ''' do something with the update ! '''
    obj = {}
    obj[entity] = data
    socket.send(json.dumps(obj))

@app.route('/')
def hello():
    return render_template('index.html')

def read_ws(ws,client):
    '''A greenlet function that reads from the websocket and updates the world'''
    r = ws.receive()
    d = json.loads(r)
    for entity in d:
        for key in d[entity]:
            myWorld.update(entity, key, d[entity][key])
        myWorld.update_listeners(entity)

@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    myWorld.add_set_listener(lambda x, y : set_listener(ws, x, y))
    ws.send(json.dumps(myWorld.world()))
    while True:
        try:
            read_ws(ws,None)
        except:
            ws.close()
            break
       

def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data != ''):
        return json.loads(request.data)
    else:
        return json.loads(request.form.keys()[0])

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    d = json.loads(request.data)
    for key in d:
        myWorld.update(entity, key, d[key])
    return request.data

@app.route("/world", methods=['POST','GET'])    
def world():
    response = make_response(json.dumps(myWorld.world()))
    response.headers['Content-Type'] = "application/json"
    
    return response

@app.route("/entity/<entity>")    
def get_entity(entity):
    return json.dumps(myWorld.get(entity))


@app.route("/clear", methods=['POST','GET'])
def clear():
    myWorld.clear()
    return ""



if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
