"""Base code shared by both server and client."""
import copy
from datetime import datetime, timezone
from importlib.resources import files
import json
import logging
import re
import string
from urllib.parse import urlencode, urljoin, urlparse

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
    'null': type(None),
    'blob': dict,
    'boolean': bool,
    'cid-link': CID,
    'integer': int,
    'string': str,
    'bytes': bytes,
    'array': list,
    'object': dict,
    # these could be tokens
    # 'ref': dict,
    # 'union': dict,
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

# duplicated in bridgy-fed/common.py
DOMAIN_PATTERN = r'([a-z0-9][a-z0-9-]{0,62}(?<!-)\.){1,}[a-z][a-z0-9-]*(?<!-)'
DOMAIN_RE = re.compile(f'^{DOMAIN_PATTERN}$')

# https://atproto.com/specs/nsid
NSID_SEGMENT = '[a-zA-Z0-9-]+'
NSID_SEGMENT_RE = re.compile(f'^{NSID_SEGMENT}$')
NSID_PATTERN = r'(?![0-9])((?!-)[a-z0-9-]{1,63}(?<!-)\.){2,}[a-zA-Z][a-zA-Z0-9]{0,62}'
NSID_RE = re.compile(f'^{NSID_PATTERN}$')

# https://atproto.com/specs/lexicon#string-formats
# https://datatracker.ietf.org/doc/html/rfc5646#section-2.1
LANG_RE = re.compile(r'^(i|[a-z]{2,3})(-[A-Za-z0-9-]+)?$')

# https://atproto.com/specs/record-key
RKEY_RE = re.compile(r'^[A-Za-z0-9._:~-]{1,512}$')

# https://atproto.com/specs/record-key#record-key-type-tid
BASE32_CHARS = string.ascii_lowercase + "234567"
TID_RE = re.compile(rf'^[{BASE32_CHARS}]{{13}}$')

CID_RE = re.compile(r'^[A-Za-z0-9+]{8,}$')

# https://www.w3.org/TR/did-core/#did-syntax
DID_PATTERN = r'did:[a-z]+:[A-Za-z0-9._%:-]{1,2048}(?<!:)'
DID_RE = re.compile(f'^{DID_PATTERN}$')

# https://atproto.com/specs/at-uri-scheme
# NOTE: duplicated in granary.bluesky!
# also see arroba.util.parse_at_uri
_CHARS = 'a-zA-Z0-9-.'
AT_URI_RE = re.compile(rf"""
    ^at://
     (?P<repo>{DID_PATTERN}|{DOMAIN_PATTERN})
      (?:/(?P<collection>{NSID_PATTERN})
       (?:/(?P<rkey>[{_CHARS}:~_]+))?)?
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
            if not nsid or not isinstance(nsid, str):
                raise ValidationError(f'Lexicon {i} missing or invalid id field')
            elif lexicon.get('lexicon') != 1:
                raise ValidationError(f'{nsid} lexicon field should be 1')
            # logger.debug(f'Loading lexicon {nsid}')

            for name, defn in lexicon.get('defs', {}).items():
                id = nsid if name == 'main' else f'{nsid}#{name}'
                self.defs[id] = defn

                type = defn['type']
                if type not in LEXICON_TYPES | PARAMETER_TYPES:
                    raise ValidationError(f'Bad type for lexicon {id}: {type}')

                if validate:
                    for field in ('input', 'output', 'message', 'parameters',
                                  'record'):
                        if schema := defn.get('field'):
                            if not isinstance(schema, dict):
                                raise ValidationError(f'{nsid} {field} is invalid')
                            elif not isinstance(schema.get('properties'), dict):
                                raise ValidationError(f'{nsid} {field} properties is invalid')

                self.defs[id] = defn

        self.defs['blob'] = BLOB_DEF

        if not self.defs:
            logger.error('No lexicons loaded!')

    def _get_def(self, id):
        """Returns the given lexicon def.

        Raises:
          NotImplementedError: if no def exists for the given id
        """
        # TODO: bring back once the Bluesky appview validates this too
        # https://github.com/bluesky-social/atproto/discussions/1968#discussioncomment-11195092
        # if id.endswith('#main'):
        #     # https://atproto.com/specs/lexicon#:~:text=main%20suffix
        #     raise ValidationError(f'#main suffix not allowed on $type: {id}')

        lexicon = self.defs.get(id)
        if not lexicon:
            fail(f'{id} not found')

        return lexicon

    def validate(self, nsid, type, obj):
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
        if not self._validate and not self._truncate:
            return obj

        assert type in ('input', 'output', 'message', 'parameters', 'record'), type

        base = self._get_def(nsid).get(type, {})
        encoding = base.get('encoding')
        if encoding and encoding != 'application/json':
            # binary or other non-JSON data, pass through
            return obj

        schema = base
        if type in ('input', 'output', 'message'):
            schema = base.get('schema')

        if not schema:
            return obj
            # ...or should we fail if obj is non-null? maybe not, since then
            # we'd fail if a query with no params gets requested with any query
            # params at all, eg utm_* tracking params

        self._validate_schema(name=type, val=obj, type_=nsid, lexicon=nsid,
                              schema=schema)

        return obj

    def _validate_schema(self, *, name, val, type_, lexicon, schema):
        """Validates an ATProto value against a lexicon schema.

        Returns ``None`` if the value validates, otherwise raises an exception.

        https://atproto.com/specs/lexicon

        Args:
          name (str): field name
          val: value
          type_ (str): name of type, eg ``integer`` or ``app.bsky.feed.post#replyRef``
          lexicon (str): fully qualified lexicon name that contains this schema,
            eg ``app.bsky.feed.post`` or ``app.bsky.feed.post#replyRef``
          schema (dict): schema to validate against if this is a compound
            object and not a primitive

        Raises:
          ValidationError: if the value is invalid
        """
        # logger.debug(f'@ {name} {type_} {lexicon} {str(val)[:100]} {str(schema)[:100]}')

        def get_schema(lex_name):
            """Returns (fully qualified lexicon name, lexicon) tuple."""
            schema_name = urljoin(lexicon, lex_name)
            schema = self._get_def(schema_name)
            if schema.get('type') == 'record':
                schema = schema.get('record')
            if not schema:
                fail(f'lexicon {schema_name} not found')
            return schema_name, schema

        def fail(msg):
            if self._validate:
                val_str = repr(val)
                if len(val_str) > 50:
                    val_str = val_str[:50] + '…'
                prefix = f'in {lexicon}, ' if lexicon != type_ else ''
                raise ValidationError(
                    f'{prefix}{type_} {name} with value `{val_str}`: {msg}')

        if const := schema.get('const'):
            if val != const:
                fail(f'is not const value {const}')

        if enums := schema.get('enum'):
            if val not in enums:
                fail('is not one of enum values')

        if type_ == 'unknown':
            if isinstance(val, dict) and val.get('$type'):
                lexicon, schema = get_schema(val['$type'])
                # pass through and validate with this schema
            else:
                return

        if expected := FIELD_TYPES.get(type_):
            if type(val) != expected:
                fail(f'has unexpected type {type(val).__name__}')

        if type_ in ('array', 'bytes', 'string'):
            min_length = schema.get('minLength')
            max_length = schema.get('maxLength')
            length = len(val.encode('utf-8') if type_ == 'string' else val)
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

        if minimum := schema.get('minimum'):
            if val < minimum:
                fail(f'is lower than minimum {minimum}')
        if maximum := schema.get('maximum'):
            if val > maximum:
                fail(f'is higher than maximum {maximum}')

        if schema and schema.get('type') == 'token':
            if val != lexicon:
                fail(f'is not token {lexicon}')
            elif val not in self.defs:
                fail(f'not found')

        if type_ == 'ref':
            ref = schema['ref']
            if isinstance(val, str) and val != ref:
                fail(f'is not {ref}')
            elif not isinstance(val, dict):
                fail('is not object')
            lexicon, schema = get_schema(ref)

        if type_ == 'union':
            if isinstance(val, dict):
                inner_type = val.get('$type')
                if not inner_type:
                    fail('missing $type')
            elif isinstance(val, str):
                inner_type = val
            else:
                fail("is invalid")

            if schema.get('closed'):
                refs = [urljoin(lexicon, ref) for ref in schema['refs']]
                if inner_type not in refs:
                    fail(f"{inner_type} isn't one of {refs}")

            try:
                lexicon, schema = get_schema(inner_type)
            except NotImplementedError:
                # https://github.com/bluesky-social/atproto/discussions/2940
                # https://github.com/snarfed/lexrpc/issues/16
                logger.debug(f'Skipping unknown type {inner_type}')
                return

        # TODO: maybe bring back once we figure out why the AppView isn't
        # currently enforcing these:
        # https://github.com/snarfed/bridgy-fed/issues/1348#issuecomment-2381056468
        # if type_ == 'blob':
        #     if max_size := schema.get('maxSize'):
        #         # old-style blobs don't have size
        #         # https://atproto.com/specs/data-model#blob-type
        #         if size := val.get('size'):
        #             if size > max_size:
        #                 fail(f'has size {val["size"]} over maxSize {max_size}')
        #     self.validate_mime_type(val['mimeType'], schema.get('accept'), name=name)

        if type_ == 'array':
            for item in val:
                self._validate_schema(
                    name=name, val=item, type_=schema['items']['type'],
                    lexicon=lexicon, schema=schema['items'])

        props = schema.get('properties', {})
        if props and not isinstance(val, dict):
            fail('should be object')

        required = schema.get('required', [])
        nullable = schema.get('nullable', [])
        for prop_name, prop_schema in props.items():
            if prop_name not in val:
                if prop_name in required:
                    fail(f'missing required property {prop_name}')
                continue

            prop_type = prop_schema['type']
            prop_lexicon = lexicon
            prop_val = val[prop_name]
            if prop_val is None:
                if prop_type != 'null' and prop_name not in nullable:
                    fail(f'property {prop_name} is not nullable')
                continue

            elif self._truncate and (max_graphemes := prop_schema.get('maxGraphemes')):
                if grapheme.length(prop_val) > max_graphemes:
                    prop_val = val[prop_name] = grapheme.slice(
                        prop_val, end=max_graphemes - 1) + '…'

            elif prop_type == 'ref':
                prop_lexicon, prop_schema = get_schema(prop_schema['ref'])
                prop_type = prop_schema['type']

            self._validate_schema(name=prop_name, val=prop_val, type_=prop_type,
                                  lexicon=prop_lexicon, schema=prop_schema)

        # unknown parameters aren't allowed
        if schema.get('type') == 'params':
            if unknown := val.keys() - props.keys():
                fail(f'unknown parameters: {unknown}')

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
                raise ValidationError(f'{val} is invalid for format {format}')

        check(val)

        # TODO: switch to match once we require Python 3.10+
        if format == 'at-identifier':
            check(DID_RE.match(val) or DOMAIN_RE.match(val.lower()))

        elif format == 'at-uri':
            check(len(val) < 8 * 1024)
            check(AT_URI_RE.match(val))
            check('/./' not in val
                  and '/../' not in val
                  and not val.endswith('/.')
                  and not val.endswith('/..'))

        elif format == 'cid':
            # ideally I'd use CID.decode here, but it doesn't support CIDv5,
            # it's too strict about padding, etc.
            check(CID_RE.match(val))

        elif format == 'datetime':
            check('T' in val)

            orig_val = val
            # timezone is required
            val = re.sub(r'([+-][0-9]{2}:[0-9]{2}|Z)$', '', orig_val)
            check(val != orig_val)

            # strip fractional seconds
            val = re.sub(r'\.[0-9]+$', '', val)

            try:
                datetime.fromisoformat(val)
            except ValueError:
                check(False)

        elif format == 'did':
            check(DID_RE.match(val))

        elif format == 'nsid':
            check(len(val) <= 317)
            check(NSID_RE.match(val) and '.' in val)

        elif format in 'handle':
            check(len(val) <= 253)
            check(DOMAIN_RE.match(val.lower()))

        elif format == 'tid':
            check(TID_RE.match(val))
            # high bit, big-endian, can't be 1
            check(not ord(val[0]) & 0x40)

        elif format == 'record-key':
            check(val not in ('.', '..') and RKEY_RE.match(val))

        elif format == 'uri':
            check(len(val) < 8 * 1024)
            check(' ' not in val)
            parsed = urlparse(val)
            check(parsed.scheme
                  and parsed.scheme[0].lower() in string.ascii_lowercase
                  and (parsed.netloc or parsed.path or parsed.query
                       or parsed.fragment))

        elif format == 'language':
            check(LANG_RE.match(val))

        else:
            raise ValidationError(f'unknown format {format}')

    @staticmethod
    def validate_mime_type(mime_type, accept, name=''):
        """Validates that a MIME type matches an accept range.

        For validating blob types. Returns ``None`` if the ``accept`` is empty
        or ``mime_type`` matches, otherwise raises an exception.

        https://atproto.com/specs/lexicon#field-type-definitions

        Args:
          mime_type (str)
          accept (sequence of str): blob ``accept`` field value, list of MIME
            type patterns, eg ``image/jpeg``, ``image/*``, or ``*/*``.
          name: blob field name, only used in exception message

        Raises:
          ValidationError: if ``mime_type`` doesn't match any pattern in ``accept``
        """
        if not accept or '*/*' in accept:
            return

        if not mime_type or (mime_type not in accept
                             and (mime_type.split('/')[0] + '/*') not in accept):
            raise ValidationError(f'blob {name} MIME type {mime_type} not in accept types {accept}')

    def encode_params(self, params):
        """Encodes decoded parameter values.

        Based on https://atproto.com/specs/xrpc#lexicon-http-endpoints

        Args:
          params (dict): maps str names to boolean, number, str, or list values

        Returns:
          bytes: URL-encoded query parameter string
        """
        return urlencode({
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

    @classmethod
    def loggable(cls, val):
        return (
            f'{len(val)} bytes' if isinstance(val, bytes)
            else val[:100] if isinstance(val, str)
            else [cls.loggable(v) for v in val] if isinstance(val, list)
            else {k: cls.loggable(v) for k, v in val.items()} if isinstance(val, dict)
            else val)
