# -*- coding: utf-8 -*-
"""
hyper/http20/bufsocket.py
~~~~~~~~~~~~~~~~~~~~~~~~~

This file implements a buffered socket wrapper.

The purpose of this is to avoid the overhead of unnecessary syscalls while
allowing small reads from the network. This represents a potentially massive
performance optimisation at the cost of burning some memory in the userspace
process.
"""
import select

class BufferedSocket(object):
    """
    A buffered socket wrapper.

    The purpose of this is to avoid the overhead of unnecessary syscalls while
    allowing small reads from the network. This represents a potentially
    massive performance optimisation at the cost of burning some memory in the
    userspace process.
    """
    def __init__(self, sck, buffer_size=1000):
        """
        Create the buffered socket.

        :param sck: The socket to wrap.
        :param buffer_size: The size of the backing buffer in bytes. This
            parameter should be set to an appropriate value for your use case.
            Small values of ``buffer_size`` increase the overhead of buffer
            management: large values cause more memory to be used.
        """
        # The wrapped socket.
        self._sck = sck

        # The buffer we're using.
        self._backing_buffer = bytearray(buffer_size)
        self._buffer_view = memoryview(self._backing_buffer)

        # The size of the buffer.
        self._buffer_size = buffer_size

        # The start index in the memory view.
        self._index = 0

        # The number of bytes in the buffer.
        self._bytes_in_buffer = 0

    @property
    def _remaining_capacity(self):
        """
        The maximum number of bytes the buffer could still contain.
        """
        return self._buffer_size - self._index

    @property
    def _buffer_end(self):
        """
        The index of the first free byte in the buffer.
        """
        return self._index + self._bytes_in_buffer

    def recv(self, amt):
        """
        Read some data from the socket.

        :param amt: The amount of data to read.
        :returns: A ``memoryview`` object containing the appropriate number of
            bytes. The data *must* be copied out by the caller before the next
            call to this function.
        """
        def read_all_from_buffer():
            end = self._index + self._bytes_in_buffer
            return self._buffer_view[self._index:end]

        # In this implementation you can never read more than the number of
        # bytes in the buffer.
        if amt > self._buffer_size:
            amt = self._buffer_size

        # If the amount of data we've been asked to read is less than the
        # remaining space in the buffer, we need to clear out the buffer and
        # start over. Copy the data into the new array.
        if amt > self._remaining_capacity:
            new_buffer = bytearray(self._buffer_size)
            new_buffer_view = memoryview(new_buffer)
            new_buffer_view[0:self._bytes_in_buffer] = read_all_from_buffer()

            self._index = 0
            self._backing_buffer = new_buffer
            self._buffer_view = new_buffer_view

        # If there's still some room in the buffer, opportunistically attempt
        # to read into it.
        # If we don't actually _need_ the data (i.e. there's enough in the
        # buffer to satisfy the request), use select to work out if the read
        # attempt will block. If it will, don't bother reading. If we need the
        # data, always do the read.
        if self._bytes_in_buffer >= amt:
            should_read = select.select([self._sck], [], [], 0)[0]
        else:
            should_read = True

        if ((self._remaining_capacity > self._bytes_in_buffer) and
            (should_read)):
            count = self._sck.recv_into(self._buffer_view[self._buffer_end:])
            self._bytes_in_buffer += count

        # Read out the bytes and update the index.
        amt = min(amt, self._bytes_in_buffer)
        data = self._buffer_view[self._index:self._index+amt]

        self._index += amt
        self._bytes_in_buffer -= amt

        return data

    def __getattr__(self, name):
        return getattr(self._sck, name)
