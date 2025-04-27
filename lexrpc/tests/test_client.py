"""Unit tests for client.py."""
from io import BytesIO
import json
from unittest import TestCase
from unittest.mock import call, patch
import urllib.parse

import dag_cbor
import requests
from requests.auth import AuthBase, HTTPBasicAuth
import simple_websocket

from .lexicons import LEXICONS
from .. import client, Client
from ..base import ValidationError

HEADERS = {
    **client.DEFAULT_HEADERS,
    'Content-Type': 'application/json',
}

FULL_HEADERS = {
    **HEADERS,
    'foo': 'ey',
}


def response(body=None, status=200, headers=None):
    resp = requests.Response()
    resp.status_code = status

    if headers:
        resp.headers.update(headers)

    if isinstance(body, (dict, list)):
        body = json.dumps(body, indent=2)
        resp._text = body
        resp._content = body.encode('utf-8')
        resp.headers.setdefault('Content-Type', 'application/json')
    elif isinstance(body, bytes):
        resp._content = body

    return resp


class FakeWebsocketClient:
    """Fake of :class:`simple_websocket.Client`."""
    url = None
    headers = None
    sent = []
    to_receive = []

    def __init__(self, url, headers=None, **kwargs):
        FakeWebsocketClient.url = url
        FakeWebsocketClient.headers = headers

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
        self.client = Client('http://ser.ver', lexicons=LEXICONS,
                             headers={'foo': 'ey'})

        simple_websocket.Client = FakeWebsocketClient
        FakeWebsocketClient.url = None
        FakeWebsocketClient.headers = None
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
            json=None, data=None, auth=None, headers=FULL_HEADERS)

    @patch('requests.get', return_value=response({'foo': 'asdf'}))
    def test_call_address_trailing_slash(self, mock_get):
        client = Client('http://ser.ver/', lexicons=LEXICONS)
        got = client.call('io.example.query', {})
        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query',
            json=None, data=None, auth=None, headers=HEADERS)

    @patch('requests.get')
    def test_query(self, mock_get):
        output = {'foo': 'asdf', 'bar': 3}
        mock_get.return_value = response(output)

        got = self.client.io.example.query({}, x='y')
        self.assertEqual(output, got)

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query?x=y',
            json=None, data=None, auth=None, headers=FULL_HEADERS)

    @patch('requests.post')
    def test_procedure(self, mock_post):
        input = {'foo': 'asdf', 'bar': 3}
        output = {'foo': 'baz', 'bar': 4}
        mock_post.return_value = response(output)

        got = self.client.io.example.procedure(input, x='y')
        self.assertEqual(output, got)

        mock_post.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.procedure?x=y',
            json=input, data=None, auth=None, headers=FULL_HEADERS)

    @patch('requests.get')
    def test_boolean_param(self, mock_get):
        output = {'foo': 'asdf', 'bar': 3}
        mock_get.return_value = response(output)

        got = self.client.io.example.query({}, z=True)
        self.assertEqual(output, got)

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query?z=true',
            json=None, data=None, auth=None, headers=FULL_HEADERS)

    @patch('requests.get')
    def test_omit_None_param(self, mock_get):
        output = {'foo': 'asdf', 'bar': 3}
        mock_get.return_value = response(output)

        got = self.client.io.example.query({}, z=None)
        self.assertEqual(output, got)

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query',
            json=None, data=None, auth=None, headers=FULL_HEADERS)

    @patch('requests.get')
    def test_call_headers(self, mock_get):
        output = {'foo': 'asdf', 'bar': 3}
        mock_get.return_value = response(output)

        got = self.client.call('io.example.query', {}, x='y', headers={'foo': 'bar'})
        self.assertEqual(output, got)

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query?x=y',
            json=None, data=None, auth=None, headers={**FULL_HEADERS, 'foo': 'bar'})

    @patch('requests.get')
    def test_call_headers_override_content_type(self, mock_get):
        output = {'foo': 'asdf', 'bar': 3}
        mock_get.return_value = response(output)

        got = self.client.call('io.example.query', {}, x='y', headers={'Content-Type': 'application/xml'})
        self.assertEqual(output, got)

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query?x=y',
            json=None, data=None, auth=None,
            headers={**FULL_HEADERS, 'Content-Type': 'application/xml'})

    @patch('requests.get', return_value=response())
    def test_no_output_error(self, mock_get):
        with self.assertRaises(ValidationError):
            got = self.client.io.example.query({})

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query',
            json=None, data=None, auth=None, headers=FULL_HEADERS)

    @patch('requests.post', return_value=response())
    def test_no_params_input_output(self, mock_post):
        self.assertIsNone(self.client.io.example.noParamsInputOutput({}))

        mock_post.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.noParamsInputOutput',
            json=None, data=None, auth=None, headers=FULL_HEADERS)

    @patch('requests.post', return_value=response())
    def test_dashed_name(self, mock_post):
        self.assertIsNone(self.client.io.exa_mple.dashedName({}))

        mock_post.assert_called_once_with(
            'http://ser.ver/xrpc/io.exa-mple.dashedName',
            json=None, data=None, auth=None, headers=FULL_HEADERS)

    @patch('requests.get', return_value=response({'out': 'foo'}))
    def test_defs(self, mock_get):
        self.assertEqual({'out': 'foo'},
                         self.client.io.example.defs({'in': 'bar'}))

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.defs',
            json={'in': 'bar'}, data=None, auth=None, headers=FULL_HEADERS)

    @patch('requests.get', return_value=response(status=400, body={
        'error': 'Something',
        'message': 'too bad'
    }))
    def test_error(self, mock_get):
        with self.assertRaises(requests.HTTPError):
            self.client.call('io.example.query', {}, x='y')

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query?x=y',
            json=None, data=None, auth=None, headers=FULL_HEADERS)

    def test_missing_params(self):
        with self.assertRaises(ValidationError):
            self.client.io.example.params({})

        with self.assertRaises(ValidationError):
            self.client.io.example.params({}, foo='a')

    def test_invalid_params(self):
        with self.assertRaises(ValidationError):
            self.client.io.example.params({}, bar='c')

    @patch('requests.post', return_value=response({'items': ['z']}))
    def test_array(self, mock_post):
        self.assertEqual({'items': ['z']},
                         self.client.io.example.array({}, foo=['a', 'b']))

        mock_post.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.array?foo=a&foo=b',
            json=None, data=None, auth=None, headers=FULL_HEADERS)

    def test_subscription(self):
        msgs = [
            {'num': 3},
            {'num': 4},
            {'num': 5},
        ]
        FakeWebsocketClient.to_receive = msgs
        expected = [({'op': 1, 't': '#foo'}, msg) for msg in msgs]

        gen = self.client.io.example.subscribe(start=3, end=6)
        self.assertEqual(expected, list(gen))
        self.assertEqual('http://ser.ver/xrpc/io.example.subscribe?start=3&end=6',
                         FakeWebsocketClient.url)
        self.assertEqual({
            **client.DEFAULT_HEADERS,
            'foo': 'ey',
        }, FakeWebsocketClient.headers)

    def test_subscription_decode_false(self):
        msgs = [
            {'num': 3},
            {'num': 4},
            {'num': 5},
        ]
        FakeWebsocketClient.to_receive = msgs
        expected = [({'op': 1, 't': '#foo'}, msg) for msg in msgs]

        gen = self.client.io.example.subscribe(start=3, end=6)
        self.assertEqual(expected, list(gen))
        self.assertEqual('http://ser.ver/xrpc/io.example.subscribe?start=3&end=6',
                         FakeWebsocketClient.url)
        self.assertEqual({
            **client.DEFAULT_HEADERS,
            'foo': 'ey',
        }, FakeWebsocketClient.headers)

    def test_subscription_validate_param_fails(self):
        with self.assertRaises(ValidationError):
            self.client.io.example.subscribe(end='not integer')

    def test_subscription_validate_output_fails(self):
        msgs = [
            {'num': 3},
            {'num': 'not integer'},
        ]
        FakeWebsocketClient.to_receive = msgs
        expected = [({'op': 1, 't': '#foo'}, msg) for msg in msgs]

        gen = self.client.io.example.subscribe(start=3, end=6)
        _, payload = next(gen)
        self.assertEqual({'num': 3}, payload)

        with self.assertRaises(ValidationError):
            next(gen)

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
            json=input, data=None, auth=None, headers=HEADERS)

    @patch('requests.get')
    def test_client_headers(self, mock_get):
        output = {'foo': 'asdf', 'bar': 3}
        mock_get.return_value = response(output)

        client = Client('http://ser.ver', lexicons=LEXICONS,
                        headers={'Baz': 'biff'})
        got = client.call('io.example.query', {}, x='y')
        self.assertEqual(output, got)

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query?x=y',
            json=None, data=None, auth=None, headers={
                **HEADERS,
                'Baz': 'biff',
            },
        )

    @patch('requests.get')
    def test_client_headers_override_content_type(self, mock_get):
        output = {'foo': 'asdf', 'bar': 3}
        mock_get.return_value = response(output)

        client = Client('http://ser.ver', lexicons=LEXICONS,
                        headers={'Baz': 'biff', 'Content-Type': 'application/xml'})
        got = client.call('io.example.query', {}, x='y')
        self.assertEqual(output, got)

        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query?x=y',
            json=None, data=None, auth=None, headers={
                **HEADERS,
                'Baz': 'biff',
                'Content-Type': 'application/xml',
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
            json=None, data=None, auth=None, headers={
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
            'handle': 'han.dull',
            'did': 'did:dyd:x',
        }
        output = {
            'did': 'did:unu:sed',
            'availableUserDomains': ['moo.com'],
        }
        mock_get.side_effect = [
            response(status=400, body={
                'error': 'ExpiredToken',
                'message': 'Token has expired',
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
        got = client.com.atproto.server.describeServer()
        self.assertEqual(output, got)
        self.assertEqual(session, client.session)
        self.assertEqual([session], callback_got)

        mock_get.assert_any_call(
            'https://bsky.social/xrpc/com.atproto.server.describeServer',
            json=None, data=None, auth=None,
            headers={**HEADERS, 'Authorization': 'Bearer towkin'})
        mock_post.assert_any_call(
            'https://bsky.social/xrpc/com.atproto.server.refreshSession',
            json=None, data=None, auth=None,
            headers={**HEADERS, 'Authorization': 'Bearer reephrush'})
        mock_get.assert_any_call(
            'https://bsky.social/xrpc/com.atproto.server.describeServer',
            json=None, data=None, auth=None,
            headers={**HEADERS, 'Authorization': 'Bearer new-towkin'})

    @patch('requests.get', return_value=response(status=400, body={
        'error': 'ExpiredToken',
        'message': 'Token has expired'
    }))
    @patch('requests.post', return_value=response(status=400, body={
        'error': 'ExpiredToken',
        'message': 'Token has been revoked'
    }))
    def test_refresh_token_fails(self, mock_post, mock_get):
        callback_got = []
        def callback(session):
            nonlocal callback_got
            callback_got.append(session)

        client = Client(access_token='towkin', refresh_token='reephrush',
                        session_callback=callback)
        with self.assertRaises(requests.HTTPError):
            client.com.atproto.server.describeServer(x='y')

        self.assertEqual({}, client.session)
        self.assertEqual([{}], callback_got)

        mock_get.assert_called_with(
            'https://bsky.social/xrpc/com.atproto.server.describeServer?x=y',
            json=None, data=None, auth=None,
            headers={**HEADERS, 'Authorization': 'Bearer towkin'})
        mock_post.assert_called_with(
            'https://bsky.social/xrpc/com.atproto.server.refreshSession',
            json=None, data=None, auth=None,
            headers={**HEADERS, 'Authorization': 'Bearer reephrush'})

    @patch('requests.post', return_value=response(status=400, body={
        'error': 'InvalidToken',
        'message': 'Token is invalid'
    }))
    def test_dont_refresh_on_identity_procedures(self, mock_post):
        client = Client(access_token='towkin', refresh_token='reephrush')
        with self.assertRaises(requests.HTTPError):
            client.com.atproto.identity.signPlcOperation({'token': 'nope'})

        self.assertEqual({
            'accessJwt': 'towkin',
            'refreshJwt': 'reephrush',
        }, client.session)

        self.assertEqual(1, mock_post.call_count)
        mock_post.assert_called_with(
            'https://bsky.social/xrpc/com.atproto.identity.signPlcOperation',
            json={'token': 'nope'}, data=None, auth=None,
            headers={**HEADERS, 'Authorization': 'Bearer towkin'})

    @patch('requests.get')
    def test_auth_refresh_token(self, mock_get):
        class TokenAuth(AuthBase):
            token = 'before'

        callback_got = []
        def callback(auth):
            nonlocal callback_got
            callback_got.append(auth)

        output = {
            'did': 'did:unu:sed',
            'availableUserDomains': ['moo.com'],
        }
        def get(*args, auth=None, **kwargs):
            auth.token = 'after'
            return response(output)

        mock_get.side_effect = get

        auth = TokenAuth()
        client = Client(auth=auth, session_callback=callback)
        got = client.com.atproto.server.describeServer()
        self.assertEqual(output, got)
        self.assertEqual([auth], callback_got)

    @patch('requests.post')
    def test_createSession_sets_session(self, mock_post):
        session = {
            'accessJwt': 'towkin',
            'refreshJwt': 'unused',
            'handle': 'unu.sed',
            'did': 'did:unu:sed',
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
            json=input, data=None, auth=None, headers=HEADERS)

    def test_not_both_auth_and_session(self):
        with self.assertRaises(AssertionError):
            Client('http://ser.ver', access_token='x',
                   auth=HTTPBasicAuth('user', 'pwd'))

    @patch('requests.get')
    def test_auth(self, mock_get):
        mock_get.return_value = response({'foo': 'asdf'})

        auth = HTTPBasicAuth('user', 'pwd')
        client = Client('http://ser.ver', lexicons=LEXICONS, auth=auth)

        got = client.call('io.example.query', {}, x='y')
        self.assertEqual({'foo': 'asdf'}, got)
        mock_get.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.query?x=y',
            json=None, data=None, auth=auth, headers=HEADERS)

    @patch('requests.get')
    def test_bundled_lexicons(self, mock_get):
        client = Client('http://ser.ver')

        output = {'did': 'did:plc:foo', 'handle': 'bar.com'}
        mock_get.return_value = response(output)

        got = client.call('com.atproto.server.getSession', {})
        self.assertEqual(output, got)

    @patch('requests.post', return_value=response(b'baz biff'))
    def test_binary_output_input_data(self, mock_post):
        resp = self.client.io.example.encodings(b'foo bar', headers={
            'Content-Type': 'foo/bar',
        })
        self.assertEqual(b'baz biff', resp)

        mock_post.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.encodings',
            json=None, data=b'foo bar', auth=None, headers={
                **client.DEFAULT_HEADERS,
                'Content-Type': 'foo/bar',
                'foo': 'ey',
            })

    @patch('requests.post', return_value=response(b'baz biff'))
    def test_binary_output_input_stream(self, mock_post):
        stream = BytesIO(b'foo bar')
        resp = self.client.io.example.encodings(stream, headers={
            'Content-Type': 'foo/bar',
        })
        self.assertEqual(b'baz biff', resp)

        mock_post.assert_called_once_with(
            'http://ser.ver/xrpc/io.example.encodings',
            json=None, data=b'foo bar', auth=None, headers={
                **client.DEFAULT_HEADERS,
                'Content-Type': 'foo/bar',
                'foo': 'ey',
            })
