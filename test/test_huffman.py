from hyper.http20.huffman import HuffmanDecoder, HuffmanEncoder
from hyper.http20.huffman_constants import REQUEST_CODES,REQUEST_CODES_LENGTH,RESPONSE_CODES,RESPONSE_CODES_LENGTH


def test_request_huffman_decoder():
    decoder = HuffmanDecoder(REQUEST_CODES,REQUEST_CODES_LENGTH)
    assert decoder.decode(b'\xdb\x6d\x88\x3e\x68\xd1\xcb\x12\x25\xba\x7f') == b"www.example.com"
    assert decoder.decode(b'\x63\x65\x4a\x13\x98\xff') == b"no-cache"
    assert decoder.decode(b'\x4e\xb0\x8b\x74\x97\x90\xfa\x7f') == b"custom-key"
    assert decoder.decode(b'\x4e\xb0\x8b\x74\x97\x9a\x17\xa8\xff') == b"custom-value"

def test_response_huffman_decoder():
    decoder = HuffmanDecoder(RESPONSE_CODES,RESPONSE_CODES_LENGTH)
    assert decoder.decode(b'\x40\x9f') == b"302"
    assert decoder.decode(b'\xc3\x1b\x39\xbf\x38\x7f') == b"private"
    assert decoder.decode(b'\xa2\xfb\xa2\x03\x20\xf2\xab\x30\x31\x24\x01\x8b\x49\x0d\x32\x09\xe8\x77') == b"Mon, 21 Oct 2013 20:13:21 GMT"
    assert decoder.decode(b'\xe3\x9e\x78\x64\xdd\x7a\xfd\x3d\x3d\x24\x87\x47\xdb\x87\x28\x49\x55\xf6\xff') == b"https://www.example.com"
    assert decoder.decode(b'\xdf\x7d\xfb\x36\xd3\xd9\xe1\xfc\xfc\x3f\xaf\xe7\xab\xfc\xfe\xfc\xbf\xaf\x3e\xdf\x2f\x97\x7f\xd3\x6f\xf7\xfd\x79\xf6\xf9\x77\xfd\x3d\xe1\x6b\xfa\x46\xfe\x10\xd8\x89\x44\x7d\xe1\xce\x18\xe5\x65\xf7\x6c\x2f') == b"foo=ASDJKHQKBZXOQWEOPIUAXQWEOIU; max-age=3600; version=1"

def test_request_huffman_encode():
    encoder = HuffmanEncoder(REQUEST_CODES, REQUEST_CODES_LENGTH)
    assert encoder.encode(b"www.example.com") == (b'\xdb\x6d\x88\x3e\x68\xd1\xcb\x12\x25\xba\x7f')
    assert encoder.encode(b"no-cache") == (b'\x63\x65\x4a\x13\x98\xff')
    assert encoder.encode(b"custom-key") == (b'\x4e\xb0\x8b\x74\x97\x90\xfa\x7f')
    assert encoder.encode(b"custom-value") == (b'\x4e\xb0\x8b\x74\x97\x9a\x17\xa8\xff')

def test_response_huffman_encode():
    encoder = HuffmanEncoder(RESPONSE_CODES, RESPONSE_CODES_LENGTH)
    assert encoder.encode(b"302") == (b'\x40\x9f')
    assert encoder.encode(b"private") == (b'\xc3\x1b\x39\xbf\x38\x7f')
    assert encoder.encode(b"Mon, 21 Oct 2013 20:13:21 GMT") == (b'\xa2\xfb\xa2\x03\x20\xf2\xab\x30\x31\x24\x01\x8b\x49\x0d\x32\x09\xe8\x77')
    assert encoder.encode(b"https://www.example.com") == (b'\xe3\x9e\x78\x64\xdd\x7a\xfd\x3d\x3d\x24\x87\x47\xdb\x87\x28\x49\x55\xf6\xff')
    assert encoder.encode(b"foo=ASDJKHQKBZXOQWEOPIUAXQWEOIU; max-age=3600; version=1") == (b'\xdf\x7d\xfb\x36\xd3\xd9\xe1\xfc\xfc\x3f\xaf\xe7\xab\xfc\xfe\xfc\xbf\xaf\x3e\xdf\x2f\x97\x7f\xd3\x6f\xf7\xfd\x79\xf6\xf9\x77\xfd\x3d\xe1\x6b\xfa\x46\xfe\x10\xd8\x89\x44\x7d\xe1\xce\x18\xe5\x65\xf7\x6c\x2f')

