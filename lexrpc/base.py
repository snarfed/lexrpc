"""Base code shared by both server and client."""
import copy
import logging
import re
import urllib.parse

import jsonschema
from jsonschema.validators import validator_for

logger = logging.getLogger(__name__)

LEXICON_TYPES = frozenset((
    'query',
    'procedure',
    'record',
    'token',
))
LEXICON_METHOD_TYPES = frozenset((
    'query',
    'procedure',
))
PARAMETER_TYPES = frozenset((
    'boolean',
    'integer',
    'number',
    'string',
))

# https://atproto.com/specs/nsid
NSID_SEGMENT = '[a-zA-Z0-9-]+'
NSID_SEGMENT_RE = re.compile(f'^{NSID_SEGMENT}$')
NSID_RE = re.compile(f'^{NSID_SEGMENT}(\.{NSID_SEGMENT})*$')


def fail(msg, exc=NotImplementedError):
    """Logs an error and raises an exception with the given message."""
    logger.error(msg)
    raise exc(msg)


class Base():
    """Base class for both XRPC client and server."""

    _lexicons = None  # dict mapping NSID to lexicon object

    def __init__(self, lexicons):
        """Constructor.

        Args:
          lexicons: sequence of dict lexicons

        Raises:
          :class:`jsonschema.SchemaError`
            if any schema is invalid
        """
        assert isinstance(lexicons, (list, tuple))
        self._lexicons = {l['id']: l for l in copy.deepcopy(lexicons)}
        logger.debug(f'Got lexicons for: {self._lexicons.keys()}')

        # validate schemas, convert parameters field into full JSON schema
        for i, lexicon in enumerate(self._lexicons.values()):
            id = lexicon.get('id')
            assert id, f'Lexicon {i} missing id field'
            logger.debug(f'Validating {id}')

            main = lexicon.get('defs', {}).get('main')
            if not main:
                logger.warning(f'Ignoring lexicon {id} with no defs.main')
                continue
            method = self._lexicons[id] = main

            type = method.get('type')
            assert type in LEXICON_TYPES, f'Bad type for lexicon {id}: {type}'

            # preprocess parameters properties into full JSON Schema
            params = method.get('parameters', {})
            method['parameters'] = {
                'schema': {
                    'type': 'object',
                    'required': params.get('required', []),
                    'properties': params.get('properties', {}),
                },
            }

            # validate schemas
            for field in 'input', 'output', 'parameters', 'record':
                logger.debug(f'Validating {id} {field} schema')
                schema = method.get(field, {}).get('schema')
                if schema:
                    validator_for(schema).check_schema(schema)

    def _get_lexicon(self, nsid):
        """Returns the given lexicon object.

        Raises:
          NotImplementedError
            if no lexicon exists for the given NSID
        """
        lexicon = self._lexicons.get(nsid)
        if not lexicon:
            fail(f'{nsid} not found')

        return lexicon

    def _validate(self, nsid, type, obj):
        """Validates a JSON object against a given schema.

        Args:
          nsid: str, method NSID
          type: either 'input' or 'output'
          obj: decoded JSON object

        Returns: None

        Raises:
          NotImplementedError
            if no lexicon exists for the given NSID, or the lexicon does not
            define a schema for the given type
          :class:`jsonschema.ValidationError`
            if the object is invalid
        """
        assert type in ('input', 'output', 'parameters', 'record'), type

        schema = self._get_lexicon(nsid).get(type, {}).get('schema')
        if not schema:
            if not obj:
                return
            fail(f'{nsid} has no schema for {type}')

        logger.debug(f'Validating {nsid} {type}')
        try:
            jsonschema.validate(obj, schema)
        except jsonschema.ValidationError as e:
            e.message = f'Error validating {nsid} {type}: {e.message}'
            raise

    def encode_params(self, params):
        """Encodes decoded parameter values.

        Based on https://atproto.com/specs/xrpc#path

        Args:
          params: dict mapping str names to boolean, number, or str values

        Returns: dict mapping str names to str encoded values
        """
        return {name: ('true' if val is True
                       else 'false' if val is False
                       else urllib.parse.quote(str(val)))
                for name, val in params.items()}

    def decode_params(self, method_nsid, params):
        """Decodes encoded parameter values.

        Based on https://atproto.com/specs/xrpc#path

        Args:
          method_nsid: str
          params: dict mapping str names to encoded str values

        Returns: dict mapping str names to decoded boolean, number, and str values

        Raises:
          ValueError
            if a parameter value can't be decoded
          NotImplementedError
            if no method lexicon is registered for the given NSID
        """
        lexicon = self._get_lexicon(method_nsid)
        params_schema = lexicon.get('parameters', {})\
                               .get('schema', {})\
                               .get('properties', {})

        decoded = {}
        for name, val in params.items():
            type = params_schema.get(name, {}).get('type') or 'string'
            assert type in PARAMETER_TYPES

            if type == 'boolean':
                if val == 'true':
                    decoded[name] = True
                elif val == 'false':
                    decoded[name] = False
                else:
                    raise ValueError(
                        f'Got {val!r} for boolean parameter {name}, expected true or false')

            try:
                if type == 'number':
                    decoded[name] = float(val)
                elif type == 'int':
                    decoded[name] = int(val)
            except ValueError as e:
                e.args = [f'{e.args[0]} for {type} parameter {name}']
                raise e

            if type == 'string':
                decoded[name] = val

        return decoded
