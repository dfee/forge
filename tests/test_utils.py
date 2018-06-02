import inspect

import pytest

import forge
from forge._exceptions import NoParameterError
from forge._marker import empty
from forge._utils import (
    KEYWORD_ONLY,
    POSITIONAL_ONLY,
    POSITIONAL_OR_KEYWORD,
    VAR_KEYWORD,
    VAR_POSITIONAL,
    CallArguments,
    callwith,
    hasparam,
    getparam,
    get_return_type,
    get_var_keyword_parameter,
    get_var_positional_parameter,
    set_return_type,
    sort_arguments,
    stringify_parameters,
    stringify_callable,
)

# pylint: disable=C0103, invalid-name
# pylint: disable=R0201, no-self-use
# pylint: disable=W0621, redefined-outer-name


class TestCallArguments:
    def test_from_bound_arguments(self):
        """
        Ensure that ``inspect.BoundArguments`` ``args`` and ``kwargs`` are
        properly mapped to a new ``CallArguments`` instance.
        """
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
        """
        Ensure that ``CallArguments`` ``args`` and ``kwargs`` are
        properly mapped to a new ``inspect.BoundArguments`` instance.
        """
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
        """
        Ensure that ``CallArguments.__repr__`` is a pretty print of ``args``
        and ``kwargs``.
        """
        assert repr(CallArguments(*args, **kwargs)) == \
            '<CallArguments ({})>'.format(expected)


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


natural_pos = inspect.Parameter('pos', POSITIONAL_ONLY)
natural_arg = inspect.Parameter('arg', POSITIONAL_OR_KEYWORD)
natural_args = inspect.Parameter('args', VAR_POSITIONAL)
natural_kwarg = inspect.Parameter('kwarg', KEYWORD_ONLY)
natural_kwargs = inspect.Parameter('kwargs', VAR_KEYWORD)
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


class TestSortArguments:
    @pytest.mark.parametrize(('in_', 'expected'), [
        pytest.param(dict(arguments={'a': 1}), 1, id='arguments'),
        pytest.param(dict(vkw={'a': 1}), 1, id='vkw'),
        pytest.param(dict(arguments={'a': 1}, vkw={'a': 2}), 1, id='override'),
    ])
    @pytest.mark.parametrize(('kind',), [
        pytest.param(POSITIONAL_ONLY, id='positional-only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional-or-keyword'),
        pytest.param(KEYWORD_ONLY, id='keyword-only'),
    ])
    def test_non_variadic(self, kind, in_, expected):
        """
        Ensure mapping for kind -> result

        - POSITIONAL_ONLY -> CallArguments(1)
        - POSITIONAL_OR_KEYWORD -> CallArguments(1)
        - KEYWORD_ONLY -> CallArguments(a=1)

        with `a` passed as an argument, as a vkw argument, and as an argument
        overriding a vkw.
        """
        sig = inspect.Signature([inspect.Parameter('a', kind)])
        result = sort_arguments(sig, **in_)
        if kind is KEYWORD_ONLY:
            assert result == CallArguments(a=expected)
        else:
            assert result == CallArguments(expected)

    @pytest.mark.parametrize(('in_',), [
        pytest.param(dict(arguments={'a': 1}), id='arguments'),
        pytest.param(dict(vkw={'a': 1}), id='vkw'),
        pytest.param(dict(arguments={'a': 1}, vkw={'a': 2}), id='override'),
    ])
    def test_to_vkw(self, in_):
        """
        Ensure mapping to vkw if parameter with name DNE
        """
        sig = inspect.Signature([inspect.Parameter('kwargs', VAR_KEYWORD)])
        assert sort_arguments(sig, **in_) == CallArguments(a=1)

    @pytest.mark.parametrize(('in_',), [(dict(vpo=[1, 2, 3]),)])
    def test_vpo_passthrough(self, in_):
        """
        Ensure mapping to vpo is pass-through
        """
        sig = inspect.Signature([inspect.Parameter('args', VAR_POSITIONAL)])
        assert sort_arguments(sig, **in_) == CallArguments(*in_['vpo'])

    @pytest.mark.parametrize(('as_',), [('arguments',), ('vkw',)])
    def test_remainder_no_vkw_param_raises(self, as_):
        """
        Ensure a signature without a var-keyword parameter raises when extra
        arguments are supplied
        """
        sig = inspect.Signature()
        with pytest.raises(TypeError) as excinfo:
            sort_arguments(sig, **{as_: {'a': 1}})
        assert excinfo.value.args[0] == 'Cannot sort arguments (a)'

    def test_remainder_no_vpo_param_raises(self):
        """
        Ensure a signature without a var-positional parameter raises when a
        var-positional argument is supplied
        """
        sig = inspect.Signature()
        with pytest.raises(TypeError) as excinfo:
            sort_arguments(sig, vpo=(1,))
        assert excinfo.value.args[0] == 'Cannot sort var-positional arguments'

    @pytest.mark.parametrize(('kind',), [
        pytest.param(POSITIONAL_ONLY, id='positional-only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional-or-keyword'),
        pytest.param(KEYWORD_ONLY, id='keyword-only'),
    ])
    def test_no_mapping_to_non_default_parameter_raises(self, kind):
        """
        Ensure that a non-default parameter must have an argument passed
        """
        sig = inspect.Signature([inspect.Parameter('a', kind)])
        with pytest.raises(ValueError) as excinfo:
            sort_arguments(sig)
        assert excinfo.value.args[0] == \
            "Non-default parameter 'a' has no argument value"

    def test_callable(self):
        """
        Ensure that callable's are viable arguments for ``to_``
        """
        func = lambda a, b=2, *args, c, d=4, **kwargs: None
        assert sort_arguments(
            func,
            arguments={'a': 1, 'c': 3},
            vpo=('args1',),
            vkw={'e': 5},
        ) == CallArguments(1, 2, 'args1', c=3, d=4, e=5)


def test_callwith():
    """
    Ensure that ``callwith`` works as expected
    """
    func = lambda a, b=2, *args, c, d=4, **kwargs: (a, b, args, c, d, kwargs)
    assert callwith(
        func,
        arguments={'a': 1, 'c': 3},
        vpo=('args1',),
        vkw={'e': 5},
    ) == (1, 2, ('args1',), 3, 4, {'e': 5})