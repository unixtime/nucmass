Database API
============

The :class:`~nucmass.NuclearDatabase` class is the main interface for querying
nuclear mass data.

NuclearDatabase
---------------

.. autoclass:: nucmass.NuclearDatabase
   :members:
   :special-members: __enter__, __exit__
   :show-inheritance:

Database Initialization
-----------------------

.. autofunction:: nucmass.init_database

.. autofunction:: nucmass.database.get_connection

Validation Constants
--------------------

The following constants define valid ranges for nuclear parameters:

.. code-block:: python

    Z_MIN, Z_MAX = 0, 140    # Proton number range
    N_MIN, N_MAX = 0, 250    # Neutron number range
