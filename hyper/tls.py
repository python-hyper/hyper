# -*- coding: utf-8 -*-
"""
hyper/tls
~~~~~~~~~

Contains the TLS/SSL logic for use in hyper.
"""
import ssl

# We have a singleton SSLContext object. There's no reason to be creating one
# per connection. We're using v23 right now until someone gives me a reason not
# to.
_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
