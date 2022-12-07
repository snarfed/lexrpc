"""Test Lexicon schemas.

Based on:
https://github.com/bluesky-social/atproto/blob/main/packages/xrpc-server/tests/bodies.test.ts
"""
SCHEMAS = [
  {
    'lexicon': 1,
    'id': 'io.example.procedure',
    'type': 'procedure',
    'input': {
      'encoding': 'application/json',
      'schema': {
        'type': 'object',
        'required': ['foo'],
        'properties': {
          'foo': { 'type': 'string' },
          'bar': { 'type': 'number' },
        },
      },
    },
    'output': {
      'encoding': 'application/json',
      'schema': {
        'type': 'object',
        'required': ['foo'],
        'properties': {
          'foo': { 'type': 'string' },
          'bar': { 'type': 'number' },
        },
      },
    },
  },
  {
    'lexicon': 1,
    'id': 'io.example.query',
    'type': 'query',
    'output': {
      'encoding': 'application/json',
      'schema': {
        'type': 'object',
        'required': ['foo'],
        'properties': {
          'foo': { 'type': 'string' },
          'bar': { 'type': 'number' },
        },
      },
    },
  },
]
