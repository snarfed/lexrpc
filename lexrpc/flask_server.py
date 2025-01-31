"""Flask handler for ``/xrpc/...`` endpoints."""
from collections import defaultdict, namedtuple
from datetime import datetime, timedelta
import logging

import dag_cbor
import dag_json
from flask import after_this_request, make_response, request
from flask.json import jsonify
from flask.views import View
from flask_sock import Sock
from iterators import TimeoutIterator
import libipld
from multiformats import CID
from simple_websocket import ConnectionClosed
from werkzeug.exceptions import TooManyRequests

from . import base
from .base import NSID_RE, ValidationError
from .server import Redirect

logger = logging.getLogger(__name__)

SUBSCRIPTION_ITERATOR_TIMEOUT = timedelta(seconds=10)

RESPONSE_HEADERS = {
    # wide open CORS to allow client-side apps like https://bsky.app/
    'Access-Control-Allow-Headers': '*',
    'Access-Control-Allow-Methods': '*',
    'Access-Control-Allow-Origin': '*',
}

# maps string NSID to Subscriber
subscribers = defaultdict(list)
Subscriber = namedtuple('Subscriber', ('ip', 'user_agent', 'args', 'start'))


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
            return make_response('', r.status, {'Location': r.to, **r.headers})
        except NotImplementedError as e:
            return {
                'error': 'MethodNotImplemented',
                'message': str(e),
            }, 501, RESPONSE_HEADERS
        except (ValidationError, ValueError) as e:
            if isinstance(e, ValueError):
                logging.debug(f'Method raised', exc_info=True)
            return {
                'error': getattr(e, 'name', 'InvalidRequest'),
                'message': getattr(e, 'message', str(e)),
            }, 400, {**RESPONSE_HEADERS, **getattr(e, 'headers', {})}

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

    Note that this calls the XRPC method on a *different thread*, so that it can
    block on it there while still periodically checking in the request thread
    that the websocket client is still connected.

    Args:
      xrpc_server (lexrpc.Server)
      nsid (str): XRPC method NSID
    """
    def handle(ws):
        """
        Args:
          ws (wsproto.WSConnection)
        """
        params = xrpc_server.decode_params(nsid, request.args.items(multi=True))

        # use TimeoutIterator here so that we can periodically detect if the
        # client has disconnected. if we don't, we'll tie up this thread forever
        # while we block waiting for results from the XRPC server method, and
        # we'll eventually exhaust the WSGI worker thread pool. background:
        # https://github.com/miguelgrinberg/flask-sock/issues/78
        iter = TimeoutIterator(xrpc_server.call(nsid, **params),
                               timeout=SUBSCRIPTION_ITERATOR_TIMEOUT.total_seconds())
        for result in iter:
            if not ws.connected:
                logger.debug(f'Websocket client disconnected from {nsid}')
                iter.interrupt()
                return
            elif result == iter.get_sentinel():
                continue

            header, payload = result
            # TODO: validate header, payload?

            # log
            seq = payload.get('seq')
            did = payload.get('did') or payload.get('repo')
            commit = payload.get('commit')
            if isinstance(commit, CID):
                commit = f'commit {commit.encode("base32")}'
            # can't DAG-JSON encode payload here? maybe? it hits
            # ValueError: Failed to encode DAG-CBOR. Unknown cbor tag `0`
            # https://console.cloud.google.com/errors/detail/CNzlgrvr2bHuvwE;time=PT1H;refresh=true;locations=global?project=bridgy-federated
            # eg dag_json.encode(payload, dialect="atproto")[:500]
            logger.debug(f'Sending {nsid.split(".")[-1]} {seq} {did} {header.get("t")}')

            # emit!
            try:
                ws.send(dag_cbor.encode(header) + dag_cbor.encode(payload))
            except (ConnectionError, ConnectionClosed, OSError) as err:
                logger.debug(f'Websocket client disconnected from {nsid}: {err}')
                iter.interrupt()
                return

    def track_subscriber(ws):
        # support X-Forwarded-For header:
        # https://cloud.google.com/appengine/docs/flexible/reference/request-headers#app_engine-specific_headers
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-For
        if x_forwarded_for := request.headers.get('X-Forwarded-For'):
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.remote_addr

        for client in subscribers[nsid]:
            if client.ip == ip:
                logger.debug(f'Rejecting connection, already connected for {nsid}: {ip} {request.user_agent}')
                raise TooManyRequests()

        logger.debug(f'New websocket client for {nsid}: {ip} {request.user_agent}')
        subscriber = Subscriber(ip=ip,
                                user_agent=str(request.user_agent),
                                args=request.args.to_dict(),
                                start=base.now().replace(microsecond=0))
        subscribers[nsid].append(subscriber)

        try:
            handle(ws)
        finally:
            # ideally I'd use Flask's after_this_request instead, but it doesn't
            # guarantee that it'll run if the request raises an uncaught
            # exception. teardown_request does, but it runs on *every* request.
            subscribers[nsid].remove(subscriber)

    return track_subscriber
