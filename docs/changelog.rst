Changelog
=========

Version 1.1.0 (2026-01-28)
--------------------------

New Features
~~~~~~~~~~~~

* **Command-Line Interface**: Added ``nucmass`` CLI with commands for quick
  lookups, isotope listings, separation energies, Q-values, and data export.

* **Physical Calculations**: New methods for computing:
  - Separation energies: ``get_separation_energy_n()``, ``get_separation_energy_p()``,
    ``get_separation_energy_2n()``, ``get_separation_energy_2p()``,
    ``get_separation_energy_alpha()``
  - Q-values: ``get_q_value()``
  - Mass excess and binding energy: ``get_mass_excess()``, ``get_binding_energy()``

* **Plotting Utilities**: New module ``nucmass.plotting`` with functions for:
  - Nuclear charts: ``plot_chart()``
  - Isotope chains: ``plot_isotope_chain()``
  - Separation energy plots: ``plot_separation_energies()``
  - Mass residuals: ``plot_mass_residuals()``
  - Binding energy curve: ``plot_binding_energy_curve()``

* **NUBASE Parser**: Added ``NUBASEParser`` for nuclear decay properties including:
  - Half-lives with automatic unit conversion to seconds (20+ time units supported)
  - Spin/parity values
  - Decay modes (α, β⁻, β⁺, EC, IT, SF, etc.)
  - Isomeric states with proper ZZZS encoding (3,558 nuclides + 2,285 isomers)
  - Discovery year
  - Optimized for NUBASE2020 format
  - Methods: ``get_stable()``, ``get_by_decay_mode()``, ``get_by_half_life()``,
    ``get_isomers()``, ``to_dataframe()``

* **Integrated Database**: NUBASE2020 decay data is now integrated into the
  unified DuckDB database:
  - New columns in ``nuclides`` view: ``half_life_str``, ``half_life_sec``,
    ``is_stable``, ``spin_parity``, ``decay_modes``, ``discovery_year``,
    ``has_decay_data``
  - Database summary now includes ``nubase2020_count`` and ``with_decay_data``
  - Automatic loading of NUBASE data during database initialization

* **Context Manager Support**: ``NuclearDatabase`` now supports the context
  manager protocol for automatic connection cleanup.

* **Progress Bars**: Added tqdm progress bars for long-running PDF extraction
  operations.

Improvements
~~~~~~~~~~~~

* **Input Validation**: Added validation for Z, N, A parameters with helpful
  error messages and suggestions.

* **Custom Exceptions**: New exception hierarchy for better error handling:
  ``NuclideNotFoundError``, ``InvalidNuclideError``, ``DataFileNotFoundError``.

* **Query Caching**: Added LRU caching for frequently accessed nuclides.

* **Better Error Messages**: ``NuclideNotFoundError`` now includes suggestions
  for nearby valid nuclides.

* **Jupyter Notebook**: Updated ``explore_nuclear_data.ipynb`` with new sections
  for decay data exploration, half-life distributions, and stability charts.

Documentation
~~~~~~~~~~~~~

* **Sphinx Documentation**: Complete documentation infrastructure with:
  - Installation guide
  - Quick start guide with examples
  - CLI reference
  - API documentation for all modules
  - Changelog

* **README**: Comprehensive README with examples for all three data sources
  (AME2020, FRDM2012, NUBASE2020).

Version 1.0.0 (2026-01-27)
--------------------------

Initial release with core functionality:

* **AME2020 Parser**: Parse experimental atomic masses from the Atomic Mass
  Evaluation 2020 data files.

* **FRDM2012 Extractor**: Extract theoretical masses and deformation parameters
  from FRDM2012 PDF tables.

* **DuckDB Database**: Unified database combining experimental and theoretical
  data with fast SQL queries.

* **NuclearDatabase API**: High-level Python interface for common queries:
  - ``get_nuclide()``: Look up individual nuclides
  - ``get_isotopes()``: Get all isotopes of an element
  - ``get_isotones()``: Get all nuclides with same N
  - ``get_isobars()``: Get all nuclides with same A
  - ``get_deformed()``: Filter by deformation
  - ``get_predicted_only()``: Get nuclides without experimental data
