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
    _, value = extract_from_key_value_set(kvset, key)
    return value if value is not None else default

def extract_from_key_value_set(kvset, *keys):
    """
    Extracts the values of ``keys`` from ``kvset`` and returns a tuple
    ``(rest, value1, value2, ...)``, where ``rest`` is the set of key-value
    pairs not specified in ``keys``. If a key is not found in ``kvset``,
    ``None`` is returned in its place.

    >>> extract_from_key_value_set([('a',0),('b',1),('c',2)], 'a', 'foo', 'c')
    ([('b', 1)], 0, None, 2)
    """
    extracted = [None] * len(keys)
    rest = []
    for key, value in kvset:
        if key in keys:
            extracted[keys.index(key)] = value
        else:
            rest.append((key, value))
    return tuple([rest] + extracted)
