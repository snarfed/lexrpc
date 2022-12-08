"""Base code shared by both server and client."""
import copy
import logging

import jsonschema

logger = logging.getLogger(__name__)


def fail(msg, exc=NotImplementedError):
    """Logs an error and raises an exception with the given message."""
    logger.error(msg)
    raise exc(msg)


class XrpcBase():
    """Base class for both XRPC client and server."""

    _lexicons = None  # dict mapping NSID to lexicon object

    def __init__(self, lexicons):
        """Constructor.

        Args:
          lexicons: sequence of dict lexicons

        Raises:
          :class:`jsonschema.SchemaError` if any schema is invalid
        """
        assert isinstance(lexicons, (list, tuple))
        self._lexicons = {s['id']: s for s in copy.deepcopy(lexicons)}
        logger.debug(f'Got lexicons for: {self._lexicons.keys()}')

        # validate schemas
        for i, lexicon in enumerate(self._lexicons.values()):
            id = lexicon.get('id')
            assert id, f'Lexicon {i} missing id field'
            type = lexicon.get('type')
            assert type in ('query', 'procedure'), f'Bad type for lexicon {id}: {type}'
            for field in 'input', 'output':
                self._validate(id, field, None)

    def _get_lexicon(self, nsid):
        """Returns the given lexicon object.

        Raises:
          NotImplementedError, if no lexicon exists for the given NSID
        """
        lexicon = self._lexicons.get(nsid)
        if not lexicon:
            fail(f'{nsid} not found')

        return lexicon

    def _validate(self, nsid, type, obj):
        """Validates a JSON object against a given schema.

        Args:
          nsid: str, method NSID
          type: either 'input' or 'output'
          obj: decoded JSON object, or None to only validate the schema itself

        Returns: None

        Raises:
          NotImplementedError, if no lexicon exists for the given NSID, or the
            lexicon does not define a schema for the given type
          :class:`jsonschema.SchemaError`, if the schema is invalid
          :class:`jsonschema.ValidationError`, if the object is invalid
        """
        assert type in ('input', 'output'), type

        schema = self._get_lexicon(nsid).get(type, {}).get('schema')
        if not schema:
            if not obj:
                return
            fail(f'{nsid} has no schema for {type}')

        logger.debug(f'Validating {nsid} {type}')
        try:
            jsonschema.validate(obj, schema)
        except jsonschema.ValidationError as e:
            # schema passed validation, obj failed
            if obj is not None:
                raise
