import inspect
import typing


T = typing.TypeVar('T')

class MarkerMeta(type):
    """
    A metaclass that creates singletons by overriding `__call__`.

    Usage::

        >>> class Marker(metaclass=MarkerMeta):
        ...     pass
        ...
        >>> assert Marker() is Marker
    """
    def __call__(cls: T, *args, **kwargs) -> T:
        """
        Returns the class itself; does not generate a new class. The class's
        ``__new__`` method is not called.
        """
        return cls

    def __repr__(cls) -> str:
        return '<{}>'.format(cls.__name__)

    def __bool__(cls) -> bool:
        return False


class void(metaclass=MarkerMeta):
    """
    A simple :class:`~forge.marker.MarkerMeta` class useful for denoting that
    no input was suplied.

    Usage::

        def proxy(a, b, extra=void):
            if extra is not void:
                return proxied(a, b)
            return proxied(a, b, c=extra)
    """
    # pylint: disable=C0103, invalid-name
    pass


def coerce_if(
        check: typing.Callable[[typing.Any], bool],
        from_: typing.Any,
        # is_: typing.Any,
        to_: typing.Any,
    ) -> typing.Any:
    """
    Coerce's a value to another value if it meets a check condition.

    Usage::

        >>> inputs = [1, 2, 3]
        >>> outputs = [coerce_if(lambda i: i % 2, val, None) for val in inputs]
        >>> assert outputs == [None, 2, None]

    :param check: the constraint checker; if the result is ``True``, then
        :paramref:`.coerce_if.from_` is replaced with :paramref:`.coerce_if.to_`
    :param from_: the value to pass to the constraint checker
    :param to_: the replacement value if :paramref:`.coerce_if.check` returns
        a value that is truthy.
    :return: a conditionally coerced value.
    """
    # TODO: test
    return to_ if check(from_) else from_
    # return to_ if from_ is is_ else from_


def void_to_empty(value):
    """
    A convenience function whose implementation reflects::

        >>> result = value if value is not void else inspect.Parameter.empty

    :class:`inspect.Parameter.empty` if the value is :class:`.void`.
    :param value: a value to compare to void
    :return: a not :class:`.void` value, either because
        :paramref:`.void_to_empty.value` was not :class:`.void` or because
        it was :class:`.void` and was converted to
        :class:`.inspect.Parameter.empty`
    """
    return coerce_if(lambda i: i is void, value, inspect.Parameter.empty)