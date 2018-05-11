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
from forge._parameter import ParameterMap
from forge._utils import (
    get_var_positional_parameter,
    get_var_keyword_parameter,
    set_return_type,
    stringify_parameters,
)


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

_run_validators = True


def get_run_validators() -> bool:
    """
    Return whether or not validators are run.
    """
    return _run_validators


def set_run_validators(run: bool) -> None:
    """
    Set whether or not validators are run.  By default, they are run.
    """
    # pylint: disable=W0603, global-statement
    if not isinstance(run, bool):
        raise TypeError("'run' must be bool.")
    global _run_validators
    _run_validators = run


def returns(
        annotation: typing.Any = void
    ) -> typing.Callable[[typing.Callable[..., typing.Any]], typing.Any]:
    def inner(callable_):
        set_return_type(callable_, void_to_empty(annotation))
        return callable_
    return inner


class CallArguments(immutable.Struct):
    __slots__ = ('args', 'kwargs')

    def __init__(
            self,
            *args: typing.Any,
            **kwargs: typing.Any
        ) -> None:
        super().__init__(args=args, kwargs=kwargs)

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


def ident_t(obj):
    return obj


def make_transform(
        from_: inspect.Signature,
        to_: inspect.Signature,
        keymap_hints: typing.Optional[typing.Dict[str, str]] = None,
    ) -> typing.Callable[[typing.Any], CallArguments]:
    '''
    Transform rules:
    1) every *to_ POSITIONAL_ONLY* must be mapped to
    2) every *to_ POSITIONAL_OR_KEYWORD w/o default* must be mapped to
    3) every *to_ KEYWORD_ONLY w/o default* must be mapped to
    4) *from_ VAR_POSITIONAL* requires *to_ VAR_POSITIONAL*
    5) *from_ VAR_KEYWORD* requires *to_ VAR_KEYWORD*
    '''
    # pylint: disable=R0914, too-many-locals
    keymap_hints = keymap_hints or {}
    ikeymap_hints = {v: k for k, v in keymap_hints.items()}

    make_index = lambda sig, *excl: {
        param.name: param for param in sig.parameters.values()
        if param not in excl
    }

    from_var_po = get_var_positional_parameter(*from_.parameters.values())
    from_var_kw = get_var_keyword_parameter(*from_.parameters.values())
    from_params = make_index(from_, from_var_po, from_var_kw)

    to_var_po = get_var_positional_parameter(*to_.parameters.values())
    to_var_kw = get_var_keyword_parameter(*to_.parameters.values())
    to_params = make_index(to_, to_var_po, to_var_kw)

    ikeymap = {}
    # TODO: improve error messages
    for to_name in list(to_params):
        to_param = to_params.pop(to_name)
        try:
            from_name = ikeymap_hints.get(to_name, to_name)
            from_params.pop(from_name)
        except KeyError:
            if to_param.default is not inspect.Parameter.empty:
                continue

            kind_repr = pk_strings[to_param.kind]
            raise TypeError(
                f"Missing requisite mapping to non-default {kind_repr} "
                f"parameter '{to_name}'"
            )
        else:
            ikeymap[to_name] = from_name

    if from_var_po and not to_var_po:
        kind_repr = pk_strings[VAR_POSITIONAL]
        raise TypeError(
            f"Missing requisite mapping from {kind_repr} parameter "
            f"'{from_var_po.name}'"
        )
    if not to_var_kw:
        kind_repr = pk_strings[VAR_KEYWORD]
        if from_var_kw:
            raise TypeError(
                f"Missing requisite mapping from {kind_repr} parameter "
                f"'{from_var_kw.name}'"
            )
        elif from_params:
            raise TypeError(
                "Missing requisite mapping from parameters "
                f"({', '.join(from_params)})"
            )

    def _transform(call_arguments: CallArguments) -> CallArguments:
        # nonlocals: from_, to_, ikeymap,
        # to_var_po, to_var_kw, from_var_po, from_var_kw
        fba = call_arguments.to_bound_arguments(from_)
        fba.apply_defaults()
        tba = to_.bind_partial()
        tba.apply_defaults()

        for to_param in to_.parameters.values():
            if to_param.kind in (VAR_POSITIONAL, VAR_KEYWORD):
                continue
            elif to_param.name not in ikeymap:
                # i.e. not mapped; e.g. from_() -> to_(a=1); >>> func()
                continue
            # i.e. argument supplied; e.g. from_(a) -> to_(a); >>> func(1)
            tba.arguments[to_param.name] = \
                fba.arguments.pop(ikeymap[to_param.name])

        if from_var_po:
            # pylint: disable=E0601, used-before-assignment
            nonlocal to_var_po
            to_var_po = typing.cast(inspect.Parameter, to_var_po)
            tba.arguments[to_var_po.name] = fba.arguments.pop(from_var_po.name)

        if from_var_kw:
            # pylint: disable=E0601, used-before-assignment
            nonlocal to_var_kw
            to_var_kw = typing.cast(inspect.Parameter, to_var_kw)
            tba.arguments[to_var_kw.name] = fba.arguments.pop(from_var_kw.name)

        if to_var_kw and fba.arguments:
            tba.arguments[to_var_kw.name].update(**fba.arguments)

        # pylint: disable=E1101, no-member
        return CallArguments.from_bound_arguments(tba)
    return _transform


class Forger(collections.abc.MutableSequence):
    # pylint: disable=R0901, too-many-ancestors
    @staticmethod
    def validate(*pmaps):
        pname_set = set()
        iname_set = set()
        for i, current in enumerate(pmaps):
            if not isinstance(current, ParameterMap):
                raise TypeError(f"Received non-ParameterMap '{current}'")
            elif not (current.name and current.interface_name):
                raise ValueError(f'Received unnamed ParameterMap: {current}')
            elif current.is_contextual and i > 0:
                raise TypeError(
                    'Only the first ParameterMap can be contextual'
                )

            if current.name in pname_set:
                raise ValueError(
                    'Received multiple ParameterMaps with name '
                    f"'{current.name}'"
                )
            pname_set.add(current.name)

            if current.interface_name in iname_set:
                raise ValueError(
                    'Received multiple ParameterMaps with interface_name '
                    f"'{current.interface_name}'"
                )
            iname_set.add(current.interface_name)

            last = pmaps[i-1] if i > 0 else None
            if not last:
                continue

            elif current.kind < last.kind:
                raise SyntaxError(
                    f"{current} of kind '{current.kind.name}' follows "
                    f"{last} of kind '{last.kind.name}'"
                )
            if current.kind is last.kind:
                if current.kind is VAR_POSITIONAL:
                    raise TypeError(
                        'Received multiple variable-positional ParameterMaps'
                    )
                elif current.kind is VAR_KEYWORD:
                    raise TypeError(
                        'Received multiple variable-keyword ParameterMaps'
                    )
                elif current.kind in (POSITIONAL_ONLY, POSITIONAL_OR_KEYWORD) \
                    and last.default is not inspect.Parameter.empty \
                    and current.default is inspect.Parameter.empty:
                    raise SyntaxError(
                        'non-default ParameterMap follows default ParameterMap'
                    )

    def __init__(self, *args: ParameterMap, **kwargs: ParameterMap) -> None:
        self._data = [
            *args,
            *[
                v.replace(
                    name=k,
                    interface_name=v.interface_name or k,
                ) for k, v in kwargs.items()
            ],
        ]
        self.validate(*self._data)

    def __eq__(self, other):
        # pylint: disable=W0212, protected-access
        if type(self) is not type(other):
            return False
        return self._data == other._data

    def __repr__(self):
        return f'<{type(self).__name__} ({stringify_parameters(*self)})>'

    # Begin MutableSequence methods
    def __getitem__(
            self,
            key: typing.Union[int, slice],
        ) -> typing.Any:
        # typing.Union[ParameterMap, typing.Sequence[ParameterMap]]
        # https://github.com/python/mypy/issues/4108
        return self._data.__getitem__(key)

    def __setitem__(
            self,
            key: typing.Union[slice, int],
            value: typing.Union[typing.Iterable[ParameterMap], ParameterMap],
        ) -> None:
        temp = list(self._data)
        temp.__setitem__(key, value)  # type: ignore
        self.validate(*temp)
        self._data = temp

    def __delitem__(self, key: typing.Union[int, slice]) -> None:
        temp = list(self._data)
        temp.__delitem__(key)
        self._data = temp

    def __len__(self) -> int:
        return len(self._data)

    def insert(self, index: int, value: ParameterMap) -> None:
        temp = list(self._data)
        temp.insert(index, value)
        self.validate(*temp)
        self._data = temp
    # End MutableSequence methods

    def __call__(
            self,
            callable_: typing.Callable[..., types.FunctionType],
        ) -> typing.Callable[..., typing.Any]:
        @functools.wraps(callable_)
        def wrapper(*args, **kwargs):
            # pylint: disable=E1102, not-callable
            transformed = wrapper.__signature_mapper__(*args, **kwargs)
            return callable_(*transformed.args, **transformed.kwargs)

        mapper = self.make_mapper(callable_)
        wrapper.__signature_mapper__ = mapper  # type: ignore
        wrapper.__signature__ = mapper.sig_public  # type: ignore
        return wrapper

    @classmethod
    def from_callable(cls, callable_: typing.Callable) -> 'Forger':
        sig = inspect.signature(callable_)
        # pylint: disable=E1101, no-member
        return cls(*[
            ParameterMap.from_parameter(param)
            for param in sig.parameters.values()
        ])

    @property
    def context(self):
        return self[0] if self and self[0].is_contextual else None

    @property
    def var_positional(self):
        return get_var_positional_parameter(*self)

    @property
    def var_keyword(self):
        return get_var_keyword_parameter(*self)

    @property
    def converters(self):
        return {
            pmap.name: pmap.converter
            for pmap in self if pmap.converter
        }

    @property
    def validators(self):
        return {
            pmap.name: pmap.validator
            for pmap in self if pmap.validator
        }

    @property
    def public_parameters(self):
        return [pmap.parameter for pmap in self]

    @property
    def interface_parameters(self):
        return [pmap.interface_parameter for pmap in self]

    def make_signature(self, interface=False, return_annotation=void):
        return inspect.Signature(
            parameters=[
                pmap.interface_parameter \
                    if interface \
                    else pmap.parameter
                for pmap in self
            ],
            return_annotation=void_to_empty(return_annotation),
        )

    def make_mapper(
            self,
            callable_: typing.Callable[..., typing.Any],
        ) -> 'SignatureMapper':
        sig_private = inspect.signature(callable_)
        sig_public = self.make_signature(
            return_annotation=sig_private.return_annotation,
        )
        sig_interface = self.make_signature(
            interface=True,
            return_annotation=sig_private.return_annotation,
        )

        return SignatureMapper(  # type: ignore
            callable_=callable_,
            has_context=bool(self.context),
            sig_public=sig_public,
            sig_interface=sig_interface,
            converters=types.MappingProxyType(self.converters),
            validators=types.MappingProxyType(self.validators),
            tf_interface=make_transform(
                sig_public,
                sig_interface,
                {p.name: p.interface_name for p in self},
            ),
            tf_private=make_transform(sig_interface, sig_private),
        )


class SignatureMapper(immutable.Struct):
    __slots__ = (
        'callable_',
        'has_context',
        'sig_public',
        'sig_interface',
        'converters',
        'validators',
        'tf_interface',
        'tf_private',
    )

    def __init__(
            self,
            callable_: typing.Callable[..., typing.Any],
            has_context: bool,
            sig_public: inspect.Signature,
            sig_interface: inspect.Signature,
            converters: types.MappingProxyType = types.MappingProxyType({}),
            validators: types.MappingProxyType = types.MappingProxyType({}),
            tf_interface: typing.Callable[[CallArguments], CallArguments] = \
                ident_t,
            tf_private: typing.Callable[[CallArguments], CallArguments] = \
                ident_t,
        ) -> None:
        # pylint: disable=R0913, too-many-arguments
        super().__init__(
            callable_=callable_,
            has_context=has_context,
            sig_public=sig_public,
            sig_interface=sig_interface,
            converters=types.MappingProxyType(converters),
            validators=types.MappingProxyType(validators),
            tf_interface=tf_interface,
            tf_private=tf_private
        )

    def __call__(
            self,
            *args: typing.Any,
            **kwargs: typing.Any
        ) -> typing.Any:
        try:
            bound = self.sig_public.bind(*args, **kwargs)
        except TypeError as exc:
            raise TypeError(f'{self.callable_.__name__}() {exc.args[0]}')

        bound.apply_defaults()
        self.convert(bound.arguments)
        self.validate(bound.arguments)

        # pylint: disable=E1101, no-member
        # pylint: disable=E1121, too-many-function-args
        call_args = CallArguments.from_bound_arguments(bound)
        return self.tf_private(self.tf_interface(call_args))  # type: ignore

    def __repr__(self) -> str:
        pubstr = stringify_parameters(
            *self.sig_public.parameters.values()
        )
        privstr = stringify_parameters(
            *self.sig_private.parameters.values()
        )
        return f'<{type(self).__name__} ({pubstr}) -> ({privstr})>'

    def _get_context(
            self,
            arguments: typing.MutableMapping[str, typing.Any]
        ) -> typing.Any:
        return next(iter(arguments.values()), None) \
            if self.has_context \
            else None

    @property
    def sig_private(self):
        return inspect.signature(self.callable_)

    def convert(
            self,
            arguments: typing.MutableMapping[str, typing.Any]
        ) -> None:
        context = self._get_context(arguments)
        for k, v in self.converters.items():
            arguments[k] = v(context, k, arguments[k])

    def validate(
            self,
            arguments: typing.MutableMapping[str, typing.Any]
        ) -> None:
        context = self._get_context(arguments)
        if get_run_validators():
            for k, validator in self.validators.items():
                if isinstance(validator, typing.Iterable):
                    for v in validator:
                        v(context, k, arguments[k])
                else:
                    validator(context, k, arguments[k])