# -*- coding: utf-8 -*-
"""
Tests the hyper SSLContext.
"""
import os

from hyper.compat import ssl
try:
    from hyper.ssl_compat import SSLContext
except ImportError:
    SSLContext = None


TEST_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_CERTS_DIR = os.path.join(TEST_DIR, 'certs')
CLIENT_CERT_FILE = os.path.join(TEST_CERTS_DIR, 'client.crt')
CLIENT_KEY_FILE = os.path.join(TEST_CERTS_DIR, 'client.key')


class TestHyperSSLContext(object):
    """
    Tests hyper SSLContext
    """
    def test_custom_context_with_cert_as_file(self):
        # Test using hyper's own SSLContext
        if SSLContext is not None:
            context = SSLContext(ssl.PROTOCOL_SSLv23)
            context.verify_mode = ssl.CERT_NONE
            context.check_hostname = False

            # Test that we can load in a cert and key protected by a passphrase,
            # from files.
            context.load_cert_chain(
                certfile=CLIENT_CERT_FILE,
                keyfile=CLIENT_KEY_FILE,
                password='abc123'
            )
