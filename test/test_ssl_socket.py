# -*- coding: utf-8 -*-
"""
test/test_ssl_socket
~~~~~~~~~~~~~~~~~~~~

This file defines tests for hyper that validate our TLS handling.
"""
import os
import socket
import ssl
import threading

import pytest

from hyper.tls import wrap_socket, init_context

from server import SocketLevelTest


TEST_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_CERTS_DIR = os.path.join(TEST_DIR, "certs")
CLIENT_CERT_FILE = os.path.join(TEST_CERTS_DIR, 'client.crt')
CLIENT_KEY_FILE = os.path.join(TEST_CERTS_DIR, 'client.key')
CLIENT_PEM_FILE = os.path.join(TEST_CERTS_DIR, 'nopassword.pem')
SERVER_CERT_FILE = os.path.join(TEST_CERTS_DIR, 'server.crt')
SERVER_KEY_FILE = os.path.join(TEST_CERTS_DIR, 'server.key')


class TestBasicSocketManipulation(SocketLevelTest):
    # These aren't HTTP/2 tests, but it doesn't hurt to leave it.
    h2 = True

    def test_connection_string(self):
        self.set_up()
        evt = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            evt.wait(5)
            sock.close()

        self._start_server(socket_handler)
        s = socket.create_connection((self.host, self.port))
        s, proto = wrap_socket(s, "localhost", force_proto=b"test")
        s.close()
        evt.set()

        assert proto == b"test"

        self.tear_down()

    @pytest.mark.parametrize(
        'context_kwargs',
        [
            {'cert': CLIENT_PEM_FILE},
            {
                'cert': (CLIENT_CERT_FILE, CLIENT_KEY_FILE),
                'cert_password': b'abc123'
            },
        ]
    )
    def test_client_certificate(self, context_kwargs):
        # Don't have the server thread do TLS: we'll do it ourselves.
        self.set_up(secure=False)
        evt = threading.Event()
        data = []

        def socket_handler(listener):
            sock = listener.accept()[0]
            sock = ssl.wrap_socket(
                sock,
                ssl_version=ssl.PROTOCOL_SSLv23,
                certfile=SERVER_CERT_FILE,
                keyfile=SERVER_KEY_FILE,
                cert_reqs=ssl.CERT_REQUIRED,
                ca_certs=CLIENT_PEM_FILE,
                server_side=True
            )
            data.append(sock.recv(65535))
            evt.wait(5)
            sock.close()

        self._start_server(socket_handler)

        # Set up the client context. Don't validate the server cert though.
        context = init_context(**context_kwargs)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        s = socket.create_connection((self.host, self.port))
        s, proto = wrap_socket(s, "localhost", ssl_context=context)
        s.sendall(b'hi')
        s.close()
        evt.set()

        self.tear_down()
