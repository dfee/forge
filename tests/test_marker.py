import pytest

from forge._marker import (
    MarkerMeta,
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
        assert repr(make_marker(name)) == f'<{name}>'

    def test__bool__(self, make_marker):
        assert not make_marker('dummy')

    def test_instance(self, make_marker):
        marker = make_marker('dummy')
        assert marker() is marker


class TestVoid:
    def test_cls(self):
        assert isinstance(void, MarkerMeta)

    def test_instance(self):
        assert void() is void

    def test__repr__(self):
        assert repr(void) == '<void>'