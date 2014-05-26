# -*- coding: utf-8 -*-
"""
hyper/http20/hpack_structures
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Contains data structures used in hyper's HPACK implementation.
"""
class Reference(object):
    """
    The reference object is essentially an object that 'points to' another
    object, not unlike a pointer in C or similar languages. This object is
    distinct from the normal Python name because we can tell the difference
    between a reference and the 'actual' object.

    It behaves in the following ways:

    - Two references to the same object evaluate equal.
    - Two references to different objects evaluate not equal, even if those
      objects themselves evaluate equal.
    - Two references to the same object hash to the same value.
    - Two references to different objects hash to different values.

    The reference is distinct from and does not use weak references. A
    reference may never point at an object that has been garbage collected.
    This means that, to ensure objects get GC'd, any reference to them must
    also go out of scope.

    This object is _conceptually_ immutable, but the implementation doesn't
    attempt to enforce that to avoid the overhead. Be warned that changing
    the object being referenced after creation could lead to all sorts of weird
    nonsense.

    :param obj: The object being referenced.
    """
    def __init__(self, obj):
        self.obj = obj

        # Whether the header being referenced by this reference has been
        # emitted in this round of header processing.
        self.emitted = False

    def __eq__(self, other):
        return (isinstance(other, Reference) and self.obj is other.obj)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return id(self.obj)
