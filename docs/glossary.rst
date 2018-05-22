========
Glossary
========

.. glossary::

  callable:
    A ``callable`` is a Python object that receives arguments and returns a result.
    Typical examples are ``builtin`` functions like ``sorted``, ``lambda``s and user-defined ``functions``, and class instances that implement a `__call__` method (including the class object itself).

  parameter:
    A ``parameter`` is the atomic unit of a signature.
    It has at minimum a name and a :term:`kind <parameter kind>`.
    The native Python implementation is :class:`inspect.Parameter` and allows for additional attributes ``default`` and ``type``.

  parameter kind
    A parameter's ``kind`` determines its position in a signature, and how arguments are mapped to the :term:`callable` it represents.
    There are five kinds of parameters: :term:`positional-only`, :term:`positional-or-keyword`, :term:`var-positional`, :term:`keyword-only` and :term:`var-keyword`.

  signature
    A :term:`callable`'s signature is the public-interface to a function. It contains zero or more :term:`parameter`s, and optionally a ``return-type`` annotation.


Parameter kinds
===============

.. glossary::

  positional-only
    A :term:`parameter kind` defined canonically by :attr:`inspect.Parameter.POSITIONAL_ONLY`, and available as :attr:`forge.POSITIONAL_ONLY`, arguments for these parameters *cannot be named* when supplied to a function.

    In function signatures, :term:`positional-only` parameters precede the ``/`` marker, and are followed by :term:`positional-or-keyword`, :term:`var-positional`, :term:`keyword-only` and :term:`var-keyword` parameters.
    Consider the builtin function :func:`pow`:

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

      Without diving into the deep internals of Python (or using this library), users are unable to write functions with :term:`positional-only` parameters.
      However, as demonstrated above, some builtin functions (such as :func:`pow`) have them.

      Writing functions with :term:`positional-only` parameters is proposed in `PEP 570`_.

  positional-or-keyword
    A :term:`parameter kind` defined canonically by :attr:`inspect.Parameter.POSITIONAL_OR_KEYWORD`, and available as :attr:`forge.POSITIONAL_OR_KEYWORD`, arguments for these parameters *can optionally be named* when supplied to a function.

    In function signatures, :term:`positional-or-keyword` parameters follow :term:`positional-only` parameters, and are followed by *var-postitional*, :term:`keyword-only` and :term:`var-keyword` parameters.
    Consider the function :func:`isequal`:

    .. code-block:: python

      >>> def isequal(a, b):
      ...     return a == b
      >>> isequal(1, 1):
      True
      >>> isequal(a=1, b=2):
      False

  var-positional
    A :term:`parameter kind` defined canonically by :attr:`inspect.Parameter.VAR_POSTIIONAL`, and available as :attr:`forge.VAR_POSTIIONAL`, arguments for this parameter cannot be specified by the caller.
    Instead, all supplied, but unbound and non-named arguments are collected into a tuple under this name.

    In function signatures, the :term:`var-positional` parameter is preceded by the ``*`` marker, and is often named ``args``.
    It follows :term:`positional-only` and :term:`positional-or-keyword` parameters, and it preceeds :term:`keyword-only` and :term:`var-keyword` parameters.
    Consider the stdlib function :func:`os.path.join`:

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
    A :term:`parameter kind` defined canonically by :attr:`inspect.Parameter.KEYWORD_ONLY`, and available as :attr:`forge.KEYWORD_ONLY`, arguments for these parameters *must be named* when supplied to a function.

    In function signatures, :term:`keyword-only` parameters follow :term:`positional-only`, :term:`positional-or-keyword` and :term:`var-keyword` parameters.
    They preceed a :term:`var-positional` parameter (if supplied).
    Consider the function :func:`compare`:

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

      Writing functions with :term:`keyword-only` parameters was proposed in `PEP 3102`_ and accepted in April, 2006.


  var-keyword
    A :term:`parameter kind` defined canonically by :attr:`inspect.Parameter.VAR_KEYWORD`, and available as :attr:`forge.VAR_KEYWORD`, arguments for this parameter cannot be specified by the caller.
    Instead, all supplied, but unbound keyword arguments are collected into a dict under this name.

    In function signatures, the :term:`var-keyword` parameter is preceded by the ``**`` marker, and is often named ``kwargs``.
    It is the last kind of parameter in a signature, following :term:`positional-only`, :term:`positional-or-keyword`, :term:`var-positional` and :term:`keyword-only` parameters.
    Consider the :class:`types.SimpleNamespace` constructor:

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


.. _`PEP 570`: https://www.python.org/dev/peps/pep-0570/
.. _`PEP 3102`: https://www.python.org/dev/peps/pep-3102/