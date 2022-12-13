"""Example XRPC server for testing interop with atproto/packages/xrpc.

Specifically: https://github.com/bluesky-social/atproto/tree/main/packages/xrpc

Run this server with flask run -p 8080, then run the code in that README ^.
"""
import logging

from flask import Flask
from lexrpc import init_flask, Server

LEXICONS = [{
    'lexicon': 1,
    'id': 'io.example.ping',
    'type': 'query',
    'description': 'Ping the server',
    'parameters': {'message': { 'type': 'string' }},
    'output': {
        'encoding': 'application/json',
        'schema': {
            'type': 'object',
            'required': ['message'],
            'properties': {'message': { 'type': 'string' }},
        },
    },
}]

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config['ENV'] = 'development'
app.json.compact = False

server = Server(LEXICONS)

@server.method('io.example.ping')
def ping(input, message=''):
    return {'message': message}

init_flask(server, app)
