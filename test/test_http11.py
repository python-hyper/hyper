# -*- coding: utf-8 -*-
"""
test_http11.py
~~~~~~~~~~~~~~

Unit tests for hyper's HTTP/1.1 implementation.
"""
from io import BytesIO

from hyper.http11.connection import HTTP11Connection
from hyper.http11.response import HTTP11Response


class TestHTTP11Connection(object):
    def test_initialization_no_port(self):
        c = HTTP11Connection('http2bin.org')

        assert c.host == 'http2bin.org'
        assert c.port == 80
        assert not c.secure

    def test_initialization_inline_port(self):
        c = HTTP11Connection('http2bin.org:443')

        assert c.host == 'http2bin.org'
        assert c.port == 443
        assert c.secure

    def test_initialization_separate_port(self):
        c = HTTP11Connection('localhost', 8080)

        assert c.host == 'localhost'
        assert c.port == 8080
        assert not c.secure

    def test_basic_request(self):
        c = HTTP11Connection('http2bin.org')
        c._sock = sock = DummySocket()

        c.request('GET', '/get', headers={'User-Agent': 'hyper'})

        expected = (
            b"GET /get HTTP/1.1\r\n"
            b"User-Agent: hyper\r\n"
            b"\r\n"
        )
        received = b''.join(sock.queue)

        assert received == expected

    def test_request_with_bytestring_body(self):
        c = HTTP11Connection('http2bin.org')
        c._sock = sock = DummySocket()

        c.request('POST', '/post', headers={'User-Agent': 'hyper'}, body=b'hi')

        expected = (
            b"POST /post HTTP/1.1\r\n"
            b"User-Agent: hyper\r\n"
            b"\r\n"
            b"hi"
        )
        received = b''.join(sock.queue)

        assert received == expected

    def test_get_response(self):
        c = HTTP11Connection('http2bin.org')
        c._sock = sock = DummySocket()

        sock.buffer= BytesIO(
            b"HTTP/1.1 201 No Content\r\n"
            b"Connection: close\r\n"
            b"Server: Socket\r\n"
            b"Content-Length: 0\r\n"
            b"\r\n"
        )

        r = c.get_response()

        assert r.status == 201
        assert r.reason == b'No Content'
        assert list(r.headers.iter_raw()) == [
            (b'Connection', b'close'),
            (b'Server', b'Socket'),
            (b'Content-Length', b'0')
        ]
        assert r.read() == b''

    def test_response_short_reads(self):
        c = HTTP11Connection('http2bin.org')
        c._sock = sock = DummySocket()

        sock.buffer= BytesIO(
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Length: 15\r\n"
            b"\r\n"
            b"hellotherechamp"
        )

        r = c.get_response()

        assert r.status == 200
        assert r.reason == b'OK'
        assert r.read(5) == b'hello'
        assert r.read(5) == b'there'
        assert r.read(5) == b'champ'
        assert r.read(5) == b''


class TestHTTP11Response(object):
    def test_short_circuit_read(self):
        r = HTTP11Response(200, 'OK', {}, None)

        assert r.read() == b''


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

    def readline(self):
        return memoryview(self.buffer.readline())
