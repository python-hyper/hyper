# -*- coding: utf-8 -*-
"""
hyper/http20/response
~~~~~~~~~~~~~~~~~~~~~

Contains the HTTP/2.0 equivalent of the HTTPResponse object defined in
httplib/http.client.
"""
class HTTP20Response(object):
    """
    An ``HTTP20Response`` wraps the HTTP/2.0 response from the server. It
    provides access to the response headers and the entity body. The response
    is an iterable object and can be used in a with statement (though due to
    the persistent connections used in HTTP/2.0 this has no effect, and is done
    soley for compatibility).
    """
    def __init__(self):
        #: The reason phrase returned by the server. This is not used in
        #: HTTP/2.0, and so is always the empty string.
        self.reason = ''

    def read(self, amt=None):
        """
        Reads the response body, or up to the next ``amt`` bytes.
        """
        pass

    def getheader(self, name, default=None):
        """
        Return the value of the header ``name``, or ``default`` if there is no
        header matching ``name``. If there is more than one header with the
        value ``name``, return all of the values joined by ', '. If ``default``
        is any iterable other than a single string, its elements are similarly
        returned joined by commas.
        """
        pass

    def getheaders(self):
        """
        Return a list of (header, value) tuples.
        """
        pass

    def fileno(self):
        """
        Return the ``fileno`` of the underlying socket.
        """
        pass

    @property
    def status(self):
        """
        Status code returned by the server.
        """
        pass
