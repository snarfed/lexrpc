lexrpc
------

Python implementation of `AT Protocol <https://atproto.com/>`__\ ’s
`XRPC <https://atproto.com/specs/xrpc>`__ +
`Lexicon <https://atproto.com/guides/lexicon>`__. lexrpc includes a
simple `XRPC <https://atproto.com/specs/xrpc>`__ client, server, and
`Flask <https://flask.palletsprojects.com/>`__ web server integration.
All three include full `Lexicon <https://atproto.com/guides/lexicon>`__
support for validating inputs, outputs, and parameters against their
schemas.

Install from `PyPI <https://pypi.org/project/lexrpc/>`__ with
``pip install lexrpc`` or ``pip install lexrpc[flask]``.

License: This project is placed in the public domain. You may also use
it under the `CC0
License <https://creativecommons.org/publicdomain/zero/1.0/>`__.

-  `Client <#client>`__
-  `Server <#server>`__
-  `Flask server <#flask-server>`__
-  `Reference
   docs <https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html>`__
-  `TODO <#todo>`__
-  `Release instructions <#release-instructions>`__
-  `Changelog <#changelog>`__

Client
------

The lexrpc client let you `call methods dynamically by their
NSIDs <https://atproto.com/guides/lexicon#rpc-methods>`__. To make a
call, first instantiate a
`Client <https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.client.Client>`__,
then use NSIDs to make calls, passing input as a dict and parameters as
kwargs. Here’s an example of logging into the `official Bluesky
PDS <https://bsky.app/>`__ and fetching the user’s timeline:

.. code:: py

   from lexrpc import Client

   client = Client()
   session = client.com.atproto.server.createSession({
       'identifier': 'snarfed.bsky.social',
       'password': 'hunter2',
   })
   print('Logged in as', session['did'])

   timeline = client.app.bsky.feed.getTimeline(limit=10)
   print('First 10 posts:', json.dumps(timeline, indent=2))

By default, ``Client`` connects to the official ``bsky.social`` PDS and
uses the `official
lexicons <https://github.com/bluesky-social/atproto/tree/main/lexicons/>`__
for ``app.bsky`` and ``com.atproto``. You can connect to a different PDS
or use custom lexicons by passing them to the ``Client`` constructor:

.. code:: py

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

Note that ``-`` characters in method NSIDs are converted to ``_``\ s, eg
the call above is for the method ``com.example.my-procedure``.

To call a method with non-JSON (eg binary) input, pass ``bytes`` to the
call instead of a ``dict``, and pass the content type with
``headers={'Content-Type': '...'}``.

`Event stream methods <https://atproto.com/specs/event-stream>`__ with
type ``subscription`` are generators that ``yield`` (header, payload)
tuples sent by the server. They take parameters as kwargs, but no
positional ``input``.

.. code:: py

   for header, msg in client.com.example.count(start=1, end=10):
       print(header['t'])
       print(msg['num'])

Server
------

To implement an XRPC server, use the
`Server <https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.server.Server>`__
class. It validates parameters, inputs, and outputs. Use the
`method <https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.server.Server.method>`__
decorator to register method handlers and
`call <https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.server.Server.call>`__
to call them, whether from your web framework or anywhere else.

.. code:: py

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

You can also register a method handler with
`Server.register <https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.server.Server.register>`__:

::

   server.register('com.example.my-query', my_query_handler)

As with ``Client``, you can use custom lexicons by passing them to the
``Server`` constructor:

::

   lexicons = [
     {
       "lexicon": 1,
       "id": "com.example.myQuery",
       "defs": ...
     },
     ...
   ]
   server = Server(lexicons=lexicons)

`Event stream methods <https://atproto.com/specs/event-stream>`__ with
type ``subscription`` should be generators that ``yield`` frames to send
to the client. `Each
frame <https://atproto.com/specs/event-stream#framing>`__ is a
``(header dict, payload dict)`` tuple that will be DAG-CBOR encoded and
sent to the websocket client. Subscription methods take parameters as
kwargs, but no positional ``input``.

::

   @server.method('com.example.count')
   def count(start=None, end=None):
       for num in range(start, end):
           yield {'num': num}

Flask server
------------

To serve XRPC methods in a
`Flask <https://flask.palletsprojects.com/>`__ web app, first install
the lexrpc package with the ``flask`` extra, eg
``pip install lexrpc[flask]``. Then, instantiate a
`Server <https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.server.Server>`__
and register method handlers as described above. Finally, attach the
server to your Flask app with
`flask_server.init_flask <https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.flask_server.init_flask>`__.

.. code:: py

   from flask import Flask
   from lexrpc.flask_server import init_flask

   # instantiate a Server like above
   server = ...

   app = Flask('my-server')
   init_flask(server, app)

This configures the Flask app to serve the methods registered with the
lexrpc server `as per the spec <https://atproto.com/specs/xrpc#path>`__.
Each method is served at the path ``/xrpc/[NSID]``, procedures via POSTs
and queries via GETs. Parameters are decoded from query parameters,
input is taken from the JSON HTTP request body, and output is returned
in the JSON HTTP response body. The ``Content-Type`` response header is
set to ``application/json``.

TODO
----

-  schema validation for records

Release instructions
--------------------

Here’s how to package, test, and ship a new release.

1.  Run the unit tests.

    .. code:: sh

       source local/bin/activate.csh
       python3 -m unittest discover

2.  Bump the version number in ``pyproject.toml`` and ``docs/conf.py``.
    ``git grep`` the old version number to make sure it only appears in
    the changelog. Change the current changelog entry in ``README.md``
    for this new version from *unreleased* to the current date.

3.  Build the docs. If you added any new modules, add them to the
    appropriate file(s) in ``docs/source/``. Then run
    ``./docs/build.sh``. Check that the generated HTML looks fine by
    opening ``docs/_build/html/index.html`` and looking around.

4.  ``git commit -am 'release vX.Y'``

5.  Upload to `test.pypi.org <https://test.pypi.org/>`__ for testing.

    .. code:: sh

       python3 -m build
       setenv ver X.Y
       twine upload -r pypitest dist/lexrpc-$ver*

6.  Install from test.pypi.org.

    .. code:: sh

       cd /tmp
       python3 -m venv local
       source local/bin/activate.csh
       pip3 uninstall lexrpc # make sure we force pip to use the uploaded version
       pip3 install --upgrade pip
       pip3 install -i https://test.pypi.org/simple --extra-index-url https://pypi.org/simple lexrpc==$ver
       deactivate

7.  Smoke test that the code trivially loads and runs.

    .. code:: sh

       source local/bin/activate.csh
       python3
       # run test code below
       deactivate

    Test code to paste into the interpreter:

    .. code:: py

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

8.  Tag the release in git. In the tag message editor, delete the
    generated comments at bottom, leave the first line blank (to omit
    the release “title” in github), put ``### Notable changes`` on the
    second line, then copy and paste this version’s changelog contents
    below it.

    .. code:: sh

       git tag -a v$ver --cleanup=verbatim
       git push && git push --tags

9.  `Click here to draft a new release on
    GitHub. <https://github.com/snarfed/lexrpc/releases/new>`__ Enter
    ``vX.Y`` in the *Tag version* box. Leave *Release title* empty. Copy
    ``### Notable changes`` and the changelog contents into the
    description text box.

10. Upload to `pypi.org <https://pypi.org/>`__!

    .. code:: sh

       twine upload dist/lexrpc-$ver.tar.gz dist/lexrpc-$ver-py3-none-any.whl

11. `Wait for the docs to build on Read the
    Docs <https://readthedocs.org/projects/lexrpc/builds/>`__, then
    check that they look ok.

12. On the `Versions
    page <https://readthedocs.org/projects/lexrpc/versions/>`__, check
    that the new version is active, If it’s not, activate it in the
    *Activate a Version* section.

Changelog
---------

0.6 - 2024-03-16
~~~~~~~~~~~~~~~~

-  Drop ``typing-extensions`` version pin now that `typing-validation
   has been updated to be compatible with
   it <https://github.com/hashberg-io/typing-validation/issues/1>`__.
-  Update bundled ``app.bsky`` and ``com.atproto`` lexicons, as of
   `bluesky-social/atproto@f45eef3 <https://github.com/bluesky-social/atproto/commit/f45eef3414f8827ba3a6958a7040c7e38bfd6282>`__.

.. _section-1:

0.5 - 2023-12-10
~~~~~~~~~~~~~~~~

-  ``Client``:

   -  Support binary request data automatically based on input type, eg
      ``dict`` vs ``bytes``.
   -  Add new ``headers`` kwarg to ``call`` and auto-generated lexicon
      method calls, useful for providing an explicit ``Content-Type``
      when sending binary data.
   -  Bug fix: don’t infinite loop if ``refreshSession`` fails.
   -  Other minor authentication bug fixes.

.. _section-2:

0.4 - 2023-10-28
~~~~~~~~~~~~~~~~

-  Bundle `the official
   lexicons <https://github.com/bluesky-social/atproto/tree/main/lexicons/>`__
   for ``app.bsky`` and ``com.atproto``, use them by default.
-  ``Base``:

   -  Expose lexicons in ``defs`` attribute.

-  ``Client``:

   -  Add minimal auth support with ``access_token`` and
      ``refresh_token`` constructor kwargs and ``session`` attribute. If
      you use a ``Client`` to call ``com.atproto.server.createSession``
      or ``com.atproto.server.refreshSession``, the returned tokens will
      be automatically stored and used in future requests.
   -  Bug fix: handle trailing slash on server address, eg
      ``http://ser.ver/`` vs ``http://ser.ver``.
   -  Default server address to official ``https://bsky.social`` PDS.
   -  Add default
      ``User-Agent: lexrpc (https://lexrpc.readthedocs.io/)`` request
      header.

-  ``Server``:

   -  Add new ``Redirect`` class. Handlers can raise this to indicate
      that the web server should serve an HTTP redirect. `Whether this
      is official supported by the XRPC spec is still
      TBD. <https://github.com/bluesky-social/atproto/discussions/1228>`__

-  ``flask_server``:

   -  Return HTTP 405 error on HTTP requests to subscription (websocket)
      XRPCs.
   -  Support the new ``Redirect`` exception.
   -  Add the ``error`` field to the JSON response bodies for most error
      responses.

.. _section-3:

0.3 - 2023-08-29
~~~~~~~~~~~~~~~~

-  Add array type support.
-  Add support for non-JSON input and output encodings.
-  Add ``subscription`` method type support over websockets.
-  Add ``headers`` kwarg to ``Client`` constructor.
-  Add new ``Server.register`` method for manually registering handlers.
-  Bug fix for server ``@method`` decorator.

.. _section-4:

0.2 - 2023-03-13
~~~~~~~~~~~~~~~~

Bluesky’s Lexicon design and schema handling is still actively changing,
so this is an interim release. It generally supports the current lexicon
design, but not full schema validation yet. I’m not yet trying to fast
follow the changes too closely; as they settle down and stabilize, I’ll
put more effort into matching and fully implementing them. Stay tuned!

*Breaking changes:*

-  Fully migrate to `new lexicon
   format <https://github.com/snarfed/atproto/commit/63b9873bb1699b6bce54e7a8d3db2fcbd2cfc5ab>`__.
   Original format is no longer supported.

.. _section-5:

0.1 - 2022-12-13
~~~~~~~~~~~~~~~~

Initial release!

Tested interoperability with the ``lexicon``, ``xprc``, and
``xrpc-server`` packages in
`bluesky-social/atproto <https://github.com/bluesky-social/atproto>`__.
Lexicon and XRPC themselves are still very early and under active
development; caveat hacker!
