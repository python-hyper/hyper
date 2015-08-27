# -*- coding: utf-8 -*-
"""
hpack
~~~~~

HTTP/2 header encoding for Python.
"""

from .hpack_compat import Encoder, Decoder


__all__ = (
    'Encoder',
    'Decoder',
    '__version__',
)


__version__ = '1.0.1'
