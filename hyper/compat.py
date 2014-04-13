# -*- coding: utf-8 -*-
"""
hyper/compat
~~~~~~~~~

Normalizes the Python 2/3 API for internal use.
"""
import sys
import zlib

# Syntax sugar.
_ver = sys.version_info

#: Python 2.x?
is_py2 = (_ver[0] == 2)

#: Python 3.x?
is_py3 = (_ver[0] == 3)

if is_py2:
    from httplib import HTTPConnection as _HTTPConnection
    class HTTPConnection(_HTTPConnection, object): # convert to new-style class
        pass
    from urlparse import urlparse

    def to_byte(char):
        return ord(char)

    def decode_hex(b):
        return b.decode('hex')

    # The standard zlib.compressobj() accepts only positional arguments.
    def zlib_compressobj(level=6, method=zlib.DEFLATED, wbits=15, memlevel=8,
                         strategy=zlib.Z_DEFAULT_STRATEGY):
        return zlib.compressobj(level, method, wbits, memlevel, strategy)

elif is_py3:
    from http.client import HTTPConnection
    from urllib.parse import urlparse

    def to_byte(char):
        return char

    def decode_hex(b):
        return bytes.fromhex(b)

    zlib_compressobj = zlib.compressobj
