# -*- coding: utf-8 -*-
"""
hyper/common/headers
~~~~~~~~~~~~~~~~~~~~~

Contains hyper's structures for storing and working with HTTP headers.
"""
import collections


class HTTPHeaderMap(collections.MutableMapping):
    """
    A structure that contains HTTP headers.

    HTTP headers are a curious beast. At the surface level they look roughly
    like a name-value set, but in practice they have many variations that
    make them tricky:

    - duplicate keys are allowed
    - keys are compared case-insensitively
    - duplicate keys are isomorphic to comma-separated values, *except when
      they aren't*!
    - they logically contain a form of ordering

    This data structure is an attempt to preserve all of that information
    while being as user-friendly as possible.
    """
    def __init__(self, *args, **kwargs):
        # The meat of the structure. In practice, headers are an ordered list
        # of tuples. This early version of the data structure simply uses this
        # directly under the covers.
        #
        # An important curiosity here is that the headers are not stored in
        # 'canonical form', but are instead stored in the form they were
        # provided in. This is to ensure that it is always possible to
        # reproduce the original header structure if necessary. This leads to
        # some unfortunate performance costs on structure access where it is
        # often necessary to transform the data into canonical form on access.
        # This cost is judged acceptable in low-level code like `hyper`, but
        # higher-level abstractions should consider if they really require this
        # logic.
        self._items = []

        for arg in args:
            self._items.extend(arg)

        for k, v in kwargs.items():
            self._items.append((k, v))

    def __getitem__(self, key):
        """
        Unlike the dict __getitem__, this returns a list of items in the order
        they were added. These items are returned in 'canonical form', meaning
        that comma-separated values are split into multiple values.
        """
        values = []

        for k, v in self._items:
            if _keys_equal(k, key):
                values.extend(x[1] for x in canonical_form(k, v))

        if not values:
            raise KeyError("Nonexistent header key: {}".format(key))

        return values

    def __setitem__(self, key, value):
        """
        Unlike the dict __setitem__, this appends to the list of items.
        """
        self._items.append((key, value))

    def __delitem__(self, key):
        """
        Sadly, __delitem__ is kind of stupid here, but the best we can do is
        delete all headers with a given key. To correctly achieve the 'KeyError
        on missing key' logic from dictionaries, we need to do this slowly.
        """
        indices = []
        for (i, (k, v)) in enumerate(self._items):
            if _keys_equal(k, key):
                indices.append(i)

        if not indices:
            raise KeyError("Nonexistent header key: {}".format(key))

        for i in indices[::-1]:
            self._items.pop(i)

    def __iter__(self):
        """
        This mapping iterates like the list of tuples it is. The headers are
        returned in canonical form.
        """
        for pair in self._items:
            for value in canonical_form(*pair):
                yield value

    def __len__(self):
        """
        The length of this mapping is the number of individual headers in
        canonical form. Sadly, this is a somewhat expensive operation.
        """
        size = 0
        for _ in self:
            size += 1

        return size

    def __contains__(self, key):
        """
        If any header is present with this key, returns True.
        """
        return any(_keys_equal(key, k) for k, _ in self._items)

    def keys(self):
        """
        Returns an iterable of the header keys in the mapping. This explicitly
        does not filter duplicates, ensuring that it's the same length as
        len().
        """
        for n, _ in self:
            yield n

    def items(self):
        """
        This mapping iterates like the list of tuples it is.
        """
        return self.__iter__()

    def values(self):
        """
        This is an almost nonsensical query on a header dictionary, but we
        satisfy it in the exact same way we satisfy 'keys'.
        """
        for _, v in self:
            yield v

    def get(self, name, default=None):
        """
        Unlike the dict get, this returns a list of items in the order
        they were added.
        """
        try:
            return self[name]
        except KeyError:
            return default

    def __eq__(self, other):
        return self._items == other._items

    def __ne__(self, other):
        return self._items != other._items


def canonical_form(k, v):
    """
    Returns an iterable of key-value-pairs corresponding to the header in
    canonical form. This means that the header is split on commas unless for
    any reason it's a super-special snowflake (I'm looking at you Set-Cookie).
    """
    SPECIAL_SNOWFLAKES = set(['set-cookie', 'set-cookie2'])

    k = k.lower()

    if k in SPECIAL_SNOWFLAKES:
        yield k, v
    else:
        for sub_val in v.split(','):
            yield k, sub_val.strip()

def _keys_equal(x, y):
    """
    Returns 'True' if the two keys are equal by the laws of HTTP headers.
    """
    return x.lower() == y.lower()
