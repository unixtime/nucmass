Plotting API
============

The plotting module provides functions for creating publication-quality
visualizations of nuclear data.

Nuclear Chart
-------------

.. autofunction:: nucmass.plot_chart

Isotope/Isotone Chains
----------------------

.. autofunction:: nucmass.plot_isotope_chain

.. autofunction:: nucmass.plot_separation_energies

Comparison Plots
----------------

.. autofunction:: nucmass.plot_mass_residuals

.. autofunction:: nucmass.plot_binding_energy_curve

Examples
--------

Nuclear chart colored by deformation:

.. code-block:: python

    from nucmass import NuclearDatabase, plot_chart

    with NuclearDatabase() as db:
        fig = plot_chart(db, color_by="beta2", figsize=(12, 10))
        fig.savefig("chart.png", dpi=150)

Two-neutron separation energies for Sn isotopes:

.. code-block:: python

    from nucmass import NuclearDatabase, plot_isotope_chain

    with NuclearDatabase() as db:
        fig = plot_isotope_chain(db, z=50, y="S_2n")
        fig.savefig("sn_s2n.png", dpi=150)

Mass residuals (experiment vs theory):

.. code-block:: python

    from nucmass import NuclearDatabase, plot_mass_residuals

    with NuclearDatabase() as db:
        fig = plot_mass_residuals(db)
        fig.savefig("residuals.png", dpi=150)
