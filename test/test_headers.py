from __future__ import unicode_literals
from hyper.common.headers import HTTPHeaderMap

import pytest


class TestHTTPHeaderMap(object):
    def test_header_map_can_insert_single_header(self):
        h = HTTPHeaderMap()
        h['key'] = 'value'
        assert h['key'] == [b'value']

    def test_header_map_insensitive_key(self):
        h = HTTPHeaderMap()
        h['KEY'] = 'value'
        assert h['key'] == [b'value']

    def test_header_map_is_iterable_in_order(self):
        h = HTTPHeaderMap()
        items = [
            (b'k1', b'v2'),
            (b'k2', b'v2'),
            (b'k2', b'v3'),
        ]

        for k, v in items:
            h[k] = v

        for i, pair in enumerate(h):
            assert items[i] == pair

    def test_header_map_allows_multiple_values(self):
        h = HTTPHeaderMap()
        h['key'] = b'v1'
        h[b'Key'] = b'v2'

        assert h['key'] == [b'v1', b'v2']

    def test_header_map_can_delete_value(self):
        h = HTTPHeaderMap()
        h['key'] = b'v1'
        del h[b'key']

        with pytest.raises(KeyError):
            h[b'key']

    def test_header_map_deletes_all_values(self):
        h = HTTPHeaderMap()
        h['key'] = 'v1'
        h['key'] = 'v2'
        del h['key']

        with pytest.raises(KeyError):
            h['key']

    def test_setting_comma_separated_header(self):
        h = HTTPHeaderMap()
        h['key'] = 'v1, v2'

        assert h[b'key'] == [b'v1', b'v2']

    def test_containment(self):
        h = HTTPHeaderMap()
        h['key'] = 'val'

        assert 'key' in h
        assert b'key' in h
        assert 'nonkey' not in h

    def test_length_counts_lines_separately(self):
        h = HTTPHeaderMap()
        h['k1'] = 'v1, v2'
        h['k2'] = 'v3'
        h['k1'] = 'v4'

        assert len(h) == 4

    def test_keys(self):
        h = HTTPHeaderMap()
        h['k1'] = 'v1, v2'
        h['k2'] = 'v3'
        h['k1'] = 'v4'

        assert len(list(h.keys())) == 4
        assert list(h.keys()) == [b'k1', b'k1', b'k2', b'k1']

    def test_values(self):
        h = HTTPHeaderMap()
        h['k1'] = 'v1, v2'
        h['k2'] = 'v3'
        h['k1'] = 'v4'

        assert len(list(h.values())) == 4
        assert list(h.values()) == [b'v1', b'v2', b'v3', b'v4']

    def test_items(self):
        h = HTTPHeaderMap()
        items = [
            (b'k1', b'v2'),
            (b'k2', b'v2'),
            (b'k2', b'v3'),
        ]

        for k, v in items:
            h[k] = v

        for i, pair in enumerate(h.items()):
            assert items[i] == pair

    def test_empty_get(self):
        h = HTTPHeaderMap()
        assert h.get('nonexistent', 'hi there') == 'hi there'

    def test_actual_get(self):
        h = HTTPHeaderMap()
        h['k1'] = 'v1, v2'
        h['k2'] = 'v3'
        h['k1'] = 'v4'

        assert h.get('k1') == [b'v1', b'v2', b'v4']

    def test_doesnt_split_set_cookie(self):
        h = HTTPHeaderMap()
        h['Set-Cookie'] = 'v1, v2'
        assert h['set-cookie'] == [b'v1, v2']
        assert h.get(b'set-cookie') == [b'v1, v2']

    def test_equality(self):
        h1 = HTTPHeaderMap()
        h1['k1'] = 'v1, v2'
        h1['k2'] = 'v3'
        h1['k1'] = 'v4'

        h2 = HTTPHeaderMap()
        h2['k1'] = 'v1, v2'
        h2['k2'] = 'v3'
        h2['k1'] = 'v4'

        assert h1 == h2

    def test_inequality_of_raw_ordering(self):
        h1 = HTTPHeaderMap()
        h1['k1'] = 'v1, v2'
        h1['k2'] = 'v3'
        h1['k1'] = 'v4'

        h2 = HTTPHeaderMap()
        h2['k1'] = 'v1'
        h2['k1'] = 'v2'
        h2['k2'] = 'v3'
        h2['k1'] = 'v4'

        assert h1 != h2

    def test_inequality(self):
        h1 = HTTPHeaderMap()
        h1['k1'] = 'v1, v2'
        h1['k2'] = 'v3'
        h1['k1'] = 'v4'

        h2 = HTTPHeaderMap()
        h2['k1'] = 'v1'
        h2['k1'] = 'v4'
        h2['k1'] = 'v2'
        h2['k2'] = 'v3'

        assert h1 != h2

    def test_deleting_nonexistent(self):
        h = HTTPHeaderMap()

        with pytest.raises(KeyError):
            del h['key']

    def test_can_create_from_iterable(self):
        items = [
            (b'k1', b'v2'),
            (b'k2', b'v2'),
            (b'k2', b'v3'),
        ]
        h = HTTPHeaderMap(items)

        assert list(h) == items

    def test_can_create_from_multiple_iterables(self):
        items = [
            (b'k1', b'v2'),
            (b'k2', b'v2'),
            (b'k2', b'v3'),
        ]
        h = HTTPHeaderMap(items, items, items)

        assert list(h) == items + items + items

    def test_create_from_iterables_and_kwargs(self):
        items = [
            (b'k1', b'v2'),
            (b'k2', b'v2'),
            (b'k2', b'v3'),
        ]
        h = list(HTTPHeaderMap(items, k3='v4', k4='v5'))

        # kwargs are an unordered dictionary, so allow for both possible
        # iteration orders.
        assert (
            h == items + [(b'k3', b'v4'), (b'k4', b'v5')] or
            h == items + [(b'k4', b'v5'), (b'k3', b'v4')]
        )

    def test_raw_iteration(self):
        items = [
            (b'k1', b'v2'),
            (b'k2', b'v2, v3, v4'),
            (b'k2', b'v3'),
        ]
        h = HTTPHeaderMap(items)

        assert list(h.iter_raw()) == items

    def test_headers_must_be_strings(self):
        with pytest.raises(ValueError):
            HTTPHeaderMap(key=1)

        h = HTTPHeaderMap()
        with pytest.raises(ValueError):
            h['k'] = 1

        with pytest.raises(ValueError):
            h[1] = 'v'

    def test_merge_self_is_no_op(self):
        h = HTTPHeaderMap([(b'hi', b'there')])
        h.merge(h)

        assert h == HTTPHeaderMap([(b'hi', b'there')])

    def test_merge_headermaps_preserves_raw(self):
        h1 = HTTPHeaderMap([
            (b'hi', b'there')
        ])
        h2 = HTTPHeaderMap([
            (b'Hi', b'there, sir, maam')
        ])

        h1.merge(h2)

        assert list(h1.iter_raw()) == [
            (b'hi', b'there'),
            (b'Hi', b'there, sir, maam'),
        ]

    def test_merge_header_map_dict(self):
        h = HTTPHeaderMap([(b'hi', b'there')])
        d = {'cat': 'dog'}

        h.merge(d)

        assert list(h.items()) == [
            (b'hi', b'there'),
            (b'cat', b'dog'),
        ]

    def test_replacing(self):
        h = HTTPHeaderMap([
            (b'name', b'value'),
            (b'name2', b'value2'),
            (b'name2', b'value2'),
            (b'name3', b'value3'),
        ])

        h.replace('name2', '42')
        h.replace('name4', 'other_value')

        assert list(h.items()) == [
            (b'name', b'value'),
            (b'name2', b'42'),
            (b'name3', b'value3'),
            (b'name4', b'other_value'),
        ]
