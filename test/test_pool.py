# -*- coding: utf-8 -*-
import unittest

from hyper.pool import SmartPool, HTTP20Protocol, UnsupportedMinProtocol, UpgradedConnection


security_noop = lambda sock, host, port, protocols: (sock, None)
protocol_noop = lambda sock, host, port, tracker: DummyConnection(sock)

class DummyConnection(object):
    def __init__(self, sock):
        self.sock = sock


def register_noops(pool, disable_upgrade=False):
    disabled_upgrade = lambda sock, host, port, protocols: None
    pool.register_security('null', None, security_noop)
    pool.register_security('weak', 'null', security_noop) # don't actually do the handshake
    pool.register_security('strong', 'weak', security_noop,
        security_noop if not disable_upgrade else disabled_upgrade)
    pool.register_protocol('h1', None, protocol_noop, single_conn=False)
    pool.register_protocol('h2', 'h1', protocol_noop)


class TestPool(unittest.TestCase):
    def test_multi_conn_not_reused(self):
        # TODO use fixture - new Pool for each test
        pool = SmartPool()
        pool.register_security('null', None, security_noop)
        pool.register_protocol('h1', None, protocol_noop, single_conn=False)

        conn, security, protocol = pool.get('google.com', 80, 'null', 'h1')
        assert protocol == 'h1'
        assert security == 'null'

        conn2 = pool.get('google.com', 80, 'null', 'h1')[0]
        assert conn2 is not conn

    def test_single_conn_reused(self):
        pool = SmartPool()
        pool.register_security('null', None, security_noop)
        pool.register_protocol('h1', None, protocol_noop, single_conn=True)

        conn, security, protocol = pool.get('google.com', 80, 'null', 'h1')
        assert protocol == 'h1'
        assert security == 'null'

        conn2 = pool.get('google.com', 80, 'null', 'h1')[0]
        assert conn2 is conn

    def test_h2_unavailable_without_npn(self):
        pool = SmartPool()
        register_noops(pool)

        self.assertRaises(UnsupportedMinProtocol, pool.get, 'google.com', 80, 'null', 'h2')

    def test_upgrade_h1_to_h2(self):
        pool = SmartPool()
        SmartPool.register_defaults(pool)

        class Response(object):
            status = 101
            will_close = False
            def __init__(self, *args, **kwargs):
                pass
            def begin(self):
                pass
            def getheader(self, name):
                return dict(Connection='Upgrade', Upgrade='h2')[name]

        conn = pool.get('google.com', 80, 'null', 'h1')[0]
        conn.response_class = Response
        conn.request('GET', '/')
        try:
            response = conn.getresponse()
            assert False, "didn't raise UpgradedConnection"
        except UpgradedConnection as e:
            new_conn = e.conn

        assert isinstance(new_conn, HTTP20Protocol)
        conn2 = pool.get('google.com', 80, 'null', 'h2')[0]
        assert conn is conn2

        # TODO test handling server that doesn't support Upgrade
        # TODO add Upgrade support to nghttp2

    def test_weak_security_cascade(self):
        pool = SmartPool()
        register_noops(pool, disable_upgrade=True)

        pool.add_known_service('google.com', 80, 'weak', 'h2')
        pool.get('google.com', 80, 'weak', 'h2')
        conn, security, protocol = pool.get('google.com', 80, 'null', 'h2')
        assert security == 'weak'

        conn, security, protocol = pool.get('google.com', 80, 'weak', 'h2')
        assert security == 'weak'

    def test_strong_security_cascade(self):
        pool = SmartPool()
        register_noops(pool, disable_upgrade=True)

        pool.add_known_service('google.com', 80, 'strong', 'h2')
        pool.get('google.com', 80, 'strong', 'h2')
        conn, security, protocol = pool.get('google.com', 80, 'null', 'h2')
        assert security == 'strong'

        conn, security, protocol = pool.get('google.com', 80, 'weak', 'h2')
        assert security == 'strong'

        conn, security, protocol = pool.get('google.com', 80, 'strong', 'h2')
        assert security == 'strong'

    def test_upgrade_weak_to_strong_security(self):
        pool = SmartPool()
        register_noops(pool)

        # TODO should this work if security=weak is a known service? at least try to upgrade it?
        pool.add_known_service('google.com', 80, 'strong', 'h2')
        conn = pool.get('google.com', 80, 'weak', 'h2')[0]
        conn2, security, protocol = pool.get('google.com', 80, 'strong', 'h2')
        assert security == 'strong'
        assert conn is conn2

    def test_h2_available_with_npn(self):
        pool = SmartPool()
        pool.register_security('strong', None, lambda sock, host, port, protocols: (sock, 'h2'))
        pool.register_protocol('h1', None, protocol_noop, single_conn=False)
        pool.register_protocol('h2', 'h1', protocol_noop)

        conn, security, protocol = pool.get('google.com', 80, 'strong', 'h1')
        assert protocol == 'h2'


# return Tracker object, rather than connection - users can get it from Tracker.conn
# relinquishing
# socket closing (from server side)
# alt-svc logic
