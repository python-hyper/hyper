# -*- coding: utf-8 -*-
"""
hyper/http20/hpack
~~~~~~~~~~~~~~~~~~

Implements the HPACK header compression algorithm as detailed by the IETF.

Implements the version dated January 9, 2014.
"""
from .huffman import HuffmanDecoder, HuffmanEncoder
from hyper.http20.huffman_constants import (
    REQUEST_CODES, REQUEST_CODES_LENGTH, RESPONSE_CODES, RESPONSE_CODES_LENGTH
)


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


def decode_integer(data, prefix_bits):
    """
    This decodes an integer according to the wacky integer encoding rules
    defined in the HPACK spec. Returns a tuple of the decoded integer and the
    number of bytes that were consumed from ``data`` in order to get that
    integer.
    """
    multiple = lambda index: 128 ** (index - 1)
    max_number = (2 ** prefix_bits) - 1
    mask = 0xFF >> (8 - prefix_bits)
    index = 0

    number = data[index] & mask

    if (number == max_number):

        while True:
            index += 1
            next_byte = data[index]

            if next_byte >= 128:
                number += (next_byte - 128) * multiple(index)
            else:
                number += next_byte * multiple(index)
                break

    return (number, index + 1)


def header_table_size(table):
    """
    Calculates the 'size' of the header table as defined by the HTTP/2.0
    specification.
    """
    # It's phenomenally frustrating that the specification feels it is able to
    # tell me how large the header table is, considering that its calculations
    # assume a very particular layout that most implementations will not have.
    # I appreciate it's an attempt to prevent DoS attacks by sending lots of
    # large headers in the header table, but it seems like a better approach
    # would be to limit the size of headers. Ah well.
    return sum(32 + len(name) + len(value) for name, value in table)


class Encoder(object):
    """
    An HPACK encoder object. This object takes HTTP headers and emits encoded
    HTTP/2.0 header blocks.
    """
    # This is the static table of header fields.
    static_table = [
        (b':authority', b''),
        (b':method', b'GET'),
        (b':method', b'POST'),
        (b':path', b'/'),
        (b':path', b'/index.html'),
        (b':scheme', b'http'),
        (b':scheme', b'https'),
        (b':status', b'200'),
        (b':status', b'500'),
        (b':status', b'404'),
        (b':status', b'403'),
        (b':status', b'400'),
        (b':status', b'401'),
        (b'accept-charset', b''),
        (b'accept-encoding', b''),
        (b'accept-language', b''),
        (b'accept-ranges', b''),
        (b'accept', b''),
        (b'access-control-allow-origin', b''),
        (b'age', b''),
        (b'allow', b''),
        (b'authorization', b''),
        (b'cache-control', b''),
        (b'content-disposition', b''),
        (b'content-encoding', b''),
        (b'content-language', b''),
        (b'content-length', b''),
        (b'content-location', b''),
        (b'content-range', b''),
        (b'content-type', b''),
        (b'cookie', b''),
        (b'date', b''),
        (b'etag', b''),
        (b'expect', b''),
        (b'expires', b''),
        (b'from', b''),
        (b'host', b''),
        (b'if-match', b''),
        (b'if-modified-since', b''),
        (b'if-none-match', b''),
        (b'if-range', b''),
        (b'if-unmodified-since', b''),
        (b'last-modified', b''),
        (b'link', b''),
        (b'location', b''),
        (b'max-forwards', b''),
        (b'proxy-authenticate', b''),
        (b'proxy-authorization', b''),
        (b'range', b''),
        (b'referer', b''),
        (b'refresh', b''),
        (b'retry-after', b''),
        (b'server', b''),
        (b'set-cookie', b''),
        (b'strict-transport-security', b''),
        (b'transfer-encoding', b''),
        (b'user-agent', b''),
        (b'vary', b''),
        (b'via', b''),
        (b'www-authenticate', b''),
    ]

    def __init__(self):
        self.header_table = []
        self.reference_set = set()
        self._header_table_size = 4096  # This value set by the standard.
        self.huffman_coder = HuffmanEncoder(
            REQUEST_CODES, REQUEST_CODES_LENGTH
        )

    @property
    def header_table_size(self):
        return self._header_table_size

    @header_table_size.setter
    def header_table_size(self, value):
        # If the new value is larger than the current one, no worries!
        # Otherwise, we may need to shrink the header table.
        if value < self._header_table_size:
            current_size = header_table_size(self.header_table)

            while value < current_size:
                n, v = self.header_table.pop()
                current_size -= (
                    32 + len(n) + len(v)
                )

                # If something is removed from the header table, it also needs
                # to be removed from the reference set.
                self.reference_set.discard((n, v))

        self._header_table_size = value

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
            headers = headers.items()

        # Next, walk across the headers and turn them all into bytestrings.
        headers = [(n.encode('utf-8'), v.encode('utf-8')) for n, v in headers]

        incoming_set = set(headers)

        # First, we need to determine what set of headers we need to emit.
        # We do this by comparing against the reference set.
        # Because the HPACK standard defines a header set as 'potentially
        # ordered', we should try to maintain their order. It's a hassle, but
        # there we go.
        to_add = (x for x in headers if x in incoming_set - self.reference_set)
        to_remove = (self.reference_set - incoming_set)

        # Now, serialize the headers. Do removal first.
        # If the list of headers we're removing is more than half of the
        # reference set, just emit an 'empty the reference set' message.
        if (len(self.reference_set - incoming_set) >
                                               (len(self.reference_set) // 2)):
            header_block = b'\x80'  # Indexed representation of 0.

            # Remove everything from the reference set.
            self.reference_set = set()
        else:
            header_block = self.remove(to_remove)

        header_block += self.add(to_add, huffman)

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
            # reference set.
            self.reference_set.remove((name, value))

        return b''.join(encoded)

    def add(self, to_add, huffman=False):
        """
        This function takes a set of header key-value tuples and serializes
        them for adding to the header table.
        """
        encoded = []

        for name, value in to_add:
            # Search for a matching header in the header table.
            match = self.matching_header(name, value)

            if match is None:
                # Not in the header table. Encode using the literal syntax,
                # and add it to the header table.
                s = self._encode_literal(name, value, True, huffman)
                encoded.append(s)
                self._add_to_header_table(name, value)
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
                    self._add_to_header_table(name, value)

                self.reference_set.add((name, value))
            else:
                # Indexed literal. Since we have a partial match, don't add to
                # the header table, it won't help us.
                s = self._encode_indexed_literal(index, value, False, huffman)
                encoded.append(s)

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

    def _add_to_header_table(self, name, value):
        """
        Adds a header to the header table, evicting old ones if necessary.
        """
        # Be optimistic: add the header straight away.
        self.header_table.insert(0, (name, value))

        # Now, work out how big the header table is.
        actual_size = header_table_size(self.header_table)

        # Loop and remove whatever we need to.
        while actual_size > self.header_table_size:
            n, v = self.header_table.pop()
            actual_size -= (
                32 + len(n) + len(v)
            )

            # If something is removed from the header table, it also needs to
            # be removed from the reference set.
            self.reference_set.discard((n, v))

    def _encode_indexed(self, index):
        """
        Encodes a header using the indexed representation.
        """
        field = encode_integer(index, 7)
        field[0] = field[0] | 0x80  # we set the top bit
        return field

    def _encode_literal(self, name, value, indexing, huffman=False):
        """
        Encodes a header with a literal name and literal value. If ``indexing``
        is True, the header will be added to the header table: otherwise it
        will not.
        """
        prefix = bytes([0x00 if indexing else 0x40])

        if huffman:
            name = self.huffman_coder.encode(name)
            value = self.huffman_coder.encode(value)

        name_len = encode_integer(len(name), 7)
        value_len = encode_integer(len(value), 7)

        if huffman:
            name_len[0] |= 0x80
            value_len[0] |= 0x80

        return b''.join([prefix, name_len, name, value_len, value])

    def _encode_indexed_literal(self, index, value, indexing, huffman=False):
        """
        Encodes a header with an indexed name and a literal value. If
        ``indexing`` is True, the header will be added to the header table:
        otherwise it will not.
        """
        mask = 0x00 if indexing else 0x40

        name = encode_integer(index, 6)
        name[0] = name[0] | mask

        if huffman:
            value = self.huffman_coder.encode(value)

        value_len = encode_integer(len(value), 7)

        if huffman:
            value_len[0] |= 0x80

        return b''.join([name, value_len, value])


class Decoder(object):
    """
    An HPACK decoder object.
    """
    static_table = []    # This is the static table of header fields.
    static_table = [
        (b':authority', b''),
        (b':method', b'GET'),
        (b':method', b'POST'),
        (b':path', b'/'),
        (b':path', b'/index.html'),
        (b':scheme', b'http'),
        (b':scheme', b'https'),
        (b':status', b'200'),
        (b':status', b'500'),
        (b':status', b'404'),
        (b':status', b'403'),
        (b':status', b'400'),
        (b':status', b'401'),
        (b'accept-charset', b''),
        (b'accept-encoding', b''),
        (b'accept-language', b''),
        (b'accept-ranges', b''),
        (b'accept', b''),
        (b'access-control-allow-origin', b''),
        (b'age', b''),
        (b'allow', b''),
        (b'authorization', b''),
        (b'cache-control', b''),
        (b'content-disposition', b''),
        (b'content-encoding', b''),
        (b'content-language', b''),
        (b'content-length', b''),
        (b'content-location', b''),
        (b'content-range', b''),
        (b'content-type', b''),
        (b'cookie', b''),
        (b'date', b''),
        (b'etag', b''),
        (b'expect', b''),
        (b'expires', b''),
        (b'from', b''),
        (b'host', b''),
        (b'if-match', b''),
        (b'if-modified-since', b''),
        (b'if-none-match', b''),
        (b'if-range', b''),
        (b'if-unmodified-since', b''),
        (b'last-modified', b''),
        (b'link', b''),
        (b'location', b''),
        (b'max-forwards', b''),
        (b'proxy-authenticate', b''),
        (b'proxy-authorization', b''),
        (b'range', b''),
        (b'referer', b''),
        (b'refresh', b''),
        (b'retry-after', b''),
        (b'server', b''),
        (b'set-cookie', b''),
        (b'strict-transport-security', b''),
        (b'transfer-encoding', b''),
        (b'user-agent', b''),
        (b'vary', b''),
        (b'via', b''),
        (b'www-authenticate', b''),
    ]

    def __init__(self):
        self.header_table = []
        self.reference_set = set()
        self._header_table_size = 4096  # This value set by the standard.
        self.huffman_coder = HuffmanDecoder(
            RESPONSE_CODES, RESPONSE_CODES_LENGTH
        )

    @property
    def header_table_size(self):
        return self._header_table_size

    @header_table_size.setter
    def header_table_size(self, value):
        # If the new value is larger than the current one, no worries!
        # Otherwise, we may need to shrink the header table.
        if value < self._header_table_size:
            current_size = header_table_size(self.header_table)

            while value < current_size:
                n, v = self.header_table.pop()
                current_size -= (
                    32 + len(n) + len(v)
                )

                # If something is removed from the header table, it also needs
                # to be removed from the reference set.
                self.reference_set.discard((n, v))

        self._header_table_size = value

    def decode(self, data):
        """
        Takes an HPACK-encoded header block and decodes it into a header set.
        """
        headers = set()
        data_len = len(data)
        current_index = 0

        while current_index < data_len:
            # Work out what kind of header we're decoding.
            # If the high bit is 1, it's an indexed field.
            indexed = bool(data[current_index] & 0x80)

            # Otherwise, if the second-highest bit is 1 it's a field that
            # doesn't alter the header table.
            literal_no_index = bool(data[current_index] & 0x40)

            if indexed:
                header, consumed = self._decode_indexed(data[current_index:])
            elif literal_no_index:
                header, consumed = self._decode_literal_no_index(
                    data[current_index:]
                )
            else:
                # It's a literal header that does affect the header table.
                header, consumed = self._decode_literal_index(
                    data[current_index:]
                )

            if header:
                headers.add(header)

            current_index += consumed

        # Now we're at the end, anything in the reference set that isn't in the
        # headers already gets added.
        headers = headers | self.reference_set

        return {(n.decode('utf-8'), v.decode('utf-8')) for n, v in headers}

    def _add_to_header_table(self, name, value):
        """
        Adds a header to the header table, evicting old ones if necessary.
        """
        # Be optimistic: add the header straight away.
        self.header_table.insert(0, (name, value))

        # Now, work out how big the header table is.
        actual_size = header_table_size(self.header_table)

        # Loop and remove whatever we need to.
        while actual_size > self.header_table_size:
            n, v = self.header_table.pop()
            actual_size -= (
                32 + len(n) + len(v)
            )

            # If something is removed from the header table, it also needs to
            # be removed from the reference set.
            self.reference_set.discard((n, v))

    def _decode_indexed(self, data):
        """
        Decodes a header represented using the indexed representation.
        """
        index, consumed = decode_integer(data, 7)

        # If we get an indexed representation of zero, empty the reference set.
        if not index:
            self.reference_set = set()
            return None, consumed

        index -= 1  # Because this idiot table is 1-indexed. Ugh.

        if index > len(self.header_table):
            index -= len(self.header_table)
            header = Decoder.static_table[index]

            # If this came out of the static table, we need to add it to the
            # header table.
            self._add_to_header_table(*header)
        else:
            header = self.header_table[index]

        # If the header is in the reference set, remove it. Otherwise, add it.
        # Since this updates the reference set, don't bother returning the
        # header.
        if header in self.reference_set:
            self.reference_set.remove(header)
            return None, consumed
        else:
            self.reference_set.add(header)
            return header, consumed


    def _decode_literal_no_index(self, data):
        return self._decode_literal(data, False)

    def _decode_literal_index(self, data):
        return self._decode_literal(data, True)

    def _decode_literal(self, data, should_index):
        """
        Decodes a header represented with a literal.
        """
        total_consumed = 0

        # If the low six bits of the first byte are nonzero, the header
        # name is indexed.
        first_byte = data[0]

        if first_byte & 0x3F:
            # Indexed header name.
            index, consumed = decode_integer(data, 6)
            index -= 1

            if index >= len(self.header_table):
                index -= len(self.header_table)
                name = Decoder.static_table[index][0]
            else:
                name = self.header_table[index][0]

            total_consumed = consumed
            length = 0
        else:
            # Literal header name. The first byte was zero, so we need to
            # move forward.
            data = data[1:]

            length, consumed = decode_integer(data, 7)
            name = data[consumed:consumed + length]

            if data[0] & 0x80:
                name = self.huffman_coder.decode(name)
            total_consumed = consumed + length + 1  # Since we moved forward 1.

        data = data[consumed + length:]

        # The header value is definitely length-based.
        length, consumed = decode_integer(data, 7)
        value = data[consumed:consumed + length]

        if data[0] & 0x80:
            value = self.huffman_coder.decode(value)

        # Updated the total consumed length.
        total_consumed += length + consumed

        # If we've been asked to index this, add it to the header table and
        # the reference set.
        if should_index:
            self._add_to_header_table(name, value)
            self.reference_set.add((name, value))

        header = (name, value)

        return header, total_consumed
