"""Flask handler for /xrpc/... endpoint."""
import logging

from flask import request
from flask.json import jsonify
from flask.views import View
from jsonschema import ValidationError

from .base import NSID_RE

logger = logging.getLogger(__name__)


def init_flask(xrpc_server, app):
    """Connects a Server to serve on /xrpc/... on a Flask app.

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

    def dispatch_request(self, nsid=None):
        if not NSID_RE.match(nsid):
            return {'message': f'{nsid} is not a valid NSID'}, 400

        # decode typed method params from string query params
        try:
            lexicon = self.server._get_lexicon(nsid)
        except NotImplementedError as e:
            return {'message': str(e)}, 501

        param_schema = lexicon.get('parameters', {})\
                              .get('schema', {})\
                              .get('properties', {})
        params = {}
        for name, value in request.args.items():
            type = param_schema.get(name, {}).get('type') or 'string'
            try:
                params[name] = self.server._decode_param(value, name=name, type=type)
            except ValidationError as e:
                return {'message': str(e)}, 400

        # run method
        try:
            input = request.json if request.content_length else {}
            output = self.server.call(nsid, params=params, input=input)
            return jsonify(output or '')
        except ValidationError as e:
            return {'message': str(e)}, 400
