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

init
~~~~

Initialize or rebuild the nuclear mass database:

.. code-block:: bash

    # Initialize database (if not exists)
    nucmass init

    # Force rebuild from source files
    nucmass init --rebuild

    # Custom database path
    nucmass init --db-path /path/to/custom.duckdb

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

    # With explicit ejectile (U-238 alpha decay)
    nucmass qvalue 92 146 90 144 --ejectile-z 2 --ejectile-n 2

summary
~~~~~~~

Display database summary:

.. code-block:: bash

    nucmass summary

export
~~~~~~

Export data to file:

.. code-block:: bash

    # Export all data to CSV
    nucmass export -o masses.csv

    # Export experimental-only nuclides
    nucmass export -o experimental.csv --experimental-only

    # Export predicted-only nuclides (FRDM2012 without AME2020 data)
    nucmass export -o predicted.csv --theoretical-only

    # Export as JSON or Parquet
    nucmass export -o masses.json --format json
    nucmass export -o masses.parquet --format parquet

batch
~~~~~

Query multiple nuclides from an input file:

.. code-block:: bash

    # Input file format (Z N pairs, comments with #):
    # nuclides.txt:
    # # Iron and Lead
    # 26 30
    # 82 126

    # Basic batch query
    nucmass batch nuclides.txt

    # Save results to file
    nucmass batch nuclides.txt -o results.csv

    # Include separation energies
    nucmass batch nuclides.txt --sep-energies

    # Output as JSON
    nucmass batch nuclides.txt --format json -o results.json

    # Comma-separated input also works
    # nuclides.txt:
    # 26,30
    # 82,126

Examples
--------

.. code-block:: bash

    # Quick lookup of Pb-208 (doubly magic)
    $ nucmass lookup 82 126
    Pb-208 (Z=82, N=126, A=208)
    ========================================
    Mass Excess:
      Experimental: -21748.6 keV
      Theoretical:  -21597.0 keV
    Deformation:
      β₂ = 0.000  (spherical)
    ...

    # Check separation energies at shell closure
    $ nucmass separation 50 82
    Separation energies for Sn-132 (Z=50, N=82)
    =============================================
      S_n  (one neutron):   7.420 MeV
      S_2n (two neutrons):  14.670 MeV
      ...
    Interpretation:
      ★ N=82 is a magic number (neutron shell closure)
      ★ Z=50 is a magic number (proton shell closure)

    # Get JSON output for scripting
    $ nucmass lookup 26 30 --json | jq '.mass_excess_exp_keV'
    -60607.4

    # Batch process multiple nuclides
    $ echo -e "26 30\n82 126\n92 146" > nuclides.txt
    $ nucmass batch nuclides.txt --sep-energies -o results.csv
    Processed 3 nuclides
    Results saved to results.csv

    # Initialize/rebuild database after data updates
    $ nucmass init --rebuild
    Removing existing database...
    Loading AME2020...
    Loading FRDM2012...
    Loading NUBASE2020...
    Database initialized successfully!
