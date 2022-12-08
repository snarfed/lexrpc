"""Unit tests for client.py.

Based on:
https://github.com/bluesky-social/atproto/blob/main/packages/xrpc-server/tests/bodies.test.ts
"""
import json
from unittest import TestCase
from unittest.mock import patch

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
        # resp.raw = io.BytesIO(resp._content)  # needed for close()

    return resp


class ClientTest(TestCase):

    def setUp(self):
        self.client = Client('http://ser.ver', LEXICONS)
        self.call = self.client.call

    @patch('requests.get')
    def test_query(self, mock_get):
        params = {'x': 'y'}
        output = {'foo': 'asdf', 'bar': 3}

        mock_get.return_value = response(output)

        got = self.call('io.example.query', params)
        self.assertEqual(output, got)

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query',
            params={'x': 'y'},
            json=None,
            headers={'Content-Type': 'application/json'},
        )

    @patch('requests.post')
    def test_procedure(self, mock_post):
        params = {'x': 'y'}
        input = {'foo': 'asdf', 'bar': 3}
        output = {'foo': 'baz', 'bar': 4}

        mock_post.return_value = response(output)

        got = self.call('io.example.procedure', params, input)
        self.assertEqual(output, got)

        mock_post.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.procedure',
            params=params,
            json=input,
            headers={'Content-Type': 'application/json'},
        )

    @patch('requests.get')
    def test_boolean_param(self, mock_get):
        pass

    @patch('requests.post')
    def test_no_output(self, mock_post):
        pass
