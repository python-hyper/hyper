Release History
===============

0.4.0 (2015-06-21)
------------------

*New Features*

- HTTP/1.1 and HTTP/2 abstraction layer. Don't specify what version you want to
  use, just automatically get the best version the server supports!
- Support for upgrading plaintext HTTP/1.1 to plaintext HTTP/2, with thanks to
  @fredthomsen! (`Issue 28`_)
- ``HTTP11Connection`` and ``HTTPConnection`` objects are now both context
  managers.
- Added support for ALPN negotiation when using PyOpenSSL. (`Issue #31`_)
- Added support for user-provided SSLContext objects, with thanks to
  @jdecuyper! (`Issue #8`_)
- Better support for HTTP/2 error codes, with thanks to @jdecuyper!
  (`Issue #119`_)
- More gracefully close connections, with thanks to @jdecuyper! (`Issue #15`_)

*Structural Changes*

- The framing and HPACK layers were stripped out into their own libraries.

*Bugfixes*

- Properly verify hostnames when using PyOpenSSL.

.. _Issue #8: https://github.com/Lukasa/hyper/issues/8
.. _Issue #15: https://github.com/Lukasa/hyper/issues/15
.. _Issue #28: https://github.com/Lukasa/hyper/issues/28
.. _Issue #31: https://github.com/Lukasa/hyper/issues/31
.. _Issue #119: https://github.com/Lukasa/hyper/issues/119

0.3.1 (2015-04-03)
------------------

*Bugfixes*

- Fix blocking ``ImportError``. (`Issue #114`_)

.. _Issue #114: https://github.com/Lukasa/hyper/issues/114

0.3.0 (2015-04-03)
------------------

*New Features*

- HTTP/1.1 support! See the documentation for more. (`Issue #75`_)
- Implementation of a ``HTTPHeaderMap`` data structure that provides dictionary
  style lookups while retaining all the semantic information of HTTP headers.

*Major Changes*

- Various changes in the HTTP/2 APIs:

  - The ``getheader``, ``getheaders``, ``gettrailer``, and ``gettrailers``
    methods on the response object have been removed, replaced instead with
    simple ``.headers`` and ``.trailers`` properties that contain
    ``HTTPHeaderMap`` structures.
  - Headers and trailers are now bytestrings, rather than unicode strings.
  - An ``iter_chunked()`` method was added to repsonse objects that allows
    iterating over data in units of individual data frames.
  - Changed the name of ``getresponse()`` to ``get_response()``, because
    ``getresponse()`` was a terrible name forced upon me by httplib.

.. _Issue #75: https://github.com/Lukasa/hyper/issues/75

0.2.2 (2015-04-03)
------------------

*Bugfixes*

- Hyper now correctly handles 'never indexed' header fields. (`Issue #110`_)

.. _Issue #110: https://github.com/Lukasa/hyper/issues/110

0.2.1 (2015-03-29)
------------------

*New Features*

- There is now a `hyper` command-line client that supports making HTTP/2
  requests directly from the command-line.

*Major Changes*

- Support for the final drafts of HTTP/2 and HPACK. Updated to offer the 'h2'
  ALPN token.

*Minor Changes*

- We not only remove the Connection header but all headers it refers to.

0.2.0 (2015-02-07)
------------------

*Major Changes*

- Python 2.7.9 is now fully supported.

0.1.2 (2015-02-07)
------------------

*Minor Changes*

- We now remove the ``Connection`` header if it's given to us, as that header
  is not valid in HTTP/2.

*Bugfixes*

- Adds workaround for HTTPie to make our responses look more like urllib3
  responses.

0.1.1 (2015-02-06)
------------------

*Minor Changes*

- Support for HTTP/2 draft 15, and 16. No drop of support for draft 14.
- Updated bundled certificate file.

*Bugfixes*

- Fixed ``AttributeError`` being raised when a PING frame was received, thanks
  to @t2y. (`Issue #79`_)
- Fixed bug where large frames could be incorrectly truncated by the buffered
  socket implementation, thanks to @t2y. (`Issue #80`_)

.. _Issue #79: https://github.com/Lukasa/hyper/issues/79
.. _Issue #80: https://github.com/Lukasa/hyper/issues/80

0.1.0 (2014-08-16)
------------------

*Regressions and Known Bugs*

- Support for Python 3.3 has been temporarily dropped due to features missing
  from the Python 3.3 ``ssl`` module. PyOpenSSL has been identified as a
  replacement, but until NPN support is merged it cannot be used. Python 3.3
  support *will* be re-added when a suitable release of PyOpenSSL is shipped.
- Technically this release also includes support for PyPy and Python 2.7. That
  support is also blocked behind a suitable PyOpenSSL release.

For more information on these regressions, please see `Issue #37`_.

*Major Changes*

- Support for HPACK draft 9.
- Support for HTTP/2 draft 14.
- Support for Sever Push, thanks to @alekstorm. (`Issue #40`_)
- Use a buffered socket to avoid unnecessary syscalls. (`Issue #56`_)
- If `nghttp2`_ is present, use its HPACK encoder for improved speed and
  compression efficiency. (`Issue #60`_)
- Add ``HTTP20Response.gettrailer()`` and ``HTTP20Response.gettrailers()``,
  supporting downloading and examining HTTP trailers. (Discussed in part in
  `Issue #71`_.)

*Bugfixes*

- ``HTTP20Response`` objects are context managers. (`Issue #24`_)
- Pluggable window managers are now correctly informed about the document size.
  (`Issue #26`_)
- Header blocks can no longer be corrupted if read in a different order to the
  one in which they were sent. (`Issue #39`_)
- Default window manager is now smarter about sending WINDOWUPDATE frames.
  (`Issue #41`_ and `Issue #52`_)
- Fixed inverted window sizes. (`Issue #27`_)
- Correct reply to PING frames. (`Issue #48`_)
- Made the wheel universal, befitting a pure-Python package. (`Issue #46`_)
- HPACK encoder correctly encodes header sets with duplicate headers.
  (`Issue #50`_)

.. _Issue #24: https://github.com/Lukasa/hyper/issues/24
.. _Issue #26: https://github.com/Lukasa/hyper/issues/26
.. _Issue #27: https://github.com/Lukasa/hyper/issues/27
.. _Issue #33: https://github.com/Lukasa/hyper/issues/33
.. _Issue #37: https://github.com/Lukasa/hyper/issues/37
.. _Issue #39: https://github.com/Lukasa/hyper/issues/39
.. _Issue #40: https://github.com/Lukasa/hyper/issues/40
.. _Issue #41: https://github.com/Lukasa/hyper/issues/41
.. _Issue #46: https://github.com/Lukasa/hyper/issues/46
.. _Issue #48: https://github.com/Lukasa/hyper/issues/48
.. _Issue #50: https://github.com/Lukasa/hyper/issues/50
.. _Issue #52: https://github.com/Lukasa/hyper/issues/52
.. _Issue #56: https://github.com/Lukasa/hyper/issues/56
.. _Issue #60: https://github.com/Lukasa/hyper/issues/60
.. _Issue #71: https://github.com/Lukasa/hyper/issues/71
.. _nghttp2: https://nghttp2.org/

0.0.4 (2014-03-08)
------------------

- Add logic for pluggable objects to manage the flow-control window for both
  connections and streams.
- Raise new ``HPACKDecodingError`` when we're unable to validly map a
  Huffman-encoded string.
- Correctly respect the HPACK EOS character.

0.0.3 (2014-02-26)
------------------

- Use bundled SSL certificates in addition to the OS ones, which have limited
  platform availability. (`Issue #9`_)
- Connection objects reset to their basic state when they're closed, enabling
  them to be reused. Note that they may not be reused if exceptions are thrown
  when they're in use: you must open a new connection in that situation.
- Connection objects are now context managers. (`Issue #13`_)
- The ``HTTP20Adapter`` correctly reuses connections.
- Stop sending WINDOWUPDATE frames with a zero-size window increment.
- Provide basic functionality for gracelessly closing streams.
- Exhausted streams are now disposed of. (`Issue #14`_)

.. _Issue #9: https://github.com/Lukasa/hyper/issues/9
.. _Issue #13: https://github.com/Lukasa/hyper/issues/13
.. _Issue #14: https://github.com/Lukasa/hyper/issues/14

0.0.2 (2014-02-20)
------------------

- Implemented logging. (`Issue #12`_)
- Stopped HTTP/2.0 special headers appearing in the response headers.
  (`Issue #16`_)
- `HTTP20Connection` objects are now context managers. (`Issue #13`_)
- Response bodies are automatically decompressed. (`Issue #20`_)
- Provide a requests transport adapter. (`Issue #19`_)
- Fix the build status indicator. (`Issue #22`_)


.. _Issue #12: https://github.com/Lukasa/hyper/issues/12
.. _Issue #16: https://github.com/Lukasa/hyper/issues/16
.. _Issue #13: https://github.com/Lukasa/hyper/issues/13
.. _Issue #20: https://github.com/Lukasa/hyper/issues/20
.. _Issue #19: https://github.com/Lukasa/hyper/issues/19
.. _Issue #22: https://github.com/Lukasa/hyper/issues/22

0.0.1 (2014-02-11)
------------------

- Initial Release
- Support for HTTP/2.0 draft 09.
- Support for HPACK draft 05.
- Support for HTTP/2.0 flow control.
- Verifies TLS certificates.
- Support for streaming uploads.
- Support for streaming downloads.
