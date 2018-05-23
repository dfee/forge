import builtins
import inspect
import typing

from forge._exceptions import NoParameterError
from forge._marker import empty
from forge._parameter import FParameter


POSITIONAL_ONLY = inspect.Parameter.POSITIONAL_ONLY
POSITIONAL_OR_KEYWORD = inspect.Parameter.POSITIONAL_OR_KEYWORD
VAR_POSITIONAL = inspect.Parameter.VAR_POSITIONAL
KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY
VAR_KEYWORD = inspect.Parameter.VAR_KEYWORD


TGenericCallable = typing.Callable[..., typing.Any]
TUnionParameter = \
    typing.TypeVar('TUnionParameter', inspect.Parameter, FParameter)


def getparam(
        callable: typing.Callable[..., typing.Any],
        name: str,
        default: typing.Any = empty,
    ) -> inspect.Parameter:
    """
    Gets a parameter object (either a :class.`inspect.Parmater` or a
    :class:`~forge.FParameter`) by name from its respective
    :class:`inspect.Signature` or :class:`~forge.FSignature`

    :param callable: the callable whose signature will be inspected
    :param name: the name of the parameter to retrieve from the
        :paramref:`.getparam.callable` signature
    :param default: a default value to return if :paramref:`.getparam.name` is
        not found in the signature of :paramref:`.getparam.callable`.
    :raises TypeError: if :paramref:`.getparam.name` not found
    :return: the :class:`inspect.Parameter` or :class:`~forge.FParameter` object
        with :paramref:`.getparam.name` from :paramref:`.getparam.callable`, or
        :paramref:`.getparam.default` if not found.
    """
    # pylint: disable=W0622, redefined-builtin
    if not builtins.callable(callable):
        raise TypeError('{} is not callable'.format(callable))

    params = inspect.signature(callable).parameters
    if default is not empty:
        return params.get(name, default)
    try:
        return params[name]
    except KeyError:
        raise NoParameterError(
            "'{callable_name}' has no parameter '{param_name}'".format(
                callable_name=callable.__name__,
                param_name=name,
            )
        )


def hasparam(
        callable: TGenericCallable,
        name: str,
    ) -> bool:
    """
    Checks (by name) whether a parameter is taken by a callable.

    :param callable: a callable whose signature will be inspected
    :param name: the name of the paramter to identify in the
        :paramref:`.hasparam.callable` signature
    :return: True if :paramref:`hasparam.callable` has
        :paramref:`.hasparam.name` in its signature.
    """
    # pylint: disable=W0622, redefined-builtin
    if not builtins.callable(callable):
        raise TypeError('{} is not callable'.format(callable))
    return name in inspect.signature(callable).parameters


def get_return_type(callable: TGenericCallable) -> typing.Any:
    """
    A convenience for retrieving the ``return-type`` annotation from a callable

    :param callable: a callable whose ``return-type`` annotation is retrieved
    :return: the ``return-type`` annotation from
        :paramref:`.get_return_type.callable`
    """
    # pylint: disable=W0622, redefined-builtin
    return inspect.signature(callable).return_annotation


def set_return_type(
        callable: TGenericCallable,
        type: typing.Any,
    ) -> None:
    """
    Set the ``return-type`` annotation on a callable.

    :param callable: a callable whose ``return-type`` annotation will be set
    :param type: the annotation to set for :paramref:`.set_return_type.callable`
    """
    # pylint: disable=W0622, redefined-builtin
    if not builtins.callable(callable):
        raise TypeError('{} is not callable'.format(callable))
    if hasattr(callable, '__signature__'):
        # https://github.com/python/mypy/issues/1170
        new_ = callable.__signature__.replace(  # type: ignore
            return_annotation=type,
        )
        callable.__signature__ = new_  # type: ignore
    elif type is inspect.Signature.empty:
        callable.__annotations__.pop('return', None)
    else:
        callable.__annotations__['return'] = type


def get_var_positional_parameter(
        *parameters: TUnionParameter
    ) -> typing.Optional[TUnionParameter]:
    """
    Get the :term:`var-positional` :term:`parameter kind`
    :class:`inspect.Parameter` of :class:`~forge.FParameter`.
    If multiple :term:`var-positional` parameters are provided, only the first
    is returned.

    :param parameters: parameters to search for :term:`var-positional`
        :term:`parameter kind`.
    :return: the first :term:`var-positional` parameter from
        :paramref:`get_var_positional_paramters.parameters` if it exists,
        else ``None``.
    """
    for param in parameters:
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            return param
    return None


def get_var_keyword_parameter(
        *parameters: TUnionParameter
    ) -> typing.Optional[TUnionParameter]:
    """
    Get the :term:`var-keyword` :term:`parameter kind`
    :class:`inspect.Parameter` of :class:`~forge.FParameter`.
    If multiple :term:`var-keyword` parameters are provided, only the first
    is returned.

    :param parameters: parameters to search for :term:`var-keyword`
        :term:`parameter kind`.
    :return: the first :term:`var-keyword` parameter from
        :paramref:`get_var_keyword_paramters.parameters` if it exists,
        else ``None``.
    """
    for param in parameters:
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return param
    return None


def stringify_parameters(*parameters: TUnionParameter) -> str:
    """
    Builds a string representation of the provided parameters for use in
    pretty-printing a signature. Includes markers ``/`` and ``*`` to distinguish
    parameters based on :term:`parameter kind`, as well as the ``type-hint``
    annotation and ``default`` value for a parameter (if provided).

    :param parameters: parameters to render to string
    :return: a string with parameters separated by ``,``
    """
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


def stringify_callable(callable: typing.Callable) -> str:
    """
    Build a string representation of a callable, including the callable's
    :attr:``__name__``, its :class:`inspect.Parameter`s and its ``return type``

    usage::

        >>> stringify_callable(stringify_callable)
        'stringify_callable(callable: Callable) -> str'

    :param callable: a Python callable to build a string representation of
    :return: the string representation of the function
    """
    # pylint: disable=W0622, redefined-builtin
    sig = inspect.signature(callable)
    rtype = ''
    if sig.return_annotation is not empty.native:
        rtype = ' -> {}'.format(
            sig.return_annotation.__name__ \
            if inspect.isclass(sig.return_annotation) \
            else str(sig.return_annotation)
        )

    return '{name}({params}){rtype}'.format(
        name=getattr(callable, '__name__', str(callable)),
        params=stringify_parameters(*sig.parameters.values()),
        rtype=rtype,
    )