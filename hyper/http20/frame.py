# -*- coding: utf-8 -*-
"""
hyper/http20/frame
~~~~~~~~~~~~~~~~~~

Defines framing logic for HTTP/2.0. Provides both classes to represent framed
data and logic for aiding the connection when it comes to reading from the
socket.
"""
class Frame(object):
    """
    The base class for all HTTP/2.0 frames.
    """
    # The flags defined on this type of frame.
    defined_flags = []

    # The type of the frame.
    type = 0

    def __init__(self, stream_id):
        self.stream_id = stream_id
        self.flags = set()

    def parse_flags(self, flag_byte):
        for flag, flag_bit in self.defined_flags:
            if flag_byte & flag_bit:
                self.flags.add(flag)

        return self.flags

    def serialize(self):
        raise NotImplementedError()

    def _get_len(self):
        raise NotImplementedError()
