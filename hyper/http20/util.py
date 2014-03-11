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
    for name, value in kvset:
        if name == key:
            return value
    return default
