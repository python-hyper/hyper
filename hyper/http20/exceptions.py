# -*- coding: utf-8 -*-
"""
hyper/http20/exceptions
~~~~~~~~~~~~~~~~~~~~~~~

This defines exceptions used in the HTTP/2.0 portion of hyper.
"""
class HTTP20Error(Exception):
    """
    The base class for all of ``hyper``'s HTTP/2.0-related exceptions.
    """
    pass


class HPACKDecodingError(HTTP20Error):
    """
    An error has been encountered while performing HPACK decoding.
    """
    pass
