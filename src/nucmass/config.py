"""
Configuration management for nucmass.

Settings can be customized via environment variables:
    NUCMASS_DATA_DIR: Directory for data files (default: <package>/../../data)
    NUCMASS_DB_PATH: Path to DuckDB database (default: DATA_DIR/nuclear_masses.duckdb)
    NUCMASS_CACHE_SIZE: Maximum cache entries (default: 2000)
    NUCMASS_DOWNLOAD_TIMEOUT: HTTP timeout in seconds (default: 60)
    NUCMASS_LOG_LEVEL: Logging level (default: INFO)

Example:
    export NUCMASS_DATA_DIR=/data/nuclear
    export NUCMASS_LOG_LEVEL=DEBUG
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

# Base directories
_PACKAGE_DIR = Path(__file__).parent
_DEFAULT_DATA_DIR = _PACKAGE_DIR.parent.parent / "data"


class Config:
    """Configuration settings for nucmass."""

    # Data directory for CSV files and database
    DATA_DIR: Path = Path(os.environ.get("NUCMASS_DATA_DIR", str(_DEFAULT_DATA_DIR)))

    # Database path
    DB_PATH: Path = Path(
        os.environ.get("NUCMASS_DB_PATH", str(DATA_DIR / "nuclear_masses.duckdb"))
    )

    # Cache settings
    CACHE_MAX_SIZE: int = int(os.environ.get("NUCMASS_CACHE_SIZE", "2000"))

    # Network settings
    DOWNLOAD_TIMEOUT: int = int(os.environ.get("NUCMASS_DOWNLOAD_TIMEOUT", "60"))
    REQUEST_DELAY: float = float(os.environ.get("NUCMASS_REQUEST_DELAY", "1.0"))

    # Logging
    LOG_LEVEL: str = os.environ.get("NUCMASS_LOG_LEVEL", "INFO")

    # Physical constants (keV) - used in separation energy calculations
    NEUTRON_MASS_EXCESS: float = 8071.32
    PROTON_MASS_EXCESS: float = 7288.97
    ALPHA_MASS_EXCESS: float = 2424.92

    # Valid ranges for nuclide parameters
    Z_MIN: int = 0
    Z_MAX: int = 140
    N_MIN: int = 0
    N_MAX: int = 250

    @classmethod
    def reload(cls) -> None:
        """Reload configuration from environment variables."""
        cls.DATA_DIR = Path(os.environ.get("NUCMASS_DATA_DIR", str(_DEFAULT_DATA_DIR)))
        cls.DB_PATH = Path(
            os.environ.get("NUCMASS_DB_PATH", str(cls.DATA_DIR / "nuclear_masses.duckdb"))
        )
        cls.CACHE_MAX_SIZE = int(os.environ.get("NUCMASS_CACHE_SIZE", "2000"))
        cls.DOWNLOAD_TIMEOUT = int(os.environ.get("NUCMASS_DOWNLOAD_TIMEOUT", "60"))
        cls.REQUEST_DELAY = float(os.environ.get("NUCMASS_REQUEST_DELAY", "1.0"))
        cls.LOG_LEVEL = os.environ.get("NUCMASS_LOG_LEVEL", "INFO")


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
