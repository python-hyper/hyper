# -*- coding: utf-8 -*-
"""
test/socket
~~~~~~~~~~~

Test the BufferedSocket implementation in hyper.
"""
import pytest

import hyper.common.bufsocket
from hyper.common.bufsocket import BufferedSocket
from hyper.common.exceptions import ConnectionResetError, LineTooLongError


# Patch the select method in bufsocket to make sure that it always returns
# the dummy socket as readable.
def dummy_select(a, b, c, d):
    return a


class TestBufferedSocket(object):
    """
    Tests of the hyper BufferedSocket object.
    """
    def test_can_create_buffered_sockets(self, monkeypatch):
        monkeypatch.setattr(
            hyper.common.bufsocket.select, 'select', dummy_select
        )
        s = DummySocket()
        b = BufferedSocket(s)

        assert b is not None
        assert b._buffer_size == 1000

    def test_can_send_on_buffered_socket(self, monkeypatch):
        monkeypatch.setattr(
            hyper.common.bufsocket.select, 'select', dummy_select
        )
        s = DummySocket()
        b = BufferedSocket(s)
        b.send(b'test data')

        assert len(s.outbound_packets) == 1
        assert s.outbound_packets[0] == b'test data'

    def test_receive_single_packet(self, monkeypatch):
        monkeypatch.setattr(
            hyper.common.bufsocket.select, 'select', dummy_select
        )
        s = DummySocket()
        b = BufferedSocket(s)
        s.inbound_packets.append(b'test data')

        d = b.recv(100).tobytes()
        assert d == b'test data'

    def test_receive_multiple_packets_one_at_a_time(self, monkeypatch):
        monkeypatch.setattr(
            hyper.common.bufsocket.select, 'select', dummy_select
        )
        s = DummySocket()
        b = BufferedSocket(s)
        s.inbound_packets = [b'Here', b'begins', b'the', b'test', b'data']

        d = b''
        for _ in range(5):
            d += b.recv(100).tobytes()

        assert d == b'Herebeginsthetestdata'

    def test_receive_small_packets(self, monkeypatch):
        monkeypatch.setattr(
            hyper.common.bufsocket.select, 'select', dummy_select
        )
        s = DummySocket()
        b = BufferedSocket(s)
        s.inbound_packets = [b'Here', b'begins', b'the', b'test', b'data']

        d = b''
        for _ in range(5):
            d += b.recv(100).tobytes()

        assert d == b'Herebeginsthetestdata'

    def test_receive_multiple_packets_at_once(self, monkeypatch):
        monkeypatch.setattr(
            hyper.common.bufsocket.select, 'select', dummy_select
        )
        s = DummySocket()
        b = BufferedSocket(s)
        s.inbound_packets = [
            b'Here', b'begins', b'the', b'test', b'data', b'!'
        ]
        s.read_count = 3

        d = b''
        for _ in range(22):
            d += b.recv(1).tobytes()

        assert d == b'Herebeginsthetestdata!'

    def test_filling_the_buffer(self, monkeypatch):
        monkeypatch.setattr(
            hyper.common.bufsocket.select, 'select', dummy_select
        )
        s = DummySocket()
        b = BufferedSocket(s)
        s.inbound_packets = [
            b'a' * 1000,
            b'a' * 800,
        ]

        d = b''
        for _ in range(2):
            d += b.recv(900).tobytes()

        assert d == (b'a' * 1800)

    def test_oversized_read(self, monkeypatch):
        monkeypatch.setattr(
            hyper.common.bufsocket.select, 'select', dummy_select
        )
        s = DummySocket()
        b = BufferedSocket(s)
        s.inbound_packets.append(b'a' * 600)

        d = b.recv(1200).tobytes()
        assert d == b'a' * 600

    def test_readline_from_buffer(self, monkeypatch):
        monkeypatch.setattr(
            hyper.common.bufsocket.select, 'select', dummy_select
        )
        s = DummySocket()
        b = BufferedSocket(s)

        one = b'hi there\r\n'
        two = b'this is another line\r\n'
        three = b'\r\n'
        combined = b''.join([one, two, three])
        b._buffer_view[0:len(combined)] = combined
        b._bytes_in_buffer += len(combined)

        assert b.readline().tobytes() == one
        assert b.readline().tobytes() == two
        assert b.readline().tobytes() == three

    def test_readline_from_socket(self, monkeypatch):
        monkeypatch.setattr(
            hyper.common.bufsocket.select, 'select', dummy_select
        )
        s = DummySocket()
        b = BufferedSocket(s)

        one = b'hi there\r\n'
        two = b'this is another line\r\n'
        three = b'\r\n'
        combined = b''.join([one, two, three])

        for i in range(0, len(combined), 5):
            s.inbound_packets.append(combined[i:i+5])

        assert b.readline().tobytes() == one
        assert b.readline().tobytes() == two
        assert b.readline().tobytes() == three

    def test_readline_both(self, monkeypatch):
        monkeypatch.setattr(
            hyper.common.bufsocket.select, 'select', dummy_select
        )
        s = DummySocket()
        b = BufferedSocket(s)

        one = b'hi there\r\n'
        two = b'this is another line\r\n'
        three = b'\r\n'
        combined = b''.join([one, two, three])

        split_index = int(len(combined) / 2)

        b._buffer_view[0:split_index] = combined[0:split_index]
        b._bytes_in_buffer += split_index

        for i in range(split_index, len(combined), 5):
            s.inbound_packets.append(combined[i:i+5])

        assert b.readline().tobytes() == one
        assert b.readline().tobytes() == two
        assert b.readline().tobytes() == three

    def test_socket_error_on_readline(self, monkeypatch):
        monkeypatch.setattr(
            hyper.common.bufsocket.select, 'select', dummy_select
        )
        s = DummySocket()
        b = BufferedSocket(s)

        with pytest.raises(ConnectionResetError):
            b.readline()

    def test_socket_readline_too_long(self, monkeypatch):
        monkeypatch.setattr(
            hyper.common.bufsocket.select, 'select', dummy_select
        )
        s = DummySocket()
        b = BufferedSocket(s)

        b._buffer_view[0:b._buffer_size] = b'0' * b._buffer_size
        b._bytes_in_buffer = b._buffer_size

        with pytest.raises(LineTooLongError):
            b.readline()

    def test_socket_fill_basic(self):
        s = DummySocket()
        b = BufferedSocket(s)
        s.inbound_packets = [b'Here', b'begins', b'the']

        assert not len(b.buffer)

        b.fill()
        assert len(b.buffer) == 4

        b.fill()
        assert len(b.buffer) == 10

        b.fill()
        assert len(b.buffer) == 13

    def test_socket_fill_resizes_if_needed(self):
        s = DummySocket()
        b = BufferedSocket(s)
        s.inbound_packets = [b'Here']
        b._index = 1000

        assert not len(b.buffer)

        b.fill()
        assert len(b.buffer) == 4
        assert b._index == 0

    def test_socket_fill_raises_connection_errors(self):
        s = DummySocket()
        b = BufferedSocket(s)

        with pytest.raises(ConnectionResetError):
            b.fill()

    def test_advancing_sockets(self):
        s = DummySocket()
        b = BufferedSocket(s)
        b._buffer_view[0:5] = b'abcde'
        b._bytes_in_buffer += 5

        assert len(b.buffer) == 5

        b.advance_buffer(3)
        assert len(b.buffer) == 2

        assert b.buffer.tobytes() == b'de'


class DummySocket(object):
    def __init__(self):
        self.inbound_packets = []
        self.outbound_packets = []
        self.read_count = 1

    def recv_into(self, buffer):
        index = 0
        try:
            for _ in range(self.read_count):
                pkt = self.inbound_packets.pop(0)
                buffer[index:index+len(pkt)] = pkt
                index += len(pkt)
        except IndexError:
            pass

        return index

    def send(self, data):
        self.outbound_packets.append(data)
