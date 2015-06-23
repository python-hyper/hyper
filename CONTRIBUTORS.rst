Hyper is written and maintained by Cory Benfield and various contributors:

Development Lead
````````````````

- Cory Benfield <cory@lukasa.co.uk>

Contributors
````````````

In chronological order:

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

