"""XRPC client implementation."""
import logging

import requests

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
    """XRPC client."""

    def __init__(self, address, lexicons, **kwargs):
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

    def __getattr__(self, attr):
        if NSID_SEGMENT_RE.match(attr):
            return _NsidClient(self, attr)

        return getattr(super(), attr)

    def call(self, nsid, input, **params):
        """Makes a remote XRPC method call.

        Args:
          nsid: str, method NSID
          input: dict, input body
          params: optional method parameters

        Returns: decoded JSON object, or None if the method has no output

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

        self._maybe_validate(nsid, 'input', input)

        # run method
        url = f'{self._address}/xrpc/{nsid}'
        defn = self._get_def(nsid)
        fn = requests.get if defn['type'] == 'query' else requests.post
        logger.debug(f'Running method')
        resp = fn(url, params=params, json=input if input else None,
                  headers={'Content-Type': 'application/json'})
        logger.debug(f'Got: {resp}')
        resp.raise_for_status()

        output = None
        content_type = resp.headers.get('Content-Type', '').split(';')[0]
        if content_type == 'application/json' and resp.content:
            output = resp.json()

        self._maybe_validate(nsid, 'output', output)
        return output
