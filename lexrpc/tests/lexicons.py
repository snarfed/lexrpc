"""Test Lexicons.

Based on:
https://github.com/bluesky-social/atproto/blob/main/packages/xrpc-server/tests/bodies.test.ts
"""
LEXICONS = [
    {
        'lexicon': 1,
        'id': 'io.example.procedure',
        'defs': {
            'main': {
                'type': 'procedure',
                'description': 'Whatever you want',
                'parameters': {
                    'type': 'params',
                    'properties': {
                        'x': { 'type': 'string' },
                        'z': { 'type': 'boolean' },
                    },
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
        },
    },

    {
        'lexicon': 1,
        'id': 'io.example.query',
        'defs': {
            'main': {
                'type': 'query',
                'parameters': {
                    'type': 'params',
                    'properties': {
                        'x': { 'type': 'string' },
                        'z': { 'type': 'boolean' },
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
        },
    },

    {
        'lexicon': 1,
        'id': 'io.example.noParamsInputOutput',
        'defs': {
            'main': {
                'type': 'procedure',
            },
        },
    },

    {
        'lexicon': 1,
        'id': 'io.example.dashed-name',
        'defs': {
            'main': {
                'type': 'procedure',
            },
        },
    },

    {
        'lexicon': 1,
        'id': 'io.example.params',
        'defs': {
            'main': {
                'type': 'procedure',
                'parameters': {
                    'type': 'params',
                    'required': ['bar'],
                    'properties': {
                        'foo': { 'type': 'string' },
                        'bar': { 'type': 'number', },
                    },
                },
            },
        },
    },

    {
        'lexicon': 1,
        'id': 'io.example.record',
        'defs': {
            'main': {
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
        },
    },

    {
        'lexicon': 1,
        'id': 'io.example.token',
        'defs': {
            'main': {
                'type': 'token',
                'description': 'Undefined!',
            },
        },
    },

    {
        'lexicon': 1,
        'id': 'io.example.defs',
        'defs': {
            'main': {
                'type': 'query',
                'input': {
                    'encoding': 'application/json',
                    'schema': {
                        'type': 'object',
                        'properties': {'in': {'type': 'string'}},
                    },
                },
                'output': {
                    'encoding': 'application/json',
                    'schema': {
                        'type': 'object',
                        'properties': {'out': {'type': 'string'}},
                    },
                },
            },
        },
    },

    {
        'lexicon': 1,
        'id': 'io.example.error',
        'defs': {
            'main': {
                'type': 'query',
                'errors': [
                    {'name': 'OneBad'},
                    {'name': 'AnotherBad'},
                    {'name': 'ThirdBad'},
                ],
            },
        },
    },
]
