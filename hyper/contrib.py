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
    from requests.utils import (
        get_encoding_from_headers, select_proxy, prepend_scheme_if_needed
    )
    from requests.cookies import extract_cookies_to_jar
except ImportError:  # pragma: no cover
    HTTPAdapter = object

from hyper.common.connection import HTTPConnection
from hyper.compat import urlparse, ssl
from hyper.tls import init_context
from hyper.common.util import to_native_string


class HTTP20Adapter(HTTPAdapter):
    """
    A Requests Transport Adapter that uses hyper to send requests over
    HTTP/2. This implements some degree of connection pooling to maximise the
    HTTP/2 gain.
    """
    def __init__(self, window_manager=None, *args, **kwargs):
        #: A mapping between HTTP netlocs and ``HTTP20Connection`` objects.
        self.connections = {}
        self.window_manager = window_manager

    def get_connection(self, host, port, scheme, cert=None, verify=True,
                       proxy=None, timeout=None):
        """
        Gets an appropriate HTTP/2 connection object based on
        host/port/scheme/cert tuples.
        """
        secure = (scheme == 'https')

        if port is None:  # pragma: no cover
            port = 80 if not secure else 443

        ssl_context = None
        if not verify:
            verify = False
            ssl_context = init_context(cert=cert)
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        elif verify is True and cert is not None:
            ssl_context = init_context(cert=cert)
        elif verify is not True:
            ssl_context = init_context(cert_path=verify, cert=cert)

        if proxy:
            proxy_headers = self.proxy_headers(proxy)
            proxy_netloc = urlparse(proxy).netloc
        else:
            proxy_headers = None
            proxy_netloc = None

        # We put proxy headers in the connection_key, because
        # ``proxy_headers`` method might be overridden, so we can't
        # rely on proxy headers being the same for the same proxies.
        proxy_headers_key = (frozenset(proxy_headers.items())
                             if proxy_headers else None)
        connection_key = (host, port, scheme, cert, verify,
                          proxy_netloc, proxy_headers_key)
        try:
            conn = self.connections[connection_key]
        except KeyError:
            conn = HTTPConnection(
                host,
                port,
                secure=secure,
                window_manager=self.window_manager,
                ssl_context=ssl_context,
                proxy_host=proxy_netloc,
                proxy_headers=proxy_headers,
                timeout=timeout)
            self.connections[connection_key] = conn

        return conn

    def send(self, request, stream=False, cert=None, verify=True, proxies=None,
             timeout=None, **kwargs):
        """
        Sends a HTTP message to the server.
        """
        proxy = select_proxy(request.url, proxies)
        if proxy:
            proxy = prepend_scheme_if_needed(proxy, 'http')

        parsed = urlparse(request.url)
        conn = self.get_connection(
            parsed.hostname,
            parsed.port,
            parsed.scheme,
            cert=cert,
            verify=verify,
            proxy=proxy,
            timeout=timeout)

        # Build the selector.
        selector = parsed.path
        selector += '?' + parsed.query if parsed.query else ''
        selector += '#' + parsed.fragment if parsed.fragment else ''

        conn.request(
            request.method,
            selector,
            request.body,
            request.headers
        )
        resp = conn.get_response()

        r = self.build_response(request, resp)

        if not stream:
            r.content

        return r

    def build_response(self, request, resp):
        """
        Builds a Requests' response object.  This emulates most of the logic of
        the standard function but deals with the lack of the ``.headers``
        property on the HTTP20Response object.

        Additionally, this function builds in a number of features that are
        purely for HTTPie. This is to allow maximum compatibility with what
        urllib3 does, so that HTTPie doesn't fall over when it uses us.
        """
        response = Response()

        response.status_code = resp.status
        response.headers = CaseInsensitiveDict((
            map(to_native_string, h)
            for h in resp.headers.iter_raw()
        ))
        response.raw = resp
        response.reason = resp.reason
        response.encoding = get_encoding_from_headers(response.headers)

        extract_cookies_to_jar(response.cookies, request, response)
        response.url = request.url

        response.request = request
        response.connection = self

        # First horrible patch: Requests expects its raw responses to have a
        # release_conn method, which I don't. We should monkeypatch a no-op on.
        resp.release_conn = lambda: None

        # Next, add the things HTTPie needs. It needs the following things:
        #
        # - The `raw` object has a property called `_original_response` that is
        #   a `httplib` response object.
        # - `raw._original_response` has three simple properties: `version`,
        #   `status`, `reason`.
        # - `raw._original_response.version` has one of three values: `9`,
        #   `10`, `11`.
        # - `raw._original_response.msg` exists.
        # - `raw._original_response.msg._headers` exists and is an iterable of
        #   two-tuples.
        #
        # We fake this out. Most of this exists on our response object already,
        # and the rest can be faked.
        #
        # All of this exists for httpie, which I don't have any tests for,
        # so I'm not going to bother adding test coverage for it.
        class FakeOriginalResponse(object):  # pragma: no cover
            def __init__(self, headers):
                self._headers = headers

            def get_all(self, name, default=None):
                values = []

                for n, v in self._headers:
                    if n == name.lower():
                        values.append(v)

                if not values:
                    return default

                return values

            def getheaders(self, name):
                return self.get_all(name, [])

        response.raw._original_response = orig = FakeOriginalResponse(None)
        orig.version = 20
        orig.status = resp.status
        orig.reason = resp.reason
        orig.msg = FakeOriginalResponse(resp.headers.iter_raw())

        return response

    def close(self):
        for connection in self.connections.values():
            connection.close()
        self.connections.clear()
