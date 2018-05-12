import inspect

import pytest

from forge._exceptions import ParameterError
import forge._parameter as fparam
from forge._utils import (
    hasparam,
    getparam,
    get_return_type,
    get_var_keyword_parameter,
    get_var_positional_parameter,
    set_return_type,
    stringify_parameters,
)

# pylint: disable=C0103, invalid-name
# pylint: disable=R0201, no-self-use
# pylint: disable=W0621, redefined-outer-name

empty = inspect.Parameter.empty

@pytest.fixture
def func_with_param():
    # pylint: disable=W0613, unused-argument
    def func(myparam):
        pass
    return func


@pytest.fixture
def func_without_param():
    def func():
        pass
    return func


class TestHasParam:
    @pytest.mark.parametrize(('has_param',), [(True,), (False,)])
    def test_correct_usage(self, has_param):
        funcs = {
            True: lambda myparam: None,
            False: lambda: None,
        }
        assert hasparam(funcs[has_param], 'myparam') == has_param

    def test_incorrect_usage_raises(self):
        with pytest.raises(TypeError) as excinfo:
            hasparam(1, 'param')
        assert excinfo.value.args[0] == '1 is not callable'


class TestGetParam:
    @pytest.mark.parametrize(('has_param', 'has_default'), [
        (True, False),
        (False, True),
        (False, False),
    ])
    def test_correct_usage(self, has_param, has_default):
        func = (lambda myparam: None) \
            if has_param \
            else (lambda: None)

        if has_param:
            assert getparam(func, 'myparam') == \
                inspect.signature(func).parameters['myparam']
        elif has_default:
            assert getparam(func, 'myparam', 'DEFAULT') == 'DEFAULT'
        else:
            with pytest.raises(ParameterError) as excinfo:
                getparam(func, 'myparam')
            assert excinfo.value.args[0] == \
                "'{}' has no parameter 'myparam'".format(func.__name__)

    def test_incorrect_usage_raises(self):
        with pytest.raises(TypeError) as excinfo:
            getparam(1, 'param')
        assert excinfo.value.args[0] == '1 is not callable'


class TestGetReturnType:
    @pytest.mark.parametrize(('returns',), [(empty,), (None,)])
    @pytest.mark.parametrize(('has_signature',), [(False,), (True,)])
    def test_callable(self, returns, has_signature):
        # pylint: disable=W0613, unused-argument
        # pylint: disable=C0321, multiple-statements
        if has_signature:
            def func(): pass
            func.__signature__ = inspect.signature(func).\
                replace(return_annotation=returns)
        else:
            def func() -> returns: pass
        assert get_return_type(func) == returns

    def test_incorrect_usage_raises(self):
        with pytest.raises(TypeError) as excinfo:
            get_return_type(1)
        assert excinfo.value.args[0] == '1 is not callable'


class TestSetRetrunType:
    @pytest.mark.parametrize(('has_signature',), [(True,), (False,)])
    @pytest.mark.parametrize(('returns',), [(int,), (empty,)])
    def test_set_return_type(self, has_signature, returns):
        # pylint: disable=W0613, unused-argument
        # pylint: disable=C0321, multiple-statements
        def func(self) -> float: pass
        if has_signature:
            func.__signature__ = inspect.signature(func)
        set_return_type(func, returns)
        if has_signature:
            assert func.__signature__.return_annotation == returns
        else:
            assert not hasattr(func, '__signature__')
            if returns is not empty:
                assert func.__annotations__['return'] == returns
            else:
                assert 'return' not in func.__annotations__

    def test_incorrect_usage_raises(self):
        with pytest.raises(TypeError) as excinfo:
            set_return_type(1, None)
        assert excinfo.value.args[0] == '1 is not callable'


natural_pos = inspect.Parameter(
    'arg',
    inspect.Parameter.POSITIONAL_ONLY,
)
natural_arg = inspect.Parameter(
    'arg',
    inspect.Parameter.POSITIONAL_OR_KEYWORD,
)
natural_args = inspect.Parameter(
    'args',
    inspect.Parameter.VAR_POSITIONAL,
)
natural_kwarg = inspect.Parameter(
    'kwarg',
    inspect.Parameter.KEYWORD_ONLY,
)
natural_kwargs = inspect.Parameter(
    'kwargs',
    inspect.Parameter.VAR_KEYWORD,
)
natural_params = [
    natural_arg,
    natural_args,
    natural_kwarg,
    natural_kwargs,
]

pt_pos = fparam.pos('pos')
pt_pok = fparam.arg('arg')
pt_vpo = list(fparam.args)[0]
pt_kwo = fparam.kwarg('kwarg')
pt_vkw = fparam.kwargs[fparam.kwargs.name]
pt_params = [
    pt_pos,
    pt_pok,
    pt_vpo,
    pt_kwo,
    pt_vkw,
]

@pytest.mark.parametrize(('params', 'expected'), [
    (natural_params, natural_args),
    (pt_params, pt_vpo),
    ((), None),
])
def test_get_var_positional_parameter(params, expected):
    assert get_var_positional_parameter(*params) is expected


@pytest.mark.parametrize(('params', 'expected'), [
    (natural_params, natural_kwargs),
    (pt_params, pt_vkw),
    ((), None),
])
def test_get_var_keyword_parameter(params, expected):
    assert get_var_keyword_parameter(*params) is expected


@pytest.mark.parametrize(('params', 'expected',), [
    pytest.param(
        (),
        '',
        id='positional_only',
    ),
    pytest.param(
        (fparam.pos('a'),),
        'a, /',
        id='positional_only',
    ),
    pytest.param(
        (fparam.arg('a'),),
        'a',
        id='positional_or_keyword',
    ),
    pytest.param(
        (fparam.kwarg('a'),),
        '*, a',
        id='keyword_only',
    ),
])
def test_stringify_parameters(params, expected):
    assert stringify_parameters(*params) == expected