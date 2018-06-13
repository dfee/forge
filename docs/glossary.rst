========
Glossary
========

General
=======

.. glossary::

    callable
        A :term:`callable` is a Python object that receives arguments and returns a result.
        Typical examples are **builtin functions** (like :func:`sorted`), **lambda functions**, **traditional functions**, and **class instances** that implement a :meth:`~object.__call__` method.

    parameter
        A :term:`parameter` is the atomic unit of a signature.
        At minimum it has a ``name`` and a :term:`kind <parameter kind>`.
        The native Python implementation is :class:`inspect.Parameter` and allows for additional attributes ``default`` and ``type``.
        The ``forge`` implementation is available at :class:`forge.FParameter`.

    parameter kind
        A parameter's :term:`kind <parameter kind>` determines its position in a signature, and how arguments to the :term:`callable` are mapped.
        There are five kinds of parameters: :term:`positional-only`, :term:`positional-or-keyword`, :term:`var-positional`, :term:`keyword-only` and :term:`var-keyword`.

    signature
        A :term:`signature` is the interface of a function.
        It contains zero or more :term:`parameters <parameter>`, and optionally a ``return-type`` annotation.
        The native Python implementation is :class:`inspect.Signature`.
        The ``forge`` implementation is available at :class:`forge.FSignature`.

    variadic parameter
        A :term:`variadic parameter` is a :term:`parameter` that accepts one or more :term:`parameters <parameter>`.
        There are two types: the :term:`var-positional` :term:`parameter` (traditionally named ``args``) and the :term:`var-keyword` :term:`parameter` (traditionally named ``kwargs``).


Parameter kinds
===============

.. glossary::

    positional-only
        A :term:`kind <parameter kind>` of :term:`parameter` that can only receive an unnamed argument.
        It is defined canonically as :attr:`inspect.Parameter.POSITIONAL_ONLY`, and is publicly available in ``forge`` as :paramref:`forge.FParameter.POSITIONAL_ONLY`.

        They are followed by :term:`positional-or-keyword`, :term:`var-positional`, :term:`keyword-only` and :term:`var-keyword` :term:`parameters <parameter>`.
        :term:`positional-only` parameters are distinguishable as they are followed by a slash (``/``).

        Consider the builtin function :func:`pow` – with three :term:`positional-only` :term:`parameters <parameter>`: ``x``, ``y``, and ``z``:

        .. code-block:: python

            >>> help(pow)
            Help on built-in function pow in module builtins:

            pow(x, y, z=None, /)
                Equivalent to x**y (with two arguments) or x**y % z (with three arguments)

                Some types, such as ints, are able to use a more efficient algorithm when invoked using the three argument form.
            >>> pow(2, 2)
            4
            >>> pow(x=2, y=2)
            TypeError: pow() takes no keyword arguments

        .. note::

            There is currently no way to compose a function with a :term:`positional-only` parameter in Python without diving deep into the internals of Python, or using a library like ``forge``.
            Without diving into the deep internals of Python and without using ``forge``, users are unable to write functions with :term:`positional-only` parameters.
            However, as demonstrated above, some builtin functions (such as :func:`pow`) have them.

            Writing functions with :term:`positional-only` parameters is proposed in :pep:`570`.

    positional-or-keyword
        A :term:`kind <parameter kind>` of :term:`parameter` that can receive either named or unnamed arguments.
        It is defined canonically as :attr:`inspect.Parameter.POSITIONAL_OR_KEYWORD`, and is publicly available in ``forge`` as :paramref:`forge.FParameter.POSITIONAL_OR_KEYWORD`.

        In function signatures, :term:`positional-or-keyword` :term:`parameters <parameter>` follow :term:`positional-only` :term:`parameters <parameter>`.
        They are followed by :term:`var-positional`, :term:`keyword-only` and :term:`var-keyword` :term:`parameters <parameter>`.
        :term:`positional-or-keyword` parameters are distinguishable as they are separated from :term:`positional-only` :term:`parameters <parameter>` by a slash (``/``).

        Consider the function :func:`isequal` which has two :term:`positional-or-keyword` :term:`parameters <parameter>`: ``a`` and ``b``:

        .. code-block:: python

            >>> def isequal(a, b):
            ...     return a == b
            >>> isequal(1, 1):
            True
            >>> isequal(a=1, b=2):
            False

    var-positional
        A :term:`kind <parameter kind>` of :term:`parameter` that receives unnamed arguments that are not associated with a :term:`positional-only` or :term:`positional-or-keyword` :term:`parameter`.
        It is defined canonically as :attr:`inspect.Parameter.VAR_POSITIONAL`, and is publicly available in ``forge`` as :paramref:`forge.FParameter.VAR_POSITIONAL`.

        In function signatures, the :term:`var-positional` :term:`parameter` follows :term:`positional-only` and :term:`positional-or-keyword` :term:`parameters <parameter>`.
        They are followed by :term:`keyword-only` and :term:`var-keyword` :term:`parameters <parameter>`.
        :term:`var-positional` parameters are distinguishable as their parameter name is prefixed by an asterisk (e.g. ``*args``).

        Consider the stdlib function :func:`os.path.join` which has the :term:`var-positional` :term:`parameter` ``p``:

        .. code-block:: python

            >>> import os
            >>> help(os.path.join)
            join(a, *p)
                Join two or more pathname components, inserting '/' as needed.
                If any component is an absolute path, all previous path components will be discarded.
                An empty last part will result in a path that ends with a separator.

            >>> os.path.join('/', 'users', 'jack', 'media')
            '/users/jack/media'

    keyword-only
        A :term:`kind <parameter kind>` of :term:`parameter` that can only receive a named argument.
        It is defined canonically as :attr:`inspect.Parameter.KEYWORD_ONLY`, and is publicly available in ``forge`` as :paramref:`forge.FParameter.KEYWORD_ONLY`.

        In function signatures, :term:`keyword-only` :term:`parameters <parameter>` follow :term:`positional-only`, :term:`positional-or-keyword` and :term:`var-positional` :term:`parameters <parameter>`.
        They are followed by the :term:`var-keyword` :term:`parameter`.
        :term:`keyword-only` parameters are distinguishable as they follow either an asterisk (``*``) or a :term:`var-positional` :term:`parameter` with an asterisk preceding its name (e.g. ``*args``).

        Consider the function :func:`compare` – with a :term:`keyword-only` :term:`parameter` ``key``:

        .. code-block:: python

            >>> def compare(a, b, *, key=None):
            ...     if key:
            ...         return a[key] == b[key]
            ...     return a == b
            >>> compare({'x': 1, 'y':2}, {'x': 1, 'y': 3})
            False
            >>> compare({'x': 1, 'y':2}, {'x': 1, 'y': 3}, key='x')
            True
            >>> compare({'x': 1, 'y':2}, {'x': 1, 'y': 3}, 'x')
            TypeError: compare() takes 2 positional arguments but 3 were given

        .. note::

            Writing functions with :term:`keyword-only` parameters was proposed in :pep:`3102` and accepted in April, 2006.


    var-keyword
        A :term:`kind <parameter kind>` of :term:`parameter` that receives named arguments that are not associated with a :term:`positional-or-keyword` or :term:`keyword-only` :term:`parameter`.
        It is defined canonically as :attr:`inspect.Parameter.VAR_KEYWORD`, and is publicly available in ``forge`` as :paramref:`forge.FParameter.VAR_KEYWORD`.

        In function signatures, the :term:`var-keyword` :term:`parameter` follows :term:`positional-only`, :term:`positional-or-keyword`, :term:`var-positional`, and :term:`keyword-only` :term:`parameters <parameter>`.
        It is distinguished with two asterisks that precedes the name.
        :term:`var-keyword` parameters are distinguishable as their parameter name is prefixed by two asterisks (e.g. ``**kwargs``).

        Consider the :class:`types.SimpleNamespace` constructor which takes only the :term:`var-keyword` parameter ``kwargs``:

        .. code-block:: python

            >>> from types import SimpleNamespace
            >>> help(SimpleNamespace)
            class SimpleNamespace(builtins.object)
            |  A simple attribute-based namespace.
            |
            |  SimpleNamespace(**kwargs)
            |  ...
            >>> SimpleNamespace(a=1, b=2, c=3)
            namespace(a=1, b=2, c=3)
