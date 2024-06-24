lexrpc [![Circle CI](https://circleci.com/gh/snarfed/lexrpc.svg?style=svg)](https://circleci.com/gh/snarfed/lexrpc) [![Coverage Status](https://coveralls.io/repos/github/snarfed/lexrpc/badge.svg?branch=main)](https://coveralls.io/github/snarfed/lexrpc?branch=master)
===

Python implementation of [AT Protocol](https://atproto.com/)'s [XRPC](https://atproto.com/specs/xrpc) + [Lexicon](https://atproto.com/guides/lexicon). lexrpc includes a simple [XRPC](https://atproto.com/specs/xrpc) client, server, and [Flask](https://flask.palletsprojects.com/) web server integration. All three include full [Lexicon](https://atproto.com/guides/lexicon) support for validating inputs, outputs, and parameters against their schemas.

Install from [PyPI](https://pypi.org/project/lexrpc/) with `pip install lexrpc` or `pip install lexrpc[flask]`.

License: This project is placed in the public domain. You may also use it under the [CC0 License](https://creativecommons.org/publicdomain/zero/1.0/).

* [Client](#client)
* [Server](#server)
* [Flask server](#flask-server)
* [Reference docs](https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html)
* [TODO](#todo)
* [Release instructions](#release-instructions)
* [Changelog](#changelog)


## Client

The lexrpc client let you [call methods dynamically by their NSIDs](https://atproto.com/guides/lexicon#rpc-methods). To make a call, first instantiate a [`Client`](https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.client.Client), then use NSIDs to make calls, passing input as a dict and parameters as kwargs. Here's an example of logging into the [official Bluesky PDS](https://bsky.app/) and fetching the user's timeline:

```py
from lexrpc import Client

client = Client()
session = client.com.atproto.server.createSession({
    'identifier': 'snarfed.bsky.social',
    'password': 'hunter2',
})
print('Logged in as', session['did'])

timeline = client.app.bsky.feed.getTimeline(limit=10)
print('First 10 posts:', json.dumps(timeline, indent=2))
```


By default, `Client` connects to the official `bsky.social` PDS and uses the [official lexicons](https://github.com/bluesky-social/atproto/tree/main/lexicons/) for `app.bsky` and `com.atproto`. You can connect to a different PDS or use custom lexicons by passing them to the `Client` constructor:

```py
lexicons = [
  {
    "lexicon": 1,
    "id": "com.example.my-procedure",
    "defs": ...
  },
  ...
]
client = Client('my.server.com', lexicons=lexicons)
output = client.com.example.my_procedure({'foo': 'bar'}, baz=5)
```

Note that `-` characters in method NSIDs are converted to `_`s, eg the call above is for the method `com.example.my-procedure`.

To call a method with non-JSON (eg binary) input, pass `bytes` to the call instead of a `dict`, and pass the content type with `headers={'Content-Type': '...'}`.

[Event stream methods](https://atproto.com/specs/event-stream) with type `subscription` are generators that `yield` (header, payload) tuples sent by the server. They take parameters as kwargs, but no positional `input`.

```py
for header, msg in client.com.example.count(start=1, end=10):
    print(header['t'])
    print(msg['num'])
```


## Server

To implement an XRPC server, use the [`Server`](https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.server.Server) class. It validates parameters, inputs, and outputs. Use the [`method`](https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.server.Server.method) decorator to register method handlers and [`call`](https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.server.Server.call) to call them, whether from your web framework or anywhere else.

```py
from lexrpc import Server

server = Server()

@server.method('com.example.my-query')
def my_query(input, num=None):
    output = {'foo': input['foo'], 'b': num + 1}
    return output

# Extract nsid and decode query parameters from an HTTP request,
# call the method, return the output in an HTTP response
nsid = request.path.removeprefix('/xrpc/')
input = request.json()
params = server.decode_params(nsid, request.query_params())
output = server.call(nsid, input, **params)
response.write_json(output)
```

You can also register a method handler with [`Server.register`](https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.server.Server.register):

```
server.register('com.example.my-query', my_query_handler)
```

As with `Client`, you can use custom lexicons by passing them to the `Server` constructor:

```
lexicons = [
  {
    "lexicon": 1,
    "id": "com.example.myQuery",
    "defs": ...
  },
  ...
]
server = Server(lexicons=lexicons)
```

[Event stream methods](https://atproto.com/specs/event-stream) with type `subscription` should be generators that `yield` frames to send to the client. [Each frame](https://atproto.com/specs/event-stream#framing) is a `(header dict, payload dict)` tuple that will be DAG-CBOR encoded and sent to the websocket client. Subscription methods take parameters as kwargs, but no positional `input`.

```
@server.method('com.example.count')
def count(start=None, end=None):
    for num in range(start, end):
        yield {'num': num}
```


## Flask server

To serve XRPC methods in a [Flask](https://flask.palletsprojects.com/) web app, first install the lexrpc package with the `flask` extra, eg `pip install lexrpc[flask]`. Then, instantiate a [`Server`](https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.server.Server) and register method handlers as described above. Finally, attach the server to your Flask app with [`flask_server.init_flask`](https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.flask_server.init_flask).

```py
from flask import Flask
from lexrpc.flask_server import init_flask

# instantiate a Server like above
server = ...

app = Flask('my-server')
init_flask(server, app)
```

This configures the Flask app to serve the methods registered with the lexrpc server [as per the spec](https://atproto.com/specs/xrpc#path). Each method is served at the path `/xrpc/[NSID]`, procedures via POSTs and queries via GETs. Parameters are decoded from query parameters, input is taken from the JSON HTTP request body, and output is returned in the JSON HTTP response body. The `Content-Type` response header is set to `application/json`.


## TODO

* schema validation for records


Release instructions
---
Here's how to package, test, and ship a new release.

1. Run the unit tests.

    ```sh
    source local/bin/activate.csh
    python -m unittest discover
    ```
1. Bump the version number in `pyproject.toml` and `docs/conf.py`. `git grep` the old version number to make sure it only appears in the changelog. Change the current changelog entry in `README.md` for this new version from _unreleased_ to the current date.
1. Build the docs. If you added any new modules, add them to the appropriate file(s) in `docs/source/`. Then run `./docs/build.sh`. Check that the generated HTML looks fine by opening `docs/_build/html/index.html` and looking around.
1. `git commit -am 'release vX.Y'`
1. Upload to [test.pypi.org](https://test.pypi.org/) for testing.

    ```sh
    python -m build
    setenv ver X.Y
    twine upload -r pypitest dist/lexrpc-$ver*
    ```
1. Install from test.pypi.org.

    ```sh
    cd /tmp
    python -m venv local
    source local/bin/activate.csh
    pip uninstall lexrpc # make sure we force pip to use the uploaded version
    pip install --upgrade pip
    pip install -i https://test.pypi.org/simple --extra-index-url https://pypi.org/simple lexrpc==$ver
    deactivate
    ```
1. Smoke test that the code trivially loads and runs.

    ```sh
    source local/bin/activate.csh
    python
    # run test code below
    deactivate
    ```
    Test code to paste into the interpreter:

    ```py
    from lexrpc import Server

    server = Server(lexicons=[{
        'lexicon': 1,
        'id': 'io.example.ping',
        'defs': {
            'main': {
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
            },
        },
    }])

    @server.method('io.example.ping')
    def ping(input, message=''):
        return {'message': message}

    print(server.call('io.example.ping', {}, message='hello world'))
    ```
1. Tag the release in git. In the tag message editor, delete the generated comments at bottom, leave the first line blank (to omit the release "title" in github), put `### Notable changes` on the second line, then copy and paste this version's changelog contents below it.

    ```sh
    git tag -a v$ver --cleanup=verbatim
    git push && git push --tags
    ```
1. [Click here to draft a new release on GitHub.](https://github.com/snarfed/lexrpc/releases/new) Enter `vX.Y` in the _Tag version_ box. Leave _Release title_ empty. Copy `### Notable changes` and the changelog contents into the description text box.
1. Upload to [pypi.org](https://pypi.org/)!

    ```sh
    twine upload dist/lexrpc-$ver.tar.gz dist/lexrpc-$ver-py3-none-any.whl
    ```
1. [Wait for the docs to build on Read the Docs](https://readthedocs.org/projects/lexrpc/builds/), then check that they look ok.
1. On the [Versions page](https://readthedocs.org/projects/lexrpc/versions/), check that the new version is active, If it's not, activate it in the _Activate a Version_ section.


## Changelog

### 0.7 - 2024-06-24

* Fix websocket subscription server hang with blocking server XRPC methods due to exhausting worker thread pool ([#8](https://github.com/snarfed/lexrpc/issues/8)).
* Add `truncate` kwarg to `Client` and `Server` constructors to automatically truncate (ellipsize) string values that are longer than their ``maxGraphemes`` or ``maxLength`` in their lexicon. Defaults to `False`.
* Add new `base.XrpcError` exception type for named errors in method definitions.
* `flask_server`:
  * Handle `base.XrpcError`, convert to [JSON error response](https://atproto.com/specs/xrpc#error-responses) with `error` and `message` fields.
* `Client`:
  * Bug fix for calls with binary inputs that refresh the access token. Calls with binary input now buffer the entire input in memory. ([snarfed/bridgy#1670](https://github.com/snarfed/bridgy/issues/1670))
  * Bug fix: omit null (`None`) parameters instead of passing them with string value `None`.
* Update bundled `app.bsky` and `com.atproto` lexicons, as of [bluesky-social/atproto@15cc6ff37c326d5c186385037c4bfe8b60ea41b1](https://github.com/bluesky-social/atproto/commit/15cc6ff37c326d5c186385037c4bfe8b60ea41b1).

### 0.6 - 2024-03-16

* Drop `typing-extensions` version pin now that [typing-validation has been updated to be compatible with it](https://github.com/hashberg-io/typing-validation/issues/1).
* Update bundled `app.bsky` and `com.atproto` lexicons, as of [bluesky-social/atproto@f45eef3](https://github.com/bluesky-social/atproto/commit/f45eef3414f8827ba3a6958a7040c7e38bfd6282).

### 0.5 - 2023-12-10

* `Client`:
  * Support binary request data automatically based on input type, eg `dict` vs `bytes`.
  * Add new `headers` kwarg to `call` and auto-generated lexicon method calls, useful for providing an explicit `Content-Type` when sending binary data.
  * Bug fix: don't infinite loop if `refreshSession` fails.
  * Other minor authentication bug fixes.

### 0.4 - 2023-10-28

* Bundle [the official lexicons](https://github.com/bluesky-social/atproto/tree/main/lexicons/) for `app.bsky` and `com.atproto`, use them by default.
* `Base`:
  * Expose lexicons in `defs` attribute.
* `Client`:
  * Add minimal auth support with `access_token` and `refresh_token` constructor kwargs and `session` attribute. If you use a `Client` to call `com.atproto.server.createSession` or `com.atproto.server.refreshSession`, the returned tokens will be automatically stored and used in future requests.
  * Bug fix: handle trailing slash on server address, eg `http://ser.ver/` vs `http://ser.ver`.
  * Default server address to official `https://bsky.social` PDS.
  * Add default `User-Agent: lexrpc (https://lexrpc.readthedocs.io/)` request header.
* `Server`:
  * Add new `Redirect` class. Handlers can raise this to indicate that the web server should serve an HTTP redirect. [Whether this is official supported by the XRPC spec is still TBD.](https://github.com/bluesky-social/atproto/discussions/1228)
* `flask_server`:
  * Return HTTP 405 error on HTTP requests to subscription (websocket) XRPCs.
  * Support the new `Redirect` exception.
  * Add the `error` field to the JSON response bodies for most error responses.


### 0.3 - 2023-08-29

* Add array type support.
* Add support for non-JSON input and output encodings.
* Add `subscription` method type support over websockets.
* Add `headers` kwarg to `Client` constructor.
* Add new `Server.register` method for manually registering handlers.
* Bug fix for server `@method` decorator.


### 0.2 - 2023-03-13

Bluesky's Lexicon design and schema handling is still actively changing, so this is an interim release. It generally supports the current lexicon design, but not full schema validation yet. I'm not yet trying to fast follow the changes too closely; as they settle down and stabilize, I'll put more effort into matching and fully implementing them. Stay tuned!

_Breaking changes:_

* Fully migrate to [new lexicon format](https://github.com/snarfed/atproto/commit/63b9873bb1699b6bce54e7a8d3db2fcbd2cfc5ab). Original format is no longer supported.


### 0.1 - 2022-12-13

Initial release!

Tested interoperability with the `lexicon`, `xprc`, and `xrpc-server` packages in [bluesky-social/atproto](https://github.com/bluesky-social/atproto). Lexicon and XRPC themselves are still very early and under active development; caveat hacker!
