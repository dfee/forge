from abc import abstractmethod
import asyncio
import builtins
import functools
import inspect
import types
import typing

from forge._exceptions import RevisionError
import forge._immutable as immutable
from forge._marker import (
    empty,
    void,
)
from forge._signature import (
    CallArguments,
    FParameter,
    FSignature,
    _get_pk_string,
    get_var_keyword_parameter,
    get_var_positional_parameter,
)

# TODO: SortRevision

# TODO: remove
_revise_return_type = typing.Union[
    typing.List[FParameter],
    typing.Tuple[FParameter, ...],
]


class Mapper(immutable.Immutable):
    """
    An immutable data structure that provides the recipe for mapping
    an :class:`~forge.FSignature` to an underlying callable.

    :param fsignature: an instance of :class:`~forge.FSignature` that provides
        the public and private interface.
    :param callable: a callable that ultimately receives the arguments provided
        to public :class:`~forge.FSignature` interface.

    :ivar callable: see :paramref:`~forge._signature.Mapper.callable`
    :ivar fsignature: see :paramref:`~forge._signature.Mapper.fsignature`
    :ivar parameter_map: a :class:`types.MappingProxy` that exposes the strategy
        of how to map from the :paramref:`.Mapper.fsignature` to the
        :paramref:`.Mapper.callable`
    :ivar private_signature: a cached copy of
        :paramref:`~forge._signature.Mapper.callable`'s
        :class:`inspect.Signature`
    :ivar public_signature: a cached copy of
        :paramref:`~forge._signature.Mapper.fsignature`'s manifest as a
        :class:`inspect.Signature`
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
        public_signature = fsignature.native
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
        Maps the arguments from the :paramref:`~forge.Mapper.public_signature`
        to the :paramref:`~forge.Mapper.private_signature`.

        Follows the strategy:

        #. bind the arguments to the :paramref:`~forge.Mapper.public_signature`
        #. partialy bind the :paramref:`~forge.Mapper.private_signature`
        #. identify the context argument (if one exists) from
        :class:`~forge.FParameter`s on the :class:`~forge.FSignature`
        #. iterate over the intersection of bound arguments and ``bound`` \
        parameters on the :paramref:`.Mapper.fsignature` to the \
        :paramref:`~forge.Mapper.private_signature` of the \
        :parmaref:`.Mapper.callable`, getting their transformed value by \
        calling :meth:`~forge.FParameter.__call__`
        #. map the resulting value into the private_signature bound arguments
        #. generate and return a :class:`~forge._signature.CallArguments` from \
        the private_signature bound arguments.

        :param args: the positional arguments to map
        :param kwargs: the keyword arguments to map
        :return: transformed :paramref:`~forge.Mapper.__call__.args` and
            :paramref:`~forge.Mapper.__call__.kwargs` mapped from
            :paramref:`~forge.Mapper.public_signature` to
            :paramref:`~forge.Mapper.private_signature`
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
        public_ba.apply_defaults()

        private_ba = self.private_signature.bind_partial()
        private_ba.apply_defaults()
        ctx = self.get_context(public_ba.arguments)

        for from_name, from_param in self.fsignature.parameters.items():
            from_val = public_ba.arguments.get(from_name, empty)
            to_name = self.parameter_map[from_name]
            to_param = self.private_signature.parameters[to_name]
            to_val = self.fsignature.parameters[from_name](ctx, from_val)

            if to_param.kind is FParameter.VAR_POSITIONAL:
                # e.g. f(*args) -> g(*args)
                private_ba.arguments[to_name] = to_val
            elif to_param.kind is FParameter.VAR_KEYWORD:
                if from_param.kind is FParameter.VAR_KEYWORD:
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
        pubstr = str(self.public_signature)
        privstr = str(self.private_signature)
        return '<{} {} => {}>'.format(type(self).__name__, pubstr, privstr)

    def get_context(self, arguments: typing.Mapping) -> typing.Any:
        return arguments[self.fsignature.context.name] \
            if self.fsignature.context \
            else None

    @staticmethod
    def map_parameters(
            fsignature: FSignature,
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

        :param fsignature: the :class:`~forge.FSignature` to map from
        :param signature: the :class:`inspect.Signature` to map to
        :return: a :class:`types.MappingProxyType` that shows how arguments
            are mapped.
        '''
        # pylint: disable=W0622, redefined-builtin
        # TODO: fsignature / signature -> from_ / to_
        fparam_vpo = fsignature.var_positional
        fparam_vkw = fsignature.var_keyword
        fparam_idx = {
            fparam.interface_name: fparam
            for fparam in fsignature.parameters.values()
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
                if param.default is not empty.native:
                    continue

                # invalid mapping, e.g. f() -> g(a)
                kind_repr = _get_pk_string(param.kind)
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
                kind_repr = _get_pk_string(FParameter.VAR_POSITIONAL)
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
                kind_repr = _get_pk_string(FParameter.VAR_KEYWORD)
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


class FParameterSelector:
    """
    Takes a selector (a string, an iterable of strings, or a callable that
    receives an instance of :class:`~forge.FParameter` and returns a boolean
    reflecting whether a match was made.

    :param selector: a string, iterable of strings, or a callable to match
        an instance of :class:`~forge.FParameter` against. If the value is a
        string than it's matched against :paramref:`~forge.FParameter.name`.
    :return: a boolean if the :class:`~forge.FParameter` matched
    """
    def __init__(
            self,
            selector: typing.Union[
                str,
                typing.Iterable[str],
                typing.Callable[[FParameter], bool],
            ],
        ) -> None:
        self.selector = selector

    def __call__(self, parameter: FParameter) -> bool:
        if isinstance(self.selector, str):
            return self.selector == parameter.name
        elif isinstance(self.selector, typing.Iterable):
            return parameter.name in self.selector
        return self.selector(parameter) # self.selector is a callable

    def __repr__(self) -> str:
        return '<{} {}>'.format(type(self).__name__, self.selector)


class BaseRevision:
    """
    Functions as an identity revision
    """
    @abstractmethod
    def revise(self, previous: FSignature) -> FSignature:
        raise NotImplementedError()

    def __call__(
            self,
            callable: typing.Callable[..., typing.Any]
        ) -> typing.Callable[..., typing.Any]:
        """
        Wraps a callable with a function that maps the new signature's
        parameters to the original function's signature.

        If the function was already wrapped (has an :attr:`__mapper__`
        attribute), then the signature and mapper are replaced, but the
        function is not rewrapped.

        :param callable: a :term:`callable` whose signature to revise
        :return: a function with the revised signature that calls into the
            provided :paramref:`~forge.BaseRevision.__call__.callable`
        """
        # pylint: disable=W0622, redefined-builtin
        if hasattr(callable, '__mapper__'):
            existing = True
            prev_ = callable.__mapper__.fsignature  # type: ignore
        else:
            existing = False
            prev_ = FSignature.from_callable(callable)

        next_ = self.revise(prev_)

        # Previously revised; already wrapped
        if existing:
            mapper = Mapper(next_, callable.__wrapped__)  # type: ignore
            callable.__mapper__ = mapper  # type: ignore
            callable.__signature__ = mapper.public_signature  # type: ignore
            return callable

        # Unrevised; not wrapped
        @functools.wraps(callable)
        def inner(*args, **kwargs):
            # pylint: disable=E1102, not-callable
            mapped = inner.__mapper__(*args, **kwargs)
            return callable(*mapped.args, **mapped.kwargs)

        if inspect.iscoroutinefunction(callable):
            inner = asyncio.coroutine(inner)

        inner.__mapper__ = Mapper(next_, callable)  # type: ignore
        inner.__signature__ = inner.__mapper__.public_signature  # type: ignore
        return inner


class BatchRevision(BaseRevision):
    def __init__(self, *revisions):
        for rev in revisions:
            if not isinstance(rev, BaseRevision):
                raise TypeError("received non-revision '{}'".format(rev))
        self.revisions = revisions

    def revise(
            self,
            *previous: FParameter
        ) -> _revise_return_type:
        return functools.reduce(
            lambda previous, revision: revision.revise(*previous),
            self.revisions,
            previous,
        )


class IdentityRevision(BaseRevision):
    def revise(
            self,
            *previous: FParameter
        ) -> _revise_return_type:
        return previous


class SynthesizeRevision(BaseRevision):
    """
    Revision that builds a new signature from instances of
    :class:`~forge.FParameter`

    Order parameters with the following strategy:

    #. arguments are returned in order
    #. keyword arguments are sorted by ``_creation_order``, and evolved with \
    the ``keyword`` value as the name and interface_name (if not set).

    .. warning::

        When supplying previously-created parameters to :func:`~forge.sign` or
        :func:`~forge.resign`, those parameters will be ordered by their
        creation order.

        This is because Python implementations prior to ``3.7`` don't
        guarantee the ordering of keyword-arguments.

        Therefore, it is recommended that when supplying pre-created
        parameters to :func:`~forge.sign` or :func:`~forge.resign` to supply
        them as positional arguments:

        .. testcode::

            import forge

            param_b = forge.arg('b')
            param_a = forge.arg('a')

            @forge.sign(a=param_a, b=param_b)
            def func1(**kwargs):
                pass

            @forge.sign(param_a, param_b)
            def func2(**kwargs):
                pass

            assert forge.stringify_callable(func1) == 'func1(b, a)'
            assert forge.stringify_callable(func2) == 'func2(a, b)'

    :param parameters: :class:`~forge.FParameter` instances to be ordered
    :param named_parameters: :class:`~forge.FParameter` instances to be
        ordered, updated
    :return: a wrapping factory that takes a callable and updates it so that
        it has a signature as defined by the
        :paramref:`.resign.parameters` and
        :paramref:`.resign.named_parameters`
    """
    def __init__(self, *parameters, **named_parameters):
        self.parameters = [
            *parameters,
            *[
                param.replace(
                    name=name,
                    interface_name=param.interface_name or name,
                ) for name, param in sorted(
                    named_parameters.items(),
                    key=lambda i: i[1]._creation_order,
                )
            ]
        ]

    def revise(self, previous: FSignature) -> FSignature:
        """
        Produces a signature with the parameters provided at initialization.

        :param previous: previous signature
        :return: updated signature
        """
        return previous.replace(parameters=self.parameters)


class DeleteRevision(BaseRevision):
    def __init__(self, selector):
        self.selector = FParameterSelector(selector)

    def revise(
            self,
            *previous: FParameter
        ) -> _revise_return_type:
        next_, selected = [], None
        for prev in previous:
            if self.selector(prev):
                selected = prev
                continue
            next_.append(prev)

        if not selected:
            raise RevisionError('cannot delete parameter: not found')
        return next_


class InsertRevision(BaseRevision):
    def __init__(self, parameter, *, index=None, before=None, after=None):
        provided = dict(filter(
            lambda i: i[1] is not None,
            {'index': index, 'before': before, 'after': after}.items(),
        ))
        if not provided:
            raise TypeError(
                "expected keyword argument 'index', 'before', or 'after'"
            )
        elif len(provided) > 1:
            raise TypeError(
                "expected 'index', 'before' or 'after' received multiple"
            )

        self.parameter = parameter
        self.index = index
        self.before = FParameterSelector(before) if before else None
        self.after = FParameterSelector(after) if after else None

    def revise(
            self,
            *previous: FParameter
        ) -> _revise_return_type:
        if self.before:
            next_, visited = [], False
            for prev in previous:
                if not visited and self.before(prev):
                    visited = True
                    next_.append(self.parameter)
                next_.append(prev)
            if not visited:
                raise RevisionError(
                    'cannot insert {fp} before selector; selector not found'.\
                    format(fp=self.parameter)
                )

        elif self.after:
            next_, visited = [], False
            for prev in previous:
                next_.append(prev)
                if not visited and self.after(prev):
                    visited = True
                    next_.append(self.parameter)
            if not visited:
                raise RevisionError(
                    'cannot insert {fp} after selector; selector not found'.\
                    format(fp=self.parameter)
                )

        else:
            next_ = list(previous)
            next_.insert(self.index, self.parameter)

        return next_


class ModifyRevision(BaseRevision):
    def __init__(
            self,
            selector,
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
        # pylint: disable=W0622, redefined-builtin
        self.selector = selector
        self.updates = {
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
        }

    def revise(
            self,
            *previous: FParameter
        ) -> _revise_return_type:
        if callable(self.selector):
            return [
                prev.replace(**self.updates) \
                    if self.selector(prev) \
                    else prev
                for prev in previous
            ]
        return [
            prev.replace(**self.updates) \
                if prev.name == self.selector \
                else prev
            for prev in previous
        ]


class TranslocateRevision(BaseRevision):
    def __init__(self, selector, *, index=None, before=None, after=None):
        provided = dict(filter(
            lambda i: i[1] is not None,
            {'index': index, 'before': before, 'after': after}.items(),
        ))
        if not provided:
            raise TypeError(
                'expected keyword argument `index`, `before`, or `after`'
            )
        elif len(provided) > 1:
            raise TypeError(
                'expected `index`, `before` or `after` received multiple'
            )

        self.selector = FParameterSelector(selector)
        self.index = index
        self.before = FParameterSelector(before) if before else None
        self.after = FParameterSelector(after) if after else None

    def revise(
            self,
            *previous: FParameter
        ) -> _revise_return_type:
        if self.before:
            next_, selected, idx = [], None, None
            for i, prev in enumerate(previous):
                if not selected and self.selector(prev):
                    selected = prev
                    continue
                if idx is None and self.before(prev):
                    idx = i if not selected else i - 1
                next_.append(prev)
            if not selected:
                raise TypeError(
                    "Cannot move as 'selector' failed to match parameter"
                )
            elif not idx:
                raise TypeError(
                    "Cannot move as 'before' failed to match parameter"
                )
            next_.insert(idx, selected)

        elif self.after:
            next_, selected, idx = [], None, None
            for i, prev in enumerate(previous):
                if not selected and self.selector(prev):
                    selected = prev
                    continue
                if idx is None and self.after(prev):
                    idx = i + 1 if not selected else i
                next_.append(prev)
            if not selected:
                raise TypeError(
                    "Cannot move as 'selector' failed to match parameter"
                )
            elif not idx:
                raise TypeError(
                    "Cannot move as 'after' failed to match parameter"
                )
            next_.insert(idx, selected)

        else:
            next_, selected = [], None
            for prev in previous:
                if not selected and self.selector(prev):
                    selected = prev
                    continue
                next_.append(prev)
            if not selected:
                raise TypeError(
                    "Cannot translocate as 'selector' failed to match "
                    "parameter"
                )
            next_.insert(self.index, selected)

        return next_


class ManageRevision(BaseRevision):
    """
    Revision that takes a function for parameter processing. Example:

    .. testcode::

        import forge

        def reverse(*previous):
            return previous[::-1]

        @forge.manage(reverse)
        def func(a, b, c):
            pass

        assert forge.stringify_callable(func) == 'func(c, b, a)'

    :param callable: a user supplied callable for enhanaced processing of the
        fparameters. Should have the signature: ()
    """
    def __init__(
            self,
            callable: typing.Callable[..., _revise_return_type]
        ) -> None:
        # pylint: disable=W0622, redefined-builtin
        self.callable = callable

    def revise(
            self,
            *previous: FParameter
        ) -> _revise_return_type:
        """
        Returns with a call to the user supplied :term:`callable`,
        :paramref:`~forge._compose.ManageRevision.callable`

        :param previous: previous :class:`~forge.FParameter` instances
        :return: :class:`~forge.FParameter` instances for building a new
            :class:`~forge.FSignature`
        """
        return self.callable(*previous)


class CopyRevision(BaseRevision):
    def __init__(self, callable, *, include=None, exclude=None):
        # pylint: disable=W0622, redefined-builtin
        if include is not None and exclude is not None:
            raise TypeError(
                "expected 'include' or 'exclude', but received both"
            )

        self.callable = callable
        if include is not None:
            self.include = include \
                if builtins.callable(include) \
                else lambda param: param.name in include
            self.exclude = None
        elif exclude is not None:
            self.exclude = exclude \
                if builtins.callable(exclude) \
                else lambda param: param.name in exclude
            self.include = None
        else:
            self.include = None
            self.exclude = None


    def revise(
            self,
            *previous: FParameter
        ) -> _revise_return_type:
        fsig = FSignature.from_callable(self.callable)
        if self.include:
            return [fp for fp in fsig.values() if self.include(fp)]
        elif self.exclude:
            return [fp for fp in fsig.values() if not self.exclude(fp)]
        return list(fsig.values())


class ReplaceRevision(BaseRevision):
    def __init__(self, selector, parameter):
        self.selector = FParameterSelector(selector)
        self.parameter = parameter

    def revise(
            self,
            *previous: FParameter
        ) -> _revise_return_type:
        return [
            self.parameter if self.selector(prev) else prev
            for prev in previous
        ]


def returns(
        type: typing.Any = empty
    ) -> typing.Callable[[typing.Callable[..., typing.Any]], typing.Any]:
    """
    Produces a factory that updates callables' signatures to reflect a  new
    ``return-type`` annotation

    :param type: the ``return-type`` for the factory
    :return: a factory that takes a callable and updates it to reflect
        the ``return-type`` as provided to :paramref:`.returns.type`
    """
    # TODO: revise impl after update "Revision"
    # pylint: disable=W0622, redefined-builtin
    def inner(callable):
        # pylint: disable=W0622, redefined-builtin
        set_return_type(callable, empty.ccoerce_native(type))
        return callable
    return inner