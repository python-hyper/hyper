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
        sent, the ``final`` flag _must_ be set to True.
        """
        pass

    def receive_frame(self, frame):
        """
        Handle a frame received on this stream.
        """
        pass
