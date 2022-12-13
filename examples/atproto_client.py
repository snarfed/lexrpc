"""Example XRPC client for testing interop with atproto/packages/xrpc-server.

Specifically: https://github.com/bluesky-social/atproto/tree/main/packages/xrpc-server

Run the code in that README ^, then run this with python atproto_client.py
"""
import logging

import requests

from lexrpc import Client

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

client = Client('http://localhost:8080', LEXICONS)
try:
  output = client.io.example.ping({}, message='fooey')
  print(output)
except requests.HTTPError as e:
    print(e)
    print(e.response.text)
