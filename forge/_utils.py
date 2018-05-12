import inspect
import typing

from forge._exceptions import ParameterError
from forge._marker import void
from forge._parameter import ParameterMap


POSITIONAL_ONLY = inspect.Parameter.POSITIONAL_ONLY
POSITIONAL_OR_KEYWORD = inspect.Parameter.POSITIONAL_OR_KEYWORD
VAR_POSITIONAL = inspect.Parameter.VAR_POSITIONAL
KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY
VAR_KEYWORD = inspect.Parameter.VAR_KEYWORD


TGenericCallable = typing.Callable[..., typing.Any]
TUnionParameter = \
    typing.TypeVar('TUnionParameter', inspect.Parameter, ParameterMap)


def hasparam(
        callable_: TGenericCallable,
        name: str,
    ) -> bool:
    if not callable(callable_):
        raise TypeError('{} is not callable'.format(callable_))
    return name in inspect.signature(callable_).parameters


def getparam(
        callable_: typing.Callable[..., typing.Any],
        name: str,
        default: typing.Any = void,
    ) -> inspect.Parameter:
    if not callable(callable_):
        raise TypeError('{} is not callable'.format(callable_))

    params = inspect.signature(callable_).parameters
    if default is not void:
        return params.get(name, default)
    try:
        return params[name]
    except KeyError:
        raise ParameterError(
            "'{callable_name}' has no parameter '{param_name}'".format(
                callable_name=callable_.__name__,
                param_name=name,
            )
        )


def get_return_type(callable_: TGenericCallable) -> typing.Any:
    if not callable(callable_):
        raise TypeError('{} is not callable'.format(callable_))
    if hasattr(callable_, '__signature__'):
        return callable_.__signature__.return_annotation  # type: ignore
    return callable_.__annotations__.get('return', inspect.Signature.empty)


def set_return_type(
        callable_: TGenericCallable,
        type: typing.Any,
    ) -> None:
    # pylint: disable=W0622, redefined-builtin
    if not callable(callable_):
        raise TypeError('{} is not callable'.format(callable_))
    if hasattr(callable_, '__signature__'):
        # https://github.com/python/mypy/issues/1170
        new_ = callable_.__signature__.replace(  # type: ignore
            return_annotation=type,
        )
        callable_.__signature__ = new_  # type: ignore
    elif type is inspect.Signature.empty:
        callable_.__annotations__.pop('return', None)
    else:
        callable_.__annotations__['return'] = type


def get_var_positional_parameter(
        *parameters: TUnionParameter
    ) -> typing.Optional[TUnionParameter]:
    for param in parameters:
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            return param
    return None


def get_var_keyword_parameter(
        *parameters: TUnionParameter
    ) -> typing.Optional[TUnionParameter]:
    for param in parameters:
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return param
    return None


def stringify_parameters(*parameters: TUnionParameter) -> str:
    if not parameters:
        return ''

    has_positional = parameters[0].kind is POSITIONAL_ONLY
    has_var_positional = get_var_positional_parameter(*parameters)

    components = []
    for i, param in enumerate(parameters):
        last_ = parameters[i - 1] if (i > 0) else None
        next_ = parameters[i + 1] if (len(parameters) > i + 1) else None

        if (
                not has_var_positional and
                parameters[i].kind is KEYWORD_ONLY and
                (not last_ or last_.kind is not KEYWORD_ONLY)
            ):
            components.append('*')

        components.append(str(param))
        if (
                has_positional and
                parameters[i].kind is POSITIONAL_ONLY and
                (
                    not next_ or
                    next_.kind is not POSITIONAL_ONLY)
            ):
            components.append('/')

    return ', '.join(components)