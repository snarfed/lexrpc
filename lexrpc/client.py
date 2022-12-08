"""XRPC client implementation.

TODO: usage description
"""
import copy
import json
import logging

import jsonschema
import requests

logger = logging.getLogger(__name__)


class Client():
    """XRPC client class."""

    _lexicons = None  # dict mapping NSID to lexicon object

    def __init__(self, address, lexicons):
        """Constructor.

        Args:
          lexicon: sequence of dict lexicons

        Raises:
          :class:`jsonschema.SchemaError` if any schema is invalid
        """
        logger.debug(f'Using server at {address}')
        assert address.startswith('http://') or address.startswith('https://'), \
            f"{address} doesn't start with http:// or https://"
        self._address = address

        logger.debug(f'Got lexicons: {json.dumps(lexicons, indent=2)}')
        assert isinstance(lexicons, (list, tuple))

        self._lexicons = {s['id']: s for s in copy.deepcopy(lexicons)}

        # validate schemas
        for i, lexicon in enumerate(self._lexicons.values()):
            id = lexicon.get('id')
            assert id, f'Lexicon {i} missing id field'
            type = lexicon.get('type')
            assert type in ('query', 'procedure'), f'Bad type for lexicon {id}: {type}'
            for field in 'input', 'output':
                schema = lexicon.get(field, {}).get('schema')
                if schema:
                    try:
                        jsonschema.validate(None, schema)
                    except jsonschema.ValidationError as e:
                        # schema passed validation, None instance failed
                        pass

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

        lexicon = self._lexicons.get(nsid)
        if not lexicon:
            msg = f'{nsid} not found'
            logger.error(msg)
            raise NotImplementedError(msg)

        # validate input
        input_schema = lexicon.get('input', {}).get('schema')
        if input_schema:
            logger.debug('Validating input')
            jsonschema.validate(input, input_schema)

        # run method
        url = f'{self._address}/xrpc/{nsid}'
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
            # validate
            logger.debug('Validating output')
            output_schema = lexicon.get('output', {}).get('schema')
            if output_schema:
                jsonschema.validate(output, output_schema)
            return output
