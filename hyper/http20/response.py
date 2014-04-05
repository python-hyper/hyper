# -*- coding: utf-8 -*-
"""
hyper/http20/response
~~~~~~~~~~~~~~~~~~~~~

Contains the HTTP/2.0 equivalent of the HTTPResponse object defined in
httplib/http.client.
"""
import zlib


class DeflateDecoder(object):
    """
    This is a decoding object that wraps ``zlib`` and is used for decoding
    deflated content.

    This rationale for the existence of this object is pretty unpleasant.
    The HTTP RFC specifies that 'deflate' is a valid content encoding. However,
    the spec _meant_ the zlib encoding form. Unfortunately, people who didn't
    read the RFC very carefully actually implemented a different form of
    'deflate'. Insanely, ``zlib`` handles them using two wbits values. This is
    such a mess it's hard to adequately articulate.

    This class was lovingly borrowed from the excellent urllib3 library under
    license: see NOTICES. If you ever see @shazow, you should probably buy him
    a drink or something.
    """
    def __init__(self):
        self._first_try = True
        self._data = b''
        self._obj = zlib.decompressobj(zlib.MAX_WBITS)

    def __getattr__(self, name):
        return getattr(self._obj, name)

    def decompress(self, data):
        if not self._first_try:
            return self._obj.decompress(data)

        self._data += data
        try:
            return self._obj.decompress(data)
        except zlib.error:
            self._first_try = False
            self._obj = zlib.decompressobj(-zlib.MAX_WBITS)
            try:
                return self.decompress(self._data)
            finally:
                self._data = None


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
        # once, and never assigned again. If a header name is repeated, its
        # values are concatenated with ``,``.
        list_headers = {}
        for name, value in headers:
            list_headers.setdefault(name, []).append(value)
        self._headers = {name: ','.join(value) for name, value in list_headers.items()}

        #: The status code returned by the server.
        self.status = int(self._headers[':status'])
        del self._headers[':status']

        # The stream this response is being sent over.
        self._stream = stream

        # We always read in one-data-frame increments from the stream, so we
        # may need to buffer some for incomplete reads.
        self._data_buffer = b''

        # This object is used for decompressing gzipped request bodies. Right
        # now we only support gzip because that's all the RFC mandates of us.
        # Later we'll add support for more encodings.
        # This 16 + MAX_WBITS nonsense is to force gzip. See this
        # Stack Overflow answer for more:
        # http://stackoverflow.com/a/2695466/1401686
        if self._headers.get('content-encoding', '') == 'gzip':
            self._decompressobj = zlib.decompressobj(16 + zlib.MAX_WBITS)
        elif self._headers.get('content-encoding', '') == 'deflate':
            self._decompressobj = DeflateDecoder()
        else:
            self._decompressobj = None

    def read(self, amt=None, decode_content=True):
        """
        Reads the response body, or up to the next ``amt`` bytes.

        :param amt: (optional) The amount of data to read. If not provided, all
            the data will be read from the response.
        :param decode_content: (optional) If ``True``, will transparently
            decode the response data.
        :returns: The read data. Note that if ``decode_content`` is set to
            ``True``, the actual amount of data returned may be different to
            the amount requested.
        """
        if amt is not None and amt <= len(self._data_buffer):
            data = self._data_buffer[:amt]
            self._data_buffer = self._data_buffer[amt:]
            response_complete = False
        elif amt is not None:
            read_amt = amt - len(self._data_buffer)
            self._data_buffer += self._stream._read(read_amt)
            data = self._data_buffer[:amt]
            self._data_buffer = self._data_buffer[amt:]
            response_complete = len(data) < amt
        else:
            data = b''.join([self._data_buffer, self._stream._read()])
            response_complete = True

        # We may need to decode the body.
        if decode_content and self._decompressobj and data:
            data = self._decompressobj.decompress(data)

        # If we're at the end of the request, we have some cleaning up to do.
        # Close the stream, and if necessary flush the buffer.
        if response_complete:
            if decode_content and self._decompressobj:
                data += self._decompressobj.flush()

        if not data:
            self.close()

        return data

    def getheader(self, name, default=None):
        """
        Return the value of the header ``name``, or ``default`` if there is no
        header matching ``name``. If there is more than one header with the
        value ``name``, return all of the values joined by ', '. If ``default``
        is any iterable other than a single string, its elements are similarly
        returned joined by commas.

        :param name: The name of the header to get the value of.
        :param default: (optional) The return value if the header wasn't sent.
        :returns: The value of the header.
        """
        return self._headers.get(name, default)

    def getheaders(self):
        """
        Get all the headers sent on the response.

        :returns: A list of (header, value) tuples.
        """
        return list(self._headers.items())

    def fileno(self):
        """
        Return the ``fileno`` of the underlying socket. This function is
        currently not implemented.
        """
        raise NotImplementedError("Not currently implemented.")

    def close(self):
        """
        Close the response. In effect this closes the backing HTTP/2.0 stream.

        :returns: Nothing.
        """
        self._stream.close()

    # The following methods implement the context manager protocol.
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        return False  # Never swallow exceptions.
