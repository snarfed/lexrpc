"""Unit tests for base.py."""
from unittest import TestCase

from jsonschema import SchemaError, ValidationError

from .lexicons import LEXICONS
from ..base import Base


class BaseTest(TestCase):
    maxDiff = None

    def setUp(self):
        super().setUp()
        self.base = Base(LEXICONS)

    def test_get_lexicon(self):
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
            self.assertEqual(expected, self.base._get_lexicon(nsid))

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
        }, self.base._lexicons['io.example.params']['parameters'])
