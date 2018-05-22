==================================================
``forge`` *(python) signatures for fun and profit*
==================================================

Release v\ |release| (:doc:`What's new? <changelog>`).

.. include:: ../README.rst
   :start-after: overview-begin
   :end-before: overview-end


Getting Started
===============

TODO: ``forge`` is a Python-only package `hosted on PyPI`_.
The recommended installation method is `pip <https://pip.pypa.io/en/stable/>`_-installing into a `virtualenv <https://docs.python.org/3/library/venv.html>`_:

.. code-block:: console

   $ pip install git+git://github.com/dfee/forge.git#egg=forge


Overview
========

- :doc:`philosophy` walks you through an example of ``forge`` wrapping the ``stdlib``'s :mod:`logging` module.
  Read this to understand the value proposition, philosphy, and design strategy behind ``forge``.
- :doc:`basic` gives a comprehensive tour of ``forge``'s features.
  Read this to learn how to use ``forge`` - from beginner to advanced features.
- :doc:`advanced` shares some common use-cases and approaches for using ``forge``.
  For example, build a function whose signature changes every call.
- :doc:`extending` demonstrates how to alter ``return-type`` annotations and add custom metadata to your parameters.
- :doc:`api` has documentation for all public functionality.
- :doc:`glossary` helps out iron out semantics and terms that are useful when (re-) designing function signatures.


Full Table of Contents
======================

.. toctree::
   :maxdepth: 2

   philosophy
   basic
   advanced
   api
   extending
   glossary
   license
   changelog


Indices and tables
==================

* :ref:`genindex`
* :ref:`search`

.. _`hosted on PyPI`: https://pypi.org/project/<TO-BE-DETERMINED>