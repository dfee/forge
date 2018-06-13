================================================
Revising signatures (i.e. *forging a signature*)
================================================

The basic *unit of work* with ``forge`` is the ``revision``.
A ``revision`` is an instance of :class:`~forge.Revision` (or a specialized subclass) that provides two interfaces:

#. a method :meth:`~forge.Revision.revise` that takes a :class:`~forge.FSignature` and returns it unchanged or returns a new :class:`~forge.FSignature`, or
#. the :func:`~forge.Revision.__call__` interface that allows the revision to be used as either a decorator or a function receiving a :term:`callable` to be wrapped.

:class:`~forge.Revision` subclasses often take initialization arguments that are used during the revision process.
For users, the most practical use of a ``revision`` is as a decorator.

While not very useful, :class:`~forge.Revision` provides the **identity** revision:

.. testcode::

    import forge

    @forge.Revision()
    def func():
        pass

The specialized subclasses are incredibly useful for surgically revising signatures.


Group revisions
===============

compose
-------

The :class:`~forge.compose` revision allows for imperatively describing the changes to a signature from top-to-bottom.

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

If we were to define recreate this without :class:`~forge.compose`, and instead use multiple signatures, the sequence would look like:

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
However, the resulting call stack and underlying :class:`~forge.Mapper` in the above example are identical.

Unlike applying multiple decorators, :class:`~forge.compose` does not validate the resulting :class:`~forge.FSignature` during internmediate steps.
This is useful when you want to change either the :term:`kind <parameter kind>` of a parameter or supply a default value - either of which often require a parameter to be moved within the signature.

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

After the ``modify`` revision, but before the ``move`` revisions, the signature appears to be ``func2(a=None, b, c)``.
Of course this is an invalid signature, as a :term:`positional-only` or :term:`positional-or-keyword` parameter with a default must follow parameters of the same kind *without* defaults.

.. note::

    The :class:`~forge.compose` revision accepts all other revisions (including :class:`~forge.compose`, itself) as arguments.


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


manage
------

The :class:`~forge.manage` revision lets you supply your own function that receives an instance of :class:`~forge.FSignature`, and returns a new instance. Because :class:`~forge.FSignature` is *immutable*, consider using :func:`~forge.FSignature.replace` to create a new :class:`~forge.FSignature` with updated attribute values or an altered ``return_annotation``

.. testcode::

    import forge

    reverse = lambda prev: prev.replace(parameters=prev[::-1])

    @forge.manage(reverse)
    def func(a, b, c):
        pass

    assert forge.repr_callable(func) == 'func(c, b, a)'


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


synthesize *(sign)*
-------------------

The :class:`~forge.synthesize` revision (also known as :data:`~forge.sign`) allows you to construct a signature by hand.

.. testcode::

    import forge

    @forge.sign(
        forge.pos('a'),
        forge.arg('b'),
        *forge.args,
        c=forge.kwarg(),
        **forge.kwargs,
    )
    def func(*args, **kwargs):
        pass

    assert forge.repr_callable(func) == 'func(a, /, b, *args, c, **kwargs)'

.. warning::

    When supplying parameters to :class:`~forge.synthesize` or :data:`~forge.sign`, unnamed parameter arguments are ordered by the order they were supplied, whereas named parameter arguments are ordered by their ``createion_order``

    This design decision is a consequence of Python <= 3.6 not guaranteeing insertion-order for dictionaries (and thus an unorderd :term:`var-keyword` argument).

    It is therefore recommended that when supplying pre-created parameters to :func:`.sign`, that they are specified only as positional arguments:

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


Unit revisions
==============

delete
------

The :class:`~forge.delete` revision removes a parameter from the signature.
This revision requires the receiving function's parameter to have a ``default`` value.
If no ``default`` value is provided, a :exc:`TypeError` will be raised.

.. testcode::

    import forge

    @forge.delete('a')
    def func(a=1, b=2, c=3):
        pass

    assert forge.repr_callable(func) == 'func(b=2, c=3)'


insert
------

The :class:`~forge.insert` revision adds a parameter or a sequence of parameters into a signature.
This revision takes the :class:`~forge.FParameter` to insert, and one of the following: :paramref:`~forge.insert.index`, :paramref:`~forge.insert.before`, or :paramref:`~forge.insert.after`.
If ``index`` is supplied, it must be an integer, whereas ``before`` and ``after`` must be the :paramref:`~forge.FParameter.name` of a parameter, an iterable of parameter names, or a function that receives a parameter and returns ``True`` if the parameter matches.

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

    In Python, :term:`positional-only` parameters are followed by :term:`positional-or-keyword` parameters. After that comes the :term:`var-positional` parameter, then any :term:`keyword-only` parameters, and finally an optional :term:`var-keyword` parameter.

    Using :class:`~forge.compose` and :class:`~forge.sort` can be helpful here to ensure that your parameters are properly ordered.

    .. testcode::

        import forge

        @forge.compose(
            forge.modify('b', kind=forge.FParameter.POSITIONAL_ONLY),
            forge.sort(),
        )
        def func(a, b, c):
            pass

        assert forge.repr_callable(func) == 'func(b, /, a, c)'


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


translocate *(move)*
--------------------

The :class:`~forge.translocate` revision (also known as :data:`~forge.move`) moves a parameter to another location in the signature.
:paramref:`~forge.translocate.selector`, :paramref:`~forge.translocate.before` and :paramref:`~forge.translocate.after` take a string for matching parameter names, an iterable of strings that contain a parameter's name, or a function that is passed the signature's :class:`~forge.FSignature` parameters and returns ``True`` upon a match.
One (and only one) of :paramref:`~forge.translocate.index`, :paramref:`~forge.translocate.before`, or :paramref:`~forge.translocate.after`, must be provided.

.. testcode::

    import forge

    @forge.move('a', after='c')
    def func(a, b, c):
        pass

    assert forge.repr_callable(func) == 'func(b, c, a)'

Mapper
======

The :class:`~forge.Mapper` is the glue that connects the :class:`~forge.FSignature` to an underlying :term:`callable`.
You shouldn't need to create a :class:`~forge.Mapper` yourself, but it's helpful to know that you can inspect the :class:`~forge.Mapper` and it's underlying strategy by looking at the ``__mapper__`` attribute on the function returned from a :class:`~forge.Revision`.
