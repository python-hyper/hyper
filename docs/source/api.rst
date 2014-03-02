.. _api:

Interface
=========

.. module:: hyper

This section of the documentation covers the interface portions of ``hyper``.

Primary HTTP/2.0 Interface
--------------------------

.. autoclass:: hyper.HTTP20Connection
   :inherited-members:

.. autoclass:: hyper.HTTP20Response
   :inherited-members:

Requests Transport Adapter
--------------------------

.. autoclass:: hyper.contrib.HTTP20Adapter
   :inherited-members:

Exceptions
----------

.. autoclass:: hyper.http20.exceptions.HTTP20Error
   :inherited-members:

.. autoclass:: hyper.http20.exceptions.HPACKDecodingError
   :inherited-members:
