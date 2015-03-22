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
import requests
from hyper import HTTP20Connection
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
        responses = [c.getresponse(i) for i in stream_ids]

        # Also get anything that was pushed. Add the responses to the list of
        # responses.
        pushes = [p for i in stream_ids for p in c.getpushes(i)]
        for p in pushes:
            responses.append(p.getresponse())

        text_data = b''.join([r.read() for r in responses])

        # Having read all the data from them, confirm that the status codes
        # are good. Also confirm that the pushes make sense.
        assert text_data
        assert all(map(lambda r: r.status == 200, responses))
        assert all(map(lambda p: p.scheme == 'https', pushes))
        assert all(map(lambda p: p.method.lower() == 'get', pushes))

    def test_hitting_http2bin_org(self):
        """
        This test function uses the requests adapter and requests to talk to http2bin.
        """
        s = requests.Session()
        a = HTTP20Adapter()
        s.mount('http://http2bin', a)
        s.mount('http://www.http2bin', a)

        # Here are some nice URLs.
        urls = [
            'http://www.http2bin.org/',
            'http://www.http2bin.org/ip',
            'http://www.http2bin.org/user-agent',
	    'http://www.http2bin.org/headers',
            'http://www.http2bin.org/get',
        ]

        # Go get everything.
        responses = [s.get(url) for url in urls]

        # Confirm all is well.
        assert all(map(lambda r: r.status_code == 200, responses))
        assert all(map(lambda r: r.text, responses))
