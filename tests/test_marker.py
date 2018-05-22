import inspect

import pytest

from forge._marker import (
    MarkerMeta,
    empty,
    void,
)

# pylint: disable=R0201, no-self-use
# pylint: disable=W0212, protected-access


class TestMarkerMeta:
    @pytest.fixture
    def make_marker(self):
        return lambda name: MarkerMeta(name, (), {})

    def test__repr__(self, make_marker):
        name = 'dummy'
        assert repr(make_marker(name)) == '<{}>'.format(name)

    def test__bool__(self, make_marker):
        assert not make_marker('dummy')

    def test_instance(self, make_marker):
        marker = make_marker('dummy')
        assert marker() is marker


class TestEmpty:
    def test_cls(self):
        assert isinstance(empty, MarkerMeta)
        assert empty.native is inspect.Parameter.empty

    @pytest.mark.parametrize(('in_', 'out_'), [
        pytest.param(1, 1, id='non_empty'),
        pytest.param(empty, inspect.Parameter.empty, id='empty'),
    ])
    def test_ccoerce(self, in_, out_):
        assert empty.ccoerce(in_) == out_


class TestVoid:
    def test_cls(self):
        assert isinstance(void, MarkerMeta)