# -*- coding: utf-8 -*-
import hyper.common.connection

from hyper.common.connection import HTTPConnection
from hyper.common.exceptions import TLSUpgrade

class TestHTTPConnection(object):
    def test_h1_kwargs(self):
        c = HTTPConnection(
            'test', 443, secure=False, window_manager=True, enable_push=True,
            other_kwarg=True
        )

        assert c._h1_kwargs == {
            'secure': False,
            'other_kwarg': True,
        }

    def test_h2_kwargs(self):
        c = HTTPConnection(
            'test', 443, secure=False, window_manager=True, enable_push=True,
            other_kwarg=True
        )

        assert c._h2_kwargs == {
            'window_manager': True,
            'enable_push': True,
            'other_kwarg': True,
        }

    def test_upgrade(self, monkeypatch):
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
        assert c._conn._sock == 'totally a socket'


class DummyH1Connection(object):
    def __init__(self, *args, **kwargs):
        pass

    def request(self, *args, **kwargs):
        raise TLSUpgrade('h2', 'totally a socket')


class DummyH2Connection(object):
    def __init__(self, *args, **kwargs):
        pass

    def _send_preamble(self):
        pass

    def request(self, *args, **kwargs):
        return 'h2'
