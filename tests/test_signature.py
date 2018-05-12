import inspect
import types
from unittest.mock import Mock

import pytest

import forge
import forge._signature
from forge._parameter import ParameterMap
from forge._signature import (
    CallArguments,
    Forger,
    SignatureMapper,
    ident_t,
    get_run_validators,
    set_run_validators,
)

# pylint: disable=C0103, invalid-name
# pylint: disable=R0201, no-self-use
# pylint: disable=W0212, protected-access
# pylint: disable=W0621, redefined-outer-name
# pylint: disable=R0904, too-many-public-methods


empty = inspect.Parameter.empty
sign = Forger

POSITIONAL_ONLY = inspect.Parameter.POSITIONAL_ONLY  # type: ignore
POSITIONAL_OR_KEYWORD = inspect.Parameter.POSITIONAL_OR_KEYWORD  # type: ignore
VAR_POSITIONAL = inspect.Parameter.VAR_POSITIONAL
KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY
VAR_KEYWORD = inspect.Parameter.VAR_KEYWORD


@pytest.fixture(autouse=True)
def _reset_run_validators():
    prerun = forge._signature._run_validators
    yield
    forge._signature._run_validators = prerun


def assert_signatures_match(func1, func2):
    assert inspect.signature(func1) == inspect.signature(func2)


class TestRunValidators:
    def test_get_run_validators(self):
        rvmock = Mock()
        forge._signature._run_validators = rvmock
        assert get_run_validators() == rvmock

    @pytest.mark.parametrize(('val',), [(True,), (False,)])
    def test_set_run_validators(self, val):
        forge._signature._run_validators = not val
        set_run_validators(val)
        assert forge._signature._run_validators == val

    def test_set_run_validators_bad_param_raises(self):
        with pytest.raises(TypeError) as excinfo:
            set_run_validators(Mock())
        assert excinfo.value.args[0] == "'run' must be bool."


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


def test_ident_t():
    obj = object()
    assert ident_t(obj) == obj


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


def make_pos_signature(name, default=empty):
    return inspect.Signature(parameters=[
        inspect.Parameter(name, POSITIONAL_ONLY, default=default)
    ])


def make_pok_signature(name, default=empty):
    return inspect.Signature(parameters=[
        inspect.Parameter(name, POSITIONAL_OR_KEYWORD, default=default)
    ])



class TestForger:
    def test_validate_non_parameter_raises(self):
        with pytest.raises(TypeError) as excinfo:
            Forger.validate(1)
        assert excinfo.value.args[0] == "Received non-ParameterMap '1'"

    def test_validate_unnamed_parameter_raises(self):
        arg = forge.arg()
        with pytest.raises(ValueError) as excinfo:
            Forger.validate(arg)
        assert excinfo.value.args[0] == \
            "Received unnamed ParameterMap: '{}'".format(arg)

    def test_validate_late_contextual_param_raises(self):
        with pytest.raises(TypeError) as excinfo:
            Forger.validate(forge.arg('a'), forge.ctx('self'))
        assert excinfo.value.args[0] == \
            'Only the first ParameterMap can be contextual'

    def test_validate_multiple_interface_name_raises(self):
        with pytest.raises(ValueError) as excinfo:
            Forger.validate(forge.arg('a1', 'b'), forge.arg('a2', 'b'))
        assert excinfo.value.args[0] == \
            "Received multiple ParameterMaps with interface_name 'b'"

    def test_validate_multiple_name_raises(self):
        with pytest.raises(ValueError) as excinfo:
            Forger.validate(forge.arg('a', 'b1'), forge.arg('a', 'b2'))
        assert excinfo.value.args[0] == \
            "Received multiple ParameterMaps with name 'a'"

    def test_validate_multiple_var_positional_parameters_raises(self):
        params = [
            ParameterMap(
                kind=inspect.Parameter.VAR_POSITIONAL,
                name='args{}'.format(i),
                interface_name='args{}'.format(i),
                default=empty,
                type=empty,
            ) for i in range(2)
        ]
        with pytest.raises(TypeError) as excinfo:
            Forger.validate(*params)
        assert excinfo.value.args[0] == \
            'Received multiple variable-positional ParameterMaps'

    def test_validate_multiple_var_keyword_parameters_raises(self):
        params = [
            ParameterMap(
                kind=inspect.Parameter.VAR_KEYWORD,
                name='kwargs{}'.format(i),
                interface_name='kwargs{}'.format(i),
                default=empty,
                type=empty,
            ) for i in range(2)
        ]
        with pytest.raises(TypeError) as excinfo:
            Forger.validate(*params)
        assert excinfo.value.args[0] == \
            'Received multiple variable-keyword ParameterMaps'

    def test_validate_out_of_order_parameters_raises(self):
        kwarg_ = forge.kwarg('kwarg')
        arg_ = forge.arg('arg')
        with pytest.raises(SyntaxError) as excinfo:
            Forger.validate(kwarg_, arg_)
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
            Forger.validate(default, nondefault)
        assert excinfo.value.args[0] == (
            'non-default ParameterMap follows default ParameterMap'
        )

    def test_validate_multiple_parameters(self):
        Forger.validate(
            forge.pos('a'),
            forge.arg('b'),
            *forge.args,
            forge.kwarg('c'),
            list(dict(forge.kwargs).values())[0],
        )

    def test__eq__(self):
        forgers = [Forger(forge.arg('a')) for i in range(2)]
        assert forgers[0] == forgers[1]

    def test__eq__type_check(self):
        assert Forger() != object()

    def test__repr__(self):
        assert repr(Forger(forge.self)) == '<Forger (self)>'

    # Begin MutableSequence Tests
    def test__getitem__(self):
        pmap = forge.arg('a')
        forger = Forger(pmap)
        assert forger[0] is pmap

    def test__setitem__(self):
        pmap1, pmap2 = forge.arg('a'), forge.arg('b')
        forger = Forger(pmap1)
        forger[0] = pmap2
        assert forger[0] is pmap2

    def test__setitem__invalid_raises(self):
        forger = Forger(forge.pos('a'), forge.pos('b'))
        with pytest.raises(SyntaxError) as excinfo:
            forger[0] = forge.arg('a')
        assert excinfo.value.args[0] == (
            "b of kind 'POSITIONAL_ONLY' follows a of kind "
            "'POSITIONAL_OR_KEYWORD'"
        )

    def test__delitem__(self):
        forger = Forger(forge.arg('a'))
        del forger[0]
        assert not forger

    def test__len__(self):
        assert len(Forger(forge.arg('a'))) == 1

    def test_insert(self):
        pmap1, pmap2, pmap3 = forge.arg('a'), forge.arg('b'), forge.arg('c')
        forger = Forger(pmap1, pmap3)
        forger.insert(1, pmap2)
        assert list(forger) == [pmap1, pmap2, pmap3]

    def test_insert_invalid_raises(self):
        forger = Forger(forge.pos('a'))
        with pytest.raises(SyntaxError) as excinfo:
            forger.insert(0, forge.arg('b'))
        assert excinfo.value.args[0] == (
            "a of kind 'POSITIONAL_ONLY' follows b of kind "
            "'POSITIONAL_OR_KEYWORD'"
        )
    # End MutableSequence Tests

    def test__call__(self, monkeypatch):
        # pylint: disable=W0613, unused-argument
        forger = forge.Forger(forge.arg('a'))
        def func(a):
            return a

        captured_mapping = None
        make_mapper_func = forger.make_mapper
        def intercept_mapping(*args, **kwargs):
            nonlocal captured_mapping
            captured_mapping = make_mapper_func(*args, **kwargs)
            return captured_mapping

        forger.make_mapper = Mock(side_effect=intercept_mapping)
        wrapped = forger(func)

        assert wrapped.__wrapped__ is func
        assert isinstance(captured_mapping, SignatureMapper)
        assert wrapped.__signature_mapper__ is captured_mapping
        assert isinstance(wrapped.__signature__, inspect.Signature)
        assert wrapped.__signature__ is captured_mapping.sig_public

        obj = object()
        assert wrapped(obj) is obj

    def test_from_callable(self):
        def func(a: int = 0):
            return a
        forger = Forger.from_callable(func)
        assert len(forger) == 1
        assert forger[0] == ParameterMap(
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            name='a',
            interface_name='a',
            default=0,
            type=int,
        )

    def test_var_positional(self):
        forger = Forger(*forge.args)
        assert forger[0] == forger.var_positional

    def test_var_keyword(self):
        forger = Forger(**forge.kwargs)
        assert forger[0] == forger.var_keyword

    def test_context(self):
        forger = Forger(forge.self)
        assert forger[0] == forger.context

    def test_converters(self):
        name, converter = 'a', lambda ctx, k, v: None
        forger = Forger(forge.arg(name, converter=converter))
        assert forger.converters == {name: converter}

    def test_validators(self):
        name, validator = 'a', lambda ctx, k, v: None
        forger = Forger(forge.arg(name, validator=validator))
        assert forger.validators == {name: validator}

    @pytest.mark.parametrize(('spec',), [('interface',), ('name',)])
    def test_get_parameters(self, spec):
        name, iname = 'name', 'iname'
        forger = Forger(forge.arg(name, iname, default=0, type=int))
        attr_name, exp_name = ('interface_parameters', iname) \
            if spec == 'interface' \
            else ('public_parameters', name)
        assert getattr(forger, attr_name) == [
            inspect.Parameter(
                name=exp_name,
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=0,
                annotation=int,
            )
        ]

    @pytest.mark.parametrize(('returns',), [(None,), (empty,)])
    @pytest.mark.parametrize(('interface',), [(False,), (True,)])
    def test_make_signature(self, returns, interface):
        pname, iname = 'pname', 'iname'
        forger = Forger(forge.arg(pname, iname))
        signature = forger.make_signature(
            interface=interface,
            return_annotation=returns,
        )
        expected_name = iname if interface else pname
        assert signature.parameters == {
            expected_name: inspect.Parameter(
                name=expected_name,
                kind=POSITIONAL_OR_KEYWORD,
            ),
        }
        assert signature.return_annotation == returns

    def test_make_mapper(self):
        converter, validator = lambda: None, lambda: None
        forger = Forger(
            forge.arg('a', 'b', converter=converter, validator=validator),
        )
        # pylint: disable=C0321, multiple-statements
        # pylint: disable=W0613, unused-argument
        def func(*, b: int = 0) -> int: pass
        mapper = forger.make_mapper(func)

        for k, v in dict(
                callable_=func,
                has_context=False,
                sig_public=inspect.Signature(parameters=[
                    inspect.Parameter(
                        name='a',
                        kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    ),
                ], return_annotation=int),
                sig_interface=inspect.Signature(parameters=[
                    inspect.Parameter(
                        name='b',
                        kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    ),
                ], return_annotation=int),
                converters={'a': converter},
                validators={'a': validator},
            ).items():
            assert getattr(mapper, k) == v

        pre_tf_interface = CallArguments(1)
        post_tf_interface = mapper.tf_interface(pre_tf_interface)
        assert pre_tf_interface == post_tf_interface

        post_tf_private = mapper.tf_private(post_tf_interface)
        assert post_tf_private == CallArguments(b=1)


class TestSignatureMapper:
    @pytest.fixture
    def mapper_factory(self):
        defaults = dict(
            callable_=lambda: None,
            has_context=False,
            sig_public=inspect.Signature(),
            sig_interface=inspect.Signature(),
        )

        def _make(*, converters=None, validators=None, **kwargs):
            if converters:
                kwargs['converters'] = types.MappingProxyType(converters)
            if validators:
                kwargs['validators'] = types.MappingProxyType(validators)
            kwargs = {**defaults, **kwargs}
            return SignatureMapper(**kwargs)

        return _make

    def test__repr__(self, mapper_factory):
        mapper = mapper_factory(
            callable_=lambda *, b: None,
            sig_public=inspect.Signature(parameters=[
                inspect.Parameter('a', POSITIONAL_ONLY)
            ]),
        )
        assert repr(mapper) == '<SignatureMapper (a, /) -> (*, b)>'

    @pytest.mark.parametrize(('has_context',), [(True,), (False,)])
    def test_convert(self, mapper_factory, has_context):
        mapper = mapper_factory(
            has_context=has_context,
            converters={'a': lambda ctx, k, v: (ctx, k, v)},
            sig_public=inspect.Signature(
                [inspect.Parameter('ctx', POSITIONAL_OR_KEYWORD)] \
                if has_context else []
            ),
        )
        arguments = {'ctx': object(), 'a': 1}
        mapper.convert(arguments)
        assert arguments == {
            'ctx': arguments['ctx'],
            'a': (arguments['ctx'] if has_context else None, 'a', 1),
        }

    @pytest.mark.parametrize(('plural',), [(True,), (False,)])
    @pytest.mark.parametrize(('has_context',), [(True,), (False,)])
    @pytest.mark.parametrize(('enabled',), [(True,), (False,)])
    def test_validate(self, mapper_factory, plural, has_context, enabled):
        called_with = None
        def validator(ctx, k, v):
            nonlocal called_with
            called_with = (ctx, k, v)
        mapper = mapper_factory(
            has_context=has_context,
            validators={'a': [validator] if plural else validator},
            sig_public=inspect.Signature(
                [inspect.Parameter('ctx', POSITIONAL_OR_KEYWORD)] \
                if has_context else []
            ),
        )
        arguments = {'ctx': object(), 'a': 1}
        if not enabled:
            set_run_validators(False)

        mapper.validate(arguments)
        if enabled:
            assert called_with == \
                (arguments['ctx'] if has_context else None, 'a', 1)

    def test__call__(self, mapper_factory):
        called = dict(
            convert=False,
            validate=False,
            tf_interface=False,
            tf_private=False,
        )
        def convert(ctx, k, v):  # pylint: disable=W0613, unused-argument
            nonlocal called
            called['convert'] = True
            return v

        def validate(ctx, k, v):  # pylint: disable=W0613, unused-argument
            nonlocal called
            called['validate'] = True

        def tf_interface(call_args):
            nonlocal called
            called['tf_interface'] = True
            return call_args

        def tf_private(call_args):
            nonlocal called
            called['tf_private'] = True
            return call_args

        sig = inspect.Signature(parameters=[
            inspect.Parameter('a', POSITIONAL_ONLY),
            inspect.Parameter('b', KEYWORD_ONLY),
        ])

        mapper = mapper_factory(
            sig_public=sig,
            sig_interface=sig,
            converters={'a': convert},
            validators={'a': validate},
            tf_interface=tf_interface,
            tf_private=tf_private,
        )

        expected = CallArguments(1, b=1)
        assert mapper(*expected.args, **expected.kwargs) == expected
        assert all(called.values())

    def test__call__binding_error_raises_named(self, mapper_factory):
        def myfunc(a):
            return a
        sig = inspect.Signature(parameters=[
            inspect.Parameter('a', POSITIONAL_ONLY)
        ])
        mapper = mapper_factory(callable_=myfunc, sig_public=sig)
        with pytest.raises(TypeError) as excinfo:
            mapper()
        assert excinfo.value.args[0] == \
            "myfunc() missing a required argument: 'a'"

    def test__call__defaults_applied(self, mapper_factory):
        sig = inspect.Signature(parameters=[
            inspect.Parameter('a', POSITIONAL_OR_KEYWORD, default=1)
        ])
        mapper = mapper_factory(
            sig_public=sig,
            sig_interface=sig,
        )
        assert mapper() == mapper(1)