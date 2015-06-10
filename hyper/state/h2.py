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


class StreamState(Enum):
    IDLE = 0
    CONTINUATION = 1
    RESERVED_REMOTE = 2
    RESERVED_LOCAL = 3
    RESERVED_REMOTE_CONT = 4
    RESERVED_LOCAL_CONT = 5
    OPEN = 6
    HALF_CLOSED_REMOTE = 7
    HALF_CLOSED_LOCAL = 8
    CLOSED = 9


class H2Stream(object):
    """
    A single HTTP/2 stream state machine.

    This stream object implements basically the state machine described in
    RFC 7540 section 5.1, with some extensions. The state machine as described
    in that RFC does not include state transitions associated with CONTINUATION
    frames. To formally handle those frames in the state machine process, we
    extend the number of states to include continuation sent/received states.
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
    # Note that we add two extra states after reserved local/remote and one
    # extra state after idle, accounting for the fact that continuation frames
    # exist. The transitions from those states occur on the receipt of either
    # END_HEADERS (transition to open or half-closed, depending on source) or
    # RST_STREAM (transition immediately to closed). This adds substantial
    # complexity, but c'est la vie.
    pass
