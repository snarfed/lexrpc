"""Flask handler for /xrpc/... endpoint."""
import logging

from flask import request
from flask.json import jsonify
from flask.views import View
from jsonschema import ValidationError

from .base import NSID_RE

logger = logging.getLogger(__name__)


def init_flask(xrpc_server, app):
    """Connects a :class:`lexrpc.Server` to serve on /xrpc/... on a Flask app.

    Args:
      xrpc_server: :class:`lexrpc.Server`
      app: :class:`flask.Flask`
    """
    logger.info(f'Registering {xrpc_server} with {app}')
    app.add_url_rule('/xrpc/<nsid>',
                     view_func=XrpcEndpoint.as_view('xrpc-endpoint', xrpc_server),
                     methods=['GET', 'POST'])


class XrpcEndpoint(View):
    """Handles inbound XRPC requests.

    Attributes:
      server: :class:`lexrpc.Server`
    """
    server = None

    def __init__(self, server):
        self.server = server

    def dispatch_request(self, nsid):
        if not NSID_RE.match(nsid):
            return {'message': f'{nsid} is not a valid NSID'}, 400
        try:
            lexicon = self.server._get_def(nsid)
        except NotImplementedError as e:
            return {'message': str(e)}, 501

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
        except NotImplementedError as e:
            return {'message': str(e)}, 501
        except ValidationError as e:
            return {'message': str(e)}, 400
        except ValueError as e:
            logging.info(f'Method raised', exc_info=True)
            return {'message': str(e)}, 400

        # prepare output
        out_encoding = lexicon.get('output', {}).get('encoding')
        if out_encoding in ('application/json', None):
            return jsonify(output or '')
        else:
            # binary
            if not isinstance(output, (str, bytes)):
                return {'message': f'Expected str or bytes output to match {out_encoding}, got {output.__class__}'}, 500
            return output
