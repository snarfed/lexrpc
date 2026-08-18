"""Property-based tests for base.py, using hypothesis.

https://hypothesis.readthedocs.io/
"""
import copy
from string import ascii_letters
from unittest import TestCase
from urllib.parse import parse_qsl

import grapheme
from hypothesis import given, strategies as st

from ...base import Base, ValidationError
from ..lexicons import LEXICONS


SCHEMA_TYPES = st.sampled_from(('input', 'output', 'message', 'parameters', 'record'))

# the bundled com.atproto and app.bsky lexicons, for broad coverage of refs,
# unions, tokens, string formats, etc
BUNDLED = Base()
NSIDS = st.sampled_from(sorted(BUNDLED.defs.keys()))

# every property name in the bundled lexicons. objects with arbitrary keys
# almost never reach property validation, so generate realistic names instead.
PROP_NAMES = set()
_defs = list(BUNDLED.defs.values())
while _defs:
    _def = _defs.pop()
    if isinstance(_def, dict):
        if isinstance(_props := _def.get('properties'), dict):
            PROP_NAMES |= _props.keys()
        _defs.extend(_def.values())
    elif isinstance(_def, list):
        _defs.extend(_def)

# arbitrary JSON documents, ie anything a client could send us. NSIDs are mixed
# in as leaves since they're what $type, refs, unions, and tokens hold. no
# floats; they're not in the ATProto data model.
KEYS = st.sampled_from(sorted(PROP_NAMES) + ['$type']) | st.text()
JSON = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text() | NSIDS,
    lambda children: st.lists(children) | st.dictionaries(KEYS, children),
    max_leaves=10)

# method NSIDs in the bundled lexicons that take parameters
PARAM_NSIDS = sorted(
    nsid for nsid, defn in BUNDLED.defs.items()
    if isinstance(defn, dict) and defn.get('parameters', {}).get('properties'))

# values a client could put in a query string. integers and the two boolean
# literals are mixed in so that those decode branches get exercised.
PARAM_VALUES = (st.text() | st.integers().map(str)
                | st.booleans().map(lambda b: str(b).lower()))

# empty strings and lists don't survive urlencode/parse_qsl: parse_qsl drops
# blank values, and an empty list encodes to nothing at all
TEXT = st.text(min_size=1)


class BaseHypothesisTest(TestCase):
    maxDiff = None

    @given(st.booleans(), st.booleans(), st.booleans(), NSIDS, SCHEMA_TYPES, JSON)
    def test_validate_only_raises_validation_error(
            self, validate, truncate, require_lexicons, nsid, type, obj):
        base = Base(validate=validate,
                    truncate=truncate,
                    require_lexicons=require_lexicons)
        try:
            base.validate(nsid, type, obj)
        except (ValidationError, NotImplementedError):
            pass

    @given(st.booleans(), NSIDS | st.text(), SCHEMA_TYPES, JSON)
    def test_validate_without_require_lexicons_never_raises_not_implemented(
            self, truncate, nsid, type, obj):
        base = Base(validate=True, truncate=truncate, require_lexicons=False)
        try:
            base.validate(nsid, type, obj)
        except ValidationError:
            pass

    @given(NSIDS, SCHEMA_TYPES, JSON)
    def test_validate_disabled_passes_through_unchanged(self, nsid, type, obj):
        orig = copy.deepcopy(obj)
        base = Base(validate=False, truncate=False)
        got = base.validate(nsid, type, obj)
        self.assertIs(obj, got)
        self.assertEqual(orig, obj)

    @given(NSIDS, SCHEMA_TYPES, JSON)
    def test_validate_without_truncate_doesnt_modify(self, nsid, type, obj):
        orig = copy.deepcopy(obj)
        base = Base(validate=True, truncate=False)
        try:
            base.validate(nsid, type, obj)
        except (ValidationError, NotImplementedError):
            pass
        self.assertEqual(orig, obj)

    @given(st.sampled_from((
        'io.example.array',
        'io.example.params',
        'io.example.query',
        'io.example.subscribe',
    )), st.data())
    def test_encode_then_decode_params_round_trips(self, nsid, data):
        params = data.draw(st.fixed_dictionaries({}, optional={
            'io.example.array': {'foo': st.lists(TEXT, min_size=1)},
            'io.example.params': {'foo': TEXT, 'bar': st.integers()},
            'io.example.query': {'x': TEXT, 'z': st.booleans()},
            'io.example.subscribe': {'start': st.integers(), 'end': st.integers()},
        }[nsid]))

        base = Base(LEXICONS)
        encoded = base.encode_params(params)
        self.assertEqual(params, base.decode_params(nsid, parse_qsl(encoded)))

    @given(st.sampled_from(PARAM_NSIDS), st.data())
    def test_decode_params_only_raises_value_error(self, nsid, data):
        # names have to come from the NSID's own parameters, or they almost
        # never match one and everything decodes as a string
        params = data.draw(st.lists(st.tuples(
            st.sampled_from(sorted(BUNDLED.defs[nsid]['parameters']['properties']))
            | st.text(),
            PARAM_VALUES)))
        try:
            Base().decode_params(nsid, params)
        except (ValueError, NotImplementedError):
            pass

    @given(st.text(), st.lists(st.text()))
    def test_truncate(self, string, strings):
        record = {'string': string, 'strings': strings}
        base = Base(LEXICONS, validate=False, truncate=True)
        truncated = base.validate('io.example.stringLength', 'record',
                                  copy.deepcopy(record))

        for orig, got in [(string, truncated['string']),
                          *zip(strings, truncated['strings'])]:
            # io.example.stringLength's maxGraphemes
            self.assertLessEqual(grapheme.length(got), 10)
            self.assertLessEqual(grapheme.length(got), grapheme.length(orig))

        self.assertEqual(truncated, base.validate(
            'io.example.stringLength', 'record', copy.deepcopy(truncated)))

    @given(st.text(ascii_letters), st.lists(st.text(ascii_letters)))
    def test_truncate_output_validates(self, string, strings):
        # ASCII only: truncating counts graphemes, so truncating a multi-byte
        # string can still leave it over io.example.stringLength's maxLength.
        # (That's the maxLength TODO in Base.__init__.)
        truncated = Base(LEXICONS, validate=False, truncate=True).validate(
            'io.example.stringLength', 'record',
            {'string': string, 'strings': strings})
        Base(LEXICONS).validate('io.example.stringLength', 'record', truncated)
