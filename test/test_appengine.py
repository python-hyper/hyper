# -*- coding: utf-8 -*-
"""
Tests the ssl compatibility module for appengine.
"""
import hyper
from hyper import ssl_compat_appengine
from server import SocketLevelTest
import socket
import pytest


class TestAppengine(object):
    """
    Test cases for ssl_compat_appengine module.
    """

    def test_field_existences(self):
        assert ssl_compat_appengine.PROTOCOL_TLSv1 is not None
        assert ssl_compat_appengine.PROTOCOL_SSLv23 is not None
        assert ssl_compat_appengine.PROTOCOL_SSLv3 is not None
        assert ssl_compat_appengine.CERT_NONE is not None
        assert ssl_compat_appengine.CERT_OPTIONAL is not None
        assert ssl_compat_appengine.CERT_REQUIRED is not None
        assert ssl_compat_appengine.OP_NO_COMPRESSION is not None
        assert ssl_compat_appengine.match_hostname is not None
        assert ssl_compat_appengine.SSLContext is not None

    def test_SSLContext(self):
        context = ssl_compat_appengine.SSLContext(
            ssl_compat_appengine.PROTOCOL_SSLv23)
        context.set_default_verify_paths()
        assert context.protocol_version == ssl_compat_appengine.PROTOCOL_SSLv23


class TestAppengineSocket(SocketLevelTest):
    """
    Test case for wrap_socket.
    """
    h2 = False

    def socket_handler(self, listener):
        sock = listener.accept()[0]
        sock.close()

    def test_wrap_socket(self):
        self.set_up()
        self._start_server(self.socket_handler)
        context = ssl_compat_appengine.SSLContext(
            ssl_compat_appengine.PROTOCOL_SSLv23)
        context.set_default_verify_paths()
        context.verify_mode = ssl_compat_appengine.CERT_NONE
        context.verify_hostname = False
        # This invocation makes sure it does not fail.
        context.load_verify_locations('test/certs/server.crt')
        sock = socket.create_connection(
            (self.server_thread.host, self.server_thread.port))
        ssl_sock = context.wrap_socket(sock, do_handshake_on_connect=False)
        assert ssl_sock.selected_npn_protocol() == 'h2'
        ssl_sock.close()
        self.tear_down()
