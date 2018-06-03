from abc import abstractmethod
import asyncio
import builtins
import functools
import inspect
import typing

from forge._exceptions import RevisionError
from forge._marker import (
    empty,
    void,
)
from forge._parameter import FParameter
from forge._signature import (
    FSignature,
    Mapper,
)

# TODO: SortRevision
# TODO: "Compose -> Revise"


_revise_return_type = typing.Union[
    typing.List[FParameter],
    typing.Tuple[FParameter, ...],
]


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

    def __call__(self, fparameter: FParameter) -> bool:
        if isinstance(self.selector, str):
            return self.selector == fparameter.name
        elif isinstance(self.selector, typing.Iterable):
            return fparameter.name in self.selector
        # else: self.selector is a callable
        return self.selector(fparameter)

    def __repr__(self) -> str:
        return '<{} {}>'.format(type(self).__name__, self.selector)


class BaseRevision:
    """
    Functions as an identity revision
    """
    @abstractmethod
    def revise(
            self,
            *previous: FParameter
        ) -> _revise_return_type:
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
            fsig = callable.__mapper__.fsignature  # type: ignore
        else:
            existing = False
            fsig = FSignature.from_callable(callable)

        fparams = self.revise(*fsig.values())
        fsignature = FSignature(fparams)

        # Previously revised; already wrapped
        if existing:
            mapper = Mapper(fsignature, callable.__wrapped__)  # type: ignore
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

        inner.__mapper__ = Mapper(fsignature, callable)  # type: ignore
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

    Order fparameters with the following strategy:

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

    :param fparameters: :class:`~forge.FParameter` instances to be ordered
    :param named_fparameters: :class:`~forge.FParameter` instances to be
        ordered, updated
    :return: a wrapping factory that takes a callable and updates it so that
        it has a signature as defined by the
        :paramref:`.resign.fparameters` and
        :paramref:`.resign.named_fparameters`
    """
    def __init__(self, *fparameters, **named_fparameters):
        self.fparameters = [
            *fparameters,
            *[
                fparam.replace(
                    name=name,
                    interface_name=fparam.interface_name or name,
                ) for name, fparam in sorted(
                    named_fparameters.items(),
                    key=lambda i: i[1]._creation_order,
                )
            ]
        ]

    def revise(
            self,
            *previous: FParameter
        ) -> _revise_return_type:
        """
        Returns the :class:`~forge.FParameter<FParameters>` from initialization

        :param previous: previous :class:`~forge.FParameter` instances
        :return: :class:`~forge.FParameter` instances for building a new
            :class:`~forge.FSignature`
        """
        return self.fparameters


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
    def __init__(self, fparameter, *, index=None, before=None, after=None):
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

        self.fparameter = fparameter
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
                    next_.append(self.fparameter)
                next_.append(prev)
            if not visited:
                raise RevisionError(
                    'cannot insert {fp} before selector; selector not found'.\
                    format(fp=self.fparameter)
                )

        elif self.after:
            next_, visited = [], False
            for prev in previous:
                next_.append(prev)
                if not visited and self.after(prev):
                    visited = True
                    next_.append(self.fparameter)
            if not visited:
                raise RevisionError(
                    'cannot insert {fp} after selector; selector not found'.\
                    format(fp=self.fparameter)
                )

        else:
            next_ = list(previous)
            next_.insert(self.index, self.fparameter)

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
    def __init__(self, selector, fparameter):
        self.selector = FParameterSelector(selector)
        self.fparameter = fparameter

    def revise(
            self,
            *previous: FParameter
        ) -> _revise_return_type:
        return [
            self.fparameter if self.selector(prev) else prev
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