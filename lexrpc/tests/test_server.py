"""Unit tests for server.py."""
from unittest import TestCase

from jsonschema import ValidationError

from .lexicons import LEXICONS
from ..server import Server


# test server and methods
server = Server(LEXICONS)

@server.method('io.example.query')
def query(input, **params):
    return {
        'foo': params.get('x'),
        'bar': ServerTest.QUERY_BAR,
    }


@server.method('io.example.procedure')
def procedure(input, **params):
    return input


@server.method('io.example.noParamsInputOutput')
def no_params_input_output(input, **params):
    pass


@server.method('io.example.dashed-name')
def dashed_name_fn(input, **params):
    pass


@server.method('io.example.params')
def params(input, **params):
    pass


@server.method('io.example.defs')
def defs(input, **params):
    return {'out': 'bar'}


@server.method('io.example.error')
def error(input, **params):
    pass


class ServerTest(TestCase):
    maxDiff = None
    QUERY_BAR = 5

    def setUp(self):
        super().setUp()
        ServerTest.QUERY_BAR = 5

    def test_procedure(self):
        input = {
            'foo': 'xyz',
            'bar': 3,
        }
        output = server.call('io.example.procedure', input)
        self.assertEqual(input, output)

    def test_query(self):
        output = server.call('io.example.query', {}, x='y')
        self.assertEqual({'foo': 'y', 'bar': 5}, output)

    def test_no_params_input_output(self):
        self.assertIsNone(server.call('io.example.noParamsInputOutput', {}))

    def test_dashed_name(self):
        self.assertIsNone(server.call('io.example.dashed-name', {}))

    def test_defs(self):
        output = server.call('io.example.defs', {'in': 'foo'})
        self.assertEqual({'out': 'bar'}, output)

    def test_procedure_missing_input(self):
        with self.assertRaises(ValidationError):
            server.call('io.example.procedure', {})

        with self.assertRaises(ValidationError):
            server.call('io.example.procedure', {'bar': 3})

    def test_procedure_bad_input(self):
        with self.assertRaises(ValidationError):
            server.call('io.example.procedure', {'foo': 2, 'bar': 3})

    def test_query_bad_output(self):
        global BAR
        self.QUERY_BAR = 'not an integer'

        with self.assertRaises(ValidationError):
            server.call('io.example.query', {}, foo='abc')

    def test_missing_params(self):
        with self.assertRaises(ValidationError):
            server.call('io.example.params', {})

        with self.assertRaises(ValidationError):
            server.call('io.example.params', {}, foo='a')

    def test_invalid_params(self):
        with self.assertRaises(ValidationError):
            server.call('io.example.params', {}, bar='c')

    def test_unknown_methods(self):
        with self.assertRaises(NotImplementedError):
            server.call('io.unknown', {})

    def test_undefined_method(self):
        with self.assertRaises(NotImplementedError):
            server.call('not.defined', {})

    def test_redefined_method_error(self):
        with self.assertRaises(AssertionError):
            @server.method('io.example.query')
            def other(input, **params):
                pass

    def test_validate_false(self):
        server = Server(LEXICONS, validate=False)

        @server.method('io.example.procedure')
        def procedure(input, **params):
            return input

        input = {'funky': 'chicken'}
        output = server.call('io.example.procedure', input)
        self.assertEqual(input, output)
