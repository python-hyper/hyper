from hyper.http20.huffman import HuffmanDecoder, HuffmanEncoder
from hyper.http20.huffman_constants import REQUEST_CODES,REQUEST_CODES_LENGTH,REQUEST_CODES,REQUEST_CODES_LENGTH


class TestHuffman(object):
    def test_request_huffman_decoder(self):
        decoder = HuffmanDecoder(REQUEST_CODES,REQUEST_CODES_LENGTH)
        assert decoder.decode(b'\xdb\x6d\x88\x3e\x68\xd1\xcb\x12\x25\xba\x7f') == b"www.example.com"
        assert decoder.decode(b'\x63\x65\x4a\x13\x98\xff') == b"no-cache"
        assert decoder.decode(b'\x4e\xb0\x8b\x74\x97\x90\xfa\x7f') == b"custom-key"
        assert decoder.decode(b'\x4e\xb0\x8b\x74\x97\x9a\x17\xa8\xff') == b"custom-value"

    def test_request_huffman_encode(self):
        encoder = HuffmanEncoder(REQUEST_CODES, REQUEST_CODES_LENGTH)
        assert encoder.encode(b"www.example.com") == (b'\xdb\x6d\x88\x3e\x68\xd1\xcb\x12\x25\xba\x7f')
        assert encoder.encode(b"no-cache") == (b'\x63\x65\x4a\x13\x98\xff')
        assert encoder.encode(b"custom-key") == (b'\x4e\xb0\x8b\x74\x97\x90\xfa\x7f')
        assert encoder.encode(b"custom-value") == (b'\x4e\xb0\x8b\x74\x97\x9a\x17\xa8\xff')

    def test_eos_terminates_decode_request(self):
        decoder = HuffmanDecoder(REQUEST_CODES,REQUEST_CODES_LENGTH)
        assert decoder.decode(b'\xff\xff\xf7\x00') == b''
