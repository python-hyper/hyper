# -*- coding: utf-8 -*-
from hyper.http20.hpack_structures import Reference

class TestReference(object):
    """
    Tests of the HPACK reference structure.
    """
    def test_references_can_be_created(self):
        r = Reference(None)
        assert r

    def test_references_have_not_been_emitted_by_default(self):
        r = Reference(None)
        assert not r.emitted

    def test_two_references_to_the_same_object_compare_equal(self):
        a = 'hi'
        r1 = Reference(a)
        r2 = Reference(a)

        assert r1 == r2

    def test_two_references_to_equal_but_different_objects_compare_different(self):
        a = ['hi']  # Use lists to avoid interning
        b = ['hi']
        r1 = Reference(a)
        r2 = Reference(b)

        assert r1 != r2

    def test_two_references_to_unequal_objects_compare_different(self):
        a = 'hi'
        b = 'hi there'
        r1 = Reference(a)
        r2 = Reference(b)

        assert r1 != r2

    def test_two_references_to_the_same_object_hash_the_same(self):
        a = 'hi'
        r1 = Reference(a)
        r2 = Reference(a)

        assert r1.__hash__() == r2.__hash__()

    def test_two_references_to_equal_but_different_objects_hash_differently(self):
        a = ['hi']  # Use lists to avoid interning.
        b = ['hi']
        r1 = Reference(a)
        r2 = Reference(b)

        assert r1.__hash__() != r2.__hash__()

    def test_two_references_to_unequal_objects_hash_differently(self):
        a = 'hi'
        b = 'hi there'
        r1 = Reference(a)
        r2 = Reference(b)

        assert r1.__hash__() != r2.__hash__()
