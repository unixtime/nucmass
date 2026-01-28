nucmass: Nuclear Mass Data Toolkit
==================================

**nucmass** is a Python toolkit for accessing and analyzing nuclear mass and
decay data from three authoritative sources:

- **AME2020**: Atomic Mass Evaluation 2020 (experimental masses for 3,558 nuclides)
- **FRDM2012**: Finite Range Droplet Model (theoretical masses for 9,318 nuclides)
- **NUBASE2020**: Nuclear properties evaluation (half-lives, decay modes for 3,558 nuclides + 2,285 isomers)

Features
--------

- **Unified Database**: Query experimental and theoretical nuclear masses
- **Decay Properties**: Half-lives, decay modes, spin/parity from NUBASE2020
- **Physical Calculations**: Separation energies, Q-values, binding energies
- **Visualization**: Publication-quality nuclear charts and isotope chain plots
- **CLI Interface**: Quick lookups and exports from the command line
- **DuckDB Backend**: Fast SQL-based queries for complex analyses

Quick Start
-----------

.. code-block:: python

    from nucmass import NuclearDatabase

    # Open database (auto-initializes on first use)
    with NuclearDatabase() as db:
        # Look up Iron-56 (most tightly bound nucleus)
        fe56 = db.get_nuclide(z=26, n=30)
        print(f"Fe-56 mass excess: {fe56['mass_excess_exp_keV']:.0f} keV")
        print(f"Deformation β₂: {fe56['beta2']:.3f}")
        print(f"Is stable: {fe56['is_stable']}")

        # Look up U-238 with decay data
        u238 = db.get_nuclide(z=92, n=146)
        print(f"U-238 half-life: {u238['half_life_str']}")
        print(f"U-238 decay modes: {u238['decay_modes']}")

        # Calculate two-neutron separation energy
        s2n = db.get_separation_energy_2n(z=82, n=126)  # Pb-208
        print(f"Pb-208 S₂ₙ = {s2n:.2f} MeV")

Installation
------------

.. code-block:: bash

    # Clone the repository
    git clone https://github.com/unixtime/nucmass.git
    cd nucmass

    # Install with uv (recommended)
    uv pip install -e .

    # Or with pip
    pip install -e .

Data Sources
------------

**AME2020** (Atomic Mass Evaluation 2020)
    Experimental atomic masses for 3,558 nuclides.

    Reference: Wang et al., *Chinese Physics C* 45, 030003 (2021)
    `DOI: 10.1088/1674-1137/abddb0 <https://doi.org/10.1088/1674-1137/abddb0>`_

**FRDM2012** (Finite Range Droplet Model)
    Theoretical masses and deformations for 9,318 nuclides (Z=8-136).

    Reference: Möller et al., *Atomic Data and Nuclear Data Tables* 109-110, 1-204 (2016)
    `DOI: 10.1016/j.adt.2015.10.002 <https://doi.org/10.1016/j.adt.2015.10.002>`_

**NUBASE2020** (Nuclear Properties Evaluation)
    Half-lives, decay modes, spin/parity for 5,656 nuclides and isomers.

    Reference: Kondev et al., *Chinese Physics C* 45, 030001 (2021)
    `DOI: 10.1088/1674-1137/abddae <https://doi.org/10.1088/1674-1137/abddae>`_

    Data available from: `ANL Atomic Mass Data Resources <https://www.anl.gov/phy/atomic-mass-data-resources>`_

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   quickstart
   cli

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/database
   api/plotting
   api/parsers
   api/exceptions

.. toctree::
   :maxdepth: 1
   :caption: Development

   changelog


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
