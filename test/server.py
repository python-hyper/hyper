# -*- coding: utf-8 -*-
"""
test/server
~~~~~~~~~~~

This module defines some testing infrastructure that is very useful for
integration-type testing of hyper. It works by spinning up background threads
that run test-defined logic while listening to a background thread.

This very-clever idea and most of its implementation are ripped off from
Andrey Petrov's excellent urllib3 project. I owe him a substantial debt in
ingenuity and about a million beers. The license is available in NOTICES.
"""

import threading
import socket
import sys
from enum import Enum

from hyper import HTTP20Connection
from hyper.compat import ssl
from hyper.http11.connection import HTTP11Connection
from hpack.hpack import Encoder
from hpack.huffman import HuffmanEncoder
from hpack.huffman_constants import (
    REQUEST_CODES, REQUEST_CODES_LENGTH
)
from hyper.tls import NPN_PROTOCOL


class SocketSecuritySetting(Enum):
    """
    Server socket TLS wrapping strategy:

    SECURE - automatically wrap socket
    INSECURE - never wrap
    SECURE_NO_AUTO_WRAP - init context, but socket must be wrapped manually

    The values are needed to be able to convert ``secure`` boolean flag of
    a client to a member of this enum:
    ``socket_security = SocketSecuritySetting(secure)``
    """
    SECURE = True
    INSECURE = False
    SECURE_NO_AUTO_WRAP = 'NO_AUTO_WRAP'


class SocketServerThread(threading.Thread):
    """
    This method stolen wholesale from shazow/urllib3 under license. See
    NOTICES.

    :param socket_handler: Callable which receives a socket argument for one
        request.
    :param ready_event: Event which gets set when the socket handler is
        ready to receive requests.
    """
    def __init__(self,
                 socket_handler,
                 host='localhost',
                 ready_event=None,
                 h2=True,
                 socket_security=SocketSecuritySetting.SECURE):
        threading.Thread.__init__(self)

        self.socket_handler = socket_handler
        self.host = host
        self.socket_security = socket_security
        self.ready_event = ready_event
        self.daemon = True

        if self.socket_security in (SocketSecuritySetting.SECURE,
                                    SocketSecuritySetting.SECURE_NO_AUTO_WRAP):
            self.cxt = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            if ssl.HAS_NPN and h2:
                self.cxt.set_npn_protocols([NPN_PROTOCOL])
            self.cxt.load_cert_chain(certfile='test/certs/server.crt',
                                     keyfile='test/certs/server.key')

    def _start_server(self):
        sock = socket.socket()
        if sys.platform != 'win32':
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        if self.socket_security == SocketSecuritySetting.SECURE:
            sock = self.wrap_socket(sock)
        sock.bind((self.host, 0))
        self.port = sock.getsockname()[1]

        # Once listen() returns, the server socket is ready
        sock.listen(1)

        if self.ready_event:
            self.ready_event.set()

        self.socket_handler(sock)
        sock.close()

    def wrap_socket(self, sock):
        return self.cxt.wrap_socket(sock, server_side=True)

    def run(self):
        self.server = self._start_server()


class SocketLevelTest(object):
    """
    A test-class that defines a few helper methods for running socket-level
    tests.
    """
    def set_up(self, secure=True, proxy=False, timeout=None):
        self.host = None
        self.port = None
        self.socket_security = SocketSecuritySetting(secure)
        self.proxy = proxy
        self.server_thread = None
        self.timeout = timeout

    def _start_server(self, socket_handler):
        """
        Starts a background thread that runs the given socket handler.
        """
        ready_event = threading.Event()
        self.server_thread = SocketServerThread(
            socket_handler=socket_handler,
            ready_event=ready_event,
            h2=self.h2,
            socket_security=self.socket_security
        )
        self.server_thread.start()
        ready_event.wait()

        self.host = self.server_thread.host
        self.port = self.server_thread.port
        self.socket_security = self.server_thread.socket_security

    @property
    def secure(self):
        return self.socket_security in \
               (SocketSecuritySetting.SECURE,
                SocketSecuritySetting.SECURE_NO_AUTO_WRAP)

    @secure.setter
    def secure(self, value):
        self.socket_security = SocketSecuritySetting(value)

    def get_connection(self):
        if self.h2:
            if not self.proxy:
                return HTTP20Connection(self.host, self.port, self.secure,
                                        timeout=self.timeout)
            else:
                return HTTP20Connection('http2bin.org', secure=self.secure,
                                        proxy_host=self.host,
                                        proxy_port=self.port,
                                        timeout=self.timeout)
        else:
            if not self.proxy:
                return HTTP11Connection(self.host, self.port, self.secure,
                                        timeout=self.timeout)
            else:
                return HTTP11Connection('httpbin.org', secure=self.secure,
                                        proxy_host=self.host,
                                        proxy_port=self.port,
                                        timeout=self.timeout)

    def get_encoder(self):
        """
        Returns a HPACK encoder set up for responses.
        """
        e = Encoder()
        e.huffman_coder = HuffmanEncoder(REQUEST_CODES, REQUEST_CODES_LENGTH)
        return e

    def tear_down(self):
        """
        Tears down the testing thread.
        """
        self.server_thread.join(0.1)
