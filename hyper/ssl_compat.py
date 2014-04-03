# -*- coding: utf-8 -*-
"""
hyper/ssl_compat
~~~~~~~~~

Shoves pyOpenSSL into an API that looks like the standard Python 3.x ssl module.

Currently exposes exactly those attributes, classes, and methods that we
actually use in hyper (all method signatures are complete, however). May be
expanded to something more general-purpose in the future.
"""
import StringIO
import errno
import socket
import time

from OpenSSL import SSL as ossl

CERT_NONE = ossl.VERIFY_NONE
CERT_REQUIRED = ossl.VERIFY_PEER | ossl.VERIFY_FAIL_IF_NO_PEER_CERT

PROTOCOL_SSLv23 = ossl.SSLv23_METHOD

for name in ['OP_NO_COMPRESSION', 'OP_NO_SSLv2']:
    value = getattr(ossl, name, None)
    if value:
        locals()[name] = value

OP_ALL = 0
for bit in [31] + list(range(10)): # TODO figure out the names of these other flags
    OP_ALL |= 1 << bit

HAS_NPN = False # TODO
HAS_SNI = False # TODO

def _proxy(method):
    return lambda self, *args, **kwargs: getattr(self._conn, method)(*args, **kwargs)

class SSLSocket(object):
    SSL_TIMEOUT = 3
    SSL_RETRY = .01

    def __init__(self, conn, server_side, do_handshake_on_connect,
                 suppress_ragged_eofs):
        self._conn = conn
        self._do_handshake_on_connect = do_handshake_on_connect
        self._suppress_ragged_eofs = suppress_ragged_eofs

        if server_side:
            self._conn.set_accept_state()
        else:
            self._conn.set_connect_state() # FIXME does this override do_handshake_on_connect=False?

        try:
            self._conn.getpeername()
        except socket.error as e:
            if e.errno != errno.ENOTCONN:
                raise
        else:
            # The socket is already connected, so do the handshake.
            if self._do_handshake_on_connect:
                self.do_handshake()

    # Lovingly stolen from CherryPy (http://svn.cherrypy.org/tags/cherrypy-3.2.1/cherrypy/wsgiserver/ssl_pyopenssl.py).
    def _safe_ssl_call(self, suppress_ragged_eofs, call, *args, **kwargs):
        """Wrap the given call with SSL error-trapping."""
        start = time.time()
        while True:
            try:
                return call(*args, **kwargs)
            except (ossl.WantReadError, ossl.WantWriteError):
                # Sleep and try again. This is dangerous, because it means
                # the rest of the stack has no way of differentiating
                # between a "new handshake" error and "client dropped".
                # Note this isn't an endless loop: there's a timeout below.
                time.sleep(self.SSL_RETRY)
            except ossl.Error as e:
                if suppress_ragged_eofs and e.args == (-1, 'Unexpected EOF'):
                    return b''
                raise socket.error(e.args[0])
            except:
                raise

            if time.time() - start > self.SSL_TIMEOUT:
                raise socket.timeout('timed out')

    def connect(self, address):
        self._conn.connect(address)
        if self._do_handshake_on_connect:
            self.do_handshake()

    def do_handshake(self):
        self._safe_ssl_call(False, self._conn.do_handshake)

    def recv(self, bufsize, flags=None):
        return self._safe_ssl_call(self._suppress_ragged_eofs, self._conn.recv,
                               bufsize, flags)

    def send(self, data, flags=None):
        return self._safe_ssl_call(False, self._conn.send, data, flags)

    def selected_npn_protocol(self):
        raise NotImplementedError()

    # a dash of magic to reduce boilerplate
    for method in ['accept', 'bind', 'close', 'getsockname', 'listen']:
        locals()[method] = _proxy(method)


class SSLContext(object):
    def __init__(self, protocol):
        self.protocol = protocol
        self._ctx = ossl.Context(protocol)
        self.options = OP_ALL

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, value):
        self._options = value
        self._ctx.set_options(value)

    @property
    def verify_mode(self):
        return self._ctx.get_verify_mode()

    @verify_mode.setter
    def verify_mode(self, value):
        # TODO verify exception is raised on failure
        self._ctx.set_verify(value, lambda conn, cert, errnum, errdepth, ok: ok)

    def set_default_verify_paths(self):
        self._ctx.set_default_verify_paths()

    def load_verify_locations(self, cafile=None, capath=None, cadata=None):
        self._ctx.load_verify_locations(cafile, capath)
        if cadata is not None:
            self._ctx.load_verify_locations(StringIO(cadata))

    def load_cert_chain(self, certfile, keyfile=None, password=None):
        self._ctx.use_certificate_file(certfile)
        if password is not None:
            self._ctx.set_password_cb(lambda max_length, prompt_twice, userdata: password)
        self._ctx.use_privatekey_file(keyfile or certfile)

    def set_npn_protocols(self, protocols):
        # TODO
        raise NotImplementedError()

    def wrap_socket(self, sock, server_side=False, do_handshake_on_connect=True,
                    suppress_ragged_eofs=True, server_hostname=None):
        if server_hostname is not None:
            raise NotImplementedError("server_hostname is not yet supported")

        conn = ossl.Connection(self._ctx, sock)
        return SSLSocket(conn, server_side, do_handshake_on_connect,
                         suppress_ragged_eofs)
