# -*- coding: utf-8 -*-
"""
hyper/http20/exceptions
~~~~~~~~~~~~~~~~~~~~~~~

This defines exceptions used in the HTTP/2 portion of hyper.
"""

from . import errors

class HTTP20Error(Exception):
    """
    The base class for all of ``hyper``'s HTTP/2-related exceptions.
    """
    pass

class ConnectionError(HTTP20Error):
    """
    The remote party signalled an error affecting the entire HTTP/2
    connection, and the connection has been closed.
    """
    error_code = errors.CONNECT_ERROR


class ProtocolError(HTTP20Error):
    """
    The remote party violated the HTTP/2 protocol.
    """
    error_code = errors.PROTOCOL_ERROR


class FrameTooLargeError(ProtocolError):
    """
    The frame that we tried to send was too large to be sent.
    """
    error_code = errors.FRAME_SIZE_ERROR


class TooManyStreamsError(ProtocolError):
    """
    An attempt was made to open a stream that would lead to too many concurrent
    streams.
    """
    error_code = errors.ENHANCE_YOUR_CALM


class FlowControlError(ProtocolError):
    """
    An attempted action violates flow control constraints.
    """
    error_code = errors.FLOW_CONTROL_ERROR


class StreamError(HTTP20Error):
    """
    A error that only affects a specific stream.
    """
    def __init__(self, stream_id):
        self.stream_id = stream_id

    def __str__(self):
        return "StreamError:  Error on stream %d" % (self.stream_id)

class StreamIDTooLowError(StreamError):
    """
    An attempt was made to open a stream that had an ID that is lower than the
    highest ID we have seen on this connection.
    """
    def __init__(self, stream_id, max_stream_id):
        self.max_stream_id = max_stream_id
        super(StreamIDTooLowError, self).__init__(steam_id)

    def __str__(self):
        return "StreamIDTooLowError: %d is lower than %d" % (
            self.stream_id, self.max_stream_id
        )

class NoSuchStreamError(StreamError):
    """
    A stream-specific action referenced a stream that does not exist.
    """
    error_code = errors.STREAM_CLOSED

    def __init__(self, stream_id):
        super(NoSuchStreamError, self).__init__(steam_id)

    def __str__(self):
        return "NoSuchStreamError: Unexpected stream identifier %d" % (
            self.stream_id)
        )

class StreamClosedError(NoSuchStreamError):
    """
    A more specific form of
    :class:`NoSuchStreamError <h2.exceptions.NoSuchStreamError>`. Indicates
    that the stream has since been closed, and that all state relating to that
    stream has been removed.
    """
    error_code = errors.STREAM_CLOSED

    def __init__(self, stream_id):
        super(StreamClosedError, self).__init__(steam_id)

    def __str__(self):
        return "StreamClosedError: Stream has already been closed" % (
            self.stream_id)
        )

class StreamResetError(NoSuchStreamError):
    """
    A stream was forcefully reset by the remote party.
    """
    error_code = errors.CANCEL

    def __init__(self, stream_id):
        super(StreamResetError, self).__init__(steam_id)

    def __str__(self):
        return "Stream %s has been reset, dropping frame." % self.stream_id

def HTTP20ErrorHandler(func):
    """
    HTTP20Error exception handler which captures exceptions thrown
    that impact a single stream or the entire connection.
    """
    def handler(self, *args, **kwargs):
        try:
            self.func(*args, **kwargs)
        except (StreamError) as e:
            self._send_rst_frame(stream_id=e.stream_id, error_code=e.error_code['Code'])
        except (ProtocolError, ConnectionError, InternalError) as e:
            self.close(error_code=e.error_code['Code'])

    return handler
