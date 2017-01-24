# -*- coding: utf-8 -*-
"""
test_http20.py
~~~~~~~~~~~~~~

Unit tests for hyper's HTTP/2.0 implementation.
"""
import pytest
from mock import patch

from server import SocketLevelTest


class TestHTTP20Connection(SocketLevelTest):
    h2 = True

    def test_useful_error_with_no_protocol(self):
        self.set_up()

        def socket_handler(listener):
            sock = listener.accept()[0]
            sock.close()

        self._start_server(socket_handler)
        conn = self.get_connection()

        with patch('hyper.http20.connection.wrap_socket') as mock:
            mock.return_value = (None, None)
            with pytest.raises(AssertionError) as exc_info:
                conn.connect()
        assert (
            "No suitable protocol found."
            in
            str(exc_info)
        )
        assert (
            "Check your OpenSSL version."
            in
            str(exc_info)
        )

        self.tear_down()
