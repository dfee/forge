from collections import OrderedDict
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
from forge._parameter import FParameter
from forge._utils import (
    get_return_type,
    get_var_positional_parameter,
    get_var_keyword_parameter,
    set_return_type,
    stringify_parameters,
)


empty = inspect.Parameter.empty  # pylint: disable=C0103, invalid-name
POSITIONAL_ONLY = inspect.Parameter.POSITIONAL_ONLY
POSITIONAL_OR_KEYWORD = inspect.Parameter.POSITIONAL_OR_KEYWORD
VAR_POSITIONAL = inspect.Parameter.VAR_POSITIONAL
KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY
VAR_KEYWORD = inspect.Parameter.VAR_KEYWORD

pk_strings = {
    POSITIONAL_ONLY: 'positional-only',
    POSITIONAL_OR_KEYWORD: 'positional-or-keyword',
    VAR_POSITIONAL: 'variable-positional',
    KEYWORD_ONLY: 'keyword-only',
    VAR_KEYWORD: 'variable-keyword',
}


def returns(
        annotation: typing.Any = void
    ) -> typing.Callable[[typing.Callable[..., typing.Any]], typing.Any]:
    def inner(callable):
        # pylint: disable=W0622, redefined-builtin
        set_return_type(callable, void_to_empty(annotation))
        return callable
    return inner


class CallArguments(immutable.Immutable):
    __slots__ = ('args', 'kwargs')

    def __init__(
            self,
            *args: typing.Any,
            **kwargs: typing.Any
        ) -> None:
        super().__init__(args=args, kwargs=types.MappingProxyType(kwargs))

    def __repr__(self):
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
        return cls(*bound.args, **bound.kwargs)  # type: ignore

    def to_bound_arguments(
            self,
            signature: inspect.Signature,
            partial: bool = False,
        ) -> inspect.BoundArguments:
        return signature.bind_partial(*self.args, **self.kwargs) \
            if partial \
            else signature.bind(*self.args, **self.kwargs)


class FSignature(collections.abc.Mapping, immutable.Immutable):
    # pylint: disable=R0901, too-many-ancestors
    @staticmethod
    def validate(*fparams):
        pname_set = set()
        iname_set = set()
        for i, current in enumerate(fparams):
            if not isinstance(current, FParameter):
                raise TypeError(
                    "Received non-FParameter '{}'".\
                    format(current)
                )
            elif not (current.name and current.interface_name):
                raise ValueError(
                    "Received unnamed FParameter: '{}'".\
                    format(current)
                )
            elif current.contextual and i > 0:
                raise TypeError(
                    'Only the first FParameter can be contextual'
                )

            if current.name in pname_set:
                raise ValueError(
                    "Received multiple FParameters with name '{}'".\
                    format(current.name)
                )
            pname_set.add(current.name)

            if current.interface_name in iname_set:
                raise ValueError(
                    "Received multiple FParameters with interface_name '{}'".\
                    format(current.interface_name)
                )
            iname_set.add(current.interface_name)

            last = fparams[i-1] if i > 0 else None
            if not last:
                continue

            elif current.kind < last.kind:
                raise SyntaxError(
                    "{current} of kind '{current.kind.name}' follows "
                    "{last} of kind '{last.kind.name}'".\
                    format(current=current, last=last)
                )
            elif current.kind is last.kind:
                if current.kind is VAR_POSITIONAL:
                    raise TypeError(
                        'Received multiple variable-positional FParameters'
                    )
                elif current.kind is VAR_KEYWORD:
                    raise TypeError(
                        'Received multiple variable-keyword FParameters'
                    )
                elif current.kind in (POSITIONAL_ONLY, POSITIONAL_OR_KEYWORD) \
                    and last.default is not empty \
                    and current.default is empty:
                    raise SyntaxError(
                        'non-default FParameter follows default FParameter'
                    )

    def __init__(
            self,
            *fparameters: FParameter,
            **named_fparameters: FParameter
        ) -> None:
        fparams = [
            *fparameters,
            *[
                v.replace(
                    name=k,
                    interface_name=v.interface_name or k,
                ) for k, v in named_fparameters.items()
            ],
        ]
        self.validate(*fparams)

        super().__init__(
            _data=OrderedDict([(fp.name, fp) for fp in fparams]),
            context=fparams[0] \
                if fparams and fparams[0].contextual \
                else None,
            var_positional=get_var_positional_parameter(*fparams),
            var_keyword=get_var_keyword_parameter(*fparams),
        )

    def __eq__(self, other):
        # pylint: disable=W0212, protected-access
        if type(self) is not type(other):
            return False
        return self._data == other._data

    def __repr__(self):
        return '<{} ({})>'.format(
            type(self).__name__,
            stringify_parameters(*self._data.values()),
        )

    # Begin Mapping methods
    def __getitem__(self, key: str) -> typing.Any:
        return self._data[key]

    def __iter__(self) -> typing.Iterator:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)
    # End Mapping methods

    @classmethod
    def from_signature(cls, signature: inspect.Signature) -> 'FSignature':
        # pylint: disable=E1101, no-member
        return cls(*[
            FParameter.from_parameter(param)
            for param in signature.parameters.values()
        ])

    @classmethod
    def from_callable(cls, callable: typing.Callable) -> 'FSignature':
        # pylint: disable=W0622, redefined-builtin
        return cls.from_signature(inspect.signature(callable))


class Mapper(immutable.Immutable):
    __slots__ = (
        'callable',
        'fsignature',
        'parameter_map',
        'private_signature',
        'public_signature',
    )

    def __init__(
            self,
            fsignature: FSignature,
            callable: typing.Callable[..., typing.Any],
        ) -> None:
        # pylint: disable=W0622, redefined-builtin
        private_signature = inspect.signature(callable)
        public_signature = inspect.Signature(
            parameters=[
                fp.parameter for fp in fsignature.values()
                if fp.bound is False
            ],
            return_annotation=get_return_type(callable),
        )
        parameter_map = self.map_parameters(fsignature, private_signature)

        super().__init__(
            callable=callable,
            fsignature=fsignature,
            private_signature=private_signature,
            public_signature=public_signature,
            parameter_map=parameter_map,
        )

    def __call__(
            self,
            *args: typing.Any,
            **kwargs: typing.Any
        ) -> typing.Any:
        try:
            public_ba = self.public_signature.bind(*args, **kwargs)
        except TypeError as exc:
            raise TypeError(
                '{callable_name}() {message}'.\
                format(
                    callable_name=self.callable.__name__,
                    message=exc.args[0],
                ),
            )

        private_ba = self.private_signature.bind_partial()
        private_ba.apply_defaults()
        ctx = self.get_context(public_ba.arguments)

        for from_name, from_param in self.fsignature.items():
            from_val = public_ba.arguments.get(from_name, void)
            to_name = self.parameter_map[from_name]
            to_param = self.private_signature.parameters[to_name]
            to_val = self.fsignature[from_name](ctx, from_name, from_val)

            if to_param.kind is VAR_POSITIONAL:
                # e.g. f(*args) -> g(*args)
                private_ba.arguments[to_name] = to_val
            elif to_param.kind is VAR_KEYWORD:
                if from_param.kind is VAR_KEYWORD:
                    # e.g. f(**kwargs) -> g(**kwargs)
                    private_ba.arguments[to_name].update(to_val)
                else:
                    # e.g. f(a) -> g(**kwargs)
                    private_ba.arguments[to_name]\
                        [from_param.interface_name] = to_val
            else:
                # e.g. f(a) -> g(a)
                private_ba.arguments[to_name] = to_val

        return CallArguments.from_bound_arguments(private_ba)

    def __repr__(self) -> str:
        pubstr = stringify_parameters(
            *self.public_signature.parameters.values()
        )
        privstr = stringify_parameters(
            *self.private_signature.parameters.values()
        )
        return '<{} ({}) -> ({})>'.format(type(self).__name__, pubstr, privstr)

    def get_context(self, arguments: typing.Mapping) -> typing.Any:
        return arguments[self.fsignature.context.name] \
            if self.fsignature.context \
            else None

    @staticmethod
    def map_parameters(
            fsignature: 'FSignature',
            signature: inspect.Signature,
        ):
        '''
        Transform rules:
        1) every *to_ POSITIONAL_ONLY* must be mapped to
        2) every *to_ POSITIONAL_OR_KEYWORD w/o default* must be mapped to
        3) every *to_ KEYWORD_ONLY w/o default* must be mapped to
        4) *from_ VAR_POSITIONAL* requires *to_ VAR_POSITIONAL*
        5) *from_ VAR_KEYWORD* requires *to_ VAR_KEYWORD*
        '''
        # pylint: disable=W0622, redefined-builtin
        fparam_vpo = fsignature.var_positional
        fparam_vkw = fsignature.var_keyword
        fparam_idx = {
            fparam.interface_name: fparam
            for fparam in fsignature.values()
            if fparam not in (fparam_vpo, fparam_vkw)
        }

        param_vpo = get_var_positional_parameter(
            *signature.parameters.values()
        )
        param_vkw = get_var_keyword_parameter(
            *signature.parameters.values()
        )
        param_idx = {
            param.name: param
            for param in signature.parameters.values()
            if param not in (param_vpo, param_vkw)
        }

        mapping = {}
        for name in list(param_idx):
            param = param_idx.pop(name)
            try:
                param_t = fparam_idx.pop(name)
            except KeyError:
                # masked mapping, e.g. f() -> g(a=1)
                if param.default is not empty:
                    continue

                # invalid mapping, e.g. f() -> g(a)
                kind_repr = pk_strings[param.kind]
                raise TypeError(
                    "Missing requisite mapping to non-default {kind_repr} "
                    "parameter '{pri_name}'".\
                    format(kind_repr=kind_repr, pri_name=name)
                )
            else:
                mapping[param_t.name] = name

        if fparam_vpo:
            # invalid mapping, e.g. f(*args) -> g()
            if not param_vpo:
                kind_repr = pk_strings[VAR_POSITIONAL]
                raise TypeError(
                    "Missing requisite mapping from {kind_repr} parameter "
                    "'{fparam_vpo.name}'".\
                    format(kind_repr=kind_repr, fparam_vpo=fparam_vpo)
                )
            # var-positional mapping, e.g. f(*args) -> g(*args)
            mapping[fparam_vpo.name] = param_vpo.name

        if fparam_vkw:
            # invalid mapping, e.g. f(**kwargs) -> g()
            if not param_vkw:
                kind_repr = pk_strings[VAR_KEYWORD]
                raise TypeError(
                    "Missing requisite mapping from {kind_repr} parameter "
                    "'{fparam_vkw.name}'".\
                    format(kind_repr=kind_repr, fparam_vkw=fparam_vkw)
                )
            # var-keyword mapping, e.g. f(**kwargs) -> g(**kwargs)
            mapping[fparam_vkw.name] = param_vkw.name

        if fparam_idx:
            # invalid mapping, e.g. f(a) -> g()
            if not param_vkw:
                raise TypeError(
                    "Missing requisite mapping from parameters ({})".\
                    format(', '.join([pt.name for pt in fparam_idx.values()]))
                )
            # to-var-keyword mapping, e.g. f(a) -> g(**kwargs)
            for param_t in fparam_idx.values():
                mapping[param_t.name] = param_vkw.name

        return types.MappingProxyType(mapping)


def sign(
        *fparameters: FParameter,
        **named_fparameters: FParameter
    ) -> typing.Callable[..., typing.Any]:
    fsignature = FSignature(*fparameters, **named_fparameters)
    def wrapper(callable):
        # pylint: disable=W0622, redefined-builtin
        @functools.wraps(callable)
        def inner(*args, **kwargs):
            # pylint: disable=E1102, not-callable
            mapped = inner.__mapper__(*args, **kwargs)
            return callable(*mapped.args, **mapped.kwargs)

        inner.__mapper__ = Mapper(fsignature, callable)  # type: ignore
        inner.__signature__ = inner.__mapper__.public_signature  # type: ignore
        return inner
    return wrapper


def resign(
        *fparameters: FParameter,
        **named_fparameters: FParameter
    ) -> typing.Callable[..., typing.Any]:
    fsignature = FSignature(*fparameters, **named_fparameters)
    def reviser(callable):
        # pylint: disable=W0622, redefined-builtin
        callable.__mapper__ = Mapper(fsignature, callable.__wrapped__)
        callable.__signature__ = callable.__mapper__.public_signature
        return callable
    return reviser
