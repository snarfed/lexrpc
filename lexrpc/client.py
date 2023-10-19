"""XRPC client implementation.

TODO:

* asyncio support for subscription websockets
"""
import copy
from io import BytesIO
import json
import logging
from urllib.parse import urljoin

import dag_cbor
import requests
import simple_websocket

from .base import Base, NSID_SEGMENT_RE

logger = logging.getLogger(__name__)

DEFAULT_PDS = 'https://bsky.social/'
DEFAULT_HEADERS = {
    'User-Agent': 'lexrpc (https://lexrpc.readthedocs.io/)',
}
LOGIN_NSID = 'com.atproto.server.createSession'


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

    Attributes:
      address (str): base URL of XRPC server, eg ``https://bsky.social/``
      access_token (str): sent in ``Authorization`` header
      headers (dict): HTTP headers to include in every request
    """

    def __init__(self, address=DEFAULT_PDS, access_token=None, headers=None,
                 **kwargs):
        """Constructor.

        Args:
          address (str): base URL of XRPC server, eg ``https://bsky.social/``
          access_token (str): optional, will be sent in ``Authorization`` header
          headers (dict): optional, HTTP headers to include in every request
          kwargs: passed through to :class:`Base`

        Raises:
          jsonschema.SchemaError: if any schema is invalid
        """
        super().__init__(**kwargs)

        logger.debug(f'Using server at {address}')
        assert address.startswith('http://') or address.startswith('https://'), \
            f"{address} doesn't start with http:// or https://"
        self.address = address
        self.headers = headers or {}
        self.access_token = access_token

    def __getattr__(self, attr):
        if NSID_SEGMENT_RE.match(attr):
            return _NsidClient(self, attr)

        return getattr(super(), attr)

    def call(self, nsid, input=None, **params):
        """Makes a remote XRPC method call.

        Args:
          nsid (str): method NSID
          input (dict): input body, optional for subscriptions
          params: optional method parameters

        Returns:
          dict or generator iterator: for queries and procedures, decoded JSON object, or None if the method has no output. For subscriptions, generator of messages from server.

        Raises:
          NotImplementedError: if the given NSID is not found in any of the
            loaded lexicons
          jsonschema.ValidationError: if the parameters, input, or returned
            output don't validate against the method's schemas
          requests.RequestException: if the connection or HTTP request to the
            remote server failed
        """
        logger.debug(f'{nsid}: {params} {input}')

        # validate params and input, then encode params
        self._maybe_validate(nsid, 'parameters', params)
        params = self.encode_params(params)

        type = self._get_def(nsid)['type']
        if type == 'subscription':
            self._maybe_validate(nsid, 'input', input)

        headers = {
            **DEFAULT_HEADERS,
            **self.headers,
            'Content-Type': 'application/json',
        }
        log_headers = copy.copy(headers)
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
            log_headers['Authorization'] = '...'

        # run method
        url = urljoin(self.address, f'/xrpc/{nsid}')
        if params:
            url += f'?{params}'

        if type == 'subscription':
            return self._subscribe(url)
        else:
            # query or procedure
            fn = requests.get if type == 'query' else requests.post
            logger.debug(f'Running {fn} {url} {input} {params} {log_headers}')
            resp = fn(url, json=input if input else None, headers=headers)
            if not resp.ok:
                logger.debug(f'Got: {resp.text}')
            resp.raise_for_status()

            output = None
            content_type = resp.headers.get('Content-Type', '').split(';')[0]
            if content_type == 'application/json' and resp.content:
                output = resp.json()
                if nsid == LOGIN_NSID:
                    if token := output.get('accessJwt'):
                        logger.info(f'Logged into {self.address} as {output.get("did")}, setting access_token')
                        self.access_token = token

            self._maybe_validate(nsid, 'output', output)
            return output

    def _subscribe(self, url):
        """Connects to a subscription websocket, yields the returned messages."""
        ws = simple_websocket.Client(url)

        try:
            while True:
                buf = BytesIO(ws.receive())
                header = dag_cbor.decode(buf, allow_concat=True)
                payload = dag_cbor.decode(buf)
                yield (header, payload)
        except simple_websocket.ConnectionClosed as cc:
            logger.debug(cc)
