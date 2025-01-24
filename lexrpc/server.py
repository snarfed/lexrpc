"""XRPC server implementation."""
from functools import wraps
import logging

from .base import fail, METHOD_TYPES, NSID_RE, Base

logger = logging.getLogger(__name__)


class Redirect(Exception):
    """Raised by XRPC handlers to direct the server to serve an HTTP redirect.

    Whether this is official supported by the XRPC spec is still TBD:
    https://github.com/bluesky-social/atproto/discussions/1228

    Attributes:
      to (str): URL to redirect to
      status (int): HTTP status code, defaults to 302
    """
    def __init__(self, to, status=302, headers=None):
        assert to
        assert status
        self.to = to
        self.status = status
        self.headers = headers or {}


class Server(Base):
    """XRPC server base class. Subclass to implement specific methods."""
    _methods = None  # dict, maps string NSID to Python callable

    def __init__(self, **kwargs):
        """Constructor.

        Args:
          kwargs: passed through to :class:`Base`

        Raises:
          ValidationError: if any schema is invalid
        """
        super().__init__(**kwargs)
        self._methods = {}

    def method(self, nsid):
        """XRPC method decorator. Use on each function that implements a method.

        Args:
          nsid (str)
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
          nsid (str)
          fn (callable)
        """
        assert NSID_RE.match(nsid)

        existing = self._methods.get(nsid)
        if existing:
            fail(f'{nsid} already registered with {existing}',  AssertionError)
        self._methods[nsid] = fn

    def call(self, nsid, input=None, **params):
        """Calls an XRPC query or procedure method.

        For subscriptions, returns a generator that yields ``(header dict, payload
        dict)`` tuples to be DAG-CBOR encoded and sent to the websocket client.

        Args:
          nsid (str): method NSID
          input (dict or bytes): input body, optional for subscriptions
          params: optional parameters

        Returns:
          dict: output

        Raises:
          NotImplementedError: if the given NSID is not implemented or found in
            any of the loaded lexicons
          ValidationError: if the parameters, input, or returned output don't
            validate against the method's schemas
        """
        logger.debug(f'{nsid}: {params} {self.loggable(input)}')

        fn = self._methods.get(nsid)
        if not fn:
            fail(f'{nsid} not implemented', NotImplementedError)

        subscription = self.defs[nsid]['type'] == 'subscription'

        # validate params and input, then encode params
        params = self.validate(nsid, 'parameters', params)
        input = self.validate(nsid, 'input', input)

        args = [] if subscription else [input]
        output = fn(*args, **params)

        if subscription:
            def validator():
                for header, payload in output:
                    payload = self.validate(nsid, 'message', payload)
                    yield header, payload
            return validator()
        else:
            logger.debug(f'Returning {self.loggable(output)}')
            return self.validate(nsid, 'output', output)
