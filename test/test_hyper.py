# -*- coding: utf-8 -*-
from hyper.packages.hyperframe.frame import (
    Frame, DataFrame, RstStreamFrame, SettingsFrame,
    PushPromiseFrame, PingFrame, WindowUpdateFrame, HeadersFrame,
    ContinuationFrame, BlockedFrame, GoAwayFrame,
)
from hyper.packages.hpack.hpack_compat import Encoder, Decoder
from hyper.http20.connection import HTTP20Connection
from hyper.http20.stream import (
    Stream, STATE_HALF_CLOSED_LOCAL, STATE_OPEN, MAX_CHUNK, STATE_CLOSED
)
from hyper.http20.response import HTTP20Response, HTTP20Push
from hyper.http20.exceptions import (
    HPACKDecodingError, HPACKEncodingError, ProtocolError, ConnectionError,
)
from hyper.http20.window import FlowControlManager
from hyper.http20.util import (
    combine_repeated_headers, split_repeated_headers, h2_safe_headers
)
from hyper.common.headers import HTTPHeaderMap
from hyper.compat import zlib_compressobj
from hyper.contrib import HTTP20Adapter
import hyper.http20.errors as errors
import errno
import os
import pytest
import socket
import zlib
from io import BytesIO


def decode_frame(frame_data):
    f, length = Frame.parse_frame_header(frame_data[:9])
    f.parse_body(memoryview(frame_data[9:9 + length]))
    assert 9 + length == len(frame_data)
    return f


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
        sock.buffer = BytesIO(b'\x00\x00\x08\x00\x01\x00\x00\x00\x01testdata')

        c = HTTP20Connection('www.google.com')
        c._sock = sock
        c.putrequest('GET', '/')
        c.endheaders()
        c._recv_cb()

        s = c.recent_stream
        assert s.data == [b'testdata']

    def test_we_can_read_fitfully_from_the_socket(self):
        sock = DummyFitfullySocket()
        sock.buffer = BytesIO(
            b'\x00\x00\x18\x00\x01\x00\x00\x00\x01'
            b'testdata'
            b'+payload'
        )

        c = HTTP20Connection('www.google.com')
        c._sock = sock
        c.putrequest('GET', '/')
        c.endheaders()
        c._recv_cb()

        s = c.recent_stream
        assert s.data == [b'testdata+payload']

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

        assert c.get_response(r3).headers == HTTPHeaderMap([('content-type', 'baz/qux')])
        assert c.get_response(r1).headers == HTTPHeaderMap([('content-type', 'foo/bar')])

    def test_headers_with_continuation(self):
        e = Encoder()
        header_data = e.encode(
            {':status': 200, 'content-type': 'foo/bar', 'content-length': '0'}
        )
        h = HeadersFrame(1)
        h.data = header_data[0:int(len(header_data)/2)]
        c = ContinuationFrame(1)
        c.data = header_data[int(len(header_data)/2):]
        c.flags |= set(['END_HEADERS', 'END_STREAM'])
        sock = DummySocket()
        sock.buffer = BytesIO(h.serialize() + c.serialize())

        c = HTTP20Connection('www.google.com')
        c._sock = sock
        r = c.request('GET', '/')

        assert set(c.get_response(r).headers.iter_raw()) == set([(b'content-type', b'foo/bar'), (b'content-length', b'0')])

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
        resp = c.get_response()
        resp.read()

        queue = list(map(decode_frame, map(memoryview, sock.queue)))
        assert len(queue) == 3  # one headers frame, two window update frames.
        assert isinstance(queue[1], WindowUpdateFrame)
        assert queue[1].window_increment == len(b'hi there sir')
        assert isinstance(queue[2], WindowUpdateFrame)
        assert queue[2].window_increment == len(b'hi there sir again')

    def test_ping_with_ack_ignored(self):
        c = HTTP20Connection('www.google.com')
        f = PingFrame(0)
        f.flags = set(['ACK'])
        f.opaque_data = b'12345678'

        def data_cb(frame, tolerate_peer_gone=False):
            assert False, 'should not be called'
        c._send_cb = data_cb
        c.receive_frame(f)

    def test_ping_without_ack_gets_reply(self):
        c = HTTP20Connection('www.google.com')
        f = PingFrame(0)
        f.opaque_data = b'12345678'

        frames = []

        def data_cb(frame, tolerate_peer_gone=False):
            frames.append(frame)
        c._send_cb = data_cb
        c.receive_frame(f)

        assert len(frames) == 1
        assert frames[0].type == PingFrame.type
        assert frames[0].flags == set(['ACK'])
        assert frames[0].opaque_data == b'12345678'

    def test_blocked_causes_window_updates(self):
        frames = []

        def data_cb(frame, *args):
            frames.append(frame)

        c = HTTP20Connection('www.google.com')
        c._send_cb = data_cb

        # Change the window size.
        c.window_manager.window_size = 60000

        # Provide a BLOCKED frame.
        f = BlockedFrame(1)
        c.receive_frame(f)

        assert len(frames) == 1
        assert frames[0].type == WindowUpdateFrame.type
        assert frames[0].window_increment == 5535


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
            frame.flags.add('END_HEADERS')
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
        self.response = self.conn.get_response()
        assert self.response.status == 200
        assert dict(self.response.headers) == {b'content-type': [b'text/html']}

    def assert_pushes(self):
        self.pushes = list(self.conn.get_pushes())
        assert len(self.pushes) == 1
        assert self.pushes[0].method == b'GET'
        assert self.pushes[0].scheme == b'https'
        assert self.pushes[0].authority == b'www.google.com'
        assert self.pushes[0].path == b'/'
        expected_headers = {b'accept-encoding': [b'gzip']}
        assert dict(self.pushes[0].request_headers) == expected_headers

    def assert_push_response(self):
        push_response = self.pushes[0].get_response()
        assert push_response.status == 200
        assert dict(push_response.headers) == {b'content-type': [b'application/javascript']}
        assert push_response.read() == b'bar'

    def test_promise_before_headers(self):
        self.add_push_frame(1, 2, [(':method', 'GET'), (':path', '/'), (':authority', 'www.google.com'), (':scheme', 'https'), ('accept-encoding', 'gzip')])
        self.add_headers_frame(1, [(':status', '200'), ('content-type', 'text/html')])
        self.add_data_frame(1, b'foo', end_stream=True)
        self.add_headers_frame(2, [(':status', '200'), ('content-type', 'application/javascript')])
        self.add_data_frame(2, b'bar', end_stream=True)

        self.request()
        assert len(list(self.conn.get_pushes())) == 0
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
        assert len(list(self.conn.get_pushes())) == 0
        self.assert_response()
        assert len(list(self.conn.get_pushes())) == 0
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
        assert len(list(self.conn.get_pushes())) == 0
        self.assert_response()
        assert len(list(self.conn.get_pushes())) == 0
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
        assert len(list(self.conn.get_pushes())) == 0
        pushes = list(self.conn.get_pushes(capture_all=True))
        assert len(pushes) == 2
        assert pushes[0].path == b'/one'
        assert pushes[1].path == b'/two'
        assert pushes[0].get_response().read() == b'one'
        assert pushes[1].get_response().read() == b'two'
        self.assert_response()
        assert self.response.read() == b'foo'

    def test_cancel_push(self):
        self.add_push_frame(1, 2, [(':method', 'GET'), (':path', '/'), (':authority', 'www.google.com'), (':scheme', 'https'), ('accept-encoding', 'gzip')])
        self.add_headers_frame(1, [(':status', '200'), ('content-type', 'text/html')])

        self.request()
        self.conn.get_response()
        list(self.conn.get_pushes())[0].cancel()

        f = RstStreamFrame(2)
        f.error_code = 8
        assert self.conn._sock.queue[-1] == f.serialize()

    def test_reset_pushed_streams_when_push_disabled(self):
        self.add_push_frame(1, 2, [(':method', 'GET'), (':path', '/'), (':authority', 'www.google.com'), (':scheme', 'https'), ('accept-encoding', 'gzip')])
        self.add_headers_frame(1, [(':status', '200'), ('content-type', 'text/html')])

        self.request()
        self.conn._enable_push = False
        self.conn.get_response()

        f = RstStreamFrame(2)
        f.error_code = 7
        assert self.conn._sock.queue[-1] == f.serialize()

    def test_pushed_requests_ignore_unexpected_headers(self):
        headers = HTTPHeaderMap([
            (':scheme', 'http'),
            (':method', 'get'),
            (':authority', 'google.com'),
            (':path', '/'),
            (':reserved', 'no'),
            ('no', 'no'),
        ])
        p = HTTP20Push(headers, DummyStream(b''))

        assert p.request_headers == HTTPHeaderMap([('no', 'no')])


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

    def test_flow_control_manager_update_includes_padding(self):
        out_frames = []
        in_frames = []

        def send_cb(frame):
            out_frames.append(frame)

        def recv_cb(s):
            def inner():
                s.receive_frame(in_frames.pop(0))
            return inner

        start_window = 65535
        s = Stream(1, send_cb, None, None, None, None, FlowControlManager(start_window))
        s._recv_cb = recv_cb(s)
        s.state = STATE_HALF_CLOSED_LOCAL

        # Provide two data frames to read.
        f = DataFrame(1)
        f.data = b'hi there!'
        f.pad_length = 10
        f.flags.add('END_STREAM')
        in_frames.append(f)

        data = s._read()
        assert data == b'hi there!'
        assert s._in_window_manager.window_size == start_window - f.pad_length - len(data) - 1

    def test_blocked_frames_cause_window_updates(self):
        out_frames = []

        def send_cb(frame, *args):
            out_frames.append(frame)

        start_window = 65535
        s = Stream(1, send_cb, None, None, None, None, FlowControlManager(start_window))
        s._data_cb = send_cb
        s.state = STATE_HALF_CLOSED_LOCAL

        # Change the window size.
        s._in_window_manager.window_size = 60000

        # Provide a BLOCKED frame.
        f = BlockedFrame(1)
        s.receive_frame(f)

        assert len(out_frames) == 1
        assert out_frames[0].type == WindowUpdateFrame.type
        assert out_frames[0].window_increment == 5535

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

    def test_can_receive_continuation_frame_after_end_stream(self):
        s = Stream(1, None, None, None, None, None, FlowControlManager(65535))
        f = HeadersFrame(1)
        f.data = 'hi there'
        f.flags = set('END_STREAM')
        f2 = ContinuationFrame(1)
        f2.data = ' sir'
        f2.flags = set('END_HEADERS')

        s.receive_frame(f)
        s.receive_frame(f2)

    def test_receive_unexpected_frame(self):
        # SETTINGS frames are never defined on streams, so send one of those.
        s = Stream(1, None, None, None, None, None, None)
        f = SettingsFrame(0)

        with pytest.raises(ValueError):
            s.receive_frame(f)

    def test_can_receive_trailers(self):
        headers = [('a', 'b'), ('c', 'd'), (':status', '200')]
        trailers = [('e', 'f'), ('g', 'h')]

        s = Stream(1, None, None, None, None, FixedDecoder(headers), None)
        s.state = STATE_HALF_CLOSED_LOCAL

        # Provide the first HEADERS frame.
        f = HeadersFrame(1)
        f.data = b'hi there!'
        f.flags.add('END_HEADERS')
        s.receive_frame(f)

        assert s.response_headers == HTTPHeaderMap(headers)

        # Now, replace the dummy decoder to ensure we get a new header block.
        s._decoder = FixedDecoder(trailers)

        # Provide the trailers.
        f = HeadersFrame(1)
        f.data = b'hi there again!'
        f.flags.add('END_STREAM')
        f.flags.add('END_HEADERS')
        s.receive_frame(f)

        # Now, check the trailers.
        assert s.response_trailers == HTTPHeaderMap(trailers)

        # Confirm we closed the stream.
        assert s.state == STATE_CLOSED

    def test_cannot_receive_three_header_blocks(self):
        first = [('a', 'b'), ('c', 'd'), (':status', '200')]

        s = Stream(1, None, None, None, None, FixedDecoder(first), None)
        s.state = STATE_HALF_CLOSED_LOCAL

        # Provide the first two header frames.
        f = HeadersFrame(1)
        f.data = b'hi there!'
        f.flags.add('END_HEADERS')
        s.receive_frame(f)

        f = HeadersFrame(1)
        f.data = b'hi there again!'
        f.flags.add('END_HEADERS')
        s.receive_frame(f)

        # Provide the third. This one blows up.
        f = HeadersFrame(1)
        f.data = b'hi there again!'
        f.flags.add('END_STREAM')
        f.flags.add('END_HEADERS')

        with pytest.raises(ProtocolError):
            s.receive_frame(f)

    def test_reading_trailers_early_reads_all_data(self):
        in_frames = []
        headers = [('a', 'b'), ('c', 'd'), (':status', '200')]
        trailers = [('e', 'f'), ('g', 'h')]

        def recv_cb(s):
            def inner():
                s.receive_frame(in_frames.pop(0))
            return inner

        s = Stream(1, None, None, None, None, FixedDecoder(headers), FlowControlManager(65535))
        s._recv_cb = recv_cb(s)
        s.state = STATE_HALF_CLOSED_LOCAL

        # Provide the first HEADERS frame.
        f = HeadersFrame(1)
        f.data = b'hi there!'
        f.flags.add('END_HEADERS')
        in_frames.append(f)

        # Provide some data.
        f = DataFrame(1)
        f.data = b'testdata'
        in_frames.append(f)

        # Provide the trailers.
        f = HeadersFrame(1)
        f.data = b'hi there again!'
        f.flags.add('END_STREAM')
        f.flags.add('END_HEADERS')
        in_frames.append(f)

        # Begin by reading the first headers.
        assert s.getheaders() == HTTPHeaderMap(headers)

        # Now, replace the dummy decoder to ensure we get a new header block.
        s._decoder = FixedDecoder(trailers)

        # Ask for the trailers. This should also read the data frames.
        assert s.gettrailers() == HTTPHeaderMap(trailers)
        assert s.data == [b'testdata']

    def test_can_read_single_frames_from_streams(self):
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

        data = s._read_one_frame()
        assert data == b'hi there!'

        data = s._read_one_frame()
        assert data == b'hi there again!'

        data = s._read_one_frame()
        assert data is None

        data = s._read()
        assert data == b''


class TestResponse(object):
    def test_status_is_stripped_from_headers(self):
        headers = HTTPHeaderMap([(':status', '200')])
        resp = HTTP20Response(headers, None)

        assert resp.status == 200
        assert not resp.headers

    def test_response_transparently_decrypts_gzip(self):
        headers = HTTPHeaderMap([(':status', '200'), ('content-encoding', 'gzip')])
        c = zlib_compressobj(wbits=24)
        body = c.compress(b'this is test data')
        body += c.flush()
        resp = HTTP20Response(headers, DummyStream(body))

        assert resp.read() == b'this is test data'

    def test_response_transparently_decrypts_real_deflate(self):
        headers = HTTPHeaderMap([(':status', '200'), ('content-encoding', 'deflate')])
        c = zlib_compressobj(wbits=zlib.MAX_WBITS)
        body = c.compress(b'this is test data')
        body += c.flush()
        resp = HTTP20Response(headers, DummyStream(body))

        assert resp.read() == b'this is test data'

    def test_response_transparently_decrypts_wrong_deflate(self):
        headers = HTTPHeaderMap([(':status', '200'), ('content-encoding', 'deflate')])
        c = zlib_compressobj(wbits=-zlib.MAX_WBITS)
        body = c.compress(b'this is test data')
        body += c.flush()
        resp = HTTP20Response(headers, DummyStream(body))

        assert resp.read() == b'this is test data'

    def test_response_calls_stream_close(self):
        headers = HTTPHeaderMap([(':status', '200')])
        stream = DummyStream('')
        resp = HTTP20Response(headers, stream)
        resp.close()

        assert stream.closed

    def test_responses_are_context_managers(self):
        headers = HTTPHeaderMap([(':status', '200')])
        stream = DummyStream('')

        with HTTP20Response(headers, stream) as resp:
            pass

        assert stream.closed

    def test_read_small_chunks(self):
        headers = HTTPHeaderMap([(':status', '200')])
        stream = DummyStream(b'1234567890')
        chunks = [b'12', b'34', b'56', b'78', b'90']
        resp = HTTP20Response(headers, stream)

        for chunk in chunks:
            assert resp.read(2) == chunk

        assert resp.read() == b''

    def test_read_buffered(self):
        headers = HTTPHeaderMap([(':status', '200')])
        stream = DummyStream(b'1234567890')
        chunks = [b'12', b'34', b'56', b'78', b'90'] * 2
        resp = HTTP20Response(headers, stream)
        resp._data_buffer = b'1234567890'

        for chunk in chunks:
            assert resp.read(2) == chunk

        assert resp.read() == b''

    def test_getheader(self):
        headers = HTTPHeaderMap([(':status', '200'), ('content-type', 'application/json')])
        stream = DummyStream(b'')
        resp = HTTP20Response(headers, stream)

        assert resp.headers[b'content-type'] == [b'application/json']

    def test_response_ignores_unknown_headers(self):
        headers = HTTPHeaderMap([(':status', '200'), (':reserved', 'yes'), ('no', 'no')])
        stream = DummyStream(b'')
        resp = HTTP20Response(headers, stream)

        assert resp.headers == HTTPHeaderMap([('no', 'no')])

    def test_fileno_not_implemented(self):
        headers = HTTPHeaderMap([(':status', '200')])
        resp = HTTP20Response(headers, DummyStream(b''))

        with pytest.raises(NotImplementedError):
            resp.fileno()

    def test_trailers_are_read(self):
        headers = HTTPHeaderMap([(':status', '200')])
        trailers = HTTPHeaderMap([('a', 'b'), ('c', 'd')])
        stream = DummyStream(b'', trailers=trailers)
        resp = HTTP20Response(headers, stream)

        assert resp.trailers == trailers
        assert resp.trailers['a'] == [b'b']
        assert resp.trailers['c'] == [b'd']

    def test_read_frames(self):
        headers = HTTPHeaderMap([(':status', '200')])
        stream = DummyStream(None)
        chunks = [b'12', b'3456', b'78', b'9']
        stream.data_frames = chunks
        resp = HTTP20Response(headers, stream)

        for recv, expected in zip(resp.read_chunked(), chunks[:]):
            assert recv == expected

    def test_read_compressed_frames(self):
        headers = HTTPHeaderMap([(':status', '200'), ('content-encoding', 'gzip')])
        c = zlib_compressobj(wbits=24)
        body = c.compress(b'this is test data')
        body += c.flush()

        stream = DummyStream(None)
        chunks = [body[x:x+2] for x in range(0, len(body), 2)]
        stream.data_frames = chunks
        resp = HTTP20Response(headers, stream)

        received = b''
        for chunk in resp.read_chunked():
            received += chunk

        assert received == b'this is test data'


class TestHTTP20Adapter(object):
    def test_adapter_reuses_connections(self):
        a = HTTP20Adapter()
        conn1 = a.get_connection('http2bin.org', 80, 'http')
        conn2 = a.get_connection('http2bin.org', 80, 'http')

        assert conn1 is conn2


class TestUtilities(object):
    def test_combining_repeated_headers(self):
        test_headers = [
            (b'key1', b'val1'),
            (b'key2', b'val2'),
            (b'key1', b'val1.1'),
            (b'key3', b'val3'),
            (b'key2', b'val2.1'),
            (b'key1', b'val1.2'),
        ]
        expected = [
            (b'key1', b'val1\x00val1.1\x00val1.2'),
            (b'key2', b'val2\x00val2.1'),
            (b'key3', b'val3'),
        ]

        assert expected == combine_repeated_headers(test_headers)

    def test_splitting_repeated_headers(self):
        test_headers = [
            (b'key1', b'val1\x00val1.1\x00val1.2'),
            (b'key2', b'val2\x00val2.1'),
            (b'key3', b'val3'),
        ]
        expected = {
            b'key1': [b'val1', b'val1.1', b'val1.2'],
            b'key2': [b'val2', b'val2.1'],
            b'key3': [b'val3'],
        }

        assert expected == split_repeated_headers(test_headers)

    def test_nghttp2_installs_correctly(self):
        # This test is a debugging tool: if nghttp2 is being tested by Travis,
        # we need to confirm it imports correctly. Hyper will normally hide the
        # import failure, so let's discover it here.
        # Alternatively, if we are *not* testing with nghttp2, this test should
        # confirm that it's not available.
        if os.environ.get('NGHTTP2'):
            import nghttp2
        else:
            with pytest.raises(ImportError):
                import nghttp2

        assert True

    def test_stripping_connection_header(self):
        headers = [('one', 'two'), ('connection', 'close')]
        stripped = [('one', 'two')]

        assert h2_safe_headers(headers) == stripped

    def test_stripping_related_headers(self):
        headers = [
            ('one', 'two'), ('three', 'four'), ('five', 'six'),
            ('connection', 'close, three, five')
        ]
        stripped = [('one', 'two')]

        assert h2_safe_headers(headers) == stripped

    def test_stripping_multiple_connection_headers(self):
        headers = [
            ('one', 'two'), ('three', 'four'), ('five', 'six'),
            ('connection', 'close'),
            ('connection', 'three, five')
        ]
        stripped = [('one', 'two')]

        assert h2_safe_headers(headers) == stripped

    def test_goaway_frame_PROTOCOL_ERROR(self):
        f = GoAwayFrame(0)
        # Set error code to PROTOCOL_ERROR
        f.error_code = 1;

        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()

        # 'Receive' the GOAWAY frame.
        # Validate that the spec error name and description are used to throw
        # the connection exception.
        with pytest.raises(ConnectionError) as conn_err:
            c.receive_frame(f)

        err_msg = str(conn_err)
        name, number, description = errors.get_data(1)

        assert name in err_msg
        assert number in err_msg
        assert description in err_msg

    def test_goaway_frame_HTTP_1_1_REQUIRED(self):
        f = GoAwayFrame(0)
        # Set error code to HTTP_1_1_REQUIRED
        f.error_code = 13;

        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()

        # 'Receive' the GOAWAY frame.
        # Validate that the spec error name and description are used to throw
        # the connection exception.
        with pytest.raises(ConnectionError) as conn_err:
            c.receive_frame(f)

        err_msg = str(conn_err)
        name, number, description = errors.get_data(13)

        assert name in err_msg
        assert number in err_msg
        assert description in err_msg

    def test_goaway_frame_NO_ERROR(self):
        f = GoAwayFrame(0)
        # Set error code to NO_ERROR
        f.error_code = 0;

        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()

        # 'Receive' the GOAWAY frame.
        # Test makes sure no exception is raised; error code 0 means we are
        # dealing with a standard and graceful shutdown.
        c.receive_frame(f)

    def test_goaway_frame_invalid_error_code(self):
        f = GoAwayFrame(0)
        # Set error code to non existing error
        f.error_code = 100;
        f.additional_data = 'data about non existing error code';

        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()

        # 'Receive' the GOAWAY frame.
        # If the error code does not exist in the spec then the additional
        # data is used instead.
        with pytest.raises(ConnectionError) as conn_err:
            c.receive_frame(f)

        err_msg = str(conn_err)
        with pytest.raises(ValueError):
            name, number, description = errors.get_data(100)

        assert 'data about non existing error code' in err_msg
        assert str(f.error_code) in err_msg

    def test_receive_unexpected_stream_id(self):
        frames = []

        def data_callback(frame):
            frames.append(frame)

        c = HTTP20Connection('www.google.com')
        c._send_cb = data_callback

        f = DataFrame(2)
        data = memoryview(b"hi there sir")
        c._consume_frame_payload(f, data)

        # If we receive an unexpected stream id then we cancel the stream
        # by sending a reset stream that contains the protocol error code (1)
        f = frames[0]
        assert len(frames) == 1
        assert f.stream_id == 2
        assert isinstance(f, RstStreamFrame)
        assert f.error_code == 1 # PROTOCOL_ERROR


# Some utility classes for the tests.
class NullEncoder(object):
    @staticmethod
    def encode(headers):
        return '\n'.join("%s%s" % (name, val) for name, val in headers)

class FixedDecoder(object):
    def __init__(self, result):
        self.result = result

    def decode(self, headers):
        return self.result

class DummySocket(object):
    def __init__(self):
        self.queue = []
        self.buffer = BytesIO()
        self.can_read = False

    def send(self, data):
        self.queue.append(data)

    def recv(self, l):
        return memoryview(self.buffer.read(l))

    def close(self):
        pass


class DummyFitfullySocket(DummySocket):
    def recv(self, l):
        length = l
        if l != 9 and l >= 4:
            length = int(round(l / 2))
        return memoryview(self.buffer.read(length))


class DummyStream(object):
    def __init__(self, data, trailers=None):
        self.data = data
        self.data_frames = []
        self.closed = False
        self.response_headers = {}
        self._remote_closed = False
        self.trailers = trailers

        if self.trailers is None:
            self.trailers = []

    def _read(self, *args, **kwargs):
        try:
            read_len = min(args[0], len(self.data))
        except IndexError:
            read_len = len(self.data)

        d = self.data[:read_len]
        self.data = self.data[read_len:]

        if not self.data:
            self._remote_closed = True

        return d

    def _read_one_frame(self):
        try:
            return self.data_frames.pop(0)
        except IndexError:
            return None

    def close(self):
        if not self.closed:
            self.closed = True
        else:
            assert False

    def gettrailers(self):
        return self.trailers
