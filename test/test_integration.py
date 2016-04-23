# -*- coding: utf-8 -*-
"""
test/integration
~~~~~~~~~~~~~~~~

This file defines integration-type tests for hyper. These are still not fully
hitting the network, so that's alright.
"""
import requests
import threading
import time
import hyper
import hyper.http11.connection
import pytest
from h2.frame_buffer import FrameBuffer
from hyper.compat import ssl
from hyper.contrib import HTTP20Adapter
from hyperframe.frame import (
    Frame, SettingsFrame, WindowUpdateFrame, DataFrame, HeadersFrame,
    GoAwayFrame, RstStreamFrame
)
from hpack.hpack import Encoder
from hpack.huffman import HuffmanEncoder
from hpack.huffman_constants import (
    REQUEST_CODES, REQUEST_CODES_LENGTH
)
from hyper.http20.exceptions import ConnectionError, StreamResetError
from server import SocketLevelTest

# Turn off certificate verification for the tests.
if ssl is not None:
    hyper.tls._context = hyper.tls.init_context()
    hyper.tls._context.check_hostname = False
    hyper.tls._context.verify_mode = ssl.CERT_NONE

    # Cover our bases because NPN doesn't yet work on all our test platforms.
    hyper.http20.connection.H2_NPN_PROTOCOLS += ['', None]


def decode_frame(frame_data):
    f, length = Frame.parse_frame_header(frame_data[:9])
    f.parse_body(memoryview(frame_data[9:9 + length]))
    assert 9 + length == len(frame_data)
    return f


def build_headers_frame(headers, encoder=None):
    f = HeadersFrame(1)
    e = encoder
    if e is None:
        e = Encoder()
        e.huffman_coder = HuffmanEncoder(REQUEST_CODES, REQUEST_CODES_LENGTH)
    f.data = e.encode(headers)
    f.flags.add('END_HEADERS')
    return f


@pytest.fixture
def frame_buffer():
    buffer = FrameBuffer()
    buffer.max_frame_size = 65535
    return buffer


def receive_preamble(sock):
    # Receive the HTTP/2 'preamble'.
    first = sock.recv(65535)

    # Work around some bugs: if the first message received was only the PRI
    # string, aim to receive a settings frame as well.
    if len(first) <= len(b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n'):
        sock.recv(65535)
    sock.send(SettingsFrame(0).serialize())
    sock.recv(65535)
    return


class TestHyperIntegration(SocketLevelTest):
    # These are HTTP/2 tests.
    h2 = True

    def test_connection_string(self):
        self.set_up()

        # Confirm that we send the connection upgrade string and the initial
        # SettingsFrame.
        data = []
        send_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            # We should get one big chunk.
            first = sock.recv(65535)
            data.append(first)

            # We need to send back a SettingsFrame.
            f = SettingsFrame(0)
            sock.send(f.serialize())

            send_event.set()
            sock.close()

        self._start_server(socket_handler)
        conn = self.get_connection()
        conn.connect()
        send_event.wait(5)

        assert data[0].startswith(b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n')

        self.tear_down()

    def test_initial_settings(self, frame_buffer):
        self.set_up()

        # Confirm that we send the connection upgrade string and the initial
        # SettingsFrame.
        data = []
        send_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            # We get one big chunk.
            first = sock.recv(65535)
            data.append(first)

            # We need to send back a SettingsFrame.
            f = SettingsFrame(0)
            sock.send(f.serialize())

            send_event.set()
            sock.close()

        self._start_server(socket_handler)
        conn = self.get_connection()
        conn.connect()
        send_event.wait()

        # Get the chunk of data after the preamble and decode it into frames.
        # We actually expect two, but only the second one contains ENABLE_PUSH.
        preamble_size = len(b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n')
        data = data[0][preamble_size:]
        frame_buffer.add_data(data)
        frames = list(frame_buffer)
        f = frames[1]

        assert isinstance(f, SettingsFrame)
        assert f.stream_id == 0
        assert f.settings == {
            SettingsFrame.ENABLE_PUSH: 0,
        }

        self.tear_down()

    def test_stream_level_window_management(self):
        self.set_up()
        data = []
        send_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            # Dispose of the first packet.
            sock.recv(65535)

            # Send a Settings frame that reduces the flow-control window to
            # 64 bytes.
            f = SettingsFrame(0)
            f.settings[SettingsFrame.INITIAL_WINDOW_SIZE] = 64
            sock.send(f.serialize())

            # Grab three frames, the settings ACK, the initial headers frame,
            # and the first data frame.
            for x in range(0, 3):
                data.append(sock.recv(65535))

            # Send a WindowUpdate giving more window room to the stream.
            f = WindowUpdateFrame(1)
            f.window_increment = 64
            sock.send(f.serialize())

            # Send one that gives more room to the connection.
            f = WindowUpdateFrame(0)
            f.window_increment = 64
            sock.send(f.serialize())

            # Reeive the remaining frame.
            data.append(sock.recv(65535))
            send_event.set()

            # We're done.
            sock.close()

        self._start_server(socket_handler)
        conn = self.get_connection()

        conn.putrequest('GET', '/')
        conn.endheaders()

        # Send the first data chunk. This is 32 bytes.
        sd = b'a' * 32
        conn.send(sd)

        # Send the second one. This should block until the WindowUpdate comes
        # in.
        sd = sd * 2
        conn.send(sd, final=True)
        assert send_event.wait(0.3)

        # Decode the frames.
        frames = [decode_frame(d) for d in data]

        # We care about the last two. The first should be a data frame
        # containing 32 bytes.
        assert (isinstance(frames[-2], DataFrame) and
                not isinstance(frames[-2], HeadersFrame))
        assert len(frames[-2].data) == 32

        # The second should be a data frame containing 64 bytes.
        assert isinstance(frames[-1], DataFrame)
        assert len(frames[-1].data) == 64

        self.tear_down()

    def test_connection_context_manager(self):
        self.set_up()

        data = []
        send_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            first = sock.recv(65535)
            data.append(first)

            # We need to send back a SettingsFrame.
            f = SettingsFrame(0)
            sock.send(f.serialize())

            send_event.wait()
            sock.recv(65535)
            sock.close()

        self._start_server(socket_handler)
        with self.get_connection() as conn:
            conn.connect()

        send_event.set()

        # Check that we closed the connection.
        assert conn._sock is None

        self.tear_down()

    def test_closed_responses_remove_their_streams_from_conn(self):
        self.set_up()

        recv_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            # We're going to get the two messages for the connection open, then
            # a headers frame.
            receive_preamble(sock)
            sock.recv(65535)

            # Now, send the headers for the response.
            f = build_headers_frame([(':status', '200')])
            f.stream_id = 1
            sock.send(f.serialize())

            # Wait for the message from the main thread.
            recv_event.set()
            sock.close()

        self._start_server(socket_handler)
        conn = self.get_connection()
        conn.request('GET', '/')
        resp = conn.get_response()

        # Close the response.
        resp.close()

        recv_event.wait(5)

        assert not conn.streams

        self.tear_down()

    def test_receiving_responses_with_no_body(self):
        self.set_up()

        recv_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            # We get two messages for the connection open and then a HEADERS
            # frame.
            receive_preamble(sock)
            sock.recv(65535)

            # Now, send the headers for the response. This response has no body
            f = build_headers_frame(
                [(':status', '204'), ('content-length', '0')]
            )
            f.flags.add('END_STREAM')
            f.stream_id = 1
            sock.send(f.serialize())

            # Wait for the message from the main thread.
            recv_event.set()
            sock.close()

        self._start_server(socket_handler)
        conn = self.get_connection()
        conn.request('GET', '/')
        resp = conn.get_response()

        # Confirm the status code.
        assert resp.status == 204

        # Confirm that we can read this, but it has no body.
        assert resp.read() == b''
        assert resp._stream._in_window_manager.document_size == 0

        # Awesome, we're done now.
        recv_event.wait(5)

        self.tear_down()

    def test_receiving_trailers(self):
        self.set_up()

        recv_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            e = Encoder()

            # We get two messages for the connection open and then a HEADERS
            # frame.
            receive_preamble(sock)
            sock.recv(65535)

            # Now, send the headers for the response.
            f = build_headers_frame(
                [(':status', '200'), ('content-length', '14')],
                e
            )
            f.stream_id = 1
            sock.send(f.serialize())

            # Also send a data frame.
            f = DataFrame(1)
            f.data = b'have some data'
            sock.send(f.serialize())

            # Now, send a headers frame again, containing trailing headers.
            f = build_headers_frame([(':res', 'no'), ('trailing', 'sure')], e)
            f.flags.add('END_STREAM')
            f.stream_id = 1
            sock.send(f.serialize())

            # Wait for the message from the main thread.
            recv_event.set()
            sock.close()

        self._start_server(socket_handler)
        conn = self.get_connection()
        conn.request('GET', '/')
        resp = conn.get_response()

        # Confirm the status code.
        assert resp.status == 200

        # Confirm that we can read this.
        assert resp.read() == b'have some data'
        assert resp._stream._in_window_manager.document_size == 14

        # Confirm that we got the trailing headers, and that they don't contain
        # reserved headers.
        assert resp.trailers['trailing'] == [b'sure']
        assert resp.trailers.get(':res') is None
        assert len(resp.headers) == 1
        assert len(resp.trailers) == 1

        # Awesome, we're done now.
        recv_event.wait(5)

        self.tear_down()

    def test_receiving_trailers_before_reading(self):
        self.set_up()

        recv_event = threading.Event()
        wait_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            e = Encoder()

            # We get two messages for the connection open and then a HEADERS
            # frame.
            receive_preamble(sock)
            sock.recv(65535)

            # Now, send the headers for the response.
            f = build_headers_frame(
                [(':status', '200'), ('content-length', '14')],
                e
            )
            f.stream_id = 1
            sock.send(f.serialize())

            # Also send a data frame.
            f = DataFrame(1)
            f.data = b'have some data'
            sock.send(f.serialize())

            # Wait for the main thread to signal that it wants the trailers,
            # then delay slightly.
            wait_event.wait(5)
            time.sleep(0.5)

            # Now, send a headers frame again, containing trailing headers.
            f = build_headers_frame([(':res', 'no'), ('trailing', 'sure')], e)
            f.flags.add('END_STREAM')
            f.stream_id = 1
            sock.send(f.serialize())

            # Wait for the message from the main thread.
            recv_event.set()
            sock.close()

        self._start_server(socket_handler)
        conn = self.get_connection()
        conn.request('GET', '/')
        resp = conn.get_response()

        # Confirm the status code.
        assert resp.status == 200

        # Ask for the trailers.
        wait_event.set()

        # Confirm that we got the trailing headers, and that they don't contain
        # reserved headers. More importantly, check the trailers *first*,
        # before we read from the stream.
        assert resp.trailers['trailing'] == [b'sure']
        assert resp.trailers.get(':res') is None
        assert len(resp.headers) == 1
        assert len(resp.trailers) == 1

        # Confirm that the stream is still readable.
        assert resp.read() == b'have some data'
        assert resp._stream._in_window_manager.document_size == 14

        # Awesome, we're done now.
        recv_event.wait(5)

        self.tear_down()

    def test_clean_shut_down(self):
        self.set_up()

        recv_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            # We should get one packet. Rather than respond to it, send a
            # GOAWAY frame with error code 0 indicating clean shutdown.
            sock.recv(65535)

            # Now, send the shut down.
            f = GoAwayFrame(0)
            f.error_code = 0
            sock.send(f.serialize())

            # Wait for the message from the main thread.
            recv_event.set()
            sock.close()

        self._start_server(socket_handler)
        conn = self.get_connection()
        conn.connect()

        # Confirm the connection is closed.
        assert conn._sock is None

        # Awesome, we're done now.
        recv_event.wait(5)

        self.tear_down()

    def test_unexpected_shut_down(self):
        self.set_up()

        recv_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            # We should get one packet. Rather than respond to it, send a
            # GOAWAY frame with error code 0 indicating clean shutdown.
            sock.recv(65535)

            # Now, send the shut down.
            f = GoAwayFrame(0)
            f.error_code = 1
            sock.send(f.serialize())

            # Wait for the message from the main thread.
            sock.close()
            recv_event.set()

        self._start_server(socket_handler)
        conn = self.get_connection()

        with pytest.raises(ConnectionError):
            conn.connect()

        # Confirm the connection is closed.
        assert conn._sock is None

        # Awesome, we're done now.
        recv_event.wait(5)

        self.tear_down()

    def test_insecure_connection(self):
        self.set_up(secure=False)

        data = []
        send_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            receive_preamble(sock)

            data.append(sock.recv(65535))
            send_event.wait(5)

            h = HeadersFrame(1)
            h.data = self.get_encoder().encode(
                [
                    (':status', 200),
                    ('content-type', 'not/real'),
                    ('content-length', 14),
                    ('server', 'socket-level-server')
                ]
            )
            h.flags.add('END_HEADERS')
            sock.send(h.serialize())

            d = DataFrame(1)
            d.data = b'nsaislistening'
            d.flags.add('END_STREAM')
            sock.send(d.serialize())

            sock.close()

        self._start_server(socket_handler)
        c = self.get_connection()
        c.request('GET', '/')
        send_event.set()
        r = c.get_response()

        assert r.status == 200
        assert len(r.headers) == 3
        assert r.headers[b'server'] == [b'socket-level-server']
        assert r.headers[b'content-length'] == [b'14']
        assert r.headers[b'content-type'] == [b'not/real']

        assert r.read() == b'nsaislistening'

        self.tear_down()

    def test_proxy_connection(self):
        self.set_up(proxy=True)

        data = []
        send_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            receive_preamble(sock)

            data.append(sock.recv(65535))
            send_event.wait(5)

            h = HeadersFrame(1)
            h.data = self.get_encoder().encode(
                [
                    (':status', 200),
                    ('content-type', 'not/real'),
                    ('content-length', 12),
                    ('server', 'socket-level-server')
                ]
            )
            h.flags.add('END_HEADERS')
            sock.send(h.serialize())

            d = DataFrame(1)
            d.data = b'thisisaproxy'
            d.flags.add('END_STREAM')
            sock.send(d.serialize())

            sock.close()

        self._start_server(socket_handler)
        c = self.get_connection()
        c.request('GET', '/')
        send_event.set()
        r = c.get_response()

        assert r.status == 200
        assert len(r.headers) == 3
        assert r.headers[b'server'] == [b'socket-level-server']
        assert r.headers[b'content-length'] == [b'12']
        assert r.headers[b'content-type'] == [b'not/real']

        assert r.read() == b'thisisaproxy'

        self.tear_down()

    def test_resetting_stream_with_frames_in_flight(self):
        """
        Hyper emits only one RST_STREAM frame, despite the other frames in
        flight.
        """
        self.set_up()

        recv_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            # We get two messages for the connection open and then a HEADERS
            # frame.
            receive_preamble(sock)
            sock.recv(65535)

            # Now, send the headers for the response. This response has no
            # body.
            f = build_headers_frame(
                [(':status', '204'), ('content-length', '0')]
            )
            f.flags.add('END_STREAM')
            f.stream_id = 1
            sock.send(f.serialize())

            # Wait for the message from the main thread.
            recv_event.wait(5)
            sock.close()

        self._start_server(socket_handler)
        conn = self.get_connection()
        stream_id = conn.request('GET', '/')

        # Now, trigger the RST_STREAM frame by closing the stream.
        conn._send_rst_frame(stream_id, 0)

        # Now, eat the Headers frame. This should not cause an exception.
        conn._recv_cb()

        # However, attempting to get the response should.
        with pytest.raises(KeyError):
            conn.get_response(stream_id)

        # Awesome, we're done now.
        recv_event.set()

        self.tear_down()

    def test_stream_can_be_reset_multiple_times(self):
        """
        Confirm that hyper gracefully handles receiving multiple RST_STREAM
        frames.
        """
        self.set_up()

        recv_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            # We get two messages for the connection open and then a HEADERS
            # frame.
            receive_preamble(sock)
            sock.recv(65535)

            # Now, send two RST_STREAM frames.
            for _ in range(0, 2):
                f = RstStreamFrame(1)
                sock.send(f.serialize())

            # Wait for the message from the main thread.
            recv_event.wait(5)
            sock.close()

        self._start_server(socket_handler)
        conn = self.get_connection()
        conn.request('GET', '/')

        # Now, eat the RstStream frames. The first one throws a
        # StreamResetError.
        with pytest.raises(StreamResetError):
            conn._single_read()

        # The next should throw no exception.
        conn._single_read()

        assert conn.reset_streams == set([1])

        # Awesome, we're done now.
        recv_event.set()

        self.tear_down()

    def test_read_chunked_http2(self):
        self.set_up()

        recv_event = threading.Event()
        wait_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            # We get two messages for the connection open and then a HEADERS
            # frame.
            receive_preamble(sock)
            sock.recv(65535)

            # Now, send the headers for the response. This response has a body.
            f = build_headers_frame([(':status', '200')])
            f.stream_id = 1
            sock.send(f.serialize())

            # Send the first two chunks.
            f = DataFrame(1)
            f.data = b'hello'
            sock.sendall(f.serialize())
            f = DataFrame(1)
            f.data = b'there'
            sock.sendall(f.serialize())

            # Now, delay a bit. We want to wait a half a second before we send
            # the next frame.
            wait_event.wait(5)
            time.sleep(0.5)
            f = DataFrame(1)
            f.data = b'world'
            f.flags.add('END_STREAM')
            sock.sendall(f.serialize())

            # Wait for the message from the main thread.
            recv_event.set()
            sock.close()

        self._start_server(socket_handler)
        conn = self.get_connection()
        conn.request('GET', '/')
        resp = conn.get_response()

        # Confirm the status code.
        assert resp.status == 200

        # Confirm that we can read this, but it has no body. First two chunks
        # should be easy, then set the event and read the next one.
        chunks = resp.read_chunked()
        first_chunk = next(chunks)
        second_chunk = next(chunks)
        wait_event.set()
        third_chunk = next(chunks)

        with pytest.raises(StopIteration):
            next(chunks)

        assert first_chunk == b'hello'
        assert second_chunk == b'there'
        assert third_chunk == b'world'

        # Awesome, we're done now.
        recv_event.wait(5)

        self.tear_down()

    def test_read_delayed(self):
        self.set_up()

        recv_event = threading.Event()
        wait_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            # We get two messages for the connection open and then a HEADERS
            # frame.
            receive_preamble(sock)
            sock.recv(65535)

            # Now, send the headers for the response. This response has a body.
            f = build_headers_frame([(':status', '200')])
            f.stream_id = 1
            sock.send(f.serialize())

            # Send the first two chunks.
            f = DataFrame(1)
            f.data = b'hello'
            sock.sendall(f.serialize())
            f = DataFrame(1)
            f.data = b'there'
            sock.sendall(f.serialize())

            # Now, delay a bit. We want to wait a half a second before we send
            # the next frame.
            wait_event.wait(5)
            time.sleep(0.5)
            f = DataFrame(1)
            f.data = b'world'
            f.flags.add('END_STREAM')
            sock.sendall(f.serialize())

            # Wait for the message from the main thread.
            recv_event.set()
            sock.close()

        self._start_server(socket_handler)
        conn = self.get_connection()
        conn.request('GET', '/')
        resp = conn.get_response()

        # Confirm the status code.
        assert resp.status == 200

        first_chunk = resp.read(10)
        wait_event.set()
        second_chunk = resp.read(5)

        assert first_chunk == b'hellothere'
        assert second_chunk == b'world'

        # Awesome, we're done now.
        recv_event.wait(5)

        self.tear_down()


class TestRequestsAdapter(SocketLevelTest):
    # This uses HTTP/2.
    h2 = True

    def test_adapter_received_values(self, monkeypatch):
        self.set_up()

        # We need to patch the ssl_wrap_socket method to ensure that we
        # forcefully upgrade.
        old_wrap_socket = hyper.http11.connection.wrap_socket

        def wrap(*args):
            sock, _ = old_wrap_socket(*args)
            return sock, 'h2'

        monkeypatch.setattr(hyper.http11.connection, 'wrap_socket', wrap)

        data = []
        send_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            # Do the handshake: conn header, settings, send settings, recv ack.
            receive_preamble(sock)

            # Now expect some data. One headers frame.
            data.append(sock.recv(65535))

            # Respond!
            h = HeadersFrame(1)
            h.data = self.get_encoder().encode(
                [
                    (':status', 200),
                    ('content-type', 'not/real'),
                    ('content-length', 20),
                ]
            )
            h.flags.add('END_HEADERS')
            sock.send(h.serialize())
            d = DataFrame(1)
            d.data = b'1234567890' * 2
            d.flags.add('END_STREAM')
            sock.send(d.serialize())

            send_event.wait(5)
            sock.close()

        self._start_server(socket_handler)

        s = requests.Session()
        s.mount('https://%s' % self.host, HTTP20Adapter())
        r = s.get('https://%s:%s/some/path' % (self.host, self.port))

        # Assert about the received values.
        assert r.status_code == 200
        assert r.headers[b'Content-Type'] == b'not/real'
        assert r.content == b'1234567890' * 2

        send_event.set()

        self.tear_down()

    def test_adapter_sending_values(self, monkeypatch):
        self.set_up()

        # We need to patch the ssl_wrap_socket method to ensure that we
        # forcefully upgrade.
        old_wrap_socket = hyper.http11.connection.wrap_socket

        def wrap(*args):
            sock, _ = old_wrap_socket(*args)
            return sock, 'h2'

        monkeypatch.setattr(hyper.http11.connection, 'wrap_socket', wrap)

        data = []

        def socket_handler(listener):
            sock = listener.accept()[0]

            # Do the handshake: conn header, settings, send settings, recv ack.
            receive_preamble(sock)

            # Now expect some data. One headers frame and one data frame.
            data.append(sock.recv(65535))
            data.append(sock.recv(65535))

            # Respond!
            h = HeadersFrame(1)
            h.data = self.get_encoder().encode(
                [
                    (':status', 200),
                    ('content-type', 'not/real'),
                    ('content-length', 20),
                ]
            )
            h.flags.add('END_HEADERS')
            sock.send(h.serialize())
            d = DataFrame(1)
            d.data = b'1234567890' * 2
            d.flags.add('END_STREAM')
            sock.send(d.serialize())

            sock.close()

        self._start_server(socket_handler)

        s = requests.Session()
        s.mount('https://%s' % self.host, HTTP20Adapter())
        r = s.post(
            'https://%s:%s/some/path' % (self.host, self.port),
            data='hi there',
        )

        # Assert about the sent values.
        assert r.status_code == 200

        f = decode_frame(data[0])
        assert isinstance(f, HeadersFrame)

        f = decode_frame(data[1])
        assert isinstance(f, DataFrame)
        assert f.data == b'hi there'

        self.tear_down()
