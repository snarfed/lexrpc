"""Unit tests for client.py."""
import json
from unittest import TestCase
from unittest.mock import patch

from jsonschema import ValidationError
import requests

from .lexicons import LEXICONS
from .. import Client


def response(body=None, status=200, headers=None):
    resp = requests.Response()
    resp.status_code = 200

    if headers:
        resp.headers.update(headers)

    if body is not None:
        assert isinstance(body, (dict, list))
        body = json.dumps(body, indent=2)
        resp._text = body
        resp._content = body.encode('utf-8')
        resp.headers.setdefault('Content-Type', 'application/json')

    return resp


class ClientTest(TestCase):
    maxDiff = None

    def setUp(self):
        self.client = Client('http://ser.ver', LEXICONS)

    @patch('requests.get')
    def test_call(self, mock_get):
        output = {'foo': 'asdf', 'bar': 3}
        mock_get.return_value = response(output)

        got = self.client.call('io.example.query', {}, x='y')
        self.assertEqual(output, got)

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query',
            params={'x': 'y'},
            json=None,
            headers={'Content-Type': 'application/json'},
        )

    @patch('requests.get')
    def test_query(self, mock_get):
        output = {'foo': 'asdf', 'bar': 3}
        mock_get.return_value = response(output)

        got = self.client.io.example.query({}, x='y')
        self.assertEqual(output, got)

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query',
            params={'x': 'y'},
            json=None,
            headers={'Content-Type': 'application/json'},
        )

    @patch('requests.post')
    def test_procedure(self, mock_post):
        input = {'foo': 'asdf', 'bar': 3}
        output = {'foo': 'baz', 'bar': 4}
        mock_post.return_value = response(output)

        got = self.client.io.example.procedure(input, x='y')
        self.assertEqual(output, got)

        mock_post.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.procedure',
            params={'x': 'y'},
            json=input,
            headers={'Content-Type': 'application/json'},
        )

    @patch('requests.get')
    def test_boolean_param(self, mock_get):
        output = {'foo': 'asdf', 'bar': 3}
        mock_get.return_value = response(output)

        got = self.client.io.example.query({}, z=True)
        self.assertEqual(output, got)

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query',
            params={'z': 'true'},
            json=None,
            headers={'Content-Type': 'application/json'},
        )

    @patch('requests.get')
    def test_no_output_error(self, mock_get):
        mock_get.return_value = response()

        with self.assertRaises(ValidationError):
            got = self.client.io.example.query({})

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query',
            params={},
            json=None,
            headers={'Content-Type': 'application/json'},
        )

    @patch('requests.post')
    def test_no_params_input_output(self, mock_post):
        mock_post.return_value = response()
        self.assertIsNone(self.client.io.example.noParamsInputOutput({}))

        mock_post.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.noParamsInputOutput',
            params={},
            json=None,
            headers={'Content-Type': 'application/json'},
        )

    @patch('requests.post')
    def test_dashed_name(self, mock_post):
        mock_post.return_value = response()
        self.assertIsNone(self.client.io.example.dashed_name({}))

        mock_post.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.dashed-name',
            params={},
            json=None,
            headers={'Content-Type': 'application/json'},
        )

    @patch('requests.get')
    def test_defs(self, mock_get):
        mock_get.return_value = response({'out': 'foo'})
        self.assertEqual({'out': 'foo'},
                         self.client.io.example.defs({'in': 'bar'}))

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.defs',
            params={},
            json={'in': 'bar'},
            headers={'Content-Type': 'application/json'},
        )

    def test_missing_params(self):
        with self.assertRaises(ValidationError):
            self.client.io.example.params({})

        with self.assertRaises(ValidationError):
            self.client.io.example.params({}, foo='a')

    def test_invalid_params(self):
        with self.assertRaises(ValidationError):
            self.client.io.example.params({}, bar='c')

    @patch('requests.post')
    def test_validate_false(self, mock_post):
        client = Client('http://ser.ver', LEXICONS, validate=False)

        input = {'funky': 'chicken'}
        output = {'O': 'K'}
        mock_post.return_value = response(output)

        got = client.io.example.procedure(input)
        self.assertEqual(output, got)

        mock_post.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.procedure',
            params={},
            json=input,
            headers={'Content-Type': 'application/json'},
        )

