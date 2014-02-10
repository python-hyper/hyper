# -*- coding: utf-8 -*-
"""
hyper
~~~~~~

A module for providing an abstraction layer over the differences between
HTTP/1.1 and HTTP/2.0.
"""
__version__ = '0.0.1'

from .http20.connection import HTTP20Connection
from .http20.response import HTTP20Response

# Throw import errors on Python 2.
import sys as _sys
if _sys.version_info[0] < 3 or _sys.version_info[1] < 3:
    raise ImportError("hyper only supports Python 3.3 or higher.")

__all__ = [HTTP20Response, HTTP20Connection]
