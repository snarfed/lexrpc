lexrpc [![Circle CI](https://circleci.com/gh/snarfed/lexrpc.svg?style=svg)](https://circleci.com/gh/snarfed/lexrpc) [![Coverage Status](https://coveralls.io/repos/github/snarfed/lexrpc/badge.svg?branch=main)](https://coveralls.io/github/snarfed/lexrpc?branch=master)
===

Python implementation of [AT Protocol](https://atproto.com/)'s [XRPC](https://atproto.com/specs/xrpc) + [Lexicon](https://atproto.com/guides/lexicon). [Docs here.](https://lexrpc.readthedocs.io/)


## Known issues
* The design choice of converting method NSIDs to snake case method names, ie translating both `.` and `-` characters to `_`, makes some methods ambiguous. Eg `com.foo.bar.baz` and `com.foo-bar` both result in calling the `com_foo_bar_baz` method. Right now the server doesn't allow loading lexicons with method NSIDs that conflict like this, but we should probably reconsider the design.
