"""Unit tests for flask_server.py."""
from datetime import datetime, timedelta
from threading import Barrier, Condition, Thread
import time
from unittest import skip, TestCase
from unittest.mock import patch

import dag_cbor
from flask import Flask
from simple_websocket import ConnectionClosed

from .. import base
from ..base import XrpcError
from ..flask_server import init_flask, subscribers, Subscriber, subscription
from ..server import Redirect
from .lexicons import LEXICONS
from .test_base import NOW
from .test_server import server


class FakeConnection:
    """Fake of :class:`simple_websocket.ws.WSConnection`."""
    exc = None
    sent = []
    connected = True

    @classmethod
    def send(cls, msg):
        if cls.exc:
            raise cls.exc
        cls.sent.append(msg)


class XrpcEndpointTest(TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        init_flask(server, cls.app)
        base.now = lambda: NOW

    def setUp(self):
        self.client = self.app.test_client()
        FakeConnection.exc = None
        FakeConnection.sent = []
        FakeConnection.connected = True

    def tearDown(self):
        server._methods.pop('io.example.delayedSubscribe', None)

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

    def test_options(self):
        resp = self.client.options('/xrpc/io.example.query')
        self.assertEqual(200, resp.status_code)
        self.assertEqual('*', resp.headers['Access-Control-Allow-Origin'])
        self.assertEqual('', resp.text)

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
        self.assertEqual({
            'error': 'InvalidRequest',
            'message': 'not_an*nsid is not a valid NSID',
        }, resp.json)

    def test_query_boolean_param(self):
        resp = self.client.get('/xrpc/io.example.query?x=&z=false')
        self.assertEqual(200, resp.status_code, resp.json)

        resp = self.client.get('/xrpc/io.example.query?z=foolz')
        self.assertEqual(400, resp.status_code)
        self.assertEqual({
            'error': 'InvalidRequest',
            'message': "Got 'foolz' for boolean parameter z, expected true or false",
        }, resp.json)

    def test_subscription(self):
        handler = subscription(server, 'io.example.subscribe')

        def subscribe():
            with self.app.test_request_context(query_string={'start': 3, 'end': 6}):
                handler(FakeConnection)

        subscriber = Thread(target=subscribe)
        subscriber.start()
        subscriber.join()

        header_bytes = dag_cbor.encode({'hea': 'der'})
        self.assertEqual([
            header_bytes + dag_cbor.encode({'num': 3}),
            header_bytes + dag_cbor.encode({'num': 4}),
            header_bytes + dag_cbor.encode({'num': 5}),
        ], FakeConnection.sent)

    def test_subscription_client_disconnects(self):
        handler = subscription(server, 'io.example.subscribe')
        FakeConnection.connected = False

        def subscribe():
            with self.app.test_request_context(query_string={'start': 3, 'end': 6}):
                handler(FakeConnection)

        subscriber = Thread(target=subscribe)
        subscriber.start()
        subscriber.join()
        self.assertEqual([], FakeConnection.sent)

    def test_subscription_connection_closed_exception(self):
        FakeConnection.exc = ConnectionClosed()
        handler = subscription(server, 'io.example.subscribe')

        def subscribe():
            with self.app.test_request_context(query_string={'start': 3, 'end': 6}):
                handler(FakeConnection)

        subscriber = Thread(target=subscribe)
        subscriber.start()
        subscriber.join()
        self.assertEqual([], FakeConnection.sent)

    @patch('lexrpc.flask_server.SUBSCRIPTION_ITERATOR_TIMEOUT',
           timedelta(milliseconds=100))
    def test_subscription_iterator_timeout(self):
        @server.method('io.example.delayedSubscribe')
        def delayed_subscribe():
            time.sleep(.15)
            yield {'foo': 'bar'}, {}
            time.sleep(.15)
            yield {'foo 2': 'bar'}, {}

        handler = subscription(server, 'io.example.delayedSubscribe')

        def subscribe():
            with self.app.test_request_context():
                handler(FakeConnection)

        subscriber = Thread(target=subscribe)
        subscriber.start()
        subscriber.join()

        self.assertEqual([
            dag_cbor.encode({'foo': 'bar'}) + dag_cbor.encode({}),
            dag_cbor.encode({'foo 2': 'bar'}) + dag_cbor.encode({}),
        ], FakeConnection.sent)

    def test_subscription_http_not_websocket_405s(self):
        resp = self.client.post('/xrpc/io.example.subscribe')
        self.assertEqual(405, resp.status_code)
        self.assertIn('Use websocket', resp.json['message'])

    def test_subscribers(self):
        start = Barrier(2)
        cont = Barrier(3)

        @server.method('io.example.delayedSubscribe')
        def delayed_subscribe(foo=None):
            start.wait()
            cont.wait()
            yield {}, {}

        handler = subscription(server, 'io.example.delayedSubscribe')

        def subscribe(**kwargs):
            with self.app.test_request_context(**kwargs):
                handler(FakeConnection)

        self.assertEqual({}, subscribers)

        first = Thread(target=subscribe, kwargs={
            'query_string': {'foo': 'bar'},
            'headers': {'User-Agent': 'first'},
            'environ_overrides': {'REMOTE_ADDR': '1.2.3.4'},
        })
        first.start()
        start.wait()

        self.assertEqual([
            Subscriber('1.2.3.4', 'first', {'foo': 'bar'}, NOW),
        ], subscribers['io.example.delayedSubscribe'])

        start.reset()
        second = Thread(target=subscribe, kwargs={
            'query_string': {'foo': 'baz'},
            'headers': {
                'User-Agent': 'second',
                'X-Forwarded-For': '5.6.7.8, 9.9.9.9'
            },
            'environ_overrides': {'REMOTE_ADDR': '0.0.0.0'},
        })
        second.start()
        start.wait()

        self.assertEqual([
            Subscriber('1.2.3.4', 'first', {'foo': 'bar'}, NOW),
            Subscriber('5.6.7.8', 'second', {'foo': 'baz'}, NOW),
        ], subscribers['io.example.delayedSubscribe'])

        cont.wait()
        first.join()
        second.join()
        self.assertEqual(0, len(subscribers['io.example.delayedSubscribe']))

    def test_procedure_missing_input(self):
        resp = self.client.post('/xrpc/io.example.procedure')
        self.assertEqual(400, resp.status_code)
        self.assertEqual('io.example.procedure missing required property foo',
                         resp.json['message'])

        resp = self.client.post('/xrpc/io.example.procedure', json={'bar': 3})
        self.assertEqual(400, resp.status_code)
        self.assertEqual('io.example.procedure missing required property foo',
                         resp.json['message'])

    def test_procedure_bad_input(self):
        resp = self.client.post('/xrpc/io.example.procedure',
                                json={'foo': 2, 'bar': 3})
        self.assertEqual(400, resp.status_code)
        self.assertEqual('string property foo value 2 has unexpected type int',
                         resp.json['message'])

    def test_query_bad_output(self):
        resp = self.client.get('/xrpc/io.example.query?foo=abc')
        self.assertEqual(400, resp.status_code)
        self.assertEqual('string property foo value None is not nullable',
                         resp.json['message'])

    def test_missing_params(self):
        resp = self.client.post('/xrpc/io.example.params')
        self.assertEqual(400, resp.status_code)
        self.assertEqual('io.example.params missing required property bar',
                         resp.json['message'])

        resp = self.client.post('/xrpc/io.example.params?foo=a')
        self.assertEqual(400, resp.status_code)
        self.assertEqual('io.example.params missing required property bar',
                         resp.json['message'])

    def test_raises_valueerror(self):
        @server.method('io.example.valueError')
        def err(input):
            raise ValueError('foo')

        resp = self.client.post('/xrpc/io.example.valueError')
        self.assertEqual(400, resp.status_code)
        self.assertEqual({
            'error': 'InvalidRequest',
            'message': 'foo',
        }, resp.json)

    def test_raises_xrpc_error(self):
        @server.method('io.example.xrpcError')
        def err(input):
            raise XrpcError('the message', name='TheName')

        resp = self.client.post('/xrpc/io.example.xrpcError')
        self.assertEqual(400, resp.status_code)
        self.assertEqual({
            'error': 'TheName',
            'message': 'the message',
        }, resp.json)

    def test_integer_param(self):
        resp = self.client.post('/xrpc/io.example.params?bar=5')
        self.assertEqual(200, resp.status_code, resp.json)

    def test_unknown_methods(self):
        resp = self.client.get('/xrpc/io.unknown')
        self.assertEqual(501, resp.status_code)
        self.assertEqual({
            'error': 'MethodNotImplemented',
            'message': 'io.unknown not found',
        }, resp.json)

    def test_undefined_method(self):
        resp = self.client.post('/xrpc/not.defined')
        self.assertEqual(501, resp.status_code)
        self.assertEqual({
            'error': 'MethodNotImplemented',
            'message': 'not.defined not found',
        }, resp.json)

    def test_encodings(self):
        val = 234892348203948
        val_bytes = val.to_bytes((val.bit_length() + 7) // 8, 'big')
        resp = self.client.post('/xrpc/io.example.encodings', data=val_bytes)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(val + 1, int.from_bytes(resp.get_data(), 'big'))

    def test_redirect(self):
        @server.method('io.example.redirect')
        def redirect(input, status=None):
            kwargs = {}
            if status:
                kwargs['status'] = status
            raise Redirect('http://to/here', **kwargs)

        resp = self.client.post('/xrpc/io.example.redirect')
        self.assertEqual(302, resp.status_code)
        self.assertEqual('http://to/here', resp.headers['Location'])

        resp = self.client.post('/xrpc/io.example.redirect?status=301')
        self.assertEqual(301, resp.status_code)
        self.assertEqual('http://to/here', resp.headers['Location'])
