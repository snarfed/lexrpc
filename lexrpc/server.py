"""XRPC server implementation."""
import copy
import logging

import jsonschema

from .base import fail, LEXICON_METHOD_TYPES, XrpcBase

logger = logging.getLogger(__name__)


class Server(XrpcBase):
    """XRPC server base class. Subclass to implement specific methods."""

    def __init__(self, lexicons):
        """Constructor.

        Args:
          lexicon: sequence of dict lexicons

        Raises:
          :class:`jsonschema.SchemaError` if any schema is invalid
          ValueError if any method NSIDs are ambiguous
        """
        super().__init__(lexicons)

        # check that all methods are implemented
        methods = {}  # maps method name to NSID
        missing = []
        for nsid, lexicon in self._lexicons.items():
            if lexicon['type'] not in LEXICON_METHOD_TYPES:
                continue
            name = self._method_name(nsid)
            existing = methods.get(name)
            if existing:
                fail(f'{existing} and {nsid} map to the same method name {name}',
                     ValueError)
            methods[name] = nsid
            if not hasattr(self, name):
                missing.append(name)

        if missing:
            fail(f'{self.__class__} is missing methods: {missing}')

    def call(self, nsid, params=None, input=None):
        """Calls an XRPC query or procedure method.

        Args:
          nsid: str, method NSID
          params: dict, optional method parameters
          input: dict, optional input body

        Raises:
          NotImplementedError, if the given NSID is not found in any of the
            loaded lexicons
          :class:`jsonschema.ValidationError`, if the input or output returned
            by the method doesn't validate against the method's schemas
        """
        logger.debug(f'{nsid}: {params} {input}')

        # validate params and input, then encode params. pass non-null object to
        # validate to force it to actually validate the object.
        params = params or {}
        input = input or {}
        self._validate(nsid, 'parameters', params)
        self._validate(nsid, 'input', input)

        logger.debug('Running method')
        output = getattr(self, self._method_name(nsid))(params, input)
        logger.debug(f'Got: {output}')

        self._validate(nsid, 'output', output or {})
        return output

    @staticmethod
    def _method_name(nsid):
        """Converts an NSID to a Python class method name.

        Args:
          nsid: str

        Returns: str
        """
        return nsid.replace('.', '_').replace('-', '_')
