=======================================
Signatures, parameters and return types
=======================================

Crash course
============

Python :term:`callables <callable>` have a :term:`signature`: the interface which describes what arguments are accepted and (optionally) what kind of value is returned.

.. testcode::

    def func(a, b, c):
        return a + b + c

The function ``func`` (above) has the :term:`signature` ``(a, b, c)``.
We know that it requires three arguments, one for ``a``, ``b`` and ``c``.
These (``a``, ``b`` and ``c``) are called :term:`parameters <parameter>`.

The :term:`parameter` is the atomic unit of a :term:`signature`.
Every :term:`parameter` has *at a minimum* a ``name`` and a :term:`kind <parameter kind>`.

There are five kinds of parameters, which determine how an argument can be provided to its callable.
These kinds (in order) are:

#. :term:`positional-only`,
#. :term:`positional-or-keyword`,
#. :term:`var-positional`,
#. :term:`keyword-only` and
#. :term:`var-keyword`.

As ``forge`` is compatible with Python 3.5+, we can also provide type-hints:

.. testcode::

    def func(a: int, b: int, c: int) -> int:
        return a + b + c

Now, ``func`` has the signature ``(a: int, b: int, c: int) -> int``.
Of course, this means that ``func`` takes three integer arguments and returns an integer.

The Python-native classes for the :term:`signature` and :term:`parameter` are :class:`inspect.Signature` and :class:`inspect.Parameter`.
``forge`` introduces the companion classes :class:`forge.FSignature` and :class:`forge.FParameter`.
These classes extend the functionality of their Python-native counterparts, and allow for comprehensive signature revision.

Like :class:`inspect.Signature`, :class:`~forge.FSignature` is a container for a sequence of parameters and (optionally) what kind of value is returned.
The parameters that :class:`~forge.FSignature` contains (instances of :class:`~forge.FParameter`) provide a recipe for building a public :class:`inspect.Parameter` instance that maps to an underlying callable.

Here's an example, that we'll discuss in detail below:

.. testcode::

    import forge

    @forge.modify(
        'private',
        name='public',
        kind=forge.FParameter.KEYWORD_ONLY,
        default=3,
    )
    def func(private):
        return private

    assert forge.repr_callable(func) == 'func(*, public=3)'
    assert func(public=4) == 4

As you can see, the original definition of ``func`` has one parameter, ``private``.
If you inspect the revised function (e.g. ``help(func)``), however, you'll see a different parameter, ``public``.
The parameter ``public`` has also gained a ``default`` value, and is now a :term:`keyword-only` parameter.

This system allows for the addition, removal and modification of parameters.
It also allows for argument value **conversion** and **validation** (and more, as described below).


FSignature
==========

As detailed above, a :class:`~forge.FSignature` is a sequence of :class:`FParameters <forge.FParameter>` and an optional ``return_annotation`` (type-hint of the return value).
It closely mimics the API of :class:`inspect.Signature`, but it's also implements the ``sequence`` interface, so you can iterate over the underlying parameters.


Constructors
------------

The constructor :func:`forge.fsignature` creates a :class:`~forge.FSignature` from a :term:`callable`:

.. testcode::

    import forge
    import typing

    def func(a:int, b:int, c:int) -> typing.Tuple[int, int, int]:
        return (a, b, c)

    fsig = forge.fsignature(func)

    assert fsig.return_annotation == typing.Tuple[int, int, int]
    assert [fp.name for fp in fsig] == ['a', 'b', 'c']


Of course, an :class:`~forge.FSignature` can also be created by hand (though it's not usually necessary):

.. testcode::

    import forge

    fsig = forge.FSignature(
        parameters=[
            forge.arg('a', type=int),
            forge.arg('b', type=int),
            forge.arg('c', type=int),
        ],
        return_annotation=typing.Tuple[int, int, int],
    )

    assert fsig.return_annotation == typing.Tuple[int, int, int]
    assert [fp.name for fp in fsig] == ['a', 'b', 'c']


:class:`~forge.FSignature` instances also support overloaded ``__getitem__`` access.
You can pass an integer, a slice of integers, a string, or a slice of strings and retrieve certain parameters:

.. testcode::

   import forge

   fsig = forge.fsignature(lambda a, b, c: None)
   assert fsig[0] == \
          fsig['a'] == \
          forge.arg('a')
   assert fsig[0:2] == \
          fsig['a':'b'] == \
          [forge.arg('a'), forge.arg('b')]

This is useful for certain revisions, like :class:`forge.synthesize` (a.k.a. :class:`forge.sign`) and :class:`forge.insert` which take one or more parameters.
Here is an example of using :class:`forge.sign` to splice in parameters from another function:

.. testcode::

   import forge

   func = lambda a=1, b=2, d=4: None

   @forge.sign(
       *forge.fsignature(func)['a':'b'],
       forge.arg('c', default=3),
       forge.fsignature(func)['d'],
   )
   def func(**kwargs):
       pass

   assert forge.repr_callable(func) == 'func(a=1, b=2, c=3, d=4)'


FParameter
==========

An :class:`~forge.FParameter` is the atomic unit of an :class:`~forge.FSignature`.
It's primary responsibility is to apply a series of transforms and validations on an value and map that value to the parameter of an underlying callable.
It mimics the API of :class:`inspect.Parameter`, and extends it further to provide enriched functionality for value transformation.


Kinds and Constructors
----------------------

The :term:`kind <parameter kind>` of a parameter determines it's position in a signature and how a user can provide its argument value.
There are five :term:`kinds <parameter kind>` of parameters:

.. list-table:: FParameter Kinds
   :header-rows: 1
   :widths: 12 8 20

   * - Parameter Kind
     - Constant Value
     - Constructors
   * - :term:`positional-only`
     - :paramref:`~forge.FParameter.POSITIONAL_ONLY`
     - :func:`forge.pos`
   * - :term:`positional-or-keyword`
     - :paramref:`~forge.FParameter.POSITIONAL_OR_KEYWORD`
     - :func:`forge.pok` (a.k.a. :func:`forge.arg`)
   * - :term:`var-positional`
     - :paramref:`~forge.FParameter.VAR_POSITIONAL`
     - :func:`forge.vpo` (or :data:`*forge.args <forge.args>`)
   * - :term:`keyword-only`
     - :paramref:`~forge.FParameter.KEYWORD_ONLY`
     - :func:`forge.kwo` (a.k.a :func:`forge.kwarg`)
   * - :term:`var-keyword`
     - :paramref:`~forge.FParameter.VAR_KEYWORD`
     - :func:`forge.vko` (or :data:`**forge.kwargs <forge.kwargs>`)

.. note::

    The constructor for the :term:`positional-or-keyword` parameter (:func:`forge.pok`) and the constructor for the :term:`keyword-only` parameter (:func:`forge.kwo`) have alternate, *conventional* names: :func:`forge.arg` and :func:`forge.kwarg`, respectively.

    In addition, the constructor for the :term:`var-positional` parameter (:func:`forge.vpo`) and the constructor for the :term:`var-keyword` parameter (:func:`forge.vkw`) have alternate constructors that make their instantiation more semantic: :func:`*forge.args <forge.args>` and :func:`**forge.kwargs <forge.kwargs>`, respectively.

    As described below, :func:`*forge.args() <forge.args>` and :func:`**forge.kwargs() <forge.kwargs>` are also callable, accepting the same parameters as :func:`forge.vpo` and :func:`forge.vkw`, respectively.


This subject is quite dense, but the code snippet below – a brief demonstration using the revising :class:`forge.sign` to create a signature with *conventional* names - should help resolve any confusion:

.. testcode::

    import forge

    @forge.sign(
        forge.pos('my_positional'),
        forge.arg('my_positional_or_keyword'),
        *forge.args('my_var_positional'),
        my_keyword=forge.kwarg(),
        **forge.kwargs('my_var_keyword'),
    )
    def func(*args, **kwargs):
        pass

    assert forge.repr_callable(func) == \
        'func(my_positional, /, my_positional_or_keyword, *my_var_positional, my_keyword, **my_var_keyword)'


Using non-semantic (or *standard*) naming, we can reproduce that same signature:

.. testcode::

    import forge

    @forge.sign(
        forge.pos('my_positional'),
        forge.pok('my_positional_or_keyword'),
        forge.vpo('my_var_positional'),
        forge.kwo('my_keyword'),
        forge.vkw('my_var_keyword'),
    )
    def func(*args, **kwargs):
        pass

    assert forge.repr_callable(func) == \
        'func(my_positional, /, my_positional_or_keyword, *my_var_positional, my_keyword, **my_var_keyword)'

The latter version is less *semantic* in that it looks less like how a function signature would naturally be written.

.. warning::

    Positional arguments to :class:`forge.synthesize` (a.k.a. :class:`forge.sign`) are ordered by placement, while keyword-arguments are ordered by initialization order.
    In practice, if you're creating :class:`FParameters <forge.FParameter>` on separate lines and pass them to :class:`forge.sign`, you should opt for *non-conventional* or *standard* naming (as described above).
    For more information, read the API documentation for :class:`forge.synthesize`.


Naming
------

:class:`FParameters <~forge.FParameter>` have both a (:paramref:`~forge.FParameter.name`) and an (:paramref:`interface name <forge.FParameter.interface_name>`) - the name of the parameter in the underlying function that is the ultimate recipient of the argument.
This distinction is necessary to support the *re-mapping* of parameters to different names.
One use case might be if you're wrapping auto-generated code and providing sensible :pep:`8` compliant parameter names.

.. note::

    ``Variadic`` parameter helpers :data:`forge.args` and :data:`forge.kwargs` (and their constructor counterparts :func:`forge.vpo` and :func:`forge.vkw` don't take an ``interface_name`` parameter, as functions can only have one :term:`var-positional` and one :term:`var-keyword` parameter.

    In addition, ``forge`` does not allow a revised signature to accept either a :term:`var-positional` or :term:`var-keyword` :term:`variadic parameter` unless the underlying callable also has a parameter of the same kind.

    However, the underlying callable may have either a :term:`var-positional` or :term:`var-keyword` :term:`variadic parameter` without the revised signature also having that (respective) :term:`kind <parameter kind>` of parameters.

:paramref:`~forge.FParameter.name` and :paramref:`~forge.FParameter.interface_name` are the first two parameters for :class:`forge.pos`, :class:`forge.pok` (a.k.a. :class:`forge.arg`), and :class:`forge.kwo` (a.k.a. :class:`forge.kwarg`).
Here is an example of renaming a parameter, by providing :paramref:`~forge.FParameter.interface_name`:

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


Supported by:

- :term:`positional-only`: via :func:`forge.pos`
- :term:`positional-or-keyword`: via :func:`forge.pok` and :func:`forge.arg`
- :term:`var-positional`: via :data:`forge.vpo` and :func:`forge.args` (``name`` only)
- :term:`keyword-only`: via :func:`forge.kwo` and :func:`forge.kwarg`
- :term:`var-keyword`: via :data:`forge.vkw` and :func:`forge.kwargs` (``name`` only)


Defaults
--------

:class:`FParameters <forge.FParameter>` support default values by providing a :paramref:`~forge.FParameter.default` keyword-argument to a non-:term:`variadic parameter`.

.. testcode::

    import forge

    @forge.sign(forge.arg('myparam', default=5))
    def func(myparam):
        return myparam

    assert forge.repr_callable(func) == 'func(myparam=5)'
    assert func() == 5

Supported by:

- :term:`positional-only`: via :func:`forge.pos`
- :term:`positional-or-keyword`: via :func:`forge.pok` and :func:`forge.arg`
- :term:`keyword-only`: via :func:`forge.kwo` and :func:`forge.kwarg`


Default factory
---------------
In addition to supporting default values, :class:`FParameters <forge.FParameter>` also support default factories.
To create default values *on-demand*, provide a :paramref:`~forge.FParamter.factory` keyword-argument.
This argument should be a :term:`callable` that take no arguments and returns a value.

This is a convenience around passing an instance of :class:`~forge.Factory` to :paramref:`~forge.FParameter.default`.

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

    :paramref:`~forge.FParameter.default` and :paramref:`~forge.FParameter.factory` are mutually exclusive.
    Passing both will raise a :exc:`TypeError`.

Supported by:

- :term:`positional-only`: via :func:`forge.pos`
- :term:`positional-or-keyword`: via :func:`forge.arg` and :func:`forge.pok`
- :term:`keyword-only`: via :func:`forge.kwarg` and :func:`forge.kwo`


Type annotation
---------------

:class:`FParameters <forge.FParameter>` support type-hints by accepting a :paramref:`~forge.FParameter.type` keyword-argument:

.. testcode::

    import forge

    @forge.sign(forge.arg('myparam', type=int))
    def func(myparam):
        return myparam

    assert forge.repr_callable(func) == 'func(myparam:int)'

``forge`` doesn't do anything with these type-hints, but there are a number of third party frameworks and packages out there that perform validation [#f1]_.

.. note::
    To provide a return-type annotation for a callable, use :class:`~forge.returns`.
    Review this revision and others in the :doc:`revision <revision>` documentation.

Supported by:

- :term:`positional-only`: via :func:`forge.pos`
- :term:`positional-or-keyword`: via :func:`forge.pok` and :func:`forge.arg`
- :term:`var-positional`: via :data:`forge.vpo` and :func:`forge.args`
- :term:`keyword-only`: via :func:`forge.kwo` and :func:`forge.kwarg`
- :term:`var-keyword`: via :data:`forge.vkw` and :func:`forge.kwargs`


Conversion
----------

:class:`FParameters <forge.FParameter>` support conversion for argument values by accepting a :paramref:`~forge.FParameter.converter` keyword-argument.
This argument should either be a :term:`callable` that take three arguments: ``context``, ``name`` and ``value``, or an iterable of callables that accept those same arguments.
``Conversion`` functions must return the *converted value*.
If :paramref:`~forge.FParameter.converter` is an iterable of :term:`callables <callable>`, the converters will be called in order.

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


.. note::

    While :class:`forge.vpo` and :class:`forge.vkw` (and their semantic counterparts :func:`forge.args` and :func:`forge.kwargs`) don't support default values, this is a convenient way to provide that same functionality.

Supported by:

- :term:`positional-only`: via :func:`forge.pos`
- :term:`positional-or-keyword`: via :func:`forge.pok` and :func:`forge.arg`
- :term:`var-positional`: via :data:`forge.vpo` and :func:`forge.args`
- :term:`keyword-only`: via :func:`forge.kwo` and :func:`forge.kwarg`
- :term:`var-keyword`: via :data:`forge.vkw` and :func:`forge.kwargs`


Validation
----------

:class:`FParameters <forge.FParameter>` support validation for argument values by accepting a :paramref:`~forge.FParameter.validator` keyword-argument.
This argument should either be a :term:`callable` that take three arguments: ``context``, ``name`` and ``value``, or an iterable of callables that accept those same arguments.
``Validation`` functions should raise an :exc:`Exception` upon validation failure.
If :paramref:`~forge.FParameter.validator` is an iterable of :term:`callables <callable>`, the validaors will be called in order.

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

    @forge.sign(forge.arg('id', validator=[validate_startswith_id, validate_endswith_0]))
    def stringify_id(id):
        return 'Your id is {}'.format(id)

    assert stringify_id('id100') == 'Your id is id100'

    raised = None
    try:
        stringify_id('id101')
    except ValueError as exc:
        raised = exc
    assert raised.args[0] == "expected value ending with '0'"


.. note::

   Validators can be enabled or disabled (they're automatically enabled) by passing a boolean to :func:`~forge.set_run_validators`.
   In addition, the current status of validation is available by calling :func:`~forge.get_run_validators`.

Supported by:

- :term:`positional-only`: via :func:`forge.pos`
- :term:`positional-or-keyword`: via :func:`forge.pok` and :func:`forge.arg`
- :term:`var-positional`: via :data:`forge.vpo` and :func:`forge.args`
- :term:`keyword-only`: via :func:`forge.kwo` and :func:`forge.kwarg`
- :term:`var-keyword`: via :data:`forge.vkw` and :func:`forge.kwargs`


Binding
-------

:class:`FParameters <forge.FParameter>` can be bound to a ``default`` value or factory by passing ``True`` as the keyword-argument :paramref:`~forge.FParameter.bound`.
Bound parameters are not visible on the revised signature, but their default value is passed to the underlying callable.

This is handy when creating utility functions that enable only a subset of callable's parameters.
For example, to build a poor man's :mod:``requests``:

.. testcode::

    import urllib.request
    import forge

    @forge.copy(urllib.request.Request, exclude='self')
    def request(**kwargs):
        return urllib.request.urlopen(urllib.request.Request(**kwargs))

    def with_method(method):
        revised = forge.modify('method', default=method, bound=True)(request)
        revised.__name__ = method.lower()
        return revised

    get = with_method('GET')
    post = with_method('POST')
    put = with_method('PUT')
    delete = with_method('DELETE')
    patch = with_method('PATCH')
    options = with_method('OPTIONS')
    head = with_method('HEAD')

    assert forge.repr_callable(request) == 'request(url, data=None, headers={}, origin_req_host=None, unverifiable=False, method=None)'
    assert forge.repr_callable(get) == 'get(url, data=None, headers={}, origin_req_host=None, unverifiable=False)'
    response = get('http://google.com')
    assert b'Feeling Lucky' in response.read()

Supported by:

- :term:`positional-only`: via :func:`forge.pos`
- :term:`positional-or-keyword`: via :func:`forge.pok` and :func:`forge.arg`
- :term:`keyword-only`: via :func:`forge.kwo` and :func:`forge.kwarg`


Context
-------

The first parameter in a :class:`~forge.FSignature` is allowed to be a ``context`` parameter; a special instance of :class:`~forge.FParameter` that is passed to ``converter`` and ``validator`` functions.
For convenience, :data:`forge.self` and :data:`forge.cls` are already provided for use with instance methods and class methods, respectively.

.. testcode::

    import forge

    def with_prefix(ctx, name, value):
        return '{}{}'.format(ctx.prefix, value)

    class Prefixer:
        def __init__(self, prefix):
            self.prefix = prefix

        @forge.sign(
            forge.self,
            forge.arg('text', converter=with_prefix),
        )
        def apply(self, text):
            return text

    prefixer = Prefixer('banana')
    assert prefixer.apply('berry') == 'bananaberry'

.. note::
    If you want to define a custom ``context`` variable for your signature, you can use :func:`forge.ctx` to create a :term:`positional-or-keyword` :class:`~forge.FParameter`.
    However, :func:`forge.ctx` has a more limited API than :func:`forge.arg`, so read the API documentation.


Metadata
--------

If you're the author of a third-party library that relies on ``forge`` you can take advantage of *parameter metadata*.

Here are some tips for effective use of metadata:

- Try making your metadata immutable.
  This keeps the entire :class:`~forge.FParameter` instance immutable.
  :paramref:`~forge.FParameter.metadata` is exposed as a :class:`MappingProxyView`, helping enforce immutability.

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

  Metadata should be composable, and namespacing is part of the solution.

- Expose :class:`~forge.FParameter` wrappers for your specific metadata.
  While this can be challenging because of the special-use value :class:`forge.void`, a template function ``with_md`` is provided below:

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

Supported by:

- :term:`positional-only`: via :func:`forge.pos`
- :term:`positional-or-keyword`: via :func:`forge.pok` and :func:`forge.arg`
- :term:`var-positional`: via :data:`forge.vpo` and :func:`forge.args`
- :term:`keyword-only`: via :func:`forge.kwo` and :func:`forge.kwarg`
- :term:`var-keyword`: via :data:`forge.vkw` and :func:`forge.kwargs`


Markers
=======

``forge`` has two ``marker`` classes – :class:`~forge.empty` and :class:`~forge.void`.
These classes are used as default values to indicate non-input.
While both have counterparts in the :mod:`inspect` module, they are different and are not interchangeable.

Typically you won't need to use :class:`forge.empty` yourself, however the pattern referenced above for adding metadata to a :class:`~forge.FParameter` does require its use.

:class:`~forge.void` is more useful, as it can help distinguish supplied arguments from default arguments:

.. testcode::

    import forge

    @forge.sign(
        forge.arg('a', default=forge.void),
        forge.arg('b', default=forge.void),
        forge.arg('c', default=forge.void),
    )
    def func(**kwargs):
        return {k: v for k, v in kwargs.items() if v is not forge.void}

    assert forge.repr_callable(func) == 'func(a=<void>, b=<void>, c=<void>)'
    assert func(b=2, c=3) == {'b': 2, 'c': 3}


Utilities
=========

findparam
---------

:func:`forge.findparam` is a utility function for finding :class:`inspect.Parameter` instances or :class:`~forge.FParameter` instances in an iterable of parameters.

The :paramref:`~forge.findparam.selector` argument must be a string, an iterbale of strings, or a callable that recieves a parameter and conditionally returns ``True`` if the parameter is a match.

This is helpful when copying matching elements from a signature.
For example, to copy all the keyword-only parameters from a function:

.. testcode::

    import forge

    func = lambda a, b, *, c, d: None
    kwo_iter = forge.findparam(
        forge.fsignature(func),
        lambda param: param.kind == forge.FParameter.KEYWORD_ONLY,
    )
    assert [param.name for param in kwo_iter] == ['c', 'd']


callwith
--------

:func:`forge.callwith` is a proxy function that takes a ``callable``, a ``named`` argument map, and an iterable of ``unnamed`` arguments, and performs a call to the ``callable`` with properly sorted and ordered arguments.
Unlike in a typical function call, it is not necessary to properly order the arguments.
This is an extremely helpful utility when you are providing an proxy to another function that has many :term:`positional-or-keyword` arguments.

.. testcode::

    import forge

    def func(a, b, c, d=4, e=5, f=6, *args):
        return (a, b, c, d, e, f, args)

    @forge.sign(
        forge.arg('a', default=1),
        forge.arg('b', default=2),
        forge.arg('c', default=3),
        *forge.args,
    )
    def func2(*args, **kwargs):
        return forge.callwith(func, kwargs, args)

    assert forge.repr_callable(func2) == 'func2(a=1, b=2, c=3, *args)'
    assert func2(10, 20, 30, 'a', 'b', 'c') == (10, 20, 30, 4, 5, 6, ('a', 'b', 'c'))

An alternative implementation not using :func:`forge.callwith`, would look like this:

.. testcode::

    import forge

    def func(a, b, c, d=4, e=5, f=6, *args):
        return (a, b, c, d, e, f, args)

    @forge.sign(
        forge.arg('a', default=1),
        forge.arg('b', default=2),
        forge.arg('c', default=3),
        *forge.args,
    )
    def func2(*args, **kwargs):
        return func(
            kwargs['a'],
            kwargs['b'],
            kwargs['c'],
            4,
            5,
            6,
            *args,
        )

    assert forge.repr_callable(func2) == 'func2(a=1, b=2, c=3, *args)'
    assert func2(10, 20, 30, 'a', 'b', 'c') == (10, 20, 30, 4, 5, 6, ('a', 'b', 'c'))

Using :func:`forge.callwith` therefore requires less precision, boilerplate and maintenance.


repr_callable
-------------

:func:`~forge.repr_callable` takes a :term:`callable` and pretty-prints the function's qualified name, its parameters, and its return type annotation.

It's used extensively in the documentation to surface the resultant signature after a revision.


****

.. rubric:: Footnotes

.. [#f1] `typeguard <https://github.com/agronholm/typeguard>`_: Run-time type checker for Python
