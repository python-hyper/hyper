# -*- coding: utf-8 -*-
"""
test_http11_parser.py
~~~~~~~~~~~~~~~~~~~~~

Unit tests for hyper's HTTP/1.1 parser.
"""
import pytest

from hyper.http11.parser import Parser, ParseError


class TestHTTP11Parser(object):
    def test_basic_http11_parsing(self):
        data = (
            b"HTTP/1.1 200 OK\r\n"
            b"Server: h2o\r\n"
            b"content-length: 2\r\n"
            b"Vary: accept-encoding\r\n"
            b"\r\n"
            b"hi"
        )
        m = memoryview(data)

        c = Parser()
        r = c.parse_response(m)

        assert r
        assert r.status == 200
        assert r.msg.tobytes() == b'OK'
        assert r.minor_version == 1

        expected_headers = [
            (b'Server', b'h2o'),
            (b'content-length', b'2'),
            (b'Vary', b'accept-encoding'),
        ]

        assert len(expected_headers) == len(r.headers)

        for (n1, v1), (n2, v2) in zip(r.headers, expected_headers):
            assert n1.tobytes() == n2
            assert v1.tobytes() == v2

        assert r.consumed == len(data) - 2

    def test_short_response_one(self):
        data = (
            b"HTTP/1.1 200 OK\r\n"
            b"Server: h2o\r\n"
            b"content"
        )
        m = memoryview(data)

        c = Parser()
        r = c.parse_response(m)

        assert r is None

    def test_short_response_two(self):
        data = (
            b"HTTP/1.1 "
        )
        m = memoryview(data)

        c = Parser()
        r = c.parse_response(m)

        assert r is None

    def test_invalid_version(self):
        data = (
            b"SQP/1 200 OK\r\n"
            b"Server: h2o\r\n"
            b"content-length: 2\r\n"
            b"Vary: accept-encoding\r\n"
            b"\r\n"
            b"hi"
        )
        m = memoryview(data)

        c = Parser()

        with pytest.raises(ParseError):
            c.parse_response(m)
