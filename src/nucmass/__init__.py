"""
nucmass - Nuclear Mass Data Toolkit for Researchers.

A Python toolkit for accessing and analyzing nuclear mass data from three primary sources:

- **AME2020**: Atomic Mass Evaluation 2020 (experimental masses for 3,558 nuclides)
- **FRDM2012**: Finite Range Droplet Model (theoretical masses for 9,318 nuclides, Z=8-136)
- **NUBASE2020**: Nuclear properties evaluation (half-lives, decay modes for 5,843 nuclides)

Quick Start:
    >>> from nucmass import NuclearDatabase
    >>> db = NuclearDatabase()
    >>> fe56 = db.get_nuclide(z=26, n=30)
    >>> print(f"Fe-56 mass excess: {fe56['mass_excess_exp_keV']:.0f} keV")

References:
    AME2020: Wang et al., Chinese Physics C 45, 030003 (2021)
        DOI: 10.1088/1674-1137/abddb0

    FRDM2012: Möller et al., Atomic Data and Nuclear Data Tables 109-110, 1-204 (2016)
        DOI: 10.1016/j.adt.2015.10.002
        arXiv: 1508.06294

    NUBASE2020: Kondev et al., Chinese Physics C 45, 030001 (2021)
        DOI: 10.1088/1674-1137/abddae
"""

from .ame2020 import AME2020Parser, download_ame2020
from .frdm2012 import FRDM2012Extractor
from .nubase2020 import NUBASEParser, NUBASE2020Parser, download_nubase2020
from .database import NuclearDatabase, init_database
from .plotting import (
    plot_chart,
    plot_isotope_chain,
    plot_separation_energies,
    plot_mass_residuals,
    plot_binding_energy_curve,
)
from .exceptions import (
    NucmassError,
    NuclideNotFoundError,
    InvalidNuclideError,
    DatabaseNotInitializedError,
    DataFileNotFoundError,
    ExtractionError,
)

__version__ = "1.1.0"
__author__ = "Nuclear Mass Toolkit Contributors"

__all__ = [
    # Core classes
    "AME2020Parser",
    "download_ame2020",
    "FRDM2012Extractor",
    "NUBASEParser",
    "NUBASE2020Parser",  # Alias for backwards compatibility
    "download_nubase2020",
    "NuclearDatabase",
    "init_database",
    # Plotting
    "plot_chart",
    "plot_isotope_chain",
    "plot_separation_energies",
    "plot_mass_residuals",
    "plot_binding_energy_curve",
    # Exceptions
    "NucmassError",
    "NuclideNotFoundError",
    "InvalidNuclideError",
    "DatabaseNotInitializedError",
    "DataFileNotFoundError",
    "ExtractionError",
]
