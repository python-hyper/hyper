# -*- coding: utf-8 -*-
"""
hyper/http20/frame
~~~~~~~~~~~~~~~~~~

Defines framing logic for HTTP/2.0. Provides both classes to represent framed
data and logic for aiding the connection when it comes to reading from the
socket.
"""
import collections
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
    type = None

    # If 'has-stream', the frame's stream_id must be non-zero. If 'no-stream',
    # it must be zero. If 'either', it's not checked.
    stream_association = None

    def __init__(self, stream_id):
        self.stream_id = stream_id
        self.flags = set()

        if self.stream_association == 'has-stream' and not self.stream_id:
            raise ValueError('Stream ID must be non-zero')
        if self.stream_association == 'no-stream' and self.stream_id:
            raise ValueError('Stream ID must be zero')

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
        body = self.serialize_body()

        # Build the common frame header.
        # First, get the flags.
        flags = 0

        for flag, flag_bit in self.defined_flags:
            if flag in self.flags:
                flags |= flag_bit

        header = struct.pack(
            "!HBBL",
            len(body) & 0x3FFF,  # Length must have the top two bits unset.
            self.type,
            flags,
            self.stream_id & 0x7FFFFFFF  # Stream ID is 32 bits.
        )

        return header + body

    def serialize_body(self):
        raise NotImplementedError()

    def parse_body(self, data):
        raise NotImplementedError()


class Padding(object):
    """
    Mixin for frames that contain padding.
    """
    def __init__(self, stream_id):
        self.data = b''
        self.low_padding = 0
        self.high_padding = 0

        super(Padding, self).__init__(stream_id)

    def serialize_padding_data(self):
        if 'PAD_LOW' in self.flags:
            if 'PAD_HIGH' in self.flags:
                return struct.pack('!BB', self.high_padding, self.low_padding)
            return struct.pack('!B', self.low_padding)
        return b''

    def parse_padding_data(self, data):
        if 'PAD_LOW' in self.flags:
            if 'PAD_HIGH' in self.flags:
                self.high_padding, self.low_padding = struct.unpack('!BB', data[:2])
                return 2
            self.low_padding = struct.unpack('!B', data[:1])[0]
            return 1
        return 0

    @property
    def total_padding(self):
        """Return the total length of the padding, if any."""
        return (self.high_padding << 8) + self.low_padding


class Priority(object):
    """
    Mixin for frames that contain priority data.
    """
    def __init__(self, stream_id):
        self.priority_group_id = None
        self.priority_group_weight = None
        self.stream_dependency_id = None
        self.stream_dependency_exclusive = None

        super(Priority, self).__init__(stream_id)

    def serialize_priority_data(self):
        if 'PRIORITY_GROUP' in self.flags:
            return struct.pack("!LB", self.priority_group_id, self.priority_group_weight)
        elif 'PRIORITY_DEPENDENCY' in self.flags:
            exclusive_bit = int(self.stream_dependency_exclusive) << 31
            return struct.pack("!L", self.stream_dependency_id | exclusive_bit)
        return b''

    def parse_priority_data(self, data):
        if 'PRIORITY_GROUP' in self.flags:
            self.priority_group_id, self.priority_group_weight = struct.unpack("!LB", data[:5])
            self.priority_group_id &= ~(1 << 31) # make sure reserved bit is ignored
            return 5
        elif 'PRIORITY_DEPENDENCY' in self.flags:
            self.stream_dependency_id = struct.unpack("!L", data[:4])[0]
            mask = 1 << 31
            self.stream_dependency_exclusive = bool(self.stream_dependency_id & mask)
            self.stream_dependency_id &= ~mask
            return 4
        return 0


class DataFrame(Padding, Frame):
    """
    DATA frames convey arbitrary, variable-length sequences of octets
    associated with a stream. One or more DATA frames are used, for instance,
    to carry HTTP request or response payloads.
    """
    defined_flags = [
        ('END_STREAM', 0x01),
        ('END_SEGMENT', 0x02),
        ('PAD_LOW', 0x08),
        ('PAD_HIGH', 0x10),
        ('PRIORITY_GROUP', 0x20),
        ('PRIORITY_DEPENDENCY', 0x40),
    ]

    type = 0x0

    stream_association = 'has-stream'

    def serialize_body(self):
        padding_data = self.serialize_padding_data()
        padding = b'\0' * self.total_padding
        return b''.join([padding_data, self.data, padding])

    def parse_body(self, data):
        padding_data_length = self.parse_padding_data(data)
        self.data = data[padding_data_length:len(data)-self.total_padding]


class PriorityFrame(Priority, Frame):
    """
    The PRIORITY frame specifies the sender-advised priority of a stream. It
    can be sent at any time for an existing stream. This enables
    reprioritisation of existing streams.
    """
    defined_flags = [('PRIORITY_GROUP', 0x20), ('PRIORITY_DEPENDENCY', 0x40)]

    type = 0x02

    stream_association = 'has-stream'

    def serialize_body(self):
        return self.serialize_priority_data()

    def parse_body(self, data):
        self.parse_priority_data(data)


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

    stream_association = 'has-stream'

    def __init__(self, stream_id):
        super(RstStreamFrame, self).__init__(stream_id)

        self.error_code = 0

    def serialize_body(self):
        return struct.pack("!L", self.error_code)

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

    stream_association = 'no-stream'

    # We need to define the known settings, they may as well be class
    # attributes.
    HEADER_TABLE_SIZE      = 0x01
    ENABLE_PUSH            = 0x02
    MAX_CONCURRENT_STREAMS = 0x03
    INITIAL_WINDOW_SIZE    = 0x04

    def __init__(self, stream_id):
        super(SettingsFrame, self).__init__(stream_id)

        # A dictionary of the setting type byte to the value.
        self.settings = {}

    def serialize_body(self):
        settings = [struct.pack("!BL", setting & 0xFF, value)
                    for setting, value in self.settings.items()]
        return b''.join(settings)

    def parse_body(self, data):
        for i in range(0, len(data), 5):
            name, value = struct.unpack("!BL", data[i:i+5])
            self.settings[name] = value


class PushPromiseFrame(Padding, Frame):
    """
    The PUSH_PROMISE frame is used to notify the peer endpoint in advance of
    streams the sender intends to initiate.
    """
    defined_flags = [('END_HEADERS', 0x04), ('PAD_LOW', 0x08), ('PAD_HIGH', 0x10)]

    type = 0x05

    stream_association = 'has-stream'

    def serialize_body(self):
        padding_data = self.serialize_padding_data()
        padding = b'\0' * self.total_padding
        data = struct.pack("!L", self.promised_stream_id)
        return b''.join([padding_data, data, self.data, padding])

    def parse_body(self, data):
        padding_data_length = self.parse_padding_data(data)
        data = data[padding_data_length:]
        self.promised_stream_id = struct.unpack("!L", data[:4])[0]
        self.data = data[4:]


class PingFrame(Frame):
    """
    The PING frame is a mechanism for measuring a minimal round-trip time from
    the sender, as well as determining whether an idle connection is still
    functional. PING frames can be sent from any endpoint.
    """
    defined_flags = [('ACK', 0x01)]

    type = 0x06

    stream_association = 'no-stream'

    def __init__(self, stream_id):
        super(PingFrame, self).__init__(stream_id)

        self.opaque_data = b''

    def serialize_body(self):
        if len(self.opaque_data) > 8:
            raise ValueError()

        data = self.opaque_data
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

    stream_association = 'no-stream'

    def __init__(self, stream_id):
        super(GoAwayFrame, self).__init__(stream_id)

        self.last_stream_id = 0
        self.error_code = 0
        self.additional_data = b''

    def serialize_body(self):
        data = struct.pack(
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
    type = 0x08

    stream_association = 'either'

    def __init__(self, stream_id):
        super(WindowUpdateFrame, self).__init__(stream_id)

        self.window_increment = 0

    def serialize_body(self):
        return struct.pack("!L", self.window_increment & 0x7FFFFFFF)

    def parse_body(self, data):
        self.window_increment = struct.unpack("!L", data)[0]


class HeadersFrame(Padding, Priority, Frame):
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

    stream_association = 'has-stream'

    defined_flags = [
        ('END_STREAM', 0x01),
        ('END_SEGMENT', 0x02),
        ('END_HEADERS', 0x04),
        ('PAD_LOW', 0x08),
        ('PAD_HIGH', 0x10),
        ('PRIORITY_GROUP', 0x20),
        ('PRIORITY_DEPENDENCY', 0x40),
    ]

    def serialize_body(self):
        padding_data = self.serialize_padding_data()
        padding = b'\0' * self.total_padding

        priority_data = self.serialize_priority_data()
        return b''.join([padding_data, priority_data, self.data, padding])

    def parse_body(self, data):
        padding_data_length = self.parse_padding_data(data)
        data = data[padding_data_length:]

        priority_data_length = self.parse_priority_data(data)
        self.data = data[priority_data_length:len(data)-self.total_padding]


class ContinuationFrame(Padding, Frame):
    """
    The CONTINUATION frame is used to continue a sequence of header block
    fragments. Any number of CONTINUATION frames can be sent on an existing
    stream, as long as the preceding frame on the same stream is one of
    HEADERS, PUSH_PROMISE or CONTINUATION without the END_HEADERS flag set.

    Much like the HEADERS frame, hyper treats this as an opaque data frame with
    different flags and a different type.
    """
    type = 0x09

    stream_association = 'has-stream'

    defined_flags = [('END_HEADERS', 0x04), ('PAD_LOW', 0x08), ('PAD_HIGH', 0x10)]

    def serialize_body(self):
        padding_data = self.serialize_padding_data()
        padding = b'\0' * self.total_padding
        return b''.join([padding_data, self.data, padding])

    def parse_body(self, data):
        padding_data_length = self.parse_padding_data(data)
        self.data = data[padding_data_length:len(data)-self.total_padding]


Origin = collections.namedtuple('Origin', ['scheme', 'host', 'port'])

class AltsvcFrame(Frame):
    """
    The ALTSVC frame is used to advertise alternate services that the current
    host, or a different one, can understand.
    """
    type = 0xA

    stream_association = 'no-stream'

    def __init__(self, stream_id):
        super(AltsvcFrame, self).__init__(stream_id)

        self.host = None
        self.port = None
        self.protocol_id = None
        self.max_age = None
        self.origin = None

    def serialize_body(self):
        first = struct.pack("!LHxB", self.max_age, self.port, len(self.protocol_id))
        host_length = struct.pack("!B", len(self.host))
        origin = b''
        if self.origin is not None:
            hostport = self.origin.host + b':' + str(self.origin.port).encode('ascii') if self.origin.port is not None else self.origin.host
            origin = self.origin.scheme + b'://' + hostport
        return b''.join([first, self.protocol_id, host_length, self.host, origin])

    def parse_body(self, data):
        self.max_age, self.port, protocol_id_length = struct.unpack("!LHxB", data[:8])
        pos = 8
        self.protocol_id = data[pos:pos+protocol_id_length]
        pos += protocol_id_length
        host_length = struct.unpack("!B", data[pos:pos+1])[0]
        pos += 1
        self.host = data[pos:pos+host_length]
        pos += host_length
        if pos != len(data):
            origin = data[pos:]
            scheme, hostport = origin.split(b'://')
            host, _, port = hostport.partition(b':')
            self.origin = Origin(scheme=scheme, host=host,
                                 port=int(port) if len(port) > 0 else None)


# A map of type byte to frame class.
_FRAME_CLASSES = [
    DataFrame,
    HeadersFrame,
    PriorityFrame,
    RstStreamFrame,
    SettingsFrame,
    PushPromiseFrame,
    PingFrame,
    GoAwayFrame,
    WindowUpdateFrame,
    ContinuationFrame,
    AltsvcFrame,
]
FRAMES = {cls.type: cls for cls in _FRAME_CLASSES}
