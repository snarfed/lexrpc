lexrpc [![Circle CI](https://circleci.com/gh/snarfed/lexrpc.svg?style=svg)](https://circleci.com/gh/snarfed/lexrpc) [![Coverage Status](https://coveralls.io/repos/github/snarfed/lexrpc/badge.svg?branch=main)](https://coveralls.io/github/snarfed/lexrpc?branch=master)
===

Python implementation of [AT Protocol](https://atproto.com/)'s [XRPC](https://atproto.com/specs/xrpc) + [Lexicon](https://atproto.com/guides/lexicon), client and server sides. [Docs here.](https://lexrpc.readthedocs.io/)

* [Getting started](#getting-started)
* [TODO](#todo)
* [Changelog](#changelog)

License: This project is placed in the public domain.


Getting started
---
lexrpc includes a simple XRPC client, server, and [Flask](https://flask.palletsprojects.com/) integration for the server. All three include full Lexicon support for validating inputs, outputs, and parameters against their schemas.


### Client

lexrpc uses [code generation](https://atproto.com/guides/lexicon#rpc-methods) to let you call methods dynamically by their NSIDs. To make a call, first instantiate a `Client` with the server address and method lexicons, then use NSIDs to make calls, passing input as a dict and parameters as kwargs:

```py
from jsonschema import Client

lexicons = [...]
client = Client('https://xrpc.example.com', lexicons)
output = client.com.example.my_query({'foo': 'bar'}, a_param=False)
```

Note that `-` characters in method NSIDs are converted to `_`s, eg the call above is for the method `com.example.my-query`.


### Server

To implement an XRPC server, use the `Server` class. It validates parameters, inputs, and outputs. Use the `method` decorator to register handlers for each NSID.

```py
from jsonschema import Server

lexicons = [...]
server = Server(lexicons)

@server.method('com.example.my-query')
def myquery(input, **params):
    ...
    return ...

# In your web framework, use Server.call to run a method
input = request.json()
params = request.query_params()
# decode params
output = server.call(input, **params)
response.write_json(output)
```


### Flask server

First, instantiate a `Server` and register method handlers as described above. Then, attach the server to your Flask app with `flask_server.init_flask`.

```py
from flask import Flask
from jsonschema import init_flask

app = Flask('my-server')
...
init_flask(server, app)
```

This serves the server's registered methods in the Flask app [as per the spec](https://atproto.com/specs/xrpc#path). Each method is served at the path `/xrpc/[NSID]`, procedures as POSTs and queries as GETs. Parameters are decoded from query parameters, input is taken from the HTTP request body, and output is returned in the HTTP response body. The `Content-Type` header is set to `application/json`.


TODO
---
* validate records/tokens in input/output? or are those only primitives?
* extensions, https://atproto.com/guides/lexicon#extensibility . is there anything to do? ah, it's currently TODO in the spec: https://atproto.com/specs/xrpc#todos
* "binary blob" support, as in https://atproto.com/specs/xrpc . is it currently undefined?
* authentication, currently TODO in the spec: https://atproto.com/specs/xrpc#todos


Changelog
---

### 0.1 - unreleased

Initial release!
