# -*- coding: utf-8 -*-
"""
hyper/tls
~~~~~~~~~

Contains the TLS/SSL logic for use in hyper.
"""
import ssl
import os.path as path

from ..compat import is_py3


# Right now we support draft 9.
SUPPORTED_PROTOCOLS = ['http/1.1', 'HTTP-draft-09/2.0']


# We have a singleton SSLContext object. There's no reason to be creating one
# per connection. We're using v23 right now until someone gives me a reason not
# to.
_context = None

# Exposed here so it can be monkey-patched in integration tests.
_verify_mode = ssl.CERT_REQUIRED


# Work out where our certificates are.
cert_loc = path.join(path.dirname(__file__), '..', 'certs.pem')


if is_py3:
    def wrap_socket(socket, server_hostname):
        """
        A vastly simplified SSL wrapping function. We'll probably extend this to
        do more things later.
        """
        global _context

        if _context is None:  # pragma: no cover
            _context = _init_context()

        if ssl.HAS_SNI:
            return _context.wrap_socket(socket, server_hostname=server_hostname)

        wrapped = _context.wrap_socket(socket)  # pragma: no cover
        assert wrapped.selected_npn_protocol() == 'HTTP-draft-09/2.0'
        return wrapped
else:
    def wrap_socket(socket, server_hostname):
        return ssl.wrap_socket(socket, ssl_version=ssl.PROTOCOL_SSLv23,
            ca_certs=cert_loc, cert_reqs=_verify_mode)


def _init_context():
    """
    Creates the singleton SSLContext we use.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.set_default_verify_paths()
    context.load_verify_locations(cafile=cert_loc)
    context.verify_mode = _verify_mode

    try:
        context.set_npn_protocols(SUPPORTED_PROTOCOLS)
    except (AttributeError, NotImplementedError):  # pragma: no cover
        pass

    # We do our best to do better security
    try:
        context.options |= ssl.OP_NO_SSLv2
    except AttributeError:  # pragma: no cover
        pass

    try:
        context.options |= ssl.OP_NO_COMPRESSION
    except AttributeError:  # pragma: no cover
        pass

    return context
