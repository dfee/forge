import collections
import collections.abc
import functools
import inspect
import types
import typing

from forge._counter import CreationOrderMeta
import forge._immutable as immutable
from forge._marker import (
    empty,
    void,
)


pk_strings = {
    inspect.Parameter.POSITIONAL_ONLY: 'positional-only',
    inspect.Parameter.POSITIONAL_OR_KEYWORD: 'positional-or-keyword',
    inspect.Parameter.VAR_POSITIONAL: 'variable-positional',
    inspect.Parameter.KEYWORD_ONLY: 'keyword-only',
    inspect.Parameter.VAR_KEYWORD: 'variable-keyword',
}

_ctx_callable_type = typing.Callable[[typing.Any, str, typing.Any], typing.Any]

# pylint: disable=W0212, protected-access, W0212, invalid-name
_kind_type = inspect._ParameterKind
_bound_type = bool
_contextual_type = bool
# pylint: enable=W0212, protected-access, W0212, invalid-name
_name_type = typing.Optional[str]
_default_type = typing.Any
_factory_type = typing.Callable[[], typing.Any]
_type_type = typing.Any
_converter_type = typing.Optional[
    typing.Union[
        _ctx_callable_type,
        typing.Iterable[_ctx_callable_type]
    ]
]
_validator_type = typing.Optional[
    typing.Union[
        _ctx_callable_type,
        typing.Iterable[_ctx_callable_type]
    ]
]
_metadata_type = typing.Mapping


class Factory(immutable.Immutable):
    # pylint: disable=R0903, too-few-public-methods
    __slots__ = ('factory',)

    def __init__(self, factory):
        # pylint: disable=C0102, blacklisted-name
        super().__init__(factory=factory)

    def __repr__(self):
        return '<{} {}>'.format(type(self).__name__, self.factory.__qualname__)

    def __call__(self):
        return self.factory()


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

    POSITIONAL_ONLY = inspect.Parameter.POSITIONAL_ONLY
    POSITIONAL_OR_KEYWORD = inspect.Parameter.POSITIONAL_OR_KEYWORD
    VAR_POSITIONAL = inspect.Parameter.VAR_POSITIONAL
    KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY
    VAR_KEYWORD = inspect.Parameter.VAR_KEYWORD

    def __init__(
            self,
            kind: _kind_type,
            name: _name_type = None,
            interface_name: _name_type = None,
            default: _default_type = empty,
            factory: _factory_type = empty,
            type: _type_type = empty,
            converter: _converter_type = None,
            validator: _validator_type = None,
            bound: _bound_type = False,
            contextual: _contextual_type = False,
            metadata: typing.Optional[_metadata_type] = None
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
    def parameter(self) -> inspect.Parameter:
        """
        A public representation of this :class:`~forge.FParameter` as an
        :class:`inspect.Parameter`, fit for an :class:`inspect.Signature`
        """
        if not self.name:
            raise TypeError('Cannot generate an unnamed parameter')
        return inspect.Parameter(
            name=self.name,
            kind=self.kind,
            default=empty.ccoerce(self.default),
            annotation=empty.ccoerce(self.type),
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
    def from_parameter(cls, parameter: inspect.Parameter) -> 'FParameter':
        """
        A factory method for creating :class:`~forge.FParameter` instances from
        :class:`inspect.Parameter` instances.

        Parameter descriptions are a subset of those defined on
        :class:`~forge.FParameter`
        """
        return cls(  # type: ignore
            kind=parameter.kind,
            name=parameter.name,
            interface_name=parameter.name,
            default=parameter.default,
            type=parameter.annotation
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
    # pylint: disable=R0903, too-few-public-methods
    _default_name = 'args'

    def __init__(
            self,
            name: _name_type = None,
            *,
            converter: _converter_type = None,
            validator: _validator_type = None,
            metadata: typing.Optional[_metadata_type] = None
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
            name: _name_type = None,
            *,
            converter: _converter_type = None,
            validator: _validator_type = None,
            metadata: typing.Optional[_metadata_type] = None
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
            name: _name_type = None,
            *,
            converter: _converter_type = None,
            validator: _validator_type = None,
            metadata: typing.Optional[_metadata_type] = None
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
            name: _name_type = None,
            *,
            converter: _converter_type = None,
            validator: _validator_type = None,
            metadata: typing.Optional[_metadata_type] = None
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