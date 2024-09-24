"""Base code shared by both server and client."""
import copy
from datetime import datetime, timezone
from importlib.resources import files
import json
import logging
import re
import string
from types import NoneType
import urllib.parse

import grapheme
from multiformats import CID

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
# https://atproto.com/specs/lexicon#overview-of-types
FIELD_TYPES = {
    'null': NoneType,
    'blob': dict,
    'boolean': bool,
    'cid-link': CID,
    'integer': int,
    'string': str,
    'bytes': bytes,
    'array': list,
    'object': dict,
}

# https://atproto.com/specs/data-model#blob-type
BLOB_DEF = {
    'type': 'record',
    'record': {
        'required': ['ref', 'mimeType', 'size'],
        'properties': {
            'ref': {
                'type': 'ref',
            },
            'mimeType': {
                'type': 'string',
                'minLength': 1,
            },
            'size': {
                'type': 'integer',
                'minimum': 1,
            },
        },
    },
}

# https://atproto.com/specs/nsid
NSID_SEGMENT = '[a-zA-Z0-9-]+'
NSID_SEGMENT_RE = re.compile(f'^{NSID_SEGMENT}$')
NSID_RE = re.compile(rf'^{NSID_SEGMENT}(\.{NSID_SEGMENT})*$')

# https://atproto.com/specs/lexicon#string-formats
# https://datatracker.ietf.org/doc/html/rfc5646#section-2.1
LANG_RE = re.compile(r'^[A-Za-z]{2,3}(-[A-Za-z0-9-]+)?$')

# https://atproto.com/specs/record-key
RKEY_RE = re.compile(r'^[A-Za-z0-9._:~-]{1,512}$')

# https://atproto.com/specs/record-key#record-key-type-tid
BASE32_CHARS = string.ascii_lowercase + "234567"
TID_RE = re.compile(rf'^[{BASE32_CHARS}]{{13}}$')

CID_BASE32_RE = re.compile(rf'^[{BASE32_CHARS}]+$')

# https://atproto.com/specs/at-uri-scheme
# NOTE: duplicated in granary.bluesky!
# also see arroba.util.parse_at_uri
_CHARS = 'a-zA-Z0-9-.:'
AT_URI_RE = re.compile(rf"""
    ^at://
     (?P<repo>[{_CHARS}]+)
      (?:/(?P<collection>[a-zA-Z0-9-.]+)
       (?:/(?P<rkey>[{_CHARS}]+))?)?
    $""", re.VERBOSE)

# wrapper for datetime.now, lets us mock it out in tests
now = lambda tz=timezone.utc, **kwargs: datetime.now(tz=tz, **kwargs)


class XrpcError(ValueError):
    """A named error in an XRPC call.

    ``name`` is the error, eg ``RepoNotFound`` in ``com.atproto.sync.getRepo``.
    ``message`` is the human-readable string error message.
    """
    def __init__(self, message, name=None, **kwargs):
        super().__init__(message, **kwargs)
        self.name = name
        self.message = message


def load_lexicons(traversable):
    if traversable.is_file():
        lexicons = [json.loads(traversable.read_text())]
    elif traversable.is_dir():
        lexicons = sum((load_lexicons(item) for item in traversable.iterdir()),
                       start=[])

    return lexicons

_bundled_lexicons = load_lexicons(files('lexrpc').joinpath('lexicons'))
logger.info(f'{len(_bundled_lexicons)} lexicons loaded')


def fail(msg, exc=NotImplementedError):
    """Logs an error and raises an exception with the given message."""
    logger.error(msg)
    raise exc(msg)


class ValidationError(ValueError):
    """Raised when an object or XRPC input or output doesn't match its schema."""
    pass


class Base():
    """Base class for both XRPC client and server."""

    defs = None  # dict mapping id to lexicon def
    _validate = None
    _truncate = None

    def __init__(self, lexicons=None, validate=True, truncate=False):
        """Constructor.

        Args:
          lexicons (sequence of dict): lexicons, optional. If not provided,
            defaults to the official, built in ``com.atproto`` and ``app.bsky``
            lexicons.
          validate (bool): whether to validate schemas, parameters, and input
            and output bodies
          truncate (bool): whether to truncate string values that are longer
            than their ``maxGraphemes`` or ``maxLength`` in their lexicon

        Raises:
          ValidationError: if any schema is invalid
        """
        self._validate = validate
        self._truncate = truncate
        self.defs = {}

        if lexicons is None:
            lexicons = _bundled_lexicons

        for i, lexicon in enumerate(copy.deepcopy(lexicons)):
            nsid = lexicon.get('id')
            if not nsid:
                raise ValidationError(f'Lexicon {i} missing id field')
            # logger.debug(f'Loading lexicon {nsid}')

            for name, defn in lexicon.get('defs', {}).items():
                id = nsid if name == 'main' else f'{nsid}#{name}'
                self.defs[id] = defn

                type = defn['type']
                if type not in LEXICON_TYPES | PARAMETER_TYPES:
                    raise ValidationError(f'Bad type for lexicon {id}: {type}')

                for field in ('input', 'output', 'message',
                              'parameters', 'record'):
                    if validate:
                        # logger.debug(f'Validating {id} {field} schema')
                        # TODO
                        pass

                # TODO: fully qualify #... references? or are we already doing that?

                self.defs[id] = defn

        self.defs['blob'] = BLOB_DEF

        if not self.defs:
            logger.error('No lexicons loaded!')

    def _get_def(self, id):
        """Returns the given lexicon def.

        Raises:
          NotImplementedError: if no def exists for the given id
        """
        lexicon = self.defs.get(id)
        if not lexicon:
            fail(f'{id} not found')

        return lexicon

    def maybe_validate(self, nsid, type, obj):
        """If configured to do so, validates a ATProto value against its lexicon.

        Returns ``None`` if the object validates, otherwise raises an exception.

        Does nothing if this object was initialized with ``validate=False``.

        Args:
          nsid (str): method NSID
          type (str): ``input``, ``output``, ``parameters``, or ``record``
          obj (dict): JSON object

        Returns:
          dict: obj, either unchanged, or possible a modified copy if
            ``truncate`` is enabled and a string value was too long

        Raises:
          NotImplementedError: if no lexicon exists for the given NSID, or the
            lexicon does not define a schema for the given type
          ValidationError: if the object is invalid
        """
        assert type in ('input', 'output', 'message', 'parameters', 'record'), type

        base = self._get_def(nsid).get(type, {})
        encoding = base.get('encoding')
        if encoding and encoding != 'application/json':
            # binary or other non-JSON data, pass through
            return obj

        schema = base
        if type != 'record':
            schema = base.get('schema')

        if not schema:
            return
            # ...or should we fail if obj is non-null? maybe not, since then
            # we'd fail if a query with no params gets requested with any query
            # params at all, eg utm_* tracking params

        if self._truncate:
            for name, config in schema.get('properties', {}).items():
                # TODO: recurse into reference, union, etc properties
                if max_graphemes := config.get('maxGraphemes'):
                    val = obj.get(name)
                    if val and grapheme.length(val) > max_graphemes:
                        obj = {
                            **obj,
                            name: grapheme.slice(val, end=max_graphemes - 1) + '…',
                        }

        if self._validate:
            self._validate_value(obj, schema)

        return obj

    def _validate_value(self, obj, lexicon):
        """Validates an ATProto object against a lexicon.

        Returns ``None`` if the object validates, otherwise raises an exception.

        https://atproto.com/specs/lexicon

        Args:
          obj (dict)
          lexicon (dict): should have at least ``properties`` key

        Raises:
          ValidationError: if the object is invalid
        """
        assert lexicon
        if lexicon.get('type') == 'token':
            if not isinstance(obj, str):
                raise ValidationError(f'got value {obj} for type token')
            # TODO: anything else to do here?
            return

        assert isinstance(obj, dict), obj

        for name, schema in lexicon.get('properties', {}).items():
            if name not in obj:
                if name in lexicon.get('required', []):
                    raise ValidationError(f'missing required property {name}')
                continue

            def trunc(val):
                val_str = repr(val)
                return val_str if len(val_str) <= 50 else val_str[:50] + '…'

            def fail(msg):
                raise ValidationError(f'{type_} property {name} value {trunc(val)} {msg}')

            type_ = schema['type']
            val = obj[name]
            if val is None:
                if type_ != 'null' and name not in lexicon.get('nullable', []):
                    fail('is not nullable')
                continue

            if type_ == 'unknown':
                continue

            if type_ == 'token':
                if val not in self.defs:
                    fail(f'not found')

            if type_ in ('blob', 'object', 'ref', 'union'):
                if type_ == 'blob':
                    max_size = schema.get('maxSize')
                    accept = schema.get('accept')
                    schema = BLOB_DEF
                if type_ == 'ref':
                    ref = schema['ref']
                    schema = self._get_def(ref)
                    if schema.get('type') == 'token' and val != ref:
                        fail('is not token value')
                elif type_ == 'union':
                    refs = schema['refs']
                    if (not isinstance(val, (str, dict))
                            or isinstance(val, str) and val not in refs):
                        fail("is invalid")
                    inner_type = (val if isinstance(val, str)  # token
                                  else val.get('$type'))
                    if not inner_type:
                        fail('missing $type')
                    schema = self._get_def(inner_type)

                if not isinstance(val, dict) and schema.get('type') != 'token':
                    fail('is invalid')

                self._validate_value(val, schema)

                if type_ == 'blob':
                    if max_size and val['size'] > max_size:
                        fail(f'has size {val["size"]} over maxSize {max_size}')

                    mime = val['mimeType']
                    if (accept and mime not in accept and '*/*' not in accept
                            and (mime.split('/')[0] + '/*') not in accept):
                        fail(f'has unsupported MIME type {mime}')

                continue

            # TODO: datetime
            # TODO: token
            if type(val) is not FIELD_TYPES[type_]:
                fail(f'has unexpected type {type(val)}')

            if minimum := schema.get('minimum'):
                if val < minimum:
                    fail(f'is less than minimum {minimum}')
            if maximum := schema.get('maximum'):
                if val > maximum:
                    fail(f'is longer than maximum {maximum}')

            if type_ in ('array', 'bytes', 'string'):
                min_length = schema.get('minLength')
                max_length = schema.get('maxLength')
                length = len(val.encode('utf-8')) if type_ == 'string' else len(val)
                if max_length and length > max_length:
                    fail(f'is longer ({length}) than maxLength {max_length}')
                elif min_length and length < min_length:
                    fail(f'is shorter ({length}) than minLength {min_length}')

            if type_ == 'string':
                if format := schema.get('format'):
                    try:
                        self._validate_string_format(val, format)
                    except ValidationError as e:
                        fail(e.args[0])

                min_graphemes = schema.get('minGraphemes')
                max_graphemes = schema.get('maxGraphemes')
                if min_graphemes or max_graphemes:
                    length = grapheme.length(val)
                    if min_graphemes and length < min_graphemes:
                        fail(f'is shorter than minGraphemes {min_graphemes}')
                    if max_graphemes and length > max_graphemes:
                        fail(f'is longer than maxGraphemes {max_graphemes}')

            if type_ == 'array':
                for item in val:
                    if type(item) is not FIELD_TYPES[schema['items']['type']]:
                        fail(f'has element {trunc(item)} with invalid type {type(item)}')

            if enums := schema.get('enum'):
                if val not in enums:
                    fail('is not one of enum values')

            if const := schema.get('const'):
                if val != const:
                    fail(f'is not const value {const}')

        return obj

    def _validate_string_format(self, val, format):
        """Validates an ATProto string value against a format.

        https://atproto.com/specs/lexicon#string-formats

        Args:
          val (str)
          format (str): one of the ATProto string formats

        Raises:
          ValidationError: if the value is invalid for the given format
        """
        def check(condition):
            if not condition:
                raise ValidationError(f'is invalid for format {format}')

        check(val)

        # TODO: switch to match once we require Python 3.10+
        if format == 'at-identifier':
            check(val.startswith('did:') or (NSID_RE.match(val) and '.' in val))

        elif format == 'at-uri':
            check(AT_URI_RE.match(val))

        elif format == 'cid':
            check(CID_BASE32_RE.match(val))

        elif format == 'datetime':
            try:
                datetime.fromisoformat(val.rstrip('Z'))
            except ValueError:
                check(False)

        elif format == 'did':
            check(val.startswith('did:'))

        elif format in ('handle', 'nsid'):
            check(NSID_RE.match(val) and '.' in val)

        elif format == 'tid':
            check(TID_RE.match(val))

        elif format == 'record-key':
            check(val not in ('.', '..') and RKEY_RE.match(val))

        elif format == 'uri':
            parsed = urllib.parse.urlparse(val)
            check(parsed.scheme and parsed.netloc)

        elif format == 'language':
            check(LANG_RE.match(val))

        else:
            raise ValidationError(f'unknown format {format}')

    def encode_params(self, params):
        """Encodes decoded parameter values.

        Based on https://atproto.com/specs/xrpc#lexicon-http-endpoints

        Args:
          params (dict): maps str names to boolean, number, str, or list values

        Returns:
          bytes: URL-encoded query parameter string
        """
        return urllib.parse.urlencode({
            name: ('true' if val is True
                   else 'false' if val is False
                   else val)
            for name, val in params.items()
        }, doseq=True)

    def decode_params(self, method_nsid, params):
        """Decodes encoded parameter values.

        Based on https://atproto.com/specs/xrpc#lexicon-http-endpoints

        Args:
          method_nsid (str):
          params (sequence of (str, str) tuple): name/value mappings

        Returns:
          dict: maps str names to decoded boolean, number, str, and array values

        Raises:
          ValueError: if a parameter value can't be decoded
          NotImplementedError: if no method lexicon is registered for the given NSID
        """
        lexicon = self._get_def(method_nsid)
        params_schema = lexicon.get('parameters', {}).get('properties', {})

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
