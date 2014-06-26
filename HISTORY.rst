Release History
===============

X.X.X (XXXX-XX-XX)
------------------

*Major Changes*

- Support for HPACK draft 8.
- Support for HTTP/2 draft 13.
- Support for Python 2.7, thanks to the inimitable @alekstorm! (`Issue #33`_)
- Support for PyPy.
- Support for Sever Push, thanks to @alekstorm. (`Issue #40`_)

*Bugfixes*

- `HTTP20Response` objects are context managers. (`Issue #24`_)
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
.. _Issue #39: https://github.com/Lukasa/hyper/issues/39
.. _Issue #40: https://github.com/Lukasa/hyper/issues/40
.. _Issue #41: https://github.com/Lukasa/hyper/issues/41
.. _Issue #46: https://github.com/Lukasa/hyper/issues/46
.. _Issue #48: https://github.com/Lukasa/hyper/issues/48
.. _Issue #50: https://github.com/Lukasa/hyper/issues/50
.. _Issue #52: https://github.com/Lukasa/hyper/issues/52

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
