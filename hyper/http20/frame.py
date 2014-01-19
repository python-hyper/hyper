# -*- coding: utf-8 -*-
"""
hyper/http20/frame
~~~~~~~~~~~~~~~~~~

Defines framing logic for HTTP/2.0. Provides both classes to represent framed
data and logic for aiding the connection when it comes to reading from the
socket.
"""
import struct

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

    def build_frame_header(self, length):
        # Build the common frame header.
        # First, get the flags.
        flags = 0

        for flag, flag_bit in self.defined_flags:
            if flag in self.flags:
                flags |= flag_bit

        header = struct.pack(
            "!HBBL",
            length & 0x3FFF,  # Length must have the top two bits unset.
            self.type,
            flags,
            self.stream_id & 0x7FFFFFFF  # Stream ID is 32 bits.
        )

        return header

    def serialize(self):
        raise NotImplementedError()

    def _get_len(self):
        raise NotImplementedError()


class DataFrame(Frame):
    """
    DATA frames convey arbitrary, variable-length sequences of octets
    associated with a stream. One or more DATA frames are used, for instance,
    to carry HTTP request or response payloads.
    """
    defined_flags = [('END_STREAM', 0x01)]

    type = 0

    def __init__(self, stream_id):
        super(DataFrame, self).__init__(stream_id)

        self.data = b''

        # Data frames may not be stream 0.
        if not self.stream_id:
            raise ValueError()

    def serialize(self):
        data = self.build_frame_header(len(self.data))
        data += self.data
        return data


class PriorityFrame(Frame):
    """
    The PRIORITY frame specifies the sender-advised priority of a stream. It
    can be sent at any time for an existing stream. This enables
    reprioritisation of existing streams.
    """

    defined_flags = []

    type = 0x02

    def __init__(self, stream_id):
        super(PriorityFrame, self).__init__(stream_id)

        self.priority = 0

        if not stream_id:
            raise ValueError()

    def serialize(self):
        data = self.build_frame_header(4)
        data += struct.pack("!L", self.priority & 0x7FFFFFFF)
        return data


# A map of type byte to frame class.
FRAMES = {
    0x00: DataFrame
}
