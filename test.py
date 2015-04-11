#import logging
#
#logging.basicConfig(level=logging.DEBUG)
from hyper.common.connection import HTTPConnection, HTTP20Connection
print("HTTP/1.1")
c = HTTPConnection('http2bin.org', 80)
print(c.request('GET', '/get'))
r = c.get_response()
print(r.read())

print("HTTP/2")
c = HTTPConnection('http2bin.org', 443)
print(c.request('GET', '/get'))
r = c.get_response()
print(r.read())
