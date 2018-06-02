import asyncio
from unittest.mock import Mock
import inspect

import pytest

import forge
from forge._compose import (
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
from forge._signature import (
    CallArguments,
    FSignature,
    Mapper,
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


class TestReturns:
    def test_no__signature__(self):
        """
        Ensure we can set the ``return type`` annotation on a function without
        a ``__signature__``
        """
        @returns(int)
        def myfunc():
            pass
        assert myfunc.__annotations__.get('return') == int

    def test__signature__(self):
        """
        Ensure we can set the ``return type`` annotation on a function with
        a ``__signature__``
        """
        def myfunc():
            pass
        myfunc.__signature__ = inspect.Signature()

        myfunc = returns(int)(myfunc)
        assert myfunc.__signature__.return_annotation == int


class BaseTestRevision:
    def run_strategy(self, strategy, revision, func):
        fsig = forge.fsignature(func)
        if strategy == 'apply':
            return list(revision.apply(*fsig.values()))
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
        rev.apply = lambda *fparams: fparams
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
        rev.apply = lambda *fparams: fparams
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
    assert rev.apply(*in_) == in_


class TestSynthesizeRevision:
    def test_args_order_preserved(self):
        """
        Ensure that the var-positional arguments *aren't* re-ordered
        """
        param_a = forge.arg('a')
        param_b = forge.arg('b')
        rev = SynthesizeRevision(param_b, param_a)
        assert rev.fparameters == [param_b, param_a]

    def test_kwargs_reordered(self):
        """
        Ensure that the var-keyword arguments *are* re-ordered
        """
        param_a = forge.arg('a')
        param_b = forge.arg('b')
        rev = SynthesizeRevision(b=param_b, a=param_a)
        assert rev.fparameters == [param_a, param_b]

    def test_args_precede_kwargs(self):
        """
        Ensure that var-postional arguments precede var-keyword arguments
        """
        param_a = forge.arg('a')
        param_b = forge.arg('b')
        rev = SynthesizeRevision(param_b, a=param_a)
        assert rev.fparameters == [param_b, param_a]


class TestBatchRevision(BaseTestRevision):
    @pytest.mark.parametrize(('strategy',), [('apply',), ('__call__',)])
    @pytest.mark.parametrize(('revisions', 'expected'), [
        # Empty
        pytest.param(
            [
                InsertRevision(forge.arg('a'), index=-1),
                TranslocateRevision('a', index=0),
            ],
            ('a', 'b', 'c', 'kwargs'),
            id='multiple',
        ),

        # None
        pytest.param(
            [],
            ('b', 'c', 'kwargs'),
            id='none',
        ),

    ])
    def test_revision(self, strategy, revisions, expected):
        revision = BatchRevision(*revisions)
        func = lambda b, c=0, **kwargs: None

        possible = {
            param.name: param for param in [
                forge.arg('a'),
                forge.arg('b'),
                forge.arg('c', default=0),
                forge.vkw('kwargs'),
            ]
        }

        assert self.run_strategy(strategy, revision, func) == \
            [possible[e] for e in expected]


    def test_non_revision_raises(self):
        with pytest.raises(TypeError) as excinfo:
            BatchRevision(1)
        assert excinfo.value.args[0] == "received non-revision '1'"


class TestDeleteRevision(BaseTestRevision):
    @pytest.mark.parametrize(('strategy',), [('apply',), ('__call__',)])
    @pytest.mark.parametrize(('selector', 'expected'), [
        pytest.param(
            'c',
            ('a', 'b'),
            id='string',
        ),
        pytest.param(
            lambda param: param.name == 'c',
            ('a', 'b'),
            id='callable',
        ),
        pytest.param(
            lambda param: False,
            RevisionError('cannot delete parameter: not found'),
            id='param_not_found',
        )
    ])
    def test_revision(self, strategy, selector, expected):
        revision = DeleteRevision(selector)
        func = lambda a, b, c=0: None

        if isinstance(expected, RevisionError):
            with pytest.raises(type(expected)) as excinfo:
                self.run_strategy(strategy, revision, func)
            assert excinfo.value.args[0] == expected.args[0]
            return

        possible = {
            param.name: param for param in [
                forge.arg('a'),
                forge.arg('b'),
                forge.arg('c', default=0),
            ]
        }

        assert self.run_strategy(strategy, revision, func) == \
            [possible[e] for e in expected]


class TestInsertRevision(BaseTestRevision):
    @pytest.mark.parametrize(('strategy',), [('apply',), ('__call__',)])
    @pytest.mark.parametrize(('kwargs', 'expected'), [
        # index
        pytest.param(
            dict(index=0),
            ('a', 'b', 'c', 'kwargs'),
            id='index',
        ),

        # before
        pytest.param(
            dict(before='b'),
            ('a', 'b', 'c', 'kwargs'),
            id='before_string',
        ),
        pytest.param(
            dict(before=lambda param: param.name == 'b'),
            ('a', 'b', 'c', 'kwargs'),
            id='before_callable',
        ),
        pytest.param(
            dict(before=lambda param: True),
            ('a', 'b', 'c', 'kwargs'),
            id='before_multi_match',
        ),
        pytest.param(
            dict(before=lambda param: False),
            RevisionError(
                'cannot insert {fp} before selector; selector not found'
            ),
            id='before_not_found_raises',
        ),

        # after
        pytest.param(
            dict(after='b'),
            ('b', 'a', 'c', 'kwargs'),
            id='after_string',
        ),
        pytest.param(
            dict(after=lambda param: param.name == 'b'),
            ('b', 'a', 'c', 'kwargs'),
            id='after_callable',
        ),
        pytest.param(
            dict(after=lambda param: True),
            ('b', 'a', 'c', 'kwargs'),
            id='after_multi_match',
        ),
        pytest.param(
            dict(after=lambda param: False),
            RevisionError(
                'cannot insert {fp} after selector; selector not found'
            ),
            id='after_not_found_raises',
        ),

    ])
    def test_revision(self, strategy, kwargs, expected):
        fparam = forge.arg('a')
        revision = InsertRevision(fparam, **kwargs)
        func = lambda b, c=0, **kwargs: None

        possible = {
            param.name: param for param in [
                forge.arg('a'),
                forge.arg('b'),
                forge.arg('c', default=0),
                forge.vkw('kwargs'),
            ]
        }

        if isinstance(expected, Exception):
            with pytest.raises(type(expected)) as excinfo:
                self.run_strategy(strategy, revision, func)
            assert excinfo.value.args[0] == expected.args[0].format(fp=fparam)
            return

        assert self.run_strategy(strategy, revision, func) == \
            [possible[e] for e in expected]

    @pytest.mark.parametrize(('kwargs'), [
        pytest.param(dict(index=0, before='a'), id='index_and_before'),
        pytest.param(dict(index=0, after='a'), id='index_and_after'),
        pytest.param(dict(before='a', after='b'), id='before_and_after'),
    ])
    def test_combo_raises(self, kwargs):
        with pytest.raises(TypeError) as excinfo:
            InsertRevision(forge.arg('x'), **kwargs)
        assert excinfo.value.args[0] == \
            "expected 'index', 'before' or 'after' received multiple"

    def test_no_position_raises(self):
        with pytest.raises(TypeError) as excinfo:
            InsertRevision(forge.arg('x'))
        assert excinfo.value.args[0] == \
            "expected keyword argument 'index', 'before', or 'after'"


class TestModifyRevision:
    def test__init__params(self):
        """
        ``ModifyRevision`` should share the same params as
        ``FParameter.replace`` (except the additional `selector` arg on the
        former)
        """
        sig1 = forge.fsignature(ModifyRevision)
        sig2 = forge.fsignature(forge.FParameter.replace)
        assert sig1[:][1:] == sig2[:][1:]

    @pytest.mark.parametrize(('selector',), [
        pytest.param(lambda param: param.name == 'b', id='callable'),
        pytest.param('b', id='string'),
    ])
    def test_revision(self, func, selector):
        func2 = ModifyRevision(selector, name='x')(func)
        assert_params(func2, 'x', 'c', 'kwargs')


class TestTranslocateRevision:
    @pytest.fixture
    def _func(self):
        return lambda a, b, c: None

    @pytest.mark.parametrize(('selector',), [
        pytest.param(lambda param: param.name == 'b', id='callable'),
        pytest.param('b', id='string'),
    ])
    def test_index(self, func, selector):
        func2 = TranslocateRevision(selector, index=0)(func)
        assert_params(func2, 'b', 'a', 'c')

    @pytest.mark.parametrize(('selector',), [
        pytest.param(lambda param: param.name == 'a', id='callable'),
        pytest.param('a', id='string'),
    ])
    @pytest.mark.parametrize(('before',), [
        pytest.param(lambda param: param.name == 'c', id='callable'),
        pytest.param('c', id='string'),
    ])
    def test_before(self, func, selector, before):
        func2 = TranslocateRevision(selector, before=before)(func)
        assert_params(func2, 'b', 'a', 'c')

    @pytest.mark.parametrize(('selector',), [
        pytest.param(lambda param: param.name == 'a', id='callable'),
        pytest.param('a', id='string'),
    ])
    @pytest.mark.parametrize(('after',), [
        pytest.param(lambda param: param.name == 'b', id='callable'),
        pytest.param('b', id='string'),
    ])
    def test_after(self, func, selector, after):
        func2 = TranslocateRevision(selector, after=after)(func)
        assert_params(func2, 'b', 'a', 'c')


class TestCopyRevision:
    @pytest.mark.parametrize(('strategy',), [('apply',), ('__call__',)])
    @pytest.mark.parametrize(('include', 'exclude', 'expected'), [
        # Neither
        pytest.param(None, None, ('a', 'b', 'c'), id='no_include_no_exclude'),

        # Include
        pytest.param(
            lambda param: param.name in ['a', 'b'],
            None,
            ('a', 'b'),
            id='include_callable',
        ),
        pytest.param(
            ['a', 'b'],
            None,
            ('a', 'b'),
            id='include_iterable',
        ),

        # Exclude
        pytest.param(
            None,
            lambda param: param.name == 'c',
            ('a', 'b'),
            id='exclude_callable',
        ),
        pytest.param(
            None,
            ['c'],
            ('a', 'b'),
            id='exclude_iterable',
        ),

        # Both
        pytest.param(
            ['a'],
            ['b'],
            TypeError("expected 'include' or 'exclude', but received both"),
            id='include_and_exclude',
        ),
    ])
    def test_apply(self, strategy, include, exclude, expected):
        """
        Ensure usage without ``include`` or ``exclude``
        """
        fromfunc = lambda a, b, c=0: None
        func = lambda **kwargs: None

        fsig_prev = forge.fsignature(func)
        if isinstance(expected, Exception):
            with pytest.raises(type(expected)) as excinfo:
                CopyRevision(fromfunc, include=include, exclude=exclude)
            assert excinfo.value.args[0] == expected.args[0]
            return

        rev = CopyRevision(fromfunc, include=include, exclude=exclude)
        if strategy == 'apply':
            fparams_prev = list(fsig_prev.values())
            fparams_next = rev.apply(*fparams_prev)
            fsig_next = forge.FSignature(fparams_next)
        elif strategy == '__call__':
            func2 = rev(func)
            fsig_next = forge.fsignature(func2)
        else:
            raise TypeError('unknown strategy {}'.format(strategy))

        assert fsig_next == forge.FSignature([
            fparam for fparam in [
                forge.arg('a'),
                forge.arg('b'),
                forge.arg('c', default=0),
            ] if fparam.name in expected
        ])



class TestReplaceRevision:
    @pytest.fixture
    def _func(self):
        return lambda a, b, **kwargs: None

    @pytest.mark.parametrize(('selector',), [
        pytest.param(lambda param: param.name == 'kwargs', id='callable'),
        pytest.param('kwargs', id='string'),
    ])
    def test_apply(self, func, selector):
        fparam = forge.arg('c')
        fsig = forge.fsignature(func)
        next_ = ReplaceRevision(selector, fparam).apply(*fsig.values())
        assert next_ == [*fsig['a':'b'], fparam]

    @pytest.mark.parametrize(('selector',), [
        pytest.param(lambda param: param.name == 'kwargs', id='callable'),
        pytest.param('kwargs', id='string'),
    ])
    def test__call__(self, func, selector):
        fparam = forge.arg('c')
        func2 = ReplaceRevision(selector, fparam)(func)
        assert_params(func2, 'a', 'b', 'c')


def test_manage_revision():
    """
    Assert that manage revision utilizes the custom callable
    """
    called_with = None
    def reverse(*previous):
        nonlocal called_with
        called_with = previous
        return previous[::-1]

    func = lambda a, b, c: None
    rev = ManageRevision(reverse)

    fparams = list(forge.fsignature(func).values())
    assert [fp.name for fp in rev.apply(*fparams)] == ['c', 'b', 'a']
    assert called_with == tuple(fparams)