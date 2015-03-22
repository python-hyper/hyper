# -*- coding: utf-8 -*-
"""
hyper/http11/parser
~~~~~~~~~~~~~~~~~~~

This module contains hyper's pure-Python HTTP/1.1 parser. This module defines
an abstraction layer for HTTP/1.1 parsing that allows for dropping in other
modules if needed, in order to obtain speedups on your chosen platform.
"""
from collections import namedtuple


Request = namedtuple(
    'Request', ['method', 'path', 'minor_version', 'headers', 'consumed']
)
Response = namedtuple(
    'Response', ['status', 'msg', 'minor_version', 'headers', 'consumed']
)


class ParseError(Exception):
    """
    An invalid HTTP message was passed to the parser.
    """
    pass


class Parser(object):
    """
    A single HTTP parser object. This object can parse HTTP requests and
    responses using picohttpparser.
    This object is not thread-safe, and it does maintain state that is shared
    across parsing requests. For this reason, make sure that access to this
    object is synchronized if you use it across multiple threads.
    """
    def __init__(self):
        pass

    def parse_request(self, buffer):
        """
        Parses a single HTTP request from a buffer.
        :param buffer: A ``memoryview`` object wrapping a buffer containing a
            HTTP request.
        :returns: A :class:`Request <hyper.http11.parser.Request>` object, or
            ``None`` if there is not enough data in the buffer.
        """
        pass

    def parse_response(self, buffer):
        """
        Parses a single HTTP response from a buffer.
        :param buffer: A ``memoryview`` object wrapping a buffer containing a
            HTTP response.
        :returns: A :class:`Response <hyper.http11.parser.Response>` object, or
            ``None`` if there is not enough data in the buffer.
        """
        pass
