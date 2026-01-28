Command-Line Interface
======================

nucmass provides a command-line interface for quick lookups and data exports.

Basic Usage
-----------

After installation, the ``nucmass`` command is available:

.. code-block:: bash

    nucmass --help

Commands
--------

lookup
~~~~~~

Look up a specific nuclide by Z and N:

.. code-block:: bash

    # Look up Fe-56
    nucmass lookup 26 30

    # Output as JSON
    nucmass lookup 26 30 --json

isotopes
~~~~~~~~

List isotopes of an element:

.. code-block:: bash

    # List tin isotopes
    nucmass isotopes 50

    # Limit output
    nucmass isotopes 50 -n 10

isotones
~~~~~~~~

List isotones (nuclides with same N):

.. code-block:: bash

    # List N=82 isotones (magic number)
    nucmass isotones 82

separation
~~~~~~~~~~

Calculate and display separation energies:

.. code-block:: bash

    # Pb-208 separation energies
    nucmass separation 82 126

qvalue
~~~~~~

Calculate Q-value for a nuclear reaction:

.. code-block:: bash

    # Q-value for Fe-56(n,gamma)Fe-57
    nucmass qvalue 26 30 26 31

    # With explicit ejectile (alpha decay)
    nucmass qvalue 92 146 90 144 --ejectile 2 2

summary
~~~~~~~

Display database summary:

.. code-block:: bash

    nucmass summary

export
~~~~~~

Export data to CSV:

.. code-block:: bash

    # Export all data
    nucmass export output.csv

    # Export specific element
    nucmass export uranium.csv --element 92

    # Export with filters
    nucmass export deformed.csv --min-beta2 0.3

Examples
--------

.. code-block:: bash

    # Quick lookup of Pb-208 (doubly magic)
    $ nucmass lookup 82 126
    Nuclide: Pb-208 (Z=82, N=126)
    ────────────────────────────────
    Mass Excess (exp): -21748.6 keV
    Mass Excess (th):  -21597.0 keV
    ...

    # Check separation energies at shell closure
    $ nucmass separation 50 82
    Nuclide: Sn-132 (Z=50, N=82)
    ────────────────────────────────
    S_n  =  7.42 MeV
    S_2n = 14.67 MeV
    ...
    Note: N=82 is a magic number

    # Get JSON output for scripting
    $ nucmass lookup 26 30 --json | jq '.mass_excess_exp_keV'
    -60607.4
