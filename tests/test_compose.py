import asyncio
from unittest.mock import Mock
import inspect

import pytest

import forge
from forge._compose import (
    Mapper,
    BaseRevision,
    BatchRevision,
    CopyRevision,
    IdentityRevision,
    InsertRevision,
    DeleteRevision,
    ManageRevision,
    ModifyRevision,
    ReplaceRevision,
    SynthesizeRevision,
    TranslocateRevision,
    returns,
)
from forge._exceptions import RevisionError
from forge._marker import empty
from forge._signature import (
    KEYWORD_ONLY,
    POSITIONAL_ONLY,
    POSITIONAL_OR_KEYWORD,
    VAR_KEYWORD,
    VAR_POSITIONAL,
    CallArguments,
    FParameter,
    FSignature,
    _get_pk_string,
)


# pylint: disable=R0201, no-self-use
# pylint: disable=W0621, redefined-outer-name


def assert_params(func, *names):
    assert list(func.__signature__.parameters) == list(names)


@pytest.fixture
def _func():
    return lambda b, c=0, **kwargs: None


@pytest.fixture(params=[True, False])
def func(request, _func):
    """
    Determines wheter _func is @forge.sign'd
    """
    # TODO: remove
    return _func \
        if not request.param \
        else forge.copy(_func)(_func)


# class TestReturns:
#     def test_no__signature__(self):
#         """
#         Ensure we can set the ``return type`` annotation on a function without
#         a ``__signature__``
#         """
#         @returns(int)
#         def myfunc():
#             pass
#         assert myfunc.__annotations__.get('return') == int

#     def test__signature__(self):
#         """
#         Ensure we can set the ``return type`` annotation on a function with
#         a ``__signature__``
#         """
#         def myfunc():
#             pass
#         myfunc.__signature__ = inspect.Signature()

#         myfunc = returns(int)(myfunc)
#         assert myfunc.__signature__.return_annotation == int


class BaseTestRevision:
    def run_strategy(self, strategy, revision, func):
        fsig = forge.fsignature(func)
        if strategy == 'revise':
            return list(revision.revise(*fsig.values()))
        elif strategy == '__call__':
            func2 = revision(func)
            return forge.fsignature(func2)[:]
        else:
            raise TypeError('unknown strategy {}'.format(strategy))


class TestRevision:
    @pytest.mark.parametrize(('as_coroutine',), [(True,), (False,)])
    def test__call__not_existing(self, loop, as_coroutine):
        """
        Ensure ``sign`` wrapper appropriately builds and sets ``__mapper__``,
        and that a call to the wrapped func traverses ``Mapper.__call__`` and
        the wrapped function.
        """
        # pylint: disable=W0108, unnecessary-lambda
        rev = BaseRevision()
        rev.revise = lambda sig: sig
        func = lambda *args, **kwargs: CallArguments(*args, **kwargs)
        if as_coroutine:
            func = asyncio.coroutine(func)

        func2 = rev(func)
        assert isinstance(func2.__mapper__, Mapper)
        assert isinstance(func2.__signature__, inspect.Signature)

        mapper = func2.__mapper__
        assert mapper.callable == func2.__wrapped__
        assert mapper.fsignature == FSignature([
            forge.vpo('args'),
            forge.vkw('kwargs'),
        ])
        assert mapper == Mapper(mapper.fsignature, func2.__wrapped__)

        func2.__mapper__ = Mock(side_effect=func2.__mapper__)
        call_args = CallArguments(0, a=1)

        result = func2(*call_args.args, **call_args.kwargs)
        if as_coroutine:
            result = loop.run_until_complete(result)

        assert result == call_args
        func2.__mapper__.assert_called_once_with(
            *call_args.args,
            **call_args.kwargs,
        )

    def test__call__existing(self):
        """
        Ensure ``__call__`` replaces the ``__mapper__``, and that a call to the
        wrapped func traverses only the new ``Mapper.__call__`` and the
        wrapped function; i.e. no double wrapping.
        """
        rev = BaseRevision()
        rev.revise = lambda sig: sig
        # pylint: disable=W0108, unnecessary-lambda
        func = lambda **kwargs: CallArguments(**kwargs)

        func2 = rev(func)
        mapper1 = func2.__mapper__
        func3 = rev(func2)
        mapper2 = func3.__mapper__

        assert func3 is func2
        assert isinstance(mapper2, Mapper)
        assert mapper2 is not mapper1
        assert mapper2.fsignature == mapper1.fsignature

        call_args = CallArguments(b=1)
        func3.__mapper__ = Mock(side_effect=mapper2)
        assert func3(*call_args.args, **call_args.kwargs) == call_args
        func3.__mapper__.assert_called_once_with(**call_args.kwargs)


def test_identity_revision():
    rev = IdentityRevision()
    in_ = (forge.arg('a'),)
    assert rev.revise(*in_) == in_


# class TestSynthesizeRevision:
#     def test_args_order_preserved(self):
#         """
#         Ensure that the var-positional arguments *aren't* re-ordered
#         """
#         param_a = forge.arg('a')
#         param_b = forge.arg('b')
#         rev = SynthesizeRevision(param_b, param_a)
#         assert rev.fparameters == [param_b, param_a]

#     def test_kwargs_reordered(self):
#         """
#         Ensure that the var-keyword arguments *are* re-ordered
#         """
#         param_a = forge.arg('a')
#         param_b = forge.arg('b')
#         rev = SynthesizeRevision(b=param_b, a=param_a)
#         assert rev.fparameters == [param_a, param_b]

#     def test_args_precede_kwargs(self):
#         """
#         Ensure that var-postional arguments precede var-keyword arguments
#         """
#         param_a = forge.arg('a')
#         param_b = forge.arg('b')
#         rev = SynthesizeRevision(param_b, a=param_a)
#         assert rev.fparameters == [param_b, param_a]


# class TestBatchRevision(BaseTestRevision):
#     @pytest.mark.parametrize(('strategy',), [('revise',), ('__call__',)])
#     @pytest.mark.parametrize(('revisions', 'expected'), [
#         # Empty
#         pytest.param(
#             [
#                 InsertRevision(forge.arg('a'), index=-1),
#                 TranslocateRevision('a', index=0),
#             ],
#             ('a', 'b', 'c', 'kwargs'),
#             id='multiple',
#         ),

#         # None
#         pytest.param(
#             [],
#             ('b', 'c', 'kwargs'),
#             id='none',
#         ),

#     ])
#     def test_revision(self, strategy, revisions, expected):
#         revision = BatchRevision(*revisions)
#         func = lambda b, c=0, **kwargs: None

#         possible = {
#             param.name: param for param in [
#                 forge.arg('a'),
#                 forge.arg('b'),
#                 forge.arg('c', default=0),
#                 forge.vkw('kwargs'),
#             ]
#         }

#         assert self.run_strategy(strategy, revision, func) == \
#             [possible[e] for e in expected]


#     def test_non_revision_raises(self):
#         with pytest.raises(TypeError) as excinfo:
#             BatchRevision(1)
#         assert excinfo.value.args[0] == "received non-revision '1'"


# class TestDeleteRevision(BaseTestRevision):
#     @pytest.mark.parametrize(('strategy',), [('revise',), ('__call__',)])
#     @pytest.mark.parametrize(('selector', 'expected'), [
#         pytest.param(
#             'c',
#             ('a', 'b'),
#             id='string',
#         ),
#         pytest.param(
#             lambda param: param.name == 'c',
#             ('a', 'b'),
#             id='callable',
#         ),
#         pytest.param(
#             lambda param: False,
#             RevisionError('cannot delete parameter: not found'),
#             id='param_not_found',
#         )
#     ])
#     def test_revision(self, strategy, selector, expected):
#         revision = DeleteRevision(selector)
#         func = lambda a, b, c=0: None

#         if isinstance(expected, RevisionError):
#             with pytest.raises(type(expected)) as excinfo:
#                 self.run_strategy(strategy, revision, func)
#             assert excinfo.value.args[0] == expected.args[0]
#             return

#         possible = {
#             param.name: param for param in [
#                 forge.arg('a'),
#                 forge.arg('b'),
#                 forge.arg('c', default=0),
#             ]
#         }

#         assert self.run_strategy(strategy, revision, func) == \
#             [possible[e] for e in expected]


# class TestInsertRevision(BaseTestRevision):
#     @pytest.mark.parametrize(('strategy',), [('revise',), ('__call__',)])
#     @pytest.mark.parametrize(('kwargs', 'expected'), [
#         # index
#         pytest.param(
#             dict(index=0),
#             ('a', 'b', 'c', 'kwargs'),
#             id='index',
#         ),

#         # before
#         pytest.param(
#             dict(before='b'),
#             ('a', 'b', 'c', 'kwargs'),
#             id='before_string',
#         ),
#         pytest.param(
#             dict(before=lambda param: param.name == 'b'),
#             ('a', 'b', 'c', 'kwargs'),
#             id='before_callable',
#         ),
#         pytest.param(
#             dict(before=lambda param: True),
#             ('a', 'b', 'c', 'kwargs'),
#             id='before_multi_match',
#         ),
#         pytest.param(
#             dict(before=lambda param: False),
#             RevisionError(
#                 'cannot insert {fp} before selector; selector not found'
#             ),
#             id='before_not_found_raises',
#         ),

#         # after
#         pytest.param(
#             dict(after='b'),
#             ('b', 'a', 'c', 'kwargs'),
#             id='after_string',
#         ),
#         pytest.param(
#             dict(after=lambda param: param.name == 'b'),
#             ('b', 'a', 'c', 'kwargs'),
#             id='after_callable',
#         ),
#         pytest.param(
#             dict(after=lambda param: True),
#             ('b', 'a', 'c', 'kwargs'),
#             id='after_multi_match',
#         ),
#         pytest.param(
#             dict(after=lambda param: False),
#             RevisionError(
#                 'cannot insert {fp} after selector; selector not found'
#             ),
#             id='after_not_found_raises',
#         ),

#     ])
#     def test_revision(self, strategy, kwargs, expected):
#         fparam = forge.arg('a')
#         revision = InsertRevision(fparam, **kwargs)
#         func = lambda b, c=0, **kwargs: None

#         possible = {
#             param.name: param for param in [
#                 forge.arg('a'),
#                 forge.arg('b'),
#                 forge.arg('c', default=0),
#                 forge.vkw('kwargs'),
#             ]
#         }

#         if isinstance(expected, Exception):
#             with pytest.raises(type(expected)) as excinfo:
#                 self.run_strategy(strategy, revision, func)
#             assert excinfo.value.args[0] == expected.args[0].format(fp=fparam)
#             return

#         assert self.run_strategy(strategy, revision, func) == \
#             [possible[e] for e in expected]

#     @pytest.mark.parametrize(('kwargs'), [
#         pytest.param(dict(index=0, before='a'), id='index_and_before'),
#         pytest.param(dict(index=0, after='a'), id='index_and_after'),
#         pytest.param(dict(before='a', after='b'), id='before_and_after'),
#     ])
#     def test_combo_raises(self, kwargs):
#         with pytest.raises(TypeError) as excinfo:
#             InsertRevision(forge.arg('x'), **kwargs)
#         assert excinfo.value.args[0] == \
#             "expected 'index', 'before' or 'after' received multiple"

#     def test_no_position_raises(self):
#         with pytest.raises(TypeError) as excinfo:
#             InsertRevision(forge.arg('x'))
#         assert excinfo.value.args[0] == \
#             "expected keyword argument 'index', 'before', or 'after'"


# class TestModifyRevision:
#     def test__init__params(self):
#         """
#         ``ModifyRevision`` should share the same params as
#         ``FParameter.replace`` (except the additional `selector` arg on the
#         former)
#         """
#         sig1 = forge.fsignature(ModifyRevision)
#         sig2 = forge.fsignature(forge.FParameter.replace)
#         assert sig1[:][1:] == sig2[:][1:]

#     @pytest.mark.parametrize(('selector',), [
#         pytest.param(lambda param: param.name == 'b', id='callable'),
#         pytest.param('b', id='string'),
#     ])
#     def test_revision(self, func, selector):
#         func2 = ModifyRevision(selector, name='x')(func)
#         assert_params(func2, 'x', 'c', 'kwargs')


# class TestTranslocateRevision:
#     @pytest.fixture
#     def _func(self):
#         return lambda a, b, c: None

#     @pytest.mark.parametrize(('selector',), [
#         pytest.param(lambda param: param.name == 'b', id='callable'),
#         pytest.param('b', id='string'),
#     ])
#     def test_index(self, func, selector):
#         func2 = TranslocateRevision(selector, index=0)(func)
#         assert_params(func2, 'b', 'a', 'c')

#     @pytest.mark.parametrize(('selector',), [
#         pytest.param(lambda param: param.name == 'a', id='callable'),
#         pytest.param('a', id='string'),
#     ])
#     @pytest.mark.parametrize(('before',), [
#         pytest.param(lambda param: param.name == 'c', id='callable'),
#         pytest.param('c', id='string'),
#     ])
#     def test_before(self, func, selector, before):
#         func2 = TranslocateRevision(selector, before=before)(func)
#         assert_params(func2, 'b', 'a', 'c')

#     @pytest.mark.parametrize(('selector',), [
#         pytest.param(lambda param: param.name == 'a', id='callable'),
#         pytest.param('a', id='string'),
#     ])
#     @pytest.mark.parametrize(('after',), [
#         pytest.param(lambda param: param.name == 'b', id='callable'),
#         pytest.param('b', id='string'),
#     ])
#     def test_after(self, func, selector, after):
#         func2 = TranslocateRevision(selector, after=after)(func)
#         assert_params(func2, 'b', 'a', 'c')


# class TestCopyRevision:
#     @pytest.mark.parametrize(('strategy',), [('revise',), ('__call__',)])
#     @pytest.mark.parametrize(('include', 'exclude', 'expected'), [
#         # Neither
#         pytest.param(None, None, ('a', 'b', 'c'), id='no_include_no_exclude'),

#         # Include
#         pytest.param(
#             lambda param: param.name in ['a', 'b'],
#             None,
#             ('a', 'b'),
#             id='include_callable',
#         ),
#         pytest.param(
#             ['a', 'b'],
#             None,
#             ('a', 'b'),
#             id='include_iterable',
#         ),

#         # Exclude
#         pytest.param(
#             None,
#             lambda param: param.name == 'c',
#             ('a', 'b'),
#             id='exclude_callable',
#         ),
#         pytest.param(
#             None,
#             ['c'],
#             ('a', 'b'),
#             id='exclude_iterable',
#         ),

#         # Both
#         pytest.param(
#             ['a'],
#             ['b'],
#             TypeError("expected 'include' or 'exclude', but received both"),
#             id='include_and_exclude',
#         ),
#     ])
#     def test_revise(self, strategy, include, exclude, expected):
#         """
#         Ensure usage without ``include`` or ``exclude``
#         """
#         fromfunc = lambda a, b, c=0: None
#         func = lambda **kwargs: None

#         fsig_prev = forge.fsignature(func)
#         if isinstance(expected, Exception):
#             with pytest.raises(type(expected)) as excinfo:
#                 CopyRevision(fromfunc, include=include, exclude=exclude)
#             assert excinfo.value.args[0] == expected.args[0]
#             return

#         rev = CopyRevision(fromfunc, include=include, exclude=exclude)
#         if strategy == 'revise':
#             fparams_prev = list(fsig_prev.values())
#             fparams_next = rev.revise(*fparams_prev)
#             fsig_next = forge.FSignature(fparams_next)
#         elif strategy == '__call__':
#             func2 = rev(func)
#             fsig_next = forge.fsignature(func2)
#         else:
#             raise TypeError('unknown strategy {}'.format(strategy))

#         assert fsig_next == forge.FSignature([
#             fparam for fparam in [
#                 forge.arg('a'),
#                 forge.arg('b'),
#                 forge.arg('c', default=0),
#             ] if fparam.name in expected
#         ])



# class TestReplaceRevision:
#     @pytest.fixture
#     def _func(self):
#         return lambda a, b, **kwargs: None

#     @pytest.mark.parametrize(('selector',), [
#         pytest.param(lambda param: param.name == 'kwargs', id='callable'),
#         pytest.param('kwargs', id='string'),
#     ])
#     def test_revise(self, func, selector):
#         fparam = forge.arg('c')
#         fsig = forge.fsignature(func)
#         next_ = ReplaceRevision(selector, fparam).revise(*fsig.values())
#         assert next_ == [*fsig['a':'b'], fparam]

#     @pytest.mark.parametrize(('selector',), [
#         pytest.param(lambda param: param.name == 'kwargs', id='callable'),
#         pytest.param('kwargs', id='string'),
#     ])
#     def test__call__(self, func, selector):
#         fparam = forge.arg('c')
#         func2 = ReplaceRevision(selector, fparam)(func)
#         assert_params(func2, 'a', 'b', 'c')


# def test_manage_revision():
#     """
#     Assert that manage revision utilizes the custom callable
#     """
#     called_with = None
#     def reverse(*previous):
#         nonlocal called_with
#         called_with = previous
#         return previous[::-1]

#     func = lambda a, b, c: None
#     rev = ManageRevision(reverse)

#     fparams = list(forge.fsignature(func).values())
#     assert [fp.name for fp in rev.revise(*fparams)] == ['c', 'b', 'a']
#     assert called_with == tuple(fparams)


class TestMapper:
    @staticmethod
    def make_param(name, kind, default=empty):
        """
        Helper factory that generates an ``inspect.Parameter`` based on
        ``name`` , ``kind`` and ``default``
        """
        return inspect.Parameter(
            name,
            kind,
            default=empty.ccoerce_native(default)
        ) if kind is not None else None

    def test__repr__(self):
        """
        Ensure the mapper is pretty printable with ``FSignature`` and
        ``inspect.Signature``
        """
        fsig = FSignature([forge.pos('a', 'b')])
        callable_ = lambda *, b: None
        mapper = Mapper(fsig, callable_)
        assert repr(mapper) == '<Mapper (a, /) => (*, b)>'

    @pytest.mark.parametrize(('has_context',), [(True,), (False,)])
    def test_get_context(self, has_context):
        """
        Ensure the mapper retrieves the context value from arguments
        """
        fparam = forge.ctx('param') \
            if has_context \
            else forge.arg('param')
        fsig = FSignature([fparam])
        mapper = Mapper(fsig, lambda param: None)

        kwargs = {'param': object()}
        ctx = mapper.get_context(kwargs)
        assert ctx == (kwargs['param'] if has_context else None)

    @pytest.mark.parametrize(('from_kind',), [
        pytest.param(POSITIONAL_ONLY, id='from_positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='from_positional_or_keyword'),
        pytest.param(KEYWORD_ONLY, id='from_keyword_only'),
    ])
    @pytest.mark.parametrize(('to_kind',), [
        pytest.param(POSITIONAL_ONLY, id='to_positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='to_positional_or_keyword'),
        pytest.param(KEYWORD_ONLY, id='to_keyword_only'),
        pytest.param(VAR_KEYWORD, id='to_var_keyword'),
    ])
    @pytest.mark.parametrize(('vary_name',), [
        pytest.param(True, id='varied_name'),
        pytest.param(False, id='same_name'),
    ])
    def test__call__params_mapped(self, from_kind, to_kind, vary_name):
        """
        Ensure that call arguments are mapped from parameters of type:
        - POSITIONAL_ONLY
        - POSITIONAL_OR_KEYWORD
        - KEYWORD_ONLY

        to their interface counterparts as:
        - POSITIONAL_ONLY
        - POSITIONAL_OR_KEYWORD
        - KEYWORD_ONLY
        - VAR_KEYWORD

        with and without names being varied.
        """
        from_name, to_name = ('p1', 'p1') if not vary_name else ('p1', 'p2')
        fsig = FSignature([FParameter(from_kind, from_name, to_name)])
        func = lambda: None
        func.__signature__ = \
            inspect.Signature([inspect.Parameter(to_name, to_kind)])
        mapper = Mapper(fsig, func)

        call_args = CallArguments(**{from_name: 1}) \
            if from_kind in (KEYWORD_ONLY, VAR_KEYWORD) \
            else CallArguments(1)
        expected = CallArguments(**{to_name: 1}) \
            if to_kind in (KEYWORD_ONLY, VAR_KEYWORD) \
            else CallArguments(1)
        result = mapper(*call_args.args, **call_args.kwargs)
        assert result == expected

    def test__call__bound_injected(self):
        """
        Ensure ``bound`` fparams are injected into the mapping.
        """
        fsig = FSignature([forge.arg('bound', default=1, bound=True)])
        func = lambda bound: bound
        mapper = Mapper(fsig, func)
        assert mapper() == CallArguments(1)

    @pytest.mark.parametrize(('vary_name',), [
        pytest.param(True, id='varied_name'),
        pytest.param(False, id='same_name'),
    ])
    def test__call__vpo_param_mapped(self, vary_name):
        """
        Ensure ``var-positional`` params are directly mapped
        (w/ and w/o varied name)
        """
        from_name, to_name = ('p1', 'p1') if not vary_name else ('p1', 'p2')
        fsig = FSignature([FParameter(VAR_POSITIONAL, from_name, to_name)])
        func = lambda: None
        func.__signature__ = \
            inspect.Signature([inspect.Parameter(to_name, VAR_POSITIONAL)])
        mapper = Mapper(fsig, func)

        call_args = CallArguments(1, 2, 3)
        assert mapper(*call_args.args) == call_args

    @pytest.mark.parametrize(('vary_name',), [
        pytest.param(True, id='varied_name'),
        pytest.param(False, id='same_name'),
    ])
    def test__call__vkw_param_mapped(self, vary_name):
        """
        Ensure ``var-keyword`` params are directly mapped
        (w/ and w/o varied name)
        """
        from_name, to_name = ('p1', 'p1') if not vary_name else ('p1', 'p2')
        fsig = FSignature([FParameter(VAR_KEYWORD, from_name, to_name)])
        func = lambda: None
        func.__signature__ = \
            inspect.Signature([inspect.Parameter(to_name, VAR_KEYWORD)])
        mapper = Mapper(fsig, func)

        call_args = CallArguments(a=1, b=2, c=3)
        assert mapper(**call_args.kwargs) == call_args

    @pytest.mark.parametrize(('from_kind',), [
        pytest.param(POSITIONAL_ONLY, id='positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional_or_keyword'),
        pytest.param(KEYWORD_ONLY, id='keyword_only'),
    ])
    def test__call__defaults_applied(self, from_kind):
        """
        Ensure that defaults are applied to the underlying params
        (i.e. args passed):
        - POSITIONAL_ONLY
        - POSITIONAL_OR_KEYWORD
        - KEYWORD_ONLY
        """
        from_param = self.make_param('a', from_kind, default=1)
        from_sig = inspect.Signature([from_param])
        fsig = FSignature.from_signature(from_sig)
        func = lambda: None
        func.__signature__ = \
            inspect.Signature([inspect.Parameter('kwargs', VAR_KEYWORD)])
        mapper = Mapper(fsig, func)

        assert mapper() == CallArguments(a=1)

    def test__call__binding_error_raises_named(self):
        """
        Ensure that a lack of required (non-default) arguments raises a
        TypeError that mirrors the one raised when calling the callable directly
        """
        fsig = FSignature([forge.arg('a')])
        def func(a):
            # pylint: disable=W0613, unused-argument
            pass
        mapper = Mapper(fsig, func)
        with pytest.raises(TypeError) as excinfo:
            mapper()
        assert excinfo.value.args[0] == \
            "func() missing a required argument: 'a'"

    @pytest.mark.parametrize(('from_name', 'to_name'), [
        pytest.param('a', 'a', id='same_name'),
        pytest.param('a', 'b', id='diff_name'),
    ])
    @pytest.mark.parametrize(('from_kind',), [
        pytest.param(None, id='no_parameter'), # i.e. map: sig() -> sig(a=1)
        pytest.param(POSITIONAL_ONLY, id='positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional_or_keyword'),
        pytest.param(KEYWORD_ONLY, id='keyword_only'),
    ])
    @pytest.mark.parametrize(('to_kind',), [
        pytest.param(POSITIONAL_ONLY, id='positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional_or_keyword'),
        pytest.param(KEYWORD_ONLY, id='keyword_only'),
    ])
    @pytest.mark.parametrize(('from_default', 'to_default'), [
        pytest.param('from_def', empty, id='from_default'),
        pytest.param(empty, 'to_def', id='to_default'),
        pytest.param('from_def', 'to_def', id='default_from_and_default_to'),
    ])
    def test_map_parameters_to_non_var_parameter(
            self,
            from_name,
            from_kind,
            from_default,
            to_name,
            to_kind,
            to_default,
        ):
        """
        Ensure the mapping **strategy** produced with input fparams of ``kind``:
        - POSITIONAL_ONLY
        - POSITIONAL_OR_KEYWORD
        - KEYWORD_ONLY

        to callable params of ``kind``:
        - POSITIONAL_ONLY
        - POSITIONAL_OR_KEYWORD
        - KEYWORD_ONLY

        with varrying ``name`` and ``default``
        """
        # pylint: disable=R0913, too-many-arguments
        # pylint: disable=R0914, too-many-locals
        from_param = self.make_param(from_name, from_kind, from_default)
        from_sig = inspect.Signature([from_param] if from_param else None)
        fsig = FSignature.from_signature(from_sig)
        to_param = self.make_param(to_name, to_kind, to_default)
        to_sig = inspect.Signature([to_param])

        # Idenitfy map_parameters errors
        expected_exc = None
        if not from_param:
            if to_param.default is empty.native:
                expected_exc = TypeError(
                    "Missing requisite mapping to non-default "
                    "{to_kind} parameter '{to_name}'".format(
                        to_kind=_get_pk_string(to_param.kind),
                        to_name=to_param.name,
                    )
                )
        elif from_param.name != to_param.name:
            if to_param.default is empty.native:
                expected_exc = TypeError(
                    "Missing requisite mapping to non-default "
                    "{to_kind} parameter '{to_name}'".format(
                        to_kind=_get_pk_string(to_param.kind),
                        to_name=to_param.name,
                    )
                )
            else:
                expected_exc = TypeError(
                    'Missing requisite mapping from parameters (a)'
                )

        if expected_exc:
            with pytest.raises(type(expected_exc)) as excinfo:
                Mapper.map_parameters(fsig, to_sig)
            assert excinfo.value.args[0] == expected_exc.args[0]
            return

        pmap = Mapper.map_parameters(fsig, to_sig)
        expected_pmap = {from_param.name: to_param.name} if from_param else {}
        assert pmap == expected_pmap

    @pytest.mark.parametrize(('from_kind',), [
        pytest.param(POSITIONAL_ONLY, id='positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional_or_keyword'),
        pytest.param(VAR_POSITIONAL, id='var_positional'),
        pytest.param(KEYWORD_ONLY, id='keyword_only'),
        pytest.param(VAR_KEYWORD, id='var_keyword'),
    ])
    def test_map_parameters_to_var_positional(self, from_kind):
        """
        Ensure the mapping **strategy** produced mapping *to* ``var-positional``
        - POSITIONAL_ONLY -> VAR_POSITIONAL (raises)
        - POSTIIONAL_OR_KEYWORD -> VAR_POSITIONAL (raises)
        - VAR_POSTIIONAL -> VAR_POSITIONAL (success)
        - KEYWORD_ONLY -> VAR_POSITIONAL (raises)
        - VAR_KEYWROD -> VAR_POSITIONAL (raises)
        """
        from_param = self.make_param('from_', from_kind)
        from_sig = inspect.Signature([from_param])
        fsig = FSignature.from_signature(from_sig)
        to_param = self.make_param('args', VAR_POSITIONAL)
        to_sig = inspect.Signature([to_param])

        if from_param.kind is VAR_POSITIONAL:
            pmap = Mapper.map_parameters(fsig, to_sig)
            assert pmap == {from_param.name: to_param.name}
            return

        with pytest.raises(TypeError) as excinfo:
            Mapper.map_parameters(fsig, to_sig)

        if from_param.kind is VAR_KEYWORD:
            assert excinfo.value.args[0] == (
                "Missing requisite mapping from variable keyword parameter "
                "'from_'"
            )
        else:
            assert excinfo.value.args[0] == \
                "Missing requisite mapping from parameters (from_)"

    @pytest.mark.parametrize(('from_kind',), [
        pytest.param(POSITIONAL_ONLY, id='positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional_or_keyword'),
        pytest.param(VAR_POSITIONAL, id='var_positional'),
        pytest.param(KEYWORD_ONLY, id='keyword_only'),
        pytest.param(VAR_KEYWORD, id='var_keyword'),
    ])
    def test_map_parameters_to_var_keyword(self, from_kind):
        """
        Ensure the mapping **strategy** produced mapping *to* ``var-keyword``
        - POSITIONAL_ONLY -> VAR_POSITIONAL (success)
        - POSTIIONAL_OR_KEYWORD -> VAR_POSITIONAL (success)
        - VAR_POSTIIONAL -> VAR_POSITIONAL (raises)
        - KEYWORD_ONLY -> VAR_POSITIONAL (success)
        - VAR_KEYWROD -> VAR_POSITIONAL (success)
        """
        from_param = self.make_param('a', from_kind)
        from_sig = inspect.Signature([from_param])
        fsig = FSignature.from_signature(from_sig)
        to_param = self.make_param('kwargs', VAR_KEYWORD)
        to_sig = inspect.Signature([to_param])

        expected_exc = None
        if from_param.kind is VAR_POSITIONAL:
            expected_exc = TypeError(
                "Missing requisite mapping from variable positional "
                "parameter 'a'"
            )

        if expected_exc:
            with pytest.raises(type(expected_exc)) as excinfo:
                Mapper.map_parameters(fsig, to_sig)
            assert excinfo.value.args[0] == expected_exc.args[0]
            return
        pmap = Mapper.map_parameters(fsig, to_sig)
        assert pmap == {from_param.name: to_param.name}

    @pytest.mark.parametrize(('from_kind',), [
        pytest.param(POSITIONAL_ONLY, id='positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional_or_keyword'),
        pytest.param(VAR_POSITIONAL, id='var_positional'),
        pytest.param(KEYWORD_ONLY, id='keyword_only'),
        pytest.param(VAR_KEYWORD, id='var_keyword'),
    ])
    def test_map_parameters_to_empty(self, from_kind):
        """
        Ensure mapping **strategy** failure when no interface param available.
        """
        from_param = self.make_param('a', from_kind)
        from_sig = inspect.Signature([from_param])
        fsig = FSignature.from_signature(from_sig)
        to_sig = inspect.Signature()

        with pytest.raises(TypeError) as excinfo:
            Mapper.map_parameters(fsig, to_sig)
        if from_param.kind in (VAR_KEYWORD, VAR_POSITIONAL):
            assert excinfo.value.args[0] == (
                "Missing requisite mapping from {from_kind} parameter 'a'".\
                    format(from_kind=_get_pk_string(from_kind))
            )
        else:
            assert excinfo.value.args[0] == \
                "Missing requisite mapping from parameters (a)"

    @pytest.mark.parametrize(('to_kind',), [
        pytest.param(POSITIONAL_ONLY, id='positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional_or_keyword'),
        pytest.param(KEYWORD_ONLY, id='keyword_only'),
    ])
    def test_map_parameters_from_hidden(self, to_kind):
        """
        Ensure mapping **strategy** success when no fparam provided.
        """
        fsig = FSignature()
        to_param = self.make_param('a', to_kind, default=1)
        to_sig = inspect.Signature([to_param])

        assert Mapper.map_parameters(fsig, to_sig) == {}