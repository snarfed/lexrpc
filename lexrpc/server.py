"""XRPC server implementation.

TODO: usage description
"""
import copy
import logging

import jsonschema

from .base import fail, XrpcBase

logger = logging.getLogger(__name__)


class Server(XrpcBase):
    """XRPC server base class. Subclass to implement specific methods."""

    def __init__(self, lexicons):
        """Constructor.

        Args:
          lexicon: sequence of dict lexicons

        Raises:
          :class:`jsonschema.SchemaError` if any schema is invalid
        """
        super().__init__(lexicons)

        # check that all methods are implemented
        methods = set(self._method_name(nsid) for nsid in self._lexicons.keys())
        missing = methods - set(dir(self))
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

        self._validate(nsid, 'input', input)

        logger.debug('Running method')
        output = getattr(self, self._method_name(nsid))(params, input)
        logger.debug(f'Got: {output}')

        self._validate(nsid, 'output', output)
        return output

    @staticmethod
    def _method_name(nsid):
        """Converts an NSID to a Python class method name.

        Args:
          nsid: str

        Returns: str
        """
        return nsid.replace('.', '_')
