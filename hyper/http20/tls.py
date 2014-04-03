# -*- coding: utf-8 -*-
"""
hyper/tls
~~~~~~~~~

Contains the TLS/SSL logic for use in hyper.
"""
import os.path as path

from ..compat import handle_missing, ssl


# Right now we support draft 9.
SUPPORTED_PROTOCOLS = ['http/1.1', 'HTTP-draft-09/2.0']


# We have a singleton SSLContext object. There's no reason to be creating one
# per connection. We're using v23 right now until someone gives me a reason not
# to.
_context = None

# Work out where our certificates are.
cert_loc = path.join(path.dirname(__file__), '..', 'certs.pem')

def wrap_socket(sock, server_hostname):
    """
    A vastly simplified SSL wrapping function. We'll probably extend this to
    do more things later.
    """
    global _context

    if _context is None:  # pragma: no cover
        _context = _init_context()

    if not ssl.HAS_SNI:  # pragma: no cover
        server_hostname = None

    ssl_sock = _context.wrap_socket(sock, server_hostname=server_hostname)
    with handle_missing():
        assert ssl_sock.selected_npn_protocol() == 'HTTP-draft-09/2.0'
    return ssl_sock


def _init_context():
    """
    Creates the singleton SSLContext we use.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.set_default_verify_paths()
    context.load_verify_locations(cafile=cert_loc)
    context.verify_mode = ssl.CERT_REQUIRED

    with handle_missing():
        context.set_npn_protocols(SUPPORTED_PROTOCOLS)

    # We do our best to do better security
    for option in ['OP_NO_SSLv2', 'OP_NO_COMPRESSION']:
        context.options |= getattr(ssl, option, 0)

    return context
