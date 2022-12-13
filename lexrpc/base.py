"""Base code shared by both server and client."""
import copy
import logging
import re

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
            type = lexicon.get('type')
            assert type in LEXICON_TYPES, f'Bad type for lexicon {id}: {type}'

            # preprocess parameters properties into full JSON Schema
            props = lexicon.get('parameters', {})
            lexicon['parameters'] = {
                'schema': {
                    'type': 'object',
                    'required': [],
                    'properties': props,
                },
            }
            for name, schema in props.items():
                if schema.pop('required', False):
                    lexicon['parameters']['schema']['required'].append(name)

            # validate schemas
            for field in 'input', 'output', 'parameters', 'record':
                logger.debug(f'Validating {id} {field} schema')
                schema = lexicon.get(field, {}).get('schema')
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

    @staticmethod
    def _encode_param(param):
        """Encodes a parameter value to a string.

        Based on https://atproto.com/specs/xrpc#path

        requests URL-encodes all query parameters, so here we only need to
        handle booleans.

        Args:
          param: boolean, number, or str

        Returns: str
        """
        return 'true' if param is True else 'false' if param is False else str(param)

    @staticmethod
    def _decode_param(param, name, type):
        """Decodes a parameter value from string.

        Based on https://atproto.com/specs/xrpc#path

        Args:
          param: str
          type: str, 'string' or 'number' or 'integer' or 'boolean'

        Returns: boolean, number, or str, depending on type
        """
        assert type in PARAMETER_TYPES

        if type == 'boolean':
            if param == 'true':
                return True
            if param == 'false':
                return False
            else:
                raise jsonschema.ValidationError(
                    f'Got {param!r} for boolean parameter {name}, expected true or false')

        try:
            if type == 'number':
                return float(param)
            elif type == 'int':
                return int(param)
        except ValueError:
            raise jsonschema.ValidationError(f'Got {param!r} for {type} parameter {name}')

        assert type == 'string'
        return param
