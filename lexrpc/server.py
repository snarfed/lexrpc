"""XRPC server implementation.

TODO: usage description
"""
import copy
import logging

import jsonschema

logger = logging.getLogger(__name__)


class Server():

    _lexicons = None  # dict mapping NSID to lexicon object

    def __init__(self, lexicons):
        """Constructor.

        Args:
          lexicon: sequence of dict lexicons

        Raises:
          :class:`jsonschema.SchemaError` if any schema is invalid
        """
        assert isinstance(lexicons, (list, tuple))

        self._lexicons = {s['id']: s for s in copy.deepcopy(lexicons)}

        # validate schemas
        for lexicon in self._lexicons.values():
            for field in 'input', 'output':
                schema = lexicon.get(field, {}).get('schema')
                if schema:
                    try:
                        jsonschema.validate(None, schema)
                    except jsonschema.ValidationError as e:
                        # schema passed validation, None instance failed
                        pass

        # check that all methods are implemented
        methods = set(self._method_name(nsid) for nsid in self._lexicons.keys())
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
            loaded lexicons
          :class:`jsonschema.ValidationError`, if the input or output returned
            by the method don't validate against the method's schemas
        """
        logger.debug(f'{nsid}: {params} {input}')

        lexicon = self._lexicons.get(nsid)
        if not lexicon:
            msg = f'{nsid} not found'
            logger.error(msg)
            raise NotImplementedError(msg)

        # validate input
        input_schema = lexicon.get('input', {}).get('schema')
        if input_schema:
            logger.debug('Validating input')
            jsonschema.validate(input, input_schema)

        # run method
        logger.debug(f'Running method')
        output = getattr(self, self._method_name(nsid))(params, input)

        # validate output
        logger.debug('Validating output')
        output_schema = lexicon.get('output', {}).get('schema')
        if output_schema:
            jsonschema.validate(output, output_schema)

        logger.debug(f'Returning: {output}')
        return output

    @staticmethod
    def _method_name(nsid):
        """Converts an NSID to a Python class method name.

        Args:
          nsid: str

        Returns: str
        """
        return nsid.replace('.', '_')
