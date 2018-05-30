==========
Philosophy
==========

Let's dig into why meta-programming function signatures is a good idea, and then we'll cover some principals.


.. _philosophy_why:

**The why**: intuitive design
=============================

Python lacks tooling to dynamically create callable signatures (without resorting to :func:`exec`).
While this sounds esoteric, it's actually a big source of error and frustration for authors and users.
Have you ever encountered a function that looks like this: ``execute(*args, **kwargs)``?

How about a real world example: the stdlib :mod:`logging` module.
Inspecting one of the six logging methods (i.e. :func:`logging.debug`, :func:`logging.info`, :func:`logging.warning`, :func:`logging.error`, :func:`logging.critical`, and :func:`logging.exception`) we get a meaningless signature:

Inspecting any of the six logging methods we get a very limited understanding of how to use the function:

- :data:`logging.debug(msg, *args, **kwargs)`,
- :data:`logging.info(msg, *args, **kwargs)`,
- :data:`logging.warning(msg, *args, **kwargs)`,
- :data:`logging.error(msg, *args, **kwargs)`,
- :data:`logging.critical(msg, *args, **kwargs)`, and
- :data:`logging.exception(msg, *args, **kwargs)`.

Furthermore, the ``docstring`` messages available via the builtin :func:`help` provide minimally more insight:

.. code-block:: python

    >>> import logging
    >>> help(logging.warning)
    Help on function warning in module logging:

    warning(msg, *args, **kwargs)
        Log a message with severity 'WARNING' on the root logger.
        If the logger has no handlers, call basicConfig() to add a console handler with a pre-defined format.


Of course the basic function of :func:`logging.warning` is to output a string, so it'd be excusable if you guessed that ``*args`` and ``**kwargs`` serve the same function as :func:`str.format`.
Let's try it:

.. code-block:: python

    >>> logging.warning('{user} changed a password', user='dave')
    TypeError: _log() got an unexpected keyword argument 'user'

It's arguable that this signature is *worse* than useless for code consumers - it's led to an incorrect inference of behavior.
If we look at the extended, online documentation for :func:`logging.warning`, we're redirected further to the online documentation for :func:`logging.debug` which clarifies the role of the :term:`var-positional` argument ``*args`` and :term:`var-keyword` argument ``**kwargs`` [#f1]_.

    ``logging.debug(msg, *args, **kwargs)``

    Logs a message with level DEBUG on the root logger.
    The **msg** is the message format string, and the **args** are the arguments which are merged into msg using the string formatting operator.
    (Note that this means that you can use keywords in the format string, together with a single dictionary argument.)

    There are three keyword arguments in kwargs which are inspected: **exc_info** which, if it does not evaluate as false, causes exception information to be added to the logging message.
    If an exception tuple (in the format returned by sys.exc_info()) is provided, it is used; otherwise, sys.exc_info() is called to get the exception information.

    The second optional keyword argument is **stack_info**, which defaults to False.
    If true, stack information is added to the logging message, including the actual logging call.
    Note that this is not the same stack information as that displayed through specifying exc_info: The former is stack frames from the bottom of the stack up to the logging call in the current thread, whereas the latter is information about stack frames which have been unwound, following an exception, while searching for exception handlers.

    You can specify stack_info independently of exc_info, e.g. to just show how you got to a certain point in your code, even when no exceptions were raised.
    The stack frames are printed following a header line which says:

    ...

    The third optional keyword argument is **extra** which can be used to pass a dictionary which is used to populate the __dict__ of the LogRecord created for the logging event with user-defined attributes.
    These custom attributes can then be used as you like.
    For example, they could be incorporated into logged messages. For example:

    ...

That's a bit of documentation, but it uncovers why our attempt at supplying keyword arguments raises a :class:`TypeError`.
The string formatting that the logging methods provide has no relation to the string formatting provided by :meth:`str.format` from `PEP 3101`_ (introduced in Python 2.6 and Python 3.0).

In fact, there is a significant amount of documentation clarifying `formatting style compatibility <https://docs.python.org/3/howto/logging-cookbook.html#use-of-alternative-formatting-styles>`_ with the ``logging`` methods.

We can also discover what parameters are actually accepted by digging through the source code.
As documentation is (often) lacking, this is a fairly standard process.

- :func:`logging.warning: `calls <https://github.com/python/cpython/blob/05f1c8902c78dce66aed067444e2b973221bae2b/Lib/logging/__init__.py#L1920>`_ ``root.warning`` (an instance of :class:`logging.Logger`)
- :meth:`logging.Logger.warning` `calls <https://github.com/python/cpython/blob/05f1c8902c78dce66aed067444e2b973221bae2b/Lib/logging/__init__.py#L1334>`_ :meth:`logging.Logger._log`.
- :meth:`logging.Logger._log` `has our expected call signature <https://github.com/python/cpython/blob/05f1c8902c78dce66aed067444e2b973221bae2b/Lib/logging/__init__.py#L1445>`_:

.. code-block:: python

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False):
        """
        Low-level logging routine which creates a LogRecord and then calls
        all the handlers of this logger to handle the record.
        """
        ...

So there are our parameters!

But, let's have some empathy; the Python core developers certainly don't want to repeat themselves six times – once for each ``logging`` level – right?

This example illuminates the problem that ``forge`` sets out to solve: writing, testing and maintaining signatures requires too much effort.
Left to their own devices, authors instead resort to hacks like signing a function with a :term:`var-keyword` parameter (e.g. ``**kwargs``).
But is there method madness? Code consumers (collaborators and users) are left in the dark, asking "what parameters are *really* accepted; what should I pass?".


.. _philosophy_how:

**The how**: magic-free manipulation
====================================

Modern Python (3.5+) advertises a ``callable`` signature by looking for:

#. a :attr:`__signature__` attribute on your callable
#. devising a signature from the :attr:`__code__` attribute of the callable

And it allows for `type-hints`_ on parameters and return-values by looking for:

#. an :attr:`__annotations__` attribute on the callable with a ``return`` key
#. devising a signature from the :attr:`__code__` attribute of the callable

When you call a function wrapped with ``forge``, the following occurs:

#. **arguments** are associated with the public-facing parameters
#. pre-**bound** parameters are added to the arguments mapping
#. **default** values are applied for missing parameters
#. **converters** (as supplied) are applied to the default or provided values
#. **validators** (as supplied) are called with the converted values
#. the arguments are mapped onto the wrapped function's signature
#. the wrapped function is called with the mapped attributes


.. _philosophy_what:

**The what**: applying the knowledge
====================================

Looking back on the code for :func:`logging.debug`, let's try and improve upon this implementation by wrapping the standard logging methods with enough information to provide basic direction for end-users.

.. testcode::

    import logging
    import forge

    make_explicit = forge.sign(
        forge.arg('msg'),
        *forge.args,
        forge.kwarg('exc_info', default=None),
        forge.kwarg('extra', default=None),
        forge.kwarg('stack_info', default=False),
    )
    debug = make_explicit(logging.debug)
    info = make_explicit(logging.info)
    warning = make_explicit(logging.warning)
    error = make_explicit(logging.error)
    critical = make_explicit(logging.critical)
    exception = make_explicit(logging.exception)

    assert forge.stringify_callable(debug) == \
        'debug(msg, *args, exc_info=None, extra=None, stack_info=False)'

We've aided our intuition about how to use these functions.

Forge provides a sane middle-ground for *well-intentioned, albeit lazy* package authors and *pragmatic, albeit lazy* package consumers to communicate functionality and intent.


**The bottom-line**: signatures shouldn't be this hard
------------------------------------------------------
After a case-study with :mod:`logging` where we enhanced the code with context, let's consider the modern state of Python signatures beyond the ``stdlib``.

Codebases you the broadly adopted :mod:`sqlalchemy` or :mod:`graphene` could benefit, as could third party corporate APIs which expect you to identify subtleties.

Driving developers from their IDE to your documentation is an dark pattern. Be a good community member – write cleanly and clearly.


.. _philosophy_design-principals:

Design principals
=================

**The API emulates usage.**
    ``forge`` provides an API for making function signatures more literate.
    Therefore, the library is designed in a literate way.
    Users are encouraged to supply :term:`positional-only` and :term:`positional-or-keyword` parameters as positional arguments, the :term:`var-positional` parameter for positional-expansion (e.g. ``*forge.args``), :term:`keyword-only` parameters as keyword arguments, and the :term:`var-keyword` parameter for keyword expansion (e.g. ``**forge.kwargs``).

**Minimal API impact.**
    Your callable, and it's underlying code is 100% unmodified, organic.
    You can even get the original function by accessing the function's :attr:`__wrapped__` attribute.

    Function in, function out: no hybrid instance-callables produced.
    :func:`classmethod``, :func:`staticmethod``, and :func:`property`` are all supported.

**Performance matters.**
    ``forge`` was written from the ground up with an eye on performance, so it does the heavy lifting once, upfront rather than every time it's called.

    All classes use :attr:`__slots__` for speeder attribute access.
    PyPy 6.0.0+ has first class support.

**Immutable and flexible.**
    ``forge`` classes are immutable, but also flexible enough to support dynamic usage.
    You can share an :class:`FParameter` or :class:`FSignature` without fearing for your previously signed classes.

**Type-Hints available.**
    ``forge`` supports the use of `type-hints`_ by providing an API for supplying types on parameters.
    In addition, ``forge`` itself is written with `type-hints`_.

**100% Coverage and Linted**
    ``forge`` maintains 100% code-coverage through unit testing.
    Code is also linted with ``mypy`` and ``pylint`` during automated testing upon every ``git push``.


.. _philosophy_what-forge-is-not:

What ``forge`` is not
=====================

``forge`` isn't an interface to the wild-west that is :func:`exec` or :func:`eval`.

All ``forge`` does is:

1. takes your new signature,
2. wraps your old callable,
3. routes calls between the two

The mapper is built prior to execution (for speed).
It's available for inspection, but immutable (at :attr:`__mapper__``).
The callable remains unmodified and intact (at :attr:``__wrapped__``).


.. _philosophy_common-names:

Common names: ``forge.arg`` and ``forge.kwarg``
===============================================

Based on a quick, informal poll of ``#python``, many developers don't know the formal parameter names. Given a function that looks like:

.. code-block:: python

    def func(a, b=3, *args, c=3, **kwargs):
        pass

- ``a`` is often referred to as an *argument* (an ``arg``), and
- ``c`` is often referred to as a *keyword argument* (a ``kwarg``),
- ``b`` is usually bucketed as either of the above,
- ``*args`` is simply referred to as ``args``, and
- ``**kwargs`` is simply referred to as ``kwargs``.

Officially, that's inaccurate.
- ``a`` and ``b`` are :term:`positional-or-keyword` parameters,
- ``c`` is a :term:`keyword-only` parameter,
- ``args`` is a :term:`var-positional` parameter, and
- ``kwargs`` is a :term:`var-keyword` parameter.

Python developers are often pragmatic developers, so ``forge`` was written in a supportive manner.
Therefore, the following synonyms are defined:

- creation of :term:`positional-only` parameters with :func:`forge.pos`,
- creation of :term:`positional-or-keyword` parameters with :func:`forge.arg` or :func:`forge.pok`, and
- creation of :term:`keyword-only` parameters with :func:`forge.kwarg` or :func:`forge.kwo`.

Use whichever variant you please.

.. _`logging module documentation`: https://docs.python.org/3.6/library/logging.html#logging.debug
.. _`type-hints`: https://docs.python.org/3/library/typing.html
.. _`PEP 3101`: https://www.python.org/dev/peps/pep-3101/

.. rubric:: Footnotes

.. [#f1] `Logging module documentation <https://docs.python.org/3.6/library/logging.html#logging.debug>`_