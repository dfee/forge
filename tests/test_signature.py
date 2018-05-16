import inspect
from unittest.mock import Mock

import pytest

import forge
import forge._signature
from forge._marker import (
    void,
    void_to_empty,
)
from forge._parameter import FParameter
from forge._signature import (
    CallArguments,
    FSignature,
    Mapper,
    pk_strings,
    sign,
    resign,
)

# pylint: disable=C0103, invalid-name
# pylint: disable=R0201, no-self-use
# pylint: disable=W0212, protected-access
# pylint: disable=W0621, redefined-outer-name
# pylint: disable=R0904, too-many-public-methods


empty = inspect.Parameter.empty

POSITIONAL_ONLY = inspect.Parameter.POSITIONAL_ONLY  # type: ignore
POSITIONAL_OR_KEYWORD = inspect.Parameter.POSITIONAL_OR_KEYWORD  # type: ignore
VAR_POSITIONAL = inspect.Parameter.VAR_POSITIONAL
KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY
VAR_KEYWORD = inspect.Parameter.VAR_KEYWORD


def assert_signatures_match(func1, func2):
    assert inspect.signature(func1) == inspect.signature(func2)


class TestCallArguments:
    def test_from_bound_arguments(self):
        # pylint: disable=W0613, unused-argument
        def func(a, *, b):
            pass
        bound = inspect.signature(func).bind(a=1, b=2)
        # pylint: disable=E1101, no-member
        assert CallArguments.from_bound_arguments(bound) == \
            CallArguments(1, b=2)

    @pytest.mark.parametrize(('partial',), [(True,), (False,)])
    @pytest.mark.parametrize(('call_args', 'incomplete'), [
        pytest.param(CallArguments(1, b=2), False, id='complete'),
        pytest.param(CallArguments(), True, id='incomplete'),
    ])
    def test_to_bound_arguments(self, call_args, partial, incomplete):
        # pylint: disable=W0613, unused-argument
        def func(a, *, b):
            pass
        sig = inspect.signature(func)
        if not partial and incomplete:
            with pytest.raises(TypeError) as excinfo:
                call_args.to_bound_arguments(sig, partial=partial)
            assert excinfo.value.args[0] == \
                "missing a required argument: 'a'"
            return
        assert call_args.to_bound_arguments(sig, partial=partial) == \
            sig.bind_partial(*call_args.args, **call_args.kwargs)

    @pytest.mark.parametrize(('args', 'kwargs', 'expected'), [
        pytest.param((0,), {}, '0', id='args_only'),
        pytest.param((), {'a': 1}, 'a=1', id='kwargs_only'),
        pytest.param((0,), {'a': 1}, '0, a=1', id='args_and_kwargs'),
        pytest.param((), {}, '', id='neither_args_nor_kwargs'),
    ])
    def test__repr__(self, args, kwargs, expected):
        assert repr(CallArguments(*args, **kwargs)) == \
            '<CallArguments ({})>'.format(expected)

class TestReturns:
    def test_no__signature__(self):
        @forge.returns(int)
        def myfunc():
            pass
        assert myfunc.__annotations__.get('return') == int

    def test__signature__(self):
        def myfunc():
            pass
        myfunc.__signature__ = inspect.Signature()

        myfunc = forge.returns(int)(myfunc)
        assert myfunc.__signature__.return_annotation == int


class TestFSignature:
    def test_validate_non_parameter_raises(self):
        with pytest.raises(TypeError) as excinfo:
            FSignature.validate(1)
        assert excinfo.value.args[0] == "Received non-FParameter '1'"

    def test_validate_unnamed_parameter_raises(self):
        arg = forge.arg()
        with pytest.raises(ValueError) as excinfo:
            FSignature.validate(arg)
        assert excinfo.value.args[0] == \
            "Received unnamed FParameter: '{}'".format(arg)

    def test_validate_late_contextual_param_raises(self):
        with pytest.raises(TypeError) as excinfo:
            FSignature.validate(forge.arg('a'), forge.ctx('self'))
        assert excinfo.value.args[0] == \
            'Only the first FParameter can be contextual'

    def test_validate_multiple_interface_name_raises(self):
        with pytest.raises(ValueError) as excinfo:
            FSignature.validate(forge.arg('a1', 'b'), forge.arg('a2', 'b'))
        assert excinfo.value.args[0] == \
            "Received multiple FParameters with interface_name 'b'"

    def test_validate_multiple_name_raises(self):
        with pytest.raises(ValueError) as excinfo:
            FSignature.validate(forge.arg('a', 'b1'), forge.arg('a', 'b2'))
        assert excinfo.value.args[0] == \
            "Received multiple FParameters with name 'a'"

    def test_validate_multiple_var_positional_parameters_raises(self):
        params = [
            FParameter(
                kind=inspect.Parameter.VAR_POSITIONAL,
                name='args{}'.format(i),
                interface_name='args{}'.format(i),
                default=empty,
                type=empty,
            ) for i in range(2)
        ]
        with pytest.raises(TypeError) as excinfo:
            FSignature.validate(*params)
        assert excinfo.value.args[0] == \
            'Received multiple variable-positional FParameters'

    def test_validate_multiple_var_keyword_parameters_raises(self):
        params = [
            FParameter(
                kind=inspect.Parameter.VAR_KEYWORD,
                name='kwargs{}'.format(i),
                interface_name='kwargs{}'.format(i),
                default=empty,
                type=empty,
            ) for i in range(2)
        ]
        with pytest.raises(TypeError) as excinfo:
            FSignature.validate(*params)
        assert excinfo.value.args[0] == \
            'Received multiple variable-keyword FParameters'

    def test_validate_out_of_order_parameters_raises(self):
        kwarg_ = forge.kwarg('kwarg')
        arg_ = forge.arg('arg')
        with pytest.raises(SyntaxError) as excinfo:
            FSignature.validate(kwarg_, arg_)
        assert excinfo.value.args[0] == (
            "{arg_} of kind '{arg_kind}' follows "
            "{kwarg_} of kind '{kwarg_kind}'".format(
                arg_=arg_,
                arg_kind=arg_.kind.name,
                kwarg_=kwarg_,
                kwarg_kind=kwarg_.kind.name,
            )
        )

    @pytest.mark.parametrize(('constructor',), [(forge.pos,), (forge.arg,)])
    def test_validate_non_default_follows_default_raises(self, constructor):
        default = constructor('d', default=None)
        nondefault = constructor('nd')
        with pytest.raises(SyntaxError) as excinfo:
            FSignature.validate(default, nondefault)
        assert excinfo.value.args[0] == (
            'non-default FParameter follows default FParameter'
        )

    def test_validate_default_kw_only_follows_non_default_kw_only(self):
        FSignature.validate(
            forge.kwarg('a', default=None),
            forge.kwarg('b'),
        )

    def test_validate_multiple_parameters(self):
        FSignature.validate(
            forge.pos('a'),
            forge.arg('b'),
            *forge.args,
            forge.kwarg('c'),
            list(dict(forge.kwargs).values())[0],
        )

    def test__eq__(self):
        fsigs = [FSignature(forge.arg('a')) for i in range(2)]
        assert fsigs[0] == fsigs[1]

    def test__eq__type_check(self):
        assert FSignature() != object()

    def test__repr__(self):
        assert repr(FSignature(forge.self)) == '<FSignature (self)>'

    # Begin MutableSequence Tests
    def test__getitem__(self):
        fparam = forge.arg('a')
        fsig = FSignature(fparam)
        assert fsig['a'] is fparam

    def test__len__(self):
        assert len(FSignature(forge.arg('a'))) == 1

    def test__iter__(self):
        fparam = forge.arg('a')
        fsig = FSignature(fparam)
        assert dict(fsig) == {fparam.name: fparam}
    # End MutableSequence Tests

    def test_from_signature(self):
        sig = inspect.Signature([
            inspect.Parameter(
                'a',
                POSITIONAL_OR_KEYWORD,
                default=0,
                annotation=int,
            ),
        ])
        fsig = FSignature.from_signature(sig)
        assert len(fsig) == 1
        assert fsig['a'] == FParameter(
            kind=POSITIONAL_OR_KEYWORD,
            name='a',
            interface_name='a',
            default=0,
            type=int,
        )

    def test_from_callable(self):
        def func(a: int = 0):
            return a
        fsig = FSignature.from_callable(func)
        assert len(fsig) == 1
        assert fsig['a'] == FParameter(
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            name='a',
            interface_name='a',
            default=0,
            type=int,
        )

    def test_var_positional(self):
        fsig = FSignature(*forge.args)
        assert fsig['args'] == fsig.var_positional

    def test_var_keyword(self):
        fsig = FSignature(**forge.kwargs)
        assert fsig['kwargs'] == fsig.var_keyword

    def test_context(self):
        fsig = FSignature(forge.self)
        assert fsig['self'] == fsig.context


class TestMapper:
    @staticmethod
    def make_param(name, kind, default=void):
        return inspect.Parameter(name, kind, default=void_to_empty(default)) \
            if kind is not None \
            else None

    def test__repr__(self):
        fsignature = FSignature(forge.pos('a', 'b'))
        callable_ = lambda *, b: None
        mapper = Mapper(fsignature, callable_)
        assert repr(mapper) == '<Mapper (a, /) -> (*, b)>'

    @pytest.mark.parametrize(('has_context',), [(True,), (False,)])
    def test_get_context(self, has_context):
        fparam = forge.ctx('param') \
            if has_context \
            else forge.arg('param')
        fsig = FSignature(fparam)
        mapper = Mapper(fsig, lambda param: None)

        kwargs = {'param': object()}
        ctx = mapper.get_context(**kwargs)
        assert ctx == (kwargs['param'] if has_context else None)

    @pytest.mark.parametrize(('from_kind',), [
        pytest.param(POSITIONAL_ONLY, id='from_positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='from_positional_or_keyword'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='from_keyword_only'),
    ])
    @pytest.mark.parametrize(('to_kind',), [
        pytest.param(POSITIONAL_ONLY, id='to_positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='to_positional_or_keyword'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='to_keyword_only'),
        pytest.param(VAR_KEYWORD, id='to_var_keyword'),
    ])
    @pytest.mark.parametrize(('vary_name',), [
        pytest.param(True, id='varied_name'),
        pytest.param(False, id='same_name'),
    ])
    def test__call__params_mapped(self, from_kind, to_kind, vary_name):
        from_name, to_name = ('p1', 'p1') if not vary_name else ('p1', 'p2')
        fsig = FSignature(FParameter(from_kind, from_name, to_name))
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

    @pytest.mark.parametrize(('vary_name',), [
        pytest.param(True, id='varied_name'),
        pytest.param(False, id='same_name'),
    ])
    def test__call__vpo_param_mapped(self, vary_name):
        from_name, to_name = ('p1', 'p1') if not vary_name else ('p1', 'p2')
        fsig = FSignature(FParameter(VAR_POSITIONAL, from_name, to_name))
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
        from_name, to_name = ('p1', 'p1') if not vary_name else ('p1', 'p2')
        fsig = FSignature(FParameter(VAR_KEYWORD, from_name, to_name))
        func = lambda: None
        func.__signature__ = \
            inspect.Signature([inspect.Parameter(to_name, VAR_KEYWORD)])
        mapper = Mapper(fsig, func)

        call_args = CallArguments(a=1, b=2, c=3)
        assert mapper(**call_args.kwargs) == call_args

    def test__call__binding_error_raises_named(self):
        fsig = FSignature(forge.arg('a'))
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
        pytest.param(POSITIONAL_OR_KEYWORD, id='keyword_only'),
    ])
    @pytest.mark.parametrize(('to_kind',), [
        pytest.param(POSITIONAL_ONLY, id='positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional_or_keyword'),
        pytest.param(KEYWORD_ONLY, id='keyword_only'),
    ])
    @pytest.mark.parametrize(('from_default', 'to_default'), [
        pytest.param('from_def', void, id='from_default'),
        pytest.param(void, 'to_def', id='to_default'),
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
        # pylint: disable=R0913, too-many-arguments
        from_param = self.make_param(from_name, from_kind, from_default)
        from_sig = inspect.Signature([from_param] if from_param else None)
        fsig = FSignature.from_signature(from_sig)
        to_param = self.make_param(to_name, to_kind, to_default)
        to_sig = inspect.Signature([to_param])

        # Idenitfy map_parameters errors
        expected_exc = None
        if not from_param:
            if to_param.default is inspect.Parameter.empty:
                expected_exc = TypeError(
                    "Missing requisite mapping to non-default "
                    "{to_kind} parameter '{to_name}'".format(
                        to_kind=pk_strings[to_param.kind],
                        to_name=to_param.name,
                    )
                )
        elif from_param.name != to_param.name:
            if to_param.default is inspect.Parameter.empty:
                expected_exc = TypeError(
                    "Missing requisite mapping to non-default "
                    "{to_kind} parameter '{to_name}'".format(
                        to_kind=pk_strings[to_param.kind],
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
                "Missing requisite mapping from variable-keyword parameter "
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
        from_param = self.make_param('a', from_kind)
        from_sig = inspect.Signature([from_param])
        fsig = FSignature.from_signature(from_sig)
        to_param = self.make_param('kwargs', VAR_KEYWORD)
        to_sig = inspect.Signature([to_param])

        expected_exc = None
        if from_param.kind is VAR_POSITIONAL:
            expected_exc = TypeError(
                "Missing requisite mapping from variable-positional "
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
        from_param = self.make_param('a', from_kind)
        from_sig = inspect.Signature([from_param])
        fsig = FSignature.from_signature(from_sig)
        to_sig = inspect.Signature()

        with pytest.raises(TypeError) as excinfo:
            Mapper.map_parameters(fsig, to_sig)
        if from_param.kind in (VAR_KEYWORD, VAR_POSITIONAL):
            assert excinfo.value.args[0] == (
                "Missing requisite mapping from {from_kind} parameter 'a'".\
                    format(from_kind=pk_strings[from_kind])
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
        fsig = FSignature()
        to_param = self.make_param('a', to_kind, default=1)
        to_sig = inspect.Signature([to_param])

        assert Mapper.map_parameters(fsig, to_sig) == {}


def test_sign():
    @sign(*forge.args, **forge.kwargs)
    def func(*args, **kwargs):
        return CallArguments(*args, **kwargs)

    assert isinstance(func.__mapper__, Mapper)
    assert isinstance(func.__signature__, inspect.Signature)

    mapper = func.__mapper__
    assert mapper.callable == func.__wrapped__
    assert mapper.fsignature == FSignature(*forge.args, **forge.kwargs)
    assert mapper == Mapper(mapper.fsignature, func.__wrapped__)

    func.__mapper__ = Mock(side_effect=func.__mapper__)
    call_args = CallArguments(0, a=1)
    assert func(*call_args.args, **call_args.kwargs) == call_args
    func.__mapper__.assert_called_once_with(
        *call_args.args,
        **call_args.kwargs,
    )


def test_resign():
    @sign(forge.arg('a'))
    def func(**kwargs):
        return CallArguments(**kwargs)

    wrapped = func.__wrapped__
    old_mapper = func.__mapper__

    resigned = resign(forge.arg('b'))(func)
    assert resigned == func
    assert func.__wrapped__ == wrapped
    new_mapper = func.__mapper__
    assert new_mapper != old_mapper
    assert isinstance(new_mapper, Mapper)
    assert resigned.__mapper__.fsignature == FSignature(forge.arg('b'))

    resigned.__mapper__ = Mock(side_effect=func.__mapper__)
    call_args = CallArguments(b=1)
    assert func(*call_args.args, **call_args.kwargs) == call_args
    func.__mapper__.assert_called_once_with(
        *call_args.args,
        **call_args.kwargs,
    )