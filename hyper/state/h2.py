# -*- coding: utf-8 -*-
"""
hyper/state/h2
~~~~~~~~~~~~~~

An implementation of a HTTP/2 state machine.

The purpose of this is to trial the effectiveness of an explicit
state-machine-based approach to HTTP/2 in Python. Ideally, if this succeeds,
it will be pulled out into its own library and act as the core of a general
Python HTTP/2 implementation that can be plugged into, for example, Twisted.
"""
from enum import Enum


class ProtocolError(Exception):
    """
    An action was attempted in violation of the HTTP/2 protocol.
    """
    pass


class StreamState(Enum):
    IDLE = 0
    RESERVED_REMOTE = 1
    RESERVED_LOCAL = 2
    OPEN = 3
    HALF_CLOSED_REMOTE = 4
    HALF_CLOSED_LOCAL = 5
    CLOSED = 6


class StreamInputs(Enum):
    SEND_HEADERS = 0
    SEND_PUSH_PROMISE = 1
    SEND_END_HEADERS = 2
    SEND_RST_STREAM = 3
    SEND_DATA = 4
    SEND_WINDOW_UPDATE = 5
    SEND_END_STREAM = 6
    RECV_HEADERS = 7
    RECV_PUSH_PROMISE = 8
    RECV_END_HEADERS = 9
    RECV_RST_STREAM = 10
    RECV_DATA = 11
    RECV_WINDOW_UPDATE = 12
    RECV_END_STREAM = 13


class H2Stream(object):
    """
    A single HTTP/2 stream state machine.

    This stream object implements basically the state machine described in
    RFC 7540 section 5.1.

    :param stream_id: The stream ID of this stream. This is stored primarily
        for logging purposes.
    """
    # For the sake of clarity, we reproduce the RFC 7540 state machine here:
    #
    #                          +--------+
    #                  send PP |        | recv PP
    #                 ,--------|  idle  |--------.
    #                /         |        |         \
    #               v          +--------+          v
    #        +----------+          |           +----------+
    #        |          |          | send H /  |          |
    # ,------| reserved |          | recv H    | reserved |------.
    # |      | (local)  |          |           | (remote) |      |
    # |      +----------+          v           +----------+      |
    # |          |             +--------+             |          |
    # |          |     recv ES |        | send ES     |          |
    # |   send H |     ,-------|  open  |-------.     | recv H   |
    # |          |    /        |        |        \    |          |
    # |          v   v         +--------+         v   v          |
    # |      +----------+          |           +----------+      |
    # |      |   half   |          |           |   half   |      |
    # |      |  closed  |          | send R /  |  closed  |      |
    # |      | (remote) |          | recv R    | (local)  |      |
    # |      +----------+          |           +----------+      |
    # |           |                |                 |           |
    # |           | send ES /      |       recv ES / |           |
    # |           | send R /       v        send R / |           |
    # |           | recv R     +--------+   recv R   |           |
    # | send R /  `----------->|        |<-----------'  send R / |
    # | recv R                 | closed |               recv R   |
    # `----------------------->|        |<----------------------'
    #                          +--------+
    #
    #    send:   endpoint sends this frame
    #    recv:   endpoint receives this frame
    #
    #    H:  HEADERS frame (with implied CONTINUATIONs)
    #    PP: PUSH_PROMISE frame (with implied CONTINUATIONs)
    #    ES: END_STREAM flag
    #    R:  RST_STREAM frame
    #
    # For the purposes of this state machine we treat HEADERS and their
    # associated CONTINUATION frames as a single jumbo frame. The protocol
    # allows/requires this by preventing other frames from being interleved in
    # between HEADERS/CONTINUATION frames.
    #
    # The _transitions dictionary contains a mapping of tuples of
    # (state, input) to tuples of (side_effect_function, end_state). This map
    # contains all allowed transitions: anything not in this map is invalid
    # and immediately causes a transition to ``closed``.
    _transitions = {
        # State: idle
        (StreamState.IDLE, StreamInputs.SEND_HEADERS): (None, StreamState.OPEN),
        (StreamState.IDLE, StreamInputs.RECV_HEADERS): (None, StreamState.OPEN),
        (StreamState.IDLE, StreamInputs.SEND_PUSH_PROMISE): (None, StreamState.RESERVED_LOCAL),
        (StreamState.IDLE, StreamInputs.RECV_PUSH_PROMISE): (None, StreamState.RESERVED_REMOTE),

        # State: reserved local
        (StreamState.RESERVED_LOCAL, StreamInputs.SEND_HEADERS): (None, StreamState.HALF_CLOSED_REMOTE),
        (StreamState.RESERVED_LOCAL, StreamInputs.SEND_WINDOW_UPDATE): (None, StreamState.RESERVED_LOCAL),
        (StreamState.RESERVED_LOCAL, StreamInputs.RECV_WINDOW_UPDATE): (None, StreamState.RESERVED_LOCAL),
        (StreamState.RESERVED_LOCAL, StreamInputs.SEND_RST_STREAM): (None, StreamState.CLOSED),
        (StreamState.RESERVED_LOCAL, StreamInputs.RECV_RST_STREAM): (None, StreamState.CLOSED),

        # State: reserved remote
        (StreamState.RESERVED_REMOTE, StreamInputs.RECV_HEADERS): (None, StreamState.HALF_CLOSED_LOCAL),
        (StreamState.RESERVED_REMOTE, StreamInputs.SEND_WINDOW_UPDATE): (None, StreamState.RESERVED_REMOTE),
        (StreamState.RESERVED_REMOTE, StreamInputs.RECV_WINDOW_UPDATE): (None, StreamState.RESERVED_REMOTE),
        (StreamState.RESERVED_REMOTE, StreamInputs.SEND_RST_STREAM): (None, StreamState.CLOSED),
        (StreamState.RESERVED_REMOTE, StreamInputs.RECV_RST_STREAM): (None, StreamState.CLOSED),

        # State: open
        (StreamState.OPEN, StreamInputs.SEND_DATA): (None, StreamState.OPEN),
        (StreamState.OPEN, StreamInputs.RECV_DATA): (None, StreamState.OPEN),
        (StreamState.OPEN, StreamInputs.SEND_END_STREAM): (None, StreamState.HALF_CLOSED_LOCAL),
        (StreamState.OPEN, StreamInputs.RECV_END_STREAM): (None, StreamState.HALF_CLOSED_REMOTE),
        (StreamState.OPEN, StreamInputs.SEND_WINDOW_UPDATE): (None, StreamState.OPEN),
        (StreamState.OPEN, StreamInputs.RECV_WINDOW_UPDATE): (None, StreamState.OPEN),
        (StreamState.OPEN, StreamInputs.SEND_RST_STREAM): (None, StreamState.CLOSED),
        (StreamState.OPEN, StreamInputs.RECV_RST_STREAM): (None, StreamState.CLOSED),

        # State: half-closed remote
        (StreamState.HALF_CLOSED_REMOTE, StreamInputs.SEND_DATA): (None, StreamState.HALF_CLOSED_REMOTE),
        (StreamState.HALF_CLOSED_REMOTE, StreamInputs.SEND_END_STREAM): (None, StreamState.CLOSED),
        (StreamState.HALF_CLOSED_REMOTE, StreamInputs.SEND_WINDOW_UPDATE): (None, StreamState.HALF_CLOSED_REMOTE),
        (StreamState.HALF_CLOSED_REMOTE, StreamInputs.RECV_WINDOW_UPDATE): (None, StreamState.HALF_CLOSED_REMOTE),
        (StreamState.HALF_CLOSED_REMOTE, StreamInputs.SEND_RST_STREAM): (None, StreamState.CLOSED),
        (StreamState.HALF_CLOSED_REMOTE, StreamInputs.RECV_RST_STREAM): (None, StreamState.CLOSED),

        # State: half-closed local
        (StreamState.HALF_CLOSED_LOCAL, StreamInputs.RECV_DATA): (None, StreamState.HALF_CLOSED_LOCAL),
        (StreamState.HALF_CLOSED_LOCAL, StreamInputs.RECV_END_STREAM): (None, StreamState.CLOSED),
        (StreamState.HALF_CLOSED_LOCAL, StreamInputs.SEND_WINDOW_UPDATE): (None, StreamState.HALF_CLOSED_LOCAL),
        (StreamState.HALF_CLOSED_LOCAL, StreamInputs.RECV_WINDOW_UPDATE): (None, StreamState.HALF_CLOSED_LOCAL),
        (StreamState.HALF_CLOSED_LOCAL, StreamInputs.SEND_RST_STREAM): (None, StreamState.CLOSED),
        (StreamState.HALF_CLOSED_LOCAL, StreamInputs.RECV_RST_STREAM): (None, StreamState.CLOSED),
    }

    def __init__(self, stream_id):
        self.state = StreamState.IDLE
        self.stream_id = stream_id

    def process_input(self, input_):
        """
        Process a specific input in the state machine.
        """
        if not isinstance(input_, StreamInputs):
            raise ValueError("Input must be an instance of StreamInputs")

        try:
            func, target_state = self._transitions[(self.state, input_)]
        except KeyError:
            self.state = StreamState.CLOSED
            raise ProtocolError(
                "Invalid input %s in state %s", input_, self.state
            )
        else:
            self.state = target_state
            if func is not None:
                return func()
