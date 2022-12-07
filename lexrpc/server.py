"""XRPC server implementation.

TODO: usage description
"""
import copy
import logging

logger = logging.getLogger(__name__)


class Server():

    _schemas = None  # dict mapping NSID to schema object

    def __init__(self, schemas):
        """Constructor.

        Args:
          schema: sequence of dict Lexicon schemas
        """
        assert isinstance(schemas, (list, tuple))

        self._schemas = {s['id']: s for s in copy.deepcopy(schemas)}

        methods = set(self._method_name(nsid) for nsid in self._schemas.keys())
        missing = methods - set(dir(self))
        if missing:
            msg = f'{self.__class__} is missing methods: {missing}'
            logger.error(msg)
            raise NotImplementedError(msg)

    def call(self, nsid, params=None, input=None):
        """Calls an XRPC query or procedure method.

        Args:
          nsid: str, method NSID
          params: dict, optional method parameters
          input: dict, optional input body

        Raises:
          NotImplementedError, if the given NSID is not found in any of the
            loaded schemas
          ValueError, if the input or output returned by the method don't
            validate against the method's schema
        """
        logger.debug(f'{nsid}: {params} {input}')

        schema = self._schemas.get(nsid)
        if not schema:
            msg = f'{nsid} not found'
            logger.error(msg)
            raise NotImplementedError(msg)

        # TODO: validate input
        output = getattr(self, self._method_name(nsid))(params, input)

        # TODO: validate output
        return output

    @staticmethod
    def _method_name(nsid):
        """Converts an NSID to a Python class method name.

        Args:
          nsid: str

        Returns: str
        """
        return nsid.replace('.', '_')
