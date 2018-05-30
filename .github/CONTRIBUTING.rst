How To Contribute
=================

First off, thank you for considering contributing to ``forge``!
It's people like *you* who make it such a great tool for everyone.

This document intends to make contribution more accessible by codifying tribal knowledge and expectations.
Don't be afraid to open half-finished PRs, and ask questions if something is unclear!


Workflow
--------

- No contribution is too small!
  Please submit as many fixes for typos and grammar bloopers as you can!
- Try to limit each pull request to *one* change only.
- *Always* add tests and docs for your code.
  This is a hard rule; patches with missing tests or documentation can't be merged.
- Make sure your changes pass our CI_.
  You won't get any feedback until it's green unless you ask for it.
- Once you've addressed review feedback, make sure to bump the pull request with a short note, so we know you're done.


Code
----

- Obey `PEP 8`_ and `PEP 257`_.
  We use the ``"""``\ -on-separate-lines style for docstrings:

  .. code-block:: python

     def func(x):
         """
         Do something.

         :param str x: A very important parameter.

         :rtype: str
         """
- If you add or change public APIs, tag the docstring using ``..  versionadded:: 16.0.0 WHAT`` or ``..  versionchanged:: 16.2.0 WHAT``.
- Prefer double quotes (``"``) over single quotes (``'``) unless the string contains double quotes itself.


Tests
-----

- Write your asserts as ``actual == expected`` to line them up nicely:

  .. code-block:: python

     x = f()

     assert x.some_attribute == 42
     assert x._a_private_attribute == 'foo'

- To run the test suite, all you need is a recent tox_.
  It will ensure the test suite runs with all dependencies against all Python versions just as it will on Travis CI.
- Write `good test docstrings`_.


Documentation
-------------

- Use `semantic newlines`_ in reStructuredText_ files (files ending in ``.rst``):

  .. code-block:: rst

     This is a sentence.
     This is another sentence.

- If you start a new section, add two blank lines before and one blank line after the header, except if two headers follow immediately after each other:

  .. code-block:: rst

     Last line of previous section.


     Header of New Top Section
     =========================

     Header of New Section
     ---------------------

     First line of new section.

- If you add a new feature, demonstrate its awesomeness on the `basic page`_!


Release
-------

The recipe for releasing new software looks like this:

- Add functionality / docstrings as appropriate
- Add tests / docstrings as necessary
- Update ``documentation`` and ``changelog``
- Tag release in ``setup.cfg``
- Merge branch into master
- Add a git tag for the release
- Build a release using ``python setup.py bdist_wheel`` and publish to PYPI as described in `Packaging Python Projects <https://packaging.python.org/tutorials/packaging-projects/>`_


Local Development Environment
-----------------------------

You can (and should) run our test suite using tox_.
However, you’ll probably want a more traditional environment as well.
We highly recommend to develop using the latest Python 3 release because ``forge`` tries to take advantage of modern features whenever possible.

First create a `virtual environment <https://docs.python.org/3/tutorial/venv.html#creating-virtual-environments>`_.

Next, get an up to date checkout of the ``forge`` repository:

.. code-block:: bash

    $ git checkout git@github.com:dfee/forge.git

Change into the newly created directory and **after activating your virtual environment** install an editable version of ``forge`` along with its tests and docs requirements:

.. code-block:: bash

    $ cd forge
    $ pip install -e .[dev]

At this point,

.. code-block:: bash

   $ python -m pytest

should work and pass, as should:

.. code-block:: bash

   $ cd docs
   $ make html

The built documentation can then be found in ``docs/_build/html/``.


Governance
----------

``forge`` is maintained by `Devin Fee`_, who welcomes any and all help.
If you'd like to help, just get a pull request merged and ask to be added in the very same pull request!

****

Thank you for contributing to ``forge``!


.. _`Devin Fee`: https://devinfee.com
.. _`PEP 8`: https://www.python.org/dev/peps/pep-0008/
.. _`PEP 257`: https://www.python.org/dev/peps/pep-0257/
.. _`good test docstrings`: https://jml.io/pages/test-docstrings.html
.. _changelog: https://github.com/dfee/forge/blob/master/CHANGELOG.rst
.. _tox: https://tox.readthedocs.io/
.. _reStructuredText: http://www.sphinx-doc.org/en/stable/rest.html
.. _semantic newlines: http://rhodesmill.org/brandon/2012/one-sentence-per-line/
.. _basic page: https://github.com/dfee/forge/blob/master/docs/basic.rst
.. _CI: https://travis-ci.org/forge/dfee/
