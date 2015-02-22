.. _CLI:

Hyper Command Line Interface
============================

For testing purposes, ``hyper`` provides a command-line tool that can make
HTTP/2 requests directly from the CLI. This is useful for debugging purposes,
and to avoid having to use the Python interactive interpreter to execute basic
queries.

The usage is::

    hyper [-h] [--version] [--debug] [METHOD] URL [REQUEST_ITEM [REQUEST_ITEM ...]]

For example:

.. code-block:: bash

    $ hyper GET https://http2bin.org/get
    {'args': {},
     'headers': {'Connection': 'close', 'Host': 'http2bin.org', 'Via': '2.0 nghttpx'},
     'origin': '81.129.184.72',
     'url': 'https://http2bin.org/get'}

This allows making basic queries to confirm that ``hyper`` is functioning
correctly, or to perform very basic interop testing with other services.

Sending Data
------------

The ``hyper`` tool has a limited ability to send certain kinds of data. You can
add extra headers by passing them as colon-separated data:

.. code-block:: bash

    $ hyper GET https://http2bin.org/get User-Agent:hyper/0.2.0 X-Totally-Real-Header:someval
    {'args': {},
     'headers': {'Connection': 'close',
                 'Host': 'http2bin.org',
                 'User-Agent': 'hyper/0.2.0',
                 'Via': '2.0 nghttpx',
                 'X-Totally-Real-Header': 'someval'},
     'origin': '81.129.184.72',
     'url': 'https://http2bin.org/get'}

You can add query-string parameters:

.. code-block:: bash

    $ hyper GET https://http2bin.org/get search==hyper
    {'args': {'search': 'hyper'},
     'headers': {'Connection': 'close', 'Host': 'http2bin.org', 'Via': '2.0 nghttpx'},
     'origin': '81.129.184.72',
     'url': 'https://http2bin.org/get?search=hyper'}

And you can upload JSON objects:

.. code-block:: bash

    $ hyper POST https://http2bin.org/post name=Hyper language=Python description='CLI HTTP client'
    {'args': {},
     'data': '{"name": "Hyper", "description": "CLI HTTP client", "language": '
             '"Python"}',
     'files': {},
     'form': {},
     'headers': {'Connection': 'close',
                 'Content-Length': '73',
                 'Content-Type': 'application/json; charset=utf-8',
                 'Host': 'http2bin.org',
                 'Via': '2.0 nghttpx'},
     'json': {'description': 'CLI HTTP client',
              'language': 'Python',
              'name': 'Hyper'},
     'origin': '81.129.184.72',
     'url': 'https://http2bin.org/post'}

Debugging and Detail
--------------------

For more detail, passing the ``--debug`` flag will enable ``hyper``'s
DEBUG-level logging. This provides a lot of low-level detail about exactly what
``hyper`` is doing, including sent and received frames and HPACK state.

Notes
-----

The ``hyper`` command-line tool is not intended to be a fully functional HTTP
CLI tool: for that, we recommend using `HTTPie`_, which uses ``hyper`` for its
HTTP/2 support.

.. _HTTPie: https://github.com/jakubroztocil/httpie-http2
