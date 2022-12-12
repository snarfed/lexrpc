"""XRPC client implementation."""
import logging

import requests

from .base import NSID_SEGMENT_RE, Base

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

    def __init__(self, address, lexicons):
        """Constructor.

        Args:
          lexicon: sequence of dict lexicons

        Raises:
          :class:`jsonschema.SchemaError` if any schema is invalid
        """
        super().__init__(lexicons)

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
          NotImplementedError, if the given NSID is not found in any of the
            loaded lexicons
          :class:`jsonschema.ValidationError`, if the input or output returned
            by the method doesn't validate against the method's schemas
          :class:`requests.Exception`, if the connection or HTTP request to the
            remote server failed
        """
        logger.debug(f'{nsid}: {params} {input}')

        # validate params and input, then encode params. pass non-null object to
        # validate to force it to actually validate the object.
        self._validate(nsid, 'parameters', params)
        self._validate(nsid, 'input', input)

        params = {name: self._encode_param(val) for name, val in params.items()}

        # run method
        url = f'{self._address}/xrpc/{nsid}'
        lexicon = self._get_lexicon(nsid)
        fn = requests.get if lexicon['type'] == 'query' else requests.post
        logger.debug(f'Running method')
        resp = fn(url, params=params, json=input,
                  headers={'Content-Type': 'application/json'})
        logger.debug(f'Got: {resp}')
        resp.raise_for_status()

        output = None
        if resp.headers.get('Content-Type') == 'application/json' and resp.content:
            output = resp.json()

        self._validate(nsid, 'output', output or {})
        return output
