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
from hyper.http20.response import HTTP20Response
from hyper.http20.exceptions import HPACKDecodingError, HPACKEncodingError
from hyper.http20.window import FlowControlManager
from hyper.compat import zlib_compressobj
from hyper.contrib import HTTP20Adapter
import errno
import pytest
import socket
import zlib
from io import BytesIO


def decode_frame(frame_data):
    f, length = Frame.parse_frame_header(frame_data[:8])
    f.parse_body(frame_data[8:8 + length])
    assert 8 + length == len(frame_data)
    return f


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

    def test_base_frame_cant_parse_body(self):
        data = b''
        f = Frame(0)
        with pytest.raises(NotImplementedError):
            f.parse_body(data)


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

    def test_data_frame_comes_on_a_stream(self):
        with pytest.raises(ValueError):
            DataFrame(0)


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

    def test_priority_frame_comes_on_a_stream(self):
        with pytest.raises(ValueError):
            PriorityFrame(0)

    def test_priority_frame_must_have_body_length_four(self):
        f = PriorityFrame(1)
        with pytest.raises(ValueError):
            f.parse_body(b'\x01')

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

    def test_rst_stream_frame_comes_on_a_stream(self):
        with pytest.raises(ValueError):
            RstStreamFrame(0)

    def test_rst_stream_frame_must_have_body_length_four(self):
        f = RstStreamFrame(1)
        with pytest.raises(ValueError):
            f.parse_body(b'\x01')


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

    def test_settings_frames_never_have_streams(self):
        with pytest.raises(ValueError):
            SettingsFrame(1)


class TestPushPromiseFrame(object):
    def test_push_promise_frame_flags(self):
        f = PushPromiseFrame(1)
        flags = f.parse_flags(0xFF)

        assert flags == set(['END_PUSH_PROMISE'])

    def test_push_promise_frame_serialize_with_priority_properly(self):
        f = PushPromiseFrame(1)
        f.parse_flags(0xFF)
        f.promised_stream_id = 4
        f.data = b'hello world'

        s = f.serialize()
        assert s == (
            b'\x00\x0F\x05\x01\x00\x00\x00\x01' +
            b'\x00\x00\x00\x04' +
            b'hello world'
        )

    def test_push_promise_frame_parses_properly(self):
        s = (
            b'\x00\x0F\x05\x0D\x00\x00\x00\x01' +
            b'\x00\x00\x00\x04' +
            b'hello world'
        )
        f, length = Frame.parse_frame_header(s[:8])
        f.parse_body(s[8:8 + length])

        assert isinstance(f, PushPromiseFrame)
        assert f.flags == set(['END_PUSH_PROMISE'])
        assert f.promised_stream_id == 4
        assert f.data == b'hello world'


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

    def test_ping_frame_never_has_a_stream(self):
        with pytest.raises(ValueError):
            PingFrame(1)

    def test_ping_frame_has_no_more_than_body_length_8(self):
        f = PingFrame(0)
        with pytest.raises(ValueError):
            f.parse_body(b'\x01\x02\x03\x04\x05\x06\x07\x08\x09')


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

    def test_goaway_frame_never_has_a_stream(self):
        with pytest.raises(ValueError):
            GoAwayFrame(1)


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


class TestHuffmanDecoder(object):
    def test_huffman_decoder_throws_useful_exceptions(self):
        # Specify a HuffmanDecoder with no values in it, then attempt to decode
        # using it.
        d = HuffmanDecoder([], [])
        with pytest.raises(HPACKDecodingError):
            d.decode(b'test')


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
        assert list(e.header_table) == [
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
        assert list(e.header_table) == []

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
        assert list(e.header_table) == [
            (n.encode('utf-8'), v.encode('utf-8')) for n, v in header_set.items()
        ]

    def test_indexed_header_field_from_static_table(self):
        e = Encoder()
        e.header_table_size = 0
        header_set = {':method': 'GET'}
        result = b'\x82'

        assert e.encode(header_set, huffman=False) == result
        assert list(e.header_table) == []

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
        assert list(e.header_table) == [
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
        assert list(e.header_table) == [
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
            b'\x80\x80\x83\x8a\x89\x46\x0fwww.example.com' +
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
        assert list(e.header_table) == [
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
        assert list(e.header_table) == [
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
            b'\x80\x80\x83\x8a\x89F\x8b\xdbm\x88>h\xd1\xcb\x12%\xba\x7f\x00\x88'
            b'N\xb0\x8bt\x97\x90\xfa\x7f\x89N\xb0\x8bt\x97\x9a\x17\xa8\xff'
        )

        assert e.encode(third_header_set, huffman=True) == third_result
        # Don't check the header table here, it's just too complex to be
        # reliable. Check its length though.
        assert len(e.header_table) == 6

    # These tests are custom, for hyper.
    def test_resizing_header_table(self):
        # We need to encode a substantial number of headers, to populate the
        # header table.
        e = Encoder()
        header_set = [
            (':method', 'GET'),
            (':scheme', 'https'),
            (':path', '/some/path'),
            (':authority', 'www.example.com'),
            ('custom-key', 'custom-value'),
            ("user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:16.0) Gecko/20100101 Firefox/16.0"),
            ("accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
            ('X-Lukasa-Test', '88989'),
        ]
        e.encode(header_set, huffman=True)

        # Resize the header table to a size so small that nothing can be in it.
        e.header_table_size = 40
        assert len(e.header_table) == 0

    def test_removing_header_partially_in_table(self):
        e = Encoder()
        e.encode([('no', 'value')])

        with pytest.raises(HPACKEncodingError):
            e.remove([(b'no', b'val')])

    def test_removing_header_not_in_table_at_all(self):
        e = Encoder()

        with pytest.raises(HPACKEncodingError):
            e.remove([(b'not', b'present')])


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
        assert list(d.header_table) == [
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
        assert list(d.header_table) == []

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
        assert list(d.header_table) == [
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
        assert list(d.header_table) == [
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
        assert list(d.header_table) == [
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
            b'\x80\x80\x83\x8a\x89\x46\x0fwww.example.com' +
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
        assert list(d.header_table) == [
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
        assert list(d.header_table) == [
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
            b'\x80\x80\x85\x8c\x8b\x84\x00\x88\x4e\xb0\x8b\x74\x97\x90\xfa\x7f\x89'
            b'\x4e\xb0\x8b\x74\x97\x9a\x17\xa8\xff'
        )

        assert d.decode(third_data) == set(third_header_set)
        # Don't check the header table here, it's just too complex to be
        # reliable. Check its length though.
        assert len(d.header_table) == 8

    # These tests are custom, for hyper.
    def test_resizing_header_table(self):
        # We need to decode a substantial number of headers, to populate the
        # header table. This string isn't magic: it's the output from the
        # equivalent test for the Encoder.
        d = Decoder()
        data = (
            b'\x82\x88F\x87\x087A\x07"9\xffC\x8b\xdbm\x88>h\xd1\xcb\x12%' +
            b'\xba\x7f\x00\x88N\xb0\x8bt\x97\x90\xfa\x7f\x89N\xb0\x8bt\x97\x9a' +
            b'\x17\xa8\xff|\xbe\xefo\xaa\x96\xb4\x05\x04/G\xfa\xefBT\xc8\xb6' +
            b'\x19\xf5t|\x19\x11_Gz\x13\xd1\xf4\xf0\xe8\xfd\xf4\x18\xa4\xaf' +
            b'\xab\xa1\xfc\xfd\x86\xa4\x85\xff}\x1e\xe1O&\x81\xcab\x94\xc57G' +
            b'\x05<qo\x98\x1a\x92\x17U\xaf\x88\xf9\xc43\x8e\x8b\xe9C\x9c\xb5' +
            b'%\x11SX\x1ey\xc7E\xff\xcf=\x17\xd2\x879jJ"\xa6\xb0<\xf4_W\x95' +
            b'\xa5%\x9d?\xd0\x7f]^V\x94\x95\xff\x00\x8a\xfd\xcb\xf2\xd7\x92 ' +
            b'\x89|F\x11\x84\xae\xbb+\xb3'
        )
        d.decode(data)

        # Resize the header table to a size so small that nothing can be in it.
        d.header_table_size = 40
        assert len(d.header_table) == 0


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
        assert s.data == [b'testdata']

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

    def test_closed_connections_are_reset(self):
        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()
        encoder = c.encoder
        decoder = c.decoder
        wm = c.window_manager
        c.request('GET', '/')
        c.close()

        assert c._sock is None
        assert not c.streams
        assert c.recent_stream is None
        assert c.next_stream_id == 1
        assert c.encoder is not encoder
        assert c.decoder is not decoder
        assert c._settings == {
            SettingsFrame.INITIAL_WINDOW_SIZE: 65535,
        }
        assert c._out_flow_control_window == 65535
        assert c.window_manager is not wm

    def test_connection_doesnt_send_window_update_on_zero_length_data_frame(self):
        # Prepare a socket with a data frame in it that has no length.
        sock = DummySocket()
        sock.buffer = BytesIO(DataFrame(1).serialize())
        c = HTTP20Connection('www.google.com')
        c._sock = sock

        # We open a request here just to allocate a stream, but we throw away
        # the frames it sends.
        c.request('GET', '/')
        sock.queue = []

        # Read the frame.
        c._recv_cb()

        # No frame should have been sent on the connection.
        assert len(sock.queue) == 0

    def test_streams_are_cleared_from_connections_on_close(self):
        # Prepare a socket so we can open a stream.
        sock = DummySocket()
        c = HTTP20Connection('www.google.com')
        c._sock = sock

        # Open a request (which creates a stream)
        c.request('GET', '/')

        # Close the stream.
        c.streams[1].close()

        # There should be nothing left, but the next stream ID should be
        # unchanged.
        assert not c.streams
        assert c.next_stream_id == 3

    def test_connections_increment_send_window_properly(self):
        f = WindowUpdateFrame(0)
        f.window_increment = 1000
        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()

        # 'Receive' the WINDOWUPDATE frame.
        c.receive_frame(f)

        assert c._out_flow_control_window == 65535 + 1000

    def test_connections_handle_resizing_header_tables_properly(self):
        sock = DummySocket()
        f = SettingsFrame(0)
        f.settings[SettingsFrame.HEADER_TABLE_SIZE] = 1024
        c = HTTP20Connection('www.google.com')
        c._sock = sock

        # 'Receive' the SETTINGS frame.
        c.receive_frame(f)

        # Confirm that the setting is stored and the header table shrunk.
        assert c._settings[SettingsFrame.HEADER_TABLE_SIZE] == 1024
        assert c.encoder.header_table_size == 1024

        # Confirm we got a SETTINGS ACK.
        f2 = decode_frame(sock.queue[0])
        assert isinstance(f2, SettingsFrame)
        assert f2.stream_id == 0
        assert f2.flags == set(['ACK'])

    def test_read_headers_out_of_order(self):
        # If header blocks aren't decoded in the same order they're received,
        # regardless of the stream they belong to, the decoder state will become
        # corrupted.
        e = Encoder()
        h1 = HeadersFrame(1)
        h1.data = e.encode({':status': 200, 'content-type': 'foo/bar'})
        h1.flags |= set(['END_HEADERS', 'END_STREAM'])
        h3 = HeadersFrame(3)
        h3.data = e.encode({':status': 200, 'content-type': 'baz/qux'})
        h3.flags |= set(['END_HEADERS', 'END_STREAM'])
        sock = DummySocket()
        sock.buffer = BytesIO(h1.serialize() + h3.serialize())

        c = HTTP20Connection('www.google.com')
        c._sock = sock
        r1 = c.request('GET', '/a')
        r3 = c.request('GET', '/b')

        assert c.getresponse(r3).getheaders() == [('content-type', 'baz/qux')]
        assert c.getresponse(r1).getheaders() == [('content-type', 'foo/bar')]

    def test_headers_with_continuation(self):
        e = Encoder()
        h = HeadersFrame(1)
        h.data = e.encode({':status': 200, 'content-type': 'foo/bar'})
        c = ContinuationFrame(1)
        c.data = e.encode({'content-length': '0'})
        c.flags |= set(['END_HEADERS', 'END_STREAM'])
        sock = DummySocket()
        sock.buffer = BytesIO(h.serialize() + c.serialize())

        c = HTTP20Connection('www.google.com')
        c._sock = sock
        r = c.request('GET', '/')

        assert set(c.getresponse(r).getheaders()) == set([('content-type', 'foo/bar'), ('content-length', '0')])

    def test_receive_unexpected_frame(self):
        # RST_STREAM frames are never defined on connections, so send one of
        # those.
        c = HTTP20Connection('www.google.com')
        f = RstStreamFrame(1)

        with pytest.raises(ValueError):
            c.receive_frame(f)

    def test_send_tolerate_peer_gone(self):
        class ErrorSocket(DummySocket):
            def send(self, data):
                raise socket.error(errno.EPIPE)

        c = HTTP20Connection('www.google.com')
        c._sock = ErrorSocket()
        f = SettingsFrame(0)
        with pytest.raises(socket.error):
            c._send_cb(f, False)
        c._sock = DummySocket()
        c._send_cb(f, True) # shouldn't raise an error

    def test_window_increments_appropriately(self):
        e = Encoder()
        h = HeadersFrame(1)
        h.data = e.encode({':status': 200, 'content-type': 'foo/bar'})
        h.flags = set(['END_HEADERS'])
        d = DataFrame(1)
        d.data = b'hi there sir'
        d2 = DataFrame(1)
        d2.data = b'hi there sir again'
        d2.flags = set(['END_STREAM'])
        sock = DummySocket()
        sock.buffer = BytesIO(h.serialize() + d.serialize() + d2.serialize())

        c = HTTP20Connection('www.google.com')
        c._sock = sock
        c.window_manager.window_size = 1000
        c.window_manager.initial_window_size = 1000
        c.request('GET', '/')
        resp = c.getresponse()
        resp.read()

        queue = list(map(decode_frame, sock.queue))
        assert len(queue) == 3  # one headers frame, two window update frames.
        assert isinstance(queue[1], WindowUpdateFrame)
        assert queue[1].window_increment == len(b'hi there sir')
        assert isinstance(queue[2], WindowUpdateFrame)
        assert queue[2].window_increment == len(b'hi there sir again')


class TestServerPush(object):
    def setup_method(self, method):
        self.frames = []
        self.encoder = Encoder()
        self.conn = None

    def add_push_frame(self, stream_id, promised_stream_id, headers, end_block=True):
        frame = PushPromiseFrame(stream_id)
        frame.promised_stream_id = promised_stream_id
        frame.data = self.encoder.encode(headers)
        if end_block:
            frame.flags.add('END_PUSH_PROMISE')
        self.frames.append(frame)

    def add_headers_frame(self, stream_id, headers, end_block=True, end_stream=False):
        frame = HeadersFrame(stream_id)
        frame.data = self.encoder.encode(headers)
        if end_block:
            frame.flags.add('END_HEADERS')
        if end_stream:
            frame.flags.add('END_STREAM')
        self.frames.append(frame)

    def add_data_frame(self, stream_id, data, end_stream=False):
        frame = DataFrame(stream_id)
        frame.data = data
        if end_stream:
            frame.flags.add('END_STREAM')
        self.frames.append(frame)

    def request(self):
        self.conn = HTTP20Connection('www.google.com', enable_push=True)
        self.conn._sock = DummySocket()
        self.conn._sock.buffer = BytesIO(b''.join([frame.serialize() for frame in self.frames]))
        self.conn.request('GET', '/')

    def assert_response(self):
        self.response = self.conn.getresponse()
        assert self.response.status == 200
        assert dict(self.response.getheaders()) == {'content-type': 'text/html'}

    def assert_pushes(self):
        self.pushes = list(self.conn.getpushes())
        assert len(self.pushes) == 1
        assert self.pushes[0].method == 'GET'
        assert self.pushes[0].scheme == 'https'
        assert self.pushes[0].authority == 'www.google.com'
        assert self.pushes[0].path == '/'
        expected_headers = {'accept-encoding': 'gzip'}
        for name, value in expected_headers.items():
            assert self.pushes[0].getrequestheader(name) == value
        assert dict(self.pushes[0].getrequestheaders()) == expected_headers

    def assert_push_response(self):
        push_response = self.pushes[0].getresponse()
        assert push_response.status == 200
        assert dict(push_response.getheaders()) == {'content-type': 'application/javascript'}
        assert push_response.read() == b'bar'

    def test_promise_before_headers(self):
        self.add_push_frame(1, 2, [(':method', 'GET'), (':path', '/'), (':authority', 'www.google.com'), (':scheme', 'https'), ('accept-encoding', 'gzip')])
        self.add_headers_frame(1, [(':status', '200'), ('content-type', 'text/html')])
        self.add_data_frame(1, b'foo', end_stream=True)
        self.add_headers_frame(2, [(':status', '200'), ('content-type', 'application/javascript')])
        self.add_data_frame(2, b'bar', end_stream=True)

        self.request()
        assert len(list(self.conn.getpushes())) == 0
        self.assert_response()
        self.assert_pushes()
        assert self.response.read() == b'foo'
        self.assert_push_response()

    def test_promise_after_headers(self):
        self.add_headers_frame(1, [(':status', '200'), ('content-type', 'text/html')])
        self.add_push_frame(1, 2, [(':method', 'GET'), (':path', '/'), (':authority', 'www.google.com'), (':scheme', 'https'), ('accept-encoding', 'gzip')])
        self.add_data_frame(1, b'foo', end_stream=True)
        self.add_headers_frame(2, [(':status', '200'), ('content-type', 'application/javascript')])
        self.add_data_frame(2, b'bar', end_stream=True)

        self.request()
        assert len(list(self.conn.getpushes())) == 0
        self.assert_response()
        assert len(list(self.conn.getpushes())) == 0
        assert self.response.read() == b'foo'
        self.assert_pushes()
        self.assert_push_response()

    def test_promise_after_data(self):
        self.add_headers_frame(1, [(':status', '200'), ('content-type', 'text/html')])
        self.add_data_frame(1, b'fo')
        self.add_push_frame(1, 2, [(':method', 'GET'), (':path', '/'), (':authority', 'www.google.com'), (':scheme', 'https'), ('accept-encoding', 'gzip')])
        self.add_data_frame(1, b'o', end_stream=True)
        self.add_headers_frame(2, [(':status', '200'), ('content-type', 'application/javascript')])
        self.add_data_frame(2, b'bar', end_stream=True)

        self.request()
        assert len(list(self.conn.getpushes())) == 0
        self.assert_response()
        assert len(list(self.conn.getpushes())) == 0
        assert self.response.read() == b'foo'
        self.assert_pushes()
        self.assert_push_response()

    def test_capture_all_promises(self):
        self.add_push_frame(1, 2, [(':method', 'GET'), (':path', '/one'), (':authority', 'www.google.com'), (':scheme', 'https'), ('accept-encoding', 'gzip')])
        self.add_headers_frame(1, [(':status', '200'), ('content-type', 'text/html')])
        self.add_push_frame(1, 4, [(':method', 'GET'), (':path', '/two'), (':authority', 'www.google.com'), (':scheme', 'https'), ('accept-encoding', 'gzip')])
        self.add_data_frame(1, b'foo', end_stream=True)
        self.add_headers_frame(4, [(':status', '200'), ('content-type', 'application/javascript')])
        self.add_headers_frame(2, [(':status', '200'), ('content-type', 'application/javascript')])
        self.add_data_frame(4, b'two', end_stream=True)
        self.add_data_frame(2, b'one', end_stream=True)

        self.request()
        assert len(list(self.conn.getpushes())) == 0
        pushes = list(self.conn.getpushes(capture_all=True))
        assert len(pushes) == 2
        assert pushes[0].path == '/one'
        assert pushes[1].path == '/two'
        assert pushes[0].getresponse().read() == b'one'
        assert pushes[1].getresponse().read() == b'two'
        self.assert_response()
        assert self.response.read() == b'foo'

    def test_cancel_push(self):
        self.add_push_frame(1, 2, [(':method', 'GET'), (':path', '/'), (':authority', 'www.google.com'), (':scheme', 'https'), ('accept-encoding', 'gzip')])
        self.add_headers_frame(1, [(':status', '200'), ('content-type', 'text/html')])

        self.request()
        self.conn.getresponse()
        list(self.conn.getpushes())[0].cancel()

        f = RstStreamFrame(2)
        f.error_code = 8
        assert self.conn._sock.queue[-1] == f.serialize()

    def test_reset_pushed_streams_when_push_disabled(self):
        self.add_push_frame(1, 2, [(':method', 'GET'), (':path', '/'), (':authority', 'www.google.com'), (':scheme', 'https'), ('accept-encoding', 'gzip')])
        self.add_headers_frame(1, [(':status', '200'), ('content-type', 'text/html')])

        self.request()
        self.conn._enable_push = False
        self.conn.getresponse()

        f = RstStreamFrame(2)
        f.error_code = 7
        assert self.conn._sock.queue[-1] == f.serialize()


class TestHyperStream(object):
    def test_streams_have_ids(self):
        s = Stream(1, None, None, None, None, None, None)
        assert s.stream_id == 1

    def test_streams_initially_have_no_headers(self):
        s = Stream(1, None, None, None, None, None, None)
        assert s.headers == []

    def test_streams_can_have_headers(self):
        s = Stream(1, None, None, None, None, None, None)
        s.add_header("name", "value")
        assert s.headers == [("name", "value")]

    def test_stream_opening_sends_headers(self):
        def data_callback(frame):
            assert isinstance(frame, HeadersFrame)
            assert frame.data == 'testkeyTestVal'
            assert frame.flags == set(['END_STREAM', 'END_HEADERS'])

        s = Stream(1, data_callback, None, None, NullEncoder, None, None)
        s.add_header("TestKey", "TestVal")
        s.open(True)

        assert s.state == STATE_HALF_CLOSED_LOCAL

    def test_file_objects_can_be_sent(self):
        def data_callback(frame):
            assert isinstance(frame, DataFrame)
            assert frame.data == b'Hi there!'
            assert frame.flags == set(['END_STREAM'])

        s = Stream(1, data_callback, None, None, NullEncoder, None, None)
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

        s = Stream(1, data_callback, None, None, NullEncoder, None, None)
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

        s = Stream(1, data_callback, None, None, NullEncoder, None, None)
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

        s = Stream(1, data_callback, None, None, NullEncoder, None, None)
        s.state = STATE_OPEN
        s.send_data(data, True)

        assert s.state == STATE_HALF_CLOSED_LOCAL
        assert recent_frame[0].flags == set(['END_STREAM'])
        assert frame_count[0] == 5
        assert s._out_flow_control_window == 65535 - len(data)

    def test_windowupdate_frames_update_windows(self):
        s = Stream(1, None, None, None, None, None, None)
        f = WindowUpdateFrame(1)
        f.window_increment = 1000
        s.receive_frame(f)

        assert s._out_flow_control_window == 65535 + 1000

    def test_stream_reading_works(self):
        out_frames = []
        in_frames = []

        def send_cb(frame, tolerate_peer_gone=False):
            out_frames.append(frame)

        def recv_cb(s):
            def inner():
                s.receive_frame(in_frames.pop(0))
            return inner

        s = Stream(1, send_cb, None, None, None, None, FlowControlManager(65535))
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

        def send_cb(frame, tolerate_peer_gone=False):
            out_frames.append(frame)

        def recv_cb(s):
            def inner():
                s.receive_frame(in_frames.pop(0))
            return inner

        s = Stream(1, send_cb, None, None, None, None, FlowControlManager(800))
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

        def send_cb(frame, tolerate_peer_gone=False):
            out_frames.append(frame)

        def recv_cb(s):
            def inner():
                s.receive_frame(in_frames.pop(0))
            return inner

        s = Stream(1, send_cb, None, None, None, None, FlowControlManager(800))
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

    def test_receive_unexpected_frame(self):
        # SETTINGS frames are never defined on streams, so send one of those.
        s = Stream(1, None, None, None, None, None, None)
        f = SettingsFrame(0)

        with pytest.raises(ValueError):
            s.receive_frame(f)


class TestResponse(object):
    def test_status_is_stripped_from_headers(self):
        headers = set([(':status', '200')])
        resp = HTTP20Response(headers, None)

        assert resp.status == 200
        assert resp.getheaders() == []

    def test_response_transparently_decrypts_gzip(self):
        headers = set([(':status', '200'), ('content-encoding', 'gzip')])
        c = zlib_compressobj(wbits=24)
        body = c.compress(b'this is test data')
        body += c.flush()
        resp = HTTP20Response(headers, DummyStream(body))

        assert resp.read() == b'this is test data'

    def test_response_transparently_decrypts_real_deflate(self):
        headers = set([(':status', '200'), ('content-encoding', 'deflate')])
        c = zlib_compressobj(wbits=zlib.MAX_WBITS)
        body = c.compress(b'this is test data')
        body += c.flush()
        resp = HTTP20Response(headers, DummyStream(body))

        assert resp.read() == b'this is test data'

    def test_response_transparently_decrypts_wrong_deflate(self):
        headers = set([(':status', '200'), ('content-encoding', 'deflate')])
        c = zlib_compressobj(wbits=-zlib.MAX_WBITS)
        body = c.compress(b'this is test data')
        body += c.flush()
        resp = HTTP20Response(headers, DummyStream(body))

        assert resp.read() == b'this is test data'

    def test_response_calls_stream_close(self):
        stream = DummyStream('')
        resp = HTTP20Response(set([(':status', '200')]), stream)
        resp.close()

        assert stream.closed

    def test_responses_are_context_managers(self):
        stream = DummyStream('')

        with HTTP20Response(set([(':status', '200')]), stream) as resp:
            pass

        assert stream.closed

    def test_read_small_chunks(self):
        headers = set([(':status', '200')])
        stream = DummyStream(b'1234567890')
        chunks = [b'12', b'34', b'56', b'78', b'90']
        resp = HTTP20Response(headers, stream)

        for chunk in chunks:
            assert resp.read(2) == chunk

        assert resp.read() == b''

    def test_read_buffered(self):
        headers = set([(':status', '200')])
        stream = DummyStream(b'1234567890')
        chunks = [b'12', b'34', b'56', b'78', b'90'] * 2
        resp = HTTP20Response(headers, stream)
        resp._data_buffer = b'1234567890'

        for chunk in chunks:
            assert resp.read(2) == chunk

        assert resp.read() == b''

    def test_getheader(self):
        headers = set([(':status', '200'), ('content-type', 'application/json')])
        stream = DummyStream(b'')
        resp = HTTP20Response(headers, stream)

        assert resp.getheader('content-type') == 'application/json'

    def test_getheader_default(self):
        headers = set([(':status', '200')])
        stream = DummyStream(b'')
        resp = HTTP20Response(headers, stream)

        assert resp.getheader('content-type', 'text/html') == 'text/html'

    def test_fileno_not_implemented(self):
        resp = HTTP20Response(set([(':status', '200')]), DummyStream(b''))

        with pytest.raises(NotImplementedError):
            resp.fileno()


class TestHTTP20Adapter(object):
    def test_adapter_reuses_connections(self):
        a = HTTP20Adapter()
        conn1 = a.get_connection('twitter.com')
        conn2 = a.get_connection('twitter.com')

        assert conn1 is conn2


# Some utility classes for the tests.
class NullEncoder(object):
    @staticmethod
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

    def close(self):
        pass

class DummyStream(object):
    def __init__(self, data):
        self.data = data
        self.closed = False

    def _read(self, *args, **kwargs):
        try:
            read_len = min(args[0], len(self.data))
        except IndexError:
            read_len = len(self.data)

        d = self.data[:read_len]
        self.data = self.data[read_len:]
        return d

    def close(self):
        if not self.closed:
            self.closed = True
        else:
            assert False
