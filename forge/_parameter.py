import collections
import collections.abc
import inspect
import types
import typing

from forge._marker import (
    coerce_if,
    void,
    void_to_empty,
)


class ParameterMap(typing.NamedTuple):
    kind: inspect._ParameterKind # pylint: disable=W0212, protected-access
    public_name: typing.Optional[str]
    interface_name: typing.Optional[str]
    default: typing.Any = inspect.Parameter.empty
    annotation: typing.Any = inspect.Parameter.empty
    converter: typing.Optional[types.FunctionType] = None
    validator: typing.Optional[
        typing.Union[
            types.FunctionType,
            typing.Iterable[types.FunctionType]
        ]
    ] = None
    is_contextual: bool = False

    def __str__(self) -> str:
        prefix = ''
        if self.kind == inspect.Parameter.VAR_POSITIONAL:
            prefix = '*'
        elif self.kind == inspect.Parameter.VAR_KEYWORD:
            prefix = '**'

        mapping = f'{prefix}{self.public_name or "<missing>"}' \
            if self.public_name == self.interface_name \
            else (
                f'{prefix}{self.public_name or "<missing>"}->'
                f'{prefix}{self.interface_name or "<missing>"}'
            )
        annotation = self.annotation.__name__ \
            if inspect.isclass(self.annotation) \
            else str(self.annotation)
        annotated = f'{mapping}:{annotation}' \
            if self.annotation is not inspect.Parameter.empty \
            else mapping
        defaulted = f'{annotated}={self.default}' \
            if self.default is not inspect.Parameter.empty \
            else annotated
        return defaulted

    def __repr__(self) -> str:
        return f'<{type(self).__name__} "{self}">'

    @property
    def public_parameter(self) -> inspect.Parameter:
        if not self.public_name:
            raise TypeError('Cannot generate parameter without public_name')
        return inspect.Parameter(
            name=typing.cast(str, self.public_name),
            kind=self.kind,
            default=self.default,
            annotation=self.annotation,
        )

    @property
    def interface_parameter(self) -> inspect.Parameter:
        if not self.interface_name:
            raise TypeError('Cannot generate parameter without interface_name')

        return inspect.Parameter(
            name=typing.cast(str, self.interface_name),
            kind=self.kind,
            default=self.default,
            annotation=self.annotation,
        )

    def replace(
            self,
            *,
            kind=void,
            public_name=void,
            interface_name=void,
            default=void,
            annotation=void,
            converter=void,
            validator=void,
            is_contextual=void,
        ):
        # pylint: disable=R0913, too-many-arguments
        # pylint: disable=E1120, no-value-for-parameter
        return type(self)(
            kind=coerce_if(kind, void, self.kind),
            public_name=coerce_if(public_name, void, self.public_name),
            interface_name=coerce_if(
                interface_name, void, self.interface_name),
            default=coerce_if(default, void, self.default),
            annotation=coerce_if(annotation, void, self.annotation),
            converter=coerce_if(converter, void, self.converter),
            validator=coerce_if(validator, void, self.validator),
            is_contextual=coerce_if(is_contextual, void, self.is_contextual),
        )

    @classmethod
    def from_parameter(cls, parameter: inspect.Parameter) -> 'ParameterMap':
        return cls(
            kind=parameter.kind,
            public_name=parameter.name,
            interface_name=parameter.name,
            default=parameter.default,
            annotation=parameter.annotation,
        )

    @classmethod
    def create_positional_only(
            cls,
            interface_name=None,
            public_name=None,
            *,
            default=void,
            annotation=void,
            converter=None,
            validator=None,
        ) -> 'ParameterMap':
        return cls(
            kind=inspect.Parameter.POSITIONAL_ONLY,
            public_name=public_name or interface_name,
            interface_name=interface_name or public_name,
            default=void_to_empty(default),
            annotation=void_to_empty(annotation),
            converter=converter,
            validator=validator,
        )

    @classmethod
    def create_positional_or_keyword(
            cls,
            interface_name=None,
            public_name=None,
            *,
            default=void,
            annotation=void,
            converter=None,
            validator=None,
        ) -> 'ParameterMap':
        return cls(
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            public_name=public_name or interface_name,
            interface_name=interface_name or public_name,
            default=void_to_empty(default),
            annotation=void_to_empty(annotation),
            converter=converter,
            validator=validator,
        )

    @classmethod
    def create_contextual(
            cls,
            interface_name=None,
            public_name=None,
            *,
            annotation=void,
        ) -> 'ParameterMap':
        return cls(
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            interface_name=interface_name or public_name,
            public_name=public_name or interface_name,
            default=inspect.Parameter.empty,
            annotation=void_to_empty(annotation),
            is_contextual=True,
        )

    @classmethod
    def create_keyword_only(
            cls,
            interface_name=None,
            public_name=None,
            *,
            default=void,
            annotation=void,
            converter=None,
            validator=None,
        ) -> 'ParameterMap':
        return cls(
            kind=inspect.Parameter.KEYWORD_ONLY,
            public_name=public_name or interface_name,
            interface_name=interface_name or public_name,
            default=void_to_empty(default),
            annotation=void_to_empty(annotation),
            converter=converter,
            validator=validator,
        )

    @classmethod
    def create_var_positional(
            cls,
            name,
            *,
            converter=None,
            validator=None,
        ) -> 'ParameterMap':
        return cls(
            kind=inspect.Parameter.VAR_POSITIONAL,
            public_name=name,
            interface_name=name,
            default=inspect.Parameter.empty,
            annotation=inspect.Parameter.empty,
            converter=converter,
            validator=validator,
        )

    @classmethod
    def create_var_keyword(
            cls,
            name,
            *,
            converter=None,
            validator=None,
        ) -> 'ParameterMap':
        return cls(
            kind=inspect.Parameter.VAR_KEYWORD,
            public_name=name,
            interface_name=name,
            default=inspect.Parameter.empty,
            annotation=inspect.Parameter.empty,
            converter=converter,
            validator=validator,
        )


class VarPositional(collections.abc.Iterable):
    _default_name = 'args'

    def __init__(
            self,
            name: typing.Optional[str] = None,
            converter: typing.Optional[types.FunctionType] = None,
            validator: typing.Union[
                typing.Optional[types.FunctionType],
                typing.Optional[typing.Iterable[types.FunctionType]],
            ]=None,
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
    def param(self) -> ParameterMap:
        # pylint: disable=E1101, no-member
        return ParameterMap.create_var_positional(
            name=self.name,
            converter=self.converter,
            validator=self.validator,
        )

    def __iter__(self) -> typing.Iterator:
        return iter((self.param,))

    def __call__(
            self,
            name: str = None,
            *,
            converter: typing.Optional[types.FunctionType] = None,
            validator: typing.Union[
                typing.Optional[types.FunctionType],
                typing.Optional[typing.Iterable[types.FunctionType]],
            ]=None,
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
            name: typing.Optional[str] = None,
            converter: typing.Optional[types.FunctionType] = None,
            validator: typing.Union[
                typing.Optional[types.FunctionType],
                typing.Optional[typing.Iterable[types.FunctionType]],
            ]=None,
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
    def param(self) -> ParameterMap:
        # pylint: disable=E1101, no-member
        return ParameterMap.create_var_keyword(
            name=self.name,
            converter=self.converter,
            validator=self.validator,
        )

    def __getitem__(self, key: str) -> ParameterMap:
        if self.name == key:
            return self.param
        raise KeyError(key)

    def __iter__(self) -> typing.Iterator[str]:
        return iter({self.name: self.param})

    def __len__(self) -> int:
        return 1

    def __call__(
            self,
            name: typing.Optional[str] = None,
            *,
            converter: typing.Optional[types.FunctionType] = None,
            validator: typing.Union[
                typing.Optional[types.FunctionType],
                typing.Optional[typing.Iterable[types.FunctionType]],
            ]=None,
    ) -> 'VarKeyword':
        return type(self)(
            name=name,
            converter=converter,
            validator=validator,
        )


# pylint: disable=C0103, invalid-name
# pylint: disable=E1101, no-member
pos = ParameterMap.create_positional_only
arg = ParameterMap.create_positional_or_keyword
args = VarPositional()
kwarg = ParameterMap.create_keyword_only
kwargs = VarKeyword()
ctx = ParameterMap.create_contextual
self_ = ctx('self')
cls_ = ctx('cls')