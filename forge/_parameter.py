import collections
import collections.abc
import functools
import inspect
import types
import typing

import forge._immutable as immutable
from forge._marker import (
    void,
    void_to_empty,
)

# pylint: disable=W0212, protected-access, W0212, invalid-name
_kind_type = inspect._ParameterKind
_is_contextual_type = bool
# pylint: enable=W0212, protected-access, W0212, invalid-name
_name_type = typing.Optional[str]
_default_type = typing.Any
_type_type = typing.Any
_converter_type = typing.Optional[types.FunctionType]
_validator_type = typing.Optional[
    typing.Union[
        types.FunctionType,
        typing.Iterable[types.FunctionType]
    ]
]


class Factory(immutable.Immutable):
    __slots__ = ('factory',)

    def __init__(self, factory):
        # pylint: disable=C0102, blacklisted-name
        super().__init__(factory=factory)

    def __repr__(self):
        return '<{} {}>'.format(type(self).__name__, self.factory.__qualname__)

    def __call__(self):
        return self.factory()


class FParameter(immutable.Immutable):
    __slots__ = (
        'kind',
        'name',
        'interface_name',
        'default',
        'type',
        'converter',
        'validator',
        'is_contextual',
    )

    def __init__(
            self,
            kind: _kind_type,
            name: _name_type = None,
            interface_name: _name_type = None,
            default: _default_type = void,
            type: _type_type = void,
            converter: _converter_type = None,
            validator: _validator_type = None,
            is_contextual: _is_contextual_type = False,
        ) -> None:
        # pylint: disable=W0622, redefined-builtin
        # pylint: disable=R0913, too-many-arguments
        super().__init__(
            kind=kind,
            name=name or interface_name,
            interface_name=interface_name or name,
            default=void_to_empty(default),
            type=void_to_empty(type),
            converter=converter,
            validator=validator,
            is_contextual=is_contextual,
        )

    def __str__(self) -> str:
        if self.kind == inspect.Parameter.VAR_POSITIONAL:
            prefix = '*'
        elif self.kind == inspect.Parameter.VAR_KEYWORD:
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
            if self.type is inspect.Parameter.empty \
            else '{mapped}:{annotation}'.format(
                mapped=mapped,
                annotation=self.type.__name__ \
                    if inspect.isclass(self.type) \
                    else str(self.type),
            )

        return annotated \
            if self.default is inspect.Parameter.empty \
            else '{annotated}={default}'.format(
                annotated=annotated,
                default=self.default,
            )

    def __repr__(self) -> str:
        return '<{} "{}">'.format(type(self).__name__, str(self))

    def apply_default(self, value):
        if value is not void:
            return value
        elif isinstance(self.default, Factory):
            return self.default()
        return self.default

    def apply_conversion(self, ctx, name, value):
        # pylint: disable=W0621, redefined-outer-name
        if self.converter is None:
            return value
        elif isinstance(self.converter, typing.Iterable):
            return functools.reduce(
                lambda val, func: func(ctx, name, val),
                [value, *self.converter],
            )
        return self.converter(ctx, name, value)

    def apply_validation(self, ctx, name, value):
        # pylint: disable=W0621, redefined-outer-name
        if self.validator is not None:
            self.validator(ctx, name, value)
        return value

    def __call__(
            self,
            ctx: typing.Any,
            name: str,
            value: typing.Any = void
        ) -> typing.Any:
        # pylint: disable=W0621, redefined-outer-name
        defaulted = self.apply_default(value)
        converted = self.apply_conversion(ctx, name, defaulted)
        return self.apply_validation(ctx, name, converted)

    @property
    def parameter(self) -> inspect.Parameter:
        if not self.name:
            raise TypeError('Cannot generate an unnamed parameter')
        return inspect.Parameter(
            name=self.name,
            kind=self.kind,
            default=self.default,
            annotation=self.type,
        )

    @property
    def interface_parameter(self) -> inspect.Parameter:
        if not self.interface_name:
            raise TypeError('Cannot generate an unnamed parameter')
        return inspect.Parameter(
            name=self.interface_name,
            kind=self.kind,
            default=self.default,
            annotation=self.type,
        )

    def _asdict(self):
        return immutable.asdict(self)

    def replace(
            self,
            *,
            kind=void,
            name=void,
            interface_name=void,
            default=void,
            type=void,
            converter=void,
            validator=void,
            is_contextual=void
        ):
        # pylint: disable=E1120, no-value-for-parameter
        # pylint: disable=W0622, redefined-builtin
        # pylint: disable=R0913, too-many-arguments
        return immutable.replace(self, **{
            k: v for k, v in {
                'kind': kind,
                'name': name,
                'interface_name': interface_name,
                'default': default,
                'type': type,
                'converter': converter,
                'validator': validator,
                'is_contextual': is_contextual,
            }.items() if v is not void
        })

    @classmethod
    def from_parameter(cls, parameter: inspect.Parameter) -> 'FParameter':
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
            default=void,
            type=void,
            converter=None,
            validator=None
        ) -> 'FParameter':
        # pylint: disable=W0622, redefined-builtin
        return cls(  # type: ignore
            kind=inspect.Parameter.POSITIONAL_ONLY,
            name=name,
            interface_name=interface_name,
            default=void_to_empty(default),
            type=void_to_empty(type),
            converter=converter,
            validator=validator
        )

    @classmethod
    def create_positional_or_keyword(
            cls,
            name=None,
            interface_name=None,
            *,
            default=void,
            type=void,
            converter=None,
            validator=None
        ) -> 'FParameter':
        # pylint: disable=W0622, redefined-builtin
        return cls(  # type: ignore
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            name=name,
            interface_name=interface_name,
            default=void_to_empty(default),
            type=void_to_empty(type),
            converter=converter,
            validator=validator,
        )

    @classmethod
    def create_contextual(
            cls,
            name=None,
            interface_name=None,
            *,
            type=void
        ) -> 'FParameter':
        # pylint: disable=W0622, redefined-builtin
        return cls(  # type: ignore
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            name=name,
            interface_name=interface_name,
            default=inspect.Parameter.empty,
            type=void_to_empty(type),
            is_contextual=True,
        )

    @classmethod
    def create_keyword_only(
            cls,
            name=None,
            interface_name=None,
            *,
            default=void,
            type=void,
            converter=None,
            validator=None
        ) -> 'FParameter':
        # pylint: disable=W0622, redefined-builtin
        return cls(  # type: ignore
            kind=inspect.Parameter.KEYWORD_ONLY,
            name=name,
            interface_name=interface_name,
            default=void_to_empty(default),
            type=void_to_empty(type),
            converter=converter,
            validator=validator,
        )

    @classmethod
    def create_var_positional(
            cls,
            name,
            *,
            converter=None,
            validator=None
        ) -> 'FParameter':
        # pylint: disable=W0622, redefined-builtin
        return cls(  # type: ignore
            kind=inspect.Parameter.VAR_POSITIONAL,
            name=name,
            default=inspect.Parameter.empty,
            type=inspect.Parameter.empty,
            converter=converter,
            validator=validator
        )

    @classmethod
    def create_var_keyword(
            cls,
            name,
            *,
            converter=None,
            validator=None
        ) -> 'FParameter':
        # pylint: disable=W0622, redefined-builtin
        return cls(  # type: ignore
            kind=inspect.Parameter.VAR_KEYWORD,
            name=name,
            default=inspect.Parameter.empty,
            type=inspect.Parameter.empty,
            converter=converter,
            validator=validator,
        )


class VarPositional(collections.abc.Iterable):
    _default_name = 'args'

    def __init__(
            self,
            name: _name_type = None,
            *,
            converter: _converter_type = None,
            validator: _validator_type = None
        ) -> None:
        '''
        There is no concept of name / interface_name, because this
        collection won't persist through re-mapping of the bound params.
        '''
        self._name = name
        self.converter = converter
        self.validator = validator

    @property
    def name(self) -> str:
        return self._name or self._default_name

    @property
    def param(self) -> FParameter:
        # pylint: disable=E1101, no-member
        return FParameter.create_var_positional(
            name=self.name,
            converter=self.converter,
            validator=self.validator,
        )

    def __iter__(self) -> typing.Iterator:
        return iter((self.param,))

    def __call__(
            self,
            name: _name_type = None,
            *,
            converter: _converter_type = None,
            validator: _validator_type = None
        ) -> 'VarPositional':
        return type(self)(
            name=name,
            converter=converter,
            validator=validator
        )



class VarKeyword(collections.abc.Mapping):
    _default_name = 'kwargs'

    def __init__(
            self,
            name: _name_type = None,
            *,
            converter: _converter_type = None,
            validator: _validator_type = None
        ) -> None:
        '''
        There is no concept of name / interface_name, because this
        collection won't persist through re-mapping of the bound params.
        '''
        self._name = name
        self.converter = converter
        self.validator = validator

    @property
    def name(self) -> str:
        return self._name or self._default_name

    @property
    def param(self) -> FParameter:
        # pylint: disable=E1101, no-member
        return FParameter.create_var_keyword(
            name=self.name,
            converter=self.converter,
            validator=self.validator
        )

    def __getitem__(self, key: str) -> FParameter:
        if self.name == key:
            return self.param
        raise KeyError(key)

    def __iter__(self) -> typing.Iterator[str]:
        return iter({self.name: self.param})

    def __len__(self) -> int:
        return 1

    def __call__(
            self,
            name: _name_type = None,
            *,
            converter: _converter_type = None,
            validator: _validator_type = None
        ) -> 'VarKeyword':
        return type(self)(
            name=name,
            converter=converter,
            validator=validator,
        )


# pylint: disable=C0103, invalid-name
# pylint: disable=E1101, no-member
pos = FParameter.create_positional_only
arg = FParameter.create_positional_or_keyword
args = VarPositional()
kwarg = FParameter.create_keyword_only
kwargs = VarKeyword()
ctx = FParameter.create_contextual
self_ = ctx('self')
cls_ = ctx('cls')