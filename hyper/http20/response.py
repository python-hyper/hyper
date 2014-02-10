# -*- coding: utf-8 -*-
"""
hyper/http20/response
~~~~~~~~~~~~~~~~~~~~~

Contains the HTTP/2.0 equivalent of the HTTPResponse object defined in
httplib/http.client.
"""
class HTTP20Response(object):
    """
    An ``HTTP20Response`` wraps the HTTP/2.0 response from the server. It
    provides access to the response headers and the entity body. The response
    is an iterable object and can be used in a with statement (though due to
    the persistent connections used in HTTP/2.0 this has no effect, and is done
    soley for compatibility).
    """
    def __init__(self, headers, stream):
        #: The reason phrase returned by the server. This is not used in
        #: HTTP/2.0, and so is always the empty string.
        self.reason = ''

        # The response headers. These are determined upon creation, assigned
        # once, and never assigned again.
        # This conversion to dictionary is unwise, as there may be repeated
        # keys, but it's acceptable for an early alpha.
        self._headers = dict(headers)

        # The stream this response is being sent over.
        self._stream = stream

        # We always read in one-data-frame increments from the stream, so we
        # may need to buffer some for incomplete reads.
        self._data_buffer = b''

    def read(self, amt=None):
        """
        Reads the response body, or up to the next ``amt`` bytes.
        """
        if amt is not None and amt <= len(self._data_buffer):
            data = self._data_buffer[:amt]
            self._data_buffer = self._data_buffer[amt:]
            return data
        elif amt is not None:
            read_amt = amt - len(self._data_buffer)
            self._data_buffer += self._stream._read(read_amt)
            data = self._data_buffer[:amt]
            self._data_buffer = self._data_buffer[amt:]
            return data
        else:
            return b''.join([self._data_buffer, self._stream._read()])

    def getheader(self, name, default=None):
        """
        Return the value of the header ``name``, or ``default`` if there is no
        header matching ``name``. If there is more than one header with the
        value ``name``, return all of the values joined by ', '. If ``default``
        is any iterable other than a single string, its elements are similarly
        returned joined by commas.
        """
        return self._headers.get(name, default)

    def getheaders(self):
        """
        Return a list of (header, value) tuples.
        """
        return list(self._headers.items())

    def fileno(self):
        """
        Return the ``fileno`` of the underlying socket.
        """
        pass

    @property
    def status(self):
        """
        Status code returned by the server.
        """
        return int(self._headers[':status'])
