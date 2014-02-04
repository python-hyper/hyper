# -*- coding: utf-8 -*-
"""
hyper/http20/frame
~~~~~~~~~~~~~~~~~~

Defines framing logic for HTTP/2.0. Provides both classes to represent framed
data and logic for aiding the connection when it comes to reading from the
socket.
"""
import struct

# The maximum length of a frame. Some frames have shorter maximum lengths.
FRAME_MAX_LEN = (2 ** 14) - 1


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

    def parse_body(self, data):
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

    def parse_body(self, data):
        self.data = data


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

    def parse_body(self, data):
        if len(data) != 4:
            raise ValueError()

        self.priority = struct.unpack("!L", data)[0]


class RstStreamFrame(Frame):
    """
    The RST_STREAM frame allows for abnormal termination of a stream. When sent
    by the initiator of a stream, it indicates that they wish to cancel the
    stream or that an error condition has occurred. When sent by the receiver
    of a stream, it indicates that either the receiver is rejecting the stream,
    requesting that the stream be cancelled or that an error condition has
    occurred.
    """
    defined_flags = []

    type = 0x03

    def __init__(self, stream_id):
        super(RstStreamFrame, self).__init__(stream_id)

        self.error_code = 0

        if not stream_id:
            raise ValueError()

    def serialize(self):
        data = self.build_frame_header(4)
        data += struct.pack("!L", self.error_code)
        return data

    def parse_body(self, data):
        if len(data) != 4:
            raise ValueError()

        self.error_code = struct.unpack("!L", data)[0]


class SettingsFrame(Frame):
    """
    The SETTINGS frame conveys configuration parameters that affect how
    endpoints communicate. The parameters are either constraints on peer
    behavior or preferences.

    Settings are not negotiated. Settings describe characteristics of the
    sending peer, which are used by the receiving peer. Different values for
    the same setting can be advertised by each peer. For example, a client
    might set a high initial flow control window, whereas a server might set a
    lower value to conserve resources.
    """
    defined_flags = [('ACK', 0x01)]

    type = 0x04

    # We need to define the known settings, they may as well be class
    # attributes.
    HEADER_TABLE_SIZE      = 0x01
    ENABLE_PUSH            = 0x02
    MAX_CONCURRENT_STREAMS = 0x04
    INITIAL_WINDOW_SIZE    = 0x07
    FLOW_CONTROL_OPTIONS   = 0x0A

    def __init__(self, stream_id):
        super(SettingsFrame, self).__init__(stream_id)

        # A dictionary of the setting type byte to the value.
        self.settings = {}

        if stream_id:
            raise ValueError()

    def serialize(self):
        # Each setting consumes 8 bytes.
        length = len(self.settings) * 8

        data = self.build_frame_header(length)

        for setting, value in self.settings.items():
            data += struct.pack("!LL", setting & 0x00FFFFFF, value)

        return data

    def parse_body(self, data):
        for i in range(0, len(data), 8):
            name, value = struct.unpack("!LL", data[i:i+8])
            self.settings[name] = value


class PushPromiseFrame(Frame):
    """
    The PUSH_PROMISE frame is used to notify the peer endpoint in advance of
    streams the sender intends to initiate.

    Right now hyper doesn't support these, so we treat the body data as totally
    opaque, along with the flags.
    """
    type = 0x05

    def __init__(self, stream_id):
        raise NotImplementedError("hyper doesn't support server push")


class PingFrame(Frame):
    """
    The PING frame is a mechanism for measuring a minimal round-trip time from
    the sender, as well as determining whether an idle connection is still
    functional. PING frames can be sent from any endpoint.
    """
    defined_flags = [('ACK', 0x01)]

    type = 0x06

    def __init__(self, stream_id):
        super(PingFrame, self).__init__(stream_id)

        self.opaque_data = b''

        if stream_id:
            raise ValueError()

    def serialize(self):
        if len(self.opaque_data) > 8:
            raise ValueError()

        data = self.build_frame_header(8)
        data += self.opaque_data
        data += b'\x00' * (8 - len(self.opaque_data))
        return data

    def parse_body(self, data):
        if len(data) > 8:
            raise ValueError()

        self.opaque_data = data


class GoAwayFrame(Frame):
    """
    The GOAWAY frame informs the remote peer to stop creating streams on this
    connection. It can be sent from the client or the server. Once sent, the
    sender will ignore frames sent on new streams for the remainder of the
    connection.
    """
    type = 0x07

    def __init__(self, stream_id):
        super(GoAwayFrame, self).__init__(stream_id)

        self.last_stream_id = 0
        self.error_code = 0
        self.additional_data = b''

        if stream_id:
            raise ValueError()

    def serialize(self):
        data = self.build_frame_header(8 + len(self.additional_data))
        data += struct.pack(
            "!LL",
            self.last_stream_id & 0x7FFFFFFF,
            self.error_code
        )
        data += self.additional_data

        return data

    def parse_body(self, data):
        self.last_stream_id, self.error_code = struct.unpack("!LL", data[:8])

        if len(data) > 8:
            self.additional_data = data[8:]


class WindowUpdateFrame(Frame):
    """
    The WINDOW_UPDATE frame is used to implement flow control.

    Flow control operates at two levels: on each individual stream and on the
    entire connection.

    Both types of flow control are hop by hop; that is, only between the two
    endpoints. Intermediaries do not forward WINDOW_UPDATE frames between
    dependent connections. However, throttling of data transfer by any receiver
    can indirectly cause the propagation of flow control information toward the
    original sender.
    """
    type = 0x09

    def __init__(self, stream_id):
        super(WindowUpdateFrame, self).__init__(stream_id)

        self.window_increment = 0

    def serialize(self):
        data = self.build_frame_header(4)
        data += struct.pack("!L", self.window_increment & 0x7FFFFFFF)

        return data

    def parse_body(self, data):
        self.window_increment = struct.unpack("!L", data)[0]


class HeadersFrame(DataFrame):
    """
    The HEADERS frame carries name-value pairs. It is used to open a stream.
    HEADERS frames can be sent on a stream in the "open" or "half closed
    (remote)" states.

    The HeadersFrame class is actually basically a data frame in this
    implementation, becuase of the requirement to control the sizes of frames.
    A header block fragment that doesn't fit in an entire HEADERS frame needs
    to be followed with CONTINUATION frames. From the perspective of the frame
    building code the header block is an opaque data segment.
    """
    type = 0x01

    defined_flags = [
        ('END_STREAM', 0x01),
        ('END_HEADERS', 0x04),
        ('PRIORITY', 0x08)
    ]

    def __init__(self, stream_id):
        super(HeadersFrame, self).__init__(stream_id)

        self.priority = None

    def serialize(self):
        if self.priority is None:
            data = self.build_frame_header(len(self.data))
        else:
            data = self.build_frame_header(len(self.data) + 4)
            data += struct.pack("!L", self.priority)

        data += self.data
        return data

    def parse_body(self, data):
        if 'PRIORITY' in self.flags:
            self.priority = struct.unpack("!L", data[:4])[0]
            data = data[4:]

        super(HeadersFrame, self).parse_body(data)


class ContinuationFrame(DataFrame):
    """
    The CONTINUATION frame is used to continue a sequence of header block
    fragments. Any number of CONTINUATION frames can be sent on an existing
    stream, as long as the preceding frame on the same stream is one of
    HEADERS, PUSH_PROMISE or CONTINUATION without the END_HEADERS or
    END_PUSH_PROMISE flag set.

    Much like the HEADERS frame, hyper treats this as an opaque data frame with
    different flags and a different type.
    """
    type = 0x0A

    defined_flags = [('END_HEADERS', 0x04)]


# A map of type byte to frame class.
FRAMES = {
    0x00: DataFrame,
    0x01: HeadersFrame,
    0x02: PriorityFrame,
    0x03: RstStreamFrame,
    0x04: SettingsFrame,
    0x05: PushPromiseFrame,
    0x06: PingFrame,
    0x07: GoAwayFrame,
    0x09: WindowUpdateFrame,
    0x0A: ContinuationFrame
}
