"""Unit tests for server.py.

Based on:
https://github.com/bluesky-social/atproto/blob/main/packages/xrpc-server/tests/bodies.test.ts
"""
from unittest import TestCase

from .schemas import SCHEMAS
from ..server import Server


class ExampleServer(Server):

    def io_example_query(self, params, input):
        return {
            'foo': params.get('foo'),
            'bar': 5,
        }

    def io_example_procedure(self, params, input):
        return input


class ServerTest(TestCase):

    server = ExampleServer(SCHEMAS)
    call = server.call

    def test_procedure(self):
        input = {
            'foo': 'xyz',
            'bar': 3,
        }
        output = self.call('io.example.procedure', {}, input)
        self.assertEqual(input, output)

    def test_query(self):
        output = self.call('io.example.query', {'foo': 'abc'})
        self.assertEqual({'foo': 'abc', 'bar': 5}, output)

    def test_procedure_bad_input(self):
        with self.assertRaises(ValueError):
            self.call('io.example.procedure', {}, {'foo': 2, 'bar': 3})

    def test_unknown_methods(self):
        with self.assertRaises(NotImplementedError):
            self.call('io.unknown', {}, {})

    def test_undefined_methods(self):
        with self.assertRaises(NotImplementedError):
            class Empty(Server):
                pass

            Empty(SCHEMAS)
