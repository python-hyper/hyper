# -*- coding: utf-8 -*-
"""
This module defines substantial HPACK integration tests. These can take a very
long time to run, so they're outside the main test suite, but they need to be
run before every change to HPACK.
"""
from hyper.http20.hpack import Decoder
from binascii import unhexlify

class TestHPACKDecoderIntegration(object):
    def test_can_decode_a_story(self, story):
        d = Decoder()
        for case in story['cases']:
            d.header_table_size = case['header_table_size']
            decoded_headers = d.decode(unhexlify(case['wire']))

            # The correct headers are a list of dicts, which is annoying.
            correct_headers = {item[0]: item[1] for header in case['headers'] for item in header.items()}
            assert correct_headers == decoded_headers

