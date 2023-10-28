"""Unit tests for client.py."""
import json
from unittest import skip, TestCase
from unittest.mock import call, patch
import urllib.parse

import dag_cbor
from jsonschema import ValidationError
import requests
import simple_websocket

from .lexicons import LEXICONS
from .. import client, Client

HEADERS = {
    **client.DEFAULT_HEADERS,
    'Content-Type': 'application/json',
}

def response(body=None, status=200, headers=None):
    resp = requests.Response()
    resp.status_code = status

    if headers:
        resp.headers.update(headers)

    if body is not None:
        assert isinstance(body, (dict, list))
        body = json.dumps(body, indent=2)
        resp._text = body
        resp._content = body.encode('utf-8')
        resp.headers.setdefault('Content-Type', 'application/json')

    return resp


class FakeWebsocketClient:
    """Fake of :class:`simple_websocket.Client`."""

    def __init__(self, url):
        FakeWebsocketClient.url = url

    def send(self, msg):
        self.sent.append(json.loads(msg))

    def receive(self):
        if not self.to_receive:
            raise simple_websocket.ConnectionClosed(message='foo')

        return (dag_cbor.encode({'op': 1, 't': '#foo'}) +
                dag_cbor.encode(self.to_receive.pop(0)))


class ClientTest(TestCase):
    maxDiff = None

    def setUp(self):
        self.client = Client('http://ser.ver', lexicons=LEXICONS)

        simple_websocket.Client = FakeWebsocketClient
        FakeWebsocketClient.sent = []
        FakeWebsocketClient.to_receive = []

    @patch('requests.get')
    def test_call(self, mock_get):
        output = {'foo': 'asdf', 'bar': 3}
        mock_get.return_value = response(output)

        got = self.client.call('io.example.query', {}, x='y')
        self.assertEqual(output, got)

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query?x=y',
            json=None, headers=HEADERS)

    @patch('requests.get')
    def test_call_address_trailing_slash(self, mock_get):
        client = Client('http://ser.ver/', lexicons=LEXICONS)
        mock_get.return_value = response({})

        got = client.call('io.example.query', {})
        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query',
            json=None, headers=HEADERS)

    @patch('requests.get')
    def test_query(self, mock_get):
        output = {'foo': 'asdf', 'bar': 3}
        mock_get.return_value = response(output)

        got = self.client.io.example.query({}, x='y')
        self.assertEqual(output, got)

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query?x=y',
            json=None, headers=HEADERS)

    @patch('requests.post')
    def test_procedure(self, mock_post):
        input = {'foo': 'asdf', 'bar': 3}
        output = {'foo': 'baz', 'bar': 4}
        mock_post.return_value = response(output)

        got = self.client.io.example.procedure(input, x='y')
        self.assertEqual(output, got)

        mock_post.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.procedure?x=y',
            json=input, headers=HEADERS)

    @patch('requests.get')
    def test_boolean_param(self, mock_get):
        output = {'foo': 'asdf', 'bar': 3}
        mock_get.return_value = response(output)

        got = self.client.io.example.query({}, z=True)
        self.assertEqual(output, got)

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query?z=true',
            json=None, headers=HEADERS)

    # TODO
    @skip
    @patch('requests.get')
    def test_no_output_error(self, mock_get):
        mock_get.return_value = response()

        with self.assertRaises(ValidationError):
            got = self.client.io.example.query({})

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query',
            json=None, headers=HEADERS)

    @patch('requests.post')
    def test_no_params_input_output(self, mock_post):
        mock_post.return_value = response()
        self.assertIsNone(self.client.io.example.noParamsInputOutput({}))

        mock_post.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.noParamsInputOutput',
            json=None, headers=HEADERS)

    @patch('requests.post')
    def test_dashed_name(self, mock_post):
        mock_post.return_value = response()
        self.assertIsNone(self.client.io.example.dashed_name({}))

        mock_post.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.dashed-name',
            json=None, headers=HEADERS)

    @patch('requests.get')
    def test_defs(self, mock_get):
        mock_get.return_value = response({'out': 'foo'})
        self.assertEqual({'out': 'foo'},
                         self.client.io.example.defs({'in': 'bar'}))

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.defs',
            json={'in': 'bar'}, headers=HEADERS)

    # TODO
    @skip
    def test_missing_params(self):
        with self.assertRaises(ValidationError):
            self.client.io.example.params({})

        with self.assertRaises(ValidationError):
            self.client.io.example.params({}, foo='a')

    # TODO
    @skip
    def test_invalid_params(self):
        with self.assertRaises(ValidationError):
            self.client.io.example.params({}, bar='c')

    @patch('requests.post')
    def test_array(self, mock_post):
        mock_post.return_value = response(['z'])

        self.assertEqual(['z'], self.client.io.example.array({}, foo=['a', 'b']))

        mock_post.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.array?foo=a&foo=b',
            json=None, headers=HEADERS)

    def test_subscription(self):
        msgs = [
            {'num': 3},
            {'num': 4},
            {'num': 5},
        ]
        FakeWebsocketClient.to_receive = list(msgs)

        expected = [({'op': 1, 't': '#foo'}, msg) for msg in msgs]

        gen = self.client.io.example.subscribe(start=3, end=6)
        self.assertEqual(expected, list(gen))
        self.assertEqual('http://ser.ver/xrpc/io.example.subscribe?start=3&end=6',
                         FakeWebsocketClient.url)

    @patch('requests.post')
    def test_validate_false(self, mock_post):
        client = Client('http://ser.ver', lexicons=LEXICONS, validate=False)

        input = {'funky': 'chicken'}
        output = {'O': 'K'}
        mock_post.return_value = response(output)

        got = client.io.example.procedure(input)
        self.assertEqual(output, got)

        mock_post.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.procedure',
            json=input, headers=HEADERS)

    @patch('requests.get')
    def test_headers(self, mock_get):
        output = {'foo': 'asdf', 'bar': 3}
        mock_get.return_value = response(output)

        client = Client('http://ser.ver', lexicons=LEXICONS,
                        headers={'Baz': 'biff'})
        got = client.call('io.example.query', {}, x='y')
        self.assertEqual(output, got)

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query?x=y',
            json=None,
            headers={
                **HEADERS,
                'Baz': 'biff',
            },
        )

    @patch('requests.get')
    def test_access_token(self, mock_get):
        output = {'foo': 'asdf', 'bar': 3}
        mock_get.return_value = response(output)

        client = Client('http://ser.ver', lexicons=LEXICONS, access_token='towkin',
                        headers={'Baz': 'biff'})
        got = client.call('io.example.query', {}, x='y')
        self.assertEqual(output, got)

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query?x=y',
            json=None,
            headers={
                **HEADERS,
                'Baz': 'biff',
                'Authorization': 'Bearer towkin',
            },
        )

    @patch('requests.get')
    @patch('requests.post')
    def test_refresh_token(self, mock_post, mock_get):
        session = {
            'accessJwt': 'new-towkin',
            'refreshJwt': 'reephrush',
            'handle': 'handull',
            'did': 'dyd',
        }
        output = {'foo': 'asdf', 'bar': 3}
        mock_get.side_effect = [
            response(status=400, body={
                'error': 'ExpiredToken',
                'message': 'Token has expired'
            }),
            response(output),
        ]
        mock_post.return_value = response(session)

        callback_got = []
        def callback(session):
            nonlocal callback_got
            callback_got.append(session)

        client = Client(access_token='towkin', refresh_token='reephrush',
                        session_callback=callback)
        got = client.com.atproto.server.describeServer(x='y')
        self.assertEqual(output, got)
        self.assertEqual(session, client.session)
        self.assertEqual([session], callback_got)

        mock_get.assert_any_call(
            'https://bsky.social/xrpc/com.atproto.server.describeServer?x=y',
            json=None,
            headers={**HEADERS, 'Authorization': 'Bearer towkin'})
        mock_post.assert_any_call(
            'https://bsky.social/xrpc/com.atproto.server.refreshSession',
            json=None,
            headers={**HEADERS, 'Authorization': 'Bearer reephrush'})
        mock_get.assert_any_call(
            'https://bsky.social/xrpc/com.atproto.server.describeServer?x=y',
            json=None,
            headers={**HEADERS, 'Authorization': 'Bearer new-towkin'})

    @patch('requests.post')
    def test_createSession_sets_session(self, mock_post):
        session = {
            'accessJwt': 'towkin',
            'foo': 'bar',
        }
        mock_post.return_value = response(session)

        input = {
            'identifier': 'snarfed.bsky.social',
            'password': 'hunter2',
        }

        client = Client()
        client.com.atproto.server.createSession(input)
        self.assertEqual(session, client.session)

        mock_post.assert_called_once_with(
            'https://bsky.social/xrpc/com.atproto.server.createSession',
            json=input, headers=HEADERS)

    @patch('requests.get')
    def test_bundled_lexicons(self, mock_get):
        client = Client('http://ser.ver')

        output = {'did': 'did:plc:foo', 'handle': 'bar.com'}
        mock_get.return_value = response(output)

        got = client.call('com.atproto.server.getSession', {})
        self.assertEqual(output, got)
