import inspect

import pytest

import forge
from forge._exceptions import NoParameterError
from forge._marker import empty
from forge._utils import (
    hasparam,
    getparam,
    get_return_type,
    get_var_keyword_parameter,
    get_var_positional_parameter,
    set_return_type,
    stringify_parameters,
    stringify_callable,
)

# pylint: disable=C0103, invalid-name
# pylint: disable=R0201, no-self-use
# pylint: disable=W0621, redefined-outer-name


class TestHasParam:
    @pytest.mark.parametrize(('has_param',), [(True,), (False,)])
    def test_callable(self, has_param):
        """
        Ensure ``hasparam`` returns an appropriately truthy value when used
        properly
        """
        funcs = {
            True: lambda myparam: None,
            False: lambda: None,
        }
        assert hasparam(funcs[has_param], 'myparam') == has_param

    def test_noncallable_raises(self):
        """
        Ensure ``hasparam`` raises a TypeError when a non-callable is passed
        """
        with pytest.raises(TypeError) as excinfo:
            hasparam(1, 'param')
        assert excinfo.value.args[0] == '1 is not callable'


class TestGetParam:
    @pytest.mark.parametrize(('has_param', 'has_default'), [
        (True, False),
        (False, True),
        (False, False),
    ])
    def test_callable(self, has_param, has_default):
        """
        Ensure ``getparam`` returns the param or the default value
        """
        func = (lambda myparam: None) \
            if has_param \
            else (lambda: None)

        if has_param:
            assert getparam(func, 'myparam') == \
                inspect.signature(func).parameters['myparam']
        elif has_default:
            assert getparam(func, 'myparam', 'DEFAULT') == 'DEFAULT'
        else:
            with pytest.raises(NoParameterError) as excinfo:
                getparam(func, 'myparam')
            assert excinfo.value.args[0] == \
                "'{}' has no parameter 'myparam'".format(func.__name__)

    def test_noncallable_raises(self):
        """
        Ensure ``getparam`` raises a TypeError when a non-callable is passed
        """
        with pytest.raises(TypeError) as excinfo:
            getparam(1, 'param')
        assert excinfo.value.args[0] == '1 is not callable'


class TestGetReturnType:
    @pytest.mark.parametrize(('returns',), [(empty.native,), (None,)])
    @pytest.mark.parametrize(('has_signature',), [(False,), (True,)])
    def test_callable(self, returns, has_signature):
        """
        Ensure ``get_return_type`` returns the correct return type annotation
        """
        # pylint: disable=W0613, unused-argument
        # pylint: disable=C0321, multiple-statements
        if has_signature:
            def func(): pass
            func.__signature__ = inspect.signature(func).\
                replace(return_annotation=returns)
        else:
            def func() -> returns: pass
        assert get_return_type(func) == returns

    def test_noncallable_raises(self):
        """
        Ensure ``get_return_type`` raises a TypeError when a non-callable is
        passed
        """
        with pytest.raises(TypeError) as excinfo:
            get_return_type(1)
        assert excinfo.value.args[0] == '1 is not a callable object'


class TestSetRetrunType:
    @pytest.mark.parametrize(('has_signature',), [(True,), (False,)])
    @pytest.mark.parametrize(('returns',), [(int,), (empty.native,)])
    def test_callable(self, has_signature, returns):
        """
        Ensure that ``set_return_type`` works across signatures:
        - with ``__annotations__`` attribute
        - without ``__annotations__`` attribute
        """
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
            if returns is not empty.native:
                assert func.__annotations__['return'] == returns
            else:
                assert 'return' not in func.__annotations__

    def test_noncallable_raises(self):
        """
        Ensure ``set_return_type`` raises a TypeError when a non-callable is
        passed
        """
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

pt_pos = forge.pos('pos')
pt_pok = forge.arg('arg')
pt_vpo = list(forge.args)[0]
pt_kwo = forge.kwarg('kwarg')
pt_vkw = forge.kwargs[forge.kwargs.name]
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
    """
    Ensure the ``var-positional`` param (or None) is returned for:
    - ``inspect.Signature``
    - ``forge.FSignature``
    """
    assert get_var_positional_parameter(*params) is expected


@pytest.mark.parametrize(('params', 'expected'), [
    (natural_params, natural_kwargs),
    (pt_params, pt_vkw),
    ((), None),
])
def test_get_var_keyword_parameter(params, expected):
    """
    Ensure the ``var-keyword`` param (or None) is returned for:
    - ``inspect.Signature``
    - ``forge.FSignature``
    """
    assert get_var_keyword_parameter(*params) is expected


@pytest.mark.parametrize(('params', 'expected',), [
    pytest.param(
        (),
        '',
        id='positional_only',
    ),
    pytest.param(
        (forge.pos('a'),),
        'a, /',
        id='positional_only',
    ),
    pytest.param(
        (forge.arg('a'),),
        'a',
        id='positional_or_keyword',
    ),
    pytest.param(
        (forge.kwarg('a'),),
        '*, a',
        id='keyword_only',
    ),
])
def test_stringify_parameters(params, expected):
    """
    Ensure that collections of parameters are appropriately stringified:
    - positional-only are followed by ``/``
    - keyword-only are preceeded by ``*``
    """
    assert stringify_parameters(*params) == expected


def dummy_func_cls_rt(a) -> bool:
    """
    dummy func with a cls return type annotation
    """
    # pylint: disable=W0613, unused-argument
    return True


def dummy_func_ins_rt(a) -> True:
    """
    dummy func with an instance return type annotation
    """
    # pylint: disable=W0613, unused-argument
    return True


class DummyCallable:
    """
    Class for testing with a ``__call__`` method
    """
    # pylint: disable=R0903, too-few-public-methods
    def __call__(self):
        pass

dummy_callable = DummyCallable()


@pytest.mark.parametrize(('callable', 'expected'), [
    pytest.param(
        dummy_func_cls_rt,
        'dummy_func_cls_rt(a) -> bool',
        id='function_cls_return_type',
    ),
    pytest.param(
        dummy_func_ins_rt,
        'dummy_func_ins_rt(a) -> True',
        id='function_ins_return_type',
    ),
    pytest.param(
        dummy_callable,
        '{}()'.format(dummy_callable),
        id='ins_callable',
    ),
    pytest.param(
        lambda x: None,
        '<lambda>(x)',
        id='lambda',
    ),
])
def test_stringify_callable(callable, expected):
    """
    Ensure that callables are stringified with:
    - func.__name__
    - parameters
    - return type annotation
    """
    # pylint: disable=W0622, redefined-builtin
    assert stringify_callable(callable) == expected