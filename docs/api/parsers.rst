Data Parsers
============

Parsers for the various nuclear data formats.

AME2020 Parser
--------------

.. autoclass:: nucmass.AME2020Parser
   :members:
   :show-inheritance:

.. autofunction:: nucmass.download_ame2020

FRDM2012 Extractor
------------------

.. autoclass:: nucmass.FRDM2012Extractor
   :members:
   :show-inheritance:

NUBASE Parser
-------------

The ``NUBASEParser`` class parses nuclear properties from NUBASE evaluation data files
(supports 2012, 2016, and 2020 formats). It provides access to half-lives, decay modes,
spin/parity, and isomeric states for 5,843+ nuclides.

.. autoclass:: nucmass.NUBASEParser
   :members:
   :show-inheritance:

.. note::
   ``NUBASE2020Parser`` is provided as an alias for backwards compatibility.

.. autofunction:: nucmass.download_nubase2020

Half-Life Parsing
~~~~~~~~~~~~~~~~~

The ``parse_half_life`` function converts half-life strings with various units
to seconds. Supported units include: ys, zs, as, fs, ps, ns, μs (or us), ms, s,
m, h, d, y, ky, My, Gy, Ty, Py, Ey, Zy, Yy.

.. autofunction:: nucmass.nubase2020.parse_half_life

Usage Example
~~~~~~~~~~~~~

.. code-block:: python

    from nucmass import NUBASEParser

    # Parse NUBASE2020 data file
    parser = NUBASEParser("data/nubase_4.mas20.txt")

    # Get a specific nuclide
    fe56 = parser.get_nuclide(z=26, n=30)
    print(f"Fe-56 is stable: {fe56['is_stable']}")
    print(f"Spin/parity: {fe56['spin_parity']}")

    # Get all stable nuclides
    stable = parser.get_stable()
    print(f"Found {len(stable)} stable nuclides")

    # Get alpha emitters
    alpha = parser.get_by_decay_mode("A=")
    print(f"Found {len(alpha)} alpha emitters")

    # Get short-lived nuclides (< 1 second)
    short = parser.get_by_half_life(max_seconds=1.0)
    print(f"Found {len(short)} nuclides with T½ < 1s")
