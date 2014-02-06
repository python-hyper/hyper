==================================
Hyper: HTTP Abstraction for Python
==================================

HTTP is changing under our feet. HTTP/1.1, our old friend, is being
supplemented by the brand new HTTP/2.0 standard. HTTP/2.0 provides many
benefits: improved speed, lower bandwidth usage, better connection management,
and more.

Unfortunately, most web servers do not support HTTP/2.0 at this time. What's
needed is to abstract the difference between HTTP/1.1 and HTTP/2.0, so that
your application can reap the benefits of HTTP/2.0 when possible whilst
maintaining maximum compatibility.

Enter ``hyper``::

    from hyper import HTTPConnection

    conn = HTTPConnection("www.python.org")
    conn.request("GET", "/index.html")

    r1 = conn.getresponse()

Did that code use HTTP/1.1, or HTTP/2.0? You don't have to worry. Whatever
``www.python.org`` supports, ``hyper`` will use.

Compatibility
=============

``hyper`` is intended to be a drop-in replacement for
``httplib``/``http.client``, with an identical API. You can get all of the
HTTP/2.0 goodness by simply replacing your ``import httplib`` or
``import http.client`` line with ``import hyper as httplib`` or ``import hyper
as http.client``. You should then be good to go.

Contributing
============

``hyper`` welcomes contributions from anyone! Unlike many other projects we are
happy to accept cosmetic contributions and small contributions, in addition to
large feature requests and changes.

Before you contribute (either by opening an issue or filing a pull request),
please read the following guidelines:

1. Check for issues, *both open and closed*, before raising a new one. It's
   possible your idea or problem has been discussed before. GitHub has a very
   useful search feature: I recommend using that for a few minutes.
2. Fork the repository on GitHub.
3. Run the tests to confirm that they all pass on your system. If they don't,
   you will need to investigate why they fail. ``hyper`` has a substantial
   suite of tests which should cover most failures.
4. Write tests that demonstrate your bug or feature. Ensure that they all fail.
5. Make your change.
6. Run the entire test suite again, confirming that all tests pass including
   the ones you just added.
7. Send a pull request. GitHub pull requests are the expected method of
   collaborating on this project.

If for whatever reason you strongly object to the GitHub workflow, email the
maintainer with a patch.

License
=======

``hyper`` is made available under the MIT License. For more details, see the
``LICENSE`` file in the repository.

Authors
=======

``hyper`` is maintained by Cory Benfield, with contributions from others. For
more details about the contributors, please see ``CONTRIBUTORS.rst``.
