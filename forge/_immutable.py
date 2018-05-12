from types import MappingProxyType
import typing


class ImmutableInstanceError(Exception):
    pass


def asdict(obj):
    return MappingProxyType(obj.__dict__) \
        if hasattr(obj, '__dict__') \
        else MappingProxyType({k: getattr(obj, k) for k in obj.__slots__})


def replace(obj, **changes):
    '''
    Return a new object replacing specified fields with new values.
    class Klass(Immutable):
        def __init__(self, value):
            # in lieu of: self.value = value
            object.__setattr__(self, 'value', value)

    k1 = Klass(1)
    k2 = replace(k1, value=2)
    assert (k1.value, k2.value) == (1, 2)
    '''
    return type(obj)(**dict(asdict(obj), **changes))


class Immutable:
    __slots__ = ()

    def __getattr__(self, key: str) -> typing.Any:
        '''Solely for placating mypy'''
        return super().__getattribute__(key)

    def __setattr__(self, key, value):
        raise ImmutableInstanceError("cannot assign to field '{}'".format(key))


class Struct(Immutable):
    __slots__ = ()

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            object.__setattr__(self, k, v)

    def __eq__(self, other: typing.Any):
        if not isinstance(other, type(self)):
            return False
        return asdict(other) == asdict(self)