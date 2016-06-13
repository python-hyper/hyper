Hyper is written and maintained by Cory Benfield and various contributors:

Development Lead
````````````````

- Cory Benfield <cory@lukasa.co.uk>

Contributors
````````````

In no particular order:

- Sriram Ganesan (@elricL)

  - Implemented the Huffman encoding/decoding logic.

- Alek Storm (@alekstorm)

  - Implemented Python 2.7 support.
  - Implemented HTTP/2 draft 10 support.
  - Implemented server push.

- Tetsuya Morimoto (@t2y)

  - Fixed a bug where large or incomplete frames were not handled correctly.
  - Added hyper command-line tool.
  - General code cleanups.

- Jerome De Cuyper (@jdecuyper)

  - Updated documentation and tests.
  - Added support for user-provided SSLContext objects.
  - Improved support for HTTP/2 error codes.
  - Added support for graceful connection closure.

- Fred Thomsen (@fredthomsen)

  - Added support for upgrade of plaintext HTTP/1.1 to plaintext HTTP/2.
  - Added proxy support.
  - Improved IPv6 support.
  - Improved ``Stream`` thread safety.

- Eugene Obukhov (@irvind)

  - General code improvements.

- Tim Emiola (@tbetbetbe)

  - Added thread-safety to hyper's HTTP/2 implementation.

- Jason Gowthorpe (@JasonGowthorpe)

  - Added support for removing the bundled certs file.

- Aviv Cohn (@AvivC)

  - Improved some default arguments.
  - Improved type checking of bodies in HTTP/2 requests.

- Ben Last (@benlast)

  - Improved SSL tests.
  - Fixed bugs in the SSL compatibility layer.

- Dmitry Simonchik (@mylh)

  - Added support for client certs.

- pkrolikowski (@pkrolikowski)

  - Added support for overriding HTTP/2 default headers from the CLI.

- Ian Cordasco (@sigmavirus24)

  - Fixed documentation bugs.
  - Fixed Travis builds.

- Collin Anderson (@collinanderson)

  - Documentation improvements.

- Vasiliy Faronov (@vfaronov)

  - Fixed bugs in HTTP/2 upgrade where the header would be set incorrectly.

- Mark Jenkins (@markjenkins)

  - Allowed the result of version negotiation to be forced.

- Masaori Koshiba (@masaori335)

  - Changed the source of the ``check_hostname`` method.

- Kubilay Kocak (@koobs)

  - Packaging improvements.

- Alex Chan (@alexwlchan)

  - Documentation improvements.

- Huayi Zhang (@irachex)

  - Fixed bugs with Python 2.7 compatibility.
