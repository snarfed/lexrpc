"""Test Lexicons.

Based on:
https://github.com/bluesky-social/atproto/blob/main/packages/xrpc-server/tests/bodies.test.ts
"""
LEXICONS = [
    {
        'lexicon': 1,
        'id': 'io.example.procedure',
        'type': 'procedure',
        'description': 'Whatever you want',
        'parameters': {
            'x': { 'type': 'string' },
            'z': { 'type': 'boolean' },
        },
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
        'parameters': {
            'x': { 'type': 'string' },
            'z': { 'type': 'boolean' },
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
        'id': 'io.example.no-params-input-output',
        'type': 'procedure',
    },

    {
        'lexicon': 1,
        'id': 'io.example.params',
        'type': 'procedure',
        'parameters': {
            'foo': { 'type': 'string' },
            'bar': { 'type': 'number', 'required': True },
        },
    },

    {
        'lexicon': 1,
        'id': 'io.example.record',
        'type': 'record',
        'record': {
            'required': ['baz'],
            'baz': { 'type': 'integer', },
            'biff': {
                'type': 'object',
                'properties': {
                    'baj': { 'type': 'string' },
                 },
            },
        },
    },

    {
        'lexicon': 1,
        'id': 'io.example.token',
        'type': 'token',
        'description': 'Undefined!',
    },
]
