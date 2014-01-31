from hyper.http20.huffman_decoder import HuffmanDecoder
from hyper.http20.huffman_constants import REQUEST_CODES,REQUEST_CODES_LENGTH,RESPONSE_CODES,RESPONSE_CODES_LENGTHS


def test_request_huffman_decoder():
    decoder = HuffmanDecoder(REQUEST_CODES,REQUEST_CODES_LENGTH)
    assert decoder.decode(r'\xdb\x6d\x883e\x68\xd1\xcb\x12\x25\xba\x7f') == "www.example.com"
    assert decoder.decode(r'\x63\x65\x4a\x13\x98\xff') == "no-cache"
    assert decoder.decode(r'\x4e\xb0\x8b\x74\x97\x90\xfa\x7f') == "custom-key"
    assert decoder.decode(r'\x4e\xb0\x8b\x74\x97\x9a\x17\xa8\xff ') == "custom-value"

def test_response_huffman_decoder():
    decoder = HuffmanDecoder(RESPONSE_CODES,RESPONSE_CODES_LENGTHS)
    assert decoder.decode(r'\x40\x9f') == "302"
    assert decoder.decode(r'\xc3\x1b\x39\xbf\x38\x7f') == "private"
    assert decoder.decode(r'\xa2\xfb\xa2\x03\x20\xf2\xab\x30\x31\x24\x01\x8b\x49\x0d\x32\x09\xe8\x77') == "Mon, 21 Oct 2013 20:13:21 GMT"
    assert decoder.decode(r'\xe3\x9e\x78\x64\xdd\x7a\xfd\x3d\x3d\x24\x87\x47\xdb\x87\x28\x49\x55\xf6\xff') == "https://www.example.com"
    assert decoder.decode(r'\xdf\x7d\xfb\x36\xd3\xd9\xe1\xfc\xfc\x3f\xaf\xe7\xab\xfc\xfe\xfc\xbf\xaf\x3e\xdf\x2f\x97\x7f\xd3\x6f\xf7\xfd\x79\xf6\xf9\x77\xfd\x3d\xe1\x6b\xfa\x46\xfe\x10\xd8\x89\x44\x7d\xe1\xce\x18\xe5\x65\xf7\x6c\x2f') == "foo=ASDJKHQKBZXOQWEOPIUAXQWEOIU; max-age=3600; version=1"
