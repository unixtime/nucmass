"""
Configuration management for nucmass.

Settings can be customized via environment variables before importing nucmass.

Environment Variables
---------------------
NUCMASS_DATA_DIR : str
    Directory for data files (default: <package>/../../data).
NUCMASS_DB_PATH : str
    Path to DuckDB database (default: DATA_DIR/nuclear_masses.duckdb).
NUCMASS_CACHE_SIZE : int
    Maximum cache entries (default: 2000).
NUCMASS_DOWNLOAD_TIMEOUT : int
    HTTP timeout in seconds (default: 60).
NUCMASS_LOG_LEVEL : str
    Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO).

Examples
--------
Configure via shell environment::

    export NUCMASS_DATA_DIR=/data/nuclear
    export NUCMASS_LOG_LEVEL=DEBUG
    python -c "from nucmass import NuclearDatabase; db = NuclearDatabase()"

Or configure in Python before importing::

    import os
    os.environ['NUCMASS_DATA_DIR'] = '/custom/data/path'
    from nucmass import NuclearDatabase
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

__all__ = [
    "Config",
    "get_logger",
]

# Base directories
_PACKAGE_DIR = Path(__file__).parent
_DEFAULT_DATA_DIR = _PACKAGE_DIR.parent.parent / "data"


class Config:
    """
    Configuration settings for nucmass.

    All settings can be customized via environment variables. Physical constants
    are based on AME2020 recommended values.

    Attributes:
        DATA_DIR: Directory for data files (CSV, database).
        DB_PATH: Path to the DuckDB database file.
        CACHE_MAX_SIZE: Maximum entries in the LRU cache for mass lookups.
        DOWNLOAD_TIMEOUT: HTTP timeout for downloading data files (seconds).
        REQUEST_DELAY: Minimum delay between HTTP requests to same domain (seconds).
        LOG_LEVEL: Logging verbosity (DEBUG, INFO, WARNING, ERROR).

    Physical Constants (keV):
        NEUTRON_MASS_EXCESS: Neutron mass excess (8071.32 keV, AME2020).
        PROTON_MASS_EXCESS: Proton/Hydrogen mass excess (7288.97 keV, AME2020).
        ALPHA_MASS_EXCESS: Alpha particle mass excess (2424.92 keV, AME2020).
        AMU_TO_KEV: Atomic mass unit in keV/c² (931494.0 keV).

    Nuclear Structure:
        MAGIC_NUMBERS: Proton/neutron numbers for closed shells.
    """

    # Data directory for CSV files and database
    DATA_DIR: Path = Path(os.environ.get("NUCMASS_DATA_DIR", str(_DEFAULT_DATA_DIR)))

    # Database path
    DB_PATH: Path = Path(
        os.environ.get("NUCMASS_DB_PATH", str(DATA_DIR / "nuclear_masses.duckdb"))
    )

    # Cache settings (validated: must be positive)
    _cache_size_env = os.environ.get("NUCMASS_CACHE_SIZE", "2000")
    CACHE_MAX_SIZE: int = max(1, int(_cache_size_env)) if _cache_size_env.isdigit() else 2000

    # Network settings (validated: must be positive)
    _timeout_env = os.environ.get("NUCMASS_DOWNLOAD_TIMEOUT", "60")
    DOWNLOAD_TIMEOUT: int = max(1, int(_timeout_env)) if _timeout_env.isdigit() else 60

    _delay_env = os.environ.get("NUCMASS_REQUEST_DELAY", "1.0")
    try:
        REQUEST_DELAY: float = max(0.0, float(_delay_env))
    except ValueError:
        REQUEST_DELAY: float = 1.0

    # Logging (validated: must be valid level)
    _log_level_env = os.environ.get("NUCMASS_LOG_LEVEL", "INFO").upper()
    LOG_LEVEL: str = _log_level_env if _log_level_env in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL") else "INFO"

    # Physical constants (keV) - AME2020 recommended values
    # Reference: Wang et al., Chinese Physics C 45, 030003 (2021)
    NEUTRON_MASS_EXCESS: float = 8071.32  # keV
    PROTON_MASS_EXCESS: float = 7288.97   # keV (hydrogen atom mass excess)
    ALPHA_MASS_EXCESS: float = 2424.92    # keV (He-4 mass excess)
    AMU_TO_KEV: float = 931494.0          # keV/c² per atomic mass unit
    AMU_TO_MEV: float = 931.494           # MeV/c² per atomic mass unit

    # Magic numbers for nuclear shell closures
    # These are Z or N values where nuclei have extra stability
    MAGIC_NUMBERS: tuple[int, ...] = (2, 8, 20, 28, 50, 82, 126)

    # Valid ranges for nuclide parameters
    Z_MIN: int = 0
    Z_MAX: int = 140
    N_MIN: int = 0
    N_MAX: int = 250

    # Element symbols (Z -> symbol mapping)
    ELEMENT_SYMBOLS: dict[int, str] = {
        0: 'n', 1: 'H', 2: 'He', 3: 'Li', 4: 'Be', 5: 'B', 6: 'C', 7: 'N', 8: 'O',
        9: 'F', 10: 'Ne', 11: 'Na', 12: 'Mg', 13: 'Al', 14: 'Si', 15: 'P', 16: 'S',
        17: 'Cl', 18: 'Ar', 19: 'K', 20: 'Ca', 21: 'Sc', 22: 'Ti', 23: 'V', 24: 'Cr',
        25: 'Mn', 26: 'Fe', 27: 'Co', 28: 'Ni', 29: 'Cu', 30: 'Zn', 31: 'Ga', 32: 'Ge',
        33: 'As', 34: 'Se', 35: 'Br', 36: 'Kr', 37: 'Rb', 38: 'Sr', 39: 'Y', 40: 'Zr',
        41: 'Nb', 42: 'Mo', 43: 'Tc', 44: 'Ru', 45: 'Rh', 46: 'Pd', 47: 'Ag', 48: 'Cd',
        49: 'In', 50: 'Sn', 51: 'Sb', 52: 'Te', 53: 'I', 54: 'Xe', 55: 'Cs', 56: 'Ba',
        57: 'La', 58: 'Ce', 59: 'Pr', 60: 'Nd', 61: 'Pm', 62: 'Sm', 63: 'Eu', 64: 'Gd',
        65: 'Tb', 66: 'Dy', 67: 'Ho', 68: 'Er', 69: 'Tm', 70: 'Yb', 71: 'Lu', 72: 'Hf',
        73: 'Ta', 74: 'W', 75: 'Re', 76: 'Os', 77: 'Ir', 78: 'Pt', 79: 'Au', 80: 'Hg',
        81: 'Tl', 82: 'Pb', 83: 'Bi', 84: 'Po', 85: 'At', 86: 'Rn', 87: 'Fr', 88: 'Ra',
        89: 'Ac', 90: 'Th', 91: 'Pa', 92: 'U', 93: 'Np', 94: 'Pu', 95: 'Am', 96: 'Cm',
        97: 'Bk', 98: 'Cf', 99: 'Es', 100: 'Fm', 101: 'Md', 102: 'No', 103: 'Lr',
        104: 'Rf', 105: 'Db', 106: 'Sg', 107: 'Bh', 108: 'Hs', 109: 'Mt', 110: 'Ds',
        111: 'Rg', 112: 'Cn', 113: 'Nh', 114: 'Fl', 115: 'Mc', 116: 'Lv', 117: 'Ts',
        118: 'Og',
    }

    @classmethod
    def get_element_symbol(cls, z: int) -> str:
        """Get element symbol from atomic number Z."""
        return cls.ELEMENT_SYMBOLS.get(z, f"E{z}")

    @classmethod
    def reload(cls) -> None:
        """
        Reload configuration from environment variables.

        Call this method after changing environment variables to update
        the configuration at runtime. Note that this does not affect
        already-opened database connections.

        Example:
            >>> import os
            >>> os.environ["NUCMASS_LOG_LEVEL"] = "DEBUG"
            >>> Config.reload()
        """
        cls.DATA_DIR = Path(os.environ.get("NUCMASS_DATA_DIR", str(_DEFAULT_DATA_DIR)))
        cls.DB_PATH = Path(
            os.environ.get("NUCMASS_DB_PATH", str(cls.DATA_DIR / "nuclear_masses.duckdb"))
        )
        # Validate cache size
        cache_env = os.environ.get("NUCMASS_CACHE_SIZE", "2000")
        cls.CACHE_MAX_SIZE = max(1, int(cache_env)) if cache_env.isdigit() else 2000

        # Validate timeout
        timeout_env = os.environ.get("NUCMASS_DOWNLOAD_TIMEOUT", "60")
        cls.DOWNLOAD_TIMEOUT = max(1, int(timeout_env)) if timeout_env.isdigit() else 60

        # Validate delay
        try:
            cls.REQUEST_DELAY = max(0.0, float(os.environ.get("NUCMASS_REQUEST_DELAY", "1.0")))
        except ValueError:
            cls.REQUEST_DELAY = 1.0

        # Validate log level
        log_env = os.environ.get("NUCMASS_LOG_LEVEL", "INFO").upper()
        cls.LOG_LEVEL = log_env if log_env in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL") else "INFO"


def setup_logging(level: str | None = None) -> logging.Logger:
    """
    Set up logging for nucmass.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR). If None, uses
            NUCMASS_LOG_LEVEL environment variable or INFO.

    Returns:
        The root nucmass logger.

    Example:
        >>> from nucmass.config import setup_logging
        >>> logger = setup_logging("DEBUG")
    """
    if level is None:
        level = Config.LOG_LEVEL

    # Create logger
    logger = logging.getLogger("nucmass")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Only add handler if none exist (avoid duplicates)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a nucmass submodule.

    Args:
        name: Module name (e.g., "database", "ame2020").

    Returns:
        Logger instance for the module.
    """
    return logging.getLogger(f"nucmass.{name}")
