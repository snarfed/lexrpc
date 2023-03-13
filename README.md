lexrpc [![Circle CI](https://circleci.com/gh/snarfed/lexrpc.svg?style=svg)](https://circleci.com/gh/snarfed/lexrpc) [![Coverage Status](https://coveralls.io/repos/github/snarfed/lexrpc/badge.svg?branch=main)](https://coveralls.io/github/snarfed/lexrpc?branch=master)
===

Python implementation of [AT Protocol](https://atproto.com/)'s [XRPC](https://atproto.com/specs/xrpc) + [Lexicon](https://atproto.com/guides/lexicon). lexrpc includes a simple [XRPC](https://atproto.com/specs/xrpc) client, server, and [Flask](https://flask.palletsprojects.com/) web server integration. All three include full [Lexicon](https://atproto.com/guides/lexicon) support for validating inputs, outputs, and parameters against their schemas.

Install from [PyPI](https://pypi.org/project/lexrpc/) with `pip install lexrpc` or `pip install lexrpc[flask]`.

License: This project is placed in the public domain.

* [Client](#client)
* [Server](#server)
* [Flask server](#flask-server)
* [Reference docs](https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html)
* [TODO](#todo)
* [Release instructions](#release-instructions)
* [Changelog](#changelog)


## Client

The lexrpc client let you [call methods dynamically by their NSIDs](https://atproto.com/guides/lexicon#rpc-methods). To make a call, first instantiate a [`Client`](https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.client.Client) object with the server address and method lexicons, then use method NSIDs to make calls, passing input as a dict and parameters as kwargs:

```py
from lexrpc import Client

lexicons = [...]
client = Client('https://xrpc.example.com', lexicons)
output = client.com.example.my_query({'foo': 'bar'}, param_a=5)
```

Note that `-` characters in method NSIDs are converted to `_`s, eg the call above is for the method `com.example.my-query`.


## Server

To implement an XRPC server, use the [`Server`](https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.server.Server) class. It validates parameters, inputs, and outputs. Use the [`method`](https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.server.Server.method) decorator to register method handlers and [`call`](https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.server.Server.call) to call them, whether from your web framework or anywhere else.

```py
from lexrpc import Server

lexicons = [...]
server = Server(lexicons)

@server.method('com.example.my-query')
def my_query_hander(input, **params):
    output = {'foo': input['foo'], 'b': params['param_a'] + 1}
    return output

# Extract nsid and decode query parameters from an HTTP request,
# call the method, return the output in an HTTP response
nsid = request.path.removeprefix('/xrpc/')
input = request.json()
params = server.decode_params(nsid, request.query_params())
output = server.call(nsid, input, **params)
response.write_json(output)
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

* support record types, eg via type "ref" and ref field pointing to the nsid [example here](https://github.com/bluesky-social/atproto/blob/main/lexicons/app/bsky/graph/follow.json#L13), ref points to [`app.bsky.actor.ref`](https://github.com/bluesky-social/atproto/blob/main/lexicons/app/bsky/actor/ref.json). ref isn't documented yet though, and these lexicons also use a `defs` field, which isn't really documented either. [they plan to update the docs and specs soon.](https://github.com/bluesky-social/atproto/pull/409#issuecomment-1348766856)
  * check out [atproto@63b9873bb1699b6bce54e7a8d3db2fcbd2cfc5ab](https://github.com/snarfed/atproto/commit/63b9873bb1699b6bce54e7a8d3db2fcbd2cfc5ab)!
* [extensions](https://atproto.com/guides/lexicon#extensibility). is there anything to do? ah, [they're currently TODO in the spec](https://atproto.com/specs/xrpc#todos).
* ["binary blob" support.](https://atproto.com/specs/xrpc) currently undefined ish? is it based on the `encoding` field?
* [authentication, currently TODO in the spec](https://atproto.com/specs/xrpc#todos)


Release instructions
---
Here's how to package, test, and ship a new release.

1. Run the unit tests.
    ```sh
    source local/bin/activate.csh
    python3 -m unittest discover
    ```
1. Bump the version number in `pyproject.toml` and `docs/conf.py`. `git grep` the old version number to make sure it only appears in the changelog. Change the current changelog entry in `README.md` for this new version from _unreleased_ to the current date.
1. Build the docs. If you added any new modules, add them to the appropriate file(s) in `docs/source/`. Then run `./docs/build.sh`. Check that the generated HTML looks fine by opening `docs/_build/html/index.html` and looking around.
1. `git commit -am 'release vX.Y'`
1. Upload to [test.pypi.org](https://test.pypi.org/) for testing.
    ```sh
    python3 -m build
    setenv ver X.Y
    twine upload -r pypitest dist/lexrpc-$ver*
    ```
1. Install from test.pypi.org.
    ```sh
    cd /tmp
    python3 -m venv local
    source local/bin/activate.csh
    pip3 uninstall lexrpc # make sure we force pip to use the uploaded version
    pip3 install --upgrade pip
    pip3 install -i https://test.pypi.org/simple --extra-index-url https://pypi.org/simple lexrpc==$ver
    deactivate
    ```
1. Smoke test that the code trivially loads and runs.
    ```sh
    source local/bin/activate.csh
    python3
    # run test code below
    deactivate
    ```
    Test code to paste into the interpreter:
    ```py
    from lexrpc import Server

    server = Server([{
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

### 0.2 - 2023-03-13

Bluesky's Lexicon design and schema handling is still actively changing, so this is an interim release. It generally supports the current lexicon design, but not full schema validation yet. I'm not yet trying to fast follow the changes too closely; as they settle down and stabilize, I'll put more effort into matching and fully implementing them. Stay tuned!

_Breaking changes:_

* Fully migrate to [new lexicon format](https://github.com/snarfed/atproto/commit/63b9873bb1699b6bce54e7a8d3db2fcbd2cfc5ab). Original format is no longer supported.


### 0.1 - 2022-12-13

Initial release!

Tested interoperability with the `lexicon`, `xprc`, and `xrpc-server` packages in [bluesky-social/atproto](https://github.com/bluesky-social/atproto). Lexicon and XRPC themselves are still very early and under active development; caveat hacker!
