.. _api:

Interface
=========

.. module:: hyper

This section of the documentation covers the interface portions of ``hyper``.

Primary HTTP Interface
----------------------

.. autoclass:: hyper.HTTPConnection
   :inherited-members:

HTTP/2
------

.. autoclass:: hyper.HTTP20Connection
   :inherited-members:

.. autoclass:: hyper.HTTP20Response
   :inherited-members:

.. autoclass:: hyper.HTTP20Push
   :inherited-members:

HTTP/1.1
--------

.. autoclass:: hyper.HTTP11Connection
   :inherited-members:

.. autoclass:: hyper.HTTP11Response
   :inherited-members:

Headers
-------

.. autoclass:: hyper.common.headers.HTTPHeaderMap
   :inherited-members:

SSLContext
----------

.. automethod:: hyper.tls.init_context

Requests Transport Adapter
--------------------------

.. autoclass:: hyper.contrib.HTTP20Adapter
   :inherited-members:

Flow Control
------------

.. autoclass:: hyper.http20.window.BaseFlowControlManager
   :inherited-members:

.. autoclass:: hyper.http20.window.FlowControlManager
   :inherited-members:

Exceptions
----------

.. autoclass:: hyper.http20.exceptions.HTTP20Error

.. autoclass:: hyper.http20.exceptions.HPACKEncodingError

.. autoclass:: hyper.http20.exceptions.HPACKDecodingError

.. autoclass:: hyper.http20.exceptions.ConnectionError
