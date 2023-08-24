"""XRPC client implementation.

TODO:
* asyncio support for subscription websockets
"""
from io import BytesIO
import json
import logging

import dag_cbor
import requests
import simple_websocket

from .base import Base, NSID_SEGMENT_RE

logger = logging.getLogger(__name__)


class _NsidClient():
    """Internal helper class to implement dynamic attribute-based method calls.

    eg client.com.example.my_method(...)
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
      _address: str, server URL
      _headers: dict, HTTP headers to include in every request
    """

    def __init__(self, address, lexicons, headers=None, **kwargs):
        """Constructor.

        Args:
          lexicon: sequence of dict lexicons

        Raises:
          :class:`jsonschema.SchemaError`
            if any schema is invalid
        """
        super().__init__(lexicons, **kwargs)

        logger.debug(f'Using server at {address}')
        assert address.startswith('http://') or address.startswith('https://'), \
            f"{address} doesn't start with http:// or https://"
        self._address = address
        self._headers = headers or {}

    def __getattr__(self, attr):
        if NSID_SEGMENT_RE.match(attr):
            return _NsidClient(self, attr)

        return getattr(super(), attr)

    def call(self, nsid, input=None, **params):
        """Makes a remote XRPC method call.

        Args:
          nsid: str, method NSID
          input: dict, input body, optional for subscriptions
          params: optional method parameters

        Returns:
          For queries and procedures: decoded JSON object, or None if the method
            has no output
          For subscriptions: generator iterator of messages from server

        Raises:
          NotImplementedError
            if the given NSID is not found in any of the loaded lexicons
          :class:`jsonschema.ValidationError`
            if the parameters, input, or returned output don't validate against
            the method's schemas
          :class:`requests.RequestException`
            if the connection or HTTP request to the remote server failed
        """
        logger.debug(f'{nsid}: {params} {input}')

        # validate params and input, then encode params
        self._maybe_validate(nsid, 'parameters', params)
        params = self.encode_params(params)

        type = self._get_def(nsid)['type']
        if type == 'subscription':
            self._maybe_validate(nsid, 'input', input)

        headers = {
            **self._headers,
            'Content-Type': 'application/json',
        }

        # run method
        url = f'{self._address}/xrpc/{nsid}'
        if params:
            url += f'?{params}'

        if type == 'subscription':
            return self._subscribe(url)
        else:
            # query or procedure
            fn = requests.get if type == 'query' else requests.post
            logger.debug(f'Running {fn} {url} {input} {params} {headers}')
            resp = fn(url, json=input if input else None, headers=headers)
            logger.debug(f'Got: {resp}')
            resp.raise_for_status()

            output = None
            content_type = resp.headers.get('Content-Type', '').split(';')[0]
            if content_type == 'application/json' and resp.content:
                output = resp.json()

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
