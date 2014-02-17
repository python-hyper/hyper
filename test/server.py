# -*- coding: utf-8 -*-
"""
test/server
~~~~~~~~~~~

This module defines some testing infrastructure that is very useful for
integration-type testing of hyper. It works by spinning up background threads
that run test-defined logic while listening to a background thread.

This very-clever idea and most of its implementation are ripped off from
Andrey Petrov's excellent urllib3 project. I owe him a substantial debt in
ingenuity and about a million beers.
"""

import threading
import socket
import ssl
import sys

from hyper.http20.hpack import Encoder
from hyper.http20.huffman import HuffmanEncoder
from hyper.http20.huffman_constants import (
    RESPONSE_CODES, RESPONSE_CODES_LENGTH
)

class SocketServerThread(threading.Thread):
    """
    This method stolen wholesale from shazow/urllib3.

    :param socket_handler: Callable which receives a socket argument for one
        request.
    :param ready_event: Event which gets set when the socket handler is
        ready to receive requests.
    """
    def __init__(self, socket_handler, host='localhost', port=8081,
                 ready_event=None):
        threading.Thread.__init__(self)

        self.socket_handler = socket_handler
        self.host = host
        self.ready_event = ready_event
        self.cxt = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        self.cxt.set_npn_protocols(['HTTP-draft-09/2.0'])
        self.cxt.load_cert_chain(certfile='test/certs/server.crt', keyfile='test/certs/server.key')

    def _start_server(self):
        sock = socket.socket(socket.AF_INET6)
        if sys.platform != 'win32':
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock = self.cxt.wrap_socket(sock, server_side=True)
        sock.bind((self.host, 0))
        self.port = sock.getsockname()[1]

        # Once listen() returns, the server socket is ready
        sock.listen(1)

        if self.ready_event:
            self.ready_event.set()

        self.socket_handler(sock)
        sock.close()

    def run(self):
        self.server = self._start_server()


class SocketLevelTest(object):
    """
    A test-class that defines a few helper methods for running socket-level
    tests.
    """
    def set_up(self):
        self.host = None
        self.port = None
        self.server_thread = None

    def _start_server(self, socket_handler):
        """
        Starts a background thread that runs the given socket handler.
        """
        ready_event = threading.Event()
        self.server_thread = SocketServerThread(
            socket_handler=socket_handler,
            ready_event=ready_event
        )
        self.server_thread.start()
        ready_event.wait()
        self.host = self.server_thread.host
        self.port = self.server_thread.port

    def get_encoder(self):
        """
        Returns a HPACK encoder set up for responses.
        """
        e = Encoder()
        e.huffman_coder = HuffmanEncoder(RESPONSE_CODES, RESPONSE_CODES_LENGTH)
        return e

    def tear_down(self):
        """
        Tears down the testing thread.
        """
        self.server_thread.join(0.1)

