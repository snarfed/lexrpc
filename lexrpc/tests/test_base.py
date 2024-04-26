"""Unit tests for base.py."""
from unittest import skip, TestCase

from jsonschema import SchemaError, ValidationError

from .lexicons import LEXICONS
from ..base import Base


class BaseTest(TestCase):
    maxDiff = None

    def setUp(self):
        super().setUp()
        self.base = Base(LEXICONS)

    def test_get_def(self):
        expected = {
            'type': 'procedure',
            'parameters': {
                'schema': {
                    'type': 'object',
                    'properties': {},
                    'required': [],
                },
            },
        }
        for nsid in 'io.example.dashed-name', 'io.example.noParamsInputOutput':
            self.assertEqual(expected, self.base._get_def(nsid))

        # self.assertEqual({
        #     'type': 'object',
        #     'required': ['boolean'],
        #     'properties': {
        #         'boolean': {'type': 'boolean'},
        #     },
        # }, self.base._get_def('com.example.kitchenSink#subobject'))

    # TODO
    @skip
    def test_validate_lexicon_schema(self):
        for bad in 'foo bar', {'type': 'foo', 'properties': 3}:
            with self.assertRaises(SchemaError):
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

    def test_preprocess_params(self):
        self.assertEqual({
            'schema': {
                'type': 'object',
                'required': ['bar'],
                'properties': {
                    'foo': { 'type': 'string' },
                    'bar': { 'type': 'number' },
                },
            },
        }, self.base.defs['io.example.params']['parameters'])

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
