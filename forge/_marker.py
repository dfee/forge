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
    # pylint: disable=R0903, too-few-public-methods
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
    # pylint: disable=C0103, invalid-name
    # pylint: disable=R0903, too-few-public-methods
    native = inspect.Parameter.empty

    @classmethod
    def ccoerce(cls, value):
        """
        Conditionally coerce the value to a non-:class:`.empty` value.

        :return: the value, if the value is not an instance of :class:`.empty`,
            otherwise return :class:`inspect.Paramter.empty`
        """
        return value if value is not cls else cls.native