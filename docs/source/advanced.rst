.. _advanced:

Advanced Usage
==============

This section of the documentation covers more advanced use-cases for ``hyper``.

Responses as Context Managers
-----------------------------

If you're concerned about having too many TCP sockets open at any one time, you
may want to keep your connections alive only as long as you know you'll need
them. In HTTP/2.0 this is generally not something you should do unless you're
very confident you won't need the connection again anytime soon. However, if
you decide you want to avoid keeping the connection open, you can use the
:class:`HTTP20Connection <hyper.HTTP20Connection>` as a context manager::

    with HTTP20Connection('twitter.com:443') as conn:
        conn.request('GET', '/')
        data = conn.getresponse().read()

    analyse(data)

You may not use any :class:`HTTP20Response <hyper.HTTP20Response>` objects
obtained from a connection after that connection is closed. Interacting with
these objects when a connection has been closed is considered undefined
behaviour.

Multithreading
--------------

Currently, ``hyper``'s :class:`HTTP20Connection <hyper.HTTP20Connection>` class
is **not** thread-safe. Thread-safety is planned for ``hyper``'s core objects,
but in this early alpha it is not a high priority.

To use ``hyper`` in a multithreaded context the recommended thing to do is to
place each connection in its own thread. Each thread should then have a request
queue and a response queue, and the thread should be able to spin over both,
sending requests and returning responses. The stream identifiers provided by
``hyper`` can be used to match the two together.

SSL/TLS Certificate Verification
--------------------------------

By default, all HTTP/2.0 connections are made over TLS, and ``hyper`` uses the
system certificate authorities to verify the offered TLS certificates.
Currently certificate verification cannot be disabled.

Streaming Uploads
-----------------

Just like the ever-popular ``requests`` module, ``hyper`` allows you to perform
a 'streaming' upload by providing a file-like object to the 'data' parameter.
This will cause ``hyper`` to read the data in 1kB at a time and send it to the
remote server. You _must_ set an accurate Content-Length header when you do
this, as ``hyper`` won't set it for you.

Content Decompression
---------------------

In HTTP/2.0 it's mandatory that user-agents support receiving responses that
have their bodies compressed. As demonstrated in the quickstart guide,
``hyper`` transparently implements this decompression, meaning that responses
are automatically decompressed for you. If you don't want this to happen,
you can turn it off by passing the ``decode_content`` parameter to
:meth:`read() <hyper.HTTP20Response.read>`, like this::

    >>> resp.read(decode_content=False)
    b'\xc9...'
