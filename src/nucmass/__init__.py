"""
nucmass - Nuclear Mass Data Toolkit for Researchers.

A Python toolkit for accessing and analyzing nuclear mass data from two primary sources:

- **AME2020**: Atomic Mass Evaluation 2020 (experimental masses for 3,558 nuclides)
- **FRDM2012**: Finite Range Droplet Model (theoretical masses for 9,318 nuclides, Z=8-136)

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
"""

from .ame2020 import AME2020Parser, download_ame2020
from .frdm2012 import FRDM2012Extractor
from .database import NuclearDatabase, init_database

__version__ = "1.0.0"
__author__ = "Nuclear Mass Toolkit Contributors"

__all__ = [
    "AME2020Parser",
    "download_ame2020",
    "FRDM2012Extractor",
    "NuclearDatabase",
    "init_database",
]
