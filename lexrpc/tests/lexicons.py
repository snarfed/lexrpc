"""Test Lexicons.

Based on:
https://github.com/bluesky-social/atproto/blob/main/packages/xrpc-server/tests/bodies.test.ts
https://github.com/snarfed/atproto/blob/main/packages/lexicon/tests/_scaffolds/lexicons.ts
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
                        'x': {'type': 'string'},
                        'z': {'type': 'boolean'},
                    },
                },
                'input': {
                    'encoding': 'application/json',
                    'schema': {
                        'type': 'object',
                        'required': ['foo'],
                        'properties': {
                            'foo': {'type': 'string'},
                            'bar': {'type': 'number'},
                        },
                    },
                },
                'output': {
                    'encoding': 'application/json',
                    'schema': {
                        'type': 'object',
                        'required': ['foo'],
                        'properties': {
                            'foo': {'type': 'string'},
                            'bar': {'type': 'number'},
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
                        'x': {'type': 'string'},
                        'z': {'type': 'boolean'},
                    },
                },
                'output': {
                    'encoding': 'application/json',
                    'schema': {
                        'type': 'object',
                        'required': ['foo'],
                        'properties': {
                            'foo': {'type': 'string'},
                            'bar': {'type': 'number'},
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
                        'foo': {'type': 'string'},
                        'bar': {'type': 'number'},
                    },
                },
            },
        },
    },

    {
        'lexicon': 1,
        'id': 'io.example.array',
        'defs': {
            'main': {
                'type': 'procedure',
                'parameters': {
                    'type': 'params',
                    'properties': {
                        'foo': {'type': 'array', 'items': {'type': 'string'}},
                    },
                },
                'input': {
                    'encoding': 'application/json',
                    'schema': {
                        'type': 'object',
                    },
                },
                'output': {
                    'encoding': 'application/json',
                    'schema': {
                        'type': 'array',
                        'items': {'type': 'string'},
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
                    'baz': {'type': 'integer', },
                    'biff': {
                        'type': 'object',
                        'properties': {
                            'baj': {'type': 'string'},
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

    {
        'lexicon': 1,
        'id': 'io.example.encodings',
        'defs': {
            'main': {
                'type': 'procedure',
                'input': {
                    'encoding': 'number/int',
                },
                'output': {
                    'encoding': 'number/int',
                },
            },
        },
    },

    {
        'lexicon': 1,
        'id': 'io.example.subscribe',
        'defs': {
            'main': {
                'type': 'subscription',
                'parameters': {
                    'type': 'params',
                    'properties': {
                        'start': {'type': 'integer'},
                        'end': {'type': 'integer'},
                    },
                },
                'message': {
                    'schema': {
                        'type': 'object',
                        'properties': {'num': {'type': 'integer'}},
                    },
                },
                'errors': {
                    'Unhappy',
                },
            },
        },
    },

    {
        'lexicon': 1,
        'id': 'io.example.redirect',
        'defs': {
            'main': {
                'type': 'query',
            },
        },
    },

    {
        'lexicon': 1,
        'id': 'io.example.valueError',
        'defs': {
            'main': {
                'type': 'query',
            },
        },
    },

    # TODO

    # {
    #     'lexicon': 1,
    #     'id': 'com.example.kitchenSink',
    #     'defs': {
    #         'main': {
    #             'type': 'record',
    #             'description': 'A record',
    #             'key': 'tid',
    #             'record': {
    #                 'type': 'object',
    #                 'required': ['object', 'array', 'boolean', 'number', 'integer', 'string', 'datetime'],
    #                 'properties': {
    #                     'object': {
    #                         'type': 'ref',
    #                         'ref': '#object'
    #                     },
    #                     'array': {
    #                         'type': 'array',
    #                         'items': {'type': 'string'},
    #                     },
    #                     'boolean': {'type': 'boolean'},
    #                     'number': {'type': 'number'},
    #                     'integer': {'type': 'integer'},
    #                     'string': {'type': 'string'},
    #                     'datetime': {'type': 'datetime'},
    #                 },
    #             },
    #         },
    #         'object': {
    #             'type': 'object',
    #             'required': ['object', 'array', 'boolean', 'number', 'integer', 'string'],
    #             'properties': {
    #                 'object': {
    #                     'type': 'ref',
    #                     'ref': '#subobject',
    #                 },
    #                 'array': {
    #                     'type': 'array',
    #                     'items': {'type': 'string'},
    #                 },
    #                 'boolean': {'type': 'boolean'},
    #                 'number': {'type': 'number'},
    #                 'integer': {'type': 'integer'},
    #                 'string': {'type': 'string'},
    #             },
    #         },
    #         'subobject': {
    #             'type': 'object',
    #             'required': ['boolean'],
    #             'properties': {
    #                 'boolean': {'type': 'boolean'},
    #             },
    #         },
    #     },
    # },

    # {
    #     'lexicon': 1,
    #     'id': 'com.example.query',
    #     'defs': {
    #         'main': {
    #             'type': 'query',
    #             'description': 'A query',
    #             'parameters': {
    #                 'type': 'params',
    #                 'required': ['boolean', 'number', 'integer'],
    #                 'properties': {
    #                     'boolean': {'type': 'boolean'},
    #                     'number': {'type': 'number'},
    #                     'integer': {'type': 'integer'},
    #                     'string': {'type': 'string'},
    #                 },
    #             },
    #             'output': {
    #                 'encoding': 'application/json',
    #                 'schema': {
    #                     'type': 'ref',
    #                     'ref': 'com.example.kitchenSink#object',
    #                 },
    #             },
    #         },
    #     },
    # },

    # {
    #     'lexicon': 1,
    #     'id': 'com.example.union',
    #     'defs': {
    #         'main': {
    #             'type': 'record',
    #             'description': 'A record',
    #             'key': 'tid',
    #             'record': {
    #                 'type': 'object',
    #                 'required': ['unionOpen', 'unionClosed'],
    #                 'properties': {
    #                     'unionOpen': {
    #                         'type': 'union',
    #                         'refs': [
    #                             'com.example.kitchenSink#object',
    #                             'com.example.kitchenSink#subobject',
    #                         ],
    #                     },
    #                     'unionClosed': {
    #                         'type': 'union',
    #                         'closed': True,
    #                         'refs': [
    #                             'com.example.kitchenSink#object',
    #                             'com.example.kitchenSink#subobject',
    #                         ],
    #                     },
    #                 },
    #             },
    #         },
    #     },
    # },

    # {
    #     'lexicon': 1,
    #     'id': 'com.example.unknown',
    #     'defs': {
    #         'main': {
    #             'type': 'record',
    #             'description': 'A record',
    #             'key': 'tid',
    #             'record': {
    #                 'type': 'object',
    #                 'required': ['unknown'],
    #                 'properties': {
    #                     'unknown': {'type': 'unknown'},
    #                     'optUnknown': {'type': 'unknown'},
    #                 },
    #             },
    #         },
    #     },
    # },

    # {
    #     'lexicon': 1,
    #     'id': 'com.example.arrayLength',
    #     'defs': {
    #         'main': {
    #             'type': 'record',
    #             'record': {
    #                 'type': 'object',
    #                 'properties': {
    #                     'array': {
    #                         'type': 'array',
    #                         'minLength': 2,
    #                         'maxLength': 4,
    #                         'items': {'type': 'number'},
    #                     },
    #                 },
    #             },
    #         },
    #     },
    # },

    # {
    #     'lexicon': 1,
    #     'id': 'com.example.boolConst',
    #     'defs': {
    #         'main': {
    #             'type': 'record',
    #             'record': {
    #                 'type': 'object',
    #                 'properties': {
    #                     'boolean': {
    #                         'type': 'boolean',
    #                         'const': False,
    #                     },
    #                 },
    #             },
    #         },
    #     },
    # },

    # {
    #     'lexicon': 1,
    #     'id': 'com.example.numberRange',
    #     'defs': {
    #         'main': {
    #             'type': 'record',
    #             'record': {
    #                 'type': 'object',
    #                 'properties': {
    #                     'number': {
    #                         'type': 'number',
    #                         'minimum': 2,
    #                         'maximum': 4,
    #                     },
    #                 },
    #             },
    #         },
    #     },
    # },

    # {
    #     'lexicon': 1,
    #     'id': 'com.example.numberEnum',
    #     'defs': {
    #         'main': {
    #             'type': 'record',
    #             'record': {
    #                 'type': 'object',
    #                 'properties': {
    #                     'number': {
    #                         'type': 'number',
    #                         'enum': [1, 1.5, 2],
    #                     },
    #                 },
    #             },
    #         },
    #     },
    # },

    # {
    #     'lexicon': 1,
    #     'id': 'com.example.numberConst',
    #     'defs': {
    #         'main': {
    #             'type': 'record',
    #             'record': {
    #                 'type': 'object',
    #                 'properties': {
    #                     'number': {
    #                         'type': 'number',
    #                         'const': 0,
    #                     },
    #                 },
    #             },
    #         },
    #     },
    # },

    # {
    #     'lexicon': 1,
    #     'id': 'com.example.integerRange',
    #     'defs': {
    #         'main': {
    #             'type': 'record',
    #             'record': {
    #                 'type': 'object',
    #                 'properties': {
    #                     'integer': {
    #                         'type': 'integer',
    #                         'minimum': 2,
    #                         'maximum': 4,
    #                     },
    #                 },
    #             },
    #         },
    #     },
    # },

    # {
    #     'lexicon': 1,
    #     'id': 'com.example.integerEnum',
    #     'defs': {
    #         'main': {
    #             'type': 'record',
    #             'record': {
    #                 'type': 'object',
    #                 'properties': {
    #                     'integer': {
    #                         'type': 'integer',
    #                         'enum': [1, 2],
    #                     },
    #                 },
    #             },
    #         },
    #     },
    # },

    # {
    #     'lexicon': 1,
    #     'id': 'com.example.integerConst',
    #     'defs': {
    #         'main': {
    #             'type': 'record',
    #             'record': {
    #                 'type': 'object',
    #                 'properties': {
    #                     'integer': {
    #                         'type': 'integer',
    #                         'const': 0,
    #                     },
    #                 },
    #             },
    #         },
    #     },
    # },

    # {
    #     'lexicon': 1,
    #     'id': 'com.example.stringLength',
    #     'defs': {
    #         'main': {
    #             'type': 'record',
    #             'record': {
    #                 'type': 'object',
    #                 'properties': {
    #                     'string': {
    #                         'type': 'string',
    #                         'minLength': 2,
    #                         'maxLength': 4,
    #                     },
    #                 },
    #             },
    #         },
    #     },
    # },
]
