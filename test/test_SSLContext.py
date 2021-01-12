# -*- coding: utf-8 -*-
"""
Tests the hyper SSLContext.
"""
import os

import hyper
from hyper.common.connection import HTTPConnection
from hyper.compat import ssl


TEST_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_CERTS_DIR = os.path.join(TEST_DIR, 'certs')
CLIENT_CERT_FILE = os.path.join(TEST_CERTS_DIR, 'client.crt')
CLIENT_KEY_FILE = os.path.join(TEST_CERTS_DIR, 'client.key')
CLIENT_PEM_FILE = os.path.join(TEST_CERTS_DIR, 'nopassword.pem')
MISSING_PEM_FILE = os.path.join(TEST_CERTS_DIR, 'missing.pem')


class TestSSLContext(object):
    """
    Tests default and custom SSLContext
    """
    def test_default_context(self):
        # Create default SSLContext
        hyper.tls._context = hyper.tls.init_context()
        assert hyper.tls._context.check_hostname
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

        assert not hyper.tls._context.check_hostname
        assert hyper.tls._context.verify_mode == ssl.CERT_NONE

    def test_HTTPConnection_with_custom_context(self):
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.set_default_verify_paths()
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = True
        context.set_npn_protocols(['h2', 'h2-15'])
        context.options |= ssl.OP_NO_COMPRESSION

        conn = HTTPConnection('http2bin.org', 443, ssl_context=context)

        assert conn.ssl_context.check_hostname
        assert conn.ssl_context.verify_mode == ssl.CERT_REQUIRED
        assert conn.ssl_context.options & ssl.OP_NO_COMPRESSION != 0

    def test_client_certificates(self):
        hyper.tls.init_context(
            cert=(CLIENT_CERT_FILE, CLIENT_KEY_FILE),
            cert_password=b'abc123')
        hyper.tls.init_context(cert=CLIENT_PEM_FILE)

    def test_missing_certs(self):
        succeeded = False
        threw_expected_exception = False
        try:
            hyper.tls.init_context(MISSING_PEM_FILE)
            succeeded = True
        except hyper.common.exceptions.MissingCertFile:
            threw_expected_exception = True
        except Exception:
            pass

        assert not succeeded
        assert threw_expected_exception
