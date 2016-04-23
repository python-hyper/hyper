# -*- coding: utf-8 -*-
"""
test/integration_http11
~~~~~~~~~~~~~~~~~~~~~~~

This file defines integration-type tests for hyper's HTTP/1.1 layer. These are
still not fully hitting the network, so that's alright.
"""
import hyper
import threading
import pytest

from hyper.compat import ssl
from server import SocketLevelTest
from hyper.common.exceptions import HTTPUpgrade

# Turn off certificate verification for the tests.
if ssl is not None:
    hyper.tls._context = hyper.tls.init_context()
    hyper.tls._context.check_hostname = False
    hyper.tls._context.verify_mode = ssl.CERT_NONE


class TestHyperH11Integration(SocketLevelTest):
    # These are HTTP/1.1 tests.
    h2 = False

    def test_basic_request_response(self):
        self.set_up()

        send_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            # We should get the initial request.
            data = b''
            while not data.endswith(b'\r\n\r\n'):
                data += sock.recv(65535)

            send_event.wait()

            # We need to send back a response.
            resp = (
                b'HTTP/1.1 201 No Content\r\n'
                b'Server: socket-level-server\r\n'
                b'Content-Length: 0\r\n'
                b'Connection: close\r\n'
                b'\r\n'
            )
            sock.send(resp)

            sock.close()

        self._start_server(socket_handler)
        c = self.get_connection()
        c.request('GET', '/')
        send_event.set()
        r = c.get_response()

        assert r.status == 201
        assert r.reason == b'No Content'
        assert len(r.headers) == 3
        assert r.headers[b'server'] == [b'socket-level-server']
        assert r.headers[b'content-length'] == [b'0']
        assert r.headers[b'connection'] == [b'close']

        assert r.read() == b''

        assert c._sock is None

    def test_closing_response(self):
        self.set_up()

        send_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            # We should get the initial request.
            data = b''
            while not data.endswith(b'\r\n\r\n'):
                data += sock.recv(65535)

            send_event.wait()

            # We need to send back a response.
            resp = (
                b'HTTP/1.1 200 OK\r\n'
                b'Server: socket-level-server\r\n'
                b'Connection: close\r\n'
                b'\r\n'
            )
            sock.send(resp)

            chunks = [
                b'hello',
                b'there',
                b'sir',
                b'finalfantasy',
            ]

            for chunk in chunks:
                sock.send(chunk)

            sock.close()

        self._start_server(socket_handler)
        c = self.get_connection()
        c.request('GET', '/')
        send_event.set()
        r = c.get_response()

        assert r.status == 200
        assert r.reason == b'OK'
        assert len(r.headers) == 2
        assert r.headers[b'server'] == [b'socket-level-server']
        assert r.headers[b'connection'] == [b'close']

        assert r.read() == b'hellotheresirfinalfantasy'

    def test_proxy_request_response(self):
        self.set_up(proxy=True)

        send_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            # We should get the initial request.
            data = b''
            while not data.endswith(b'\r\n\r\n'):
                data += sock.recv(65535)

            send_event.wait()

            # We need to send back a response.
            resp = (
                b'HTTP/1.1 201 No Content\r\n'
                b'Server: socket-level-server\r\n'
                b'Content-Length: 0\r\n'
                b'Connection: close\r\n'
                b'\r\n'
            )
            sock.send(resp)

            sock.close()

        self._start_server(socket_handler)
        c = self.get_connection()
        c.request('GET', '/')
        send_event.set()
        r = c.get_response()

        assert r.status == 201
        assert r.reason == b'No Content'
        assert len(r.headers) == 3
        assert r.headers[b'server'] == [b'socket-level-server']
        assert r.headers[b'content-length'] == [b'0']
        assert r.headers[b'connection'] == [b'close']

        assert r.read() == b''

        assert c._sock is None

    def test_response_with_body(self):
        self.set_up()

        send_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            # We should get the initial request.
            data = b''
            while not data.endswith(b'\r\n\r\n'):
                data += sock.recv(65535)

            send_event.wait()

            # We need to send back a response.
            resp = (
                b'HTTP/1.1 200 OK\r\n'
                b'Server: socket-level-server\r\n'
                b'Content-Length: 15\r\n'
                b'\r\n'
            )
            sock.send(resp)

            chunks = [
                b'hello',
                b'there',
                b'hello',
            ]

            for chunk in chunks:
                sock.send(chunk)

            sock.close()

        self._start_server(socket_handler)
        c = self.get_connection()
        c.request('GET', '/')
        send_event.set()
        r = c.get_response()

        assert r.status == 200
        assert r.reason == b'OK'
        assert len(r.headers) == 2
        assert r.headers[b'server'] == [b'socket-level-server']
        assert r.headers[b'content-length'] == [b'15']

        assert r.read() == b'hellotherehello'

    def test_connection_context_manager(self):
        self.set_up()

        send_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            # We should get the initial request.
            data = b''
            while not data.endswith(b'\r\n\r\n'):
                data += sock.recv(65535)

            send_event.wait()

            # We need to send back a response.
            resp = (
                b'HTTP/1.1 200 OK\r\n'
                b'Server: socket-level-server\r\n'
                b'Content-Length: 15\r\n'
                b'\r\n'
            )
            sock.send(resp)

            chunks = [
                b'hello',
                b'there',
                b'hello',
            ]

            for chunk in chunks:
                sock.send(chunk)

            sock.close()

        self._start_server(socket_handler)
        with self.get_connection() as c:
            c.request('GET', '/')
            send_event.set()
            r = c.get_response()
            data = r.read()

        assert r.status == 200
        assert r.reason == b'OK'
        assert len(r.headers) == 2
        assert data == b'hellotherehello'

        assert c._sock is None

    def test_upgrade_response(self):
        self.set_up()
        self.secure = False

        send_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            # We should get the initial request.
            data = b''
            while not data.endswith(b'\r\n\r\n'):
                data += sock.recv(65535)

            send_event.wait()

            # We need to send back a response.
            resp = (
                b'HTTP/1.1 101 Upgrade\r\n'
                b'Server: socket-level-server\r\n'
                b'Content-Length: 0\r\n'
                b'Connection: upgrade\r\n'
                b'Upgrade: h2c\r\n'
                b'\r\n'
            )
            sock.send(resp)

            sock.close()

        self._start_server(socket_handler)
        c = self.get_connection()
        c.request('GET', '/')
        send_event.set()

        with pytest.raises(HTTPUpgrade):
            c.get_response()
