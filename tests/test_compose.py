import asyncio
import inspect
from unittest.mock import Mock

import pytest

import forge
from forge._compose import (
    Mapper,
    Revision,
    compose,
    copy,
    insert,
    delete,
    manage,
    modify,
    replace,
    synthesize,
    translocate,
    returns,
    sort
)
from forge._marker import empty
from forge._signature import (
    KEYWORD_ONLY,
    POSITIONAL_ONLY,
    POSITIONAL_OR_KEYWORD,
    VAR_KEYWORD,
    VAR_POSITIONAL,
    FParameter,
    FSignature,
    fsignature,
    _get_pk_string,
)
from forge._utils import CallArguments

# pylint: disable=C0103, invalid-name
# pylint: disable=R0201, no-self-use
# pylint: disable=W0621, redefined-outer-name


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
        param = forge.ctx('param') \
            if has_context \
            else forge.arg('param')
        fsig = FSignature([param])
        mapper = Mapper(fsig, lambda param: None)

        assert mapper.context_param == (param if has_context else None)
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
        fsig = FSignature.from_native(from_sig)
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
        fsig = FSignature.from_native(from_sig)
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
        fsig = FSignature.from_native(from_sig)
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
        fsig = FSignature.from_native(from_sig)
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
        fsig = FSignature.from_native(from_sig)
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


class TestRevision:
    @pytest.mark.parametrize(('as_coroutine',), [(True,), (False,)])
    def test__call__not_existing(self, loop, as_coroutine):
        """
        Ensure ``sign`` wrapper appropriately builds and sets ``__mapper__``,
        and that a call to the wrapped func traverses ``Mapper.__call__`` and
        the wrapped function.
        """
        # pylint: disable=W0108, unnecessary-lambda
        rev = Revision()
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
        rev = Revision()
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

    def test_revise(self):
        """
        Ensure that the revise function is the identity function
        """
        rev = Revision()
        in_ = FSignature()
        assert rev.revise(in_) is in_

    def test__call__validates(self):
        """
        Ensure that `__call__` validates the signature. Notable because
        `revise` methods typically don't validate.
        """
        rev = Revision()
        rev.revise = lambda prev: FSignature(
            [forge.arg('b'), forge.pos('a')],
            __validate_parameters__=False,
        )
        with pytest.raises(SyntaxError) as excinfo:
            rev(lambda a, b: None)
        assert excinfo.value.args[0] == (
            "'a' of kind 'POSITIONAL_ONLY' follows 'b' of kind "
            "'POSITIONAL_OR_KEYWORD'"
        )


## Test Group Revisions
class TestCompose:
    def test_revise(self):
        """
        Ensure that ``compose`` applies the underlying revisions from top to
        bottom.
        """
        fsig1 = FSignature()
        mock1 = Mock(
            spec=Revision,
            revise=Mock(side_effect=lambda prev: fsig1),
        )

        fsig2 = FSignature()
        mock2 = Mock(
            spec=Revision,
            revise=Mock(side_effect=lambda prev: fsig2),
        )

        rev = compose(mock1, mock2)
        in_ = FSignature([forge.arg('a')])

        assert rev.revise(in_) is fsig2
        mock1.revise.assert_called_once_with(in_)
        mock2.revise.assert_called_once_with(fsig1)

    def test_revise_none(self):
        """
        Ensure that ``compose`` without any revisions is the identity function
        """
        fsig = FSignature()
        rev = compose()
        assert rev.revise(fsig) is fsig

    def test_non_revision_raises(self):
        """
        Ensure that supplying a non-revision to ``compose`` raises TypeError
        """
        with pytest.raises(TypeError) as excinfo:
            compose(1)
        assert excinfo.value.args[0] == "received non-revision '1'"


class TestCopy:
    @pytest.mark.parametrize(('include', 'exclude', 'expected'), [
        # Neither
        pytest.param(
            None,
            None,
            FSignature([forge.arg('a'), forge.arg('b'), forge.arg('c')]),
            id='no_include_no_exclude',
        ),

        # Include
        pytest.param(
            'a',
            None,
            forge.FSignature([forge.arg('a')]),
            id='include_str',
        ),
        pytest.param(
            ('a', 'b'),
            None,
            forge.FSignature([forge.arg('a'), forge.arg('b')]),
            id='include_iter_str',
        ),
        pytest.param(
            lambda param: param.name != 'a',
            None,
            forge.FSignature([forge.arg('b'), forge.arg('c')]),
            id='include_callable',
        ),

        # Exclude
        pytest.param(
            None,
            'a',
            forge.FSignature([forge.arg('b'), forge.arg('c')]),
            id='exclude_str',
        ),
        pytest.param(
            None,
            ('a', 'b'),
            forge.FSignature([forge.arg('c')]),
            id='exclude_iter_str',
        ),
        pytest.param(
            None,
            lambda param: param.name == 'a',
            forge.FSignature([forge.arg('b'), forge.arg('c')]),
            id='include_callable',
        ),

        # Both
        pytest.param(
            'a',
            'b',
            TypeError(
                "expected 'include', 'exclude', or neither, but received both"
            ),
            id='include_and_exclude',
        ),

    ])
    def test_revise(self, include, exclude, expected):
        """
        Ensure that ``copy`` copies a callable's signature, or the select
        parameters with ``include`` and ``exclude``.
        Also ensures that ``include`` and ``exclude`` take selector values;
        i.e. what's supplied to ``findparam``.
        """
        func = lambda a, b, c: None
        if isinstance(expected, Exception):
            with pytest.raises(type(expected)) as excinfo:
                copy(func, include=include, exclude=exclude)
            assert excinfo.value.args[0] == expected.args[0]
            return

        rev = copy(func, include=include, exclude=exclude)
        assert rev.revise(FSignature()) == expected


class TestManage:
    def test_revise(self):
        """
        Ensure that manage revision passes the input signature to the user
        supplied function and returns (the user-defined function's) value.
        """
        fsig = fsignature(lambda a, b, c: None)
        reverse = Mock(
            side_effect=lambda prev: prev.replace(
                parameters=list(prev.parameters.values())[::-1]
            )
        )
        rev = manage(reverse)

        assert rev.revise(fsig) == \
            FSignature([forge.arg('c'), forge.arg('b'), forge.arg('a')])


class TestReturns:
    def test_revise(self):
        """
        Ensure we set the ``return type`` annotation on an fsignature
        """
        rev = returns(int)
        assert rev.revise(FSignature()).return_annotation == int

    @pytest.mark.parametrize(('strategy',), [
        ('annotations',),
        ('signature',),
        ('mapper',),
    ])
    def test__call__(self, strategy):
        """
        Ensure we set the ``return type`` annotation following the strategy:

        - annotations: (no __mapper__, no __signature__), set __annotations__
        - signature: (no __mapper__), set __signature__
        - mapper: update __mapper__
        """
        rev = returns(int)
        def func():
            pass

        if strategy == 'annotations':
            pass
        elif strategy == 'signature':
            func.__signature__ = inspect.Signature()
        elif strategy == 'mapper':
            identity_rev = Revision()
            identity_rev.revise = lambda prev: prev
            func = identity_rev(func)
        else:
            raise TypeError('Unknown strategy {}'.format(strategy))

        assert rev(func) is func

        if strategy == 'annotations':
            assert not hasattr(func, '__signature__')
            assert func.__annotations__['return'] is int
        elif strategy == 'signature':
            assert not func.__annotations__
            assert hasattr(func, '__signature__')
            assert func.__signature__.return_annotation is int
        elif strategy == 'mapper':
            assert func.__signature__.return_annotation is int
            assert func.__mapper__.fsignature.return_annotation is int

    def test_revise_no_validation(self):
        """
        Ensure no validation is performed on the revision
        """
        rev = returns(int)
        fsig = FSignature(
            [forge.arg('b'), forge.pos('a')],
            __validate_parameters__=False,
        )
        assert rev.revise(fsig).parameters == fsig.parameters


class TestSynthesize:
    def test_sign(self):
        """
        Ensure that the nickname ``sign`` is the class ``synthesize``
        """
        assert forge.sign is synthesize

    def test_revise_args_order_preserved(self):
        """
        Ensure that the var-positional arguments *aren't* re-ordered
        """
        param_a = forge.arg('a')
        param_b = forge.arg('b')
        rev = synthesize(param_b, param_a)
        assert rev.revise(FSignature()) == FSignature([param_b, param_a])

    def test_revise_kwargs_reordered(self):
        """
        Ensure that the var-keyword arguments *are* re-ordered
        """
        param_a = forge.arg('a')
        param_b = forge.arg('b')
        rev = synthesize(b=param_b, a=param_a)
        assert rev.revise(FSignature()) == FSignature([param_a, param_b])

    def test_revise_args_precede_kwargs(self):
        """
        Ensure that var-postional arguments precede var-keyword arguments
        """
        param_a = forge.arg('a')
        param_b = forge.arg('b')
        rev = synthesize(param_b, a=param_a)
        assert rev.revise(FSignature()) == FSignature([param_b, param_a])

    def test_revise_no_validation(self):
        """
        Ensure no validation is performed on the revision
        """
        rev = synthesize(forge.arg('b'), forge.pos('a'))
        assert rev.revise(FSignature()) == FSignature(
            [forge.arg('b'), forge.pos('a')],
            __validate_parameters__=False,
        )


class TestSort:
    @pytest.mark.parametrize(('in_', 'sortkey', 'expected'), [
        pytest.param(
            [forge.arg('b'), forge.arg('a')],
            None,
            [forge.arg('a'), forge.arg('b')],
            id='lexicographical',
        ),
        pytest.param(
            [forge.arg('a', default=None), forge.arg('b')],
            None,
            [forge.arg('b'), forge.arg('a', default=None)],
            id='default',
        ),
        pytest.param(
            [
                forge.vkw('e'),
                forge.kwo('d'),
                forge.vpo('c'),
                forge.pok('b'),
                forge.pos('a'),
            ],
            None,
            [
                forge.pos('a'),
                forge.pok('b'),
                forge.vpo('c'),
                forge.kwo('d'),
                forge.vkw('e'),
            ],
            id='kind',
        ),
        pytest.param(
            [forge.arg('x', 'b'), forge.arg('y', 'a')],
            lambda param: param.interface_name,
            [forge.arg('y', 'a'), forge.arg('x', 'b')],
            id='sortkey_interface_name',
        ),
        pytest.param(
            [forge.vpo('a'), forge.vpo('b')],
            None,
            [forge.vpo('a'), forge.vpo('b')],
            id='novalidate',
        ),
    ])
    def test_revise(self, in_, sortkey, expected):
        """
        Ensure that parameter sorting:
        - doesn't validate the signature
        - by default sorts by (kind, has-default, name)
        - takes advantage of user-supplied sortkey
        """
        rev = sort(sortkey)
        in_ = FSignature(in_, __validate_parameters__=False)
        expected = FSignature(expected, __validate_parameters__=False)
        assert rev.revise(in_) == expected


## Test Unit Revisions
class TestDelete:
    @pytest.mark.parametrize(
        ('selector', 'multiple', 'raising', 'in_', 'out_'),
        [
            pytest.param(
                'a',
                False,
                True,
                FSignature([forge.arg('a'), forge.arg('b'), forge.arg('c')]),
                FSignature([forge.arg('b'), forge.arg('c')]),
                id='selector_str',
            ),

            pytest.param(
                ('a', 'b'),
                False,
                True,
                FSignature([forge.arg('a'), forge.arg('b'), forge.arg('c')]),
                FSignature([forge.arg('b'), forge.arg('c')]),
                id='selector_iter_str',
            ),

            pytest.param(
                lambda param: param.name not in ('a', 'b'),
                False,
                True,
                FSignature([forge.arg('a'), forge.arg('b'), forge.arg('c')]),
                FSignature([forge.arg('a'), forge.arg('b')]),
                id='selector_iter_str',
            ),

            pytest.param(
                ('a', 'b'),
                True,
                True,
                FSignature([forge.arg('a'), forge.arg('b'), forge.arg('c')]),
                FSignature([forge.arg('c')]),
                id='selector_multiple',
            ),

            pytest.param(
                'z',
                False,
                True,
                FSignature([forge.arg('a'), forge.arg('b'), forge.arg('c')]),
                ValueError("No parameter matched selector 'z'"),
                id='selector_no_match_raises',
            ),

            pytest.param(
                'z',
                False,
                False,
                FSignature([forge.arg('a'), forge.arg('b'), forge.arg('c')]),
                None,
                id='selector_no_match_not_raising',
            ),

        ]
    )
    def test_revision(self, selector, multiple, raising, in_, out_):
        """
        Ensure that delete:
        - raises if ``raising = True``
        - deletes multiple if ``multiple = True``
        - takes selector values; i.e. what's supplied to ``findparam``.
        """
        # pylint: disable=R0913, too-many-arguments
        rev = delete(selector, multiple, raising)
        if isinstance(out_, Exception):
            with pytest.raises(type(out_)) as excinfo:
                rev.revise(in_)
            assert excinfo.value.args[0] == out_.args[0]
        elif out_:
            assert rev.revise(in_) == out_
        else:
            assert rev.revise(in_) is in_

    def test_revise_no_validation(self):
        """
        Ensure no validation is performed on the revision
        """
        rev = delete('x', raising=False)
        fsig = FSignature(
            [forge.arg('b'), forge.pos('a')],
            __validate_parameters__=False,
        )
        assert rev.revise(fsig) is fsig


class TestInsert:
    @pytest.mark.parametrize(
        ('index', 'before', 'after', 'in_', 'out_'),
        [
            # Index
            pytest.param(
                0, None, None,
                FSignature([forge.arg('b')]),
                FSignature([forge.arg('a'), forge.arg('b')]),
                id='index',
            ),

            # Before
            pytest.param(
                None, 'b', None,
                FSignature([forge.arg('b'), forge.arg('c')]),
                FSignature([forge.arg('a'), forge.arg('b'), forge.arg('c')]),
                id='before_str',
            ),
            pytest.param(
                None, ('b', 'c'), None,
                FSignature([forge.arg('b'), forge.arg('c')]),
                FSignature([forge.arg('a'), forge.arg('b'), forge.arg('c')]),
                id='before_iter_str',
            ),
            pytest.param(
                None, lambda param: param.name != 'c', None,
                FSignature([forge.arg('b'), forge.arg('c')]),
                FSignature([forge.arg('a'), forge.arg('b'), forge.arg('c')]),
                id='before_callable',
            ),
            pytest.param(
                None, 'x', None,
                FSignature([forge.arg('b'), forge.arg('c')]),
                ValueError("No parameter matched selector 'x'"),
                id='before_no_mach',
            ),

            # After
            pytest.param(
                None, None, '_',
                FSignature([forge.arg('__'), forge.arg('_')]),
                FSignature([forge.arg('__'), forge.arg('_'), forge.arg('a')]),
                id='after_str',
            ),
            pytest.param(
                None, None, ('_', 'c'),
                FSignature([forge.arg('__'), forge.arg('_')]),
                FSignature([forge.arg('__'), forge.arg('_'), forge.arg('a')]),
                id='after_iter_str',
            ),
            pytest.param(
                None, None, lambda param: True,
                FSignature([forge.arg('__'), forge.arg('_')]),
                FSignature([forge.arg('__'), forge.arg('_'), forge.arg('a')]),
                id='after_callable',
            ),
            pytest.param(
                None, None, 'x',
                FSignature([forge.arg('__'), forge.arg('_')]),
                ValueError("No parameter matched selector 'x'"),
                id='after_no_mach',
            ),

        ],
    )
    @pytest.mark.parametrize(('insertion',), [
        pytest.param(forge.arg('a'), id='unit'),
        pytest.param([forge.arg('a')], id='iterable'),
    ])
    def test_revise(self, insertion, index, before, after, in_, out_):
        """
        Ensure that insert:
        - takes a parameter or iterable of parameters for ``insertion``
        - accepts an index
        - accepts before or after as selector values; i.e. what's supplied to \
        ``findparam``.
        """
        # pylint: disable=R0913, too-many-arguments
        rev = insert(insertion, index=index, before=before, after=after)
        if isinstance(out_, Exception):
            with pytest.raises(type(out_)) as excinfo:
                rev.revise(in_)
            assert excinfo.value.args[0] == out_.args[0]
            return
        assert rev.revise(in_) == out_

    @pytest.mark.parametrize(('kwargs'), [
        pytest.param(dict(index=0, before='a'), id='index_and_before'),
        pytest.param(dict(index=0, after='a'), id='index_and_after'),
        pytest.param(dict(before='a', after='b'), id='before_and_after'),
    ])
    def test_combo_raises(self, kwargs):
        """
        Ensure that insertion with more than one of (index, before, or after)
        raises.
        """
        with pytest.raises(TypeError) as excinfo:
            insert(forge.arg('x'), **kwargs)
        assert excinfo.value.args[0] == \
            "expected 'index', 'before' or 'after' received multiple"

    def test_no_position_raises(self):
        """
        Ensure that insertion without index, before, or after raises.
        """
        with pytest.raises(TypeError) as excinfo:
            insert(forge.arg('x'))
        assert excinfo.value.args[0] == \
            "expected keyword argument 'index', 'before', or 'after'"

    def test_revise_no_validation(self):
        """
        Ensure no validation is performed on the revision
        """
        rev = insert(forge.arg('b'), index=0)
        fsig = FSignature([forge.pos('a')], __validate_parameters__=False)
        assert rev.revise(fsig) == FSignature(
            [forge.arg('b'), forge.pos('a')],
            __validate_parameters__=False,
        )


class TestModify:
    @pytest.mark.parametrize(('revision',), [
        pytest.param(dict(kind=POSITIONAL_OR_KEYWORD), id='kind'),
        pytest.param(dict(name='b'), id='name'),
        pytest.param(dict(interface_name='b'), id='interface_name'),
        pytest.param(dict(default=None), id='default'),
        pytest.param(dict(factory=lambda: None), id='factory'),
        pytest.param(dict(type=int), id='type'),
        pytest.param(dict(converter=lambda *_: None), id='converter'),
        pytest.param(dict(validator=lambda *_: None), id='validator'),
        pytest.param(dict(bound=True, default=None), id='bound'),
        pytest.param(dict(contextual=True), id='contextual'),
        pytest.param(dict(metadata={'a': 1}), id='metadata'),
    ])
    def test_revise(self, revision):
        """
        Ensure that ``modify`` appropriately revises every attribute of a
        parameter.
        """
        in_param = forge.pos('a')
        out_param = in_param.replace(**revision)
        assert in_param != out_param # ensure we've got a good test setup

        rev = modify('a', **revision)
        assert rev.revise(FSignature([in_param])) == FSignature([out_param])

    @pytest.mark.parametrize(('multiple',), [(True,), (False,)])
    def test_revise_multiple(self, multiple):
        """
        Ensure that passing ``multiple=True`` allows for modification of every
        parameter that matches the selector; i.e. values passed to ``findparam``
        """
        in_ = FSignature([forge.arg('a'), forge.arg('b')])
        rev = modify(('a', 'b'), multiple=multiple, kind=POSITIONAL_ONLY)
        out_ = rev.revise(in_)

        kinds = [param.kind for param in out_.parameters.values()]
        if multiple:
            assert kinds == [POSITIONAL_ONLY, POSITIONAL_ONLY]
        else:
            assert kinds == [POSITIONAL_ONLY, POSITIONAL_OR_KEYWORD]

    @pytest.mark.parametrize(('raising',), [(True,), (False,)])
    def test_revise_no_match(self, raising):
        """
        Ensure that only when ``raising=True``, an exception is raised if
        ``selector`` doesn't match a parameter.
        """
        in_ = FSignature([forge.arg('a')])
        rev = modify('x', raising=raising, kind=POSITIONAL_ONLY)

        if raising:
            with pytest.raises(ValueError) as excinfo:
                rev.revise(in_)
            assert excinfo.value.args[0] == "No parameter matched selector 'x'"
            return

        assert rev.revise(in_) is in_

    def test_revise_no_validation(self):
        """
        Ensure no validation is performed on the revision
        """
        rev = modify('b', kind=POSITIONAL_ONLY)
        in_ = FSignature([forge.arg('a'), forge.arg('b')])
        out_ = FSignature(
            [forge.arg('a'), forge.pos('b')],
            __validate_parameters__=False,
        )
        assert rev.revise(in_) == out_

    def test_accepted_params(self):
        """
        Ensure that ``modify`` takes the same arguments as
        ``FParameter.replace``. Keeps code in sync.
        """
        assert fsignature(modify).parameters['name':] == \
            fsignature(FParameter.replace).parameters['name':]


class TestReplace:
    @pytest.mark.parametrize(('selector',), [
        pytest.param('old', id='selector_str'),
        pytest.param(('old', 'other'), id='selector_iter_str'),
        pytest.param(
            lambda param: param.name != 'other',
            id='selector_callable',
        ),
    ])
    def test_revise(self, selector):
        """
        Ensure that ``replace`` accepts selector values; i.e. those passed to
        ``findparam``.
        """
        new_param = forge.arg('new')
        old_param = forge.arg('old')
        in_ = FSignature([old_param])
        out_ = FSignature([new_param])

        rev = replace(selector, new_param)
        assert rev.revise(in_) == out_

    def test_no_match_raises(self):
        """
        Ensure that if selector doesn't find a match, an exception is rasied.
        """
        rev = replace('i', forge.arg('a'))
        with pytest.raises(ValueError) as excinfo:
            rev.revise(FSignature())
        assert excinfo.value.args[0] == \
            "No parameter matched selector 'i'"

    def test_revise_no_validation(self):
        """
        Ensure no validation is performed on the revision
        """
        rev = replace('b', forge.pos('b'))
        in_ = FSignature([forge.arg('a'), forge.arg('b')])
        out_ = FSignature(
            [forge.arg('a'), forge.pos('b')],
            __validate_parameters__=False,
        )
        assert rev.revise(in_) == out_


class TestTranslocate:
    def test_move(self):
        """
        Ensure that forge.move is a nickname for ``translocate``
        """
        assert forge.move is translocate

    @pytest.mark.parametrize(('index', 'before', 'after'), [
        # Index
        pytest.param(1, None, None, id='index'),

        # Before
        pytest.param(None, 'c', None, id='before_str'),
        pytest.param(None, ('c', 'x'), None, id='before_iter_str'),
        pytest.param(
            None,
            lambda param: param.name == 'c',
            None,
            id='before_callable',
        ),

        # After
        pytest.param(None, None, 'a', id='after_str'),
        pytest.param(None, None, ('a', 'x'), id='after_iter_str'),
        pytest.param(
            None,
            None,
            lambda param: param.name == 'a',
            id='after_callable',
        ),
    ])
    @pytest.mark.parametrize(('selector',), [
        pytest.param('b', id='selector_str'),
        pytest.param(('b', 'x'), id='selector_iter_str'),
        pytest.param(lambda param: param.name == 'b', id='selector_callable'),
    ])
    def test_revise(self, selector, index, before, after):
        """
        Ensure that ``translocate``:
        - takes index
        - takes before as a selector value; i.e. value passed to ``findparam``
        - takes after as a selector value; i.e. value passed to ``findparam``
        """
        # pylint: disable=R0913, too-many-arguments
        rev = translocate(selector, index=index, before=before, after=after)
        in_ = FSignature([forge.arg('a'), forge.arg('c'), forge.arg('b')])
        out_ = FSignature([forge.arg('a'), forge.arg('b'), forge.arg('c')])

        if isinstance(out_, Exception):
            with pytest.raises(type(out_)) as excinfo:
                rev.revise(in_)
            assert excinfo.value.args[0] == out_.args[0]
            return
        assert rev.revise(in_) == out_

    def test_revise_selector_no_match_raises(self):
        """
        Ensure that a ``selector`` without a match raises
        """
        rev = translocate('x', index=0)
        with pytest.raises(ValueError) as excinfo:
            rev.revise(fsignature(lambda a: None))
        assert excinfo.value.args[0] == \
            "No parameter matched selector 'x'"

    def test_revise_before_no_match_raises(self):
        """
        Ensure that a ``before`` value with a match raises
        """
        rev = translocate('a', before='x')
        with pytest.raises(ValueError) as excinfo:
            rev.revise(fsignature(lambda a: None))
        assert excinfo.value.args[0] == \
            "No parameter matched selector 'x'"

    def test_revise_after_no_match_raises(self):
        """
        Ensure that an ``after`` value with a match raises
        """
        rev = translocate('a', after='x')
        with pytest.raises(ValueError) as excinfo:
            rev.revise(fsignature(lambda a: None))
        assert excinfo.value.args[0] == \
            "No parameter matched selector 'x'"

    @pytest.mark.parametrize(('kwargs'), [
        pytest.param(dict(index=0, before='a'), id='index_and_before'),
        pytest.param(dict(index=0, after='a'), id='index_and_after'),
        pytest.param(dict(before='a', after='b'), id='before_and_after'),
    ])
    def test_combo_raises(self, kwargs):
        """
        Ensure that ``index``, ``before``, or ``after`` can be passed, but not a
        combination
        """
        with pytest.raises(TypeError) as excinfo:
            translocate(forge.arg('x'), **kwargs)
        assert excinfo.value.args[0] == \
            "expected 'index', 'before' or 'after' received multiple"

    def test_no_position_raises(self):
        """
        Ensure that ``index``, ``before``, or ``after`` must be passed
        """
        with pytest.raises(TypeError) as excinfo:
            translocate(forge.arg('x'))
        assert excinfo.value.args[0] == \
            "expected keyword argument 'index', 'before', or 'after'"

    def test_revise_no_validation(self):
        """
        Ensure no validation is performed on the revision
        """
        rev = translocate('b', index=0)
        in_ = FSignature([forge.pos('a'), forge.arg('b')])
        out_ = FSignature(
            [forge.arg('b'), forge.pos('a')],
            __validate_parameters__=False,
        )
        assert rev.revise(in_) == out_