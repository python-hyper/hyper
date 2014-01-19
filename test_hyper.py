# -*- coding: utf-8 -*-
from hyper.http20.frame import (
    Frame, DataFrame, PriorityFrame, RstStreamFrame, SettingsFrame,
    PushPromiseFrame, PingFrame
)
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


class TestPriorityFrame(object):
    def test_priority_frame_has_no_flags(self):
        f = PriorityFrame(1)
        flags = f.parse_flags(0xFF)
        assert not flags
        assert isinstance(flags, set)

    def test_priority_frame_serializes_properly(self):
        f = PriorityFrame(1)
        f.priority = 0xFF

        s = f.serialize()
        assert s == b'\x00\x04\x02\x00\x00\x00\x00\x01\x00\x00\x00\xff'


class TestRstStreamFrame(object):
    def test_rst_stream_frame_has_no_flags(self):
        f = RstStreamFrame(1)
        flags = f.parse_flags(0xFF)
        assert not flags
        assert isinstance(flags, set)

    def test_rst_stream_frame_serializes_properly(self):
        f = RstStreamFrame(1)
        f.error_code = 420

        s = f.serialize()
        assert s == b'\x00\x04\x03\x00\x00\x00\x00\x01\x00\x00\x01\xa4'


class TestSettingsFrame(object):
    def test_settings_frame_has_only_one_flag(self):
        f = SettingsFrame(0)
        flags = f.parse_flags(0xFF)
        assert flags == set(['ACK'])

    def test_settings_frame_serializes_properly(self):
        f = SettingsFrame(0)
        f.parse_flags(0xFF)
        f.settings = {
            SettingsFrame.HEADER_TABLE_SIZE: 4096,
            SettingsFrame.ENABLE_PUSH: 0,
            SettingsFrame.MAX_CONCURRENT_STREAMS: 100,
            SettingsFrame.INITIAL_WINDOW_SIZE: 65535,
            SettingsFrame.FLOW_CONTROL_OPTIONS: 1,
        }

        s = f.serialize()
        assert s == (
            b'\x00\x28\x04\x01\x00\x00\x00\x00' +  # Frame header
            b'\x00\x00\x00\x01\x00\x00\x10\x00' +  # HEADER_TABLE_SIZE
            b'\x00\x00\x00\x02\x00\x00\x00\x00' +  # ENABLE_PUSH
            b'\x00\x00\x00\x04\x00\x00\x00\x64' +  # MAX_CONCURRENT_STREAMS
            b'\x00\x00\x00\x0A\x00\x00\x00\x01' +  # FLOW_CONTROL_OPTIONS
            b'\x00\x00\x00\x07\x00\x00\xFF\xFF'    # INITIAL_WINDOW_SIZE
        )


class TestPushPromiseFrame(object):
    def test_push_promise_unsupported(self):
        with pytest.raises(NotImplementedError):
            f = PushPromiseFrame(1)


class TestPingFrame(object):
    def test_ping_frame_has_only_one_flag(self):
        f = PingFrame(0)
        flags = f.parse_flags(0xFF)

        assert flags == set(['ACK'])

    def test_ping_frame_serializes_properly(self):
        f = PingFrame(0)
        f.parse_flags(0xFF)
        f.opaque_data = b'\x01\x02'

        s = f.serialize()
        assert s == (
            b'\x00\x08\x06\x01\x00\x00\x00\x00\x01\x02\x00\x00\x00\x00\x00\x00'
        )

    def test_no_more_than_8_octets(self):
        f = PingFrame(0)
        f.opaque_data = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09'

        with pytest.raises(ValueError):
            f.serialize()
