import inspect
import typing


class MarkerMeta(type):
    def __call__(cls, *args, **kwargs):
        return cls

    def __repr__(cls) -> str:
        return '<{}>'.format(cls.__name__)

    def __bool__(cls) -> bool:
        return False


class void(metaclass=MarkerMeta):
    # pylint: disable=C0103, invalid-name
    pass

def coerce_if(
        from_: typing.Any,
        is_: typing.Any,
        to_: typing.Any,
    ) -> typing.Any:
    return to_ if from_ is is_ else from_


def void_to_empty(value):
    return coerce_if(value, void, inspect.Parameter.empty)