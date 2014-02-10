# -*- coding: utf-8 -*-
from hyper.http20.frame import (
    Frame, DataFrame, PriorityFrame, RstStreamFrame, SettingsFrame,
    PushPromiseFrame, PingFrame, GoAwayFrame, WindowUpdateFrame, HeadersFrame,
    ContinuationFrame,
)
from hyper.http20.hpack import Encoder, Decoder, encode_integer, decode_integer
from hyper.http20.huffman import HuffmanDecoder
from hyper.http20.huffman_constants import REQUEST_CODES, REQUEST_CODES_LENGTH
from hyper.http20.connection import HTTP20Connection
from hyper.http20.stream import (
    Stream, STATE_HALF_CLOSED_LOCAL, STATE_OPEN, MAX_CHUNK, STATE_CLOSED
)
import pytest
from io import BytesIO


class TestGeneralFrameBehaviour(object):
    def test_base_frame_ignores_flags(self):
        f = Frame(0)
        flags = f.parse_flags(0xFF)
        assert not flags
        assert isinstance(flags, set)

    def test_base_frame_cant_serialize(self):
        f = Frame(0)
        with pytest.raises(NotImplementedError):
            f.serialize()


class TestDataFrame(object):
    def test_data_frame_has_only_one_flag(self):
        f = DataFrame(1)
        flags = f.parse_flags(0xFF)
        assert flags == set(['END_STREAM'])

    def test_data_frame_serializes_properly(self):
        f = DataFrame(1)
        f.flags = set(['END_STREAM'])
        f.data = b'testdata'

        s = f.serialize()
        assert s == b'\x00\x08\x00\x01\x00\x00\x00\x01testdata'

    def test_data_frame_parses_properly(self):
        s = b'\x00\x08\x00\x01\x00\x00\x00\x01testdata'
        f, length = Frame.parse_frame_header(s[:8])
        f.parse_body(s[8:8 + length])

        assert isinstance(f, DataFrame)
        assert f.flags == set(['END_STREAM'])
        assert f.data == b'testdata'


class TestPriorityFrame(object):
    def test_priority_frame_has_no_flags(self):
        f = PriorityFrame(1)
        flags = f.parse_flags(0xFF)
        assert not flags
        assert isinstance(flags, set)

    def test_priority_frame_serializes_properly(self):
        f = PriorityFrame(1)
        f.priority = 0xFF

        s = f.serialize()
        assert s == b'\x00\x04\x02\x00\x00\x00\x00\x01\x00\x00\x00\xff'

    def test_priority_frame_parses_properly(self):
        s = b'\x00\x04\x02\x00\x00\x00\x00\x01\x00\x00\x00\xff'
        f, length = Frame.parse_frame_header(s[:8])
        f.parse_body(s[8:8 + length])

        assert isinstance(f, PriorityFrame)
        assert f.flags == set()
        assert f.priority == 0xFF


class TestRstStreamFrame(object):
    def test_rst_stream_frame_has_no_flags(self):
        f = RstStreamFrame(1)
        flags = f.parse_flags(0xFF)
        assert not flags
        assert isinstance(flags, set)

    def test_rst_stream_frame_serializes_properly(self):
        f = RstStreamFrame(1)
        f.error_code = 420

        s = f.serialize()
        assert s == b'\x00\x04\x03\x00\x00\x00\x00\x01\x00\x00\x01\xa4'

    def test_rst_stream_frame_parses_properly(self):
        s = b'\x00\x04\x03\x00\x00\x00\x00\x01\x00\x00\x01\xa4'
        f, length = Frame.parse_frame_header(s[:8])
        f.parse_body(s[8:8 + length])

        assert isinstance(f, RstStreamFrame)
        assert f.flags == set()
        assert f.error_code == 420


class TestSettingsFrame(object):
    def test_settings_frame_has_only_one_flag(self):
        f = SettingsFrame(0)
        flags = f.parse_flags(0xFF)
        assert flags == set(['ACK'])

    def test_settings_frame_serializes_properly(self):
        f = SettingsFrame(0)
        f.parse_flags(0xFF)
        f.settings = {
            SettingsFrame.HEADER_TABLE_SIZE: 4096,
            SettingsFrame.ENABLE_PUSH: 0,
            SettingsFrame.MAX_CONCURRENT_STREAMS: 100,
            SettingsFrame.INITIAL_WINDOW_SIZE: 65535,
            SettingsFrame.FLOW_CONTROL_OPTIONS: 1,
        }

        s = f.serialize()
        assert s == (
            b'\x00\x28\x04\x01\x00\x00\x00\x00' +  # Frame header
            b'\x00\x00\x00\x01\x00\x00\x10\x00' +  # HEADER_TABLE_SIZE
            b'\x00\x00\x00\x02\x00\x00\x00\x00' +  # ENABLE_PUSH
            b'\x00\x00\x00\x04\x00\x00\x00\x64' +  # MAX_CONCURRENT_STREAMS
            b'\x00\x00\x00\x0A\x00\x00\x00\x01' +  # FLOW_CONTROL_OPTIONS
            b'\x00\x00\x00\x07\x00\x00\xFF\xFF'    # INITIAL_WINDOW_SIZE
        )

    def test_settings_frame_parses_properly(self):
        s = (
            b'\x00\x28\x04\x01\x00\x00\x00\x00' +  # Frame header
            b'\x00\x00\x00\x01\x00\x00\x10\x00' +  # HEADER_TABLE_SIZE
            b'\x00\x00\x00\x02\x00\x00\x00\x00' +  # ENABLE_PUSH
            b'\x00\x00\x00\x04\x00\x00\x00\x64' +  # MAX_CONCURRENT_STREAMS
            b'\x00\x00\x00\x0A\x00\x00\x00\x01' +  # FLOW_CONTROL_OPTIONS
            b'\x00\x00\x00\x07\x00\x00\xFF\xFF'    # INITIAL_WINDOW_SIZE
        )
        f, length = Frame.parse_frame_header(s[:8])
        f.parse_body(s[8:8 + length])

        assert isinstance(f, SettingsFrame)
        assert f.flags == set(['ACK'])
        assert f.settings == {
            SettingsFrame.HEADER_TABLE_SIZE: 4096,
            SettingsFrame.ENABLE_PUSH: 0,
            SettingsFrame.MAX_CONCURRENT_STREAMS: 100,
            SettingsFrame.INITIAL_WINDOW_SIZE: 65535,
            SettingsFrame.FLOW_CONTROL_OPTIONS: 1,
        }


class TestPushPromiseFrame(object):
    def test_push_promise_unsupported(self):
        with pytest.raises(NotImplementedError):
            f = PushPromiseFrame(1)


class TestPingFrame(object):
    def test_ping_frame_has_only_one_flag(self):
        f = PingFrame(0)
        flags = f.parse_flags(0xFF)

        assert flags == set(['ACK'])

    def test_ping_frame_serializes_properly(self):
        f = PingFrame(0)
        f.parse_flags(0xFF)
        f.opaque_data = b'\x01\x02'

        s = f.serialize()
        assert s == (
            b'\x00\x08\x06\x01\x00\x00\x00\x00\x01\x02\x00\x00\x00\x00\x00\x00'
        )

    def test_no_more_than_8_octets(self):
        f = PingFrame(0)
        f.opaque_data = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09'

        with pytest.raises(ValueError):
            f.serialize()

    def test_ping_frame_parses_properly(self):
        s = b'\x00\x08\x06\x01\x00\x00\x00\x00\x01\x02\x00\x00\x00\x00\x00\x00'
        f, length = Frame.parse_frame_header(s[:8])
        f.parse_body(s[8:8 + length])

        assert isinstance(f, PingFrame)
        assert f.flags == set(['ACK'])
        assert f.opaque_data == b'\x01\x02\x00\x00\x00\x00\x00\x00'


class TestGoAwayFrame(object):
    def test_go_away_has_no_flags(self):
        f = GoAwayFrame(0)
        flags = f.parse_flags(0xFF)

        assert not flags
        assert isinstance(flags, set)

    def test_goaway_serializes_properly(self):
        f = GoAwayFrame(0)
        f.last_stream_id = 64
        f.error_code = 32
        f.additional_data = b'hello'

        s = f.serialize()
        assert s == (
            b'\x00\x0D\x07\x00\x00\x00\x00\x00' +  # Frame header
            b'\x00\x00\x00\x40'                 +  # Last Stream ID
            b'\x00\x00\x00\x20'                 +  # Error Code
            b'hello'                               # Additional data
        )

    def test_goaway_frame_parses_properly(self):
        s = (
            b'\x00\x0D\x07\x00\x00\x00\x00\x00' +  # Frame header
            b'\x00\x00\x00\x40'                 +  # Last Stream ID
            b'\x00\x00\x00\x20'                 +  # Error Code
            b'hello'                               # Additional data
        )
        f, length = Frame.parse_frame_header(s[:8])
        f.parse_body(s[8:8 + length])

        assert isinstance(f, GoAwayFrame)
        assert f.flags == set()
        assert f.additional_data == b'hello'


class TestWindowUpdateFrame(object):
    def test_window_update_has_no_flags(self):
        f = WindowUpdateFrame(0)
        flags = f.parse_flags(0xFF)

        assert not flags
        assert isinstance(flags, set)

    def test_window_update_serializes_properly(self):
        f = WindowUpdateFrame(0)
        f.window_increment = 512

        s = f.serialize()
        assert s == b'\x00\x04\x09\x00\x00\x00\x00\x00\x00\x00\x02\x00'

    def test_windowupdate_frame_parses_properly(self):
        s = b'\x00\x04\x09\x00\x00\x00\x00\x00\x00\x00\x02\x00'
        f, length = Frame.parse_frame_header(s[:8])
        f.parse_body(s[8:8 + length])

        assert isinstance(f, WindowUpdateFrame)
        assert f.flags == set()
        assert f.window_increment == 512


class TestHeadersFrame(object):
    def test_headers_frame_flags(self):
        f = HeadersFrame(1)
        flags = f.parse_flags(0xFF)

        assert flags == set(['END_STREAM', 'END_HEADERS', 'PRIORITY'])

    def test_headers_frame_serialize_with_priority_properly(self):
        f = HeadersFrame(1)
        f.parse_flags(0xFF)
        f.priority = (2 ** 30) + 1
        f.data = b'hello world'

        s = f.serialize()
        assert s == (
            b'\x00\x0F\x01\x0D\x00\x00\x00\x01' +
            b'\x40\x00\x00\x01' +
            b'hello world'
        )

    def test_headers_frame_serialize_without_priority_properly(self):
        f = HeadersFrame(1)
        f.parse_flags(0xFF)
        f.data = b'hello world'

        s = f.serialize()
        assert s == (
            b'\x00\x0B\x01\x0D\x00\x00\x00\x01' +
            b'hello world'
        )

    def test_headers_frame_parses_properly(self):
        s = (
            b'\x00\x0F\x01\x0D\x00\x00\x00\x01' +
            b'\x40\x00\x00\x01' +
            b'hello world'
        )
        f, length = Frame.parse_frame_header(s[:8])
        f.parse_body(s[8:8 + length])

        assert isinstance(f, HeadersFrame)
        assert f.flags == set(['END_STREAM', 'END_HEADERS', 'PRIORITY'])
        assert f.priority == (2 ** 30) + 1
        assert f.data == b'hello world'


class TestContinuationFrame(object):
    def test_continuation_frame_flags(self):
        f = ContinuationFrame(1)
        flags = f.parse_flags(0xFF)

        assert flags == set(['END_HEADERS'])

    def test_continuation_frame_serializes(self):
        f = ContinuationFrame(1)
        f.parse_flags(0xFF)
        f.data = b'hello world'

        s = f.serialize()
        assert s == (
            b'\x00\x0B\x0A\x04\x00\x00\x00\x01' +
            b'hello world'
        )

    def test_continuation_frame_parses_properly(self):
        s = b'\x00\x0B\x0A\x04\x00\x00\x00\x01hello world'
        f, length = Frame.parse_frame_header(s[:8])
        f.parse_body(s[8:8 + length])

        assert isinstance(f, ContinuationFrame)
        assert f.flags == set(['END_HEADERS'])
        assert f.data == b'hello world'


class TestHPACKEncoder(object):
    # These tests are stolen entirely from the IETF specification examples.
    def test_literal_header_field_with_indexing(self):
        """
        The header field representation uses a literal name and a literal
        value.
        """
        e = Encoder()
        header_set = {'custom-key': 'custom-header'}
        result = b'\x00\x0acustom-key\x0dcustom-header'

        assert e.encode(header_set, huffman=False) == result
        assert e.header_table == [
            (n.encode('utf-8'), v.encode('utf-8')) for n, v in header_set.items()
        ]

    def test_literal_header_field_without_indexing(self):
        """
        The header field representation uses an indexed name and a literal
        value.
        """
        e = Encoder()
        header_set = {':path': '/sample/path'}
        result = b'\x44\x0c/sample/path'

        assert e.encode(header_set, huffman=False) == result
        assert e.header_table == []

    def test_indexed_header_field(self):
        """
        The header field representation uses an indexed header field, from
        the static table.  Upon using it, the static table entry is copied
        into the header table.
        """
        e = Encoder()
        header_set = {':method': 'GET'}
        result = b'\x82'

        assert e.encode(header_set, huffman=False) == result
        assert e.header_table == [
            (n.encode('utf-8'), v.encode('utf-8')) for n, v in header_set.items()
        ]

    def test_indexed_header_field_from_static_table(self):
        e = Encoder()
        e.header_table_size = 0
        header_set = {':method': 'GET'}
        result = b'\x82'

        assert e.encode(header_set, huffman=False) == result
        assert e.header_table == []

    def test_request_examples_without_huffman(self):
        """
        This section shows several consecutive header sets, corresponding to
        HTTP requests, on the same connection.
        """
        e = Encoder()
        first_header_set = [
            (':method', 'GET',),
            (':scheme', 'http',),
            (':path', '/',),
            (':authority', 'www.example.com'),
        ]
        # The first_header_table doesn't contain 'authority'
        first_header_table = first_header_set[::-1][1:]
        first_result = b'\x82\x87\x86\x44\x0fwww.example.com'

        assert e.encode(first_header_set, huffman=False) == first_result
        assert e.header_table == [
            (n.encode('utf-8'), v.encode('utf-8')) for n, v in first_header_table
        ]

        # This request takes advantage of the differential encoding of header
        # sets.
        second_header_set = [
            (':method', 'GET',),
            (':scheme', 'http',),
            (':path', '/',),
            (':authority', 'www.example.com',),
            ('cache-control', 'no-cache'),
        ]
        second_result = b'\x44\x0fwww.example.com\x5a\x08no-cache'

        assert e.encode(second_header_set, huffman=False) == second_result
        assert e.header_table == [
            (n.encode('utf-8'), v.encode('utf-8')) for n, v in first_header_table
        ]

        # This request has not enough headers in common with the previous
        # request to take advantage of the differential encoding.  Therefore,
        # the reference set is emptied before encoding the header fields.
        third_header_set = [
            (':method', 'GET',),
            (':scheme', 'https',),
            (':path', '/index.html',),
            (':authority', 'www.example.com',),
            ('custom-key', 'custom-value'),
        ]
        third_result = (
            b'\x80\x83\x8a\x89\x46\x0fwww.example.com' +
            b'\x00\x0acustom-key\x0ccustom-value'
        )

        assert e.encode(third_header_set, huffman=False) == third_result
        # Don't check the header table here, it's just too complex to be
        # reliable. Check its length though.
        assert len(e.header_table) == 6

    def test_request_examples_with_huffman(self):
        """
        This section shows the same examples as the previous section, but
        using Huffman encoding for the literal values.
        """
        e = Encoder()
        first_header_set = [
            (':method', 'GET',),
            (':scheme', 'http',),
            (':path', '/',),
            (':authority', 'www.example.com'),
        ]
        # The first_header_table doesn't contain 'authority'
        first_header_table = first_header_set[::-1][1:]
        first_result = (
            b'\x82\x87\x86\x44\x8b\xdb\x6d\x88\x3e\x68\xd1\xcb\x12\x25\xba\x7f'
        )

        assert e.encode(first_header_set, huffman=True) == first_result
        assert e.header_table == [
            (n.encode('utf-8'), v.encode('utf-8')) for n, v in first_header_table
        ]

        # This request takes advantage of the differential encoding of header
        # sets.
        second_header_set = [
            (':method', 'GET',),
            (':scheme', 'http',),
            (':path', '/',),
            (':authority', 'www.example.com',),
            ('cache-control', 'no-cache'),
        ]
        second_result = b'\x44\x8b\xdb\x6d\x88\x3e\x68\xd1\xcb\x12\x25\xba\x7f\x5a\x86\x63\x65\x4a\x13\x98\xff'

        assert e.encode(second_header_set, huffman=True) == second_result
        assert e.header_table == [
            (n.encode('utf-8'), v.encode('utf-8')) for n, v in first_header_table
        ]

        # This request has not enough headers in common with the previous
        # request to take advantage of the differential encoding.  Therefore,
        # the reference set is emptied before encoding the header fields.
        third_header_set = [
            (':method', 'GET',),
            (':scheme', 'https',),
            (':path', '/index.html',),
            (':authority', 'www.example.com',),
            ('custom-key', 'custom-value'),
        ]
        third_result = (
            b'\x80\x83\x8a\x89F\x8b\xdbm\x88>h\xd1\xcb\x12%\xba\x7f\x00\x88N'
            b'\xb0\x8bt\x97\x90\xfa\x7f\x89N\xb0\x8bt\x97\x9a\x17\xa8\xff'
        )

        assert e.encode(third_header_set, huffman=True) == third_result
        # Don't check the header table here, it's just too complex to be
        # reliable. Check its length though.
        assert len(e.header_table) == 6


class TestHPACKDecoder(object):
    # These tests are stolen entirely from the IETF specification examples.
    def test_literal_header_field_with_indexing(self):
        """
        The header field representation uses a literal name and a literal
        value.
        """
        d = Decoder()
        header_set = set([('custom-key', 'custom-header')])
        data = b'\x00\x0acustom-key\x0dcustom-header'

        assert d.decode(data) == header_set
        assert d.header_table == [
            (n.encode('utf-8'), v.encode('utf-8')) for n, v in header_set
        ]

    def test_literal_header_field_without_indexing(self):
        """
        The header field representation uses an indexed name and a literal
        value.
        """
        d = Decoder()
        header_set = set([(':path', '/sample/path')])
        data = b'\x44\x0c/sample/path'

        assert d.decode(data) == header_set
        assert d.header_table == []

    def test_indexed_header_field(self):
        """
        The header field representation uses an indexed header field, from
        the static table.  Upon using it, the static table entry is copied
        into the header table.
        """
        d = Decoder()
        header_set = set([(':method', 'GET')])
        data = b'\x82'

        assert d.decode(data) == header_set
        assert d.header_table == [
            (n.encode('utf-8'), v.encode('utf-8')) for n, v in header_set
        ]

    def test_request_examples_without_huffman(self):
        """
        This section shows several consecutive header sets, corresponding to
        HTTP requests, on the same connection.
        """
        d = Decoder()
        first_header_set = [
            (':method', 'GET',),
            (':scheme', 'http',),
            (':path', '/',),
            (':authority', 'www.example.com'),
        ]
        # The first_header_table doesn't contain 'authority'
        first_header_table = first_header_set[::-1][1:]
        first_data = b'\x82\x87\x86\x44\x0fwww.example.com'

        assert d.decode(first_data) == set(first_header_set)
        assert d.header_table == [
            (n.encode('utf-8'), v.encode('utf-8')) for n, v in first_header_table
        ]

        # This request takes advantage of the differential encoding of header
        # sets.
        second_header_set = [
            (':method', 'GET',),
            (':scheme', 'http',),
            (':path', '/',),
            (':authority', 'www.example.com',),
            ('cache-control', 'no-cache'),
        ]
        second_data = b'\x44\x0fwww.example.com\x5a\x08no-cache'

        assert d.decode(second_data) == set(second_header_set)
        assert d.header_table == [
            (n.encode('utf-8'), v.encode('utf-8')) for n, v in first_header_table
        ]

        # This request has not enough headers in common with the previous
        # request to take advantage of the differential encoding.  Therefore,
        # the reference set is emptied before encoding the header fields.
        third_header_set = [
            (':method', 'GET',),
            (':scheme', 'https',),
            (':path', '/index.html',),
            (':authority', 'www.example.com',),
            ('custom-key', 'custom-value'),
        ]
        third_data = (
            b'\x80\x83\x8a\x89\x46\x0fwww.example.com' +
            b'\x00\x0acustom-key\x0ccustom-value'
        )

        assert d.decode(third_data) == set(third_header_set)
        # Don't check the header table here, it's just too complex to be
        # reliable. Check its length though.
        assert len(d.header_table) == 6

    def test_request_examples_with_huffman(self):
        """
        This section shows the same examples as the previous section, but
        using Huffman encoding for the literal values.
        """
        d = Decoder()

        # Patch the decoder to use the Request Huffman tables, not the Response
        # ones.
        d.huffman_coder = HuffmanDecoder(REQUEST_CODES, REQUEST_CODES_LENGTH)
        first_header_set = [
            (':method', 'GET',),
            (':scheme', 'http',),
            (':path', '/',),
            (':authority', 'www.example.com'),
        ]
        first_header_table = first_header_set[::-1]
        first_data = (
            b'\x82\x87\x86\x04\x8b\xdb\x6d\x88\x3e\x68\xd1\xcb\x12\x25\xba\x7f'
        )

        assert d.decode(first_data) == set(first_header_set)
        assert d.header_table == [
            (n.encode('utf-8'), v.encode('utf-8')) for n, v in first_header_table
        ]

        # This request takes advantage of the differential encoding of header
        # sets.
        second_header_set = [
            (':method', 'GET',),
            (':scheme', 'http',),
            (':path', '/',),
            (':authority', 'www.example.com',),
            ('cache-control', 'no-cache'),
        ]
        second_header_table = second_header_set[::-1]
        second_data = b'\x1b\x86\x63\x65\x4a\x13\x98\xff'

        assert d.decode(second_data) == set(second_header_set)
        assert d.header_table == [
            (n.encode('utf-8'), v.encode('utf-8')) for n, v in second_header_table
        ]

        # This request has not enough headers in common with the previous
        # request to take advantage of the differential encoding.  Therefore,
        # the reference set is emptied before encoding the header fields.
        third_header_set = [
            (':method', 'GET',),
            (':scheme', 'https',),
            (':path', '/index.html',),
            (':authority', 'www.example.com',),
            ('custom-key', 'custom-value'),
        ]
        third_data = (
            b'\x80\x85\x8c\x8b\x84\x00\x88\x4e\xb0\x8b\x74\x97\x90\xfa\x7f\x89'
            b'\x4e\xb0\x8b\x74\x97\x9a\x17\xa8\xff'
        )

        assert d.decode(third_data) == set(third_header_set)
        # Don't check the header table here, it's just too complex to be
        # reliable. Check its length though.
        assert len(d.header_table) == 8


class TestIntegerEncoding(object):
    # These tests are stolen from the HPACK spec.
    def test_encoding_10_with_5_bit_prefix(self):
        val = encode_integer(10, 5)
        assert len(val) == 1
        assert val == bytearray(b'\x0a')

    def test_encoding_1337_with_5_bit_prefix(self):
        val = encode_integer(1337, 5)
        assert len(val) == 3
        assert val == bytearray(b'\x1f\x9a\x0a')

    def test_encoding_42_with_8_bit_prefix(self):
        val = encode_integer(42, 8)
        assert len(val) == 1
        assert val == bytearray(b'\x2a')


class TestIntegerDecoding(object):
    # These tests are stolen from the HPACK spec.
    def test_decoding_10_with_5_bit_prefix(self):
        val = decode_integer(b'\x0a', 5)
        assert val == (10, 1)

    def test_encoding_1337_with_5_bit_prefix(self):
        val = decode_integer(b'\x1f\x9a\x0a', 5)
        assert val == (1337, 3)

    def test_encoding_42_with_8_bit_prefix(self):
        val = decode_integer(b'\x2a', 8)
        assert val == (42, 1)


class TestHyperConnection(object):
    def test_connections_accept_hosts_and_ports(self):
        c = HTTP20Connection(host='www.google.com', port=8080)
        assert c.host =='www.google.com'
        assert c.port == 8080

    def test_connections_can_parse_hosts_and_ports(self):
        c = HTTP20Connection('www.google.com:8080')
        assert c.host == 'www.google.com'
        assert c.port == 8080

    def test_putrequest_establishes_new_stream(self):
        c = HTTP20Connection("www.google.com")

        stream_id = c.putrequest('GET', '/')
        stream = c.streams[stream_id]

        assert len(c.streams) == 1
        assert c.recent_stream is stream

    def test_putrequest_autosets_headers(self):
        c = HTTP20Connection("www.google.com")

        c.putrequest('GET', '/')
        s = c.recent_stream

        assert s.headers == [
            (':method', 'GET'),
            (':scheme', 'https'),
            (':authority', 'www.google.com'),
            (':path', '/'),
        ]

    def test_putheader_puts_headers(self):
        c = HTTP20Connection("www.google.com")

        c.putrequest('GET', '/')
        c.putheader('name', 'value')
        s = c.recent_stream

        assert s.headers == [
            (':method', 'GET'),
            (':scheme', 'https'),
            (':authority', 'www.google.com'),
            (':path', '/'),
            ('name', 'value'),
        ]

    def test_endheaders_sends_data(self):
        frames = []

        def data_callback(frame):
            frames.append(frame)

        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()
        c._send_cb = data_callback
        c.putrequest('GET', '/')
        c.endheaders()

        assert len(frames) == 1
        f = frames[0]
        assert isinstance(f, HeadersFrame)

    def test_we_can_send_data_using_endheaders(self):
        frames = []

        def data_callback(frame):
            frames.append(frame)

        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()
        c._send_cb = data_callback
        c.putrequest('GET', '/')
        c.endheaders(message_body=b'hello there', final=True)

        assert len(frames) == 2
        assert isinstance(frames[0], HeadersFrame)
        assert frames[0].flags == set(['END_HEADERS'])
        assert isinstance(frames[1], DataFrame)
        assert frames[1].data == b'hello there'
        assert frames[1].flags == set(['END_STREAM'])

    def test_that_we_correctly_send_over_the_socket(self):
        sock = DummySocket()
        c = HTTP20Connection('www.google.com')
        c._sock = sock
        c.putrequest('GET', '/')
        c.endheaders(message_body=b'hello there', final=True)

        # Don't bother testing that the serialization was ok, that should be
        # fine.
        assert len(sock.queue) == 2
        # Confirm the window got shrunk.
        assert c._out_flow_control_window == 65535 - len(b'hello there')

    def test_we_can_read_from_the_socket(self):
        sock = DummySocket()
        sock.buffer = BytesIO(b'\x00\x08\x00\x01\x00\x00\x00\x01testdata')

        c = HTTP20Connection('www.google.com')
        c._sock = sock
        c.putrequest('GET', '/')
        c.endheaders()
        c._recv_cb()

        s = c.recent_stream
        assert len(s._queued_frames) == 1
        assert isinstance(s._queued_frames[0], DataFrame)
        assert s._queued_frames[0].data == b'testdata'

    def test_putrequest_sends_data(self):
        sock = DummySocket()

        c = HTTP20Connection('www.google.com')
        c._sock = sock
        c.request(
            'GET',
            '/',
            body='hello',
            headers={'Content-Type': 'application/json'}
        )

        # The socket should have received one headers frame and one body frame.
        assert len(sock.queue) == 2
        assert c._out_flow_control_window == 65535 - len(b'hello')


class TestHyperStream(object):
    def test_streams_have_ids(self):
        s = Stream(1, None, None, None, None)
        assert s.stream_id == 1

    def test_streams_initially_have_no_headers(self):
        s = Stream(1, None, None, None, None)
        assert s.headers == []

    def test_streams_can_have_headers(self):
        s = Stream(1, None, None, None, None)
        s.add_header("name", "value")
        assert s.headers == [("name", "value")]

    def test_stream_opening_sends_headers(self):
        def data_callback(frame):
            assert isinstance(frame, HeadersFrame)
            assert frame.data == 'TestKeyTestVal'
            assert frame.flags == set(['END_STREAM', 'END_HEADERS'])

        s = Stream(1, data_callback, None, NullEncoder, None)
        s.add_header("TestKey", "TestVal")
        s.open(True)

        assert s.state == STATE_HALF_CLOSED_LOCAL

    def test_receiving_a_frame_queues_it(self):
        s = Stream(1, None, None, None, None)
        s.receive_frame(Frame(0))
        assert len(s._queued_frames) == 1

    def test_file_objects_can_be_sent(self):
        def data_callback(frame):
            assert isinstance(frame, DataFrame)
            assert frame.data == b'Hi there!'
            assert frame.flags == set(['END_STREAM'])

        s = Stream(1, data_callback, None, NullEncoder, None)
        s.state = STATE_OPEN
        s.send_data(BytesIO(b'Hi there!'), True)

        assert s.state == STATE_HALF_CLOSED_LOCAL
        assert s._out_flow_control_window == 65535 - len(b'Hi there!')

    def test_large_file_objects_are_broken_into_chunks(self):
        frame_count = [0]
        recent_frame = [None]

        def data_callback(frame):
            assert isinstance(frame, DataFrame)
            assert len(frame.data) <= MAX_CHUNK
            frame_count[0] += 1
            recent_frame[0] = frame

        data = b'test' * (MAX_CHUNK + 1)

        s = Stream(1, data_callback, None, NullEncoder, None)
        s.state = STATE_OPEN
        s.send_data(BytesIO(data), True)

        assert s.state == STATE_HALF_CLOSED_LOCAL
        assert recent_frame[0].flags == set(['END_STREAM'])
        assert frame_count[0] == 5
        assert s._out_flow_control_window == 65535 - len(data)

    def test_bytestrings_can_be_sent(self):
        def data_callback(frame):
            assert isinstance(frame, DataFrame)
            assert frame.data == b'Hi there!'
            assert frame.flags == set(['END_STREAM'])

        s = Stream(1, data_callback, None, NullEncoder, None)
        s.state = STATE_OPEN
        s.send_data(b'Hi there!', True)

        assert s.state == STATE_HALF_CLOSED_LOCAL
        assert s._out_flow_control_window == 65535 - len(b'Hi there!')

    def test_long_bytestrings_are_split(self):
        frame_count = [0]
        recent_frame = [None]

        def data_callback(frame):
            assert isinstance(frame, DataFrame)
            assert len(frame.data) <= MAX_CHUNK
            frame_count[0] += 1
            recent_frame[0] = frame

        data = b'test' * (MAX_CHUNK + 1)

        s = Stream(1, data_callback, None, NullEncoder, None)
        s.state = STATE_OPEN
        s.send_data(data, True)

        assert s.state == STATE_HALF_CLOSED_LOCAL
        assert recent_frame[0].flags == set(['END_STREAM'])
        assert frame_count[0] == 5
        assert s._out_flow_control_window == 65535 - len(data)

    def test_windowupdate_frames_update_windows(self):
        s = Stream(1, None, None, None, None)
        f = WindowUpdateFrame(1)
        f.window_increment = 1000
        s.receive_frame(f)

        assert s._out_flow_control_window == 65535 + 1000

    def test_stream_reading_works(self):
        out_frames = []
        in_frames = []

        def send_cb(frame):
            out_frames.append(frame)

        def recv_cb(s):
            def inner():
                s.receive_frame(in_frames.pop(0))
            return inner

        s = Stream(1, send_cb, None, None, None)
        s._recv_cb = recv_cb(s)
        s.state = STATE_HALF_CLOSED_LOCAL

        # Provide a data frame to read.
        f = DataFrame(1)
        f.data = b'hi there!'
        f.flags.add('END_STREAM')
        in_frames.append(f)

        data = s._read()
        assert data == b'hi there!'
        assert len(out_frames) == 0

    def test_can_read_multiple_frames_from_streams(self):
        out_frames = []
        in_frames = []

        def send_cb(frame):
            out_frames.append(frame)

        def recv_cb(s):
            def inner():
                s.receive_frame(in_frames.pop(0))
            return inner

        s = Stream(1, send_cb, None, None, None)
        s._recv_cb = recv_cb(s)
        s.state = STATE_HALF_CLOSED_LOCAL

        # Provide two data frames to read.
        f = DataFrame(1)
        f.data = b'hi there!'
        in_frames.append(f)

        f = DataFrame(1)
        f.data = b'hi there again!'
        f.flags.add('END_STREAM')
        in_frames.append(f)

        data = s._read()
        assert data == b'hi there!hi there again!'
        assert len(out_frames) == 1
        assert isinstance(out_frames[0], WindowUpdateFrame)
        assert out_frames[0].window_increment == len(b'hi there!')

    def test_partial_reads_from_streams(self):
        out_frames = []
        in_frames = []

        def send_cb(frame):
            out_frames.append(frame)

        def recv_cb(s):
            def inner():
                s.receive_frame(in_frames.pop(0))
            return inner

        s = Stream(1, send_cb, None, None, None)
        s._recv_cb = recv_cb(s)
        s.state = STATE_HALF_CLOSED_LOCAL

        # Provide two data frames to read.
        f = DataFrame(1)
        f.data = b'hi there!'
        in_frames.append(f)

        f = DataFrame(1)
        f.data = b'hi there again!'
        f.flags.add('END_STREAM')
        in_frames.append(f)

        # We'll get the entire first frame.
        data = s._read(4)
        assert data == b'hi there!'
        assert len(out_frames) == 1

        # Now we'll get the entire of the second frame.
        data = s._read(4)
        assert data == b'hi there again!'
        assert len(out_frames) == 1
        assert s.state == STATE_CLOSED

# Some utility classes for the tests.
class NullEncoder(object):
    def encode(headers):
        return '\n'.join("%s%s" % (name, val) for name, val in headers)

class DummySocket(object):
    def __init__(self):
        self.queue = []
        self.buffer = BytesIO()

    def send(self, data):
        self.queue.append(data)

    def recv(self, l):
        return self.buffer.read(l)
