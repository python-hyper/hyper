.. _user:

Quickstart Guide
================

First, congratulations on picking ``hyper`` for your HTTP needs. ``hyper``
is the premier (and, as far as we're aware, the only) Python HTTP/2 library,
as well as a very servicable HTTP/1.1 library.

In this section, we'll walk you through using ``hyper``.

Installing hyper
----------------

To begin, you will need to install ``hyper``. This can be done like so:

.. code-block:: bash

    $ pip install hyper

If ``pip`` is not available to you, you can try:

.. code-block:: bash

    $ easy_install hyper

If that fails, download the library from its GitHub page and install it using:

.. code-block:: bash

    $ python setup.py install

Installation Requirements
~~~~~~~~~~~~~~~~~~~~~~~~~

The HTTP/2 specification requires very modern TLS support from any compliant
implementation. When using Python 3.4 and later this is automatically provided
by the standard library. For earlier releases of Python, we use PyOpenSSL to
provide the TLS support we need.

Unfortunately, this is not always totally trivial. You will need to build
PyOpenSSL against a version of OpenSSL that is at least 1.0.1, and to do that
you'll actually need to obtain that version of OpenSSL.

To install against the relevant version of OpenSSL for your system, follow the
instructions from the `cryptography`_ project, replacing references to
``cryptography`` with ``hyper``.

.. _cryptography: https://cryptography.io/en/latest/installation/#installation

Making Your First HTTP/2 Request
--------------------------------

With ``hyper`` installed, you can start making HTTP/2 requests. At this
stage, ``hyper`` can only be used with services that *definitely* support
HTTP/2. Before you begin, ensure that whichever service you're contacting
definitely supports HTTP/2. For the rest of these examples, we'll use
http2bin.org, a HTTP/1.1 and HTTP/2 testing service.

Begin by getting the homepage::

    >>> from hyper import HTTP20Connection
    >>> c = HTTP20Connection('http2bin.org')
    >>> c.request('GET', '/')
    1
    >>> resp = c.get_response()

Used in this way, ``hyper`` behaves exactly like ``http.client``. You can make
sequential requests using the exact same API you're accustomed to. The only
difference is that
:meth:`HTTP20Connection.request() <hyper.HTTP20Connection.request>` returns a
value, unlike the equivalent ``http.client`` function. The return value is the
HTTP/2 *stream identifier*. If you're planning to use ``hyper`` in this very
simple way, you can choose to ignore it, but it's potentially useful. We'll
come back to it.

Once you've got the data, things diverge a little bit::

    >>> resp.headers['content-type']
    [b'text/html; charset=utf-8']
    >>> resp.headers
    HTTPHeaderMap([(b'server', b'h2o/1.0.2-alpha1')...
    >>> resp.status
    200

If http2bin had compressed the response body. ``hyper`` would automatically
decompress that body for you, no input required. This means you can always get
the body by simply reading it::

    >>> body = resp.read()
    b'<!DOCTYPE html>\n<!--[if IE 8]><html clas ....

That's all it takes.

Streams
-------

In HTTP/2, connections are divided into multiple streams. Each stream carries
a single request-response pair. You may start multiple requests before reading
the response from any of them, and switch between them using their stream IDs.

For example::

    >>> from hyper import HTTP20Connection
    >>> c = HTTP20Connection('http2bin.org')
    >>> first = c.request('GET', '/get')
    >>> second = c.request('POST', '/post', data='key=value')
    >>> third = c.request('GET', '/ip')
    >>> second_response = c.getresponse(second)
    >>> first_response = c.getresponse(first)
    >>> third_response = c.getresponse(third)

``hyper`` will ensure that each response is matched to the correct request.

Making Your First HTTP/1.1 Request
-----------------------------------

With ``hyper`` installed, you can start making HTTP/2 requests. At this
stage, ``hyper`` can only be used with services that *definitely* support
HTTP/2. Before you begin, ensure that whichever service you're contacting
definitely supports HTTP/2. For the rest of these examples, we'll use
Twitter.

You can also use ``hyper`` to make HTTP/1.1 requests. The code is very similar.
For example, to get the Twitter homepage::

    >>> from hyper import HTTP11Connection
    >>> c = HTTP11Connection('twitter.com:443')
    >>> c.request('GET', '/')
    >>> resp = c.get_response()

The key difference between HTTP/1.1 and HTTP/2 is that when you make HTTP/1.1
requests you do not get a stream ID. This is, of course, because HTTP/1.1 does
not have streams.

Things behave exactly like they do in the HTTP/2 case, right down to the data
reading::

    >>> resp.headers['content-encoding']
    [b'deflate']
    >>> resp.headers
    HTTPHeaderMap([(b'x-xss-protection', b'1; mode=block')...
    >>> resp.status
    200
    >>> body = resp.read()
    b'<!DOCTYPE html>\n<!--[if IE 8]><html clas ....

That's all it takes.

Requests Integration
--------------------

Do you like `requests`_? Of course you do, everyone does! It's a shame that
requests doesn't support HTTP/2 though. To rectify that oversight, ``hyper``
provides a transport adapter that can be plugged directly into Requests, giving
it instant HTTP/2 support.

All you have to do is identify a host that you'd like to communicate with over
HTTP/2. Once you've worked that out, you can get started straight away::

    >>> import requests
    >>> from hyper.contrib import HTTP20Adapter
    >>> s = requests.Session()
    >>> s.mount('https://http2bin.org', HTTP20Adapter())
    >>> r = s.get('https://http2bin.org/get')
    >>> print(r.status_code)
    200

This transport adapter is subject to all of the limitations that apply to
``hyper``, and provides all of the goodness of requests.

A quick warning: some hosts will redirect to new hostnames, which may redirect
you away from HTTP/2. Make sure you install the adapter for all the hostnames
you're interested in::

    >>> a = HTTP20Adapter()
    >>> s.mount('https://http2bin.org', a)
    >>> s.mount('https://www.http2bin.org', a)

.. _requests: http://python-requests.org/

HTTPie Integration
------------------

`HTTPie`_ is a popular tool for making HTTP requests from the command line, as
an alternative to the ever-popular `cURL`_. Collaboration between the ``hyper``
authors and the HTTPie authors allows HTTPie to support making HTTP/2 requests.

To add this support, follow the instructions in the `GitHub repository`_.

.. _HTTPie: http://httpie.org/
.. _cURL: http://curl.haxx.se/
.. _GitHub repository: https://github.com/jakubroztocil/httpie-http2

hyper CLI
---------

For testing purposes, ``hyper`` provides a command-line tool that can make
HTTP/2 requests directly from the CLI. This is useful for debugging purposes,
and to avoid having to use the Python interactive interpreter to execute basic
queries.

For more information, see the CLI section.
