import inspect
import typing

# pylint: disable=C0103, invalid-name

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
    pass


class empty(metaclass=MarkerMeta):
    """
    A simple :class:`~forge.marker.MarkerMeta` class useful for denoting that
    no input was suplied. Used in place of :class:`inspect.Parameter.empty`
    as that is not repr'd (providing confusing usage).

    Usage::

        def proxy(a, b, extra=empty):
            if extra is not empty:
                return proxied(a, b)
            return proxied(a, b, c=inspect.Parameter.empty)

    :ivar native: local storage of :class:`inspect.Parameter.empty`
    """
    native = inspect.Parameter.empty

    @classmethod
    def ccoerce_native(cls, value):
        """
        Conditionally coerce the value to a non-:class:`~forge.empty` value.

        .. versionchanged:: 18.5.1 ``coerce`` -> ``coerce_native``

        :param value: the value to conditionally coerce
        :return: the value, if the value is not an instance of
            :class:`~forge.empty`, otherwise return
            :class:`inspect.Paramter.empty`
        """
        return value if value is not cls else cls.native

    @classmethod
    def ccoerce_synthetic(cls, value):
        """
        Conditionally coerce the value to a
        non-:class:`inspect.Parameter.empty` value.

        .. versionadded:: 18.5.1

        :param value: the value to conditionally coerce
        :return: the value, if the value is not an instance of
            :class:`inspect.Paramter.empty`, otherwise return
            :class:`~forge.empty`
        """
        return value if value is not cls.native else cls
