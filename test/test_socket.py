# -*- coding: utf-8 -*-
"""
test/socket
~~~~~~~~~~~

Test the BufferedSocket implementation in hyper.
"""
import hyper.http20.bufsocket
from hyper.http20.bufsocket import BufferedSocket

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
            hyper.http20.bufsocket.select, 'select', dummy_select
        )
        s = DummySocket()
        b = BufferedSocket(s)

        assert b is not None
        assert b._buffer_size == 1000

    def test_can_send_on_buffered_socket(self, monkeypatch):
        monkeypatch.setattr(
            hyper.http20.bufsocket.select, 'select', dummy_select
        )
        s = DummySocket()
        b = BufferedSocket(s)
        b.send(b'test data')

        assert len(s.outbound_packets) == 1
        assert s.outbound_packets[0] == b'test data'

    def test_receive_single_packet(self, monkeypatch):
        monkeypatch.setattr(
            hyper.http20.bufsocket.select, 'select', dummy_select
        )
        s = DummySocket()
        b = BufferedSocket(s)
        s.inbound_packets.append(b'test data')

        d = b.recv(100).tobytes()
        assert d == b'test data'

    def test_receive_multiple_packets_one_at_a_time(self, monkeypatch):
        monkeypatch.setattr(
            hyper.http20.bufsocket.select, 'select', dummy_select
        )
        s = DummySocket()
        b = BufferedSocket(s)
        s.inbound_packets = [b'Here', b'begins', b'the', b'test', b'data']

        d = b''
        for _ in range(5):
            d += b.recv(100).tobytes()

        assert d == b'Herebeginsthetestdata'

    def test_receive_empty_packet(self, monkeypatch):
        monkeypatch.setattr(
            hyper.http20.bufsocket.select, 'select', dummy_select
        )
        s = DummySocket()
        b = BufferedSocket(s)
        s.inbound_packets = [b'Here', b'begins', b'', b'the', b'', b'test', b'data']

        d = b''
        for _ in range(7):
            d += b.recv(100).tobytes()

        assert d == b'Herebeginsthetestdata'

    def test_receive_multiple_packets_at_once(self, monkeypatch):
        monkeypatch.setattr(
            hyper.http20.bufsocket.select, 'select', dummy_select
        )
        s = DummySocket()
        b = BufferedSocket(s)
        s.inbound_packets = [b'Here', b'begins', b'the', b'test', b'data', b'!']
        s.read_count = 3

        d = b''
        for _ in range(22):
            d += b.recv(1).tobytes()

        assert d == b'Herebeginsthetestdata!'

    def test_filling_the_buffer(self, monkeypatch):
        monkeypatch.setattr(
            hyper.http20.bufsocket.select, 'select', dummy_select
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
            hyper.http20.bufsocket.select, 'select', dummy_select
        )
        s = DummySocket()
        b = BufferedSocket(s)
        s.inbound_packets.append(b'a' * 600)

        d = b.recv(1200).tobytes()
        assert d == b'a' * 600


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
