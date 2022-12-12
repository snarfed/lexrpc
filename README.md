lexrpc [![Circle CI](https://circleci.com/gh/snarfed/lexrpc.svg?style=svg)](https://circleci.com/gh/snarfed/lexrpc) [![Coverage Status](https://coveralls.io/repos/github/snarfed/lexrpc/badge.svg?branch=main)](https://coveralls.io/github/snarfed/lexrpc?branch=master)
===

Python implementation of [AT Protocol](https://atproto.com/)'s [XRPC](https://atproto.com/specs/xrpc) + [Lexicon](https://atproto.com/guides/lexicon). [Docs here.](https://lexrpc.readthedocs.io/)

License: This project is placed in the public domain.

## TODO
* validate records (and tokens?) in input/output
* fill in server.py and client.py docstrings, and/or getting started guide here
* extensions, https://atproto.com/guides/lexicon#extensibility . is there anything to do? ah, it's currently TODO in the spec: https://atproto.com/specs/xrpc#todos
* "binary blob" support, as in https://atproto.com/specs/xrpc . is it currently undefined?
* authentication, currently TODO in the spec: https://atproto.com/specs/xrpc#todos
