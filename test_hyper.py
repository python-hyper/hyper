# -*- coding: utf-8 -*-
from hyper.http20.frame import Frame, DataFrame
import pytest


class TestGeneralFrameBehaviour(object):
    def test_base_frame_ignores_flags(self):
        f = Frame(0)
        flags = f.parse_flags(0xFF)
        assert not flags
        assert isinstance(flags, set)

    def test_base_frame_cant_serialize(self):
        f = Frame(0)
        with pytest.raises(NotImplementedError):
            f.serialize()

    def test_base_frame_cant_generate_frame_header(self):
        f = Frame(0)
        with pytest.raises(NotImplementedError):
            f.build_frame_header()


class TestDataFrame(object):
    def test_data_frame_has_only_one_flag(self):
        f = DataFrame(1)
        flags = f.parse_flags(0xFF)
        assert flags == set(['END_STREAM'])

    def test_data_frame_serializes_properly(self):
        f = DataFrame(1)
        f.flags = set(['END_STREAM'])
        f.data = b'testdata'

        s = f.serialize()
        assert s == b'\x00\x08\x00\x01\x00\x00\x00\x01testdata'
