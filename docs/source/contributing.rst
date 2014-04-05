.. _contributing:

Contributor's Guide
===================

If you're reading this you're probably interested in contributing to ``hyper``.
First, I'd like to say: thankyou! Projects like this one live-and-die based on
the support they receive from others, and the fact that you're even
*considering* supporting ``hyper`` is incredibly generous of you.

This document lays out guidelines and advice for contributing to ``hyper``. If
you're thinking of contributing, start by reading this thoroughly and getting a
feel for how contributing to the project works. If you've still got questions
after reading this, you should go ahead and contact `the author`_: he'll be
happy to help.

The guide is split into sections based on the type of contribution you're
thinking of making, with a section that covers general guidelines for all
contributors.

.. _the author: https://lukasa.co.uk/about


All Contributions
-----------------

Be Cordial Or Be On Your Way
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``hyper`` has one very important guideline governing all forms of contribution,
including things like reporting bugs or requesting features. The guideline is
`be cordial or be on your way`_. **All contributions are welcome**, but they
come with an implicit social contract: everyone must be treated with respect.

This can be a difficult area to judge, so the maintainer will enforce the
following policy. If any contributor acts rudely or aggressively towards any
other contributor, **regardless of whether they perceive themselves to be acting
in retaliation for an earlier breach of this guideline**, they will be subject
to the following steps:

1. They must apologise. This apology must be genuine in nature: "I'm sorry you
   were offended" is not sufficient. The judgement of 'genuine' is at the
   discretion of the maintainer.
2. If the apology is not offered, any outstanding and future contributions from
   the violating contributor will be rejected immediately.

Everyone involved in the ``hyper`` project, the maintainer included, is bound
by this policy. Failing to abide by it leads to the offender being kicked off
the project.

.. _be cordial or be on your way: http://kennethreitz.org/be-cordial-or-be-on-your-way/

.. _early-feedback:

Get Early Feedback
~~~~~~~~~~~~~~~~~~

If you are contributing, do not feel the need to sit on your contribution until
it is perfectly polished and complete. It helps everyone involved for you to
seek feedback as early as you possibly can. Submitting an early, unfinished
version of your contribution for feedback in no way prejudices your chances of
getting that contribution accepted, and can save you from putting a lot of work
into a contribution that is not suitable for the project.

Contribution Suitability
~~~~~~~~~~~~~~~~~~~~~~~~

The project maintainer has the last word on whether or not a contribution is
suitable for ``hyper``. All contributions will be considered, but from time to
time contributions will be rejected because they do not suit the project.

If your contribution is rejected, don't despair! So long as you followed these
guidelines, you'll have a much better chance of getting your next contribution
accepted.


Code Contributions
------------------

Steps
~~~~~

When contributing code, you'll want to follow this checklist:

1. Fork the repository on GitHub.
2. Run the tests to confirm they all pass on your system. If they don't, you'll
   need to investigate why they fail. If you're unable to diagnose this
   yourself, raise it as a bug report by following the guidelines in this
   document: :ref:`bug-reports`.
3. Write tests that demonstrate your bug or feature. Ensure that they fail.
4. Make your change.
5. Run the entire test suite again, confirming that all tests pass *including
   the ones you just added*.
6. Send a GitHub Pull Request to the main repository's ``development`` branch.
   GitHub Pull Requests are the expected method of code collaboration on this
   project. If you object to the GitHub workflow, you may mail a patch to the
   maintainer.

The following sub-sections go into more detail on some of the points above.

Tests & Code Coverage
~~~~~~~~~~~~~~~~~~~~~

``hyper`` has a substantial suite of tests, both unit tests and integration
tests, and has 100% code coverage. Whenever you contribute, you must write tests
that exercise your contributed code, and you must not regress the code coverage.

To run the tests, you need to install `tox`_. Once you have, you can run the
tests against all supported platforms by simply executing ``tox``.

If you're having trouble running the tests, please consider raising a bug report
using the guidelines in the :ref:`bug-reports` section.

If you've done this but want to get contributing right away, you can take
advantage of the fact that ``hyper`` uses a continuous integration system. This
will automatically run the tests against any pull request raised against the
main ``hyper`` repository. The continuous integration system treats a regression
in code coverage as a failure of the test suite.

Before a contribution is merged it must have a green run through the CI system.

.. _tox: http://tox.readthedocs.org/en/latest/

Code Review
~~~~~~~~~~~

Contributions will not be merged until they've been code reviewed. You should
implement any code review feedback unless you strongly object to it. In the
event that you object to the code review feedback, you should make your case
clearly and calmly. If, after doing so, the feedback is judged to still apply,
you must either apply the feedback or withdraw your contribution.

New Contributors
~~~~~~~~~~~~~~~~

If you are new or relatively new to Open Source, welcome! ``hyper`` aims to be a
gentle introduction to the world of Open Source. If you're concerned about how
best to contribute, please consider mailing the maintainer and asking for help.

Please also check the :ref:`early-feedback` section.

Documentation Contributions
---------------------------

Documentation improvements are always welcome! The documentation files live in
the ``docs/`` directory of the codebase. They're written in `reStructuredText`_,
and use `Sphinx`_ to generate the full suite of documentation.

When contributing documentation, please attempt to follow the style of the
documentation files. This means a soft-limit of 79 characters wide in your text
files and a semi-formal prose style.

.. _reStructuredText: http://docutils.sourceforge.net/rst.html
.. _Sphinx: http://sphinx-doc.org/index.html


.. _bug-reports:

Bug Reports
-----------

Bug reports are hugely important! Before you raise one, though, please check
through the `GitHub issues`_, **both open and closed**, to confirm that the bug
hasn't been reported before. Duplicate bug reports are a huge drain on the time
of other contributors, and should be avoided as much as possible.

.. _GitHub issues: https://github.com/Lukasa/hyper/issues


Feature Requests
----------------

Feature requests are always welcome, but please note that all the general
guidelines for contribution apply. Also note that the importance of a feature
request *without* an associated Pull Request is always lower than the importance
of one *with* an associated Pull Request: code is more valuable than ideas.
