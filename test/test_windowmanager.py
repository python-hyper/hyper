# -*- coding: utf-8 -*-
"""
Tests the hyper window manager.
"""
from hyper.http20.window import BaseFlowControlManager, FlowControlManager
import pytest


class TestBaseFCM(object):
    """
    Tests the base flow control manager.
    """
    def test_base_manager_stores_data(self):
        b = BaseFlowControlManager(65535)
        assert b.initial_window_size == 65535
        assert b.window_size == 65535
        assert b.document_size is None

    def test_base_manager_stores_document_size(self):
        b = BaseFlowControlManager(0, 650)
        assert b.document_size == 650

    def test_base_manager_doesnt_function(self):
        b = BaseFlowControlManager(10, 10)
        with pytest.raises(NotImplementedError):
            b.increase_window_size(10)

    def test_base_manager_private_interface_doesnt_function(self):
        b = BaseFlowControlManager(10, 10)
        with pytest.raises(NotImplementedError):
            b._handle_frame(10)

    def test_base_manager_decrements_window_size(self):
        class TestFCM(BaseFlowControlManager):
            def increase_window_size(self, frame_size):
                return 0

        b = TestFCM(10, 10)
        b._handle_frame(5)
        assert b.initial_window_size == 10
        assert b.window_size == 5
        assert b.document_size == 10

    def test_base_manager_blocked_doesnt_function(self):
        b = BaseFlowControlManager(10, 10)
        with pytest.raises(NotImplementedError):
            b.blocked()

    def test_base_manager_blocked_private_interface_doesnt_function(self):
        b = BaseFlowControlManager(10, 10)
        with pytest.raises(NotImplementedError):
            b._blocked()


class TestFCM(object):
    """
    Test's hyper's build-in Flow-Control Manager.
    """
    def test_fcm_emits_when_window_drops_below_one_quarter(self):
        b = FlowControlManager(65535)

        # Receive a frame slightly smaller than 3/4 of the size of the window.
        assert b._handle_frame(49000) == 0
        assert b.window_size == 65535 - 49000

        # Now push us over to 3/4.
        assert b._handle_frame(1000) == 50000
        assert b.window_size == 65535

    def test_fcm_emits_when_window_drops_below_1k(self):
        b = FlowControlManager(1500)

        # Receive a frame slightly smaller than 500 bytes.
        assert b._handle_frame(499) == 0
        assert b.window_size == 1001

        # Push us over to 1k.
        assert b._handle_frame(2) == 501
        assert b.window_size == 1500

    def test_fcm_emits_difference_when_blocked(self):
        b = FlowControlManager(1500)

        # Move the window size down from the base.
        b.window_size = 1000

        assert b._blocked() == 500
        assert b.window_size == 1500
