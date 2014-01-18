# -*- coding: utf-8 -*-
"""
hyper/tls
~~~~~~~~~

Contains the TLS/SSL logic for use in hyper.
"""
import ssl

SUPPORTED_PROTOCOLS = ['http/1.1']
# We have a singleton SSLContext object. There's no reason to be creating one
# per connection. We're using v23 right now until someone gives me a reason not
# to.
_context = None

def _init_context():
    """
    Creates the singleton SSLContext we use.
    """
    _context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    _context.set_default_verify_paths()
    _context.verify_mode = ssl.CERT_REQUIRED

    try:
        _context.set_npn_protocols(SUPPORTED_PROTOCOLS)
    except (AttributeError, NotImplementedError):
        pass

    # We do our best to do better security
    try:
        _context.options |= ssl.OP_NO_SSLv2
    except AttributeError:
        pass

    try:
        _context.options |= ssl.OP_NO_COMPRESSION
    except AttributeError:
        pass
