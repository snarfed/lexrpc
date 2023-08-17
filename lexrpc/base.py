"""Base code shared by both server and client."""
import copy
import logging
import re
import urllib.parse

import jsonschema
from jsonschema import validators

logger = logging.getLogger(__name__)

METHOD_TYPES = frozenset((
    'query',
    'procedure',
    'subscription',
))
LEXICON_TYPES = METHOD_TYPES | frozenset((
    'object',
    'record',
    'ref',
    'token',
))
PARAMETER_TYPES = frozenset((
    'array',
    'boolean',
    'integer',
    'number',
    'string',
))

# https://atproto.com/specs/nsid
NSID_SEGMENT = '[a-zA-Z0-9-]+'
NSID_SEGMENT_RE = re.compile(f'^{NSID_SEGMENT}$')
NSID_RE = re.compile(f'^{NSID_SEGMENT}(\.{NSID_SEGMENT})*$')


# TODO: drop jsonschema, implement from scratch? maybe skip until some methods
# are implemented? probably not?

# in progress code to extend jsonschema validator to support ref etc
#
# def is_ref(checker, instance):
#     return True

# class CustomValidator(validators._LATEST_VERSION):
#     TYPE_CHECKER = validators._LATEST_VERSION.TYPE_CHECKER.redefine('ref', is_ref)

# # CustomValidator.META_SCHEMA['type'] += ['record', 'ref', 'token']
# import json; print(json.dumps(CustomValidator.META_SCHEMA, indent=2))

# CustomValidator._META_SCHEMAS\
#     ['https://json-schema.org/draft/2020-12/meta/validation']\
#     ['$defs']['simpleTypes'].append('ref')


def fail(msg, exc=NotImplementedError):
    """Logs an error and raises an exception with the given message."""
    logger.error(msg)
    raise exc(msg)


class Base():
    """Base class for both XRPC client and server."""

    _defs = None  # dict mapping id to lexicon def
    _validate = True

    def __init__(self, lexicons, validate=True):
        """Constructor.

        Args:
          lexicons: sequence of dict lexicons
          validate: boolean, whether to validate schemas, parameters, and input
            and output bodies

        Raises:
          :class:`jsonschema.SchemaError`
            if any schema is invalid
        """
        self._validate = validate
        self._defs = {}

        for i, lexicon in enumerate(copy.deepcopy(lexicons)):
            nsid = lexicon.get('id')
            assert nsid, f'Lexicon {i} missing id field'
            # logger.debug(f'Loading lexicon {nsid}')

            for name, defn in lexicon.get('defs', {}).items():
                id = nsid if name == 'main' else f'{nsid}#{name}'
                self._defs[id] = defn

                type = defn['type']
                assert type in LEXICON_TYPES | PARAMETER_TYPES, \
                    f'Bad type for lexicon {id}: {type}'

                if type in METHOD_TYPES:
                    # preprocess parameters properties into full JSON Schema
                    params = defn.get('parameters', {})
                    defn['parameters'] = {
                        'schema': {
                            'type': 'object',
                            'required': params.get('required', []),
                            'properties': params.get('properties', {}),
                        },
                    }

                    if validate:
                        # validate schemas
                        for field in ('input', 'output', 'message',
                                      'parameters', 'record'):
                            # logger.debug(f'Validating {id} {field} schema')
                            schema = defn.get(field, {}).get('schema')
                            # if schema:
                                # TODO: adapt jsonschema to support Lexicon, or drop
                                # validators.validator_for(schema).check_schema(schema)

                self._defs[id] = defn

    def _get_def(self, id):
        """Returns the given lexicon def.

        Raises:
          NotImplementedError
            if no def exists for the given id
        """
        lexicon = self._defs.get(id)
        if not lexicon:
            fail(f'{id} not found')

        return lexicon

    def _maybe_validate(self, nsid, type, obj):
        """If configured to do so, validates a JSON object against a given schema.

        Does nothing if this object was initialized with validate=False.

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
        if not self._validate:
            return

        assert type in ('input', 'output', 'parameters', 'record'), type

        base = self._get_def(nsid).get(type, {})
        encoding = base.get('encoding')
        if encoding and encoding != 'application/json':
            # binary or other non-JSON data, pass through
            return

        schema = base.get('schema')
        if not schema:
            if not obj:
                return
            fail(f'{nsid} has no schema for {type}')

        logger.debug(f'Validating {nsid} {type}')
        try:
            # TODO: adapt jsonschema to support Lexicon, or drop
            # jsonschema.validate(obj, schema)
            pass
        except jsonschema.ValidationError as e:
            e.message = f'Error validating {nsid} {type}: {e.message}'
            raise

    def encode_params(self, params):
        """Encodes decoded parameter values.

        Based on https://atproto.com/specs/xrpc#path

        Args:
          params: dict mapping str names to boolean, number, str, or list values

        Returns: bytes, URL-encoded query parameter string
        """
        return urllib.parse.urlencode({
            name: ('true' if val is True
                   else 'false' if val is False
                   else val)
            for name, val in params.items()
        }, doseq=True)

    def decode_params(self, method_nsid, params):
        """Decodes encoded parameter values.

        Based on https://atproto.com/specs/xrpc#path

        Args:
          method_nsid: str
          params: sequence of (str name, str encoded value) tuples

        Returns:
          dict mapping str names to decoded boolean, number, str, and array values

        Raises:
          ValueError
            if a parameter value can't be decoded
          NotImplementedError
            if no method lexicon is registered for the given NSID
        """
        lexicon = self._get_def(method_nsid)
        params_schema = lexicon.get('parameters', {})\
                               .get('schema', {})\
                               .get('properties', {})

        decoded = {}
        for name, val in params:
            type = params_schema.get(name, {}).get('type') or 'string'
            assert type in PARAMETER_TYPES, type

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
                elif type in ('int', 'integer'):
                    decoded[name] = int(val)
            except ValueError as e:
                e.args = [f'{e.args[0]} for {type} parameter {name}']
                raise e

            if type == 'string':
                decoded[name] = val

            if type == 'array':
                decoded.setdefault(name, []).append(val)

        return decoded
