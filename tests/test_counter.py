from forge._counter import (
    Counter,
    CreationOrderMeta,
)


def test_counter():
    """
    Ensure that calling a ``Counter`` instance returns the next value.
    """
    counter = Counter()
    assert counter() == 0
    assert counter() == 1


def test_cretion_order_meta():
    """
    Ensure that ``CreationOrderMeta`` classes have instances that are ordered.
    """
    class Klass(metaclass=CreationOrderMeta):
        # pylint: disable=R0903, too-few-public-methods
        pass

    assert hasattr(Klass, '_creation_counter')
    # pylint: disable=E1101, no-member
    assert isinstance(Klass._creation_counter, Counter)
    # pylint: enable=E1101, no-member
    klass1, klass2 = Klass(), Klass()
    for i, kls in enumerate([klass1, klass2]):
        assert hasattr(kls, '_creation_order')
        assert i == kls._creation_order