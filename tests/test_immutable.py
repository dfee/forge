import pytest

from forge._immutable import (
    Immutable,
    ImmutableInstanceError,
    Struct,
    asdict,
    replace,
)

# pylint: disable=C0103, invalid-name
# pylint: disable=R0201, no-self-use


def test_asdict_with__slots__():
    class Klass:
        __slots__ = ('value',)
        def __init__(self, value):
            self.value = value

    kwargs = {'value': 1}
    ins = Klass(**kwargs)
    assert not hasattr(ins, '__dict__')
    assert asdict(ins) == kwargs


def test_asdict_with__dict__():
    class Klass:
        def __init__(self, value):
            self.value = value

    kwargs = {'value': 1}
    ins = Klass(**kwargs)
    assert not hasattr(ins, '__slots__')
    assert asdict(ins) == kwargs


def test_replace():
    class Klass:
        def __init__(self, value):
            self.value = value

    k1 = Klass(1)
    k2 = replace(k1, value=2)
    assert (k1.value, k2.value) == (1, 2)


class TestImmutable:
    def test_type(self):
        ins = Immutable()
        assert hasattr(ins, '__slots__')
        assert not hasattr(ins, '__dict__')

    def test__getattr__(self):
        class Parent:
            called_with = None
            def __getattribute__(self, key):
                type(self).called_with = key

        class Klass(Immutable, Parent):
            pass

        ins = Klass()
        assert not ins.default
        assert Klass.called_with == 'default'

    def test__setattr__(self):
        class Klass(Immutable):
            a = 1

        ins = Klass()
        with pytest.raises(ImmutableInstanceError) as excinfo:
            ins.a = 1
        assert excinfo.value.args[0] == "cannot assign to field 'a'"


class TestStruct:
    def test_type(self):
        ins = Struct()
        assert hasattr(ins, '__slots__')
        assert not hasattr(ins, '__dict__')

    def test__init__(self):
        class Klass(Struct):
            __slots__ = ('a', 'b', 'c')
            def __init__(self):
                super().__init__(**dict(zip(['a', 'b', 'c'], range(3))))

        ins = Klass()
        for i, key in enumerate(Klass.__slots__):
            assert getattr(ins, key) == i

    @pytest.mark.parametrize(('val1', 'val2', 'eq'), [
        pytest.param(1, 1, True, id='eq'),
        pytest.param(1, 2, False, id='ne'),
    ])
    def test__eq__(self, val1, val2, eq):
        class Klass(Struct):
            __slots__ = ('a',)
            def __init__(self, a):
                super().__init__(a=a)

        assert (Klass(val1) == Klass(val2)) == eq

    def test__eq__type(self):
        class Klass1(Struct):
            __slots__ = ('a',)
            def __init__(self, a):
                super().__init__(a=a)

        class Klass2:
            __slots__ = ('a',)
            def __init__(self, a):
                self.a = a

        assert Klass1(1) != Klass2(2)
