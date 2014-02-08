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
from .frame import FRAME_MAX_LEN, HeadersFrame


# Define a set of states for a HTTP/2.0 stream.
STATE_IDLE               = 0
STATE_OPEN               = 1
STATE_HALF_CLOSED_LOCAL  = 2
STATE_HALF_CLOSED_REMOTE = 3
STATE_CLOSED             = 4


class Stream(object):
    """
    A single HTTP/2.0 stream.

    A stream is an independent, bi-directional sequence of HTTP headers and
    data. Each stream is identified by a single integer. From a HTTP
    perspective, a stream _approximately_ matches a single request-response
    pair.
    """
    def __init__(self, stream_id, data_cb, header_encoder, header_decoder):
        self.stream_id = stream_id
        self.state = STATE_IDLE
        self.headers = []
        self._queued_frames = []
        self._flow_control_window = 65535

        # This is the callback handed to the stream by its parent connection.
        # It is called when the stream wants to send data. It expects to
        # receive a list of frames that will be automatically serialized.
        self._data_cb = data_cb

        # A reference to the header encoder and decoder objects belonging to
        # the parent connection.
        self._encoder = header_encoder
        self._decoder = header_decoder

    def add_header(self, name, value):
        """
        Adds a single HTTP header to the headers to be sent on the request.
        """
        self.headers.append((name, value))

    def send_data(self, data, final):
        """
        Send some data on the stream. If this is the end of the data to be
        sent, the ``final`` flag _must_ be set to True. If no data is to be
        sent, set ``data`` to ``None``.
        """
        self.open(not data)

    def receive_frame(self, frame):
        """
        Handle a frame received on this stream.
        """
        pass

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
        # data needs to go into one HEADERS frame, followed by a nubmber of
        # CONTINUATION frames. For now, for ease of implementation, let's just
        # assume that's never going to happen (16kB of headers is lots!).
        if len(encoded_headers) > FRAME_MAX_LEN:
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
