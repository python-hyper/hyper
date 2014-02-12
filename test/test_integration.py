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
from hyper.http20.frame import Frame, SettingsFrame
from server import SocketLevelTest

# Turn off certificate verification for the tests.
hyper.http20.tls._context = hyper.http20.tls._init_context()
hyper.http20.tls._context.verify_mode = ssl.CERT_NONE

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

            send_event.set()
            sock.close()

        self._start_server(socket_handler)
        conn = HTTP20Connection(self.host, self.port)
        conn.connect()
        send_event.wait()

        # Get the second chunk of data and decode it into a frame.
        data = data[1]
        f, length = Frame.parse_frame_header(data[:8])
        f.parse_body(data[8:])

        assert isinstance(f, SettingsFrame)
        assert f.stream_id == 0
        assert f.settings == {SettingsFrame.ENABLE_PUSH: 0}

        self.tear_down()
