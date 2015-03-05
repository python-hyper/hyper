from hyper.common.headers import HTTPHeaderMap

import pytest

class TestHTTPHeaderMap(object):
    def test_header_map_can_insert_single_header(self):
        h = HTTPHeaderMap()
        h['key'] = 'value'
        assert h['key'] == ['value']

    def test_header_map_insensitive_key(self):
        h = HTTPHeaderMap()
        h['KEY'] = 'value'
        assert h['key'] == ['value']

    def test_header_map_is_iterable_in_order(self):
        h = HTTPHeaderMap()
        items = [
            ('k1', 'v2'),
            ('k2', 'v2'),
            ('k2', 'v3'),
        ]

        for k, v in items:
            h[k] = v

        for i, pair in enumerate(h):
            assert items[i] == pair

    def test_header_map_allows_multiple_values(self):
        h = HTTPHeaderMap()
        h['key'] = 'v1'
        h['Key'] = 'v2'

        assert h['key'] == ['v1', 'v2']

    def test_header_map_can_delete_value(self):
        h = HTTPHeaderMap()
        h['key'] = 'v1'
        del h['key']

        with pytest.raises(KeyError):
            h['key']

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

        assert h['key'] == ['v1', 'v2']

    def test_containment(self):
        h = HTTPHeaderMap()
        h['key'] = 'val'

        assert 'key' in h
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
        assert list(h.keys()) == ['k1', 'k1', 'k2', 'k1']

    def test_values(self):
        h = HTTPHeaderMap()
        h['k1'] = 'v1, v2'
        h['k2'] = 'v3'
        h['k1'] = 'v4'

        assert len(list(h.values())) == 4
        assert list(h.values()) == ['v1', 'v2', 'v3', 'v4']

    def test_items(self):
        h = HTTPHeaderMap()
        items = [
            ('k1', 'v2'),
            ('k2', 'v2'),
            ('k2', 'v3'),
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

        assert h.get('k1') == ['v1', 'v2', 'v4']

    def test_doesnt_split_set_cookie(self):
        h = HTTPHeaderMap()
        h['Set-Cookie'] = 'v1, v2'
        assert h['set-cookie'] == ['v1, v2']
        assert h.get('set-cookie') == ['v1, v2']

    def test_equality(self):
        h1 = HTTPHeaderMap()
        h1['k1'] = 'v1, v2'
        h1['k2'] = 'v3'
        h1['k1'] = 'v4'

        h2 = HTTPHeaderMap()
        h2['k1'] = 'v1'
        h2['k1'] = 'v2'
        h2['k2'] = 'v3'
        h2['k1'] = 'v4'

        assert h1 == h2

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
            ('k1', 'v2'),
            ('k2', 'v2'),
            ('k2', 'v3'),
        ]
        h = HTTPHeaderMap(items)

        assert list(h) == items

    def test_can_create_from_multiple_iterables(self):
        items = [
            ('k1', 'v2'),
            ('k2', 'v2'),
            ('k2', 'v3'),
        ]
        h = HTTPHeaderMap(items, items, items)

        assert list(h) == items + items + items

    def test_create_from_iterables_and_kwargs(self):
        items = [
            ('k1', 'v2'),
            ('k2', 'v2'),
            ('k2', 'v3'),
        ]
        h = HTTPHeaderMap(items, k3='v4', k4='v5')

        assert list(h) == items + [('k3', 'v4'), ('k4', 'v5')]
