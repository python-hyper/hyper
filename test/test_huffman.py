from hyper.http20.huffman import HuffmanDecoder, HuffmanEncoder
from hyper.http20.huffman_constants import REQUEST_CODES,REQUEST_CODES_LENGTH


class TestHuffman(object):
    def test_request_huffman_decoder(self):
        decoder = HuffmanDecoder(REQUEST_CODES,REQUEST_CODES_LENGTH)
        assert decoder.decode(b'\xe7\xcf\x9b\xeb\xe8\x9b\x6f\xb1\x6f\xa9\xb6\xff') == b"www.example.com"
        assert decoder.decode(b'\xb9\xb9\x94\x95\x56\xbf') == b"no-cache"
        assert decoder.decode(b'\x57\x1c\x5c\xdb\x73\x7b\x2f\xaf') == b"custom-key"
        assert decoder.decode(b'\x57\x1c\x5c\xdb\x73\x72\x4d\x9c\x57') == b"custom-value"

    def test_request_huffman_encode(self):
        encoder = HuffmanEncoder(REQUEST_CODES, REQUEST_CODES_LENGTH)
        assert encoder.encode(b"www.example.com") == (b'\xe7\xcf\x9b\xeb\xe8\x9b\x6f\xb1\x6f\xa9\xb6\xff')
        assert encoder.encode(b"no-cache") == (b'\xb9\xb9\x94\x95\x56\xbf')
        assert encoder.encode(b"custom-key") == (b'\x57\x1c\x5c\xdb\x73\x7b\x2f\xaf')
        assert encoder.encode(b"custom-value") == (b'\x57\x1c\x5c\xdb\x73\x72\x4d\x9c\x57')

    def test_eos_terminates_decode_request(self):
        decoder = HuffmanDecoder(REQUEST_CODES,REQUEST_CODES_LENGTH)
        assert decoder.decode(b'\xff\xff\xff\xfc') == b''
