Quick Start Guide
=================

This guide covers the most common use cases for nucmass.

Opening the Database
--------------------

The recommended way is using a context manager:

.. code-block:: python

    from nucmass import NuclearDatabase

    with NuclearDatabase() as db:
        # Your queries here
        fe56 = db.get_nuclide(z=26, n=30)
    # Connection automatically closed

Or manage the connection manually:

.. code-block:: python

    db = NuclearDatabase()
    # ... use db ...
    db.close()

Looking Up Nuclides
-------------------

Get data for a specific nuclide by proton (Z) and neutron (N) numbers:

.. code-block:: python

    with NuclearDatabase() as db:
        # Iron-56 (Z=26, N=30)
        fe56 = db.get_nuclide(z=26, n=30)

        print(f"Element: {fe56['Element']}")
        print(f"Mass excess (exp): {fe56['mass_excess_exp_keV']:.0f} keV")
        print(f"Mass excess (th): {fe56['mass_excess_th_keV']:.0f} keV")
        print(f"Deformation β₂: {fe56['beta2']:.3f}")

For nuclides that might not exist, use ``get_nuclide_or_none``:

.. code-block:: python

    result = db.get_nuclide_or_none(z=26, n=999)
    if result is None:
        print("Nuclide not found")

Getting Groups of Nuclides
--------------------------

**Isotopes** (same Z, varying N):

.. code-block:: python

    # All uranium isotopes
    uranium = db.get_isotopes(z=92)
    print(f"Found {len(uranium)} U isotopes")

**Isotones** (same N, varying Z):

.. code-block:: python

    # All N=126 isotones (shell closure)
    n126 = db.get_isotones(n=126)
    print(f"Found {len(n126)} N=126 isotones")

**Isobars** (same A, varying Z):

.. code-block:: python

    # All A=56 isobars
    a56 = db.get_isobars(a=56)
    print(f"Found {len(a56)} A=56 isobars")

Physical Calculations
---------------------

**Separation Energies**

.. code-block:: python

    with NuclearDatabase() as db:
        # One-neutron separation energy S_n
        s_n = db.get_separation_energy_n(z=82, n=126)
        print(f"Pb-208 S_n = {s_n:.2f} MeV")

        # Two-neutron separation energy S_2n
        s_2n = db.get_separation_energy_2n(z=82, n=126)
        print(f"Pb-208 S_2n = {s_2n:.2f} MeV")

        # Proton separation energies
        s_p = db.get_separation_energy_p(z=82, n=126)
        s_2p = db.get_separation_energy_2p(z=82, n=126)

        # Alpha separation energy
        s_alpha = db.get_separation_energy_alpha(z=92, n=146)

**Q-Values**

.. code-block:: python

    # Q-value for neutron capture: Fe-56(n,γ)Fe-57
    q = db.get_q_value(
        z_initial=26, n_initial=30,
        z_final=26, n_final=31,
        z_ejectile=0, n_ejectile=0  # gamma
    )
    print(f"Q = {q:.2f} MeV")

**Mass Excess and Binding Energy**

.. code-block:: python

    # Get mass excess (prefers experimental, falls back to theoretical)
    m = db.get_mass_excess(z=26, n=30)

    # Get total binding energy
    b = db.get_binding_energy(z=26, n=30)
    print(f"Fe-56 total B.E. = {b:.2f} MeV")

Finding Special Nuclides
------------------------

**Deformed nuclei**:

.. code-block:: python

    # Get all nuclides with |β₂| > 0.3
    deformed = db.get_deformed(min_beta2=0.3)
    print(f"{len(deformed)} strongly deformed nuclides")

**Theoretical predictions only**:

.. code-block:: python

    # Nuclides with no experimental data
    predictions = db.get_predicted_only()
    superheavy = predictions[predictions["Z"] > 110]
    print(f"{len(superheavy)} superheavy predictions")

Plotting
--------

.. code-block:: python

    from nucmass import NuclearDatabase, plot_chart, plot_isotope_chain

    with NuclearDatabase() as db:
        # Nuclear chart colored by deformation
        fig = plot_chart(db, color_by="beta2")
        fig.savefig("nuclear_chart.png", dpi=150)

        # Sn isotope chain with S_2n
        fig = plot_isotope_chain(db, z=50, y="S_2n")
        fig.savefig("sn_chain.png", dpi=150)

See :doc:`api/plotting` for more plotting options.

Decay Data (NUBASE2020)
-----------------------

For nuclear decay properties, use the ``NUBASEParser``:

.. code-block:: python

    from nucmass import NUBASEParser

    # Parse NUBASE2020 data
    parser = NUBASEParser("data/nubase_4.mas20.txt")

    # Get decay properties for a nuclide
    co60 = parser.get_nuclide(z=27, n=33)  # Cobalt-60
    print(f"Half-life: {co60['half_life_str']}")
    print(f"Half-life (s): {co60['half_life_sec']:.2e}")
    print(f"Decay modes: {co60['decay_modes']}")
    print(f"Spin/parity: {co60['spin_parity']}")

**Finding stable nuclides**:

.. code-block:: python

    stable = parser.get_stable()
    print(f"Found {len(stable)} stable nuclides")

**Finding nuclides by decay mode**:

.. code-block:: python

    # Alpha emitters (mode "A=" in NUBASE format)
    alpha = parser.get_by_decay_mode("A=")
    print(f"Found {len(alpha)} alpha emitters")

    # Beta-minus emitters
    beta_minus = parser.get_by_decay_mode("B-")
    print(f"Found {len(beta_minus)} β⁻ emitters")

**Finding nuclides by half-life**:

.. code-block:: python

    # Very short-lived (< 1 second)
    short = parser.get_by_half_life(max_seconds=1.0)

    # Long-lived (> 1 million years)
    long_lived = parser.get_by_half_life(min_seconds=3.15e13)

**Getting isomeric states**:

.. code-block:: python

    # All isomers of an element
    ta_isomers = parser.get_isomers(z=73)  # Tantalum isomers
    for iso in ta_isomers:
        print(f"Ta-{iso['A']}{iso['isomer_flag']}: {iso['half_life_str']}")

Custom SQL Queries
------------------

For advanced analysis, use raw SQL:

.. code-block:: python

    with NuclearDatabase() as db:
        # Find the 10 most deformed nuclides
        df = db.query(\"\"\"
            SELECT Z, N, A, Element, beta2
            FROM nuclides
            WHERE beta2 IS NOT NULL
            ORDER BY ABS(beta2) DESC
            LIMIT 10
        \"\"\")
        print(df)
