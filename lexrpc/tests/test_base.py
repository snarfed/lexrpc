"""Unit tests for base.py."""
from unittest import TestCase

from jsonschema import SchemaError, ValidationError

from .lexicons import LEXICONS
from ..base import XrpcBase


class BaseTest(TestCase):

    def setUp(self):
        super().setUp()
        self.base = XrpcBase(LEXICONS)

    def test_get_lexicon(self):
        self.assertEqual(LEXICONS[0], self.base._get_lexicon('io.example.procedure'))
        self.assertEqual(LEXICONS[1], self.base._get_lexicon('io.example.query'))
        self.assertEqual(LEXICONS[2], self.base._get_lexicon(
            'io.example.no-params-input-output'))

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
