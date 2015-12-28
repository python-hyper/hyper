# -*- coding: utf-8 -*-
"""
hyper/http20/exceptions
~~~~~~~~~~~~~~~~~~~~~~~

This defines exceptions used in the HTTP/2 portion of hyper.
"""

class HTTP20Error(IOError):
    """
    The base class for all of ``hyper``'s HTTP/2-related exceptions.
    """
    pass


class HPACKEncodingError(HTTP20Error):
    """
    An error has been encountered while performing HPACK encoding.
    """
    pass


class HPACKDecodingError(HTTP20Error):
    """
    An error has been encountered while performing HPACK decoding.
    """
    pass


class ConnectionError(HTTP20Error):
    """
    The remote party signalled an error affecting the entire HTTP/2
    connection, and the connection has been closed.
    """
    pass


class ProtocolError(HTTP20Error):
    """
    The remote party violated the HTTP/2 protocol.
    """
    pass


class StreamResetError(HTTP20Error):
    """
    A stream was forcefully reset by the remote party.
    """
    pass

class InternalError(HTTP20Error):
    pass

class FlowControlError(HTTP20Error):
    pass

class SettingsTimeout(HTTP20Error):
    pass

class StreamClosed(HTTP20Error):
    pass

class FrameSizeError(HTTP20Error):
    pass

class RefusedStream(HTTP20Error):
    pass

class CompressionError(HTTP20Error):
    pass

class EnhanceYourCalm(HTTP20Error):
    pass

class InadequateSecurity(HTTP20Error):
    pass

class Http11Required(HTTP20Error):
    pass

def HTTP20ErrorHandler(func):
    """
    HTTP20Error exception handler which captures exceptions thrown
    that impact a single stream or the entire connection.
    """
    def handler(*args, **kwargs):
        try:
            func(*args, **kwargs)

        # Handle errors that impact entire connection.
        except (ProtocolError, ConnectionError, InternalError) as e:
            pass

        # Handle errors that impact only single stream.
        except (StreamResetError, RefusedStream, StreamClosed) as e:
            pass

        except HTTP20Error:
            pass

    return handler
