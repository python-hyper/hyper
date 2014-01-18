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

import ssl

# If there's no NPN support, we're going to drop all support for HTTP/2.0.
try:
    support_20 = ssl.HAS_NPN
except AttributeError:
    support_20 = False

# The HTTPConnection object is currently always the underlying one.
HTTPConnection = httplib.HTTPConnection
HTTPSConnection = httplib.HTTPSConnection

# If we have NPN support, define our custom one, otherwise just use the
# default.
if support_20:
    class HTTPSConnection(object):
        """
        An object representing a single HTTPS connection, whether HTTP/1.1 or
        HTTP/2.0.

        More specifically, this object represents an abstraction over the
        distinction. This object encapsulates a connection object for one of
        the specific types of connection, and delegates most of the work to
        that object.
        """
        def __init__(self, *args, **kwargs):
            # Whatever arguments and keyword arguments are passed to this
            # object need to be saved off for when we initialise one of our
            # subsidiary objects.
            self._original_args = args
            self._original_kwargs = kwargs

            # Set up some variables we're going to use later.
            self._sock = None
            self._conn = None

            # Prepare our backlog of method calls.
            self._call_queue = []

        def __getattr__(self, name):
            # Anything that can't be found on this instance is presumably a
            # property of underlying connection object.
            # We need to be a little bit careful here. There are a few methods
            # that can act on a HTTPSConnection before it actually connects to
            # the remote server. We don't want to change the semantics of the,
            # HTTPSConnection so we need to spot these and queue them up. When
            # we actually create the backing Connection, we'll apply them
            # immediately. These methods can't throw exceptions, so we should
            # be fine.
            delay_methods = ["set_tunnel", "set_debuglevel"]

            if self._conn is None and name in delay_methods:
                # Return a little closure that saves off the method call to
                # apply later.
                def capture(obj, *args, **kwargs):
                    self._call_queue.append((name, args, kwargs))
                return capture
            elif self._conn is None:
                # We're being told to do something! We can now connect to the
                # remote server and build the connection object.
                self._delayed_connect()

            # Call through to the underlying object.
            return getattr(self._conn, name)
