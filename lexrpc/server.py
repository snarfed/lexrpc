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
          nsid: str
        """
        def decorated(fn):
            self.register(nsid, fn)

            @wraps(fn)
            def wrapped(*args, **kwargs):
                return fn(*args, **kwargs)
            return wrapped

        return decorated

    def register(self, nsid, fn):
        """Registers an XRPC method decorator. Alternative to :meth:`method`.

        Args:
          nsid: str
          fn: callable
        """
        assert NSID_RE.match(nsid)

        existing = self._methods.get(nsid)
        if existing:
            fail(f'{nsid} already registered with {existing}',  AssertionError)
        self._methods[nsid] = fn


    def call(self, nsid, input=None, **params):
        """Calls an XRPC query or procedure method.

        For subscriptions, returns a generator that yields (header dict, payload
        dict) tuples to be DAG-CBOR encoded and sent to the websocket client.

        Args:
          nsid: str, method NSID
          input: dict or bytes, input body, optional for subscriptions
          params: optional parameters

        Raises:
          NotImplementedError
            if the given NSID is not implemented or found in any of the loaded
            lexicons
          :class:`jsonschema.ValidationError`
            if the parameters, input, or returned output don't validate against
            the method's schemas
        """
        def loggable(val):
            return f'{len(val)} bytes' if isinstance(val, bytes) else val

        logger.debug(f'{nsid}: {params} {loggable(input)}')

        fn = self._methods.get(nsid)
        if not fn:
            fail(f'{nsid} not implemented', NotImplementedError)

        subscription = self._defs[nsid]['type'] == 'subscription'

        # validate params and input, then encode params
        self._maybe_validate(nsid, 'parameters', params)
        if not subscription:
            self._maybe_validate(nsid, 'input', input)

        logger.debug('Running method')
        args = [] if subscription else [input]
        output = fn(*args, **params)

        if not subscription:
            logger.debug(f'Got: {loggable(output)}')
            self._maybe_validate(nsid, 'output', output)

        return output
