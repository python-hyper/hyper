.. _user:

Quickstart Guide
================

First, congratulations on picking ``hyper`` for your HTTP needs. ``hyper``
is the premier (and, as far as we're aware, the only) Python HTTP/2 library,
as well as a very serviceable HTTP/1.1 library.

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

Making Your First HTTP Request
------------------------------

With ``hyper`` installed, you can start making HTTP/2 requests. For the rest of
these examples, we'll use http2bin.org, a HTTP/1.1 and HTTP/2 testing service.

Begin by getting the homepage::

    >>> from hyper import HTTPConnection
    >>> c = HTTPConnection('http2bin.org')
    >>> c.request('GET', '/')
    1
    >>> resp = c.get_response()

Used in this way, ``hyper`` behaves exactly like ``http.client``. You can make
sequential requests using the exact same API you're accustomed to. The only
difference is that
:meth:`HTTPConnection.request() <hyper.HTTPConnection.request>` may return a
value, unlike the equivalent ``http.client`` function. If present, the return
value is the HTTP/2 *stream identifier*. If you're planning to use ``hyper``
in this very simple way, you can choose to ignore it, but it's potentially
useful. We'll come back to it.

Once you've got the data, things diverge a little bit::

    >>> resp.headers['content-type']
    [b'text/html; charset=utf-8']
    >>> resp.headers
    HTTPHeaderMap([(b'server', b'h2o/1.0.2-alpha1')...
    >>> resp.status
    200

If http2bin had compressed the response body then ``hyper`` would automatically
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

    >>> from hyper import HTTPConnection
    >>> c = HTTPConnection('http2bin.org')
    >>> first = c.request('GET', '/get', headers={'key': 'value'})
    >>> second = c.request('POST', '/post', body=b'hello')
    >>> third = c.request('GET', '/ip')
    >>> second_response = c.get_response(second)
    >>> first_response = c.get_response(first)
    >>> third_response = c.get_response(third)

``hyper`` will ensure that each response is matched to the correct request.

Abstraction
-----------

When you use the :class:`HTTPConnection <hyper.HTTPConnection>` object, you
don't have to know in advance whether your service supports HTTP/2 or not. If
it doesn't, ``hyper`` will transparently fall back to HTTP/1.1.

You can tell the difference: if :meth:`request <hyper.HTTPConnection.request>`
returns a stream ID, then the connection is using HTTP/2: if it returns
``None``, then HTTP/1.1 is being used.

Generally, though, you don't need to care.

Requests Integration
--------------------

Do you like `requests`_? Of course you do, everyone does! It's a shame that
requests doesn't support HTTP/2 though. To rectify that oversight, ``hyper``
provides a transport adapter that can be plugged directly into Requests, giving
it instant HTTP/2 support.

Using ``hyper`` with requests is super simple::

    >>> import requests
    >>> from hyper.contrib import HTTP20Adapter
    >>> s = requests.Session()
    >>> s.mount('https://http2bin.org', HTTP20Adapter())
    >>> r = s.get('https://http2bin.org/get')
    >>> print(r.status_code)
    200

This transport adapter is subject to all of the limitations that apply to
``hyper``, and provides all of the goodness of requests.

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
