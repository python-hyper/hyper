from hyper.http20.huffman import HuffmanDecoder, HuffmanEncoder
from hyper.http20.huffman_constants import REQUEST_CODES,REQUEST_CODES_LENGTH


class TestHuffman(object):
    def test_request_huffman_decoder(self):
        decoder = HuffmanDecoder(REQUEST_CODES,REQUEST_CODES_LENGTH)
        assert decoder.decode(b'\xf1\xe3\xc2\xe5\xf2:k\xa0\xab\x90\xf4\xff') == b"www.example.com"
        assert decoder.decode(b'\xa8\xeb\x10d\x9c\xbf') == b"no-cache"
        assert decoder.decode(b'%\xa8I\xe9[\xa9}\x7f') == b"custom-key"
        assert decoder.decode(b'%\xa8I\xe9[\xb8\xe8\xb4\xbf') == b"custom-value"

    def test_request_huffman_encode(self):
        encoder = HuffmanEncoder(REQUEST_CODES, REQUEST_CODES_LENGTH)
        assert encoder.encode(b"www.example.com") == (b'\xf1\xe3\xc2\xe5\xf2:k\xa0\xab\x90\xf4\xff')
        assert encoder.encode(b"no-cache") == (b'\xa8\xeb\x10d\x9c\xbf')
        assert encoder.encode(b"custom-key") == (b'%\xa8I\xe9[\xa9}\x7f')
        assert encoder.encode(b"custom-value") == (b'%\xa8I\xe9[\xb8\xe8\xb4\xbf')

    def test_eos_terminates_decode_request(self):
        decoder = HuffmanDecoder(REQUEST_CODES,REQUEST_CODES_LENGTH)
        assert decoder.decode(b'\xff\xff\xff\xfc') == b''
