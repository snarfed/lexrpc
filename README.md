lexrpc [![Circle CI](https://circleci.com/gh/snarfed/lexrpc.svg?style=svg)](https://circleci.com/gh/snarfed/lexrpc) [![Coverage Status](https://coveralls.io/repos/github/snarfed/lexrpc/badge.svg?branch=main)](https://coveralls.io/github/snarfed/lexrpc?branch=master)
===

Python implementation of [AT Protocol](https://atproto.com/)'s [XRPC](https://atproto.com/specs/xrpc) + [Lexicon](https://atproto.com/guides/lexicon). lexrpc includes a simple [XRPC](https://atproto.com/specs/xrpc) client, server, and [Flask](https://flask.palletsprojects.com/) web server integration. All three include full [Lexicon](https://atproto.com/guides/lexicon) support for validating inputs, outputs, and parameters against their schemas.

* [Client](#client)
* [Server](#server)
* [Flask server](#flask-server)
* [Reference](https://lexrpc.readthedocs.io/en/docs/source/lexrpc.html)
* [TODO](#todo)
* [Changelog](#changelog)

License: This project is placed in the public domain.


## Client

The lexrpc client let you [call methods dynamically by their NSIDs](https://atproto.com/guides/lexicon#rpc-methods). To make a call, first instantiate a [`Client`](https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.client.Client) object with the server address and method lexicons, then use NSIDs to make calls, passing input as a dict and parameters as kwargs:

```py
from jsonschema import Client

lexicons = [...]
client = Client('https://xrpc.example.com', lexicons)
output = client.com.example.my_query({'foo': 'bar'}, param_a=5)
```

Note that `-` characters in method NSIDs are converted to `_`s, eg the call above is for the method `com.example.my-query`.


## Server

To implement an XRPC server, use the [`Server`](https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.server.Server) class. It validates parameters, inputs, and outputs. Use the [`method`](https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.server.Server.method) decorator to register handlers for each NSID, [`Server.call`](https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.server.Server.call) to call a method from your web framework or anywhere else.

```py
from jsonschema import Server

lexicons = [...]
server = Server(lexicons)

@server.method('com.example.my-query')
def my_query_hander(input, **params):
    ...
    output = ...
    return output

# In your web framework, use Server.call to run a method
input = request.json()
params = request.query_params()
# decode params here
output = server.call(input, **params)
response.write_json(output)
```


## Flask server

First, instantiate a `Server` and register method handlers as described above. Then, attach the server to your Flask app with [`init_flask`](https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.flask_server.init_flask).

```py
from flask import Flask
from lexrpc import init_flask

app = Flask('my-server')
...
init_flask(server, app)
```

This configures the Flask app to serve the methods registered with the lexrpc server [as per the spec](https://atproto.com/specs/xrpc#path). Each method is served at the path `/xrpc/[NSID]`, procedures via POSTs and queries via GETs. Parameters are decoded from query parameters, input is taken from the JSON HTTP request body, and output is returned in the JSON HTTP response body. The `Content-Type` response header is set to `application/json`.


## TODO

* support record types, eg via type "ref" and ref field pointing to the nsid in https://github.com/bluesky-social/atproto/blob/main/lexicons/app/bsky/graph/follow.json#L13 , which points to app.bsky.actor.ref , which is defined in https://github.com/bluesky-social/atproto/blob/main/lexicons/app/bsky/actor/ref.json  
  ref isn't documented on https://atproto.com/docs yet though, and these lexicons also use a defs field, which is in schemas in the Lexicon guide and spec but not really documented either. I'm guessing these parts are still under active development.
* extensions, https://atproto.com/guides/lexicon#extensibility . is there anything to do? ah, it's currently TODO in the spec: https://atproto.com/specs/xrpc#todos
* "binary blob" support, as in https://atproto.com/specs/xrpc . is it currently undefined?
* authentication, currently TODO in the spec: https://atproto.com/specs/xrpc#todos


## Changelog

### 0.1 - unreleased

Initial release!
