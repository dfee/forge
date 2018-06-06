import pytest

from forge._exceptions import ImmutableInstanceError
from forge._immutable import Immutable, asdict, replace

# pylint: disable=C0103, invalid-name
# pylint: disable=R0201, no-self-use


class TestAsDict:
    def test__slots__(self):
        """
        Ensure that ``asdict`` pulls ivars from classes with ``__slots__``,
        and excludes private attributes (those starting with `_`)
        """
        class Klass:
            __slots__ = ('value', '_priv')
            def __init__(self, value):
                self.value = value
                self._priv = 1

        kwargs = {'value': 1}
        ins = Klass(**kwargs)
        assert not hasattr(ins, '__dict__')
        assert asdict(ins) == kwargs

    def test__dict__(self):
        """
        Ensure that ``asdict`` pulls ivars from classes with ``__dict__``, and
        excludes private attributes (those starting with `_`)
        """
        class Klass:
            def __init__(self, value):
                self.value = value
                self._priv = 1

        kwargs = {'value': 1}
        ins = Klass(**kwargs)
        assert not hasattr(ins, '__slots__')
        assert asdict(ins) == kwargs


def test_replace():
    """
    Ensure that ``replace`` produces a varied copy
    """
    class Klass:
        def __init__(self, value):
            self.value = value

    k1 = Klass(1)
    k2 = replace(k1, value=2)
    assert (k1.value, k2.value) == (1, 2)


class TestImmutable:
    def test_type(self):
        """
        Ensure an instance of ``Immutable`` has ```__slots__` but not
        ``__dict__``; i.e. it's truly a slots instance.
        """
        ins = Immutable()
        assert hasattr(ins, '__slots__')
        assert not hasattr(ins, '__dict__')

    def test__init__(self):
        """
        Ensure that Immutable.__init__ sets values without relying on
        ``__setattr__``.
        """
        class Klass(Immutable):
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
        """
        Ensure equality check compares ivars.
        """
        class Klass(Immutable):
            __slots__ = ('a',)
            def __init__(self, a):
                super().__init__(a=a)

        assert (Klass(val1) == Klass(val2)) == eq

    def test__eq__type(self):
        """
        Ensure equality check compares types
        """
        class Klass1(Immutable):
            __slots__ = ('a',)
            def __init__(self, a):
                super().__init__(a=a)

        class Klass2:
            __slots__ = ('a',)
            def __init__(self, a):
                self.a = a

        assert Klass1(1) != Klass2(1)

    def test__getattr__(self):
        """
        Ensure ``__getattr__`` passes request to ``super().__getattribute__``
        """
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
        """
        Ensure Immutable is immutable; ``__setattr__`` raises
        """
        class Klass(Immutable):
            a = 1

        ins = Klass()
        with pytest.raises(ImmutableInstanceError) as excinfo:
            ins.a = 1
        assert excinfo.value.args[0] == "cannot assign to field 'a'"
