.. _faq:

Frequently Asked Questions
==========================

``hyper`` is a project that's under active development, and is in early alpha.
As a result, there are plenty of rough edges and bugs. This section of the
documentation attempts to address some of your likely questions.

If you find there is no answer to your question in this list, please send me
an email. My email address can be found `on my GitHub profile page`_.

.. _on my GitHub profile page: https://github.com/Lukasa

What version of the HTTP/2 draft specification does ``hyper`` support?
----------------------------------------------------------------------

Currently, ``hyper`` supports version 12 of the HTTP/2 draft specification,
and version 7 of the HPACK draft specification. ``hyper`` will be updated to
keep up with the HTTP/2 draft specifications as they progress.

Does ``hyper`` support HTTP/2 flow control?
-------------------------------------------

It should! If you find it doesn't, that's a bug: please `report it on GitHub`_.

.. _report it on GitHub: https://github.com/Lukasa/hyper/issues

Does ``hyper`` support Server Push?
-----------------------------------

Yes! See :ref:`server-push`.

I hit a bug! What should I do?
------------------------------

Please tell me about it using the GitHub page for the project, here_, by filing
an issue. There will definitely be bugs as ``hyper`` is very new, and reporting
them is the fastest way to get them fixed.

When you report them, please follow the contribution guidelines in the README.
It'll make it a lot easier for me to fix the problem.

.. _here: https://github.com/Lukasa/hyper

Updates
-------

Further questions will be added here over time. Please check back regularly.
