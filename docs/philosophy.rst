==========
Philosophy
==========

Let's dig into why meta-programming function signatures is a good idea, and finish with a defense of the design of ``forge``.

.. _philosophy-why_how_what:

Why, what and how
=================

.. _philosophy-why_how_what-why:

**The why**: intuitive design
-----------------------------

Python lacks tooling to dynamically create callable signatures (without resorting to :func:`exec`).
While this sounds esoteric, it's actually a big source of error and frustration for authors and users.
Have you ever encountered a function that looks like this?

.. code-block:: python

    def do_something_complex(*args, **kwargs):
        ...

What arguments does this function recieve?
Is it *really* anything?
Often this is how code-base treasure-hunts begin.

How about a real world example: the stdlib :mod:`logging` module.
Inspecting one of the six logging methods we get a mostly opaque signature:

- :func:`logging.debug(msg, *args, **kwargs) <logging.debug>`,
- :func:`logging.info(msg, *args, **kwargs) <logging.info>`,
- :func:`logging.warning(msg, *args, **kwargs) <logging.warning>`,
- :func:`logging.error(msg, *args, **kwargs) <logging.error>`,
- :func:`logging.critical(msg, *args, **kwargs) <logging.critical>`, and
- :func:`logging.exception(msg, *args, **kwargs) <logging.exception>`.

Furthermore, the ``docstring`` messages available via the builtin :func:`help` provide minimally more insight:

.. code-block:: python

    >>> import logging
    >>> help(logging.warning)
    Help on function warning in module logging:

    warning(msg, *args, **kwargs)
        Log a message with severity 'WARNING' on the root logger.
        If the logger has no handlers, call basicConfig() to add a console handler with a pre-defined format.


Of course the basic function of :func:`logging.warning` is to output a string, so it'd be excusable if you guessed that ``*args`` and ``**kwargs`` serve the same function as :func:`str.format`.
Let's try that:

.. code-block:: python

    >>> logging.warning('{user} changed a password', user='dave')
    TypeError: _log() got an unexpected keyword argument 'user'

Oops – perhaps not.

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
The string formatting that the logging methods provide has no relation to the string formatting provided by :meth:`str.format` from :pep:`3101` (introduced in Python 2.6 and Python 3.0).

In fact, there is a significant amount of documentation clarifying `formatting style compatibility <https://docs.python.org/3/howto/logging-cookbook.html#use-of-alternative-formatting-styles>`_ with the :mod:`logging` methods.

We can also discover what parameters are actually accepted by digging through the source code.
As documentation is (often) lacking, this is a fairly standard process.

- :func:`logging.warning` calls ``root.warning`` (an instance of :class:`logging.Logger`) [#f2]_
- :meth:`logging.Logger.warning` calls :meth:`logging.Logger._log`. [#f3]_
- :meth:`logging.Logger._log` has our expected call signature [#f4]_:

.. code-block:: python

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False):
        """
        Low-level logging routine which creates a LogRecord and then calls
        all the handlers of this logger to handle the record.
        """
        ...

So there are our parameters!

It's understandable that the Python core developers don't want to repeat themselves six times – once for each ``logging`` level.
However, these opaque signatures aren't user-friendly.

This example illuminates the problem that ``forge`` sets out to solve: writing, testing and maintaining signatures requires too much effort.
Left to their own devices, authors instead resort to hacks like signing a function with a :term:`var-keyword` parameter (e.g. ``**kwargs``).
But is there method madness? Code consumers (collaborators and users) are left in the dark, asking "what parameters are *really* accepted; what should I pass?".


.. _philosophy-why_how_what-how:

**The how**: magic-free manipulation
------------------------------------

Modern Python (3.5+) advertises a ``callable`` signature by looking for:

#. a :attr:`__signature__` attribute on your callable
#. devising a signature from the :attr:`__code__` attribute of the callable

And it allows for `type-hints`_ on parameters and return-values by looking for:

#. an :attr:`__annotations__` attribute on the callable with a ``return`` key
#. devising a signature from the :attr:`__code__` attribute of the callable

When you call a function signed with ``forge``, the following occurs:

#. parameters are associated with the supplied **arguments** (as usual)
#. :paramref:`pre-bound <forge.FParameter.bound>` parameters are added to the mapping of arguments
#. **default** values are provided for missing parameters
#. **converters** (as available) are applied to the default or provided values
#. **validators** (as available) are called with the converted values
#. the arguments are mapped and passed to the underlying :term:`callable`


.. _philosophy-why_how_what-what:

**The what**: applying the knowledge
------------------------------------

Looking back on the code for :func:`logging.debug`, let's try and improve upon this implementation by generating functions with robust signatures to replace the standard logging methods.

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

    assert forge.repr_callable(debug) == \
        'debug(msg, *args, exc_info=None, extra=None, stack_info=False)'

Hopefully this is much clearer for the end-user.

``Forge`` provides a sane middle-ground for *well-intentioned, albeit lazy* package authors and *pragmatic, albeit lazy* package consumers to communicate functionality and intent.


.. _philosophy-why_how_what-bottom_line:

**The bottom-line**: signatures shouldn't be this hard
------------------------------------------------------
After a case-study with enhancing the signatures of the :mod:`logging` module, let's consider the modern state of Python signatures beyond the ``stdlib``.

Third-party codebases that the broadly adopted (e.g. :mod:`sqlalchemy` and :mod:`graphene`) could benefit, as could third party corporate APIs which expect you to identify subtleties.

Driving developers from their IDE to your documentation - and then to your codebase - to figure out what parameters are actually accepted is an dark pattern.
Be a good community member – write cleanly and clearly.


.. _philosophy-design_defense:

Design defense
==============

.. _philosophy-design_defense-design_principals:

Principals
----------

**The API emulates usage.**
    ``forge`` provides an API for making function signatures more literate - they say what the mean, and they mean what they say.
    Therefore, the library, too, is designed in a literate way.

    Users are encouraged to supply :term:`positional-only` and :term:`positional-or-keyword` parameters as positional arguments, the :term:`var-positional` parameter as an expanded sequence (e.g. :func:`*forge.args <forge.args>`), :term:`keyword-only` parameters as keyword arguments, and the :term:`var-keyword` parameter as an expanded dictionary (e.g. :func:`**forge.kwargs <forge.kwargs>`).

**Minimal API impact.**
    Your callable, and it's underlying code is unmodified (except when using :class:`forge.returns` without another signature revision).
    You can even get the original function by accessing the function's :attr:`__wrapped__` attribute.

    Callable in, function out: no hybrid instance-callables produced.
    :func:`classmethod`, :func:`staticmethod`, and :func:`property` are all supported, as well as ``coroutine`` functions.

**Performance matters.**
    ``forge`` was written from the ground up with an eye on performance, so it does the heavy lifting once, upfront, rather than every time it's called.

    :class:`~forge.FSignature`, :class:`~forge.FParameter` and :class:`~forge.Mapper` use :attr:`__slots__` for faster attribute access.

    PyPy 6.0.0+ has first class support.

**Immutable and flexible.**
    The core ``forge`` classes are immutable, but also flexible enough to support dynamic usage.
    You can share an :class:`FParameter` or :class:`FSignature` without fearing strange side-effects might occur.

**Type-hints available.**
    ``forge`` supports the use of `type-hints`_ by providing an API for supplying types on parameters.
    In addition, ``forge`` itself is written with `type-hints`_.

**100% covered and linted.**
    ``forge`` maintains 100% code-coverage through unit testing.
    Code is also linted with ``mypy`` and ``pylint`` during automated testing upon every ``git push``.


.. _philosophy-design_defense-revision_naming:

Revision naming
---------------

Revisions (the unit of work in ``forge``) are subclasses of :class:`~forge.Revision`, and their names are lower case.
This is stylistic choice, as revision instances are callables, typically used as decorators.


.. _philosophy-design_defense-parameter_names:

Parameter names
---------------

Many Python developers don't refer to parameters by their formal names.
Given a function that looks like this:

.. code-block:: python

    def func(a, b=3, *args, c=3, **kwargs):
        pass

- ``a`` is conventionally referred to as an *argument*
- ``c`` is conventionally referred to as a *keyword argument*
- ``b`` is conventionally bucketed as either of the above,
- ``*args`` has implicit meaning and is simply referred to as ``args``, and
- ``**kwargs`` has implicit meaning and is simply referred to as ``kwargs``.

While conversationally  acceptable, its inaccurate.
- ``a`` and ``b`` are :term:`positional-or-keyword` parameters,
- ``c`` is a :term:`keyword-only` parameter,
- ``args`` is a :term:`var-positional` parameter, and
- ``kwargs`` is a :term:`var-keyword` parameter.

We Python developers are a pragrmatic people, so ``forge`` is written in a supportive manner; the following synonyms are defined:

- creation of :term:`positional-or-keyword` parameters with :func:`forge.arg` or :func:`forge.pok`, and
- creation of :term:`keyword-only` parameters with :func:`forge.kwarg` or :func:`forge.kwo`.

Use whichever variant you please.

In addition, the :class:`forge.args` and :class:`forge.kwargs` expand to produce a sequence of one parameter (the :term:`var-positional` parameter) and a one-item mapping (the value being the :term:`var-keyword` parameter), respectively.
This allows for a function signature, created with :class:`forge.sign` to resemble a native function signature:

.. testcode::

    import forge

    @forge.sign(
        forge.arg('a'),
        *forge.args,
        b=forge.kwarg(),
        **forge.kwargs,
    )
    def func(*args, **kwargs):
        pass

    assert forge.repr_callable(func) == 'func(a, *args, b, **kwargs)'


.. _philosophy-design_defense-what_forge_is_not:

What ``forge`` is not
---------------------

``forge`` isn't an interface to the wild-west that is :func:`exec` or :func:`eval`.

All ``forge`` does is:

1. collects a set of revisions
2. provides an interface wrapper to a supplied callable
3. routes calls and returns values

The :class:`~forge.Mapper` is available for inspection (but immutable) at :attr:`__mapper__`.
The supplied callable remains unmodified and intact at :attr:`__wrapped__`.


.. _`logging module documentation`: https://docs.python.org/3.6/library/logging.html#logging.debug
.. _`type-hints`: https://docs.python.org/3/library/typing.html

.. rubric:: Footnotes

.. [#f1] `logging.debug <https://docs.python.org/3.6/library/logging.html#logging.debug>`_
.. [#f2] `logging.warning <https://github.com/python/cpython/blob/05f1c8902c78dce66aed067444e2b973221bae2b/Lib/logging/__init__.py#L1920>`_
.. [#f3] `logging.Logger.warning <https://github.com/python/cpython/blob/05f1c8902c78dce66aed067444e2b973221bae2b/Lib/logging/__init__.py#L1334>`_
.. [#f4] `logging.Logger._log <https://github.com/python/cpython/blob/05f1c8902c78dce66aed067444e2b973221bae2b/Lib/logging/__init__.py#L1445>`_
