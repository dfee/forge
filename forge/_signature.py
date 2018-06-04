import builtins
from collections import OrderedDict
import collections.abc
import functools
import inspect
import types
import typing

from forge._counter import CreationOrderMeta
from forge._exceptions import NoParameterError
import forge._immutable as immutable
from forge._marker import (
    empty,
    void,
)


## Parameter
POSITIONAL_ONLY = inspect.Parameter.POSITIONAL_ONLY
POSITIONAL_OR_KEYWORD = inspect.Parameter.POSITIONAL_OR_KEYWORD
VAR_POSITIONAL = inspect.Parameter.VAR_POSITIONAL
KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY
VAR_KEYWORD = inspect.Parameter.VAR_KEYWORD

_PARAMETER_KIND_STRINGS = {
    inspect.Parameter.POSITIONAL_ONLY: 'positional only',
    inspect.Parameter.POSITIONAL_OR_KEYWORD: 'positional or keyword',
    inspect.Parameter.VAR_POSITIONAL: 'variable positional',
    inspect.Parameter.KEYWORD_ONLY: 'keyword only',
    inspect.Parameter.VAR_KEYWORD: 'variable keyword',
}
_get_pk_string = _PARAMETER_KIND_STRINGS.__getitem__


class Factory(immutable.Immutable):
    # TODO: document
    __slots__ = ('factory',)

    def __init__(self, factory):
        # pylint: disable=C0102, blacklisted-name
        super().__init__(factory=factory)

    def __repr__(self):
        return '<{} {}>'.format(type(self).__name__, self.factory.__qualname__)

    def __call__(self):
        return self.factory()


# Common type hints for FParameter
_TYPE_FP_CTX_CALLABLE = typing.Callable[
    [typing.Any, str, typing.Any],
    typing.Any,
]
_TYPE_FP_KIND = inspect._ParameterKind # pylint: disable=C0103, invalid-name
_TYPE_FP_BOUND = bool # pylint: disable=C0103, invalid-name
_TYPE_FP_CONTEXTUAL = bool # pylint: disable=C0103, invalid-name
_TYPE_FP_NAME = typing.Optional[str]
_TYPE_FP_DEFAULT = typing.Any
_TYPE_FP_FACTORY = typing.Callable[[], typing.Any]
_TYPE_FP_TYPE = typing.Any
_TYPE_FP_CONVERTER = typing.Optional[
    typing.Union[
        _TYPE_FP_CTX_CALLABLE,
        typing.Iterable[_TYPE_FP_CTX_CALLABLE]
    ]
]
_TYPE_FP_VALIDATOR = typing.Optional[
    typing.Union[
        _TYPE_FP_CTX_CALLABLE,
        typing.Iterable[_TYPE_FP_CTX_CALLABLE]
    ]
]
_TYPE_FP_METADATA = typing.Mapping


class FParameter(immutable.Immutable, metaclass=CreationOrderMeta):
    """
    An immutable representation of a signature parameter that encompasses its
    public name, its interface name, transformations to be applied, and
    associated meta-data that defines its behavior in a signature.

    .. note::

        This class doesn't need to be invoked directly. Use one of the
        constructor methods instead:

        - :func:`~forge.pos` for :term:`positional-only` \
        :class:`~forge.FParameter`
        - :func:`~forge.pok` *or* :func:`~forge.arg` for \
        :term:`positional-or-keyword` :class:`~forge.FParameter`
        - :func:`~forge.vpo` for :term:`var-positional` \
        :class:`~forge.FParameter`
        - :func:`~forge.kwo` *or* :func:`~forge.kwarg` for \
        :term:`keyword-only` :class:`~forge.FParameter`
        - :func:`~forge.vkw` for :term:`var-keyword` :class:`~forge.FParameter`

    .. versionchanged:: 18.5.1 added :class:`~forge.empty`

    :param kind: the :term:`parameter kind`, which detemrines the position
        of the parameter in a callable signature.
    :param name: the public name of the parameter.
        For example, in :code:`f(x)` -> :code:`g(y)`, ``name`` is ``x``.
    :param interface_name: the name of mapped-to the parameter.
        For example, in :code:`f(x)` -> :code:`g(y)`,
        ``interface_name`` is ``y``.
    :param default: the default value for the parameter.
        Cannot be supplied alongside a ``factory`` argument.
        For example, to achieve :code:`f(x=3)`, specify :code`default=3`.
    :param factory: a function that generates a default for the parameter
        Cannot be supplied alongside a ``default`` argument.
        For example, to achieve :code:`f(x=<Factory now>)`,
        specify :code:`factory=default.now` (notice: without parentheses).
    :param type: the type annotation of the parameter.
        For example, to achieve :code:`f(x: int)`, ``type`` is ``int``.
    :param converter: a callable or iterable of callables that receive a
        ``ctx`` argument, a ``name`` argument and a ``value`` argument
        for transforming inputs.
    :param validator: a callable that receives a ``ctx`` argument,
        a ``name`` argument and a ``value`` argument for validating inputs.
    :param bound: whether the parameter is visible in the signature
        (requires ``default`` or ``factory`` if True)
    :param contextual: whether the parameter will be passed to
        ``converter`` and ``validator`` callables as the context
        (only the first parameter in a :class:`~forge.FSignature` can be
        contextual)
    :param metadata: optional, extra meta-data that describes the parameter

    :cvar empty: :class:`~forge.empty`
    :cvar POSITIONAL_ONLY: :attr:`inspect.Parameter.POSITIONAL_ONLY`
    :cvar POSITIONAL_OR_KEYWORD: :attr:`inspect.Parameter.POSITIONAL_OR_KEYWORD`
    :cvar VAR_POSITIONAL: :attr:`inspect.Parameter.VAR_POSITIONAL`
    :cvar KEYWORD_ONLY: :attr:`inspect.Parameter.KEYWORD_ONLY`
    :cvar VAR_KEYWORD: :attr:`inspect.Parameter.VAR_KEYWORD`
    """

    __slots__ = (
        '_creation_order',
        'kind',
        'name',
        'interface_name',
        'default',
        'type',
        'converter',
        'validator',
        'bound',
        'contextual',
        'metadata',
    )

    empty = empty
    POSITIONAL_ONLY = POSITIONAL_ONLY
    POSITIONAL_OR_KEYWORD = POSITIONAL_OR_KEYWORD
    VAR_POSITIONAL = VAR_POSITIONAL
    KEYWORD_ONLY = KEYWORD_ONLY
    VAR_KEYWORD = VAR_KEYWORD

    def __init__(
            self,
            kind: _TYPE_FP_KIND,
            name: _TYPE_FP_NAME = None,
            interface_name: _TYPE_FP_NAME = None,
            default: _TYPE_FP_DEFAULT = empty,
            factory: _TYPE_FP_FACTORY = empty,
            type: _TYPE_FP_TYPE = empty,
            converter: _TYPE_FP_CONVERTER = None,
            validator: _TYPE_FP_VALIDATOR = None,
            bound: _TYPE_FP_BOUND = False,
            contextual: _TYPE_FP_CONTEXTUAL = False,
            metadata: typing.Optional[_TYPE_FP_METADATA] = None
        ) -> None:
        # pylint: disable=W0622, redefined-builtin
        # pylint: disable=R0913, too-many-arguments
        if factory is not empty:
            if default is not empty:
                raise TypeError(
                    'expected either "default" or "factory", received both'
                )
            default = Factory(factory)

        if bound and default is empty:
            raise TypeError('bound arguments must have a default value')

        super().__init__(
            kind=kind,
            name=name or interface_name,
            interface_name=interface_name or name,
            default=default,
            type=type,
            converter=converter,
            validator=validator,
            contextual=contextual,
            bound=bound,
            metadata=types.MappingProxyType(metadata or {}),
        )

    def __str__(self) -> str:
        """
        Generates a string representation of the :class:`~forge.FParameter`
        """
        if self.kind == self.VAR_POSITIONAL:
            prefix = '*'
        elif self.kind == self.VAR_KEYWORD:
            prefix = '**'
        else:
            prefix = ''

        mapped = \
            '{prefix}{name}'.format(
                prefix=prefix,
                name=self.name or '<missing>',
            ) if self.name == self.interface_name \
            else '{prefix}{name}->{prefix}{interface_name}'.format(
                prefix=prefix,
                name=self.name or '<missing>',
                interface_name=self.interface_name or '<missing>',
            )

        annotated = mapped \
            if self.type is empty \
            else '{mapped}:{annotation}'.format(
                mapped=mapped,
                annotation=self.type.__name__ \
                    if inspect.isclass(self.type) \
                    else str(self.type),
            )

        return annotated \
            if self.default is empty \
            else '{annotated}={default}'.format(
                annotated=annotated,
                default=self.default,
            )

    def __repr__(self) -> str:
        return '<{} "{}">'.format(type(self).__name__, str(self))

    def apply_default(self, value: typing.Any) -> typing.Any:
        """
        Return the argument value (if not :class:`~forge.empty`), or the value
        from :paramref:`~forge.FParmeter.default` (if not an instance of
        :class:`~forge.Factory`), or the value obtained by calling
        :paramref:`~forge.FParameter.default` (if an instance of
        :class:`~forge.Factory`).

        :param value: the argument value for this parameter
        :return: the input value or a default value
        """
        if value is not empty:
            return value() if isinstance(value, Factory) else value
        return self.default

    def apply_conversion(
            self,
            ctx: typing.Any,
            value: typing.Any,
        ) -> typing.Any:
        """
        Apply a transform or series of transforms against the argument value
        with the callables from :paramref:`~forge.FParameter.converter`.

        :param ctx: the context of this parameter as provided by the
            :class:`~forge.FSignature` (typically self or ctx).
        :param value: the argument value for this parameter
        :return: the converted value
        """
        # pylint: disable=W0621, redefined-outer-name
        if self.converter is None:
            return value
        elif isinstance(self.converter, typing.Iterable):
            return functools.reduce(
                lambda val, func: func(ctx, self.name, val),
                [value, *self.converter],
            )
        return self.converter(ctx, self.name, value)

    def apply_validation(
            self,
            ctx: typing.Any,
            value: typing.Any,
        ) -> typing.Any:
        """
        Apply a validation or series of validations against the argument value
        with the callables from :paramref:`~forge.FParameter.validator`.

        :param ctx: the context of this parameter as provided by the
            :class:`~forge.FSignature` (typically self or ctx).
        :param value: the value the user has supplied or a default value
        :return: the (unchanged) validated value
        """
        # pylint: disable=W0621, redefined-outer-name
        if isinstance(self.validator, typing.Iterable):
            for validate in self.validator:
                validate(ctx, self.name, value)
        elif self.validator is not None:
            self.validator(ctx, self.name, value)
        return value

    def __call__(
            self,
            ctx: typing.Any,
            value: typing.Any
        ) -> typing.Any:
        """
        Can be called after defaults have been applied (if not a ``bound``
        :class:`~forge.FParameter`) or without a value (i.e.
        :class:`inspect.Parameter.emtpy`) in the case of a ``bound``
        :class:`~forge.FParameter`.

        Process:

        - conditionally apply the :class:`~forge.Factory`,
        - convert the resulting value with the \
        :paramref:`~forge.FParameter.converter`, and then
        - validate the resulting value with the \
        :forge:`~forge.FParameter.validator`.

        :param ctx: the context of this parameter as provided by the
            :class:`~forge.FSignature` (typically self or ctx).
        :param value: the user-supplied (or default) value
        """
        # pylint: disable=W0621, redefined-outer-name
        defaulted = self.apply_default(value)
        converted = self.apply_conversion(ctx, defaulted)
        return self.apply_validation(ctx, converted)

    @property
    def native(self) -> inspect.Parameter:
        """
        A native representation of this :class:`~forge.FParameter` as an
        :class:`inspect.Parameter`, fit for an instance of
        :class:`inspect.Signature`
        """
        if not self.name:
            raise TypeError('Cannot generate an unnamed parameter')
        return inspect.Parameter(
            name=self.name,
            kind=self.kind,
            default=empty.ccoerce_native(self.default),
            annotation=empty.ccoerce_native(self.type),
        )

    def replace(
            self,
            *,
            kind=void,
            name=void,
            interface_name=void,
            default=void,
            factory=void,
            type=void,
            converter=void,
            validator=void,
            bound=void,
            contextual=void,
            metadata=void
        ):
        """
        An evolution method that generates a new :class:`~forge.FParameter`
        derived from this instance and the provided updates.

        :param kind: see :paramref:`~forge.FParameter.kind`
        :param name: see :paramref:`~forge.FParameter.name`
        :param interface_name: see :paramref:`~forge.FParameter.interface_name`
        :param default: see :paramref:`~forge.FParameter.default`
        :param factory: see :paramref:`~forge.FParameter.factory`
        :param type: see :paramref:`~forge.FParameter.type`
        :param converter: see :paramref:`~forge.FParameter.converter`
        :param validator: see :paramref:`~forge.FParameter.validator`
        :param bound: see :paramref:`~forge.FParameter.bound`
        :param contextual: see :paramref:`~forge.FParameter.contextual`
        :param metadata: see :paramref:`~forge.FParameter.metadata`
        :return: an instance of `~forge.FParameter`
        """
        # pylint: disable=E1120, no-value-for-parameter
        # pylint: disable=W0622, redefined-builtin
        # pylint: disable=R0913, too-many-arguments
        if factory is not void and default is void:
            default = empty

        return immutable.replace(self, **{
            k: v for k, v in {
                'kind': kind,
                'name': name,
                'interface_name': interface_name,
                'default': default,
                'factory': factory,
                'type': type,
                'converter': converter,
                'validator': validator,
                'bound': bound,
                'contextual': contextual,
                'metadata': metadata,
            }.items() if v is not void
        })

    @classmethod
    def from_native(cls, native: inspect.Parameter) -> 'FParameter':
        """
        A factory method for creating :class:`~forge.FParameter` instances from
        :class:`inspect.Parameter` instances.

        Parameter descriptions are a subset of those defined on
        :class:`~forge.FParameter`

        :param native: an instance of :class:`inspect.Parameter`, used as a
            template for creating a new :class:`~forge.FParameter`
        :return: a new instance of :class:`~forge.FParameter`, using
            :paramref:`~forge.FParameter.from_native.native` as a template
        """
        return cls(  # type: ignore
            kind=native.kind,
            name=native.name,
            interface_name=native.name,
            default=cls.empty.ccoerce_synthetic(native.default),
            type=cls.empty.ccoerce_synthetic(native.annotation),
        )

    @classmethod
    def create_positional_only(
            cls,
            name=None,
            interface_name=None,
            *,
            default=empty,
            factory=empty,
            type=empty,
            converter=None,
            validator=None,
            bound=False,
            metadata=None
        ) -> 'FParameter':
        """
        A factory method for creating :term:`positional-only`
        :class:`~forge.FParameter` instances.

        :param name: see :paramref:`~forge.FParameter.name`
        :param interface_name: see :paramref:`~forge.FParameter.interface_name`
        :param default: see :paramref:`~forge.FParameter.default`
        :param factory: see :paramref:`~forge.FParameter.factory`
        :param type: see :paramref:`~forge.FParameter.type`
        :param converter: see :paramref:`~forge.FParameter.converter`
        :param validator: see :paramref:`~forge.FParameter.validator`
        :param bound: see :paramref:`~forge.FParameter.bound`
        :param metadata: see :paramref:`~forge.FParameter.metadata`
        """
        # pylint: disable=W0622, redefined-builtin
        return cls(  # type: ignore
            kind=cls.POSITIONAL_ONLY,
            name=name,
            interface_name=interface_name,
            default=default,
            factory=factory,
            type=type,
            converter=converter,
            validator=validator,
            bound=bound,
            metadata=metadata,
        )

    @classmethod
    def create_positional_or_keyword(
            cls,
            name=None,
            interface_name=None,
            *,
            default=empty,
            factory=empty,
            type=empty,
            converter=None,
            validator=None,
            bound=False,
            metadata=None
        ) -> 'FParameter':
        """
        A factory method for creating :term:`positional-or-keyword`
        :class:`~forge.FParameter` instances.

        :param name: see :paramref:`~forge.FParameter.name`
        :param interface_name: see :paramref:`~forge.FParameter.interface_name`
        :param default: see :paramref:`~forge.FParameter.default`
        :param factory: see :paramref:`~forge.FParameter.factory`
        :param type: see :paramref:`~forge.FParameter.type`
        :param converter: see :paramref:`~forge.FParameter.converter`
        :param validator: see :paramref:`~forge.FParameter.validator`
        :param bound: see :paramref:`~forge.FParameter.bound`
        :param metadata: see :paramref:`~forge.FParameter.metadata`
        """
        # pylint: disable=W0622, redefined-builtin
        return cls(  # type: ignore
            kind=cls.POSITIONAL_OR_KEYWORD,
            name=name,
            interface_name=interface_name,
            default=default,
            factory=factory,
            type=type,
            converter=converter,
            validator=validator,
            bound=bound,
            metadata=metadata,
        )

    @classmethod
    def create_contextual(
            cls,
            name=None,
            interface_name=None,
            *,
            type=empty,
            metadata=None
        ) -> 'FParameter':
        """
        A factory method for creating :term:`positional-or-keyword`
        :class:`~forge.FParameter` instances that are ``contextual`` (this value
        is passed to other :class:`~forge.FParameter`s ``converter`` and
        ``validator`` functions.)

        :param name: see :paramref:`~forge.FParameter.name`
        :param interface_name: see :paramref:`~forge.FParameter.interface_name`
        :param type: see :paramref:`~forge.FParameter.type`
        :param metadata: see :paramref:`~forge.FParameter.metadata`
        """
        # pylint: disable=W0622, redefined-builtin
        return cls(  # type: ignore
            kind=cls.POSITIONAL_OR_KEYWORD,
            name=name,
            interface_name=interface_name,
            type=type,
            contextual=True,
            metadata=metadata,
        )

    @classmethod
    def create_var_positional(
            cls,
            name,
            *,
            converter=None,
            validator=None,
            metadata=None
        ) -> 'FParameter':
        """
        A factory method for creating :term:`var-positional`
        :class:`~forge.FParameter` instances.

        :param name: see :paramref:`~forge.FParameter.name`
        :param converter: see :paramref:`~forge.FParameter.converter`
        :param validator: see :paramref:`~forge.FParameter.validator`
        :param metadata: see :paramref:`~forge.FParameter.metadata`
        """
        # pylint: disable=W0622, redefined-builtin
        return cls(  # type: ignore
            kind=cls.VAR_POSITIONAL,
            name=name,
            converter=converter,
            validator=validator,
            metadata=metadata,
        )

    @classmethod
    def create_keyword_only(
            cls,
            name=None,
            interface_name=None,
            *,
            default=empty,
            factory=empty,
            type=empty,
            converter=None,
            validator=None,
            bound=False,
            metadata=None
        ) -> 'FParameter':
        """
        A factory method for creating :term:`keyword-only`
        :class:`~forge.FParameter` instances.

        :param name: see :paramref:`~forge.FParameter.name`
        :param interface_name: see :paramref:`~forge.FParameter.interface_name`
        :param default: see :paramref:`~forge.FParameter.default`
        :param factory: see :paramref:`~forge.FParameter.factory`
        :param type: see :paramref:`~forge.FParameter.type`
        :param converter: see :paramref:`~forge.FParameter.converter`
        :param validator: see :paramref:`~forge.FParameter.validator`
        :param bound: see :paramref:`~forge.FParameter.bound`
        :param metadata: see :paramref:`~forge.FParameter.metadata`
        """
        # pylint: disable=W0622, redefined-builtin
        return cls(  # type: ignore
            kind=cls.KEYWORD_ONLY,
            name=name,
            interface_name=interface_name,
            default=default,
            factory=factory,
            type=type,
            converter=converter,
            validator=validator,
            bound=bound,
            metadata=metadata,
        )

    @classmethod
    def create_var_keyword(
            cls,
            name,
            *,
            converter=None,
            validator=None,
            metadata=None
        ) -> 'FParameter':
        """
        A factory method for creating :term:`var-keyword`
        :class:`~forge.FParameter` instances.

        :param name: see :paramref:`~forge.FParameter.name`
        :param converter: see :paramref:`~forge.FParameter.converter`
        :param validator: see :paramref:`~forge.FParameter.validator`
        :param metadata: see :paramref:`~forge.FParameter.metadata`
        """
        # pylint: disable=W0622, redefined-builtin
        return cls(  # type: ignore
            kind=cls.VAR_KEYWORD,
            name=name,
            converter=converter,
            validator=validator,
            metadata=metadata,
        )


class VarPositional(collections.abc.Iterable):
    """
    A convenience class that generates an iterable consisting of one
    :class:`~forge.FParameter` of :term:`parameter kind` :term:`var-positional`.

    Instances can be used as either ``*args`` or ``*args()``.

    Typical usage::

        >>> import forge
        >>> fsig = forge.FSignature(*forge.args)
        >>> print(fsig)
        <FSignature (*args)>

        >>> import forge
        >>> fsig = forge.FSignature(*forge.args(name='vars'))
        >>> print(fsig)
        <FSignature (*vars)>

    While ``name`` can be supplied (by default it's ``args``),
    ``interface_name`` is unavailable.
    This is because when :class:`~forge.FSignature` maps parameters, the mapping
    between :term:`var-positional` parameters is 1:1, so the interface name for
    :term:`var-positional` is auto-discovered.

    Implements :class:`collections.abc.Iterable`, with provided: ``__iter__``.
    Inherits method: ``__next__``.

    :param name: see :paramref:`~forge.FParameter.name`
    :param converter: see :paramref:`~forge.FParameter.converter`
    :param validator: see :paramref:`~forge.FParameter.validator`
    :param metadata: see :paramref:`~forge.FParameter.metadata`
    """
    _default_name = 'args'

    def __init__(
            self,
            name: _TYPE_FP_NAME = None,
            *,
            converter: _TYPE_FP_CONVERTER = None,
            validator: _TYPE_FP_VALIDATOR = None,
            metadata: typing.Optional[_TYPE_FP_METADATA] = None
        ) -> None:
        self.name = name or self._default_name
        self.converter = converter
        self.validator = validator
        self.metadata = metadata

    @property
    def fparameter(self) -> FParameter:
        """
        :return: a representation of this
            :class:`~forge._parameter.VarPositional` as a
            :class:`~forge.FParameter` of :term:`parameter kind`
            :term:`var-positional`, with attributes ``name``, ``converter``,
            ``validator`` and ``metadata`` from the instance.
        """
        # pylint: disable=E1101, no-member
        return FParameter.create_var_positional(
            name=self.name,
            converter=self.converter,
            validator=self.validator,
            metadata=self.metadata,
        )

    def __iter__(self) -> typing.Iterator:
        """
        Concrete method for :class:`collections.abc.Iterable`

        :return: an iterable consisting of one item: the representation of this
            :class:`~forge._parameter.VarPositional` as a
            :class:`~forge.FParameter` via
            :attr:`~forge._parameter.VarPositional.fparameter`.
        """
        return iter((self.fparameter,))

    def __call__(
            self,
            name: _TYPE_FP_NAME = None,
            *,
            converter: _TYPE_FP_CONVERTER = None,
            validator: _TYPE_FP_VALIDATOR = None,
            metadata: typing.Optional[_TYPE_FP_METADATA] = None
        ) -> 'VarPositional':
        """
        A factory method which creates a new
        :class:`~forge._parameter.VarPositional` instance.
        Convenient for use like::

            *args(converter=lambda ctx, name, value: value[::-1])

        :param name: see :paramref:`~forge.FParameter.name`
        :param converter: see :paramref:`~forge.FParameter.converter`
        :param validator: see :paramref:`~forge.FParameter.validator`
        :param metadata: see :paramref:`~forge.FParameter.metadata`
        :return: a new instance of :class:`~forge._parameter.VarPositional`
        """
        return type(self)(
            name=name,
            converter=converter,
            validator=validator,
            metadata=metadata,
        )


class VarKeyword(collections.abc.Mapping):
    """
    A convenience class that generates an iterable consisting of a mapping
    of ``name`` to a :class:`~forge.FParameter` of :term:`parameter kind`
    :term:`var-keyword`.

    Instances can be used as either ``**kwargs`` or ``**kwargs()``.

    Typical usage::

        >>> import forge
        >>> fsig = forge.FSignature(**forge.kwargs)
        >>> print(fsig)
        <FSignature (**kwargs)>

        >>> import forge
        >>> fsig = forge.FSignature(**forge.kwargs(name='items'))
        >>> print(fsig)
        <FSignature (**items)>

    While ``name`` can be supplied (by default it's ``kwargs``),
    ``interface_name`` is unavailable.
    This is because when :class:`~forge.FSignature` maps parameters, the mapping
    between :term:`var-keyword` parameters is 1:1, so the interface name for
    :term:`var-keyword` is auto-discovered.

    Implements :class:`collections.abc.Mapping`, with provided: ``__getitem__``,
    ``__iter__`` and ``__len__``. Inherits methods: ``__contains__``, ``keys``,
    ``items``, ``values``, ``get``, ``__eq__`` and ``__ne__``.

    :param name: see :paramref:`~forge.FParameter.name`
    :param converter: see :paramref:`~forge.FParameter.converter`
    :param validator: see :paramref:`~forge.FParameter.validator`
    :param metadata: see :paramref:`~forge.FParameter.metadata`
    """
    _default_name = 'kwargs'

    def __init__(
            self,
            name: _TYPE_FP_NAME = None,
            *,
            converter: _TYPE_FP_CONVERTER = None,
            validator: _TYPE_FP_VALIDATOR = None,
            metadata: typing.Optional[_TYPE_FP_METADATA] = None
        ) -> None:
        self.name = name or self._default_name
        self.converter = converter
        self.validator = validator
        self.metadata = metadata

    @property
    def fparameter(self) -> FParameter:
        """
        :return: a representation of this :class:`~forge._parameter.VarKeyword`
            as a :class:`~forge.FParameter` of :term:`parameter kind`
            :term:`var-keyword`, with attributes ``name``, ``converter``,
            ``validator`` and ``metadata`` from the instance.
        """
        # pylint: disable=E1101, no-member
        return FParameter.create_var_keyword(
            name=self.name,
            converter=self.converter,
            validator=self.validator,
            metadata=self.metadata,
        )

    def __getitem__(self, key: str) -> FParameter:
        """
        Concrete method for :class:`collections.abc.Mapping`

        :key: only retrieves for :paramref:`.VarKeyword.name`
        :raise: KeyError (if ``key`` is not
            :paramref:`~forge._parameter.VarKeyword.name`)
        :return: an representation of this :class:`~forge._parameter.VarKeyword`
            as a :class:`~forge.FParameter` via
            :attr:`~forge._parameter.VarKeyword.fparameter`.
        """
        if self.name == key:
            return self.fparameter
        raise KeyError(key)

    def __iter__(self) -> typing.Iterator[str]:
        """
        Concrete method for :class:`collections.abc.Mapping`

        :return: an iterable consisting of one item: the representation of this
            :class:`~forge._parameter.VarKeyword` as a
            :class:`~forge.FParameter` via
            :attr:`~forge._parameter.VarKeyword.fparameter`.
        """
        return iter({self.name: self.fparameter})

    def __len__(self) -> int:
        """
        Concrete method for :class:`collections.abc.Mapping`

        :return: 1
        """
        return 1

    def __call__(
            self,
            name: _TYPE_FP_NAME = None,
            *,
            converter: _TYPE_FP_CONVERTER = None,
            validator: _TYPE_FP_VALIDATOR = None,
            metadata: typing.Optional[_TYPE_FP_METADATA] = None
        ) -> 'VarKeyword':
        """
        A factory method which creates a new
        :class:`~forge._parameter.VarKeyword` instance.
        Convenient for use like::

            **kwargs(
                converter=lambda ctx, name, value:
                    {'_' + k: v for k, v in value.items()},
            )

        :param name: see :paramref:`~forge.FParameter.name`
        :param converter: see :paramref:`~forge.FParameter.converter`
        :param validator: see :paramref:`~forge.FParameter.validator`
        :param metadata: see :paramref:`~forge.FParameter.metadata`
        :return: a new instance of :class:`~forge._parameter.VarKeyword`
        """
        return type(self)(
            name=name,
            converter=converter,
            validator=validator,
            metadata=metadata,
        )


# Common type hints for FParameterMap
_TYPE_FPM_PARAMETERS = typing.Optional[
    typing.Union[
        typing.List[FParameter],
        typing.Tuple[FParameter, ...],
    ]
]
_TYPE_FPM_VALIDATE = bool  # pylint: disable=C0103, invalid-name


class FParameterMap(collections.abc.Mapping):
    # TODO: document
    # TODO: move to parameters
    def __init__(
            self,
            parameters: _TYPE_FPM_PARAMETERS = None,
            validate: _TYPE_FPM_VALIDATE = True,
        ) -> None:
        parameters = parameters or []
        if validate:
            self.validate(*parameters)
        self._data = OrderedDict([(param.name, param) for param in parameters])

    def __getitem__(
            self,
            key: typing.Union[str, slice],
        ) -> typing.Union[FParameter, typing.List[FParameter]]:
        """
        Concrete method for :class:`collections.abc.Mapping`

        :param key: a key that corresponds to a
            :paramref:`~forge.FParameter.name`, or an instance of
            :class:`slice`, with ``start`` and ``stop`` being valid
            :paramref:`~forge.FParameter.name`. Note that unlike list slices,
            *both* the start and stop are included when present in the
            :class:`~forge.FSignature`.
        :raises KeyError: if an instance of :class:`~forge.FParameter` with
            :paramref:`~forge.FParameter.name` doesn't exist on this
            :class:`~forge.FSignature`.
        :return: the instance of :class:`~forge.FParameter.name` for which
            :paramref:`~forge.FSignature.__getitem__.key` corresponds.
        """
        if isinstance(key, slice):
            params = []
            visited_start = not bool(key.start)
            for name, param in self.items():
                if name == key.stop:
                    params.append(param)
                    break
                elif visited_start:
                    params.append(param)
                elif name == key.start:
                    visited_start = True
                    params.append(param)
            return params
        return self._data[key]

    def __iter__(self) -> typing.Iterator:
        """
        Concrete method for :class:`collections.abc.Mapping`

        :return: an iterator over this instance which maps
            :paramref:`~forge.FParameter.name` to a :class:`~forge.FParameter`.
        """
        return iter(self._data)

    def __len__(self) -> int:
        """
        Concrete method for :class:`collections.abc.Mapping`

        :return: the number of parameters in this :class:`~forge.FSignature`
            instance.
        """
        return len(self._data)

    def __str__(self):
        # TODO: test
        sig = inspect.Signature(
            [fp.native for fp in self.values()],
            __validate_parameters__=False,
        )
        return str(sig)

    def __repr__(self):
        # TODO: test
        return '<{} {}>'.format(type(self).__name__, str(self))

    @classmethod
    def validate(cls, *parameters: FParameter) -> None:
        # pylint: disable=R0912, too-many-branches
        name_set = set()  # type: typing.Set[str]
        iname_set = set()  # type: typing.Set[str]
        for i, current in enumerate(parameters):
            if not isinstance(current, FParameter):
                raise TypeError(
                    "Received non-FParameter '{}'".\
                    format(current)
                )
            elif not (current.name and current.interface_name):
                raise ValueError(
                    "Received unnamed parameter: '{}'".\
                    format(current)
                )
            elif current.contextual:
                if i > 0:
                    raise TypeError(
                        'Only the first parameter can be contextual'
                    )

            if current.name in name_set:
                raise ValueError(
                    "Received multiple parameters with name '{}'".\
                    format(current.name)
                )
            name_set.add(current.name)

            if current.interface_name in iname_set:
                raise ValueError(
                    "Received multiple parameters with interface_name '{}'".\
                    format(current.interface_name)
                )
            iname_set.add(current.interface_name)

            last = parameters[i-1] if i > 0 else None
            if not last:
                continue

            elif current.kind < last.kind:
                raise SyntaxError(
                    "{current} of kind '{current.kind.name}' follows "
                    "{last} of kind '{last.kind.name}'".\
                    format(current=current, last=last)
                )
            elif current.kind is last.kind:
                if current.kind is FParameter.VAR_POSITIONAL:
                    raise TypeError(
                        'Received multiple variable-positional parameters'
                    )
                elif current.kind is FParameter.VAR_KEYWORD:
                    raise TypeError(
                        'Received multiple variable-keyword parameters'
                    )
                elif current.kind in (
                        FParameter.POSITIONAL_ONLY,
                        FParameter.POSITIONAL_OR_KEYWORD
                    ) \
                    and last.default is not empty \
                    and current.default is empty:
                    raise SyntaxError(
                        'non-default parameter follows default parameter'
                    )


def getparam(
        callable: typing.Callable[..., typing.Any],
        name: str,
        default: typing.Any = empty,
    ) -> inspect.Parameter:
    """
    Gets a parameter object (either a :class.`inspect.Parameter` or a
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


def hasparam(callable: typing.Callable[..., typing.Any], name: str) -> bool:
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
        *parameters: typing.Union[inspect.Parameter, FParameter],
    ) -> typing.Optional[typing.Union[inspect.Parameter, FParameter]]:
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
        *parameters: typing.Union[inspect.Parameter, FParameter],
    ) -> typing.Optional[typing.Union[inspect.Parameter, FParameter]]:
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


class FSignature(immutable.Immutable):
    """
    An immutable, validated representation of a signature composed of
    :class:`~forge.FParameter` instances.

    Validation ensures:

    - the appropriate order of parameters by kind:

        #. (optional) :term:`positional-only`, followed by
        #. (optional) :term:`positional-or-keyword`, followed by
        #. (optional) :term:`var-positional`, followed by
        #. (optional) :term:`keyword-only`, followed by
        #. (optional) :term:`var-keyword`

    - that non-default :term:`positional-only` or
        :term:`positional-or-keyword` parameters don't follow their respective
        similarly-kinded parameters with defaults,

        .. note::

            Python signatures allow non-default :term:`keyword-only` parameters
            to follow default :term:`keyword-only` parameters.

    - that at most there is one :term:`var-positional` parameter,

    - that at most there is one :term:`var-keyword` parameter,

    - that at most there is one ``context`` parameter, and that it
        is the first parameter (if it is provided.)

    - that no two instances of :class:`~forge.FParameter` share the same
        :paramref:`~forge.FParameter.name` or
        :paramref:`~forge.FParameter.interface_name`.

    .. note::

        This class usually doesn't usually need to be invoked directly.
        Consider using one of the constructor methods instead:

        - :func:`~forge.sign` to wrap a callable with a \
        :class:`~forge.FSignature`.
        - :func:`~forge.resign` to revise a wrapped callable's \
        :class:`~forge.FSignature`.
        - :func:`~forge.FSignature.from_callable` to generate a \
        :class:`~forge.FSignature` from any Python callable.
        - :func:`~forge.FSignature.from_signature` to generate a \
        :class:`~forge.FSignature` from a :class:`inspect.Signature`.

    Implements :class:`collections.abc.Mapping`, with provided: ``__getitem__``,
    ``__iter__`` and ``__len__``. Inherits methods: ``__contains__``, ``keys``,
    ``items``, ``values``, ``get``, ``__eq__`` and ``__ne__``.

    :param parameters: an ordered list or tuple of :class:`~forge.FParameter`
        instances.
    """
    # pylint: disable=R0901, too-many-ancestors

    def __init__(
            self,
            parameters: typing.Optional[
                typing.Union[
                    typing.List[FParameter],
                    typing.Tuple[FParameter, ...],
                ]
            ]=None,
            *,
            return_annotation: typing.Any = empty.native,
            __validate_parameter__: bool = False
        ) -> None:
        # TODO: add return_annotation to docs
        # TODO: add __validate_parameter__ to docs
        super().__init__(
            _data=FParameterMap(parameters),
            return_annotation=return_annotation
        )

    @property
    def context(self):
        if not self.parameters:
            return None
        param0 = next(iter(self.parameters.values()))
        return param0 if param0.contextual is True else None

    @property
    def var_positional(self):
        return get_var_positional_parameter(*self.parameters.values())

    @property
    def var_keyword(self):
        return get_var_keyword_parameter(*self.parameters.values())

    def __str__(self):
        sig = inspect.Signature(
            [fp.native for fp in self.parameters.values()],
            return_annotation=self.return_annotation,
            __validate_parameters__=False,
        )
        return str(sig)

    def __repr__(self):
        return '<{} {}>'.format(type(self).__name__, self)

    @property
    def native(self):
        """
        Provides a representation of this :class:`~forge.FSignature` as an
        instance of :class:`inspect.Signature`
        """
        return inspect.Signature([
            param.native for param in self.parameters.values()
            if not param.bound
        ], return_annotation=self.return_annotation)

    @property
    def parameters(self):
        """
        Provides read-only mapping access to the underlying parameters
        (instances of :class:`~forge.FParameter`)
        """
        return types.MappingProxyType(self._data)

    @classmethod
    def from_signature(cls, signature: inspect.Signature) -> 'FSignature':
        """
        A factory method that creates an instance of
        :class:`~forge.FSignature` from an instance of
        :class:`inspect.Signature`.
        Calls down to :class:`~forge.FParameter` to map the
        :attr:`inspect.Signature.parameters` to :class:`inspect.Parameter`
        instances.

        The ``return type`` annotation from the provided signature is not
        retained, as :meth:`~forge.FSignature.from_signature` doesn't provide
        this functionality.

        :param signature: an instance of :class:`inspect.Signature` from which
            to derive the :class:`~forge.FSignature`
        :return: an instance of :class:`~forge.FSignature` derived from the
            :paramref:`~forge.FSignature.from_signature.signature` argument.
        """
        # TODO: test return_annotation
        # pylint: disable=E1101, no-member
        return cls([
            FParameter.from_native(native)
            for native in signature.parameters.values()
        ], return_annotation=signature.return_annotation)

    @classmethod
    def from_callable(cls, callable: typing.Callable) -> 'FSignature':
        """
        A factory method that creates an instance of
        :class:`~forge.FSignature` from a callable. Calls down to
        :meth:`~forge.FSignature.from_signature` to do the heavy loading.

        :param callable: a callable from which to derive the
            :class:`~forge.FSignature`
        :return: an instance of :class:`~forge.FSignature` derived from the
            :paramref:`~forge.FSignature.from_callable.callable` argument.
        """
        # pylint: disable=W0622, redefined-builtin
        return cls.from_signature(inspect.signature(callable))


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