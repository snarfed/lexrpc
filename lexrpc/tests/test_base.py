"""Unit tests for base.py."""
from datetime import datetime
from unittest import skip, TestCase

from .lexicons import LEXICONS
from ..base import Base, ValidationError

# set as the base.now return value in mocks in tests
NOW = datetime(2022, 2, 3)


class BaseTest(TestCase):
    maxDiff = None

    def setUp(self):
        super().setUp()
        self.base = Base(LEXICONS)

    def test_get_def(self):
        for nsid in 'io.example.dashed-name', 'io.example.noParamsInputOutput':
            self.assertEqual({'type': 'procedure'}, self.base._get_def(nsid))

        self.assertEqual({
            'type': 'object',
            'required': ['boolean'],
            'properties': {
                'boolean': {'type': 'boolean'},
            },
        }, self.base._get_def('io.example.kitchenSink#subobject'))

    # TODO
    @skip
    def test_validate_lexicon_schema(self):
        for bad in 'foo bar', {'type': 'foo', 'properties': 3}:
            with self.assertRaises(ValidationError):
                Base([{
                    'lexicon': 1,
                    'id': 'io.example.procedure',
                    'defs': {
                        'main': {
                            'type': 'procedure',
                            'input': {
                                'schema': bad,
                            },
                        },
                    },
                }])

    def test_validate_record_pass(self):
        self.base._maybe_validate('io.example.record', 'record', {
            'baz': 3,
            'biff': {
                'baj': 'foo',
            },
        })

    def test_maybe_validate_truncate(self):
        base = Base(LEXICONS, truncate=True)

        for input, expected in (
            ('short', 'short'),
            ('too many graphemes', 'too many …'),
            # ('🇨🇾🇬🇭 bytes', '🇨🇾…'),  # TODO
        ):
            self.assertEqual(
                {'string': expected},
                base._maybe_validate('com.example.stringLength', 'record',
                                     {'string': input}))

    def test_validate_record_pass_nested_optional_field_missing(self):
        self.base._maybe_validate('io.example.record', 'record', {
            'baz': 3,
            'biff': {
            },
        })

    def test_validate_record_pass_optional_field_missing(self):
        self.base._maybe_validate('io.example.record', 'record', {
            'baz': 3,
        })


    def test_validate_record_fail_integer_field_bad_type(self):
        self.base._validate = True
        with self.assertRaises(ValidationError):
            self.base._maybe_validate('io.example.record', 'record', {
                'baz': 'x',
                'biff': {
                    'baj': 'foo',
                },
            })

    def test_validate_record_fail_object_field_bad_type(self):
        self.base._validate = True
        with self.assertRaises(ValidationError):
            self.base._maybe_validate('io.example.record', 'record', {
                'baz': 3,
                'biff': 4,
            })

    def test_validate_record_fail_missing_required_field(self):
        self.base._validate = True
        with self.assertRaises(ValidationError):
            self.base._maybe_validate('io.example.record', 'record', {
                'biff': {
                    'baj': 'foo',
                },
            })

    def test_validate_record_kitchen_sinkpass(self):
        self.base._maybe_validate('io.example.kitchenSink', 'record', {
            # TODO
            # 'object': {
            #     'type': 'ref',
            #     'ref': '#object'
            # },
            'array': ['x', 'y'],
            'boolean': True,
            'integer': 3,
            'string': 'z',
        })
