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
        # First, turn the headers into a list of tuples if possible. This is
        # the natural way to interact with them in HPACK.
        if isinstance(headers, dict):
            incoming_set = set(headers.items())
        else:
            incoming_set = set(headers)

        # First, we need to determine what set of headers we need to emit.
        # We do this by comparing against the reference set.
        to_add = incoming_set - self.reference_set
        to_remove = self.reference_set - incoming_set

        # Now, serialize the headers. Do removal first.
        header_block = self.remove(to_remove)
        header_block += self.add(to_add)

        return header_block

    def remove(self, to_remove):
        """
        This function takes a set of header key-value tuples and serializes
        them. These must be in the header table, so must be represented as
        their indexed form.
        """
        encoded = []

        for name, value in to_remove:
            try:
                index, perfect = self.matching_header(name, value)
            except TypeError:
                index, perfect = -1, False

            # The header must be in the header block. That means that:
            # - perfect must be True
            # - index must be <= len(self.header_table)
            max_index = len(self.header_table)

            if (not perfect) or (index > max_index):
                raise ValueError(
                    '"%s: %s" not present in the header table' % (name, value)
                )

            # We can safely encode this as the indexed representation.
            encoded.append(self._encode_indexed(index))

            # Having encoded it in the indexed form, we now remove it from the
            # header table and the reference set.
            del self.header_table[index]
            self.reference_set.remove((name, value))

        return b''.join(encoded)

    def add(self, to_add):
        """
        This function takes a set of header key-valu tuples and serializes
        them for adding to the header table.
        """
        encoded = []

        for name, value in to_add:
            # Search for a matching header in the header table.
            match = self.matching_header(name, value)

            if match is None:
                # Not in the header table. Encode using the literal syntax,
                # and add it to the header table.
                s = self._encode_literal(name, value, True)
                encoded.append(s)
                self.header_table.insert(0, (name, value))
                self.reference_set.add((name, value))
                continue

            # The header is in the table, break out the values. If we matched
            # perfectly, we can use the indexed representation: otherwise we
            # can use the indexed literal.
            index, perfect = match

            if perfect:
                # Indexed representation. If the index is larger than the size
                # of the header table, also add to the header table.
                s = self._encode_indexed(index)
                encoded.append(s)

                if index > len(self.header_table):
                    self.header_table.insert(0, (name, value))
            else:
                # Indexed literal. Since we have a partial match, don't add to
                # the header table, it won't help us.
                s = self._encode_indexed_literal(index, value, False)
                encoded.append(s)

            # Either way, we add to the reference set.
            self.reference_set.add((name, value))

        return b''.join(encoded)

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
        prefix = bytes([0x00 if indexing else 0x40])

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
        mask = 0x00 if indexing else 0x40

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
