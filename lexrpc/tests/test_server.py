"""Unit tests for server.py."""
from unittest import TestCase
from unittest.mock import patch

from ..base import ValidationError
from .lexicons import LEXICONS
from ..server import Server


# test server and methods
server = Server(lexicons=LEXICONS)

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


@server.method('io.exa-mple.dashedName')
def dashed_name_fn(input, **params):
    pass


@server.method('io.example.params')
def params(input, **params):
    pass


@server.method('io.example.array')
def array(input, foo=None):
    assert isinstance(foo, list)
    return {'items': foo + ['z']}


@server.method('io.example.defs')
def defs(input, **params):
    return {'out': 'bar'}


@server.method('io.example.encodings')
def encodings(input, **params):
    assert isinstance(input, bytes)
    val = int.from_bytes(input, 'big')
    val += 1
    return val.to_bytes((val.bit_length() + 7) // 8, 'big')


@server.method('io.example.subscribe')
def subscribe(start=None, end=None):
    for num in range(start, end):
        yield {'hea': 'der'}, {'num': num}


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
        self.assertIsNone(server.call('io.exa-mple.dashedName', {}))

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

    def test_array(self):
        self.assertEqual({'items': ['a', 'b', 'z']},
                         server.call('io.example.array', {}, foo=['a', 'b']))

    def test_subscription(self):
        gen = server.call('io.example.subscribe', start=3, end=6)
        self.assertEqual([
            ({'hea': 'der'}, {'num': 3}),
            ({'hea': 'der'}, {'num': 4}),
            ({'hea': 'der'}, {'num': 5}),
        ], list(gen))

    def test_subscription_params_validate_fails(self):
        with self.assertRaises(ValidationError):
            server.call('io.example.subscribe', start='not integer')

    def test_subscription_output_validate_fails(self):
        def subscribe(start=None, end=None):
            yield {'hea': 'der'}, {'num': 3}
            yield {'hea': 'der'}, {'num': 'not integer'}

        with patch.dict(server._methods, values={'io.example.subscribe': subscribe}):
            gen = server.call('io.example.subscribe', start=3, end=6)
            self.assertEqual(({'hea': 'der'}, {'num': 3}), next(gen))

            with self.assertRaises(ValidationError):
                next(gen)

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
        server = Server(lexicons=LEXICONS, validate=False)

        @server.method('io.example.procedure')
        def procedure(input, **params):
            return input

        input = {'funky': 'chicken'}
        output = server.call('io.example.procedure', input)
        self.assertEqual(input, output)

    def test_byte_encodings(self):
        val = 234892348203948
        val_bytes = val.to_bytes((val.bit_length() + 7) // 8, 'big')
        got = server.call('io.example.encodings', val_bytes)
        self.assertTrue(isinstance(got, bytes))
        self.assertEqual(val + 1, int.from_bytes(got, 'big'))

    def test_decorator_call(self):
        output = query({}, x='y')
        self.assertEqual({'foo': 'y', 'bar': 5}, output)

    def test_decorator_bad_method_name(self):
        with self.assertRaises(AssertionError):
            @server.method('not an NSID')
            def foo(input, **params):
                pass

    def test_decorator_method_name_already_registered(self):
        with self.assertRaises(AssertionError):
            @server.method('io.example.query')
            def query(input, **params):
                pass

    def test_register(self):
        del server._methods['io.example.query']

        server.register('io.example.query', query)
        output = server.call('io.example.query', {}, x='y')
        self.assertEqual({'foo': 'y', 'bar': 5}, output)

    def test_bundled_lexicons(self):
        server = Server()

        output = {'did': 'did:plc:foo', 'handle': 'bar.com'}

        @server.method('com.atproto.server.getSession')
        def get_session(input):
            return output

        self.assertEqual(output, server.call('com.atproto.server.getSession', {}))

