"""Unit tests for client.py.

Based on:
https://github.com/bluesky-social/atproto/blob/main/packages/xrpc-server/tests/bodies.test.ts
"""
from unittest import TestCase
from unittest.mock import ANY, call, patch

import requests

from .schemas import SCHEMAS


@patch('requests.get')
@patch('requests.post')
class ClientTest(TestCase):

    def setUp(self):
        self.client = xrpc.service('http://localhost:8892')
        xrpc.addSchemas(SCHEMAS)

    # def test_one(self):
    #     self.client.call(
    #   'io.example.validationTest',
    #   {},
    #   {
    #     foo: 'hello',
    #     bar: 123,
    #   },
    # )
    # expect(res1.success).toBeTruthy()
    # expect(res1.data.foo).toBe('hello')
    # expect(res1.data.bar).toBe(123)

    # await expect(client.call('io.example.validationTest', {})).rejects.toThrow(
    #   `A request body is expected but none was provided`,
    # )
    # await expect(
    #   client.call('io.example.validationTest', {}, {}),
    # ).rejects.toThrow(`data must have required property 'foo'`)
    # await expect(
    #   client.call('io.example.validationTest', {}, { foo: 123 }),
    # ).rejects.toThrow(`data/foo must be string`)

    # await expect(client.call('io.example.validationTest2')).rejects.toThrow(
    #   `data must have required property 'foo'`,
    # )
