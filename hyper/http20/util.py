# -*- coding: utf-8 -*-
"""
hyper/http20/util
~~~~~~~~~~~~~~~~~

Utility functions for use with hyper.
"""
def get_from_key_value_set(kvset, key, default=None):
    """
    Returns a value from a key-value set, or the default if the value isn't
    present.
    """
    value = pop_from_key_value_set(kvset.copy(), key)[0]
    return value if value is not None else default

def pop_from_key_value_set(kvset, *keys):
    """
    Pops the values of ``keys`` from ``kvset`` and returns them as a tuple. If a
    key is not found in ``kvset``, ``None`` is used instead.

    >>> kvset = [('a',0), ('b',1), ('c',2)]
    >>> pop_from_key_value_set(kvset, 'a', 'foo', 'c')
    (0, None, 2)
    >>> kvset
    [('b', 1)]
    """
    extracted = [None] * len(keys)
    rest = set()
    for key, value in kvset:
        try:
            extracted[keys.index(key)] = value
        except ValueError:
            rest.add((key, value))
    kvset.intersection_update(rest)
    return tuple(extracted)
