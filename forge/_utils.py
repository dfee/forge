import builtins
import inspect
import types
import typing

from forge._exceptions import NoParameterError
import forge._immutable as immutable
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


class CallArguments(immutable.Immutable):
    """
    An immutable container for call arguments, i.e. term:`var-positional`
    (e.g. ``*args``) and :term:`var-keyword` (e.g. ``**kwargs``).

    :param args: positional arguments used in a call
    :param kwargs: keyword arguments used in a call
    """
    __slots__ = ('args', 'kwargs')

    def __init__(
            self,
            *args: typing.Any,
            **kwargs: typing.Any
        ) -> None:
        super().__init__(args=args, kwargs=types.MappingProxyType(kwargs))

    def __repr__(self) -> str:
        arguments = ', '.join([
            *[repr(arg) for arg in self.args],
            *['{}={}'.format(k, v) for k, v in self.kwargs.items()],
        ])
        return '<{} ({})>'.format(type(self).__name__, arguments)

    @classmethod
    def from_bound_arguments(
            cls,
            bound: inspect.BoundArguments,
        ) -> 'CallArguments':
        """
        A factory method that creates an instance of
        :class:`~forge._signature.CallArguments` from an instance of
        :class:`instance.BoundArguments` generated from
        :meth:`inspect.Signature.bind` or :meth:`inspect.Signature.bind_partial`

        :param bound: an instance of :class:`inspect.BoundArguments`
        :return: an unpacked version of :class:`inspect.BoundArguments`
        """
        return cls(*bound.args, **bound.kwargs)  # type: ignore

    def to_bound_arguments(
            self,
            signature: inspect.Signature,
            partial: bool = False,
        ) -> inspect.BoundArguments:
        """
        Generates an instance of :class:inspect.BoundArguments` for a given
        :class:`inspect.Signature`.
        Does not raise if invalid or incomplete arguments are provided, as the
        underlying implementation uses :meth:`inspect.Signature.bind_partial`.

        :param signature: an instance of :class:`inspect.Signature` to which
            :paramref:`.CallArguments.args` and
            :paramref:`.CallArguments.kwargs` will be bound.
        :param partial: does not raise if invalid or incomplete arguments are
            provided, as the underlying implementation uses
            :meth:`inspect.Signature.bind_partial`
        :return: an instance of :class:`inspect.BoundArguments` to which
            :paramref:`.CallArguments.args` and
            :paramref:`.CallArguments.kwargs` are bound.
        """
        return signature.bind_partial(*self.args, **self.kwargs) \
            if partial \
            else signature.bind(*self.args, **self.kwargs)



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


def sort_arguments(
        to_: typing.Union[typing.Callable[..., typing.Any], inspect.Signature],
        named: typing.Optional[typing.Dict[str, typing.Any]] = None,
        unnamed: typing.Optional[typing.Iterable] = None,
    ) -> CallArguments:
    """
    Iterates over the :paramref:`~forge.sort_arguments.named` arguments and
    assinging the values to the parameters with the key as a name.
    :paramref:`~forge.sort_arguments.unnamed` arguments are assigned to the
    :term:`var-positional` parameter.

    Usage:

    .. testcode::

        import forge

        def func(a, b=2, *args, c, d=5, **kwargs):
            return (a, b, args, c, d, kwargs)

        assert forge.callwith(
            func,
            named=dict(a=1, c=4, e=6),
            unnamed=(3,),
        ) == forge.CallArguments(1, 2, 3, c=4, d=5, e=6)

    .. versionadded:: v18.5.1

    :param to_: a callable to call with the named and unnamed parameters
    :param named: a mapping of parameter names to argument values.
        Appropriate values are all :term:`positional-only`,
        :term:`positional-or-keyword`, and :term:`keyword-only` arguments,
        as well as additional :term:`var-keyword` mapped arguments which will
        be used to construct the :term:`var-positional` argument on
        :paramref:`~forge.callwith.to_` (if it has such an argument).
        Parameters on :paramref:`~forge.callwith.to_` with default values can
        be ommitted (as expected).
    :param unnamed: an iterable to be passed as the :term:`var-positional`
        parameter. Requires :paramref:`~forge.callwith.to_` to accept
        :term:`var-positional` arguments.
    """
    if not isinstance(to_, inspect.Signature):
        to_ = inspect.signature(to_)
    to_ba = to_.bind_partial()
    to_ba.apply_defaults()

    arguments = named.copy() if named else {}

    vpo_param = get_var_positional_parameter(*to_.parameters.values())
    vkw_param = get_var_keyword_parameter(*to_.parameters.values())

    for name, param in to_.parameters.items():
        if param in (vpo_param, vkw_param):
            continue

        elif name in arguments:
            to_ba.arguments[name] = arguments.pop(name)
            continue

        elif param.default is empty.native:
            raise ValueError(
                "Non-default parameter '{}' has no argument value".format(name)
            )

    if arguments:
        if not vkw_param:
            raise TypeError('Cannot sort arguments ({})'.\
            format(', '.join(arguments.keys())))
        to_ba.arguments[vkw_param.name].update(arguments)

    if unnamed:
        if not vpo_param:
            raise TypeError("Cannot sort var-positional arguments")
        to_ba.arguments[vpo_param.name] = tuple(unnamed)

    return CallArguments.from_bound_arguments(to_ba)


def callwith(
        to_: typing.Callable[..., typing.Any],
        named: typing.Optional[typing.Dict[str, typing.Any]] = None,
        unnamed: typing.Optional[typing.Iterable] = None,
    ) -> typing.Any:
    """
    Calls and returns the result of :paramref:`~forge.callwith.to_` with the
    supplied ``named`` and ``unnamed`` arguments.

    The arguments and their order as supplied to
    :paramref:`~forge.callwith.to_` is determined by
    iterating over the :paramref:`~forge.callwith.named` arguments and
    assinging the values to the parameters with the key as a name.
    :paramref:`~forge.callwith.unnamed` arguments are assigned to the
    :term:`var-positional` parameter.

    Usage:

    .. testcode::

        import forge

        def func(a, b=2, *args, c, d=5, **kwargs):
            return (a, b, args, c, d, kwargs)

        assert forge.callwith(
            func,
            named=dict(a=1, c=4, e=6),
            unnamed=(3,),
        ) == (1, 2, (3,), 4, 5, {'e': 6})

    .. versionadded:: v18.5.1

    :param to_: a callable to call with the named and unnamed parameters
    :param named: a mapping of parameter names to argument values.
        Appropriate values are all :term:`positional-only`,
        :term:`positional-or-keyword`, and :term:`keyword-only` arguments,
        as well as additional :term:`var-keyword` mapped arguments which will
        be used to construct the :term:`var-positional` argument on
        :paramref:`~forge.callwith.to_` (if it has such an argument).
        Parameters on :paramref:`~forge.callwith.to_` with default values can
        be ommitted (as expected).
    :param unnamed: an iterable to be passed as the :term:`var-positional`
        parameter. Requires :paramref:`~forge.callwith.to_` to accept
        :term:`var-positional` arguments.
    """
    call_args = sort_arguments(to_, named, unnamed)
    return to_(*call_args.args, **call_args.kwargs)


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
    name = getattr(callable, '__name__', str(callable))
    return '{}{}'.format(name, sig)