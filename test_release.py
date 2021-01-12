# -*- coding: utf-8 -*-
"""
test_release.py
~~~~~~~~~~~~~~~

This function contains the release tests for `hyper`. These tests rely on
third-party implementations of HTTP/2 servers, and so are not usually run as
part of our regression tests. They are instead run before releasing `hyper`
as a sanity check to confirm that the library itself appears to function and is
capable of achieving basic tasks.
"""

import logging
import random
from concurrent.futures import as_completed, ThreadPoolExecutor

import requests

from hyper import HTTP20Connection, HTTP11Connection, HTTPConnection
from hyper.common.util import HTTPVersion
from hyper.contrib import HTTP20Adapter

logging.basicConfig(level=logging.INFO)


class TestHyperActuallyWorks(object):
    def test_abusing_nghttp2_org(self):
        """
        This test function loads all of nghttp2.org's pages in parallel. This
        tests us against the most common open source HTTP/2 server
        implementation.
        """
        paths = [
            '/',
            '/blog/2014/04/27/how-dependency-based-prioritization-works/',
            '/blog/2014/04/25/http-slash-2-draft-12-update/',
            '/blog/2014/04/23/nghttp2-dot-org-now-installed-valid-ssl-slash-tls-certificate/',
            '/blog/2014/04/21/h2load-now-supports-spdy-in-clear-text/',
            '/blog/2014/04/18/nghttp2-dot-org-goes-live/',
            '/blog/archives/',
        ]

        c = HTTP20Connection('nghttp2.org', enable_push=True)

        # Make all the requests, then read the responses in a random order.
        stream_ids = [c.request('GET', path) for path in paths]
        random.shuffle(stream_ids)
        responses = [c.get_response(i) for i in stream_ids]

        # Also get anything that was pushed. Add the responses to the list of
        # responses.
        pushes = [p for i in stream_ids for p in c.get_pushes(i)]
        for p in pushes:
            responses.append(p.get_response())

        text_data = b''.join([r.read() for r in responses])

        # Having read all the data from them, confirm that the status codes
        # are good. Also confirm that the pushes make sense.
        assert text_data
        assert all(map(lambda r: r.status == 200, responses))
        assert all(map(lambda p: p.scheme == b'https', pushes))
        assert all(map(lambda p: p.method.lower() == b'get', pushes))

    def test_threaded_abusing_nghttp2_org(self):
        """
        This test function loads all of nghttp2.org's pages in parallel using
        threads. This tests us against the most common open source HTTP/2
        server implementation.

        """
        paths = [
            '/',
            '/blog/2014/04/27/how-dependency-based-prioritization-works/',
            '/blog/2014/04/25/http-slash-2-draft-12-update/',
            '/blog/2014/04/23/nghttp2-dot-org-now-installed-valid-ssl-slash-tls-certificate/',
            '/blog/2014/04/21/h2load-now-supports-spdy-in-clear-text/',
            '/blog/2014/04/18/nghttp2-dot-org-goes-live/',
            '/blog/archives/',
        ]

        c = HTTP20Connection('nghttp2.org', enable_push=True)

        def do_one_page(path):
            stream_id = c.request('GET', path)
            responses = [c.get_response(stream_id)]
            pushes = c.get_pushes(stream_id)
            responses.extend(p.get_response() for p in pushes)
            text_data = b''.join([r.read() for r in responses])
            # Having read all the data from them, confirm that the status codes
            # are good. Also confirm that the pushes make sense.
            assert all(map(lambda r: r.status == 200, responses))
            assert all(map(lambda p: p.scheme == b'https', pushes))
            assert all(map(lambda p: p.scheme == b'https', pushes))
            assert text_data

        max_workers = len(paths)
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [ex.submit(do_one_page, p) for p in paths]
            for f in as_completed(futures):
                f.result()

    def test_hitting_nghttp2_org(self):
        """
        This test function uses the requests adapter and requests to talk to nghttp2.org/httpbin.
        """
        s = requests.Session()
        a = HTTP20Adapter()
        s.mount('https://nghttp2', a)
        s.mount('https://www.nghttp2', a)

        # Here are some nice URLs.
        urls = [
            'https://www.nghttp2.org/httpbin/',
            'https://www.nghttp2.org/httpbin/ip',
            'https://www.nghttp2.org/httpbin/user-agent',
            'https://www.nghttp2.org/httpbin/headers',
            'https://www.nghttp2.org/httpbin/get',
            'https://nghttp2.org/httpbin/',
            'https://nghttp2.org/httpbin/ip',
            'https://nghttp2.org/httpbin/user-agent',
            'https://nghttp2.org/httpbin/headers',
            'https://nghttp2.org/httpbin/get',
        ]

        # Go get everything.
        responses = [s.get(url) for url in urls]

        # Confirm all is well.
        assert all(map(lambda r: r.status_code == 200, responses))
        assert all(map(lambda r: r.text, responses))

    def test_hitting_httpbin_org_http11(self):
        """
        This test function uses hyper's HTTP/1.1 support to talk to httpbin
        """
        c = HTTP11Connection('httpbin.org:443')

        # Here are some nice URLs.
        urls = [
            '/',
            '/ip',
            '/user-agent',
            '/headers',
            '/get',
        ]

        # Go get everything.
        for url in urls:
            c.request('GET', url)
            resp = c.get_response()

            assert resp.status == 200
            assert resp.read()

    def test_hitting_nghttp2_org_via_h2c_upgrade(self):
        """
        This tests our support for cleartext HTTP/1.1 -> HTTP/2 upgrade
        against the most common open source HTTP/2 server implementation.
        """
        c = HTTPConnection('nghttp2.org:80')

        # Make the request.
        c.request('GET', '/')
        response = c.get_response()

        # Check that the response is OK and that we did upgrade to HTTP/2.
        assert response.status == 200
        assert response.read()
        assert response.version == HTTPVersion.http20

    def test_http11_response_body_length(self):
        """
        This test function uses check the expected length of the HTTP/1.1-response-body.
        """
        c = HTTP11Connection('httpbin.org:443')

        # Make some HTTP/1.1 requests.
        methods = ['GET', 'HEAD']
        for method in methods:
            c.request(method, '/')
            resp = c.get_response()

            # Check the expected length of the body.
            if method == 'HEAD':
                assert resp._length == 0
                assert resp.read() == b''
            else:
                try:
                    content_length = int(resp.headers[b'Content-Length'][0])
                except KeyError:
                    continue
                assert resp._length == content_length
                assert resp.read()
