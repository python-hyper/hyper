# -*- coding: utf-8 -*-
"""
hyper/tls
~~~~~~~~~

Contains the TLS/SSL logic for use in hyper.
"""
import ssl
import os.path as path


# Right now we support draft 9.
SUPPORTED_PROTOCOLS = ['http/1.1', 'HTTP-draft-09/2.0']


# We have a singleton SSLContext object. There's no reason to be creating one
# per connection. We're using v23 right now until someone gives me a reason not
# to.
_context = None


# Work out where our certificates are.
cert_loc = path.join(path.dirname(__file__), '..', 'certs.pem')


def wrap_socket(socket, server_hostname):
    """
    A vastly simplified SSL wrapping function. We'll probably extend this to
    do more things later.
    """
    global _context

    if _context is None:
        _context = _init_context()

    if ssl.HAS_SNI:
        return _context.wrap_socket(socket, server_hostname=server_hostname)

    return _context.wrap_socket(socket)


def _init_context():
    """
    Creates the singleton SSLContext we use.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.set_default_verify_paths()
    context.load_verify_locations(cafile=cert_loc)
    context.verify_mode = ssl.CERT_REQUIRED

    try:
        context.set_npn_protocols(SUPPORTED_PROTOCOLS)
    except (AttributeError, NotImplementedError):
        pass

    # We do our best to do better security
    try:
        context.options |= ssl.OP_NO_SSLv2
    except AttributeError:
        pass

    try:
        context.options |= ssl.OP_NO_COMPRESSION
    except AttributeError:
        pass

    return context
