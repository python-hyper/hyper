# -*- coding: utf-8 -*-
"""
Tests the hyper SSLContext.
"""
import hyper
from hyper.common.connection import HTTPConnection
from hyper.compat import ssl
import pytest

class TestSSLContext(object):
    """
    Tests default and custom SSLContext
    """
    def test_default_context(self):
        # Create default SSLContext
        hyper.tls._context = hyper.tls.init_context()
        assert hyper.tls._context.check_hostname == True
        assert hyper.tls._context.verify_mode == ssl.CERT_REQUIRED
        assert hyper.tls._context.options & ssl.OP_NO_COMPRESSION != 0


    def test_custom_context(self):
        # The following SSLContext doesn't provide any valid certicate.
        # Its purpose is only to confirm that hyper is not using its
        # default SSLContext.
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.verify_mode = ssl.CERT_NONE
        context.check_hostname = False

        hyper.tls._context = context

        assert hyper.tls._context.check_hostname == False
        assert hyper.tls._context.verify_mode == ssl.CERT_NONE
        assert hyper.tls._context.options & ssl.OP_NO_COMPRESSION == 0


    def test_HTTPConnection_with_custom_context(self):
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.set_default_verify_paths()
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = True
        context.set_npn_protocols(['h2', 'h2-15'])
        context.options |= ssl.OP_NO_COMPRESSION

        conn = HTTPConnection('http2bin.org', 443, ssl_context=context)

        assert conn.ssl_context.check_hostname == True
        assert conn.ssl_context.verify_mode == ssl.CERT_REQUIRED
        assert conn.ssl_context.options & ssl.OP_NO_COMPRESSION != 0
