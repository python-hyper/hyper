# -*- coding: utf-8 -*-
"""
hyper/ssl_compat_appengine
~~~~~~~~~

Provides the ssl module interface which hyper assumes, based on AppEngine ssl.

This module complements some constants and classes which don't exist on
AppEngine's SSL module, to be used by hyper smoothly.
See: https://cloud.google.com/appengine/docs/python/sockets/ssl_support
"""

import ssl

from ssl import PROTOCOL_TLSv1, PROTOCOL_SSLv23, PROTOCOL_SSLv3
from ssl import CERT_NONE, CERT_OPTIONAL, CERT_REQUIRED
from ssl import match_hostname

OP_NO_COMPRESSION = 0


class SSLContext:
    """A SSL context which implements the methods used by hyper."""

    def __init__(self, proto):
        self.protocol_version = proto
        self.verify_mode = CERT_REQUIRED
        self.check_hostname = True
        self.options = 0
        self.custom_ca_cert = None

    def set_default_verify_paths(self):
        # Intentionally do nothing.
        pass

    def load_verify_locations(self, cafile):
        self.custom_ca_cert = cafile

    def wrap_socket(self, sock, server_side=False, do_handshake_on_connect=True,
                    suppress_ragged_eofs=True, server_hostname=None):
        sock = ssl.wrap_socket(
            sock, server_side=server_side, cert_reqs=self.verify_mode,
            ssl_version=self.protocol_version, ca_certs=self.custom_ca_cert,
            suppress_ragged_eofs=suppress_ragged_eofs,
            do_handshake_on_connect=do_handshake_on_connect)
        # AppEngine SSLSocket does not have selected_npn_protocol, a hacky
        # solution to return a dummy data.
        sock.selected_npn_protocol = lambda: 'h2c'
        return sock
