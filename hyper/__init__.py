# -*- coding: utf-8 -*-
"""
hyper
~~~~~~

A module for providing an abstraction layer over the differences between
HTTP/1.1 and HTTP/2.
"""
import logging
import sys as _sys

from .http20.connection import HTTP20Connection
from .http20.response import HTTP20Response, HTTP20Push

__version__ = '0.2.0'

# Throw import errors on Python <2.7 and 3.0-3.2.
if _sys.version_info < (2, 7) or (3, 0) <= _sys.version_info < (3, 3):
    raise ImportError("hyper only supports Python 2.7 and Python 3.3 or higher.")

__all__ = [HTTP20Response, HTTP20Push, HTTP20Connection]

# Set default logging handler.
logging.getLogger(__name__).addHandler(logging.NullHandler())
