# -*- coding: utf-8 -*-
"""
hyper/http20/util
~~~~~~~~~~~~~~~~~

Utility functions for use with hyper.
"""
from collections import defaultdict


def get_from_key_value_set(kvset, key, default=None):
    """
    Returns a value from a key-value set, or the default if the value isn't
    present.
    """
    value = pop_from_key_value_set(kvset[:], key)[0]
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
    indices_to_remove = []
    for index, elem in enumerate(kvset):
        key, value = elem
        try:
            extracted[keys.index(key)] = value
            indices_to_remove.append(index)
        except ValueError:
            pass

    for index in indices_to_remove[::-1]:
        kvset.pop(index)

    return tuple(extracted)

def combine_repeated_headers(kvset):
    """
    Given a list of key-value pairs (like for HTTP headers!), combines pairs
    with the same key together, separating the values with NULL bytes. This
    function maintains the order of input keys, because it's awesome.
    """
    def set_pop(set, item):
        set.remove(item)
        return item

    headers = defaultdict(list)
    keys = set()

    for key, value in kvset:
        headers[key].append(value)
        keys.add(key)

    return [(set_pop(keys, k), b'\x00'.join(headers[k])) for k, v in kvset
            if k in keys]

def split_repeated_headers(kvset):
    """
    Given a set of key-value pairs (like for HTTP headers!), finds values that
    have NULL bytes in them and splits them into a dictionary whose values are
    lists.
    """
    headers = defaultdict(list)

    for key, value in kvset:
        headers[key] = value.split(b'\x00')

    return dict(headers)
