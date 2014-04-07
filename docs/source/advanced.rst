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
remote server. You *must* set an accurate Content-Length header when you do
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

Flow Control & Window Managers
------------------------------

HTTP/2.0 provides a facility for performing 'flow control', enabling both ends
of a HTTP/2.0 connection to influence the rate at which data is received. When
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

    HTTP20Connection('twitter.com:443', window_manager=StupidFlowControlManager)

Note that we don't plug an instance of the class in, we plug the class itself
in. We do this because the connection object will spawn instances of the class
in order to manage the flow control windows of streams in addition to managing
the window of the connection itself.

Server Push
-----------

HTTP/2.0 provides servers with the ability to "push" additional resources to
clients in response to a request, as if the client had requested the resources
themselves. When minimizing round trips is more critical than maximizing
bandwidth usage, this can be a significant performance improvement.

Pushed resources are available through the
:attr:`HTTP20Response.pushes <hyper.HTTP20Response.pushes>` attribute, which
exposes the headers of the simulated request through its
:meth:`getrequestheaders() <hyper.HTTP20Push.getrequestheaders>` method, and a
response object through :meth:`getresponse() <hyper.HTTP20Push.getresponse>`::

    for push in response.pushes:
        print('{}: {}'.format(push.path, push.getresponse().read()))

It is important to remember that because the server may interleave frames from
different streams as it sees fit, a call to
:meth:`read() <hyper.HTTP20PushedResponse.read>` on an
:class:`HTTP20PushedResponse <hyper.HTTP20PushedResponse>` object may terminate
*after* a simultaneous call to :meth:`read() <hyper.HTTP20Response.read>` on the
original :class:`HTTP20Response <hyper.HTTP20Response>` object would
(although it is safe to call them in any order). Users are advised to read the
body of the original response first, unless they know beforehand that it cannot
be processed at all without the pushed resources.

``hyper`` does not currently provide any way to limit the number of pushed
streams, disable them altogether, or cancel in-progress pushed streams, although
HTTP/2.0 allows all of these actions.

``hyper`` does not currently verify that pushed resources comply with the
Same-Origin Policy, so users must take care that they do not treat pushed
resources as authoritative without performing this check themselves.
