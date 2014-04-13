# -*- coding: utf-8 -*-
"""
hyper/pool
~~~~~~~~~~~~~

FIXME
"""
import itertools
import socket
import time

from .compat import urlparse, HTTPConnection
from .http20.connection import HTTP20Connection
from .http20.tls import wrap_socket


class SocketFactory(object):
    def __init__(self, timeout=5):
        self.timeout = timeout

    def __call__(self, host, port):
        return socket.create_connection((host, port), self.timeout)


class UpgradedConnection(Exception):
    def __init__(self, conn):
        super(UpgradedConnection, self).__init__(conn)
        self.conn = conn


# TODO include list of protocols the server *does* support, for debugging
class UnsupportedMinProtocol(Exception):
    pass


# TODO better name
class Tracker(object):
    def __init__(self, pool, host, port, security, protocol):
        self.pool = pool
        self.host = host
        self.port = port
        self.security = security
        self.protocol = protocol

    def switch_protocol(self, new_protocol):
        self.pool.switch_protocol(self.conn, self.host, self.port, self.security, self.protocol, new_protocol)
        self.protocol = new_protocol

    def relinquish(self):
        self.pool.relinquish(self.conn, self.host, self.port, self.security, self.protocol)


class HTTP11Protocol(HTTPConnection):
    def __init__(self, sock, host, port, tracker):
        super(HTTP11Protocol, self).__init__(host, port)
        self.sock = sock
        self.tracker = tracker

    def connect(self):
        # we're already connected; this is basically a no-op
        if self._tunnel_host:
            self._tunnel()

    def putrequest(self, method, url, skip_host=False,
                   skip_accept_encoding=False, skip_upgrade=False):
        super(HTTP11Protocol, self).putrequest(method, url, skip_host=skip_host,
                                               skip_accept_encoding=skip_accept_encoding)
        self.putheader('Connection', 'Upgrade, HTTP2-Settings')
        # TODO should include draft number, e.g. h2-10
        self.putheader('Upgrade', 'h2')
        #self.putheader('HTTP2-Settings', ) # FIXME

    def getresponse(self, buffering=False):
        response = super(HTTP11Protocol, self).getresponse(buffering=buffering)
        if response.status == 101 and response.getheader('Connection') == 'Upgrade' and response.getheader('Upgrade') == 'h2':
            # TODO are all response headers consumed at this point?
            self.tracker.switch_protocol('h2')
            raise UpgradedConnection(HTTP20Protocol(self.sock, self.host, self.port, self.tracker))
        self.tracker.relinquish()
        return response


class HTTP20Protocol(HTTP20Connection):
    def __init__(self, sock, host, port, tracker):
        super(HTTP20Protocol, self).__init__(host, port)
        self._sock = sock
        self.tracker = tracker


def weak_security(sock, host, port, protocols):
    # TODO use protocols, raise UnsupportedMinProtocol if server and client have none in common
    ssl_sock = wrap_socket(sock)
    return ssl_sock, ssl_sock.selected_npn_protocols()

# TODO maybe some kind of (sock, host, port) association class? at least use (host, port) address pairs
def strong_security(sock, host, port, protocols):
    # TODO use protocols
    ssl_sock = wrap_socket(sock, host)
    return ssl_sock, ssl_sock.selected_npn_protocols()


# TODO have different hostnames that point to the same IP share a connection, unless user specifies otherwise
# - but tolerate different IPs for same hostname, since it could be GeoIP or DNS-based load balancing/failover
class SmartPool(object):
    def __init__(self, socket_factory=None):
        self._socket_factory = socket_factory or SocketFactory()
        self._registered_securities = []
        self._registered_protocols = []
        self._connections = {}
        self._known_services = {}

    def get(self, host, port, min_security, min_protocol):
        # Look for an existing connection that meets the security and protocol
        # conditions.
        # TODO construct a dict mapping securities/protocols to precedence integers, to simplify logic
        for security_name, security_factory, upgrade in reversed(self._registered_securities):
            for protocol_name, protocol_factory, single_conn in reversed(self._registered_protocols):
                # TODO reuse existing one with completed state
                socks = self._connections.get((host, port, security_name, protocol_name), [])
                if len(socks) > 0:
                    sock = socks[-1]

                    connected = True
                    try:
                        sock.sock.getpeername() # TODO more elegant way
                    except socket.error as e:
                        if e.errno != errno.ENOTCONN:
                            # It's an error other than the one we expected if
                            # we're not connected.
                            raise
                        connected = False

                    if not single_conn or not connected:
                        socks.pop()
                    return sock, security_name, protocol_name

                if protocol_name == min_protocol:
                    break
            if security_name == min_security:
                break

        # At this point, we know we have to make a new connection.
        # NPN/ALPN can override alt-svc knowledge (for absence), but only if the server and client both support it

        sock = self._socket_factory(host, port)

        # Get the minimum security, and keep bumping it up as long as we're
        # allowed to.

        start_security = False
        selected_protocol = None
        # all the protocols we're willing to speak, i.e. those with
        # min_protocol's precedence or higher - reversed to indicate our
        # preference to the server
        supported_protocols = [protocol[0] for protocol in reversed(list(itertools.dropwhile(lambda protocol: protocol[0] != min_protocol, self._registered_protocols)))]
        selected_security = None
        for name, factory, upgrade in self._registered_securities:
            if name == min_security:
                start_security = True
                selected_security = name
                sock, selected_protocol = factory(sock, host, port, supported_protocols)
            elif start_security:
                if upgrade is None:
                    break
                retval = upgrade(sock, host, port, supported_protocols)
                if retval is None:
                    # upgrade was unsuccessful
                    break
                selected_security = name
                sock, selected_protocol = retval

        if selected_protocol is None:
            # we didn't negotiate a protocol through NPN/ALPN, so look for a
            # singleton unexpired protocol we know the server speaks
            for protocol in supported_protocols:
                expiry = self._known_services.get((host, port, selected_security, protocol), 0)
                if expiry is None or expiry > time.time():
                    if selected_protocol is not None:
                        raise MultipleKnownProtocols()
                    selected_protocol = protocol
            if selected_protocol is None:
                # we didn't find a fresh known protocol, so assume the server
                # speaks the first registered protocol (usually 'h1')
                selected_protocol = self._registered_protocols[0][0]

        reached_minimum = False
        for name, factory, single_conn in self._registered_protocols:
            if name == min_protocol:
                reached_minimum = True
            if name == selected_protocol:
                # ensure the selected protocol has at least min_protocol's precedence
                if not reached_minimum:
                    raise UnsupportedMinProtocol()
                tracker = Tracker(self, host, port, selected_security, selected_protocol)
                connection = factory(sock, host, port, tracker)
                tracker.conn = connection
                if single_conn:
                    self._connections.setdefault((host, port, selected_security, selected_protocol), []).append(connection)
                return (connection, selected_security, selected_protocol)

    def relinquish(self, conn, host, port, security, protocol):
        self._connections.setdefault((host, port, security, protocol), []).append(conn)

    # called post-Upgrade dance
    def switch_protocol(self, conn, host, port, security, old_protocol, new_protocol):
        for name, factory, single_conn in self._registered_protocols:
            if single_conn:
                if name == old_protocol:
                    conns = self._connections[(host, port, security, old_protocol)]
                    conns.remove(conn)
                if name == new_protocol:
                    self._connections.setdefault((host, port, security, new_protocol), []).append(conn)

    # works for both alt-svc and prior knowledge
    # expiry=None --> "never expire"
    def add_known_service(self, host, port, security, protocol, expiry=None, src_address=None):
        self._known_services[(host, port, security, protocol)] = expiry
        if src_address is not None:
            self.alt_services[src_address] = (host, port) # TODO use somewhere

    def _register(self, coll, thing, pred):
        if pred is None:
            coll.append(thing)
        else:
            idx = [i for i in range(len(coll)) if coll[i][0] == pred][0]
            coll.insert(idx+1, thing)

    def register_security(self, name, pred, factory, upgrade=None):
        self._register(self._registered_securities, (name, factory, upgrade), pred)

    def register_protocol(self, name, pred, factory, single_conn=True):
        self._register(self._registered_protocols, (name, factory, single_conn), pred)

    @staticmethod
    def register_defaults(pool):
        pool.register_security('null', None, lambda sock, host, port, protocols: (sock, None))
        pool.register_security('weak', 'null', weak_security)
        pool.register_security('strong', 'weak', strong_security, lambda sock, host, port, protocols: (sock, None)) # FIXME real upgrade()
        pool.register_protocol('h1', None, HTTP11Protocol, False)
        pool.register_protocol('h2', 'h1', HTTP20Protocol)


_pool = SmartPool()
SmartPool.register_defaults(_pool)
