# -*- coding: utf-8 -*-
"""
hyper/common/util
~~~~~~~~~~~~~~~~~

General utility functions for use with hyper.
"""
from hyper.compat import unicode, bytes, imap

def to_bytestring(element):
    """
    Converts a single string to a bytestring, encoding via UTF-8 if needed.
    """
    if isinstance(element, unicode):
        return element.encode('utf-8')
    elif isinstance(element, bytes):
        return element
    else:
        raise ValueError("Non string type.")


def to_bytestring_tuple(*x):
    """
    Converts the given strings to a bytestring if necessary, returning a
    tuple. Uses ``to_bytestring``.
    """
    return tuple(imap(to_bytestring, x))
