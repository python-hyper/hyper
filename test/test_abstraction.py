# -*- coding: utf-8 -*-
import hyper.common.connection

from hyper.common.connection import HTTPConnection
from hyper.common.exceptions import TLSUpgrade, HTTPUpgrade


class TestHTTPConnection(object):
    def test_h1_kwargs(self):
        c = HTTPConnection(
            'test', 443, secure=False, window_manager=True, enable_push=True,
            ssl_context=False, proxy_host=False, proxy_port=False,
            proxy_headers=False, other_kwarg=True, timeout=5
        )

        assert c._h1_kwargs == {
            'secure': False,
            'ssl_context': False,
            'proxy_host': False,
            'proxy_port': False,
            'proxy_headers': False,
            'other_kwarg': True,
            'enable_push': True,
            'timeout': 5,
        }

    def test_h2_kwargs(self):
        c = HTTPConnection(
            'test', 443, secure=False, window_manager=True, enable_push=True,
            ssl_context=True, proxy_host=False, proxy_port=False,
            proxy_headers=False, other_kwarg=True, timeout=(10, 30)
        )

        assert c._h2_kwargs == {
            'window_manager': True,
            'enable_push': True,
            'secure': False,
            'ssl_context': True,
            'proxy_host': False,
            'proxy_port': False,
            'proxy_headers': False,
            'other_kwarg': True,
            'timeout': (10, 30),
        }

    def test_tls_upgrade(self, monkeypatch):
        monkeypatch.setattr(
            hyper.common.connection, 'HTTP11Connection', DummyH1Connection
        )
        monkeypatch.setattr(
            hyper.common.connection, 'HTTP20Connection', DummyH2Connection
        )
        c = HTTPConnection('test', 443)

        assert isinstance(c._conn, DummyH1Connection)

        r = c.request('GET', '/')

        assert r == 'h2'
        assert isinstance(c._conn, DummyH2Connection)
        assert c._conn._sock == 'totally a secure socket'

    def test_http_upgrade(self, monkeypatch):
        monkeypatch.setattr(
            hyper.common.connection, 'HTTP11Connection', DummyH1Connection
        )
        monkeypatch.setattr(
            hyper.common.connection, 'HTTP20Connection', DummyH2Connection
        )
        c = HTTPConnection('test', 80)

        assert isinstance(c._conn, DummyH1Connection)

        c.request('GET', '/')
        resp = c.get_response()

        assert resp == 'h2c'
        assert isinstance(c._conn, DummyH2Connection)
        assert c._conn._sock == 'totally a non-secure socket'


class DummyH1Connection(object):
    def __init__(self,  host, port=None, secure=None, **kwargs):
        self.host = host
        self.port = port

        if secure is not None:
            self.secure = secure
        elif self.port == 443:
            self.secure = True
        else:
            self.secure = False

    def request(self, *args, **kwargs):
        if self.secure:
            raise TLSUpgrade('h2', 'totally a secure socket')

    def get_response(self):
        if not self.secure:
            raise HTTPUpgrade('h2c', 'totally a non-secure socket')


class DummyH2Connection(object):
    def __init__(self, host, port=None, secure=None, **kwargs):
        self.host = host
        self.port = port

        if secure is not None:
            self.secure = secure
        elif self.port == 443:
            self.secure = True
        else:
            self.secure = False

    def _send_preamble(self):
        pass

    def _connect_upgrade(self, sock):
        self._sock = sock

    def _new_stream(self, *args, **kwargs):
        pass

    def request(self, *args, **kwargs):
        if self.secure:
            return 'h2'

    def get_response(self, *args, **kwargs):
        if not self.secure:
            return 'h2c'
