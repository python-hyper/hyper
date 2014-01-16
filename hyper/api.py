# -*- coding: utf-8 -*-
"""
hyper/api
~~~~~~~~~

This file defines the publicly-accessible API for hyper. This API also
constitutes the abstraction layer between HTTP/1.1 and HTTP/2.0.
"""
try:
    import http.client as httplib
except ImportError:
    import httplib


class HTTPConnection(object):
    """
    An object representing a single HTTP connection, whether HTTP/1.1 or
    HTTP/2.0.

    More specifically, this object represents an abstraction over the
    distinction. This object encapsulates a connection object for one of the
    specific types of connection, and delegates most of the work to that
    object.
    """
    def __init__(self, *args, **kwargs):
        # Whatever arguments and keyword arguments are passed to this object
        # need to be saved off for when we initialise one of our subsidiary
        # objects.
        self._original_args = args
        self._original_kwargs = kwargs

        # Set up some variables we're going to use later.
        self._sock = None
        self._conn = None
