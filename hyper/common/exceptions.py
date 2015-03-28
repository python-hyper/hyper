# -*- coding: utf-8 -*-
"""
hyper/common/exceptions
~~~~~~~~~~~~~~~~~~~~~~~

Contains hyper's exceptions.
"""
class ChunkedDecodeError(Exception):
    """
    An error was encountered while decoding a chunked response.
    """
    pass


class InvalidResponseError(Exception):
    """
    A problem was found with the response that makes it invalid.
    """
    pass
