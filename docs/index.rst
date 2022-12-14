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

-  `Client <#client>`__
-  `Server <#server>`__
-  `Flask server <#flask-server>`__
-  `Reference <https://lexrpc.readthedocs.io/en/docs/source/lexrpc.html>`__
-  `TODO <#todo>`__
-  `Changelog <#changelog>`__

License: This project is placed in the public domain.

Client
------

The lexrpc client let you `call methods dynamically by their
NSIDs <https://atproto.com/guides/lexicon#rpc-methods>`__. To make a
call, first instantiate a
`Client <https://lexrpc.readthedocs.io/en/latest/source/lexrpc.html#lexrpc.client.Client>`__
object with the server address and method lexicons, then use method
NSIDs to make calls, passing input as a dict and parameters as kwargs:

.. code:: py

   from lexrpc import Client

   lexicons = [...]
   client = Client('https://xrpc.example.com', lexicons)
   output = client.com.example.my_query({'foo': 'bar'}, param_a=5)

Note that ``-`` characters in method NSIDs are converted to ``_``\ s, eg
the call above is for the method ``com.example.my-query``.

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
   output = server.call(input, **params)
   response.write_json(output)

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

-  support record types, eg via type “ref” and ref field pointing to the
   nsid `example
   here <https://github.com/bluesky-social/atproto/blob/main/lexicons/app/bsky/graph/follow.json#L13>`__,
   ref points to
   `app.bsky.actor.ref <https://github.com/bluesky-social/atproto/blob/main/lexicons/app/bsky/actor/ref.json>`__.
   ref isn’t documented yet though, and these lexicons also use a
   ``defs`` field, which isn’t really documented either. `they plan to
   update the docs and specs
   soon. <https://github.com/bluesky-social/atproto/pull/409#issuecomment-1348766856>`__
-  `extensions <https://atproto.com/guides/lexicon#extensibility>`__. is
   there anything to do? ah, `they’re currently TODO in the
   spec <https://atproto.com/specs/xrpc#todos>`__.
-  `“binary blob” support. <https://atproto.com/specs/xrpc>`__ currently
   undefined ish? is it based on the ``encoding`` field?
-  `authentication, currently TODO in the
   spec <https://atproto.com/specs/xrpc#todos>`__

Release instructions
--------------------

Here’s how to package, test, and ship a new release. (Note that this is
`largely duplicated in the oauth-dropins readme
too <https://github.com/snarfed/oauth-dropins#release-instructions>`__.)

1.  Run the unit tests.
    ``sh     source local/bin/activate.csh     python3 -m unittest discover``

2.  Bump the version number in ``setup.py`` and ``docs/conf.py``.
    ``git grep`` the old version number to make sure it only appears in
    the changelog. Change the current changelog entry in ``README.md``
    for this new version from *unreleased* to the current date.

3.  Build the docs. If you added any new modules, add them to the
    appropriate file(s) in ``docs/source/``. Then run
    ``./docs/build.sh``. Check that the generated HTML looks fine by
    opening ``docs/_build/html/index.html`` and looking around.

4.  ``git commit -am 'release vX.Y'``

5.  Upload to `test.pypi.org <https://test.pypi.org/>`__ for testing.
    ``sh     python3 -m build     setenv ver X.Y     twine upload -r pypitest dist/lexrpc-$ver*``

6.  Install from test.pypi.org.
    ``sh     cd /tmp     python3 -m venv local     source local/bin/activate.csh     pip3 uninstall lexrpc # make sure we force pip to use the uploaded version     pip3 install --upgrade pip     pip3 install -i https://test.pypi.org/simple --extra-index-url https://pypi.org/simple lexrpc==$ver     deactivate``

7.  Smoke test that the code trivially loads and runs.
    ``sh     source local/bin/activate.csh     python3     # run test code below     deactivate``
    Test code to paste into the interpreter: \`py from lexrpc import
    Server

    server = Server([{ ‘lexicon’: 1, ‘id’: ‘io.example.ping’, ‘defs’: {
    ‘main’: { ‘type’: ‘query’, ‘description’: ‘Ping the server’,
    ‘parameters’: {‘message’: { ‘type’: ‘string’ }}, ‘output’: {
    ‘encoding’: ‘application/json’, ‘schema’: { ‘type’: ‘object’,
    ‘required’: [‘message’], ‘properties’: {‘message’: { ‘type’:
    ‘string’ }}, }, }, }, }, }])

    @server.method(‘io.example.ping’) def ping(input, message=’‘):
    return {’message’: message}

    print(server.call(‘io.example.ping’, {}, message=‘hello world’))
    \``\`

8.  Tag the release in git. In the tag message editor, delete the
    generated comments at bottom, leave the first line blank (to omit
    the release “title” in github), put ``### Notable changes`` on the
    second line, then copy and paste this version’s changelog contents
    below it.
    ``sh     git tag -a v$ver --cleanup=verbatim     git push && git push --tags``

9.  `Click here to draft a new release on
    GitHub. <https://github.com/snarfed/lexrpc/releases/new>`__ Enter
    ``vX.Y`` in the *Tag version* box. Leave *Release title* empty. Copy
    ``### Notable changes`` and the changelog contents into the
    description text box.

10. Upload to `pypi.org <https://pypi.org/>`__!
    ``sh     twine upload dist/lexrpc-$ver*``

11. `Wait for the docs to build on Read the
    Docs <https://readthedocs.org/projects/lexrpc/builds/>`__, then
    check that they look ok.

12. On the `Versions
    page <https://readthedocs.org/projects/lexrpc/versions/>`__, check
    that the new version is active, If it’s not, activate it in the
    *Activate a Version* section.

Changelog
---------

0.1 - 2022-12-13
~~~~~~~~~~~~~~~~

Initial release!

Tested interoperability with the ``lexicon``, ``xprc``, and
``xrpc-server`` packages in
`bluesky-social/atproto <https://github.com/bluesky-social/atproto>`__.
Lexicon and XRPC are still very early and under active development;
caveat hacker!
