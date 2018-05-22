=========
Extending
=========

Each callable wrapped with :func:`forge.sign` has a ``__mapper__`` attribute on the returned function.
The ``__mapper__`` is an instance of :class:`forge.Mapper` that provides the recipe for transforming arguments from the public signature to the signature of the wrapped callable.

Callables wrapped with :func:`forge.sign` are easily re-wapped with custom decorators, or you can replace the ``__mapper__`` without re-wrapping the function.
For convenience, :func:`forge.resign` does exactly that.


.. _extending_types:

Types
=====

``forge`` allows users to supply parameter and return-value annotations (type-hints).

To add type information to a parameter:

.. doctest::

   >>> import forge
   >>> @forge.sign(forge.arg('param', type=int))
   ... def func(param):
   ...     return 1
   ...
   >>> help(func)
   func(param:int)

:func:`forge.sign` automatically captures the return-type for functions it wraps, but you can alter the return-type with :func:`forge.returns`.

.. doctest::

  >>> import forge
  >>> @forge.returns(False)
  ... @forge.sign()
  ... def return_false() -> bool:
  ...     return False
  ...
  >>> help(return_false)
  return_false() -> False

``forge`` doesn't do anything with these type-hints, but there are a number of third party frameworks and packages out there that perform validation.


.. _extending_metadata:

Metadata
========

If you're the author of a third-party library with ``forge`` integration, you may want to take advantage of parameter metadata.

Here are some tips for effective use of metadata:

- Try making your metadata immutable.
  This keeps the entire ``Parameter`` instance immutable.
  :attr:`FParameter.metdata` is exposed as a :class:`MappingProxyView`, helping enforce immutability.

- To avoid metadata key collisions, provide namespaced keys:

  .. doctest::

    >>> MY_PREFIX = '__my_prefix'
    >>> @forge.sign(
    ...     forge.arg('param', metadata={f'{MY_PREFIX}_mykey': 'value'}),
    ... )
    >>> def func(param):
    ...     pass

  Metadata should be composable, so consider supporting this approach even if you decide implementing your metadata in one of the following ways.

- Expose ``FParameter`` wrappers for your specific metadata.
  This can be more challenging because of the special-use value :class:`forge.void`, but a template function ``with_md`` is provided below:

  .. doctest::

    >>> import forge
    >>> MY_PREFIX = '__my_prefix'
    >>> def update_metadata(ctx, name, value):
    ...     return dict(value or {}, **{f'{MY_PREFIX}_mykey': 'myvalue'})
    ...
    >>> def with_md(constructor):
    ...     fparams = dict(forge.FSignature.from_callable(constructor))
    ...     for k in ('default', 'factory', 'type'):
    ...         if k not in fparams:
    ...             continue
    ...         fparams[k] = fparams[k].replace(
    ...             converter=lambda ctx, name, value: forge.void,
    ...             factory=lambda: forge.void,
    ...         )
    ...     fparams['metadata'] = fparams['metadata'].\
    ...         replace(converter=update_metadata)
    ...     return forge.sign(**fparams)(constructor)
    ...
    >>> md_arg = with_md(forge.arg)
    >>> param = md_arg('x')
    >>> assert param.metadata == {'__my_prefix_mykey': 'myvalue'}

:term:`positional-only`