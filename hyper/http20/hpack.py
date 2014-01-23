# -*- coding: utf-8 -*-
"""
hyper/http20/hpack
~~~~~~~~~~~~~~~~~~

Implements the HPACK header compression algorithm as detailed by the IETF.

Implements the version dated January 9, 2014.
"""
def encode_integer(integer, prefix_bits):
    """
    This encodes an integer according to the wacky integer encoding rules
    defined in the HPACK spec.
    """
    max_number = (2 ** prefix_bits) - 1

    if (integer < max_number):
        return bytearray([integer])  # Seriously?
    else:
        elements = [max_number]
        integer = integer - max_number

        while integer >= 128:
            elements.append((integer % 128) + 128)
            integer = integer // 128  # We need integer division

        elements.append(integer)

        return bytearray(elements)



class Encoder(object):
    """
    An HPACK encoder object. This object takes HTTP headers and emits encoded
    HTTP/2.0 header blocks.
    """
    # This is the static table of header fields.
    static_table = [
        (':authority', ''),
        (':method', 'GET'),
        (':method', 'POST'),
        (':path', '/'),
        (':path', '/index.html'),
        (':scheme', 'http'),
        (':scheme', 'https'),
        (':status', '200'),
        (':status', '500'),
        (':status', '404'),
        (':status', '403'),
        (':status', '400'),
        (':status', '401'),
        ('accept-charset', ''),
        ('accept-encoding', ''),
        ('accept-language', ''),
        ('accept-ranges  ', ''),
        ('accept', ''),
        ('access-control-allow-origin', ''),
        ('age', ''),
        ('allow', ''),
        ('authorization', ''),
        ('cache-control', ''),
        ('content-disposition', ''),
        ('content-encoding', ''),
        ('content-language', ''),
        ('content-length', ''),
        ('content-location', ''),
        ('content-range', ''),
        ('content-type', ''),
        ('cookie', ''),
        ('date', ''),
        ('etag', ''),
        ('expect', ''),
        ('expires', ''),
        ('from', ''),
        ('host', ''),
        ('if-match', ''),
        ('if-modified-since', ''),
        ('if-none-match', ''),
        ('if-range', ''),
        ('if-unmodified-since', ''),
        ('last-modified', ''),
        ('link', ''),
        ('location', ''),
        ('max-forwards', ''),
        ('proxy-authenticate', ''),
        ('proxy-authorization', ''),
        ('range', ''),
        ('referer', ''),
        ('refresh', ''),
        ('retry-after', ''),
        ('server', ''),
        ('set-cookie', ''),
        ('strict-transport-security', ''),
        ('transfer-encoding', ''),
        ('user-agent', ''),
        ('vary', ''),
        ('via', ''),
        ('www-authenticate', ''),
    ]

    def __init__(self):
        self.header_table = []
        self.reference_set = set()
        self.header_table_size = 4096  # This value set by the standard.

    def encode(self, headers, huffman=True):
        """
        Takes a set of headers and encodes them into a HPACK-encoded header
        block.

        Transforming the headers into a header block is a procedure that can
        be modeled as a chain or pipe. First, the headers are compared against
        the reference set. Any headers already in the reference set don't need
        to be emitted at all, they can be left alone. Headers not in the
        reference set need to be emitted. Headers in the reference set that
        need to be removed (potentially to be replaced) need to be emitted as
        well.

        Next, the headers are encoded. This encoding can be done a number of
        ways. If the header name-value pair are already in the header table we
        can represent them using the indexed representation: the same is true
        if they are in the static table. Otherwise, a literal representation
        will be used.

        Literal text values may optionally be Huffman encoded. For now we don't
        do that, because it's an extra bit of complication, but we will later.
        """
        # First, turn the headers into an iterable of tuples if possible. This
        # is the natural way to interact with them in HPACK.
        if isinstance(headers, dict):
            headers = headers.items()

        for name, value in headers:
            # First, we need to determine what set of headers we need to emit.
            # We do this by comparing against the reference set.

            # Check if we're already in the header table.
            name_matches = self.matching_header(name, value)

            if name_matches is not None and name_matches[1]:
                pass
            elif name_matches is not None:
                # Have a partial match.
                pass
            else:
                # No match, need to use a literal.
                pass


    def matching_header(self, name, value):
        """
        Scans the header table and the static table. Returns a tuple, where the
        first value is the index of the match, and the second is whether there
        was a full match or not. Prefers full matches to partial ones.

        Upsettingly, the header table is one-indexed, not zero-indexed.
        """
        partial_match = None
        header_table_size = len(self.header_table)

        for (i, (n, v)) in enumerate(self.header_table):
            if n == name:
                if v == value:
                    return (i + 1, True)
                elif partial_match is None:
                    partial_match = (i + 1, False)

        for (i, (n, v)) in enumerate(Encoder.static_table):
            if n == name:
                if v == value:
                    return (i + header_table_size + 1, True)
                elif partial_match is None:
                    partial_match = (i + header_table_size + 1, False)

        return partial_match

    def _encode_indexed(self, index):
        """
        Encodes a header using the indexed representation.
        """
        field = encode_integer(index, 7)
        field[0] = field[0] | 0x80  # we set the top bit
        return field

    def _encode_literal(self, name, value, indexing):
        """
        Encodes a header with a literal name and literal value. If ``indexing``
        is True, the header will be added to the header table: otherwise it
        will not.
        """
        prefix = 0x40 if indexing else 0x00

        name = name.encode('utf-8')
        value = value.encode('utf-8')
        name_len = encode_integer(len(name), 8)
        value_len = encode_integer(len(value), 8)

        return b''.join([prefix, name_len, name, value_len, value])

    def _encode_indexed_literal(self, index, value, indexing):
        """
        Encodes a header with an indexed name and a literal value. If
        ``indexing`` is True, the header will be added to the header table:
        otherwise it will not.
        """
        mask = 0x40 if indexing else 0x00

        name = encode_integer(index, 6)
        name[0] = name[0] | mask

        value = value.encode('utf-8')
        value_len = encode_integer(len(value), 8)

        return b''.join([name, value_len, value])


class Decoder(object):
    """
    An HPACK decoder object.
    """
    static_table = []

    def __init__(self):
        self.header_table = []
        self.reference_set = set()
        self.header_table_size = 4096  # This value set by the standard.
