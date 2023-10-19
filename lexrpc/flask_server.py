"""Flask handler for ``/xrpc/...`` endpoints."""
import logging

import dag_cbor
from flask import redirect, request
from flask.json import jsonify
from flask.views import View
from flask_sock import Sock
from jsonschema import ValidationError
from simple_websocket import ConnectionClosed

from .base import NSID_RE
from .server import Redirect

logger = logging.getLogger(__name__)

RESPONSE_HEADERS = {
    # wide open CORS to allow client-side apps like https://bsky.app/
    'Access-Control-Allow-Headers': '*',
    'Access-Control-Allow-Methods': '*',
    'Access-Control-Allow-Origin': '*',
}


def init_flask(xrpc_server, app):
    """Connects a :class:`lexrpc.Server` to serve ``/xrpc/...`` on a Flask app.

    Args:
      xrpc_server (lexrpc.Server)
      app (flask.Flask)
    """
    logger.info(f'Registering {xrpc_server} with {app}')

    sock = Sock(app)
    for nsid, _ in xrpc_server._methods.items():
        if xrpc_server.defs[nsid]['type'] == 'subscription':
            sock.route(f'/xrpc/{nsid}')(subscription(xrpc_server, nsid))

    app.add_url_rule('/xrpc/<nsid>',
                     view_func=XrpcEndpoint.as_view('xrpc-endpoint', xrpc_server),
                     methods=['GET', 'POST', 'OPTIONS'])


class XrpcEndpoint(View):
    """Handles inbound XRPC query and procedure (but not subscription) methods.

    Attributes:
      server (lexrpc.Server)
    """
    server = None

    def __init__(self, server):
        self.server = server

    def dispatch_request(self, nsid):
        if not NSID_RE.match(nsid):
            return {
                'error': 'InvalidRequest',
                'message': f'{nsid} is not a valid NSID',
            }, 400, RESPONSE_HEADERS
        try:
            lexicon = self.server._get_def(nsid)
        except NotImplementedError as e:
            return {
                'error': 'MethodNotImplemented',
                'message': str(e),
            }, 501, RESPONSE_HEADERS

        if lexicon['type'] == 'subscription':
            return {'message': f'Use websocket for {nsid}, not HTTP'}, 405

        if request.method == 'OPTIONS':
            return '', 200, RESPONSE_HEADERS

        # prepare input
        in_encoding = lexicon.get('input', {}).get('encoding')
        if in_encoding in ('application/json', None):
            input = request.json if request.content_length else {}
        else:
            # binary
            if request.content_type != in_encoding:
                logger.warning(f'expecting input encoding {in_encoding}, request has Content-Type {request.content_type} !')
            input = request.get_data()

        # run method
        try:
            params = self.server.decode_params(nsid, request.args.items(multi=True))
            # TODO: for binary input/output, support streaming with eg
            # io.BufferedReader/Writer?
            output = self.server.call(nsid, input=input, **params)
        except Redirect as r:
            return redirect(r.to)
        except NotImplementedError as e:
            return {
                'error': 'MethodNotImplemented',
                'message': str(e),
            }, 501, RESPONSE_HEADERS
        except (ValidationError, ValueError) as e:
            if isinstance(e, ValueError):
                logging.info(f'Method raised', exc_info=True)
            return {
                'error': 'InvalidRequest',
                'message': str(e),
            }, 400, RESPONSE_HEADERS

        # prepare output
        out_encoding = lexicon.get('output', {}).get('encoding')
        if out_encoding in ('application/json', None):
            return jsonify(output or ''), RESPONSE_HEADERS
        else:
            # binary
            if not isinstance(output, (str, bytes)):
                return {'message': f'Expected str or bytes output to match {out_encoding}, got {output.__class__}'}, 500
            return output, RESPONSE_HEADERS


def subscription(xrpc_server, nsid):
    """Generates websocket handlers for inbound XRPC subscription methods.

    Args:
      xrpc_server (lexrpc.Server)
      nsid (str): XRPC method NSID
    """
    def handler(ws):
        """
        Args:
          ws (simple_websocket.ws.WSConnection)
        """
        logger.debug(f'New websocket client for {nsid}')
        params = xrpc_server.decode_params(nsid, request.args.items(multi=True))
        try:
            for header, payload in xrpc_server.call(nsid, **params):
                # TODO: validate header, payload?
                logger.debug(f'Sending to {nsid} websocket client: {header} {str(payload)[:500]}...')
                ws.send(dag_cbor.encode(header) + dag_cbor.encode(payload))
        except ConnectionClosed as cc:
            logger.debug(f'Websocket client disconnected from {nsid}: {cc}')

    return handler
