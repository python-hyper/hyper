# -*- coding: utf-8 -*-
from hyper.http20.frame import (
    Frame, DataFrame, PriorityFrame, RstStreamFrame, SettingsFrame,
    PushPromiseFrame, PingFrame, GoAwayFrame, WindowUpdateFrame, HeadersFrame,
    ContinuationFrame,
)
from hyper.http20.hpack import Encoder, Decoder, encode_integer, decode_integer
import pytest


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

    @pytest.mark.xfail
    def test_request_examples_with_huffman(self):
        """
        This section shows the same examples as the previous section, but
        using Huffman encoding for the literal values.
        """
        e = Encoder()
        first_header_set = {
            ':method': 'GET',
            ':scheme': 'http',
            ':path': '/',
            ':authority': 'www.example.com'
        }
        first_result = (
            b'\x82\x87\x86\x04\x8b\xdb\x6d\x88\x3e\x68\xd1\xcb\x12\x25\xba\x7f'
        )

        assert e.encode(first_header_set, huffman=True) == first_result
        assert e.header_table == list(first_header_set.items())

        # This request takes advantage of the differential encoding of header
        # sets.
        second_header_set = {
            ':method': 'GET',
            ':scheme': 'http',
            ':path': '/',
            ':authority': 'www.example.com',
            'cache-control': 'no-cache'
        }
        second_result = b'\x1b\x86\x63\x65\x4a\x13\x98\xff'

        assert e.encode(second_header_set, huffman=True) == second_result
        assert e.header_table == (
            [('cache-control', 'no-cache')] + list(first_header_set.items())
        )

        # This request has not enough headers in common with the previous
        # request to take advantage of the differential encoding.  Therefore,
        # the reference set is emptied before encoding the header fields.
        third_header_set = {
            ':method': 'GET',
            ':scheme': 'https',
            ':path': '/index.html',
            ':authority': 'www.example.com',
            'custom-key': 'custom-value'
        }
        third_result = (
            b'\x80\x85\x8c\x8b\x84\x00\x88\x4e\xb0\x8b\x74\x97\x90\xfa\x7f\x89'
            b'\x4e\xb0\x8b\x74\x97\x9a\x17\xa8\xff'
        )

        assert e.encode(third_header_set, huffman=True) == third_result
        # Don't check the header table here, it's just too complex to be
        # reliable. Check its length though.
        assert len(e.header_table) == 8


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
        second_data = b'\x1b\x86\x63\x65\x4a\x13\x98\xff'

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
            b'\x80\x85\x8c\x8b\x84\x00\x88\x4e\xb0\x8b\x74\x97\x90\xfa\x7f\x89'
            b'\x4e\xb0\x8b\x74\x97\x9a\x17\xa8\xff'
        )

        assert d.decode(third_data) == set(third_header_set)
        # Don't check the header table here, it's just too complex to be
        # reliable. Check its length though.
        assert len(d.header_table) == 6


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
