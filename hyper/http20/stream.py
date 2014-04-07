# -*- coding: utf-8 -*-
"""
hyper/http20/stream
~~~~~~~~~~~~~~~~~~~

Objects that make up the stream-level abstraction of hyper's HTTP/2.0 support.

These objects are not expected to be part of the public HTTP/2.0 API: they're
intended purely for use inside hyper's HTTP/2.0 abstraction.

Conceptually, a single HTTP/2.0 connection is made up of many streams: each
stream is an independent, bi-directional sequence of HTTP headers and data.
Each stream is identified by a monotonically increasing integer, assigned to
the stream by the endpoint that initiated the stream.
"""
from .frame import (
    FRAME_MAX_LEN, HeadersFrame, DataFrame, WindowUpdateFrame,
    ContinuationFrame,
)
from .response import HTTP20Response
from .util import get_from_key_value_set
import collections


# Define a set of states for a HTTP/2.0 stream.
STATE_IDLE               = 0
STATE_OPEN               = 1
STATE_HALF_CLOSED_LOCAL  = 2
STATE_HALF_CLOSED_REMOTE = 3
STATE_CLOSED             = 4


# Define the largest chunk of data we'll send in one go. Realistically, we
# should take the MSS into account but that's pretty dull, so let's just say
# 1kB and call it a day.
MAX_CHUNK = 1024


class Stream(object):
    """
    A single HTTP/2.0 stream.

    A stream is an independent, bi-directional sequence of HTTP headers and
    data. Each stream is identified by a single integer. From a HTTP
    perspective, a stream _approximately_ matches a single request-response
    pair.
    """
    def __init__(self,
                 stream_id,
                 data_cb,
                 recv_cb,
                 close_cb,
                 header_encoder,
                 header_decoder,
                 window_manager):
        self.stream_id = stream_id
        self.state = STATE_IDLE
        self.headers = []

        self.response_headers = None
        self.header_data = []
        self.data = []

        # There are two flow control windows: one for data we're sending,
        # one for data being sent to us.
        self._in_window_manager = window_manager
        self._out_flow_control_window = 65535

        # This is the callback handed to the stream by its parent connection.
        # It is called when the stream wants to send data. It expects to
        # receive a list of frames that will be automatically serialized.
        self._data_cb = data_cb

        # Similarly, this is a callback that reads one frame off the
        # connection.
        self._recv_cb = recv_cb

        # This is the callback to be called when the stream is closed.
        self._close_cb = close_cb

        # A reference to the header encoder and decoder objects belonging to
        # the parent connection.
        self._encoder = header_encoder
        self._decoder = header_decoder

    def add_header(self, name, value):
        """
        Adds a single HTTP header to the headers to be sent on the request.
        """
        self.headers.append((name.lower(), value))

    def send_data(self, data, final):
        """
        Send some data on the stream. If this is the end of the data to be
        sent, the ``final`` flag _must_ be set to True. If no data is to be
        sent, set ``data`` to ``None``.
        """
        # Define a utility iterator for file objects.
        def file_iterator(fobj):
            while True:
                data = fobj.read(MAX_CHUNK)
                yield data
                if len(data) < MAX_CHUNK:
                    break

        # Build the appropriate iterator for the data, in chunks of CHUNK_SIZE.
        if hasattr(data, 'read'):
            chunks = file_iterator(data)
        else:
            chunks = (data[i:i+MAX_CHUNK]
                      for i in range(0, len(data), MAX_CHUNK))

        for chunk in chunks:
            self._send_chunk(chunk, final)

    @property
    def _local_closed(self):
        return self.state in (STATE_CLOSED, STATE_HALF_CLOSED_LOCAL)

    @property
    def _remote_closed(self):
        return self.state in (STATE_CLOSED, STATE_HALF_CLOSED_REMOTE)

    @property
    def _local_open(self):
        return self.state in (STATE_OPEN, STATE_HALF_CLOSED_REMOTE)

    @property
    def _remote_open(self):
        return self.state in (STATE_OPEN, STATE_HALF_CLOSED_LOCAL)

    def _close_local(self):
        self.state = (
            STATE_HALF_CLOSED_LOCAL if self.state == STATE_OPEN
            else STATE_CLOSED
        )

    def _close_remote(self):
        self.state = (
            STATE_HALF_CLOSED_REMOTE if self.state == STATE_OPEN
            else STATE_CLOSED
        )

    def _read(self, amt=None):
        """
        Read data from the stream. Unlike a normal read behaviour, this
        function returns _at least_ ``amt`` data, but may return more.
        """
        if self.state == STATE_CLOSED:
            return b''

        assert self._remote_open

        def listlen(list):
            return sum(map(len, list))

        # Keep reading until the stream is closed or we get enough data.
        while not self._remote_closed and (amt is None or listlen(self.data) < amt):
            self._recv_cb()

        result = b''.join(self.data)
        self.data = []
        return result

    def receive_frame(self, frame):
        """
        Handle a frame received on this stream.
        """
        if isinstance(frame, WindowUpdateFrame):
            self._out_flow_control_window += frame.window_increment
        elif isinstance(frame, (HeadersFrame, ContinuationFrame)):
            self.header_data.append(frame.data)
        elif isinstance(frame, DataFrame):
            # Append the data to the buffer.
            self.data.append(frame.data)

            # Increase the window size. Only do this if the data frame contains
            # actual data.
            increment = self._in_window_manager._handle_frame(len(frame.data))
            if increment:
                w = WindowUpdateFrame(self.stream_id)
                w.window_increment = increment
                self._data_cb(w)
        else: # pragma: no cover
            raise ValueError('Unexpected frame type: %i' % frame.type)

        if 'END_HEADERS' in frame.flags:
            self.response_headers = self._decoder.decode(b''.join(self.header_data))

        if 'END_STREAM' in frame.flags:
            self._close_remote()

    def open(self, end):
        """
        Open the stream. Does this by encoding and sending the headers: no more
        calls to ``add_header`` are allowed after this method is called.
        The `end` flag controls whether this will be the end of the stream, or
        whether data will follow.
        """
        # Encode the headers.
        encoded_headers = self._encoder.encode(self.headers)

        # It's possible that there is a substantial amount of data here. The
        # data needs to go into one HEADERS frame, followed by a number of
        # CONTINUATION frames. For now, for ease of implementation, let's just
        # assume that's never going to happen (16kB of headers is lots!).
        # Additionally, since this is so unlikely, there's no point writing a
        # test for this: it's just so simple.
        if len(encoded_headers) > FRAME_MAX_LEN:  # pragma: no cover
            raise ValueError("Header block too large.")

        header_frame = HeadersFrame(self.stream_id)
        header_frame.data = encoded_headers

        # If no data has been provided, this is the end of the stream. Either
        # way, due to the restriction above it's definitely the end of the
        # headers.
        header_frame.flags.add('END_HEADERS')

        if end:
            header_frame.flags.add('END_STREAM')

        # Send the header frame.
        self._data_cb(header_frame)

        # Transition the stream state appropriately.
        self.state = STATE_HALF_CLOSED_LOCAL if end else STATE_OPEN

        return

    def getresponse(self):
        """
        Once all data has been sent on this connection, returns a
        HTTP20Response object wrapping this stream.
        """
        assert self._local_closed

        # Keep reading until all headers are received.
        while self.response_headers is None:
            self._recv_cb()

        # Find the Content-Length header if present.
        self._in_window_manager.document_size = (
            int(get_from_key_value_set(self.response_headers, 'content-length', 0))
        )

        # Create the HTTP response.
        return HTTP20Response(self.response_headers, self)

    def close(self):
        """
        Closes the stream. If the stream is currently open, attempts to close
        it as gracefully as possible.

        :returns: Nothing.
        """
        # Right now let's not bother with grace, let's just call close on the
        # connection.
        self._close_cb(self.stream_id)

    def _send_chunk(self, data, final):
        """
        Implements most of the sending logic.

        Takes a single chunk of size at most MAX_CHUNK, wraps it in a frame and
        sends it. Optionally sets the END_STREAM flag if this is the last chunk
        (determined by being of size less than MAX_CHUNK) and no more data is
        to be sent.
        """
        assert self._local_open

        f = DataFrame(self.stream_id)
        f.data = data

        # If the length of the data is less than MAX_CHUNK, we're probably
        # at the end of the file. If this is the end of the data, mark it
        # as END_STREAM.
        if len(data) < MAX_CHUNK and final:
            f.flags.add('END_STREAM')

        # If we don't fit in the connection window, try popping frames off the
        # connection in hope that one might be a Window Update frame.
        while len(data) > self._out_flow_control_window:
            self._recv_cb()

        # Send the frame and decrement the flow control window.
        self._data_cb(f)
        self._out_flow_control_window -= len(data)

        # If no more data is to be sent on this stream, transition our state.
        if len(data) < MAX_CHUNK and final:
            self._close_local()
