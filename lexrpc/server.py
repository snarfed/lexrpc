"""XRPC server implementation."""
import copy
from functools import wraps
import logging

import jsonschema

from .base import fail, LEXICON_METHOD_TYPES, NSID_RE, XrpcBase

logger = logging.getLogger(__name__)


class Server(XrpcBase):
    """XRPC server base class. Subclass to implement specific methods."""
    _methods = None  # dict, maps string NSID to Python callable

    def __init__(self, lexicons):
        """Constructor.

        Args:
          lexicon: sequence of dict lexicons

        Raises:
          :class:`jsonschema.SchemaError` if any schema is invalid
          ValueError if any method NSIDs are ambiguous
        """
        super().__init__(lexicons)
        self._methods = {}

    def method(self, nsid):
        """XRPC method decorator. Use on each function that implements a method.

        Args:
          fn: callable
          nsid: str
        """
        assert NSID_RE.match(nsid)

        def decorated(fn):
            existing = self._methods.get(nsid)
            if existing:
                fail(f'{nsid} already registered with {existing}',  AssertionError)
            self._methods[nsid] = fn

            @wraps(fn)
            def wrapped(*args, **kwargs):
                return fn(*args, **kwarg)
            return wrapped

        return decorated

    def call(self, nsid, params=None, input=None):
        """Calls an XRPC query or procedure method.

        Args:
          nsid: str, method NSID
          params: dict, optional method parameters
          input: dict, optional input body

        Raises:
          NotImplementedError, if the given NSID is not implemented or found in
            any of the loaded lexicons
          :class:`jsonschema.ValidationError`, if the input or output returned
            by the method doesn't validate against the method's schemas
        """
        logger.debug(f'{nsid}: {params} {input}')

        fn = self._methods.get(nsid)
        if not fn:
            fail(f'{nsid} not implemented', NotImplementedError)

        # validate params and input, then encode params. pass non-null object to
        # validate to force it to actually validate the object.
        params = params or {}
        input = input or {}
        self._validate(nsid, 'parameters', params)
        self._validate(nsid, 'input', input)

        logger.debug('Running method')
        output = fn(params, input)
        logger.debug(f'Got: {output}')

        self._validate(nsid, 'output', output or {})
        return output
