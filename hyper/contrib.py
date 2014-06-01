# -*- coding: utf-8 -*-
"""
hyper/contrib
~~~~~~~~~~~~~

Contains a few utilities for use with other HTTP libraries.
"""
try:
    from requests.adapters import HTTPAdapter
    from requests.models import Response
    from requests.structures import CaseInsensitiveDict
    from requests.utils import get_encoding_from_headers
    from requests.cookies import extract_cookies_to_jar
except ImportError:  # pragma: no cover
    HTTPAdapter = object

from hyper import HTTP20Connection
from hyper.compat import urlparse

class HTTP20Adapter(HTTPAdapter):
    """
    A Requests Transport Adapter that uses hyper to send requests over
    HTTP/2. This implements some degree of connection pooling to maximise the
    HTTP/2 gain.
    """
    def __init__(self, *args, **kwargs):
        #: A mapping between HTTP netlocs and ``HTTP20Connection`` objects.
        self.connections = {}

    def get_connection(self, netloc):
        """
        Gets an appropriate HTTP/2 connection object based on netloc.
        """
        try:
            conn = self.connections[netloc]
        except KeyError:
            conn = HTTP20Connection(netloc)
            self.connections[netloc] = conn

        return conn

    def send(self, request, stream=False, **kwargs):
        """
        Sends a HTTP message to the server.
        """
        parsed = urlparse(request.url)

        conn = self.get_connection(parsed.netloc)

        # Build the selector.
        selector = parsed.path
        selector += '?' + parsed.query if parsed.query else ''
        selector += '#' + parsed.fragment if parsed.fragment else ''

        stream_id = conn.request(
            request.method,
            selector,
            request.body,
            request.headers
        )
        resp = conn.getresponse(stream_id)

        r = self.build_response(request, resp)

        if not stream:
            r.content

        return r

    def build_response(self, request, resp):
        """
        Builds a Requests' response object.  This emulates most of the logic of
        the standard fuction but deals with the lack of the ``.headers``
        property on the HTTP20Response object.
        """
        response = Response()

        response.status_code = resp.status
        response.headers = CaseInsensitiveDict(resp.getheaders())
        response.raw = resp
        response.reason = resp.reason
        response.encoding = get_encoding_from_headers(response.headers)

        extract_cookies_to_jar(response.cookies, request, response)
        response.url = request.url

        response.request = request
        response.connection = self

        # One last horrible patch: Requests expects its raw responses to have a
        # release_conn method, which I don't. We should monkeypatch a no-op on.
        resp.release_conn = lambda: None

        return response
