"""XRPC client implementation.

TODO:

* asyncio support for subscription websockets
"""
import copy
from io import BytesIO, IOBase
import json
import logging
from urllib.parse import urljoin

import libipld
import requests
import simple_websocket

from .base import Base, NSID_SEGMENT_RE

logger = logging.getLogger(__name__)

DEFAULT_PDS = 'https://bsky.social/'
DEFAULT_HEADERS = {
    'User-Agent': 'lexrpc (https://lexrpc.readthedocs.io/)',
}
LOGIN_NSID = 'com.atproto.server.createSession'
REFRESH_NSID = 'com.atproto.server.refreshSession'
TOKEN_ERRORS = (
    'AccountNotFound',
    'AuthenticationRequired',
    'ExpiredToken',
    'InvalidToken',
    'TokenRequired',
)


class _NsidClient():
    """Internal helper class to implement dynamic attribute-based method calls.

    eg ``client.com.example.my_method(...)``
    """
    client = None
    nsid = None

    def __init__(self, client, nsid):
        assert client and nsid
        self.client = client
        self.nsid = nsid

    def __getattr__(self, attr):
        segment = attr.replace('_', '-')
        if NSID_SEGMENT_RE.match(segment):
            return _NsidClient(self.client, f'{self.nsid}.{segment}')

        return getattr(super(), attr)

    def __call__(self, *args, **kwargs):
        return self.client.call(self.nsid, *args, **kwargs)


class Client(Base):
    """XRPC client.

    Calling ``com.atproto.server.createSession`` will store the returned session
    and include its acccess token in subsequent requests. If a request fails
    with ``ExpiredToken`` and we have a session stored, the access token will be
    refreshed with ``com.atproto.server.refreshSession`` and then the original
    request will be retried.

    Attributes:
      address (str): base URL of XRPC server, eg ``https://bsky.social/``
      session (dict): ``createSession`` response with ``accessJwt``,
        `refreshJwt``, ``handle``, and ``did``
      requests_kwargs (dict): passed to :func:`requests.get`/:func:`requests.post`
    """

    def __init__(self, address=None, access_token=None, refresh_token=None,
                 session_callback=None, lexicons=None, validate=True, truncate=False,
                 **requests_kwargs):
        """Constructor.

        Args:
          address (str): base URL of XRPC server, eg ``https://bsky.social/``
          access_token (str): optional, will be sent in ``Authorization`` header
          refresh_token (str): optional; used to refresh access token
          session_callback (callable, dict or requests.auth.AuthBase => None): called
            when a new session is created with new access and refresh tokens, or when
            ``auth.token`` changes, eg it gets refreshed. This callable is passed one
            positional argument: if the client has ``access_token``, the dict JSON
            output from ``com.atproto.server.createSession`` or
            ``com.atproto.server.refreshSession``; or if the client has ``auth``,
            auth itself.
          lexicons (sequence of dict): lexicons, optional. If not provided,
            defaults to the official, built in ``com.atproto`` and ``app.bsky``
            lexicons.
          validate (bool): whether to validate schemas, parameters, and input
            and output bodies
          truncate (bool): whether to truncate string values that are longer
            than their ``maxGraphemes`` or ``maxLength`` in their lexicon
          requests_kwargs: passed to :func:`requests.get`/:func:`requests.post`, eg
            ``auth`` (:class:`requests.auth.AuthBase`), ``headers`` (dict),
            ``timeout`` (int, seconds), etc.

        Raises:
          ValidationError: if any lexicon schema is invalid
        """
        super().__init__(lexicons=lexicons, validate=validate, truncate=truncate)

        assert not ((access_token or refresh_token) and requests_kwargs.get('auth'))

        if address:
            assert address.startswith('http://') or address.startswith('https://'), \
                f"{address} doesn't start with http:// or https://"
            self.address = address
        else:
            self.address = DEFAULT_PDS
        # logger.debug(f'Using server at {address}')

        self.requests_kwargs = copy.copy(requests_kwargs)
        headers = self.requests_kwargs.setdefault('headers', {})
        for name, val in DEFAULT_HEADERS.items():
            headers.setdefault(name, val)

        self.session = {}
        if access_token or refresh_token:
            self.session.update({
                'accessJwt': access_token,
                'refreshJwt': refresh_token,
            })
        self.session_callback = session_callback

    def __getattr__(self, attr):
        if NSID_SEGMENT_RE.match(attr):
            return _NsidClient(self, attr)

        return getattr(super(), attr)

    def call(self, nsid, input=None, headers={}, decode=True, **params):
        """Makes a remote XRPC method call.

        Args:
          nsid (str): method NSID
          input (dict or bytes): input body, optional for subscriptions
          headers (dict): HTTP headers to include in this request. Overrides any
            headers passed to the constructor.
          decode (bool): if this is a subscription, decode header and payload
            before returning, otherwise return raw bytes
          params: optional method parameters

        Returns:
          dict, requests.Response, or generator iterator: for queries and
          procedures with JSON output, decoded JSON object or None if the method
          has no output. For non-JSON output, the full requests.Response object.
          For subscriptions, generator of messages from server, as (dict header,
          dict payload) tuple if ``decode`` is True, bytes otherwise.

        Raises:
          NotImplementedError: if the given NSID is not found in any of the
            loaded lexicons
          ValidationError: if the parameters, input, or returned output don't
            validate against the method's schemas
          requests.RequestException: if the connection or HTTP request to the
            remote server failed
        """
        # logger.debug(f'{nsid}: {params} {self.loggable(input)}')

        # strip null params, validate params and input, then encode params
        params = {k: v for k, v in params.items() if v is not None}
        params = self.validate(nsid, 'parameters', params)
        params_str = self.encode_params(params)

        type = self._get_def(nsid)['type']
        if type == 'subscription':
            input = self.validate(nsid, 'input', input)

        requests_kwargs = copy.copy(self.requests_kwargs)
        headers = {
            'Content-Type': 'application/json',
            **requests_kwargs.pop('headers'),
            **headers,
        }

        # auth
        token = (self.session.get('refreshJwt') if nsid == REFRESH_NSID
                 else self.session.get('accessJwt'))
        if token:
            headers['Authorization'] = f'Bearer {token}'

        # run method
        url = urljoin(self.address, f'/xrpc/{nsid}')
        if params_str:
            url += f'?{params_str}'

        # event stream
        if type == 'subscription':
            return self._subscribe(url, nsid, decode=decode)

        # query or procedure
        fn = requests.get if type == 'query' else requests.post

        # buffer binary inputs in memory. ideally we'd stream instead, but if we
        # have to refresh our token below, we need to seek the stream back to the
        # beginning, and not all streams are seekable, eg requests.Request.raw
        if isinstance(input, IOBase) or hasattr(input, 'read'):
            input = input.read()

        logger.debug(f'requests.{getattr(fn, "__name__", fn)} {url} {params_str} {self.loggable(input)} {headers} {requests_kwargs}')

        if auth := requests_kwargs.get('auth'):
            orig_token = getattr(auth, 'token', None)
        resp = fn(
          url,
          json=input if input and isinstance(input, dict) else None,
          data=input if input and not isinstance(input, dict) else None,
          headers=headers,
          **requests_kwargs,
        )

        if (auth and self.session_callback
                and getattr(auth, 'token', None) != orig_token):
            self.session_callback(auth)

        output = resp.content
        content_type = resp.headers.get('Content-Type', '').split(';')[0]
        if content_type == 'application/json' and resp.content:
            output = resp.json()

        if not resp.ok:
            logger.debug(f'Got {resp.status_code}: {resp.text}')

        if nsid in (LOGIN_NSID, REFRESH_NSID):  # auth
            if resp.ok:
                logger.debug(f'Logged in as {output.get("did")}, storing session')
            else:
                logger.debug(f'Login failed, nulling out session')
                output = {}

            self.session = output
            if self.session_callback:
                self.session_callback(output)

        elif not resp.ok:  # token expired, try to refresh it
            if (output and isinstance(output, dict)
                    and output.get('error') in TOKEN_ERRORS
                    # for these, error field is InvalidRequest (missing PLC code),
                    # InvalidToken (bad code), or AuthMissing (no Authorization header)
                    and not (type == 'procedure'
                             and nsid.startswith('com.atproto.identity'))):
                self.call(REFRESH_NSID)
                return self.call(nsid, input=input, headers=headers, **params)  # retry

        resp.raise_for_status()

        # logger.debug(json.dumps(output, indent=2))
        output = self.validate(nsid, 'output', output)

        # Return full Response object for non-JSON outputs
        if content_type != 'application/json':
            return resp

        return output

    def _subscribe(self, url, nsid, decode=True):
        """Connects to a subscription websocket, yields the returned messages.

        Args:
          url (str): websocket URL to connect to
          nsid (str): subscription method NSID
          decode (bool): if True, decodes messages before returning

        Returns:
          (dict header, dict payload) or bytes: tuple of dicts if ``decode`` is
            True, otherwise raw bytes

        Raises:
          ValidationError: if ``decode`` is True and an output payload doesn't
            validate gainst the subscription method's lexicon
        """
        ws = simple_websocket.Client(url, headers={
            **DEFAULT_HEADERS,
            **self.requests_kwargs.get('headers', {}),
        })

        try:
            while True:
                msg = ws.receive()
                if decode:
                    header, payload = libipld.decode_dag_cbor_multi(msg)
                    payload = self.validate(nsid, 'message', payload)
                    yield (header, payload)
                else:
                    yield msg
        except simple_websocket.ConnectionClosed as cc:
            logger.debug(cc)
