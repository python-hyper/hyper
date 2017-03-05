.. _advanced:

Advanced Usage
==============

This section of the documentation covers more advanced use-cases for ``hyper``.

Responses as Context Managers
-----------------------------

If you're concerned about having too many TCP sockets open at any one time, you
may want to keep your connections alive only as long as you know you'll need
them. In HTTP/2 this is generally not something you should do unless you're
very confident you won't need the connection again anytime soon. However, if
you decide you want to avoid keeping the connection open, you can use the
:class:`HTTPConnection <hyper.HTTPConnection>` as a context manager::

    with HTTPConnection('http2bin.org') as conn:
        conn.request('GET', '/get')
        data = conn.get_response().read()

    analyse(data)

You may not use any :class:`HTTP20Response <hyper.HTTP20Response>` or
:class:`HTTP11Response <hyper.HTTP11Response>` objects obtained from a
connection after that connection is closed. Interacting with these objects when
a connection has been closed is considered undefined behaviour.

Chunked Responses
-----------------

Plenty of APIs return chunked data, and it's often useful to iterate directly
over the chunked data. ``hyper`` lets you iterate over each data frame of a
HTTP/2 response, and each chunk of a HTTP/1.1 response delivered with
``Transfer-Encoding: chunked``::

    for chunk in response.read_chunked():
        do_something_with_chunk(chunk)

There are some important caveats with this iteration: mostly, it's not
guaranteed that each chunk will be non-empty. In HTTP/2, it's entirely legal to
send zero-length data frames, and this API will pass those through unchanged.
Additionally, by default this method will decompress a response that has a
compressed ``Content-Encoding``: if you do that, each element of the iterator
will no longer be a single chunk, but will instead be whatever the decompressor
returns for that chunk.

If that's problematic, you can set the ``decode_content`` parameter to
``False`` and, if necessary, handle the decompression yourself::

    for compressed_chunk in response.read_chunked(decode_content=False):
        decompress(compressed_chunk)

Very easy!

Multithreading
--------------

Currently, ``hyper``'s :class:`HTTPConnection <hyper.HTTPConnection>` class
is **not** thread-safe. Thread-safety is planned for ``hyper``'s core objects,
but in this early alpha it is not a high priority.

To use ``hyper`` in a multithreaded context the recommended thing to do is to
place each connection in its own thread. Each thread should then have a request
queue and a response queue, and the thread should be able to spin over both,
sending requests and returning responses. The stream identifiers provided by
``hyper`` can be used to match the two together.

SSL/TLS Certificate Verification
--------------------------------

By default, all HTTP/2 connections are made over TLS, and ``hyper`` bundles
certificate authorities that it uses to verify the offered TLS certificates.

You can change how certificates are verified by getting a new SSL context
from :func:`hyper.tls.init_context`, tweaking its options, and passing it
to the :class:`HTTPConnection <hyper.HTTPConnection>`. For example, this will
disable verification altogether::

    import ssl
    context = hyper.tls.init_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    conn = HTTPConnection('http2bin.org:443', ssl_context=context)

Streaming Uploads
-----------------

Just like the ever-popular ``requests`` module, ``hyper`` allows you to perform
a 'streaming' upload by providing a file-like object to the 'data' parameter.
This will cause ``hyper`` to read the data in 1kB at a time and send it to the
remote server. You *must* set an accurate Content-Length header when you do
this, as ``hyper`` won't set it for you.

Content Decompression
---------------------

In HTTP/2 it's mandatory that user-agents support receiving responses that
have their bodies compressed. As demonstrated in the quickstart guide,
``hyper`` transparently implements this decompression, meaning that responses
are automatically decompressed for you. If you don't want this to happen,
you can turn it off by passing the ``decode_content`` parameter to
:meth:`read() <hyper.HTTP20Response.read>`, like this::

    >>> resp.read(decode_content=False)
    b'\xc9...'

Flow Control & Window Managers
------------------------------

HTTP/2 provides a facility for performing 'flow control', enabling both ends
of a HTTP/2 connection to influence the rate at which data is received. When
used correctly flow control can be a powerful tool for maximising the efficiency
of a connection. However, when used poorly, flow control leads to severe
inefficiency and can adversely affect the throughput of the connection.

By default ``hyper`` does its best to manage the flow control window for you,
trying to avoid severe inefficiencies. In general, though, the user has a much
better idea of how to manage the flow control window than ``hyper`` will: you
know your use case better than ``hyper`` possibly can.

For that reason, ``hyper`` provides a facility for using pluggable *window
managers*. A *window manager* is an object that is in control of resizing the
flow control window. This object gets informed about every frame received on the
connection, and can make decisions about when to increase the size of the
receive window. This object can take advantage of knowledge from layers above
``hyper``, in the user's code, as well as knowledge from ``hyper``'s layer.

To implement one of these objects, you will want to subclass the
:class:`BaseFlowControlManager <hyper.http20.window.BaseFlowControlManager>`
class and implement the
:meth:`increase_window_size() <hyper.http20.window.BaseFlowControlManager.increase_window_size>`
method. As a simple example, we can implement a very stupid flow control manager
that always resizes the window in response to incoming data like this::

    class StupidFlowControlManager(BaseFlowControlManager):
        def increase_window_size(self, frame_size):
            return frame_size

The *class* can then be plugged straight into a connection object::

    HTTP20Connection('http2bin.org', window_manager=StupidFlowControlManager)

Note that we don't plug an instance of the class in, we plug the class itself
in. We do this because the connection object will spawn instances of the class
in order to manage the flow control windows of streams in addition to managing
the window of the connection itself.

.. _server-push:

Server Push
-----------

HTTP/2 provides servers with the ability to "push" additional resources to
clients in response to a request, as if the client had requested the resources
themselves. When minimizing the number of round trips is more critical than
maximizing bandwidth usage, this can be a significant performance improvement.

Servers may declare their intention to push a given resource by sending the
headers and other metadata of a request that would return that resource - this
is referred to as a "push promise". They may do this before sending the response
headers for the original request, after, or in the middle of sending the
response body.

In order to receive pushed resources, the
:class:`HTTPConnection <hyper.HTTPConnection>` object must be constructed with
``enable_push=True``.

You may retrieve the push promises that the server has sent *so far* by calling
:meth:`get_pushes() <hyper.HTTP20Connection.get_pushes>`, which returns a
generator that yields :class:`HTTP20Push <hyper.HTTP20Push>` objects. Note that
this method is not idempotent; promises returned in one call will not be
returned in subsequent calls. If ``capture_all=False`` is passed (the default),
the generator will yield all buffered push promises without blocking. However,
if ``capture_all=True`` is passed, the generator will first yield all buffered
push promises, then yield additional ones as they arrive, and terminate when the
original stream closes. Using this parameter is only recommended when it is
known that all pushed streams, or a specific one, are of higher priority than
the original response, or when also processing the original response in a
separate thread (N.B. do not do this; ``hyper`` is not yet thread-safe)::

    conn.request('GET', '/')
    response = conn.get_response()
    for push in conn.get_pushes(): # all pushes promised before response headers
        print(push.path)
    conn.read()
    for push in conn.get_pushes(): # all other pushes
        print(push.path)

To cancel an in-progress pushed stream (for example, if the user already has
the given path in cache), call
:meth:`HTTP20Push.cancel() <hyper.HTTP20Push.cancel>`.

``hyper`` does not currently verify that pushed resources comply with the
Same-Origin Policy, so users must take care that they do not treat pushed
resources as authoritative without performing this check themselves (since
the server push mechanism is only an optimization, and clients are free to
issue requests for any pushed resources manually, there is little downside to
simply ignoring suspicious ones).

Nghttp2
-------

By default ``hyper`` uses its built-in pure-Python HPACK encoder and decoder.
These are reasonably efficient, and suitable for most use cases. However, they
do not produce the best compression ratio possible, and because they're written
in pure-Python they incur a cost in memory usage above what is strictly
necessary.

`nghttp2`_ is a HTTP/2 library written in C that includes a HPACK encoder and
decoder. ``nghttp2``'s encoder produces extremely compressed output, and
because it is written in C it is also fast and memory efficient. For this
reason, performance conscious users may prefer to use ``nghttp2``'s HPACK
implementation instead of ``hyper``'s.

You can do this very easily. If ``nghttp2``'s Python bindings are installed,
``hyper`` will transparently switch to using ``nghttp2``'s HPACK implementation
instead of its own. No configuration is required.

Instructions for installing ``nghttp2`` `are available here`_.

.. _nghttp2: https://nghttp2.org/
.. _are available here: https://nghttp2.org/documentation/package_README.html#requirements
