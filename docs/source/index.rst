.. hyper documentation master file, created by
   sphinx-quickstart on Mon Feb 10 21:05:53 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Hyper: HTTP/2.0 for Python
=================================

Release v\ |version|.

HTTP is changing under our feet. HTTP/1.1, our old friend, is being
supplemented by the brand new HTTP/2.0 standard. HTTP/2.0 provides many
benefits: improved speed, lower bandwidth usage, better connection management,
and more.

``hyper`` provides these benefits to your Python code. How? Like this::

    from hyper import HTTP20Connection

    conn = HTTP20Connection('twitter.com:443')
    conn.request('GET', '/')
    resp = conn.getresponse()

    print(resp.read())

Simple. ``hyper`` is written in 100% pure Python, which means no C extensions.
It is also 100% self-contained: there are no external dependencies beyond the
Python standard library.

``hyper`` supports Python 3.3 and onward.

Caveat Emptor!
--------------

Please be warned: ``hyper`` is in a very early alpha. You *will* encounter bugs
when using it. In addition, there are very many rough edges. With that said,
please try it out in your applications: I need your feedback to fix the bugs
and file down the rough edges.

Get Stuck In
------------

The quickstart documentation will help get you going with ``hyper``.

.. toctree::
   :maxdepth: 2

   quickstart

Advanced Documentation
----------------------

More advanced topics are covered here.

.. toctree::
   :maxdepth: 2

   advanced

Contributing
------------

Want to contribute? Awesome! This guide goes into detail about how to
contribute, and provides guidelines for project contributions.

.. toctree::
   :maxdepth: 2

   contributing

Frequently Asked Questions
--------------------------

Got a question? I might have answered it already! Take a look.

.. toctree::
   :maxdepth: 2

   faq

API Documentation
-----------------

The ``hyper`` API is documented in these pages.

.. toctree::
   :maxdepth: 2

   api
