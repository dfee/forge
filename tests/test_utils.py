import inspect
import sys

import pytest

from forge._signature import (
    KEYWORD_ONLY,
    POSITIONAL_ONLY,
    POSITIONAL_OR_KEYWORD,
    VAR_KEYWORD,
    VAR_POSITIONAL,
)
from forge._utils import CallArguments, callwith, repr_callable, sort_arguments

# pylint: disable=C0103, invalid-name
# pylint: disable=R0201, no-self-use


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


@pytest.mark.parametrize(('strategy',), [('class_callable',), ('function',)])
def test_repr_callable(strategy):
    """
    Ensure that callables are stringified with:
    - func.__name__ OR repr(func) if class callable
    - parameters
    - return type annotation
    """
    # pylint: disable=W0622, redefined-builtin
    class Dummy:
        def __init__(self, value: int = 0) -> None:
            self.value = value
        def __call__(self, value: int = 1) -> int:
            return value

    if strategy == 'class_callable':
        ins = Dummy()
        expected = '{}(value:int=1) -> int'.format(ins) \
            if sys.version_info.minor < 7 \
            else '{}(value: int = 1) -> int'.format(ins)
        assert repr_callable(ins) == expected
    elif strategy == 'function':
        expected = 'Dummy(value:int=0) -> None' \
            if sys.version_info.minor < 7 \
            else 'Dummy(value: int = 0) -> None'
        assert repr_callable(Dummy) == expected
    else:
        raise TypeError('Unknown strategy {}'.format(strategy))


class TestSortArguments:
    @pytest.mark.parametrize(('kind', 'named', 'unnamed', 'expected'), [
        pytest.param(  # func(param, /)
            POSITIONAL_ONLY, dict(param=1), None, CallArguments(1),
            id='positional-only',
        ),
        pytest.param(  # func(param)
            POSITIONAL_OR_KEYWORD, dict(param=1), None, CallArguments(1),
            id='positional-or-keyword',
        ),
        pytest.param(  # func(*param)
            VAR_POSITIONAL, None, (1,), CallArguments(1),
            id='var-positional',
        ),
        pytest.param(  # func(*, param)
            KEYWORD_ONLY, dict(param=1), None, CallArguments(param=1),
            id='keyword-only',
        ),
        pytest.param( # func(**param)
            VAR_KEYWORD, dict(param=1), None, CallArguments(param=1),
            id='var-keyword',
        ),
    ])
    def test_sorting(self, kind, named, unnamed, expected):
        """
        Ensure that a named argument is appropriately sorted into a:
        - positional-only param
        - positional-or-keyword param
        - keyword-only param
        - var-keyword param
        """
        to_ = inspect.Signature([inspect.Parameter('param', kind)])
        result = sort_arguments(to_, named, unnamed)
        assert result == expected

    @pytest.mark.parametrize(('kind', 'expected'), [
        pytest.param(  # func(param=1, /)
            POSITIONAL_ONLY, CallArguments(1),
            id='positional-only',
        ),
        pytest.param(  # func(param=1)
            POSITIONAL_OR_KEYWORD, CallArguments(1),
            id='positional-or-keyword',
        ),
        pytest.param(  # func(*, param=1)
            KEYWORD_ONLY, CallArguments(param=1),
            id='keyword-only',
        ),
    ])
    def test_sorting_with_defaults(self, kind, expected):
        """
        Ensure that unsuplied named arguments use default values
        """
        to_ = inspect.Signature([inspect.Parameter('param', kind, default=1)])
        result = sort_arguments(to_)
        assert result == expected

    @pytest.mark.parametrize(('kind',), [
        pytest.param(POSITIONAL_ONLY, id='positional-only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional-or-keyword'),
        pytest.param(KEYWORD_ONLY, id='keyword-only'),
    ])
    def test_no_argument_for_non_default_param_raises(self, kind):
        """
        Ensure that a non-default parameter must have an argument passed
        """
        sig = inspect.Signature([inspect.Parameter('a', kind)])
        with pytest.raises(ValueError) as excinfo:
            sort_arguments(sig)
        assert excinfo.value.args[0] == \
            "Non-default parameter 'a' has no argument value"

    def test_extra_to_sig_without_vko_raises(self):
        """
        Ensure a signature without a var-keyword parameter raises when extra
        arguments are supplied
        """
        sig = inspect.Signature()
        with pytest.raises(TypeError) as excinfo:
            sort_arguments(sig, {'a': 1})
        assert excinfo.value.args[0] == 'Cannot sort arguments (a)'

    def test_unnamaed_to_sig_without_vpo_raises(self):
        """
        Ensure a signature without a var-positional parameter raises when a
        var-positional argument is supplied
        """
        sig = inspect.Signature()
        with pytest.raises(TypeError) as excinfo:
            sort_arguments(sig, unnamed=(1,))
        assert excinfo.value.args[0] == 'Cannot sort var-positional arguments'

    def test_callable(self):
        """
        Ensure that callable's are viable arguments for ``to_``
        """
        func = lambda a, b=2, *args, c, d=4, **kwargs: None
        assert sort_arguments(func, dict(a=1, c=3, e=5), ('args1',)) == \
            CallArguments(1, 2, 'args1', c=3, d=4, e=5)


def test_callwith():
    """
    Ensure that ``callwith`` works as expected
    """
    func = lambda a, b=2, *args, c, d=4, **kwargs: (a, b, args, c, d, kwargs)
    assert callwith(func, dict(a=1, c=3, e=5), ('args1',)) == \
        (1, 2, ('args1',), 3, 4, {'e': 5})
