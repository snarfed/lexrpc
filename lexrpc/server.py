"""XRPC server implementation."""
from functools import wraps
import logging

from .base import fail, METHOD_TYPES, NSID_RE, Base

logger = logging.getLogger(__name__)


class Server(Base):
    """XRPC server base class. Subclass to implement specific methods."""
    _methods = None  # dict, maps string NSID to Python callable

    def __init__(self, *args, **kwargs):
        """Constructor.

        Args:
          lexicon: sequence of dict lexicons

        Raises:
          :class:`jsonschema.SchemaError`
            if any schema is invalid
        """
        super().__init__(*args, **kwargs)
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

    def call(self, nsid, input, **params):
        """Calls an XRPC query or procedure method.

        Args:
          nsid: str, method NSID
          input: dict, input body
          params: optional parameters

        Raises:
          NotImplementedError
            if the given NSID is not implemented or found in any of the loaded
            lexicons
          :class:`jsonschema.ValidationError`
            if the parameters, input, or returned output don't validate against
            the method's schemas
        """
        logger.debug(f'{nsid}: {params} {input}')

        fn = self._methods.get(nsid)
        if not fn:
            fail(f'{nsid} not implemented', NotImplementedError)

        # validate params and input, then encode params
        self._maybe_validate(nsid, 'parameters', params)
        self._maybe_validate(nsid, 'input', input)

        logger.debug('Running method')
        output = fn(input, **params)
        logger.debug(f'Got: {output}')

        self._maybe_validate(nsid, 'output', output)
        return output
