# -*- coding: utf-8 -*-
"""
hyper/http11/connection
~~~~~~~~~~~~~~~~~~~~~~~

Objects that build hyper's connection-level HTTP/1.1 abstraction.
"""
import io
import logging
import socket

from .response import HTTP11Response
from ..http20.bufsocket import BufferedSocket

log = logging.getLogger(__name__)


class HTTP11Connection(object):
    """
    An object representing a single HTTP/1.1 connection to a server.

    :param host: The host to connect to. This may be an IP address or a
        hostname, and optionally may include a port: for example,
        ``'twitter.com'``, ``'twitter.com:443'`` or ``'127.0.0.1'``.
    :param port: (optional) The port to connect to. If not provided and one also
        isn't provided in the ``host`` parameter, defaults to 443.
    """
    def __init__(self, host, port):
        if port is None:
            try:
                self.host, self.port = host.split(':')
                self.port = int(self.port)
            except ValueError:
                self.host, self.port = host, 443
        else:
            self.host, self.port = host, port

        self._sock = None

        #: The size of the in-memory buffer used to store data from the
        #: network. This is used as a performance optimisation. Increase buffer
        #: size to improve performance: decrease it to conserve memory.
        #: Defaults to 64kB.
        self.network_buffer_size = 65536

    def connect(self):
        """
        Connect to the server specified when the object was created. This is a
        no-op if we're already connected.

        :returns: Nothing.
        """
        if self._sock is None:
            sock = socket.create_connection((self.host, self.port), 5)
            self._sock = BufferedSocket(sock, self.network_buffer_size)

        return

    def request(self, method, url, body=None, headers={}):
        """
        This will send a request to the server using the HTTP request method
        ``method`` and the selector ``url``. If the ``body`` argument is
        present, it should be string or bytes object of data to send after the
        headers are finished. Strings are encoded as UTF-8. To use other
        encodings, pass a bytes object. The Content-Length header is set to the
        length of the body field.

        :param method: The request method, e.g. ``'GET'``.
        :param url: The URL to contact, e.g. ``'/path/segment'``.
        :param body: (optional) The request body to send. Must be a bytestring
            or a file-like object.
        :param headers: (optional) The headers to send on the request.
        :returns: Nothing.
        """
        if self._sock is None:
            self.connect()

        # In this initial implementation, let's just write straight to the
        # socket. We'll fix this up as we go.
        # TODO: Fix fix fix.
        self._sock.send(b' '.join([method, url, b'HTTP/1.1\r\n']))

        for name, value in headers.items():
            self._sock.send(name)
            self._sock.send(b': ')
            self._sock.send(value)
            self._sock.send(b'\r\n')

        self._sock.send(b'\r\n')

        if body:
            # TODO: Come back here to support non-string bodies.
            self._sock.send(body)

        return

    def get_response(self):
        """
        Returns a response object.

        This is an early beta, so the response object is pretty stupid. That's
        ok, we'll fix it later.
        """
        headers = {}

        # First read the header line and drop it on the floor.
        self._sock.readline()

        while True:
            line = self._sock.readline().tobytes()
            if len(line) <= 2:
                break

            name, val = line.split(b':', 1)
            val = val.lstrip().rstrip(b'\r\n')
            headers[name] = val

        return HTTP11Response(headers, self._sock)
