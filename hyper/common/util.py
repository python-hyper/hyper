# -*- coding: utf-8 -*-
"""
hyper/common/util
~~~~~~~~~~~~~~~~~

General utility functions for use with hyper.
"""
from hyper.compat import unicode, bytes, imap
import re

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

def to_host_port_tuple(host_port_str, default_port=80):
    """
    Converts the given string containing a host and possibly a port
    to a tuple.
    """
    if re.search("\]:\d+|\.\d{1-3}:\d+|[a-zA-Z0-9-]+:\d+", host_port_str):
        host, port = host_port_str.rsplit(':', 1)
        port = int(port)
    else:
        host, port = host_port_str, default_port

    host = host.strip('[]')

    return ((host, port))
