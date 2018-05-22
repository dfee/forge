from collections import OrderedDict
import collections.abc
import functools
import inspect
import types
import typing

import forge._immutable as immutable
from forge._marker import (
    coerce_if,
    void,
    void_to_empty,
)
from forge._parameter import (
    POSITIONAL_ONLY,
    POSITIONAL_OR_KEYWORD,
    VAR_KEYWORD,
    VAR_POSITIONAL,
    FParameter,
    empty,
    pk_strings,
)
from forge._utils import (
    get_return_type,
    get_var_positional_parameter,
    get_var_keyword_parameter,
    set_return_type,
    stringify_parameters,
)


class CallArguments(immutable.Immutable):
    """
    An immutable container for call arguments, i.e. term:`var-positional`
    (e.g. `*args``) and :term:`var-keyword` (e.g. **kwargs``).

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
        A factory method that creates an instance of :class:`.CallArguments`
        from an instance of :class:`instance.BoundArguments` generated from
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


class FSignature(collections.abc.Mapping, immutable.Immutable):
    """
    An immutable representation of a callable signature composed of
    :class:`forge.FParameter` instances.`

    Unliked :class:`inspect.Signature`, :class:`FSignature` does not provide or
    manage ``return type`` annotations. That is the work of :func:`.returns`
    and / or :class:`.Mapper`.

    .. note::

        This class doesn't usually need to be invoked directly. Use one of the
        constructor methods instead:

        - :func:`~forge.sign` to wrap a callable with a :class:`.FSignature`.
        - :func:`~forge.resign` to revise a wrapped callable's \
        :class:`.FSignature`.
        - :func:`~forge.FSignature.from_callable` to generate a \
        :class:`.FSignature` from any Python callable.
        - :func:`~forge.FSignature.from_signature` to generate a \
        :class:`.FSignature` from a :class:`inspect.Signature`.

    Implements :class:`collections.abc.Mapping`, with provided: ``__getitem__``,
    ``__iter__`` and ``__len__``. Inherits methods: ``__contains__``, ``keys``,
    ``items``, ``values``, ``get``, ``__eq__`` and ``__ne__``.

    :param fparameters: :class:`forge.FParameter` instances passed as arguments
    :param named_fparameters: :class:`forge.FParameter` instances passed as
        as keyword arguments.
    """

    # pylint: disable=R0901, too-many-ancestors
    @staticmethod
    def validate(*fparameters: FParameter) -> None:
        """
        Validate an ordered sequence of :class:`forge.FParameter` instances for
        use with a :class:`forge.FSignature`.

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

        - that at most there is one :term:`contextual` parameter, and that it
        is the first parameter (if it is provided.)

        - that no two :class:`FParameter`s share the same
        :paramref:`.FParameter.name` or :paramref:`.FParameter.interface_name`.

        :param fparameters: a sequence of :class:`forge.FParameter` instances
        """
        pname_set: typing.Set[str] = set()
        iname_set: typing.Set[str] = set()
        for i, current in enumerate(fparameters):
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

            last = fparameters[i-1] if i > 0 else None
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
        # TODO: remove
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
        """
        Concrete method for :class:`collections.abc.Mapping`

        :param key: a key that corresponds to a :paramref:`.FParameter.name`
        :raises KeyError: if an instance of :class:`FParameter` with
            :paramref:`.FParameter.name` doesn't exist on this
            :class:`FSignature`.
        :return: the instance of :class:`FParameter.name` for which
            :paramref:`.FSignature.__getitem__.key` corresponds.
        """
        return self._data[key]

    def __iter__(self) -> typing.Iterator:
        """
        Concrete method for :class:`collections.abc.Mapping`

        :return: an iterator over this instance which maps
            :paramref:`.FParameter.name` to a :class:`FParameter`.
        """
        return iter(self._data)

    def __len__(self) -> int:
        """
        Concrete method for :class:`collections.abc.Mapping`

        :return: the number of parameters in this :class:`FSignature` instance.
        """
        return len(self._data)
    # End Mapping methods

    @classmethod
    def from_signature(cls, signature: inspect.Signature) -> 'FSignature':
        """
        A factory method that creates an instance of :class:`FSignature` from
        an instance of :class:`inspect.Signature`. Calls down to
        :class:`FParameter` to map the :attr:`inspect.Signature.parameters`
        to :class:`inspect.Parameter` instances.

        The ``return type`` annotation from the provided signature is not
        retained, as :meth:`FSignature.from_signature` doesn't provide this
        functionality.

        :param signature: an instance of :class:`inspect.Signature` from which
            to derive the :class:`FSignature`
        :return: an instance of :class:`FSignature` derived from the
            :paramref:`.FSignature.from_signature.signature` argument.
        """
        # pylint: disable=E1101, no-member
        return cls(*[
            FParameter.from_parameter(param)
            for param in signature.parameters.values()
        ])

    @classmethod
    def from_callable(cls, callable: typing.Callable) -> 'FSignature':
        """
        A factory method that creates an instance of :class:`FSignature` from
        a callable. Calls down to :meth:`.FSignature.from_signature` to do the
        heavy loading.

        :param callable: a callable from which to derive the :class:`FSignature`
        :return: an instance of :class:`FSignature` derived from the
            :paramref:`.FSignature.from_callable.callable` argument.
        """
        # pylint: disable=W0622, redefined-builtin
        return cls.from_signature(inspect.signature(callable))


class Mapper(immutable.Immutable):
    """
    An immutable data structure that provides the recipe for mapping
    an :class:`FSignature` to an underlying callable.

    :param fsignature: an instance of :class:`FSignature` that provides the
        public and private interface.
    :param callable: a callable that ultimately receives the arguments provided
        to public :class:`FSignature` interface.

    :ivar callable: see :paramref:`.Mapper.callable`
    :ivar fsignature: see :paramref:`.Mapper.fsignature`
    :ivar parameter_map: a :class:`types.MappingProxy` that exposes the strategy
        of how to map from the :paramref:`.Mapper.fsignature` to the
        :paramref:`.Mapper.callable`
    :ivar private_signature: a cached copy of :paramref:`.Mapper.callable`'s
        :class:`inspect.Signature`
    :ivar public_signature: a cached copy of :paramref:`.Mapper.fsignature`'s
        manifest as a :class:`inspect.Signature`
    """
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
        ) -> CallArguments:
        """
        Maps the arguments from the :attr:`.Mapper.public_signature` to the
        :attr:`.Mapper.private_signature`.

        Follows the strategy:

        #. bind the arguments to the :attr:`.Mapper.public_signature`
        #. partialy bind the :attr:`.Mapper.private_signature`
        #. identify the context argument (if one exists) from
        :class:`FParameter`s on the :class:`.FSignature`
        #. iterate over the intersection of bound arguments and ``bound``
        parameters on the :paramref:`.Mapper.fsignature` to the
        :attr:`.Mapper.private_signature` of the :parmaref:`.Mapper.callable`,
        getting their transformed value by calling
        :meth:`~forge.FParameter.__call__`
        #. map the resulting value into the private_signature bound arguments
        #. generate and return a :class:`CallArguments` from the
        private_signature bound arguments.

        :param args: the positional arguments to map
        :param kwargs: the keyword arguments to map
        :return: transformd :paramref:`.Mapper.__call__.args` and
            :paramref:`.Mapper.__call__.kwargs` mapped from
            :attr:`.Mapper.public_signature` to
            :attr:`.Mapper.private_signature`
        """
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
        # TODO: test defaults applied, *args, **kwargs, etc.
        public_ba.apply_defaults()

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
                    private_ba.arguments[to_name].update(
                        coerce_if(lambda i: i == {}, to_val, empty)
                    )
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
        ) -> types.MappingProxyType:
        '''
        Build a mapping of parameters from the
        :paramref:`.Mapper.map_parameters.fsignature` to the
        :paramref:`.Mapper.map_parameters.signature`.

        Strategy rules:
        #. every *to_* :term:`positional-only` must be mapped to
        #. every *to_* :term:`positional-or-keyword` w/o default must be
        mapped to
        #. every *to_* :term:`keyword-only` w/o default must be mapped to
        #. *from_* :term:`var-positional` requires *to_* :term:`var-positional`
        #. *from_* :term:`var-keyword` requires *to_* :term:`var-keyword`

        :param fsignature: the :class:`FSignature` to map from
        :param signature: the :class:`inspect.Signature` to map to
        :return: a :class:`types.MappingProxyType` that shows how arguments
            are mapped.
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
    """
    Takes instances of :class:`~forge.FParameter` and returns a wrapping factory
    to generate forged signatures.

    :param fparameters: see :paramref:`.FSignature.fparameters`
    :param named_fparameters: see :paramref:`.FSignature.named_fparameters`
    :return: a revision factory that takes a callable and updates it so that
        it has a signature as defined by the
        :paramref:`.resign.fparameters` and
        :paramref:`.resign.named_fparameters`
    """
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
    """
    Takes instances of :class:`~forge.FParameter` and returns a revision factory
    that alters already-forged signatures.

    :param fparameters: see :paramref:`.FSignature.fparameters`
    :param named_fparameters: see :paramref:`.FSignature.named_fparameters`
    :return: a revision factory that takes a callable and updates it so that
        it has a signature as defined by the
        :paramref:`.resign.fparameters` and
        :paramref:`.resign.named_fparameters`
    """
    fsignature = FSignature(*fparameters, **named_fparameters)
    def reviser(callable):
        # pylint: disable=W0622, redefined-builtin
        callable.__mapper__ = Mapper(fsignature, callable.__wrapped__)
        callable.__signature__ = callable.__mapper__.public_signature
        return callable
    return reviser


def returns(
        type: typing.Any = void
    ) -> typing.Callable[[typing.Callable[..., typing.Any]], typing.Any]:
    """
    Produces a factory that updates callables' signatures to reflect a  new
    ``return-type`` annotation

    :param type: the ``return-type`` for the factory
    :return: a factory that takes a callable and updates it to reflect
        the ``return-type`` as provided to :paramref:`.returns.type`
    """
    # pylint: disable=W0622, redefined-builtin
    def inner(callable):
        # pylint: disable=W0622, redefined-builtin
        set_return_type(callable, void_to_empty(type))
        return callable
    return inner