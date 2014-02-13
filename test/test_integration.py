# -*- coding: utf-8 -*-
"""
test/integration
~~~~~~~~~~~~~~~~

This file defines integration-type tests for hyper. These are still not fully
hitting the network, so that's alright.
"""
import ssl
import threading
import hyper
from hyper import HTTP20Connection
from hyper.http20.frame import (
    Frame, SettingsFrame, WindowUpdateFrame, DataFrame
)
from server import SocketLevelTest

# Turn off certificate verification for the tests.
hyper.http20.tls._context = hyper.http20.tls._init_context()
hyper.http20.tls._context.verify_mode = ssl.CERT_NONE

def decode_frame(frame_data):
    f, length = Frame.parse_frame_header(frame_data[:8])
    f.parse_body(frame_data[8:8 + length])
    assert 8 + length == len(frame_data)
    return f

class TestHyperIntegration(SocketLevelTest):
    def test_connection_string(self):
        self.set_up()

        # Confirm that we send the connection upgrade string and the initial
        # SettingsFrame.
        data = []
        send_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            # We should get two packets: one connection header string, one
            # SettingsFrame.
            first = sock.recv(65535)
            second = sock.recv(65535)
            data.append(first)
            data.append(second)

            # We need to send back a SettingsFrame.
            f = SettingsFrame(0)
            sock.send(f.serialize())

            send_event.set()
            sock.close()

        self._start_server(socket_handler)
        conn = HTTP20Connection(self.host, self.port)
        conn.connect()
        send_event.wait()

        assert data[0] == b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n'

        self.tear_down()

    def test_initial_settings(self):
        self.set_up()

        # Confirm that we send the connection upgrade string and the initial
        # SettingsFrame.
        data = []
        send_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            # We should get two packets: one connection header string, one
            # SettingsFrame.
            first = sock.recv(65535)
            second = sock.recv(65535)
            data.append(first)
            data.append(second)

            # We need to send back a SettingsFrame.
            f = SettingsFrame(0)
            sock.send(f.serialize())

            send_event.set()
            sock.close()

        self._start_server(socket_handler)
        conn = HTTP20Connection(self.host, self.port)
        conn.connect()
        send_event.wait()

        # Get the second chunk of data and decode it into a frame.
        data = data[1]
        f = decode_frame(data)

        assert isinstance(f, SettingsFrame)
        assert f.stream_id == 0
        assert f.settings == {SettingsFrame.ENABLE_PUSH: 0}

        self.tear_down()

    def test_stream_level_window_management(self):
        self.set_up()
        data = []
        send_event = threading.Event()

        def socket_handler(listener):
            sock = listener.accept()[0]

            # Dispose of the first two packets.
            sock.recv(65535)
            sock.recv(65535)

            # Send a Settings frame that reduces the flow-control window to
            # 64 bytes.
            f = SettingsFrame(0)
            f.settings[SettingsFrame.INITIAL_WINDOW_SIZE] = 64
            sock.send(f.serialize())

            # Grab three frames, the settings ACK, the initial headers frame,
            # and the first data frame.
            for x in range(0, 3):
                data.append(sock.recv(65535))

            # Send a WindowUpdate giving more window room to the stream.
            f = WindowUpdateFrame(1)
            f.window_increment = 64
            sock.send(f.serialize())

            # Reeive the remaining frame.
            data.append(sock.recv(65535))
            send_event.set()

            # We're done.
            sock.close()

        self._start_server(socket_handler)
        conn = HTTP20Connection(self.host, self.port)

        conn.putrequest('GET', '/')
        conn.endheaders()

        # Send the first data chunk. This is 32 bytes.
        sd = b'a' * 32
        conn.send(sd)

        # Send the second one. This should block until the WindowUpdate comes
        # in.
        sd = sd * 2
        conn.send(sd, final=True)
        assert send_event.wait(0.3)

        # Decode the frames.
        print(data)
        frames = [decode_frame(d) for d in data]

        # We care about the last two. The first should be a data frame
        # containing 32 bytes.
        assert isinstance(frames[-2], DataFrame)
        assert len(frames[-2].data) == 32

        # The second should be a data frame containing 64 bytes.
        assert isinstance(frames[-1], DataFrame)
        assert len(frames[-1].data) == 64

        self.tear_down()
