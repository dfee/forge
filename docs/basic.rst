===========
Basic Usage
===========

.. _basic-usage_forging-signatures:

Forging signatures
==================

``forge``'s primary function is to allow users to revise and refine callable signatures.
This functionality is achieved on builtins, functions, and class instances with the special `__call__` dunder method by wrapping a callable with the special wrapping factory :func:`forge.sign`.

The minimal example is to wrap a function that takes no arguments (has no parameters) with a function that also takes no arguments (and has no parameters).

.. code-block:: python

    import forge

    @forge.sign()
    def func():
        pass

Forging a signature works as expected with ``staticmethod``, ``classmethod``, the instance ``method``, as well as ``property`` and ``__call__``.
The following example is a bit tedious, but its relevance is that it demonstrates that :func:`forge.sign` is transparent to underlying code.

.. code-block:: python

    import random
    import forge

    smin = 0
    smax = 10

    class Klass:
        cmin = 11
        cmax = 20

        def __init__(self):
            self.imin = 21
            self.imax = 30

        @staticmethod
        @forge.sign()
        def srandom():
            return random.randint(smin, smax)

        @classmethod
        @forge.sign(forge.cls)
        def crandom(cls):
            return random.randint(cls.cmin, cls.cmax)

        @property
        @forge.sign(forge.self)
        def irange(self):
            return range(self.imin, self.imax)

        @forge.sign(forge.self)
        def irandom(self):
            return random.randint(self.imin, self.imax)

        @forge.sign(forge.self)
        def __call__(self):
            return (self.imin, self.imax)

    assert smin <= Klass.srandom() <= smax
    assert Klass.cmin <= Klass.crandom() <= Klass.cmax

    klass = Klass()
    assert klass.imin <= klass.irandom() <= klass.imax
    assert klass.irange == range(klass.imin, klass.imax)
    assert klass() == (klass.imin, klass.imax)

The original function is available, unmodified at :attr:`func.__wrapped__`.
In addition, there are two additional attributes on the function, an instance of :class:`inspect.Signature`, and a :class:`~forge.Mapper` instance available at :attr:`__mapper__` that holds information about the new signature, the wrapped callable, and how to *map* arguments between the old and new signatures.

Function authors don't need to worry about their code signatures being altered as it's an implementation detail.
This expands the dynamic functionality of Python *upwards*.
This is exciting because while we've been able to dynamically create ``class`` objects by calling :func:``type(name, bases, namespace)``, **we've been unable to dynamically define function parameters at runtime**.

.. note::

    Sometimes you'll want to further simplify the forged signature, and to help there is a convenience function :func:`forge.resign` that revises a signature further without providing a second-level of nesting.
    Take a look at the :doc:`api` for more information.


.. _basic-usage_adding-a-parameter:

Adding a parameter
==================

``forge`` allows function signatures to be extended – that is for additional parameters to be added to a signature – if a signature has a :term:`var-keyword` argument (e.g. ``**kwargs``).

The additional parameter is mapped into the :term:`var-keyword` parameter, and will be available there within the function.
Users may add `postiional-only`, `positional-or-keyword` or `keyword-only` arguments with this method.

.. code-block:: python

    import forge

    @forge.sign(forge.arg('myparam', default=0))
    def func(**kwargs):
        # will have signature: func(myparam=0)
        return kwargs['myparam']

    assert func() == 0
    assert func(myparm=1) == 1

.. warning::

    ``variadic`` parameters (:term:`var-positional` and :term:`var-keyword`) cannot be added to a signature, as there is nowhere to map those parameters.


Supported by:

- :term:`positional-only`: via :func:`forge.pos`
- :term:`positional-or-keyword`: via :func:`forge.arg` and :func:`forge.pok`
- :term:`keyword-only`: via :func:`forge.kwarg` and :func:`forge.kwo`


.. basic-usage_removing-a-parameter:

Removing a parameter
====================

``forge`` expects the underlying function to rely on a parameter, so only parameters with default values (or variadic parameters :term:`var-positional` and :term:`var-keyword`) can be removed from the signature.

For example, if a function has a parameter with a default:

.. code-block:: python

    import forge

    @forge.sign()
    def func(myparam=0):
        # will have signature: func()
        return myparam

    assert func() == 0

And removing a variadic parameter:

.. code-block:: python

    import forge

    @forge.sign()
    def func(*args):
        return args

    assert func() == ()

If a callable's parameter doesn't have a default value, you can still remove it, but you must set the parameter's default and ``bind`` the argument value:

.. code-block:: python

    import forge

    @forge.sign(forge.arg('myparam', default=0, bound=True))
    def func(myparam):
        # will have signature: func()
        return myparam

    assert func() == 0


Supported by:

- :term:`positional-only`: via :func:`forge.pos`
- :term:`positional-or-keyword`: via :func:`forge.arg` and :func:`forge.pok`
- :term:`var-positional`: via :data:`forge.args` and :func:`forge.vpo`
- :term:`keyword-only`: via :func:`forge.kwarg` and :func:`forge.kwo`
- :term:`var-keyword`: via :data:`forge.kwargs` and :func:`forge.vkw`


.. basic-usage_renaming-a-parameter:

Renaming a parameter
====================

``forge`` allows parameters to be mapped to a different name.
This is useful when a callable's parameter names are generic, uninformative, or deceptively named.

To rename a ``non-variadic`` parameter, :class:`~forge.FParameter` takes a second positional argument, :paramref:`~forge.FParameter.interface_name` which is the name of the underlying parameter to map an argument value to:

.. code-block:: python

    import forge

    @forge.sign(
        forge.arg('value'),
        forge.arg('increment_by', 'other_value'),
    )
    def func(value, other_value):
        # will have signature: func(increment_by)
        return value + other_value

    assert func(3, increment_by=5) == 8

``Variadic`` parameter helpers :data:`forge.args` and :data:`forge.kwargs` (and their constructor counterparts :func:`forge.vpo` and :func:`forge.vkw` don't take an ``interface_name`` parameter, as functions can only have one :term:`var-positional` and one :term:`var-keyword` parameter.

.. code-block:: python

    import forge

    @forge.sign(*forge.args, **forge.kwargs)
    def func(*myargs, **mykwargs):
        # will have signature: func(*args, **kwargs)
        return myargs, mykwargs

    assert func(0, a=1, b=2, c=3) == ((0,), {'a': 1, 'b': 2, 'c': 3})

Supported by:

- :term:`positional-only`: via :func:`forge.pos`
- :term:`positional-or-keyword`: via :func:`forge.arg` and :func:`forge.pok`
- :term:`var-positional`: via :data:`forge.args` and :func:`forge.vpo`
- :term:`keyword-only`: via :func:`forge.kwarg` and :func:`forge.kwo`
- :term:`var-keyword`: via :data:`forge.kwargs` and :func:`forge.vkw`


.. basic-usage_setting-a-default-value:

Setting a default value
=======================

``forge`` allows default values to be provided for parameters by providing a ``default`` keyword-argument to :class:`~forge.FParameter` constructor:

.. code-block:: python

    import forge

    @forge.sign(forge.arg('myparam', default=5))
    def func(myparam):
        # will have signature: func(myparam=5)
        return myparam

    assert func() == 5

To **generate** default values using a function, rather than providing a constant value, provide a ``factory`` keyword-argument to :class:`~forge.FParameter`:

.. code-block:: python

    from datetime import datetime
    import forge

    @forge.sign(forge.arg('when', factory=datetime.now))
    def func(when):
        # will have signature: func(myparam=<Factory datetime.now>)
        return when

    func_ts = func()
    assert (datetime.now() - func_ts).seconds < 1

.. warning::

    :paramref:`~forge.FParameter.default` and :paramref:`~forge.FParameter.factory` mutually exclusive. Passing both will raise an :class:`TypeError`.

Supported by:

- :term:`positional-only`: via :func:`forge.pos`
- :term:`positional-or-keyword`: via :func:`forge.arg` and :func:`forge.pok`
- :term:`var-positional`: via :data:`forge.args` and :func:`forge.vpo`
- :term:`keyword-only`: via :func:`forge.kwarg` and :func:`forge.kwo`
- :term:`var-keyword`: via :data:`forge.kwargs` and :func:`forge.vkw`


.. basic-usage_setting-a-type-annotation:

Setting a type annotation
=========================

``forge`` allows type annotations to be added to parameters by providing a ``type`` keyword-argument to a :class:`~forge.FParameter` constructor:

.. code-block:: python

    import forge

    @forge.sign(forge.arg('myparam', type=int))
    def func(myparam):
        # will have signature: func(myparam:int)
        return myparam

Supported by:

- :term:`positional-only`: via :func:`forge.pos`
- :term:`positional-or-keyword`: via :func:`forge.arg` and :func:`forge.pok`
- :term:`var-positional`: via :data:`forge.args` and :func:`forge.vpo`
- :term:`keyword-only`: via :func:`forge.kwarg` and :func:`forge.kwo`
- :term:`var-keyword`: via :data:`forge.kwargs` and :func:`forge.vkw`

To provide a return-type annotation for a callable, use :func:`~forge.returns`:

.. code-block:: python

    import forge

    @forge.returns(int)
    def func():
        # will have signature: func() -> int
        return 42

Callables wrapped with :func:`forge.sign` or :func:`forge.resign` preserve the underlying return-type annotation if it's provided:

.. code-block:: python

    import forge

    @forge.sign()
    def func() -> int:
        # signature remains the same: func() -> int
        return 42


.. basic-usage_argument-conversion:

Argument conversion
===================

``forge`` supports argument value conversion by providing a keyword-argument :paramref:`~forge.FParameter.converter` to a :class:`~forge.FParameter` constructor.
:paramref:`~forge.FParameter.converter` must be a callable, or an iterable of callables, which accept three positional arguments: ``ctx``, ``name`` and ``value``:

.. code-block:: python

    def limit_to_max(ctx, name, value):
        if value > ctx.maximum:
            return ctx.maximum
        return value

    class MaxNumber:
        def __init__(self, maximum, capacity=0):
            self.maximum = maximum
            self.capacity = capacity

        @forge.sign(forge.self, forge.arg('value', converter=limit_to_max))
        def set_capacity(self, value):
            self.capacity = value

    maxn = MaxNumber(1000)

    maxn.set_capacity(500)
    assert maxn.capacity == 500

    maxn.set_capacity(1500)
    assert maxn.capacity == 1000

Supported by:

- :term:`positional-only`: via :func:`forge.pos`
- :term:`positional-or-keyword`: via :func:`forge.arg` and :func:`forge.pok`
- :term:`var-positional`: via :data:`forge.args` and :func:`forge.vpo`
- :term:`keyword-only`: via :func:`forge.kwarg` and :func:`forge.kwo`
- :term:`var-keyword`: via :data:`forge.kwargs` and :func:`forge.vkw`


.. basic-usage_argument-validation:

Argument validation
===================

``forge`` supports argument value validation by providing a keyword-argument :paramref:`~forge.FParameter.validator` to a :class:`~forge.FParameter` constructor.
:paramref:`~forge.FParameter.validator` must be a callable, or an iterable of callables, which accept three positional arguments: ``ctx``, ``name`` and ``value``:

.. code-block:: python

    def validate_lte_max(ctx, name, value):
        if value > ctx.maximum:
            raise ValueError('{} is greater than {}'.format(value, ctx.maximum))

    class MaxNumber:
        def __init__(self, maximum, capacity=0):
            self.maximum = maximum
            self.capacity = capacity

        @forge.sign(forge.self, forge.arg('value', validator=validate_lte_max))
        def set_capacity(self, value):
            self.capacity = value

    maxn = MaxNumber(1000)

    maxn.set_capacity(500)
    assert maxn.capacity == 500

    raised = None
    try:
        maxn.set_capacity(1500)
    except ValueError as exc:
        raised = exc
    assert raised.args[0] == '1500 is greater than 1000'


To use multiple validators, specify them in a ``list`` or ``tuple``:

.. code-block:: python

    import forge

    def validate_startswith_id(ctx, name, value):
        import ipdb; ipdb.set_trace()
        if not value.startswith('id'):
            raise ValueError("expected value beggining with 'id'")

    def validate_endswith_0(ctx, name, value):
        import ipdb; ipdb.set_trace()
        if not value.endswith('0'):
            raise ValueError("expected value ending with '0'")

    @forge.sign(
        forge.arg(
            'id',
            validator=[validate_startswith_id, validate_endswith_0],
        )
    )
    def stringify_id(id):
        return 'Your id is {}'.format(id)

    assert stringify_id('id100') == 'Your id is id100'

    raised = None
    try:
        stringify_id('id101')
    except ValueError as exc:
        raised = exc
    assert exc.args[0] == "expected value ending with '0'"

Supported by:

- :term:`positional-only`: via :func:`forge.pos`
- :term:`positional-or-keyword`: via :func:`forge.arg` and :func:`forge.pok`
- :term:`var-positional`: via :data:`forge.args` and :func:`forge.vpo`
- :term:`keyword-only`: via :func:`forge.kwarg` and :func:`forge.kwo`
- :term:`var-keyword`: via :data:`forge.kwargs` and :func:`forge.vkw`


.. basic-usage_parameter-metadata:

Parameter metadata
==================

``forge`` allows extra parameter metadata by providing a ``dict`` to a :class:`~forge.FParameter` constructor.
This metadata can be used in any way, but is exposed on the :class:`~forge.FParameter` as a :class:`types.MappingProxyView` (effectively a read-only ``dict``).

:class:`~forge.FParameter`s are available on an :class:`~forge.FSignature` instance as the ``fparameters`` attribute:

.. code-block:: python

    import forge

    @forge.sign(forge.arg('myparam', metadata={'__myproject_version': 3}))
    def func(myparam):
        # signature and functionality remains the same: func(myparam)
        return myparam

    fsig = func.__mapper__.fsignature
    myparam_md = fsig['myparam'].metadata
    assert myparam_md.get('__myproject_version') == 3


.. basic-usage_signature-context:

Signature context
=================

As mentioned in :ref:`argument-conversion` and :ref:`argument-validation`, a :class:`~forge.FSignature` can have a special first parameter known as a ``context`` parameter (a special :term:`positional-or-keyword` :class:`~forge.FParameter`).

Typically, ``context`` variables are useful for ``method``s and ``forge`` ships with two convenience ``context`` variables for convenience: :data:`forge.self` (for use with instance methods) and :data:`forge.cls` (available for ``classmethods``).

The value proposition for the ``context`` variable is that other :class:`~forge.FParameter` instances on the :class:`~forge.FSignature` that have a :paramref:`~forge.FParameter.converter` or :paramref:`~forge.FParameter.validator`, receive the ``context`` argument value as the first positional argument.

.. code-block:: python

    import forge

    def with_prefix(ctx, name, value):
        return '{}{}'.format(ctx.prefix, value)

    class Prefixer:
        def __init__(self, prefix):
            self.prefix = prefix

        @forge.sign(forge.self, forge.arg('text', converter=with_prefix))
        def apply(self, text):
            return text

    prefixer = Prefixer('banana')
    assert prefixer.apply('berry') == 'bananaberry'

If you want to define an additional ``context`` variable for your signature, you can use :func:`forge.ctx` to create a :term:`positional-or-keyword` :class:`~forge.FParameter`.
However, note that it has a more limited API than :func:`forge.arg`.