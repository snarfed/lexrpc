"""Unit tests for flask_server.py."""
from unittest import TestCase

from flask import Flask

from ..flask_server import init_flask
from .lexicons import LEXICONS
from .test_server import server


class XrpcEndpointTest(TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        init_flask(server, cls.app)

    def setUp(self):
        self.client = self.app.test_client()

    def test_procedure(self):
        input = {
            'foo': 'xyz',
            'bar': 3,
        }
        resp = self.client.post('/xrpc/io.example.procedure', json=input)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(input, resp.json)

    def test_query(self):
        resp = self.client.get('/xrpc/io.example.query?x=y')
        self.assertEqual(200, resp.status_code)
        self.assertEqual('application/json', resp.headers['Content-Type'])
        self.assertEqual({'foo': 'y', 'bar': 5}, resp.json)

    def test_no_params_input_output(self):
        resp = self.client.post('/xrpc/io.example.noParamsInputOutput')
        self.assertEqual(200, resp.status_code)

    def test_dashed_name(self):
        resp = self.client.post('/xrpc/io.example.dashed-name')
        self.assertEqual(200, resp.status_code)

    def test_not_nsid(self):
        resp = self.client.post('/xrpc/not_an*nsid')
        self.assertEqual(400, resp.status_code)
        self.assertEqual('application/json', resp.headers['Content-Type'])
        self.assertEqual({'message': 'not_an*nsid is not a valid NSID'}, resp.json)

    def test_query_boolean_param(self):
        resp = self.client.get('/xrpc/io.example.query?x=&z=false')
        self.assertEqual(200, resp.status_code, resp.json)

        resp = self.client.get('/xrpc/io.example.query?z=foolz')
        self.assertEqual(400, resp.status_code)
        self.assertEqual("Got 'foolz' for boolean parameter z, expected true or false",
                         resp.json['message'])

    def test_procedure_missing_input(self):
        resp = self.client.post('/xrpc/io.example.procedure')
        self.assertEqual(400, resp.status_code)
        self.assertTrue(resp.json['message'].startswith(
            'Error validating io.example.procedure input:'))

        resp = self.client.post('/xrpc/io.example.procedure', json={'bar': 3})
        self.assertEqual(400, resp.status_code)
        self.assertTrue(resp.json['message'].startswith(
            'Error validating io.example.procedure input:'))

    def test_procedure_bad_input(self):
        resp = self.client.post('/xrpc/io.example.procedure', json={'foo': 2, 'bar': 3})
        self.assertEqual(400, resp.status_code)
        self.assertTrue(resp.json['message'].startswith(
            'Error validating io.example.procedure input:'))

    def test_query_bad_output(self):
        global BAR
        BAR = 'not an integer'

        resp = self.client.get('/xrpc/io.example.query?foo=abc')
        self.assertEqual(400, resp.status_code)
        self.assertTrue(resp.json['message'].startswith(
            'Error validating io.example.query output:'))

    def test_missing_params(self):
        resp = self.client.post('/xrpc/io.example.params')
        self.assertEqual(400, resp.status_code)
        self.assertTrue(resp.json['message'].startswith(
            'Error validating io.example.params parameters:'))

        resp = self.client.post('/xrpc/io.example.params?foo=a')
        self.assertEqual(400, resp.status_code)
        self.assertTrue(resp.json['message'].startswith(
            'Error validating io.example.params parameters:'))

    def test_invalid_params(self):
        resp = self.client.post('/xrpc/io.example.params?bar=c')
        self.assertEqual(400, resp.status_code)
        self.assertIn("'c' for number parameter bar", resp.json['message'])

    def test_integer_param(self):
        resp = self.client.post('/xrpc/io.example.params?bar=5')
        self.assertEqual(200, resp.status_code, resp.json)

    def test_unknown_methods(self):
        resp = self.client.get('/xrpc/io.unknown')
        self.assertEqual(501, resp.status_code)

    def test_undefined_method(self):
        resp = self.client.post('/xrpc/not.defined')
        self.assertEqual(501, resp.status_code)
