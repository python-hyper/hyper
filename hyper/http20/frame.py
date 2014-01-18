# -*- coding: utf-8 -*-
"""
hyper/http20/frame
~~~~~~~~~~~~~~~~~~

Defines framing logic for HTTP/2.0. Provides both classes to represent framed
data and logic for aiding the connection when it comes to reading from the
socket.
"""
import struct

# A map of type byte to frame class.
FRAMES = {
    0x00: DataFrame
}


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

    @staticmethod
    def parse_frame_header(header):
        """
        Takes an 8-byte frame header and returns a tuple of the appropriate
        Frame object and the length that needs to be read from the socket.
        """
        fields = struct.unpack("!HBBL", header)
        length = fields[0] & 0x3FFF
        type = fields[1]
        flags = fields[2]
        stream_id = fields[3]

        frame = FRAMES[type](stream_id)
        frame.parse_flags(flags)
        return (frame, length)

    def parse_flags(self, flag_byte):
        for flag, flag_bit in self.defined_flags:
            if flag_byte & flag_bit:
                self.flags.add(flag)

        return self.flags

    def serialize(self):
        raise NotImplementedError()

    def _get_len(self):
        raise NotImplementedError()
