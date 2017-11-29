# -*- coding: utf-8 -*-
import h2.settings

from h2.frame_buffer import FrameBuffer
from h2.connection import ConnectionState
from hyperframe.frame import (
    Frame, DataFrame, RstStreamFrame, SettingsFrame, PushPromiseFrame,
    WindowUpdateFrame, HeadersFrame, ContinuationFrame, GoAwayFrame,
    PingFrame, FRAME_MAX_ALLOWED_LEN
)
from hpack.hpack_compat import Encoder
from hyper.common.connection import HTTPConnection
from hyper.http20.connection import HTTP20Connection
from hyper.http20.response import HTTP20Response, HTTP20Push
from hyper.http20.exceptions import ConnectionError, StreamResetError
from hyper.http20.util import (
    combine_repeated_headers, split_repeated_headers, h2_safe_headers
)
from hyper.common.headers import HTTPHeaderMap
from hyper.common.util import to_bytestring, HTTPVersion
from hyper.compat import zlib_compressobj, is_py2, ssl
from hyper.contrib import HTTP20Adapter
import hyper.http20.errors as errors
import errno
import os
import pytest
import socket
import zlib
import brotli
from io import BytesIO

TEST_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_CERTS_DIR = os.path.join(TEST_DIR, 'certs')
CLIENT_PEM_FILE = os.path.join(TEST_CERTS_DIR, 'nopassword.pem')
SERVER_CERT_FILE = os.path.join(TEST_CERTS_DIR, 'server.crt')


def decode_frame(frame_data):
    f, length = Frame.parse_frame_header(frame_data[:9])
    f.parse_body(memoryview(frame_data[9:9 + length]))
    assert 9 + length == len(frame_data)
    return f


@pytest.fixture
def frame_buffer():
    buffer = FrameBuffer()
    buffer.max_frame_size = FRAME_MAX_ALLOWED_LEN
    return buffer


class TestHyperConnection(object):
    def test_connections_accept_hosts_and_ports(self):
        c = HTTP20Connection(host='www.google.com', port=8080)
        assert c.host == 'www.google.com'
        assert c.port == 8080
        assert c.proxy_host is None

    def test_connections_can_parse_hosts_and_ports(self):
        c = HTTP20Connection('www.google.com:8080')
        assert c.host == 'www.google.com'
        assert c.port == 8080
        assert c.proxy_host is None

    def test_connections_accept_proxy_hosts_and_ports(self):
        c = HTTP20Connection('www.google.com', proxy_host='localhost:8443')
        assert c.host == 'www.google.com'
        assert c.proxy_host == 'localhost'
        assert c.proxy_port == 8443

    def test_connections_can_parse_proxy_hosts_with_userinfo(self):
        c = HTTP20Connection('www.google.com',
                             proxy_host='azAz09!==:fakepaswd@localhost:8443')
        # Note that the userinfo part is getting stripped out,
        # it's not automatically added as Basic Auth header to
        # the proxy_headers! It should be done manually.
        assert c.host == 'www.google.com'
        assert c.proxy_host == 'localhost'
        assert c.proxy_port == 8443

    def test_connections_can_parse_proxy_hosts_and_ports(self):
        c = HTTP20Connection('www.google.com',
                             proxy_host='localhost',
                             proxy_port=8443)
        assert c.host == 'www.google.com'
        assert c.proxy_host == 'localhost'
        assert c.proxy_port == 8443

    def test_connections_can_parse_ipv6_hosts_and_ports(self):
        c = HTTP20Connection('[abcd:dcba::1234]',
                             proxy_host='[ffff:aaaa::1]:8443')

        assert c.host == 'abcd:dcba::1234'
        assert c.port == 443
        assert c.proxy_host == 'ffff:aaaa::1'
        assert c.proxy_port == 8443

    def test_connection_version(self):
        c = HTTP20Connection('www.google.com')
        assert c.version is HTTPVersion.http20

    def test_connection_timeout(self):
        c = HTTP20Connection('httpbin.org', timeout=30)

        assert c._timeout == 30

    def test_connection_tuple_timeout(self):
        c = HTTP20Connection('httpbin.org', timeout=(5, 60))

        assert c._timeout == (5, 60)

    def test_ping(self, frame_buffer):
        def data_callback(chunk, **kwargs):
            frame_buffer.add_data(chunk)

        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()
        c._send_cb = data_callback
        opaque = '00000000'
        c.ping(opaque)

        frames = list(frame_buffer)
        assert len(frames) == 1
        f = frames[0]
        assert isinstance(f, PingFrame)
        assert f.opaque_data == to_bytestring(opaque)

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

        assert list(s.headers.items()) == [
            (b':method', b'GET'),
            (b':scheme', b'https'),
            (b':authority', b'www.google.com'),
            (b':path', b'/'),
        ]

    def test_putheader_puts_headers(self):
        c = HTTP20Connection("www.google.com")

        c.putrequest('GET', '/')
        c.putheader('name', 'value')
        s = c.recent_stream

        assert list(s.headers.items()) == [
            (b':method', b'GET'),
            (b':scheme', b'https'),
            (b':authority', b'www.google.com'),
            (b':path', b'/'),
            (b'name', b'value'),
        ]

    def test_putheader_replaces_headers(self):
        c = HTTP20Connection("www.google.com")

        c.putrequest('GET', '/')
        c.putheader(':authority', 'www.example.org', replace=True)
        c.putheader('name', 'value')
        c.putheader('name', 'value2', replace=True)
        s = c.recent_stream

        assert list(s.headers.items()) == [
            (b':method', b'GET'),
            (b':scheme', b'https'),
            (b':authority', b'www.example.org'),
            (b':path', b'/'),
            (b'name', b'value2'),
        ]

    def test_endheaders_sends_data(self, frame_buffer):
        def data_callback(chunk, **kwargs):
            frame_buffer.add_data(chunk)

        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()
        c._send_cb = data_callback
        c.putrequest('GET', '/')
        c.endheaders()

        frames = list(frame_buffer)
        assert len(frames) == 1
        f = frames[0]
        assert isinstance(f, HeadersFrame)

    def test_we_can_send_data_using_endheaders(self, frame_buffer):
        def data_callback(chunk, **kwargs):
            frame_buffer.add_data(chunk)

        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()
        c._send_cb = data_callback
        c.putrequest('GET', '/')
        c.endheaders(message_body=b'hello there', final=True)

        frames = list(frame_buffer)
        assert len(frames) == 2
        assert isinstance(frames[0], HeadersFrame)
        assert frames[0].flags == set(['END_HEADERS'])
        assert isinstance(frames[1], DataFrame)
        assert frames[1].data == b'hello there'
        assert frames[1].flags == set(['END_STREAM'])

    def test_request_correctly_sent_max_chunk(self, frame_buffer):
        """
        Test that request correctly sent when data length multiple
        max chunk. We check last chunk has a end flag and correct number
        of chunks.
        """
        def data_callback(chunk, **kwargs):
            frame_buffer.add_data(chunk)

        # one chunk
        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()
        c._send_cb = data_callback
        c.putrequest('GET', '/')
        c.endheaders(message_body=b'1'*1024, final=True)

        frames = list(frame_buffer)
        assert len(frames) == 2
        assert isinstance(frames[1], DataFrame)
        assert frames[1].flags == set(['END_STREAM'])

        # two chunks
        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()
        c._send_cb = data_callback
        c.putrequest('GET', '/')
        c.endheaders(message_body=b'1' * 2024, final=True)

        frames = list(frame_buffer)
        assert len(frames) == 3
        assert isinstance(frames[1], DataFrame)
        assert frames[2].flags == set(['END_STREAM'])

        # two chunks with last chunk < 1024
        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()
        c._send_cb = data_callback
        c.putrequest('GET', '/')
        c.endheaders(message_body=b'1' * 2000, final=True)

        frames = list(frame_buffer)
        assert len(frames) == 3
        assert isinstance(frames[1], DataFrame)
        assert frames[2].flags == set(['END_STREAM'])

        # no chunks
        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()
        c._send_cb = data_callback
        c.putrequest('GET', '/')
        c.endheaders(message_body=b'', final=True)

        frames = list(frame_buffer)
        assert len(frames) == 1

    def test_that_we_correctly_send_over_the_socket(self):
        sock = DummySocket()
        c = HTTP20Connection('www.google.com')
        c._sock = sock
        c.putrequest('GET', '/')
        c.endheaders(message_body=b'hello there', final=True)

        # Don't bother testing that the serialization was ok, that should be
        # fine.
        assert len(sock.queue) == 3

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

        # The socket should have received one headers frame and two body
        # frames.
        assert len(sock.queue) == 3

    def test_request_with_utf8_bytes_body(self):
        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()
        body = '你好' if is_py2 else '你好'.encode('utf-8')
        c.request('GET', '/', body=body)

    def test_request_with_unicode_body(self):
        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()
        body = '你好'.decode('unicode-escape') if is_py2 else '你好'
        c.request('GET', '/', body=body)

    def test_different_request_headers(self):
        sock = DummySocket()

        c = HTTP20Connection('www.google.com')
        c._sock = sock
        c.request('GET', '/', body='hello', headers={b'name': b'value'})
        s = c.recent_stream

        assert list(s.headers.items()) == [
            (b':method', b'GET'),
            (b':scheme', b'https'),
            (b':authority', b'www.google.com'),
            (b':path', b'/'),
            (b'name', b'value'),
        ]

        c.request('GET', '/', body='hello', headers={u'name2': u'value2'})
        s = c.recent_stream

        assert list(s.headers.items()) == [
            (b':method', b'GET'),
            (b':scheme', b'https'),
            (b':authority', b'www.google.com'),
            (b':path', b'/'),
            (b'name2', b'value2'),
        ]

    def test_closed_connections_are_reset(self):
        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()
        wm = c.window_manager
        c.request('GET', '/')
        c.close()

        assert c._sock is None
        assert not c.streams
        assert c.recent_stream is None
        assert c.next_stream_id == 1
        assert c.window_manager is not wm
        with c._conn as conn:
            assert conn.state_machine.state == ConnectionState.IDLE
            origin_h2_conn = conn

        c.close()
        assert c._sock is None
        assert not c.streams
        assert c.recent_stream is None
        assert c.next_stream_id == 1
        assert c.window_manager is not wm
        with c._conn as conn:
            assert conn.state_machine.state == ConnectionState.IDLE
            assert conn != origin_h2_conn

    def test_streams_removed_on_close(self):
        # Create content for read from socket
        e = Encoder()
        h1 = HeadersFrame(1)
        h1.data = e.encode([(':status', 200), ('content-type', 'foo/bar')])
        h1.flags |= set(['END_HEADERS', 'END_STREAM'])
        sock = DummySocket()
        sock.buffer = BytesIO(h1.serialize())

        c = HTTP20Connection('www.google.com')
        c._sock = sock
        stream_id = c.request('GET', '/')

        # Create reference to current recent_recv_streams set
        recent_recv_streams = c.recent_recv_streams
        streams = c.streams

        resp = c.get_response(stream_id=stream_id)
        assert stream_id in recent_recv_streams
        assert stream_id in streams
        resp.read()
        assert stream_id not in recent_recv_streams
        assert stream_id not in streams

    def test_connection_no_window_update_on_zero_length_data_frame(self):
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

    def test_streams_raise_error_on_read_after_close(self):
        # Prepare a socket so we can open a stream.
        sock = DummySocket()
        c = HTTP20Connection('www.google.com')
        c._sock = sock

        # Open a request (which creates a stream)
        stream_id = c.request('GET', '/')

        # close connection
        c.close()

        # try to read the stream
        with pytest.raises(StreamResetError):
            c.get_response(stream_id)

    def test_reads_on_remote_close(self):
        # Prepare a socket so we can open a stream.
        sock = DummySocket()
        c = HTTP20Connection('www.google.com')
        c._sock = sock

        # Open a few requests (which creates a stream)
        s1 = c.request('GET', '/')
        s2 = c.request('GET', '/')

        # simulate state of blocking on read while sock
        f = GoAwayFrame(0)
        # Set error code to PROTOCOL_ERROR
        f.error_code = 1
        c._sock.buffer = BytesIO(f.serialize())

        # 'Receive' the GOAWAY frame.
        # Validate that the spec error name and description are used to throw
        # the connection exception.
        with pytest.raises(ConnectionError):
            c.get_response(s1)

        # try to read the stream
        with pytest.raises(StreamResetError):
            c.get_response(s2)

    def test_race_condition_on_socket_close(self):
        # Prepare a socket so we can open a stream.
        sock = DummySocket()
        c = HTTP20Connection('www.google.com')
        c._sock = sock

        # Open a few requests (which creates a stream)
        s1 = c.request('GET', '/')
        c.request('GET', '/')

        # simulate state of blocking on read while sock
        f = GoAwayFrame(0)
        # Set error code to PROTOCOL_ERROR
        f.error_code = 1
        c._sock.buffer = BytesIO(f.serialize())

        # 'Receive' the GOAWAY frame.
        # Validate that the spec error name and description are used to throw
        # the connection exception.
        with pytest.raises(ConnectionError):
            c.get_response(s1)

        # try to read again after close
        with pytest.raises(ConnectionError):
            c._single_read()

    def test_stream_close_behavior(self):
        # Prepare a socket so we can open a stream.
        sock = DummySocket()
        c = HTTP20Connection('www.google.com')
        c._sock = sock

        # Open a few requests (which creates a stream)
        s1 = c.request('GET', '/')
        c.request('GET', '/')

        # simulate state of blocking on read while sock
        f = GoAwayFrame(0)
        # Set error code to PROTOCOL_ERROR
        f.error_code = 1
        c._sock.buffer = BytesIO(f.serialize())

        # 'Receive' the GOAWAY frame.
        # Validate that the spec error name and description are used to throw
        # the connection exception.
        with pytest.raises(ConnectionError):
            c.get_response(s1)

        # try to read again after close
        with pytest.raises(ConnectionError):
            c._single_read()

    def test_read_headers_out_of_order(self):
        # If header blocks aren't decoded in the same order they're received,
        # regardless of the stream they belong to, the decoder state will
        # become corrupted.
        e = Encoder()
        h1 = HeadersFrame(1)
        h1.data = e.encode([(':status', 200), ('content-type', 'foo/bar')])
        h1.flags |= set(['END_HEADERS', 'END_STREAM'])
        h3 = HeadersFrame(3)
        h3.data = e.encode([(':status', 200), ('content-type', 'baz/qux')])
        h3.flags |= set(['END_HEADERS', 'END_STREAM'])
        sock = DummySocket()
        sock.buffer = BytesIO(h1.serialize() + h3.serialize())

        c = HTTP20Connection('www.google.com')
        c._sock = sock
        r1 = c.request('GET', '/a')
        r3 = c.request('GET', '/b')

        assert c.get_response(r3).headers == HTTPHeaderMap(
            [('content-type', 'baz/qux')]
        )
        assert c.get_response(r1).headers == HTTPHeaderMap(
            [('content-type', 'foo/bar')]
        )

    def test_headers_with_continuation(self):
        e = Encoder()
        header_data = e.encode([
            (':status', 200), ('content-type', 'foo/bar'),
            ('content-length', '0')
        ])
        h = HeadersFrame(1)
        h.data = header_data[0:int(len(header_data) / 2)]
        h.flags.add('END_STREAM')
        c = ContinuationFrame(1)
        c.data = header_data[int(len(header_data) / 2):]
        c.flags.add('END_HEADERS')
        sock = DummySocket()
        sock.buffer = BytesIO(h.serialize() + c.serialize())

        c = HTTP20Connection('www.google.com')
        c._sock = sock
        r = c.request('GET', '/')

        assert set(c.get_response(r).headers.iter_raw()) == set(
            [(b'content-type', b'foo/bar'), (b'content-length', b'0')]
        )

    def test_send_tolerate_peer_gone(self):
        class ErrorSocket(DummySocket):
            def sendall(self, data):
                raise socket.error(errno.EPIPE)

        c = HTTP20Connection('www.google.com')
        c._sock = ErrorSocket()
        f = SettingsFrame(0)
        with pytest.raises(socket.error):
            c._send_cb(f, False)
        c._sock = DummySocket()
        c._send_cb(f, True)  # shouldn't raise an error

    def test_connection_window_increments_appropriately(self, frame_buffer):
        e = Encoder()
        h = HeadersFrame(1)
        h.data = e.encode([(':status', 200), ('content-type', 'foo/bar')])
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

        frame_buffer.add_data(b''.join(sock.queue))
        queue = list(frame_buffer)
        assert len(queue) == 3  # one headers frame, two window update frames.
        assert isinstance(queue[1], WindowUpdateFrame)
        assert queue[1].window_increment == len(b'hi there sir')
        assert isinstance(queue[2], WindowUpdateFrame)
        assert queue[2].window_increment == len(b'hi there sir again')

    def test_stream_window_increments_appropriately(self, frame_buffer):
        e = Encoder()
        h = HeadersFrame(1)
        h.data = e.encode([(':status', 200), ('content-type', 'foo/bar')])
        h.flags = set(['END_HEADERS'])
        d = DataFrame(1)
        d.data = b'hi there sir'
        d2 = DataFrame(1)
        d2.data = b'hi there sir again'
        sock = DummySocket()
        sock.buffer = BytesIO(h.serialize() + d.serialize() + d2.serialize())

        c = HTTP20Connection('www.google.com')
        c._sock = sock
        c.request('GET', '/')
        c.streams[1]._in_window_manager.window_size = 1000
        c.streams[1]._in_window_manager.initial_window_size = 1000
        resp = c.get_response()
        resp.read(len(b'hi there sir'))
        resp.read(len(b'hi there sir again'))

        frame_buffer.add_data(b''.join(sock.queue))
        queue = list(frame_buffer)
        assert len(queue) == 3  # one headers frame, two window update frames.
        assert isinstance(queue[1], WindowUpdateFrame)
        assert queue[1].window_increment == len(b'hi there sir')
        assert isinstance(queue[2], WindowUpdateFrame)
        assert queue[2].window_increment == len(b'hi there sir again')

    def test_that_using_proxy_keeps_http_headers_intact(self):
        sock = DummySocket()
        c = HTTP20Connection(
            'www.google.com', secure=False, proxy_host='localhost'
        )
        c._sock = sock
        c.request('GET', '/')
        s = c.recent_stream

        assert list(s.headers.items()) == [
            (b':method', b'GET'),
            (b':scheme', b'http'),
            (b':authority', b'www.google.com'),
            (b':path', b'/'),
        ]

    def test_proxy_headers_presence_for_insecure_request(self):
        sock = DummySocket()
        c = HTTP20Connection(
            'www.google.com', secure=False, proxy_host='localhost',
            proxy_headers={'Proxy-Authorization': 'Basic ==='}
        )
        c._sock = sock
        c.request('GET', '/')
        s = c.recent_stream

        assert list(s.headers.items()) == [
            (b':method', b'GET'),
            (b':scheme', b'http'),
            (b':authority', b'www.google.com'),
            (b':path', b'/'),
            (b'proxy-authorization', b'Basic ==='),
        ]

    def test_proxy_headers_absence_for_secure_request(self):
        sock = DummySocket()
        c = HTTP20Connection(
            'www.google.com', secure=True, proxy_host='localhost',
            proxy_headers={'Proxy-Authorization': 'Basic ==='}
        )
        c._sock = sock
        c.request('GET', '/')
        s = c.recent_stream

        assert list(s.headers.items()) == [
            (b':method', b'GET'),
            (b':scheme', b'https'),
            (b':authority', b'www.google.com'),
            (b':path', b'/'),
        ]

    def test_recv_cb_n_times(self):
        sock = DummySocket()
        sock.can_read = True

        c = HTTP20Connection('www.google.com')
        c._sock = sock

        mutable = {'counter': 0}

        def consume_single_frame():
            mutable['counter'] += 1

        c._single_read = consume_single_frame
        c._recv_cb()

        assert mutable['counter'] == 10

    def test_sending_file(self, frame_buffer):
        # Prepare a socket so we can open a stream.
        sock = DummySocket()
        c = HTTP20Connection('www.google.com')
        c._sock = sock

        # Send a request that involves uploading a file handle.
        with open(__file__, 'rb') as f:
            c.request('GET', '/', body=f)

        # Get all the frames
        frame_buffer.add_data(b''.join(sock.queue))
        frames = list(frame_buffer)

        # Reconstruct the file from the sent data.
        sent_data = b''.join(
            f.data for f in frames if isinstance(f, DataFrame)
        )

        with open(__file__, 'rb') as f:
            assert f.read() == sent_data

    def test_closing_incomplete_stream(self, frame_buffer):
        # Prepare a socket so we can open a stream.
        sock = DummySocket()
        c = HTTP20Connection('www.google.com')
        c._sock = sock

        # Send a request that involves uploading some data, but don't finish.
        c.putrequest('POST', '/')
        c.endheaders(message_body=b'some data', final=False)

        # Close the stream.
        c.streams[1].close()

        # Get all the frames
        frame_buffer.add_data(b''.join(sock.queue))
        frames = list(frame_buffer)

        # The last one should be a RST_STREAM frame.
        f = frames[-1]
        assert isinstance(f, RstStreamFrame)
        assert 1 not in c.streams

    def test_incrementing_window_after_close(self):
        """
        Hyper does not attempt to increment the flow control window once the
        stream is closed.
        """
        # For this test, we want to send a response that has three frames at
        # the default max frame size (16,384 bytes). That will, on the third
        # frame, trigger the processing to increment the flow control window,
        # which should then not happen.
        f = SettingsFrame(0, settings={h2.settings.INITIAL_WINDOW_SIZE: 100})

        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()
        c._sock.buffer = BytesIO(f.serialize())

        # Open stream 1.
        c.request('GET', '/')

        # Check what data we've sent right now.
        originally_sent_data = c._sock.queue[:]

        # Swap out the buffer to get a GoAway frame.
        length = 16384
        total_length = (3 * 16384) + len(b'some more data')
        e = Encoder()
        h1 = HeadersFrame(1)
        h1.data = e.encode(
            [(':status', 200), ('content-length', '%d' % total_length)]
        )
        h1.flags |= set(['END_HEADERS'])

        d1 = DataFrame(1)
        d1.data = b'\x00' * length
        d2 = d1
        d3 = d1
        d4 = DataFrame(1)
        d4.data = b'some more data'
        d4.flags |= set(['END_STREAM'])

        buffer = BytesIO(
            b''.join(f.serialize() for f in [h1, d1, d2, d3, d4])
        )
        c._sock.buffer = buffer

        # Read the response
        resp = c.get_response(stream_id=1)
        assert resp.status == 200
        assert resp.read() == b''.join(
            [b'\x00' * (3 * length), b'some more data']
        )

        # We should have sent only one extra frame
        assert len(originally_sent_data) + 1 == len(c._sock.queue)


class FrameEncoderMixin(object):
    def setup_method(self, method):
        self.frames = []
        self.encoder = Encoder()
        self.conn = None

    def add_push_frame(self, stream_id, promised_stream_id, headers,
                       end_block=True):
        frame = PushPromiseFrame(stream_id)
        frame.promised_stream_id = promised_stream_id
        frame.data = self.encoder.encode(headers)
        if end_block:
            frame.flags.add('END_HEADERS')
        self.frames.append(frame)

    def add_headers_frame(self, stream_id, headers, end_block=True,
                          end_stream=False):
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


class TestServerPush(FrameEncoderMixin):
    def request(self, enable_push=True):
        self.conn = HTTP20Connection('www.google.com', enable_push=enable_push)
        self.conn._sock = DummySocket()
        self.conn._sock.buffer = BytesIO(
            b''.join([frame.serialize() for frame in self.frames])
        )
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
        assert dict(push_response.headers) == {
            b'content-type': [b'application/javascript']
        }
        assert push_response.read() == b'bar'

    def test_promise_before_headers(self):
        self.add_push_frame(
            1,
            2,
            [
                (':method', 'GET'),
                (':path', '/'),
                (':authority', 'www.google.com'),
                (':scheme', 'https'),
                ('accept-encoding', 'gzip')
            ]
        )
        self.add_headers_frame(
            1, [(':status', '200'), ('content-type', 'text/html')]
        )
        self.add_data_frame(1, b'foo', end_stream=True)
        self.add_headers_frame(
            2, [(':status', '200'), ('content-type', 'application/javascript')]
        )
        self.add_data_frame(2, b'bar', end_stream=True)

        self.request()
        assert len(list(self.conn.get_pushes())) == 0
        self.assert_response()
        self.assert_pushes()
        assert self.response.read() == b'foo'
        self.assert_push_response()

    def test_promise_after_headers(self):
        self.add_headers_frame(
            1, [(':status', '200'), ('content-type', 'text/html')]
        )
        self.add_push_frame(
            1,
            2,
            [
                (':method', 'GET'),
                (':path', '/'),
                (':authority', 'www.google.com'),
                (':scheme', 'https'),
                ('accept-encoding', 'gzip')
            ]
        )
        self.add_data_frame(1, b'foo', end_stream=True)
        self.add_headers_frame(
            2, [(':status', '200'), ('content-type', 'application/javascript')]
        )
        self.add_data_frame(2, b'bar', end_stream=True)

        self.request()
        assert len(list(self.conn.get_pushes())) == 0
        self.assert_response()
        assert self.response.read() == b'foo'
        self.assert_pushes()
        self.assert_push_response()

    def test_promise_after_data(self):
        self.add_headers_frame(
            1, [(':status', '200'), ('content-type', 'text/html')]
        )
        self.add_data_frame(1, b'fo')
        self.add_push_frame(
            1,
            2,
            [
                (':method', 'GET'),
                (':path', '/'),
                (':authority', 'www.google.com'),
                (':scheme', 'https'),
                ('accept-encoding', 'gzip')
            ]
        )
        self.add_data_frame(1, b'o', end_stream=True)
        self.add_headers_frame(
            2, [(':status', '200'), ('content-type', 'application/javascript')]
        )
        self.add_data_frame(2, b'bar', end_stream=True)

        self.request()
        assert len(list(self.conn.get_pushes())) == 0
        self.assert_response()
        assert self.response.read() == b'foo'
        self.assert_pushes()
        self.assert_push_response()

    def test_capture_all_promises(self):
        self.add_push_frame(
            1,
            2,
            [
                (':method', 'GET'),
                (':path', '/one'),
                (':authority', 'www.google.com'),
                (':scheme', 'https'),
                ('accept-encoding', 'gzip')
            ]
        )
        self.add_headers_frame(
            1, [(':status', '200'), ('content-type', 'text/html')]
        )
        self.add_push_frame(
            1,
            4,
            [
                (':method', 'GET'),
                (':path', '/two'),
                (':authority', 'www.google.com'),
                (':scheme', 'https'),
                ('accept-encoding', 'gzip')
            ]
        )
        self.add_data_frame(1, b'foo', end_stream=True)
        self.add_headers_frame(
            4, [(':status', '200'), ('content-type', 'application/javascript')]
        )
        self.add_headers_frame(
            2, [(':status', '200'), ('content-type', 'application/javascript')]
        )
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
        self.add_push_frame(
            1,
            2,
            [
                (':method', 'GET'),
                (':path', '/'),
                (':authority', 'www.google.com'),
                (':scheme', 'https'),
                ('accept-encoding', 'gzip')
            ]
        )
        self.add_headers_frame(
            1, [(':status', '200'), ('content-type', 'text/html')]
        )

        self.request()
        self.conn.get_response()
        list(self.conn.get_pushes())[0].cancel()

        f = RstStreamFrame(2)
        f.error_code = 8
        assert self.conn._sock.queue[-1] == f.serialize()

    def test_reset_pushed_streams_when_push_disabled(self):
        self.add_push_frame(
            1,
            2,
            [
                (':method', 'GET'),
                (':path', '/'),
                (':authority', 'www.google.com'),
                (':scheme', 'https'),
                ('accept-encoding', 'gzip')
            ]
        )
        self.add_headers_frame(
            1, [(':status', '200'), ('content-type', 'text/html')]
        )

        self.request(False)
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


class TestResponse(object):
    def test_status_is_stripped_from_headers(self):
        headers = HTTPHeaderMap([(':status', '200')])
        resp = HTTP20Response(headers, None)

        assert resp.status == 200
        assert not resp.headers

    def test_response_transparently_decrypts_gzip(self):
        headers = HTTPHeaderMap(
            [(':status', '200'), ('content-encoding', 'gzip')]
        )
        c = zlib_compressobj(wbits=25)
        body = c.compress(b'this is test data')
        body += c.flush()
        resp = HTTP20Response(headers, DummyStream(body))

        assert resp.read() == b'this is test data'

    def test_response_transparently_decrypts_brotli(self):
        headers = HTTPHeaderMap(
            [(':status', '200'), ('content-encoding', 'br')]
        )
        body = brotli.compress(b'this is test data')
        resp = HTTP20Response(headers, DummyStream(body))

        assert resp.read() == b'this is test data'

    def test_response_transparently_decrypts_real_deflate(self):
        headers = HTTPHeaderMap(
            [(':status', '200'), ('content-encoding', 'deflate')]
        )
        c = zlib_compressobj(wbits=zlib.MAX_WBITS)
        body = c.compress(b'this is test data')
        body += c.flush()
        resp = HTTP20Response(headers, DummyStream(body))

        assert resp.read() == b'this is test data'

    def test_response_transparently_decrypts_wrong_deflate(self):
        headers = HTTPHeaderMap(
            [(':status', '200'), ('content-encoding', 'deflate')]
        )
        c = zlib_compressobj(wbits=-zlib.MAX_WBITS)
        body = c.compress(b'this is test data')
        body += c.flush()
        resp = HTTP20Response(headers, DummyStream(body))

        assert resp.read() == b'this is test data'

    def test_response_ignored_unsupported_compression(self):
        headers = HTTPHeaderMap(
            [(':status', '200'), ('content-encoding', 'invalid')]
        )
        body = b'this is test data'
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

        with HTTP20Response(headers, stream):
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
        headers = HTTPHeaderMap(
            [(':status', '200'), ('content-type', 'application/json')]
        )
        stream = DummyStream(b'')
        resp = HTTP20Response(headers, stream)

        assert resp.headers[b'content-type'] == [b'application/json']

    def test_response_ignores_unknown_headers(self):
        headers = HTTPHeaderMap(
            [(':status', '200'), (':reserved', 'yes'), ('no', 'no')]
        )
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
        headers = HTTPHeaderMap(
            [(':status', '200'), ('content-encoding', 'gzip')]
        )
        c = zlib_compressobj(wbits=25)
        body = c.compress(b'this is test data')
        body += c.flush()

        stream = DummyStream(None)
        chunks = [body[x:x + 2] for x in range(0, len(body), 2)]
        stream.data_frames = chunks
        resp = HTTP20Response(headers, stream)

        received = b''
        for chunk in resp.read_chunked():
            received += chunk

        assert received == b'this is test data'

    def test_response_version(self):
        r = HTTP20Response(HTTPHeaderMap([(':status', '200')]), None)
        assert r.version is HTTPVersion.http20


class TestHTTP20Adapter(object):
    def test_adapter_reuses_connections(self):
        a = HTTP20Adapter()
        conn1 = a.get_connection('http2bin.org', 80, 'http')
        conn2 = a.get_connection('http2bin.org', 80, 'http')

        assert conn1 is conn2

    def test_adapter_accept_client_certificate(self):
        a = HTTP20Adapter()
        conn1 = a.get_connection(
            'http2bin.org',
            80,
            'http',
            cert=CLIENT_PEM_FILE)
        conn2 = a.get_connection(
            'http2bin.org',
            80,
            'http',
            cert=CLIENT_PEM_FILE)
        assert conn1 is conn2
        assert conn1._conn.ssl_context.check_hostname
        assert conn1._conn.ssl_context.verify_mode == ssl.CERT_REQUIRED

    def test_adapter_respects_disabled_ca_verification(self):
        a = HTTP20Adapter()
        conn = a.get_connection(
            'http2bin.org',
            80,
            'http',
            verify=False,
            cert=CLIENT_PEM_FILE)
        assert not conn._conn.ssl_context.check_hostname
        assert conn._conn.ssl_context.verify_mode == ssl.CERT_NONE

    def test_adapter_respects_custom_ca_verification(self):
        a = HTTP20Adapter()
        conn = a.get_connection(
            'http2bin.org',
            80,
            'http',
            verify=SERVER_CERT_FILE)
        assert conn._conn.ssl_context.check_hostname
        assert conn._conn.ssl_context.verify_mode == ssl.CERT_REQUIRED


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
                import nghttp2  # noqa

        assert True

    def test_stripping_connection_header(self):
        headers = [(b'one', b'two'), (b'connection', b'close')]
        stripped = [(b'one', b'two')]

        assert h2_safe_headers(headers) == stripped

    def test_stripping_related_headers(self):
        headers = [
            (b'one', b'two'), (b'three', b'four'), (b'five', b'six'),
            (b'connection', b'close, three, five')
        ]
        stripped = [(b'one', b'two')]

        assert h2_safe_headers(headers) == stripped

    def test_stripping_multiple_connection_headers(self):
        headers = [
            (b'one', b'two'), (b'three', b'four'), (b'five', b'six'),
            (b'connection', b'close'),
            (b'connection', b'three, five')
        ]
        stripped = [(b'one', b'two')]

        assert h2_safe_headers(headers) == stripped

    def test_goaway_frame_PROTOCOL_ERROR(self):
        f = GoAwayFrame(0)
        # Set error code to PROTOCOL_ERROR
        f.error_code = 1

        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()
        c._sock.buffer = BytesIO(f.serialize())

        # 'Receive' the GOAWAY frame.
        # Validate that the spec error name and description are used to throw
        # the connection exception.
        with pytest.raises(ConnectionError) as conn_err:
            c._single_read()

        err_msg = str(conn_err)
        name, number, description = errors.get_data(1)

        assert name in err_msg
        assert number in err_msg
        assert description in err_msg

    def test_goaway_frame_HTTP_1_1_REQUIRED(self):
        f = GoAwayFrame(0)
        # Set error code to HTTP_1_1_REQUIRED
        f.error_code = 13

        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()
        c._sock.buffer = BytesIO(f.serialize())

        # 'Receive' the GOAWAY frame.
        # Validate that the spec error name and description are used to throw
        # the connection exception.
        with pytest.raises(ConnectionError) as conn_err:
            c._single_read()

        err_msg = str(conn_err)
        name, number, description = errors.get_data(13)

        assert name in err_msg
        assert number in err_msg
        assert description in err_msg

    def test_goaway_frame_NO_ERROR(self):
        f = GoAwayFrame(0)
        # Set error code to NO_ERROR
        f.error_code = 0

        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()
        c._sock.buffer = BytesIO(f.serialize())

        # 'Receive' the GOAWAY frame.
        # Test makes sure no exception is raised; error code 0 means we are
        # dealing with a standard and graceful shutdown.
        c._single_read()

    def test_goaway_frame_invalid_error_code(self):
        f = GoAwayFrame(0)
        # Set error code to non existing error
        f.error_code = 100

        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()
        c._sock.buffer = BytesIO(f.serialize())

        # 'Receive' the GOAWAY frame.
        # If the error code does not exist in the spec then the additional
        # data is used instead.
        with pytest.raises(ConnectionError) as conn_err:
            c._single_read()

        err_msg = str(conn_err)
        with pytest.raises(ValueError):
            name, number, description = errors.get_data(100)

        assert str(f.error_code) in err_msg

    def test_resetting_streams_after_close(self):
        """
        Attempts to reset streams when the connection is torn down are
        tolerated.
        """
        f = SettingsFrame(0)

        c = HTTP20Connection('www.google.com')
        c._sock = DummySocket()
        c._sock.buffer = BytesIO(f.serialize())

        # Open stream 1.
        c.request('GET', '/')

        # Swap out the buffer to get a GoAway frame.
        f = GoAwayFrame(0)
        f.error_code = 1
        c._sock.buffer = BytesIO(f.serialize())

        # "Read" the GoAway
        with pytest.raises(ConnectionError):
            c._single_read()


class TestUpgradingPush(FrameEncoderMixin):
    http101 = (b"HTTP/1.1 101 Switching Protocols\r\n"
               b"Connection: upgrade\r\n"
               b"Upgrade: h2c\r\n"
               b"\r\n")

    def request(self, enable_push=True):
        self.frames = [SettingsFrame(0)] + self.frames  # Server side preface
        self.conn = HTTPConnection('www.google.com', enable_push=enable_push)
        self.conn._conn._sock = DummySocket()
        self.conn._conn._sock.buffer = BytesIO(
            self.http101 + b''.join([frame.serialize()
                                     for frame in self.frames])
        )
        self.conn.request('GET', '/')

    def assert_response(self):
        self.response = self.conn.get_response()
        assert self.response.status == 200
        assert dict(self.response.headers) == {b'content-type': [b'text/html']}

    def assert_pushes(self):
        self.pushes = list(self.conn.get_pushes())
        assert len(self.pushes) == 1
        assert self.pushes[0].method == b'GET'
        assert self.pushes[0].scheme == b'http'
        assert self.pushes[0].authority == b'www.google.com'
        assert self.pushes[0].path == b'/'
        expected_headers = {b'accept-encoding': [b'gzip']}
        assert dict(self.pushes[0].request_headers) == expected_headers

    def assert_push_response(self):
        push_response = self.pushes[0].get_response()
        assert push_response.status == 200
        assert dict(push_response.headers) == {
            b'content-type': [b'application/javascript']
        }
        assert push_response.read() == b'bar'

    def test_promise_before_headers(self):
        # Current implementation only support get_pushes call
        # after get_response
        pass

    def test_promise_after_headers(self):
        self.add_headers_frame(
            1, [(':status', '200'), ('content-type', 'text/html')]
        )
        self.add_push_frame(
            1,
            2,
            [
                (':method', 'GET'),
                (':path', '/'),
                (':authority', 'www.google.com'),
                (':scheme', 'http'),
                ('accept-encoding', 'gzip')
            ]
        )
        self.add_data_frame(1, b'foo', end_stream=True)
        self.add_headers_frame(
            2, [(':status', '200'), ('content-type', 'application/javascript')]
        )
        self.add_data_frame(2, b'bar', end_stream=True)

        self.request()
        self.assert_response()
        assert self.response.read() == b'foo'
        self.assert_pushes()
        self.assert_push_response()

    def test_promise_after_data(self):
        self.add_headers_frame(
            1, [(':status', '200'), ('content-type', 'text/html')]
        )
        self.add_data_frame(1, b'fo')
        self.add_push_frame(
            1,
            2,
            [
                (':method', 'GET'),
                (':path', '/'),
                (':authority', 'www.google.com'),
                (':scheme', 'http'),
                ('accept-encoding', 'gzip')
            ]
        )
        self.add_data_frame(1, b'o', end_stream=True)
        self.add_headers_frame(
            2, [(':status', '200'), ('content-type', 'application/javascript')]
        )
        self.add_data_frame(2, b'bar', end_stream=True)

        self.request()
        self.assert_response()
        assert self.response.read() == b'foo'
        self.assert_pushes()
        self.assert_push_response()

    def test_capture_all_promises(self):
        # Current implementation does not support capture_all
        # for h2c upgrading connection.
        pass

    def test_cancel_push(self):
        self.add_push_frame(
            1,
            2,
            [
                (':method', 'GET'),
                (':path', '/'),
                (':authority', 'www.google.com'),
                (':scheme', 'http'),
                ('accept-encoding', 'gzip')
            ]
        )
        self.add_headers_frame(
            1, [(':status', '200'), ('content-type', 'text/html')]
        )

        self.request()
        self.conn.get_response()
        list(self.conn.get_pushes())[0].cancel()

        f = RstStreamFrame(2)
        f.error_code = 8
        assert self.conn._sock.queue[-1] == f.serialize()

    def test_reset_pushed_streams_when_push_disabled(self):
        self.add_push_frame(
            1,
            2,
            [
                (':method', 'GET'),
                (':path', '/'),
                (':authority', 'www.google.com'),
                (':scheme', 'http'),
                ('accept-encoding', 'gzip')
            ]
        )
        self.add_headers_frame(
            1, [(':status', '200'), ('content-type', 'text/html')]
        )

        self.request(False)
        self.conn.get_response()

        f = RstStreamFrame(2)
        f.error_code = 7
        assert self.conn._sock.queue[-1].endswith(f.serialize())


# Some utility classes for the tests.
class NullEncoder(object):
    @staticmethod
    def encode(headers):

        def to_str(v):
            if is_py2:
                return str(v)
            else:
                if not isinstance(v, str):
                    v = str(v, 'utf-8')
                return v

        return '\n'.join("%s%s" % (to_str(name), to_str(val))
                         for name, val in headers)


class FixedDecoder(object):
    def __init__(self, result):
        self.result = result

    def decode(self, headers):
        return self.result


class DummySocket(object):
    def __init__(self):
        self.queue = []
        self._buffer = BytesIO()
        self._read_counter = 0
        self.can_read = False

    @property
    def buffer(self):
        return memoryview(self._buffer.getvalue()[self._read_counter:])

    @buffer.setter
    def buffer(self, value):
        self._buffer = value
        self._read_counter = 0

    def advance_buffer(self, amt):
        self._read_counter += amt
        self._buffer.read(amt)

    def send(self, data):
        self.queue.append(data)

    sendall = send

    def recv(self, l):
        data = self._buffer.read(l)
        self._read_counter += len(data)
        return memoryview(data)

    def close(self):
        pass

    def fill(self):
        pass


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
