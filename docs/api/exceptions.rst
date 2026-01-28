Exceptions
==========

Custom exceptions for nucmass error handling.

Exception Hierarchy
-------------------

All nucmass exceptions inherit from :class:`~nucmass.NucmassError`:

.. code-block:: text

    NucmassError (base)
    ├── NuclideNotFoundError
    ├── InvalidNuclideError
    ├── DatabaseNotInitializedError
    ├── DataFileNotFoundError
    └── ExtractionError

Exception Classes
-----------------

.. autoexception:: nucmass.NucmassError
   :show-inheritance:

.. autoexception:: nucmass.NuclideNotFoundError
   :members:
   :show-inheritance:

.. autoexception:: nucmass.InvalidNuclideError
   :members:
   :show-inheritance:

.. autoexception:: nucmass.DatabaseNotInitializedError
   :show-inheritance:

.. autoexception:: nucmass.DataFileNotFoundError
   :members:
   :show-inheritance:

.. autoexception:: nucmass.ExtractionError
   :show-inheritance:

Usage Example
-------------

.. code-block:: python

    from nucmass import NuclearDatabase, NuclideNotFoundError, InvalidNuclideError

    db = NuclearDatabase()

    try:
        # This will raise InvalidNuclideError (Z too large)
        db.get_nuclide(z=200, n=300)
    except InvalidNuclideError as e:
        print(f"Invalid input: {e}")

    try:
        # This will raise NuclideNotFoundError
        db.get_nuclide(z=26, n=100)  # Valid range but doesn't exist
    except NuclideNotFoundError as e:
        print(f"Not found: {e}")
        if e.suggestions:
            print(f"Did you mean: {e.suggestions}")
