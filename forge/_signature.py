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


def returns(
        annotation: typing.Any = void
    ) -> typing.Callable[[typing.Callable[..., typing.Any]], typing.Any]:
    def inner(callable):
        # pylint: disable=W0622, redefined-builtin
        set_return_type(callable, void_to_empty(annotation))
        return callable
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
    param_t_var_po = get_var_positional_parameter(*fsignature)
    param_t_var_kw = get_var_keyword_parameter(*fsignature)
    param_t_idx = {
        param_t.interface_name: param_t
        for param_t in fsignature
        if param_t not in (param_t_var_po, param_t_var_kw)
    }

    param_var_po = get_var_positional_parameter(*signature.parameters.values())
    param_var_kw = get_var_keyword_parameter(*signature.parameters.values())
    param_idx = {
        param.name: param
        for param in signature.parameters.values()
        if param not in (param_var_po, param_var_kw)
    }

    mapping = {} # type: typing.MutableMapping[str, str]
    for name in list(param_idx):
        param = param_idx.pop(name)
        try:
            param_t = param_t_idx.pop(name)
        except KeyError:
            if param.default is not inspect.Parameter.empty:
                # masked mapping, e.g. f() -> g(a=1)
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

    if param_t_var_po:
        if not param_var_po:
            # invalid mapping, e.g. f(*args) -> g()
            kind_repr = pk_strings[VAR_POSITIONAL]
            raise TypeError(
                "Missing requisite mapping from {kind_repr} parameter "
                "'{param_t_var_po.name}'".\
                    format(kind_repr=kind_repr, param_t_var_po=param_t_var_po)
            )
        # var-positional mapping, e.g. f(*args) -> g(*args)
        mapping[param_t_var_po.name] = param_var_po.name

    if param_t_var_kw:
        if not param_var_kw:
            # invalid mapping, e.g. f(**kwargs) -> g()
            kind_repr = pk_strings[VAR_KEYWORD]
            raise TypeError(
                "Missing requisite mapping from {kind_repr} parameter "
                "'{param_t_var_kw.name}'".\
                    format(kind_repr=kind_repr, param_t_var_kw=param_t_var_kw)
            )
        mapping[param_t_var_kw.name] = param_var_kw.name

    if param_t_idx:
        if not param_var_kw:
            # invalid mapping, e.g. f(a) -> g()
            raise TypeError(
                "Missing requisite mapping from parameters ({})".\
                    format(', '.join([pt.name for pt in param_t_idx.values()]))
            )
        for param_t in param_t_idx.values():
            mapping[param_t.name] = param_var_kw.name

    return mapping


class FSignature(collections.abc.MutableSequence):
    # pylint: disable=R0901, too-many-ancestors
    @staticmethod
    def validate(*fparams):
        pname_set = set()
        iname_set = set()
        for i, current in enumerate(fparams):
            if not isinstance(current, FParameter):
                raise TypeError(
                    "Received non-FParameter '{}'".format(current)
                )
            elif not (current.name and current.interface_name):
                raise ValueError(
                    "Received unnamed FParameter: '{}'".format(current)
                )
            elif current.is_contextual and i > 0:
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
                    "Received multiple FParameters with interface_name "
                    "'{}'".format(current.interface_name)
                )
            iname_set.add(current.interface_name)

            last = fparams[i-1] if i > 0 else None
            if not last:
                continue

            elif current.kind < last.kind:
                raise SyntaxError(
                    "{current} of kind '{current.kind.name}' follows "
                    "{last} of kind '{last.kind.name}'".format(
                        current=current,
                        last=last,
                    )
                )
            if current.kind is last.kind:
                if current.kind is VAR_POSITIONAL:
                    raise TypeError(
                        'Received multiple variable-positional FParameters'
                    )
                elif current.kind is VAR_KEYWORD:
                    raise TypeError(
                        'Received multiple variable-keyword FParameters'
                    )
                elif current.kind in (POSITIONAL_ONLY, POSITIONAL_OR_KEYWORD) \
                    and last.default is not inspect.Parameter.empty \
                    and current.default is inspect.Parameter.empty:
                    raise SyntaxError(
                        'non-default FParameter follows default FParameter'
                    )

    def __init__(self, *args: FParameter, **kwargs: FParameter) -> None:
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
        return '<{} ({})>'.format(
            type(self).__name__,
            stringify_parameters(*self),
        )

    # Begin MutableSequence methods
    def __getitem__(
            self,
            key: typing.Union[int, slice],
        ) -> typing.Any:
        # typing.Union[FParameter, typing.Sequence[FParameter]]
        # https://github.com/python/mypy/issues/4108
        return self._data.__getitem__(key)

    def __setitem__(
            self,
            key: typing.Union[slice, int],
            value: typing.Union[typing.Iterable[FParameter], FParameter],
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

    def insert(self, index: int, value: FParameter) -> None:
        temp = list(self._data)
        temp.insert(index, value)
        self.validate(*temp)
        self._data = temp
    # End MutableSequence methods

    def __call__(
            self,
            callable: typing.Callable[..., types.FunctionType],
        ) -> typing.Callable[..., typing.Any]:
        # pylint: disable=W0622, redefined-builtin
        @functools.wraps(callable)
        def wrapper(*args, **kwargs):
            # pylint: disable=E1102, not-callable
            transformed = wrapper.__signature_mapper__(*args, **kwargs)
            return callable(*transformed.args, **transformed.kwargs)

        mapper = self.make_mapper(callable)
        wrapper.__signature_mapper__ = mapper  # type: ignore
        wrapper.__signature__ = mapper.sig_public  # type: ignore
        return wrapper

    @classmethod
    def from_signature(cls, signature: inspect.Signature) -> 'FSignature':
        # TODO: test
        # pylint: disable=E1101, no-member
        return cls(*[
            FParameter.from_parameter(param)
            for param in signature.parameters.values()
        ])

    @classmethod
    def from_callable(cls, callable: typing.Callable) -> 'FSignature':
        # pylint: disable=W0622, redefined-builtin
        return cls.from_signature(inspect.signature(callable))

    @property
    def context(self):
        return self[0] if self and self[0].is_contextual else None

    @property
    def var_positional(self):
        return get_var_positional_parameter(*self)

    @property
    def var_keyword(self):
        return get_var_keyword_parameter(*self)

    def make_signature(self, interface=False, return_annotation=void):
        return inspect.Signature(
            parameters=[
                fparams.interface_parameter \
                    if interface \
                    else fparams.parameter
                for fparams in self
            ],
            return_annotation=void_to_empty(return_annotation),
        )

    def make_mapper(
            self,
            callable: typing.Callable[..., typing.Any],
        ) -> 'SignatureMapper':
        # pylint: disable=W0622, redefined-builtin
        sig_private = inspect.signature(callable)
        sig_public = self.make_signature(
            return_annotation=sig_private.return_annotation,
        )
        sig_interface = self.make_signature(
            interface=True,
            return_annotation=sig_private.return_annotation,
        )

        return SignatureMapper(  # type: ignore
            callable=callable,
            sig_public=sig_public,
            parameter_transforms=self._data,
            parameter_mapping=map_parameters(self, inspect.signature(callable))
        )


class SignatureMapper(immutable.Struct):
    __slots__ = (
        'callable',
        'sig_public',
        'parameter_transforms',
        'parameter_mapping',
    )

    def __init__(
            self,
            callable: typing.Callable[..., typing.Any],
            sig_public: inspect.Signature,
            parameter_transforms: typing.Optional[typing.Iterable] = None,
            parameter_mapping: types.MappingProxyType = \
                types.MappingProxyType({})
        ) -> None:
        # pylint: disable=W0622, redefined-builtin
        # pylint: disable=R0913, too-many-arguments
        super().__init__(
            callable=callable,
            sig_public=sig_public,
            parameter_transforms=parameter_transforms,
            parameter_mapping=types.MappingProxyType(parameter_mapping or {}),
        )

    def __call__(
            self,
            *args: typing.Any,
            **kwargs: typing.Any
        ) -> typing.Any:
        try:
            pub_ba = self.sig_public.bind(*args, **kwargs)
        except TypeError as exc:
            raise TypeError(
                '{callable_name}() {message}'.format(
                    callable_name=self.callable.__name__,
                    message=exc.args[0],
                ),
            )

        pts = OrderedDict([(pt.name, pt) for pt in self.parameter_transforms])
        ctx = self._get_context(pub_ba.arguments)
        arguments = OrderedDict([
            (name, pts[name](ctx, name, value))
            for name, value in pub_ba.arguments.items()
        ])
        pub_ba.arguments.update(arguments)

        pri_ba = self.sig_private.bind_partial()
        pri_ba.apply_defaults()

        try:
            pri_var_po_name = get_var_positional_parameter(
                self.sig_private.parameters.values()
            )
        except AttributeError:
            pri_var_po_name = None

        try:
            pri_var_kw_name = get_var_keyword_parameter(
                self.sig_private.parameters.values()
            )
        except AttributeError:
            pri_var_kw_name = None

        try:
            pub_var_kw_name = get_var_keyword_parameter(
                self.sig_public.parameters.values()
            )
        except AttributeError:
            pub_var_kw_name = None


        for k, v in pub_ba.arguments.items():
            if k == pri_var_po_name:
                # only pub_var_po can map to pri_var_po
                pri_ba.arguments[pri_var_po_name] = v
            elif k == pri_var_kw_name:
                if k == pub_var_kw_name:
                    pri_ba.arguments[pri_var_kw_name][k] = v
                else:
                    pri_ba.arguments[pri_var_kw_name][k].update(v)
            else:
                pri_ba.arguments[k] = v

        return CallArguments.from_bound_arguments(pri_ba)

    def __repr__(self) -> str:
        pubstr = stringify_parameters(
            *self.sig_public.parameters.values()
        )
        privstr = stringify_parameters(
            *self.sig_private.parameters.values()
        )
        return '<{} ({}) -> ({})>'.format(type(self).__name__, pubstr, privstr)


    def _get_context(
            self,
            arguments: typing.MutableMapping[str, typing.Any]
        ) -> typing.Any:
        try:
            pt1 = self.parameter_transforms[0]
        except IndexError:
            return None
        return arguments[pt1.name] \
            if pt1.is_contextual \
            else None

    @property
    def sig_private(self):
        return inspect.signature(self.callable)