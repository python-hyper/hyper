# -*- coding: utf-8 -*-
from hyper.http20.frame import (
    Frame, DataFrame, PriorityFrame, RstStreamFrame, SettingsFrame,
    PushPromiseFrame, PingFrame, GoAwayFrame, WindowUpdateFrame, HeadersFrame,
    ContinuationFrame,
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


class TestGoAwayFrame(object):
    def test_go_away_has_no_flags(self):
        f = GoAwayFrame(0)
        flags = f.parse_flags(0xFF)

        assert not flags
        assert isinstance(flags, set)

    def test_goaway_serializes_properly(self):
        f = GoAwayFrame(0)
        f.last_stream_id = 64
        f.error_code = 32
        f.additional_data = b'hello'

        s = f.serialize()
        assert s == (
            b'\x00\x0D\x07\x00\x00\x00\x00\x00' +  # Frame header
            b'\x00\x00\x00\x40'                 +  # Last Stream ID
            b'\x00\x00\x00\x20'                 +  # Error Code
            b'hello'                               # Additional data
        )


class TestWindowUpdateFrame(object):
    def test_window_update_has_no_flags(self):
        f = WindowUpdateFrame(0)
        flags = f.parse_flags(0xFF)

        assert not flags
        assert isinstance(flags, set)

    def test_window_update_serializes_properly(self):
        f = WindowUpdateFrame(0)
        f.window_increment = 512

        s = f.serialize()
        assert s == b'\x00\x04\x09\x00\x00\x00\x00\x00\x00\x00\x02\x00'


class TestHeadersFrame(object):
    def test_headers_frame_flags(self):
        f = HeadersFrame(1)
        flags = f.parse_flags(0xFF)

        assert flags == set(['END_STREAM', 'END_HEADERS', 'PRIORITY'])

    def test_headers_frame_serialize_with_priority_properly(self):
        f = HeadersFrame(1)
        f.parse_flags(0xFF)
        f.priority = (2 ** 30) + 1
        f.data = b'hello world'

        s = f.serialize()
        assert s == (
            b'\x00\x0F\x01\x0D\x00\x00\x00\x01' +
            b'\x40\x00\x00\x01' +
            b'hello world'
        )

    def test_headers_frame_serialize_without_priority_properly(self):
        f = HeadersFrame(1)
        f.parse_flags(0xFF)
        f.data = b'hello world'

        s = f.serialize()
        assert s == (
            b'\x00\x0B\x01\x0D\x00\x00\x00\x01' +
            b'hello world'
        )


class TestContinuationFrame(object):
    def test_continuation_frame_flags(self):
        f = ContinuationFrame(1)
        flags = f.parse_flags(0xFF)

        assert flags == set(['END_HEADERS'])
