# -*- coding: utf-8 -*-
"""
hyper/http20/response
~~~~~~~~~~~~~~~~~~~~~

Contains the HTTP/2 equivalent of the HTTPResponse object defined in
httplib/http.client.
"""
import logging

log = logging.getLogger(__name__)


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


class HTTP11Response(object):
    """
    An ``HTTP11Response`` wraps the HTTP/1.1 response from the server. It
    provides access to the response headers and the entity body. The response
    is an iterable object and can be used in a with statement.
    """
    def __init__(self, headers, sock):
        #: The reason phrase returned by the server.
        self.reason = ''

        #: The status code returned by the server.
        self.status = 0

        # The response headers. These are determined upon creation, assigned
        # once, and never assigned again.
        self._headers = headers

        # The response trailers. These are always intially ``None``.
        self._trailers = None

        # The socket this response is being sent over.
        self._sock = sock

        # We always read in one-data-frame increments from the stream, so we
        # may need to buffer some for incomplete reads.
        self._data_buffer = b''

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
        # For now, just read what we're asked, unless we're not asked:
        # then, read content-length. This obviously doesn't work longer term,
        # we need to do some content-length processing there.
        if amt is None:
            amt = self.headers.get(b'content-length', 0)

        # Return early if we've lost our connection.
        if self._sock is None:
            return b''

        data = self._sock.read(amt)

        # We may need to decode the body.
        if decode_content and self._decompressobj and data:
            data = self._decompressobj.decompress(data)

        # If we're at the end of the request, we have some cleaning up to do.
        # Close the stream, and if necessary flush the buffer.
        if decode_content and self._decompressobj:
            data += self._decompressobj.flush()

        # We're at the end. Close the connection.
        if not data:
            self.close()

        return data

    def fileno(self):
        """
        Return the ``fileno`` of the underlying socket. This function is
        currently not implemented.
        """
        raise NotImplementedError("Not currently implemented.")

    def close(self):
        """
        Close the response. In effect this closes the backing HTTP/2 stream.

        :returns: Nothing.
        """
        self._sock = None

    # The following methods implement the context manager protocol.
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        return False  # Never swallow exceptions.
