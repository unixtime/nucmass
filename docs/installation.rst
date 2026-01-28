Installation
============

Requirements
------------

- Python 3.12 or later
- pandas >= 2.0
- duckdb >= 1.4.4
- matplotlib >= 3.8
- seaborn >= 0.13
- click >= 8.0
- tqdm >= 4.60
- requests >= 2.31
- pdfplumber >= 0.10 (for FRDM2012 extraction)

Installation from Source
------------------------

Clone the repository and install with uv (recommended):

.. code-block:: bash

    git clone https://github.com/unixtime/nucmass.git
    cd nucmass
    uv pip install -e .

Or using pip:

.. code-block:: bash

    git clone https://github.com/unixtime/nucmass.git
    cd nucmass
    pip install -e .

Optional Dependencies
---------------------

For development:

.. code-block:: bash

    uv pip install -e ".[dev]"

For Jupyter notebooks:

.. code-block:: bash

    uv pip install -e ".[notebook]"

For documentation building:

.. code-block:: bash

    uv pip install -e ".[docs]"

Data Setup
----------

On first use, nucmass will initialize the database from CSV data files.
These files should be present in the ``data/`` directory:

- ``ame2020_masses.csv`` - AME2020 experimental masses
- ``frdm2012_masses.csv`` - FRDM2012 theoretical masses

If the CSV files don't exist, run the download script:

.. code-block:: bash

    python scripts/download_nuclear_data.py

Verify Installation
-------------------

Test that everything works:

.. code-block:: python

    from nucmass import NuclearDatabase

    db = NuclearDatabase()
    summary = db.summary()
    print(f"AME2020: {summary['ame2020_count']} nuclides")
    print(f"FRDM2012: {summary['frdm2012_count']} nuclides")
    db.close()
