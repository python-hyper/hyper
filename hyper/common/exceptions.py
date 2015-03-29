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


class SocketError(Exception):
    """
    An error occurred during socket operation.
    """
    pass


class LineTooLongError(Exception):
    """
    An attempt to read a line from a socket failed because no newline was
    found.
    """
    pass


# Create our own ConnectionResetError.
try:  # pragma: no cover
    ConnectionResetError = ConnectionResetError
except NameError:  # pragma: no cover
    class ConnectionResetError(Exception):
        """
        A HTTP connection was unexpectedly reset.
        """
