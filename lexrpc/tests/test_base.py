"""Unit tests for base.py."""
from unittest import TestCase

from jsonschema import SchemaError, ValidationError

from .lexicons import LEXICONS
from ..base import XrpcBase


class BaseTest(TestCase):
    maxDiff = None

    def setUp(self):
        super().setUp()
        self.base = XrpcBase(LEXICONS)

    def test_get_lexicon(self):
        self.assertEqual('io.example.procedure',
                         self.base._get_lexicon('io.example.procedure')['id'])
        self.assertEqual('io.example.query',
                         self.base._get_lexicon('io.example.query')['id'])
        self.assertEqual('io.example.no-params-input-output',
                         self.base._get_lexicon('io.example.no-params-input-output')['id'])

    def test_validate_lexicon_schema(self):
        with self.assertRaises(SchemaError):
            XrpcBase([{
                'lexicon': 1,
                'id': 'io.example.procedure',
                'type': 'procedure',
                'input': {
                    'schema': 'foo bar',
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
