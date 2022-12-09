"""XRPC client implementation.

TODO: usage description
"""
import logging

import requests

from .base import XrpcBase

logger = logging.getLogger(__name__)


class Client(XrpcBase):
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

    def call(self, nsid, params=None, input=None):
        """Makes a remote XRPC method call.

        Args:
          nsid: str, method NSID
          params: dict, optional method parameters
          input: dict, optional input body

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

        self._validate(nsid, 'input', input)

        # encode params
        if params:
            params = {name: self._encode_param(val) for name, val in params.items()}

        # run method
        url = f'{self._address}/xrpc/{nsid}'
        lexicon = self._get_lexicon(nsid)
        fn = requests.get if lexicon['type'] == 'query' else requests.post
        logger.debug(f'Running method')
        resp = fn(url, params=params,
                  json=input if input else None,
                  headers={'Content-Type': 'application/json'},
                  )
        logger.debug(f'Got: {resp}')
        resp.raise_for_status()

        if resp.headers.get('Content-Type') == 'application/json' and resp.content:
            output = resp.json()
            self._validate(nsid, 'output', output)
            return output

    @staticmethod
    def _encode_param(param):
        """Encodes a parameter value.

        Based on https://atproto.com/specs/xrpc#path

        requests URL-encodes all query parameters, so here we only need to
        handle booleans.
        """
        return 'true' if param is True else 'false' if param is False else param
