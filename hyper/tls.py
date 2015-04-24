# -*- coding: utf-8 -*-
"""
hyper/tls
~~~~~~~~~

Contains the TLS/SSL logic for use in hyper.
"""
import os.path as path

from .compat import ignore_missing, ssl


NPN_PROTOCOL = 'h2'
H2_NPN_PROTOCOLS = [NPN_PROTOCOL, 'h2-16', 'h2-15', 'h2-14']
SUPPORTED_NPN_PROTOCOLS = H2_NPN_PROTOCOLS + ['http/1.1']


# We have a singleton SSLContext object. There's no reason to be creating one
# per connection.
_context = None

# Work out where our certificates are.
cert_loc = path.join(path.dirname(__file__), 'certs.pem')


def wrap_socket(sock, server_hostname, ssl_context=None):
    """
    A vastly simplified SSL wrapping function. We'll probably extend this to
    do more things later.
    """
    global _context

    if _context is None:  # pragma: no cover
        _context = _init_context()

    # if an SSLContext is provided then use it instead of default context
    _ssl_context = ssl_context or _context

    # the spec requires SNI support
    ssl_sock = _ssl_context.wrap_socket(sock, server_hostname=server_hostname)
    # Setting SSLContext.check_hostname to True only verifies that the
    # post-handshake servername matches that of the certificate. We also need
    # to check that it matches the requested one.
    if _context.check_hostname:  # pragma: no cover
        try:
            ssl.match_hostname(ssl_sock.getpeercert(), server_hostname)
        except AttributeError:
            ssl.verify_hostname(ssl_sock, server_hostname)  # pyopenssl

    proto = None

    # ALPN is newer, so we prefer it over NPN. The odds of us getting different
    # answers is pretty low, but let's be sure.
    with ignore_missing():
        proto = ssl_sock.selected_alpn_protocol()

    with ignore_missing():
        if proto is None:
            proto = ssl_sock.selected_npn_protocol()

    return (ssl_sock, proto)


def _init_context():
    """
    Creates the singleton SSLContext we use.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.set_default_verify_paths()
    context.load_verify_locations(cafile=cert_loc)
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True

    with ignore_missing():
        context.set_npn_protocols(SUPPORTED_NPN_PROTOCOLS)

    with ignore_missing():
        context.set_alpn_protocols(SUPPORTED_NPN_PROTOCOLS)

    # required by the spec
    context.options |= ssl.OP_NO_COMPRESSION

    return context
