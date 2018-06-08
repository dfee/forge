===========
Basic Usage
===========

.. _basic-usage_forging-signatures:

Forging signatures
==================

``forge``'s primary function is to allow users to revise and refine callable signatures.
Builtins, functions, and class instance callables (classes with the special `__call__` dunder method) are all supported.

The most practical example might be to :class:`~forge.copy` the signature from one function to another:

.. testcode::

    from types import SimpleNamespace
    from datetime import datetime
    import forge

    class Article(SimpleNamespace):
        pass

    def create_article(title=None, text=None):
        return Article(title=title, text=text, created_at=datetime.now())

    @forge.copy(create_article)
    def create_draft(**kwargs):
        kwargs['title'] = kwargs['title'] or '(draft)'
        return create_article(**kwargs)

    assert forge.repr_callable(create_draft) == \
        "create_draft(title=None, text=None)"

    draft = create_draft()
    assert draft.title == '(draft)'

As we can see, ``create_draft`` no longer exposes the :term:`var-keyword` parameter ``kwargs``.
Instead, it has the same function signature as ``create_article``.

As you might expect, passing a keyword-argument that's not ``title`` or ``text`` raises a TypeError.

.. testcode::

    try:
        create_draft(author='Abe Lincoln')
    except TypeError as exc:
        assert exc.args[0] == "create_draft() got an unexpected keyword argument 'author'"

Indeed, the signature is enforced!
How about creating another method for editing the article?
Let's keep in mind that we might want to erase the ``text`` of the article, so a value of ``None`` is significant.

In this example we're going to use four revisions: :class:`~forge.compose` (to perform a batch of revisions), :class:`~forge.copy` (to copy another function's signature), :class:`~forge.insert` (to add an additional parameter), and :class:`~forge.modify` (to alter one or more parameters).

.. testcode::

    @forge.compose(
        forge.copy(create_article),
        forge.insert(forge.arg('article'), index=0),
        forge.modify(
            lambda param: param.name != 'article',
            multiple=True,
            default=forge.void,
        ),
    )
    def edit_article(article, **kwargs):
        for k, v in kwargs.items():
            if v is not forge.void:
                setattr(article, k, v)

    assert forge.repr_callable(edit_article) == \
        "edit_article(article, title=<void>, text=<void>)"

    edit_article(draft, text='hello world')
    assert draft.title == '(draft)'
    assert draft.text == 'hello world'

As your ``Article`` class gains more attributes (``author``, ``tags``, ``status``, ``published_on``, etc.) the amount of effort to maintenance, update and test these parameters - or a subset of these parameters – becomes costly and taxing.





The "unit of work" with ``forge`` is the ``revision``.
A ``revision`` is an instance of :class:`~forge.Revision` (or an instance of a specialized subclass).
``Revision`` subclasses often take initialized arguments, and :meth:`~forge.Revision.revise` :class:`~forge.FSignature` instances.
The most practical use of a ``revision`` is as a decorator:

.. testcode::

    import forge

    @forge.Revision()
    def func():
        pass

The specialized subclasses are incredibly useful for surgically revising signatures.


.. _basic-revisions_group:

Revisions (group)
=================

The following revisions operate primarily on the signature as a whole.

.. _basic-revisions_group-compose:

compose
-------

The :class:`~forge.compose` revision allows for creating a batch revision ordered from top-to-bottom without validation performed between intermediate steps.

.. testcode::

    import forge

    func = lambda a, b, c: None

    @forge.compose(
        forge.copy(func),
        forge.modify('c', default=None)
    )
    def func2(**kwargs):
        pass

    assert forge.repr_callable(func2) == 'func2(a, b, c=None)'

If we were to define recreate this without :class:`~forge.compose`, it would look like:

.. testcode::

    import forge

    func = lambda a, b, c: None

    @forge.modify('c', default=None)
    @forge.copy(func)
    def func2(**kwargs):
        pass

    assert forge.repr_callable(func2) == 'func2(a, b, c=None)'

Notice how :class:`~forge.modify` comes before :class:`~forge.copy` in this latter example?
That's because the Python interpreter builds ``func2``, passes it to the the instance of :class:`~forge.copy`, and then passes *that* return value to :class:`~forge.modify`.

:class:`~forge.compose` is therefore as a useful tool to reason about your code top-to-bottom, rather than in an inverted manner.

In addition, if you were to to revise a signature so that it's no longer valid in an intermediate step (say you wanted to give a parameter a default value, but it's followed by another parameter of the same :term:`parameter kind` without a default value), :class:`~forge.compose` allows for signatures to have an invalid intermediate state:

.. testcode::

    import forge

    func = lambda a, b, c: None

    @forge.compose(
        forge.copy(func),
        forge.modify('a', default=None),
        forge.move('a', after='c'),
    )
    def func2(**kwargs):
        pass

    assert forge.repr_callable(func2) == 'func2(b, c, a=None)'

After the ``modify`` revision, but before the ``move`` revisions, the signature is ``func2(a=None, b, c)``, but of course a :term:`positional-only` or :term:`positional-or-keyword` parameter with a default must follow parameters of the same kind *without* defaults.

.. note::

    The :class:`~forge.compose` revision accepts all other revisions (including :class:`~forge.compose`, itself) as arguments.


.. _basic-revisions_group-copy:

copy
----

The :class:`~forge.copy` revision is straightforward: use it when you want to *copy* the signature from another callable.

.. testcode::

    import forge

    func = lambda a, b, c: None

    @forge.copy(func)
    def func2(**kwargs):
        pass

    assert forge.repr_callable(func2) == 'func2(a, b, c)'

As you can see, the signature of ``func`` is copied in its entirety to ``func2``.

.. note::

    In order to :class:`~forge.copy` a signature, the receiving callable must either have a :term:`var-keyword` parameter which collects the extra keyword arguments (as demonstrated above), or be pre-defined with all the same parameters:

    .. testcode::

        import forge

        func = lambda a, b, c: None

        @forge.copy(func)
        def func2(a=1, b=2, c=3):
            pass

        assert forge.repr_callable(func2) == 'func2(a, b, c)'

    The exception is the :term:`var-positional` parameter.
    If the new signature takes a :term:`var-positional` parameter (e.g. ``*args``), then the receiving function must also accept a :term:`var-positional` parameter.


.. _basic-revisions_group-manage:

manage
------

The :class:`~forge.manage` revision lets you supply your own function that receives an instance of :class:`~forge.FSignature`, and returns a new instance. Because :class:`~forge.FSignature` is *immutable*, consider using :meth:`~forge.FSignature.replace` to create a new :class:`~forge.FSignature` with updated ``parameters`` or an updated ``return_annotation``

.. testcode::

    import forge

    reverse = lambda prev: prev.replace(parameters=prev[::-1])

    @forge.manage(reverse)
    def func(a, b, c):
        pass

    assert forge.repr_callable(func) == 'func(c, b, a)'


.. _basic-revisions_group-returns:

returns
-------

The :class:`~forge.returns` revision alters the return type annotation of the receiving function.
In the case that there are no other revisions, :class:`~forge.returns` updates the receiving signature without wrapping it.

.. testcode::

    import forge

    @forge.returns(int)
    def func():
        pass

    assert forge.repr_callable(func) == 'func() -> int'

Of course, if you've defined a return type annotation on a function that has a forged signature, it's return type annotation will stay in place:

.. testcode::

    import forge

    @forge.compose()
    def func() -> int:
        pass

    assert forge.repr_callable(func) == 'func() -> int'


.. _basic-revisions_group-synthesize:

synthesize / sign
-----------------

The :class:`~forge.synthesize` revision (also known as :data:`~forge.sign`) allows you to construct a signature by hand.

.. testcode::

    import forge

    @forge.sign(
        forge.pos('a'),
        forge.arg('b'),
        *forge.args,
        c=forge.kwo(),
        **forge.kwargs,
    )
    def func(*args, **kwargs):
        pass

    assert forge.repr_callable(func) == 'func(a, /, b, *args, c, **kwargs)'

.. warning::

    When supplying parameters to :class:`~forge.synthesize` or :data:`~forge.sign`, unnamed parameter arguments are ordered by the order they were supplied, whereas named paramter arguments are ordered by their ``createion_order``

    This design decision is a consequence of Python <= 3.6 not guaranteeing insertion-order for dictionaries (and thus an unorderd :term:`var-keyword` argument).

    It is therefore recommended that when supplying pre-created parameters to :func:`.sign` or :func:`.resign` to supply them as positional arguments:

    .. testcode::

        import forge

        param_b = forge.arg('b')
        param_a = forge.arg('a')

        @forge.sign(a=param_a, b=param_b)
        def func1(**kwargs):
            pass

        @forge.sign(param_a, param_b)
        def func2(**kwargs):
            pass

        assert forge.repr_callable(func1) == 'func1(b, a)'
        assert forge.repr_callable(func2) == 'func2(a, b)'


.. _basic-revisions_group-sort:

sort
----

By default, the :class:`~forge.sort` revision sorts the parameters by :term:`parameter kind <kind>`, by whether they have a default value, and then by the name (lexicographically).

.. testcode::

    import forge

    @forge.sort()
    def func(c, b, a, *, f=None, e, d):
        pass

    assert forge.repr_callable(func) == 'func(a, b, c, *, d, e, f=None)'

:class:`~forge.sort` also accepts a user-defined function (:paramref:`~forge.sort.sortkey`) that receives the signature's :class:`~forge.FParameter` instances and emits a key for sorting.
The underlying implementation relies on :func:`builtins.sorted`, so head on over to the Python docs to jog your memory on how to use ``sortkey``.


.. _basic-revisions_unit:

Revisions (unit)
================

The following revisions work on one or more individual parameters of a signature.
As with the group revisions (above), the underlying function remains unmodified.


.. _basic-revisions_unit-delete:

delete
------

The :class:`~forge.delete` revision removes a parameter from the signature.
This revision requires the receiving function's parameter to have a default value.
If no default value is provided, a :exc:`TypeError` will be raised.

.. testcode::

    import forge

    @forge.delete('a')
    def func(a=1, b=2, c=3):
        pass

    assert forge.repr_callable(func) == 'func(b=2, c=3)'


.. _basic-revisions_unit-insert:

insert
------

The :class:`~forge.insert` revision adds a parameter or a sequence of parameters into a signature.
This revision takes the :class:`~forge.FParameter` to insert, and one of the following: :paramref:`~forge.insert.index`, :paramref:`~forge.insert.before`, or :paramref:`~forge.insert.after`.
If ``index`` is supplied, it must be an integer, whereas ``before`` and ``after`` must be the :paramref:`~forge.FParameter.name` of a parameter, an iterable of parameter names, or a function that receives a parameter and returns ``True`` if the paramter matches.

.. testcode::

    import forge

    @forge.insert(forge.arg('a'), index=0)
    def func(b, c, **kwargs):
        pass

    assert forge.repr_callable(func) == 'func(a, b, c, **kwargs)'

Or, to insert multiple parameters using :paramref:`~forge.FParameter.after` with a parameter name:

.. testcode::

    import forge

    @forge.insert([forge.arg('b'), forge.arg('c')], after='a')
    def func(a, **kwargs):
        pass

    assert forge.repr_callable(func) == 'func(a, b, c, **kwargs)'


.. _basic-revisions_unit-modify:

modify
------

The :class:`~forge.modify` revision modifies one or more of the receiving function's parameters.
It takes a :paramref:`~forge.modify.selector` argument (a parameter name, an iterable of names, or a callable that takes a parameter and returns ``True`` if matched), (optionally) a :paramref:`~forge.modify.multiple` argument (whether to apply the modification to all matching parameters), and keyword-arguments that map to the attributes of the underlying :class:`~forge.FParameter` to modify.

.. testcode::

    import forge

    @forge.modify('c', default=None)
    def func(a, b, c):
        pass

    assert forge.repr_callable(func) == 'func(a, b, c=None)'

.. warning::

    When using :class:`~forge.modify` to alter a signature's parameters, keep an eye on the :term:`parameter kind` of surrounding parameters and whether other parameters of the same :term:`parameter kind` lack default values.

    In Python, :term:`positional-only` paramters are followed by :term:`positional-or-keyword` parameters. After that comes the :term:`var-positional` parameter, then any :term:`keyword-only` parameters, and finally an optional :term:`var-keyword` parameter.

    Using :class:`~forge.compose` and :class:`~forge.sort` can be helpful here to ensure that your paramters are properly ordered.

    .. testcode::

        import forge

        @forge.compose(
            forge.modify('b', kind=forge.FParameter.POSITIONAL_ONLY),
            forge.sort(),
        )
        def func(a, b, c):
            pass

        assert forge.repr_callable(func) == 'func(b, /, a, c)'


.. _basic-revisions_unit-replace:

replace
-------

The :class:`~forge.replace` revision replaces a parameter outright.
This is a helpful alternative to ``modify`` when it's easier to replace a parameter outright than to alter its state.
:class:`~forge.replace` takes a :paramref:`~forge.replace.selector` argument (a string for matching parameter names, an iterable of strings that contain a parameter's name, or a function that is passed the signature's :class:`~forge.FSignature` parameters and returns ``True`` upon a match) and a new :class:`~forge.FParameter` instance.

.. testcode::

    import forge

    @forge.replace('a', forge.pos('a'))
    def func(a=0, b=1, c=2):
        pass

    assert forge.repr_callable(func) == 'func(a, /, b=1, c=2)'


.. _basic-revisions_unit-translocate:

translocate / move
------------------

The :class:`~forge.translocate` revision (also known as :data:`~forge.move`) moves a parameter to another location in the signature.
:paramref:`~forge.translocate.selector`, :paramref:`~forge.translocate.before` and :paramref:`~forge.translocate.after` take a string for matching parameter names, an iterable of strings that contain a parameter's name, or a function that is passed the signature's :class:`~forge.FSignature` parameters and returns ``True`` upon a match.
One (and only one) of :paramref:`~forge.translocate.index`, :paramref:`~forge.translocate.before`, or :paramref:`~forge.translocate.after`, must be provided.

.. testcode::

    import forge

    @forge.move('a', after='c')
    def func(a, b, c):
        pass

    assert forge.repr_callable(func) == 'func(b, c, a)'

Function authors don't need to worry about their code signatures being altered as it's an implementation detail.
This expands the dynamic functionality of Python *upwards*.
This is exciting because while we've been able to dynamically create ``class`` objects by calling :func:``type(name, bases, namespace)``, **we've been unable to dynamically define function parameters at runtime**.


.. _basic-usage_reflecting-a-signature:

Reflecting a signature
======================

Python developers often want to reflect the parameters of another callable, for instance when specializing a callable's usage.
For example:

.. testcode::

    import logging

    def func(a, b, c=0, *args, **kwargs):
        return (a, b, c, args, kwargs)

    def log_and_func(a, b, c, *args, **kwargs):
        logging.warning('{}'.format(dict(a=a, b=b, c=c, args=args, kwargs=kwargs)))
        return func(a, b, c, *args, **kwargs)

    assert log_and_func(1, 2, 3, 4, d=5) == (1, 2, 3, (4,), {'d': 5})

This can be simplified with :func:`~forge.reflect`, a convenience for applying the call signature of another function, and :func:`~forge.callwith`, a convenience for "calling out" to the underlying function with appropriately ordered arguments:

.. testcode::

    import logging
    import forge

    def func(a, b, c, *args, **kwargs):
        return (a, b, c, args, kwargs)

    @forge.copy(func)
    def log_and_func(*args, **kwargs):
        logging.warning('{}'.format(dict(args=args, kwargs=kwargs)))
        return forge.callwith(func, named=kwargs, unnamed=args)

    assert forge.repr_callable(log_and_func) == "log_and_func(a, b, c, *args, **kwargs)"
    assert log_and_func(1, 2, 3, 4, d=5) == (1, 2, 3, (4,), {'d': 5})

:func:`~forge.reflect` also supports :paramref:`~forge.reflect.include` and :paramref:`~forge.reflect.exclude`, which are iterables of parameter names to include or exclude, respectively.

.. testcode::

    import logging
    import forge

    def func(a, b, c, *args, **kwargs):
        return (a, b, c, args, kwargs)

    @forge.copy(func, exclude=['args'])
    def log_and_func(**kwargs):
        logging.warning('{}'.format(kwargs))
        return forge.callwith(func, named=kwargs)

    assert forge.repr_callable(log_and_func) == "log_and_func(a, b, c, **kwargs)"
    assert log_and_func(1, 2, 3, d=5) == (1, 2, 3, (), {'d': 5})


.. _basic-usage_adding-a-parameter:

Adding a parameter
==================

``forge`` allows function signatures to be extended – that is for additional parameters to be added to a signature – if a signature has a :term:`var-keyword` argument (e.g. ``**kwargs``).

The additional parameter is mapped into the :term:`var-keyword` parameter, and will be available there within the function.
Users may add `postiional-only`, `positional-or-keyword` or `keyword-only` arguments with this method.

.. testcode::

    import forge

    @forge.sign(forge.arg('myparam', default=0))
    def func(**kwargs):
        return kwargs['myparam']

    assert forge.repr_callable(func) == 'func(myparam=0)'

    assert func() == 0
    assert func(myparam=1) == 1

.. warning::

    ``variadic`` parameters (:term:`var-positional` and :term:`var-keyword`) cannot be added to a signature, as there is nowhere to map those parameters.


Supported by:

- :term:`positional-only`: via :func:`forge.pos`
- :term:`positional-or-keyword`: via :func:`forge.arg` and :func:`forge.pok`
- :term:`keyword-only`: via :func:`forge.kwarg` and :func:`forge.kwo`


.. _basic-usage_removing-a-parameter:

Removing a parameter
====================

``forge`` expects the underlying function to rely on a parameter, so only parameters with default values (or variadic parameters :term:`var-positional` and :term:`var-keyword`) can be removed from the signature.

For example, if a function has a parameter with a default:

.. testcode::

    import forge

    @forge.sign()
    def func(myparam=0):
        return myparam

    assert forge.repr_callable(func) == 'func()'
    assert func() == 0

And removing a variadic parameter:

.. testcode::

    import forge

    @forge.sign()
    def func(*args):
        return args

    assert forge.repr_callable(func) == 'func()'
    assert func() == ()

If a callable's parameter doesn't have a default value, you can still remove it, but you must set the parameter's default and ``bind`` the argument value:

.. testcode::

    import forge

    @forge.sign(forge.arg('myparam', default=0, bound=True))
    def func(myparam):
        return myparam

    assert forge.repr_callable(func) == 'func()'
    assert func() == 0

Supported by:

- :term:`positional-only`: via :func:`forge.pos`
- :term:`positional-or-keyword`: via :func:`forge.arg` and :func:`forge.pok`
- :term:`var-positional`: via :data:`forge.args` and :func:`forge.vpo`
- :term:`keyword-only`: via :func:`forge.kwarg` and :func:`forge.kwo`
- :term:`var-keyword`: via :data:`forge.kwargs` and :func:`forge.vkw`


.. _basic-usage_renaming-a-parameter:

Renaming a parameter
====================

``forge`` allows parameters to be mapped to a different name.
This is useful when a callable's parameter names are generic, uninformative, or deceptively named.

To rename a ``non-variadic`` parameter, :class:`~forge.FParameter` takes a second positional argument, :paramref:`~forge.FParameter.interface_name` which is the name of the underlying parameter to map an argument value to:

.. testcode::

    import forge

    @forge.sign(
        forge.arg('value'),
        forge.arg('increment_by', 'other_value'),
    )
    def func(value, other_value):
        return value + other_value

    assert forge.repr_callable(func) == 'func(value, increment_by)'
    assert func(3, increment_by=5) == 8

``Variadic`` parameter helpers :data:`forge.args` and :data:`forge.kwargs` (and their constructor counterparts :func:`forge.vpo` and :func:`forge.vkw` don't take an ``interface_name`` parameter, as functions can only have one :term:`var-positional` and one :term:`var-keyword` parameter.

.. testcode::

    import forge

    @forge.sign(*forge.args, **forge.kwargs)
    def func(*myargs, **mykwargs):
        return myargs, mykwargs

    assert forge.repr_callable(func) == 'func(*args, **kwargs)'
    assert func(0, a=1, b=2, c=3) == ((0,), {'a': 1, 'b': 2, 'c': 3})

Supported by:

- :term:`positional-only`: via :func:`forge.pos`
- :term:`positional-or-keyword`: via :func:`forge.arg` and :func:`forge.pok`
- :term:`var-positional`: via :data:`forge.args` and :func:`forge.vpo`
- :term:`keyword-only`: via :func:`forge.kwarg` and :func:`forge.kwo`
- :term:`var-keyword`: via :data:`forge.kwargs` and :func:`forge.vkw`


.. _basic-usage_type-annotation:

Type annotation
===============

``forge`` allows type annotations (i.e. ``type-hints``) to be added to parameters by providing a ``type`` keyword-argument to a :class:`~forge.FParameter` constructor:

.. testcode::

    import forge

    @forge.sign(forge.arg('myparam', type=int))
    def func(myparam):
        return myparam

    assert forge.repr_callable(func) == 'func(myparam:int)'

``forge`` doesn't do anything with these type-hints, but there are a number of third party frameworks and packages out there that perform validation.

Supported by:

- :term:`positional-only`: via :func:`forge.pos`
- :term:`positional-or-keyword`: via :func:`forge.arg` and :func:`forge.pok`
- :term:`var-positional`: via :data:`forge.args` and :func:`forge.vpo`
- :term:`keyword-only`: via :func:`forge.kwarg` and :func:`forge.kwo`
- :term:`var-keyword`: via :data:`forge.kwargs` and :func:`forge.vkw`

To provide a return-type annotation for a callable, use :func:`~forge.returns`:

.. testcode::

    import forge

    @forge.returns(int)
    def func():
        return 42

    assert forge.repr_callable(func) == 'func() -> int'

Callables wrapped with :func:`forge.sign` or :func:`forge.resign` preserve the underlying return-type annotation if it's provided:

.. testcode::

    import forge

    @forge.sign()
    def func() -> int:
        # signature remains the same: func() -> int
        return 42

    assert forge.repr_callable(func) == 'func() -> int'


.. _basic-usage_argument-defaults:

Argument defaults
=================

``forge`` allows default values to be provided for parameters by providing a ``default`` keyword-argument to :class:`~forge.FParameter` constructor:

.. testcode::

    import forge

    @forge.sign(forge.arg('myparam', default=5))
    def func(myparam):
        return myparam

    assert forge.repr_callable(func) == 'func(myparam=5)'
    assert func() == 5

To **generate** default values using a function, rather than providing a constant value, provide a ``factory`` keyword-argument to :class:`~forge.FParameter`:

.. testcode::

    from datetime import datetime
    import forge

    @forge.sign(forge.arg('when', factory=datetime.now))
    def func(when):
        return when

    assert forge.repr_callable(func) == 'func(when=<Factory datetime.now>)'
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


.. _basic-usage_argument-conversion:

Argument conversion
===================

``forge`` supports argument value conversion by providing a keyword-argument :paramref:`~forge.FParameter.converter` to a :class:`~forge.FParameter` constructor.
:paramref:`~forge.FParameter.converter` must be a callable, or an iterable of callables, which accept three positional arguments: ``ctx``, ``name`` and ``value``:

.. testcode::

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


.. _basic-usage_argument-validation:

Argument validation
===================

``forge`` supports argument value validation by providing a keyword-argument :paramref:`~forge.FParameter.validator` to a :class:`~forge.FParameter` constructor.
:paramref:`~forge.FParameter.validator` must be a callable, or an iterable of callables, which accept three positional arguments: ``ctx``, ``name`` and ``value``:

.. testcode::

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

.. testcode::

    import forge

    def validate_startswith_id(ctx, name, value):
        if not value.startswith('id'):
            raise ValueError("expected value beggining with 'id'")

    def validate_endswith_0(ctx, name, value):
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
    assert raised.args[0] == "expected value ending with '0'"

Supported by:

- :term:`positional-only`: via :func:`forge.pos`
- :term:`positional-or-keyword`: via :func:`forge.arg` and :func:`forge.pok`
- :term:`var-positional`: via :data:`forge.args` and :func:`forge.vpo`
- :term:`keyword-only`: via :func:`forge.kwarg` and :func:`forge.kwo`
- :term:`var-keyword`: via :data:`forge.kwargs` and :func:`forge.vkw`


.. _basic-usage_parameter-metadata:

Parameter metadata
==================

If you're the author of a third-party library with ``forge`` integration, you may want to take advantage of parameter metadata.

Here are some tips for effective use of metadata:

- Try making your metadata immutable.
    This keeps the entire ``Parameter`` instance immutable.
    :attr:`FParameter.metdata` is exposed as a :class:`MappingProxyView`, helping enforce immutability.

- To avoid metadata key collisions, provide namespaced keys:

    .. testcode::

        import forge

        MY_PREFIX = '__my_prefix'
        MY_KEY = '{}_mykey'.format(MY_PREFIX)

        @forge.sign(forge.arg('param', metadata={MY_KEY: 'value'}))
        def func(param):
            pass

        param = func.__mapper__.fsignature.parameters['param']
        assert param.metadata == {MY_KEY: 'value'}

    Metadata should be composable, so consider supporting this approach even if you decide implementing your metadata in one of the following ways.

- Expose ``FParameter`` wrappers for your specific metadata.
    This can be more challenging because of the special-use value :class:`forge.void`, but a template function ``with_md`` is provided below:

    .. testcode::

        import forge

        MY_PREFIX = '__my_prefix'
        MY_KEY = '{}_mykey'.format(MY_PREFIX)

        def update_metadata(ctx, name, value):
            return dict(value or {}, **{MY_KEY: 'myvalue'})

        def with_md(constructor):
            fsig = forge.FSignature.from_callable(constructor)
            parameters = []
            for name, param in fsig.parameters.items():
                if name in ('default', 'factory', 'type'):
                    parameters.append(param.replace(
                        converter=lambda ctx, name, value: forge.empty,
                        factory=lambda: forge.empty,
                    ))
                elif name == 'metadata':
                    parameters.append(param.replace(converter=update_metadata))
                else:
                    parameters.append(param)
            return forge.sign(*parameters)(constructor)

        md_arg = with_md(forge.arg)
        param = md_arg('x')
        assert param.metadata == {'__my_prefix_mykey': 'myvalue'}


.. _basic-usage_signature-context:

Signature context
=================

As mentioned in :ref:`basic-usage_argument-conversion` and :ref:`basic-usage_argument-validation`, a :class:`~forge.FSignature` can have a special first parameter known as a ``context`` parameter (a special :term:`positional-or-keyword` :class:`~forge.FParameter`).

Typically, ``context`` variables are useful for ``method``s and ``forge`` ships with two convenience ``context`` variables for convenience: :data:`forge.self` (for use with instance methods) and :data:`forge.cls` (available for ``classmethods``).

The value proposition for the ``context`` variable is that other :class:`~forge.FParameter` instances on the :class:`~forge.FSignature` that have a :paramref:`~forge.FParameter.converter` or :paramref:`~forge.FParameter.validator`, receive the ``context`` argument value as the first positional argument.

.. testcode::

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