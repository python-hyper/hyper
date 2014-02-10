# -*- coding: utf-8 -*-
"""
This module defines substantial HPACK integration tests. These can take a very
long time to run, so they're outside the main test suite, but they need to be
run before every change to HPACK.
"""
from hyper.http20.hpack import Decoder, Encoder
from hyper.http20.huffman import HuffmanDecoder, HuffmanEncoder
from hyper.http20.huffman_constants import (
    REQUEST_CODES, REQUEST_CODES_LENGTH, RESPONSE_CODES, RESPONSE_CODES_LENGTH
)
from binascii import unhexlify

class TestHPACKDecoderIntegration(object):
    def test_can_decode_a_story(self, story):
        d = Decoder()

        # We support draft 5 of the HPACK spec.
        assert story['draft'] == 5

        if story['context'] == 'request':
            d.huffman_coder = HuffmanDecoder(REQUEST_CODES, REQUEST_CODES_LENGTH)

        for case in story['cases']:
            d.header_table_size = case['header_table_size']
            decoded_headers = d.decode(unhexlify(case['wire']))

            # The correct headers are a list of dicts, which is annoying.
            correct_headers = {(item[0], item[1]) for header in case['headers'] for item in header.items()}
            assert correct_headers == decoded_headers

    def test_can_encode_a_story_no_huffman(self, raw_story):
        d = Decoder()
        e = Encoder()

        if raw_story['context'] == 'request':
            d.huffman_coder = HuffmanDecoder(REQUEST_CODES, REQUEST_CODES_LENGTH)
        else:
            e.huffman_coder = HuffmanEncoder(RESPONSE_CODES, RESPONSE_CODES_LENGTH)

        for case in raw_story['cases']:
            # The input headers are a list of dicts, which is annoying.
            input_headers = {(item[0], item[1]) for header in case['headers'] for item in header.items()}

            encoded = e.encode(input_headers, huffman=False)
            decoded_headers = d.decode(encoded)

            assert input_headers == decoded_headers

    def test_can_encode_a_story_with_huffman(self, raw_story):
        d = Decoder()
        e = Encoder()

        if raw_story['context'] == 'request':
            d.huffman_coder = HuffmanDecoder(REQUEST_CODES, REQUEST_CODES_LENGTH)
        else:
            e.huffman_coder = HuffmanEncoder(RESPONSE_CODES, RESPONSE_CODES_LENGTH)

        for case in raw_story['cases']:
            # The input headers are a list of dicts, which is annoying.
            input_headers = {(item[0], item[1]) for header in case['headers'] for item in header.items()}

            encoded = e.encode(input_headers, huffman=True)
            decoded_headers = d.decode(encoded)

            assert input_headers == decoded_headers
