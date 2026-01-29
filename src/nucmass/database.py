"""
DuckDB Database Interface for Nuclear Mass Data.

This module provides a user-friendly interface to query nuclear mass data
stored in a DuckDB database. It combines experimental data (AME2020),
theoretical predictions (FRDM2012), and decay properties (NUBASE2020)
into a unified queryable format.

The database is designed for researchers who may not be SQL experts.
Simple Python methods are provided for common queries.

Example:
    >>> from nucmass import NuclearDatabase
    >>> db = NuclearDatabase()
    >>>
    >>> # Look up a specific nuclide
    >>> fe56 = db.get_nuclide(z=26, n=30)
    >>> print(f"Iron-56 mass excess: {fe56['mass_excess_exp_keV']:.0f} keV")
    >>>
    >>> # Get all isotopes of an element
    >>> uranium = db.get_isotopes(z=92)
    >>> print(f"Found {len(uranium)} uranium isotopes")

References:
    AME2020: Wang et al., Chinese Physics C 45, 030003 (2021)
    FRDM2012: Möller et al., ADNDT 109-110, 1-204 (2016)
    NUBASE2020: Kondev et al., Chinese Physics C 45, 030001 (2021)
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import duckdb
import pandas as pd

from .config import Config, get_logger
from .exceptions import (
    InvalidNuclideError,
    NuclideNotFoundError,
    DataFileNotFoundError,
    DatabaseCorruptError,
)

if TYPE_CHECKING:
    from typing import Optional

# Module logger
logger = get_logger("database")

# Use config for paths (kept for backward compatibility)
DATA_DIR = Config.DATA_DIR
DB_PATH = Config.DB_PATH

# Physical constants (from Config for consistency)
AMU_TO_MEV = Config.AMU_TO_MEV  # MeV/c² per atomic mass unit

# Valid ranges for nuclide parameters (from config)
Z_MIN, Z_MAX = Config.Z_MIN, Config.Z_MAX
N_MIN, N_MAX = Config.N_MIN, Config.N_MAX


def _validate_z(z: int, context: str = "") -> None:
    """Validate proton number Z."""
    if not isinstance(z, (int, type(None))):
        raise InvalidNuclideError(f"Z must be an integer, got {type(z).__name__}")
    if z is not None and (z < Z_MIN or z > Z_MAX):
        raise InvalidNuclideError(
            f"Z={z} is out of valid range [{Z_MIN}, {Z_MAX}]. {context}",
            z=z
        )


def _validate_n(n: int, context: str = "") -> None:
    """Validate neutron number N."""
    if not isinstance(n, (int, type(None))):
        raise InvalidNuclideError(f"N must be an integer, got {type(n).__name__}")
    if n is not None and (n < N_MIN or n > N_MAX):
        raise InvalidNuclideError(
            f"N={n} is out of valid range [{N_MIN}, {N_MAX}]. {context}",
            n=n
        )


def _validate_a(a: int, context: str = "") -> None:
    """Validate mass number A."""
    if not isinstance(a, (int, type(None))):
        raise InvalidNuclideError(f"A must be an integer, got {type(a).__name__}")
    if a is not None and (a < 1 or a > Z_MAX + N_MAX):
        raise InvalidNuclideError(
            f"A={a} is out of valid range [1, {Z_MAX + N_MAX}]. {context}",
        )


def get_connection(db_path: Path | str | None = None) -> duckdb.DuckDBPyConnection:
    """
    Get a connection to the nuclear mass database.

    .. deprecated:: 1.2.0
        Use :class:`NuclearDatabase` context manager instead to ensure
        proper resource cleanup. This function returns an unmanaged connection
        that the caller must close explicitly.

    Args:
        db_path: Path to the DuckDB database file. If None, uses the default
            location (data/nuclear_masses.duckdb).

    Returns:
        A DuckDB connection object that can be used for SQL queries.
        **Important**: The caller is responsible for closing this connection.

    Example:
        >>> # Preferred: use NuclearDatabase context manager
        >>> with NuclearDatabase() as db:
        ...     result = db.query("SELECT COUNT(*) FROM nuclides")
        >>>
        >>> # Legacy: manual connection (ensure you close it!)
        >>> conn = get_connection()
        >>> try:
        ...     result = conn.execute("SELECT COUNT(*) FROM nuclides").fetchone()
        ...     print(f"Total nuclides: {result[0]}")
        ... finally:
        ...     conn.close()
    """
    import warnings
    warnings.warn(
        "get_connection() returns an unmanaged connection. "
        "Use NuclearDatabase context manager instead for automatic cleanup.",
        DeprecationWarning,
        stacklevel=2
    )
    if db_path is None:
        db_path = DB_PATH
    return duckdb.connect(str(db_path))


def init_database(
    db_path: Path | str | None = None,
    show_progress: bool = True
) -> duckdb.DuckDBPyConnection:
    """
    Initialize or rebuild the nuclear mass database from CSV files.

    This function creates a DuckDB database with four components:
    - **ame2020 table**: Experimental atomic masses (3,558 nuclides)
    - **frdm2012 table**: Theoretical masses and deformations (9,318 nuclides)
    - **nubase2020 table**: Decay properties (half-lives, decay modes, 5,843 nuclides)
    - **nuclides view**: Combined view joining all datasets

    Args:
        db_path: Where to save the database. If None, uses the default
            location (data/nuclear_masses.duckdb).
        show_progress: Whether to print progress messages.

    Returns:
        A DuckDB connection to the newly created database.

    Raises:
        DataFileNotFoundError: If CSV files are not found in data/ directory.

    Note:
        This function expects CSV files to exist in the data/ directory.
        Run `python scripts/download_nuclear_data.py` first to generate them.

    Example:
        >>> conn = init_database()
        Loading AME2020 from data/ame2020_masses.csv...
          Loaded 3558 nuclides into ame2020 table
        Loading FRDM2012 from data/frdm2012_masses.csv...
          Loaded 9318 nuclides into frdm2012 table
        Loading NUBASE2020...
          Loaded 5843 entries into nubase2020 table
        Creating combined nuclides view...
          Combined view has 9420 nuclides
    """
    if db_path is None:
        db_path = DB_PATH

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(db_path))

    # Load AME2020 experimental data
    ame_csv = DATA_DIR / "ame2020_masses.csv"
    if not ame_csv.exists():
        raise DataFileNotFoundError(
            str(ame_csv),
            "Run `python scripts/download_nuclear_data.py` to download the data."
        )

    logger.info(f"Loading AME2020 from {ame_csv}...")
    conn.execute("""
        CREATE OR REPLACE TABLE ame2020 AS
        SELECT * FROM read_csv_auto(?)
    """, [str(ame_csv)])
    count = conn.execute("SELECT COUNT(*) FROM ame2020").fetchone()[0]
    logger.info(f"  Loaded {count} nuclides into ame2020 table")

    # Load FRDM2012 theoretical data
    frdm_csv = DATA_DIR / "frdm2012_masses.csv"
    if not frdm_csv.exists():
        raise DataFileNotFoundError(
            str(frdm_csv),
            "Run `python scripts/download_nuclear_data.py` to download the data."
        )

    logger.info(f"Loading FRDM2012 from {frdm_csv}...")
    conn.execute("""
        CREATE OR REPLACE TABLE frdm2012 AS
        SELECT * FROM read_csv_auto(?)
    """, [str(frdm_csv)])
    count = conn.execute("SELECT COUNT(*) FROM frdm2012").fetchone()[0]
    logger.info(f"  Loaded {count} nuclides into frdm2012 table")

    # Load NUBASE2020 decay data (if available)
    nubase_loaded = False
    nubase_files = [
        DATA_DIR / "nubase_4.mas20.txt",
        DATA_DIR / "nubase2020.txt",
        DATA_DIR / "nubase.mas20.txt",
    ]
    nubase_file = None
    for f in nubase_files:
        if f.exists():
            nubase_file = f
            break

    if nubase_file:
        logger.info(f"Loading NUBASE2020 from {nubase_file}...")
        try:
            from .nubase2020 import NUBASEParser
            parser = NUBASEParser(str(nubase_file))
            nubase_df = parser.to_dataframe()

            # Create table from DataFrame
            conn.execute("CREATE OR REPLACE TABLE nubase2020 AS SELECT * FROM nubase_df")
            count = conn.execute("SELECT COUNT(*) FROM nubase2020").fetchone()[0]
            logger.info(f"  Loaded {count} entries into nubase2020 table")
            nubase_loaded = True
        except (FileNotFoundError, PermissionError, IOError) as e:
            # File access errors - log and continue without NUBASE
            logger.warning(f"Could not read NUBASE2020 file: {e}")
        except (ValueError, KeyError, IndexError, TypeError) as e:
            # Parsing errors - log and continue without NUBASE
            logger.warning(f"Could not parse NUBASE2020 data: {e}")
        except ImportError as e:
            # Missing dependency
            logger.warning(f"NUBASE2020 parser unavailable: {e}")
        except duckdb.Error as e:
            # Database error during table creation
            logger.warning(f"Could not create NUBASE2020 table: {e}")
    else:
        logger.info("NUBASE2020 file not found, skipping decay data")

    # Create combined view joining experimental, theoretical, and decay data
    logger.info("Creating combined nuclides view...")

    if nubase_loaded:
        # Join all three datasets
        conn.execute("""
            CREATE OR REPLACE VIEW nuclides AS
            SELECT
                COALESCE(a.Z, f.Z, n.Z) AS Z,
                COALESCE(a.N, f.N, n.N) AS N,
                COALESCE(a.A, f.A, n.A) AS A,
                COALESCE(a.Element, n.symbol) AS Element,
                -- Experimental data (AME2020)
                a.Mass_excess_keV AS mass_excess_exp_keV,
                a.Mass_excess_unc_keV AS mass_excess_exp_unc_keV,
                a.Binding_energy_per_A_keV AS binding_per_A_exp_keV,
                -- Theoretical data (FRDM2012)
                f.M_th * 1000 AS mass_excess_th_keV,
                f.E_bind AS binding_total_th_MeV,
                f.beta2,
                f.beta3,
                f.beta4,
                f.beta6,
                f."E_s+p" AS shell_pairing_MeV,
                f.E_mic AS microscopic_MeV,
                -- Decay data (NUBASE2020)
                n.half_life_str,
                n.half_life_sec,
                n.is_stable,
                n.spin_parity,
                n.decay_modes,
                n.discovery_year,
                n.isomer_flag,
                -- Comparison
                CASE WHEN a.Mass_excess_keV IS NOT NULL AND f.M_th IS NOT NULL
                     THEN a.Mass_excess_keV - f.M_th * 1000
                     ELSE NULL END AS exp_minus_th_keV,
                -- Flags
                a.Mass_excess_keV IS NOT NULL AS has_experimental,
                f.M_th IS NOT NULL AS has_theoretical,
                n.Z IS NOT NULL AS has_decay_data
            FROM ame2020 a
            FULL OUTER JOIN frdm2012 f ON a.Z = f.Z AND a.N = f.N AND a.A = f.A
            LEFT JOIN (
                SELECT * FROM nubase2020 WHERE isomer_flag = '' OR isomer_flag IS NULL
            ) n ON COALESCE(a.Z, f.Z) = n.Z AND COALESCE(a.N, f.N) = n.N
        """)
    else:
        # Original view without NUBASE data
        conn.execute("""
            CREATE OR REPLACE VIEW nuclides AS
            SELECT
                COALESCE(a.Z, f.Z) AS Z,
                COALESCE(a.N, f.N) AS N,
                COALESCE(a.A, f.A) AS A,
                a.Element,
                -- Experimental data (AME2020)
                a.Mass_excess_keV AS mass_excess_exp_keV,
                a.Mass_excess_unc_keV AS mass_excess_exp_unc_keV,
                a.Binding_energy_per_A_keV AS binding_per_A_exp_keV,
                -- Theoretical data (FRDM2012)
                f.M_th * 1000 AS mass_excess_th_keV,
                f.E_bind AS binding_total_th_MeV,
                f.beta2,
                f.beta3,
                f.beta4,
                f.beta6,
                f."E_s+p" AS shell_pairing_MeV,
                f.E_mic AS microscopic_MeV,
                -- Placeholder decay columns
                NULL AS half_life_str,
                NULL AS half_life_sec,
                NULL AS is_stable,
                NULL AS spin_parity,
                NULL AS decay_modes,
                NULL AS discovery_year,
                NULL AS isomer_flag,
                -- Comparison
                CASE WHEN a.Mass_excess_keV IS NOT NULL AND f.M_th IS NOT NULL
                     THEN a.Mass_excess_keV - f.M_th * 1000
                     ELSE NULL END AS exp_minus_th_keV,
                -- Flags
                a.Mass_excess_keV IS NOT NULL AS has_experimental,
                f.M_th IS NOT NULL AS has_theoretical,
                FALSE AS has_decay_data
            FROM ame2020 a
            FULL OUTER JOIN frdm2012 f ON a.Z = f.Z AND a.N = f.N AND a.A = f.A
        """)

    count = conn.execute("SELECT COUNT(*) FROM nuclides").fetchone()[0]
    logger.info(f"  Combined view has {count} nuclides")

    # Create indexes for faster lookups
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ame_zna ON ame2020(Z, N, A)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_frdm_zna ON frdm2012(Z, N, A)")
    if nubase_loaded:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nubase_zn ON nubase2020(Z, N)")

    logger.info(f"Database saved to {db_path}")
    return conn


class NuclearDatabase:
    """
    High-level interface for querying nuclear mass data.

    This class provides simple Python methods for common research queries,
    without requiring SQL knowledge. For advanced users, raw SQL queries
    are also supported via the `query()` method.

    The class supports context manager protocol for automatic cleanup:

        with NuclearDatabase() as db:
            fe56 = db.get_nuclide(z=26, n=30)
        # Connection automatically closed

    Attributes:
        db_path: Path to the DuckDB database file.

    Example:
        Basic usage - look up a nuclide::

            from nucmass import NuclearDatabase

            db = NuclearDatabase()

            # Get Iron-56 (the most tightly bound nucleus)
            fe56 = db.get_nuclide(z=26, n=30)
            print(f"Mass excess: {fe56['mass_excess_exp_keV']:.0f} keV")
            print(f"Deformation: {fe56['beta2']:.3f}")

        Get all isotopes of an element::

            uranium = db.get_isotopes(z=92)
            print(f"Found {len(uranium)} uranium isotopes")

        Find nuclides without experimental data::

            predictions = db.get_predicted_only()
            superheavy = predictions[predictions['Z'] > 118]
            print(f"{len(superheavy)} superheavy predictions")

    Note:
        The database must be initialized before use. If the database file
        doesn't exist, it will be created automatically from CSV files.
        Run `python scripts/download_nuclear_data.py` first.
    """

    # Class-level LRU cache for mass excess values (shared across instances)
    # Key: (db_path, z, n, prefer), Value: mass_excess in keV
    # Using OrderedDict for proper LRU eviction with popitem(last=False)
    _mass_cache: OrderedDict[tuple, float | None] = OrderedDict()
    _CACHE_MAX_SIZE = Config.CACHE_MAX_SIZE
    _cache_lock = threading.Lock()

    # Thread-local storage for connections (enables thread-safe usage)
    _thread_local = threading.local()

    def __init__(self, db_path: Path | str | None = None, thread_safe: bool = False):
        """
        Initialize the database connection.

        Args:
            db_path: Path to the DuckDB database file. If None, uses the
                default location (data/nuclear_masses.duckdb).
            thread_safe: If True, use thread-local connections for safe
                multi-threaded access. Each thread gets its own connection.
        """
        if db_path is None:
            db_path = DB_PATH
        self.db_path = Path(db_path)
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._cache_enabled = True
        self._thread_safe = thread_safe

    def __enter__(self) -> "NuclearDatabase":
        """Enter context manager - returns self."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager - closes connection."""
        self.close()

    def __repr__(self) -> str:
        """String representation."""
        status = "connected" if self._conn is not None else "not connected"
        return f"NuclearDatabase(path={self.db_path}, status={status})"

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        """Get the database connection, initializing if needed.

        In thread-safe mode, each thread gets its own connection via
        thread-local storage. This is essential for multi-threaded applications.
        """
        if self._thread_safe:
            # Thread-safe mode: use thread-local connections
            thread_conn = getattr(self._thread_local, 'conn', None)
            if thread_conn is None:
                thread_conn = self._create_connection()
                self._thread_local.conn = thread_conn
            return thread_conn
        else:
            # Standard mode: single connection
            if self._conn is None:
                self._conn = self._create_connection()
            return self._conn

    def _create_connection(self) -> duckdb.DuckDBPyConnection:
        """Create a new database connection, initializing DB if needed."""
        if not self.db_path.exists():
            try:
                logger.debug(f"Database not found, initializing: {self.db_path}")
                return init_database(self.db_path)
            except DataFileNotFoundError as e:
                raise DataFileNotFoundError(
                    str(e.filepath),
                    f"Database initialization failed. {e.suggestion or ''}\n"
                    "Run: python scripts/download_nuclear_data.py"
                ) from e
            except Exception as e:
                raise RuntimeError(
                    f"Failed to initialize database at {self.db_path}: {e}\n"
                    "Try removing the database file and running:\n"
                    "  python scripts/download_nuclear_data.py"
                ) from e
        else:
            # Connect to existing database and validate
            logger.debug(f"Connecting to existing database: {self.db_path}")
            try:
                conn = duckdb.connect(str(self.db_path))
                self._validate_database(conn)
                return conn
            except DatabaseCorruptError:
                raise
            except duckdb.Error as e:
                raise DatabaseCorruptError(
                    str(self.db_path),
                    f"DuckDB error: {e}"
                ) from e

    def _validate_database(self, conn: duckdb.DuckDBPyConnection) -> None:
        """Validate database integrity on connection."""
        try:
            # Check required tables exist
            tables = conn.execute("SHOW TABLES").fetchall()
            table_names = {t[0] for t in tables}
            required_tables = {"ame2020", "frdm2012"}

            missing = required_tables - table_names
            if missing:
                raise DatabaseCorruptError(
                    str(self.db_path),
                    f"Missing required tables: {missing}"
                )

            # Check nuclides view exists
            views = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_type = 'VIEW'"
            ).fetchall()
            view_names = {v[0] for v in views}
            if "nuclides" not in view_names:
                raise DatabaseCorruptError(
                    str(self.db_path),
                    "Missing 'nuclides' view"
                )

            # Quick integrity check: verify A = Z + N for sample
            invalid = conn.execute(
                "SELECT COUNT(*) FROM nuclides WHERE A != Z + N LIMIT 1"
            ).fetchone()[0]
            if invalid > 0:
                raise DatabaseCorruptError(
                    str(self.db_path),
                    "Data integrity check failed: A != Z + N"
                )

            logger.debug("Database validation passed")
        except DatabaseCorruptError:
            raise
        except Exception as e:
            raise DatabaseCorruptError(
                str(self.db_path),
                f"Validation query failed: {e}"
            ) from e

    def query(self, sql: str) -> pd.DataFrame:
        """
        Execute a custom SQL query and return results as a DataFrame.

        This method is for advanced users who want to write their own SQL.
        For common queries, use the convenience methods like `get_nuclide()`.

        Args:
            sql: SQL query string to execute.

        Returns:
            pandas DataFrame containing the query results.

        Example:
            Find all magic nuclei (Z or N = 2, 8, 20, 28, 50, 82, 126)::

                db = NuclearDatabase()
                magic = db.query('''
                    SELECT Z, N, A, Element, beta2
                    FROM nuclides
                    WHERE Z IN (2, 8, 20, 28, 50, 82)
                      AND N IN (2, 8, 20, 28, 50, 82, 126)
                    ORDER BY A
                ''')

            Count nuclides by element::

                counts = db.query('''
                    SELECT Z, Element, COUNT(*) as isotope_count
                    FROM nuclides
                    WHERE Element IS NOT NULL
                    GROUP BY Z, Element
                    ORDER BY Z
                ''')
        """
        return self.conn.execute(sql).df()

    def get_nuclide(self, z: int, n: int) -> pd.Series:
        """
        Get all data for a specific nuclide.

        Args:
            z: Proton number (atomic number). Example: 26 for Iron.
            n: Neutron number. Example: 30 for Iron-56.

        Returns:
            pandas Series with all columns for this nuclide.
            Key columns include:
            - mass_excess_exp_keV: Experimental mass excess (keV)
            - mass_excess_th_keV: Theoretical mass excess (keV)
            - beta2: Quadrupole deformation parameter
            - has_experimental: True if AME2020 data exists
            - has_theoretical: True if FRDM2012 data exists

        Raises:
            InvalidNuclideError: If Z or N are invalid (negative, wrong type).
            NuclideNotFoundError: If no data exists for this Z, N combination.

        Example:
            >>> db = NuclearDatabase()
            >>> pb208 = db.get_nuclide(z=82, n=126)  # Lead-208 (doubly magic)
            >>> print(f"Pb-208 is spherical: beta2 = {pb208['beta2']:.3f}")
            Pb-208 is spherical: beta2 = 0.000
        """
        _validate_z(z, "Proton number must be non-negative.")
        _validate_n(n, "Neutron number must be non-negative.")

        df = self.conn.execute(
            "SELECT * FROM nuclides WHERE Z = ? AND N = ?", [z, n]
        ).df()

        if len(df) == 0:
            # Get available N values for this Z to provide helpful suggestions
            available = self.conn.execute(
                "SELECT DISTINCT N FROM nuclides WHERE Z = ? ORDER BY N", [z]
            ).df()
            suggestions = [(z, int(row['N'])) for _, row in available.iterrows()]
            raise NuclideNotFoundError(z, n, suggestions)

        return df.iloc[0]

    def get_nuclide_or_none(self, z: int, n: int) -> pd.Series | None:
        """
        Get nuclide data, returning None if not found (no exception).

        This is useful when checking many nuclides where some may not exist.

        Args:
            z: Proton number.
            n: Neutron number.

        Returns:
            pandas Series with nuclide data, or None if not found.
        """
        _validate_z(z)
        _validate_n(n)

        df = self.conn.execute(
            "SELECT * FROM nuclides WHERE Z = ? AND N = ?", [z, n]
        ).df()
        if len(df) == 0:
            return None
        return df.iloc[0]

    def get_isotopes(self, z: int) -> pd.DataFrame:
        """
        Get all isotopes of an element (same Z, different N).

        Args:
            z: Proton number (atomic number).

        Returns:
            DataFrame with all isotopes, sorted by neutron number.

        Raises:
            InvalidNuclideError: If Z is invalid.

        Example:
            >>> db = NuclearDatabase()
            >>> tin = db.get_isotopes(z=50)  # Tin has the most stable isotopes
            >>> print(f"Tin has {len(tin)} known isotopes")
            >>> print(f"N range: {tin['N'].min()} to {tin['N'].max()}")
        """
        _validate_z(z, f"Invalid proton number Z={z}")
        return self.conn.execute(
            "SELECT * FROM nuclides WHERE Z = ? ORDER BY N", [z]
        ).df()

    def get_isotones(self, n: int) -> pd.DataFrame:
        """
        Get all isotones (same N, different Z).

        Isotones share the same neutron number. Magic neutron numbers
        (N = 2, 8, 20, 28, 50, 82, 126) produce more stable isotones.

        Args:
            n: Neutron number.

        Returns:
            DataFrame with all isotones, sorted by proton number.

        Raises:
            InvalidNuclideError: If N is invalid.

        Example:
            >>> db = NuclearDatabase()
            >>> n82 = db.get_isotones(n=82)  # N=82 magic number
            >>> print(f"Found {len(n82)} N=82 isotones")
        """
        _validate_n(n, f"Invalid neutron number N={n}")
        return self.conn.execute(
            "SELECT * FROM nuclides WHERE N = ? ORDER BY Z", [n]
        ).df()

    def get_isobars(self, a: int) -> pd.DataFrame:
        """
        Get all isobars (same mass number A).

        Isobars have the same total number of nucleons (A = Z + N).

        Args:
            a: Mass number (total nucleons).

        Returns:
            DataFrame with all isobars, sorted by proton number.

        Raises:
            InvalidNuclideError: If A is invalid.

        Example:
            >>> db = NuclearDatabase()
            >>> a56 = db.get_isobars(a=56)  # A=56 includes Fe-56
            >>> print(a56[['Z', 'Element', 'N', 'mass_excess_exp_keV']])
        """
        _validate_a(a, f"Invalid mass number A={a}")
        return self.conn.execute(
            "SELECT * FROM nuclides WHERE A = ? ORDER BY Z", [a]
        ).df()

    def get_deformed(self, min_beta2: float = 0.2) -> pd.DataFrame:
        """
        Get nuclei with significant quadrupole deformation.

        The deformation parameter beta2 describes nuclear shape:
        - beta2 ≈ 0: Spherical (magic nuclei)
        - beta2 > 0: Prolate (cigar-shaped, stretched along symmetry axis)
        - beta2 < 0: Oblate (disc-shaped, flattened)

        Args:
            min_beta2: Minimum absolute value of beta2. Default 0.2.

        Returns:
            DataFrame with deformed nuclei, sorted by |beta2| descending.

        Raises:
            ValueError: If min_beta2 is negative.

        Example:
            >>> db = NuclearDatabase()
            >>> deformed = db.get_deformed(min_beta2=0.3)
            >>> print(f"Found {len(deformed)} highly deformed nuclei")
            >>> # Most deformed are in rare earth and actinide regions
            >>> print(deformed[['Z', 'N', 'A', 'beta2']].head(10))
        """
        if min_beta2 < 0:
            raise ValueError(f"min_beta2 must be non-negative, got {min_beta2}")

        return self.conn.execute(
            "SELECT * FROM nuclides WHERE ABS(beta2) >= ? ORDER BY ABS(beta2) DESC",
            [min_beta2]
        ).df()

    def get_predicted_only(self) -> pd.DataFrame:
        """
        Get nuclides with only theoretical predictions (no experimental data).

        These are nuclides where FRDM2012 provides mass predictions, but
        no experimental measurement exists in AME2020. Includes:
        - Very neutron-rich nuclei (important for r-process)
        - Superheavy elements (Z > 118)
        - Proton-rich nuclei far from stability

        Returns:
            DataFrame with predicted-only nuclides, sorted by Z and N.

        Example:
            >>> db = NuclearDatabase()
            >>> predicted = db.get_predicted_only()
            >>> print(f"Total predictions without experiment: {len(predicted)}")
            >>>
            >>> # How many superheavy predictions?
            >>> superheavy = predicted[predicted['Z'] > 118]
            >>> print(f"Superheavy (Z > 118): {len(superheavy)}")
        """
        return self.query("""
            SELECT * FROM nuclides
            WHERE has_experimental = FALSE AND has_theoretical = TRUE
            ORDER BY Z, N
        """)

    def get_mass_excess(self, z: int, n: int, prefer: str = "experimental") -> float | None:
        """
        Get the mass excess for a nuclide in keV.

        Results are cached for performance when computing separation energies.

        Args:
            z: Proton number.
            n: Neutron number.
            prefer: Which value to prefer if both exist.
                "experimental" (default): Use AME2020 if available
                "theoretical": Use FRDM2012 if available

        Returns:
            Mass excess in keV, or None if not available.

        Raises:
            InvalidNuclideError: If Z or N are invalid.
            ValueError: If prefer is not "experimental" or "theoretical".
        """
        if prefer not in ("experimental", "theoretical"):
            raise ValueError(f"prefer must be 'experimental' or 'theoretical', got '{prefer}'")

        # Check cache first (thread-safe read)
        cache_key = (str(self.db_path), z, n, prefer)
        if self._cache_enabled:
            with NuclearDatabase._cache_lock:
                if cache_key in NuclearDatabase._mass_cache:
                    # Move to end to mark as recently used (LRU)
                    NuclearDatabase._mass_cache.move_to_end(cache_key)
                    return NuclearDatabase._mass_cache[cache_key]

        nuclide = self.get_nuclide_or_none(z, n)
        if nuclide is None:
            result = None
        elif prefer == "experimental":
            if pd.notna(nuclide['mass_excess_exp_keV']):
                result = float(nuclide['mass_excess_exp_keV'])
            elif pd.notna(nuclide['mass_excess_th_keV']):
                result = float(nuclide['mass_excess_th_keV'])
            else:
                result = None
        else:
            if pd.notna(nuclide['mass_excess_th_keV']):
                result = float(nuclide['mass_excess_th_keV'])
            elif pd.notna(nuclide['mass_excess_exp_keV']):
                result = float(nuclide['mass_excess_exp_keV'])
            else:
                result = None

        # Store in cache (thread-safe write with size limit using LRU eviction)
        if self._cache_enabled:
            with NuclearDatabase._cache_lock:
                # Evict oldest entries if at capacity (atomic popitem operations)
                while len(NuclearDatabase._mass_cache) >= self._CACHE_MAX_SIZE:
                    NuclearDatabase._mass_cache.popitem(last=False)  # Remove oldest
                NuclearDatabase._mass_cache[cache_key] = result

        return result

    def get_binding_energy(self, z: int, n: int) -> float | None:
        """
        Get the total binding energy for a nuclide in MeV.

        Calculated from mass excess: B = Z*M_H + N*M_n - M_atom
        where M_H = 7.289 MeV (hydrogen mass excess) and M_n = 8.071 MeV (neutron).

        Args:
            z: Proton number.
            n: Neutron number.

        Returns:
            Total binding energy in MeV, or None if mass data unavailable.
        """
        mass_excess_keV = self.get_mass_excess(z, n)
        if mass_excess_keV is None:
            return None

        a = z + n
        # Binding energy from mass excess (AME2020 convention)
        # B = Z*Delta_H + N*Delta_n - Delta_atom
        # Using Config constants for consistency across the codebase
        binding_keV = (z * Config.PROTON_MASS_EXCESS +
                       n * Config.NEUTRON_MASS_EXCESS -
                       mass_excess_keV)
        return binding_keV / 1000.0  # Convert to MeV

    # === Separation Energy Methods ===

    def get_separation_energy_n(self, z: int, n: int) -> float | None:
        """
        Calculate one-neutron separation energy S_n.

        S_n(Z,N) = B(Z,N) - B(Z,N-1)
                 = M(Z,N-1) + M_n - M(Z,N)

        This is the energy required to remove one neutron from the nucleus.

        Args:
            z: Proton number.
            n: Neutron number (must be >= 1).

        Returns:
            S_n in MeV, or None if mass data unavailable.
        """
        if n < 1:
            return None

        m_parent = self.get_mass_excess(z, n)
        m_daughter = self.get_mass_excess(z, n - 1)

        if m_parent is None or m_daughter is None:
            return None

        s_n = m_daughter + Config.NEUTRON_MASS_EXCESS - m_parent
        return s_n / 1000.0  # Convert to MeV

    def get_separation_energy_p(self, z: int, n: int) -> float | None:
        """
        Calculate one-proton separation energy S_p.

        S_p(Z,N) = B(Z,N) - B(Z-1,N)
                 = M(Z-1,N) + M_H - M(Z,N)

        This is the energy required to remove one proton from the nucleus.

        Args:
            z: Proton number (must be >= 1).
            n: Neutron number.

        Returns:
            S_p in MeV, or None if mass data unavailable.
        """
        if z < 1:
            return None

        m_parent = self.get_mass_excess(z, n)
        m_daughter = self.get_mass_excess(z - 1, n)

        if m_parent is None or m_daughter is None:
            return None

        s_p = m_daughter + Config.PROTON_MASS_EXCESS - m_parent
        return s_p / 1000.0  # Convert to MeV

    def get_separation_energy_2n(self, z: int, n: int) -> float | None:
        """
        Calculate two-neutron separation energy S_2n.

        S_2n(Z,N) = B(Z,N) - B(Z,N-2)
                  = M(Z,N-2) + 2*M_n - M(Z,N)

        Two-neutron separation energies show clear signatures of shell closures.

        Args:
            z: Proton number.
            n: Neutron number (must be >= 2).

        Returns:
            S_2n in MeV, or None if mass data unavailable.
        """
        if n < 2:
            return None

        m_parent = self.get_mass_excess(z, n)
        m_daughter = self.get_mass_excess(z, n - 2)

        if m_parent is None or m_daughter is None:
            return None

        s_2n = m_daughter + 2 * Config.NEUTRON_MASS_EXCESS - m_parent
        return s_2n / 1000.0  # Convert to MeV

    def get_separation_energy_2p(self, z: int, n: int) -> float | None:
        """
        Calculate two-proton separation energy S_2p.

        S_2p(Z,N) = B(Z,N) - B(Z-2,N)
                  = M(Z-2,N) + 2*M_H - M(Z,N)

        Args:
            z: Proton number (must be >= 2).
            n: Neutron number.

        Returns:
            S_2p in MeV, or None if mass data unavailable.
        """
        if z < 2:
            return None

        m_parent = self.get_mass_excess(z, n)
        m_daughter = self.get_mass_excess(z - 2, n)

        if m_parent is None or m_daughter is None:
            return None

        s_2p = m_daughter + 2 * Config.PROTON_MASS_EXCESS - m_parent
        return s_2p / 1000.0  # Convert to MeV

    def get_separation_energy_alpha(self, z: int, n: int) -> float | None:
        """
        Calculate alpha separation energy S_α.

        S_α(Z,N) = B(Z,N) - B(Z-2,N-2) - B(α)
                 = M(Z-2,N-2) + M_α - M(Z,N)

        where M_α = 2.425 MeV is the alpha particle mass excess.

        Args:
            z: Proton number (must be >= 2).
            n: Neutron number (must be >= 2).

        Returns:
            S_α in MeV, or None if mass data unavailable.
        """
        if z < 2 or n < 2:
            return None

        m_parent = self.get_mass_excess(z, n)
        m_daughter = self.get_mass_excess(z - 2, n - 2)

        if m_parent is None or m_daughter is None:
            return None

        s_alpha = m_daughter + Config.ALPHA_MASS_EXCESS - m_parent
        return s_alpha / 1000.0  # Convert to MeV

    def get_q_value(
        self,
        z_initial: int,
        n_initial: int,
        z_final: int,
        n_final: int,
        z_ejectile: int = 0,
        n_ejectile: int = 0,
    ) -> float | None:
        """
        Calculate Q-value for a nuclear reaction.

        Q = (M_initial + M_projectile) - (M_final + M_ejectile)
          = (sum of initial mass excesses) - (sum of final mass excesses)

        Positive Q means energy is released (exothermic).
        Negative Q means energy must be supplied (endothermic).

        Args:
            z_initial: Proton number of initial (target) nucleus.
            n_initial: Neutron number of initial nucleus.
            z_final: Proton number of final (residual) nucleus.
            n_final: Neutron number of final nucleus.
            z_ejectile: Proton number of ejectile (default 0 for neutron or gamma).
            n_ejectile: Neutron number of ejectile (default 0).

        Returns:
            Q-value in MeV, or None if mass data unavailable.

        Example:
            # (n,γ) capture: initial + n -> final + γ
            >>> db.get_q_value(26, 30, 26, 31)  # Fe-56(n,γ)Fe-57

            # (n,p) reaction: initial + n -> final + p
            >>> db.get_q_value(26, 30, 25, 31, z_ejectile=1)
        """
        m_initial = self.get_mass_excess(z_initial, n_initial)
        m_final = self.get_mass_excess(z_final, n_final)

        if m_initial is None or m_final is None:
            return None

        # Get projectile and ejectile masses from conservation
        # Z: z_initial + z_projectile = z_final + z_ejectile
        # N: n_initial + n_projectile = n_final + n_ejectile
        z_projectile = z_final + z_ejectile - z_initial
        n_projectile = n_final + n_ejectile - n_initial

        # Get mass excesses for light particles (from Config)
        def get_light_particle_mass(z: int, n: int) -> float | None:
            if z == 0 and n == 0:
                return 0.0  # gamma ray
            elif z == 0 and n == 1:
                return Config.NEUTRON_MASS_EXCESS  # neutron
            elif z == 1 and n == 0:
                return Config.PROTON_MASS_EXCESS  # proton
            elif z == 2 and n == 2:
                return Config.ALPHA_MASS_EXCESS  # alpha
            else:
                # Look up in database
                m = self.get_mass_excess(z, n)
                return m * 1000 if m else None  # Convert MeV to keV

        m_projectile = get_light_particle_mass(z_projectile, n_projectile)
        m_ejectile = get_light_particle_mass(z_ejectile, n_ejectile)

        if m_projectile is None or m_ejectile is None:
            return None

        # Q = (M_i + M_proj) - (M_f + M_ej)  [all in keV]
        q_keV = (m_initial + m_projectile) - (m_final + m_ejectile)
        return q_keV / 1000.0  # Convert to MeV

    def compare_masses(self, max_diff_keV: float = 5000) -> pd.DataFrame:
        """
        Compare experimental and theoretical masses where both exist.

        Useful for assessing model accuracy and identifying discrepancies.

        Args:
            max_diff_keV: Maximum difference to include (filters outliers).
                Default 5000 keV (5 MeV).

        Returns:
            DataFrame with comparison data, sorted by |difference| descending.
            Includes: Z, N, A, Element, mass_excess_exp_keV, mass_excess_th_keV,
            exp_minus_th_keV (difference), beta2.

        Example:
            >>> db = NuclearDatabase()
            >>> comparison = db.compare_masses()
            >>> print(f"Nuclides with both exp and theory: {len(comparison)}")
            >>>
            >>> # Calculate RMS deviation
            >>> import numpy as np
            >>> rms = np.sqrt((comparison['exp_minus_th_keV']**2).mean())
            >>> print(f"RMS deviation: {rms/1000:.2f} MeV")
        """
        return self.conn.execute(
            """SELECT Z, N, A, Element,
                      mass_excess_exp_keV,
                      mass_excess_th_keV,
                      exp_minus_th_keV,
                      beta2
               FROM nuclides
               WHERE has_experimental AND has_theoretical
                 AND ABS(exp_minus_th_keV) <= ?
               ORDER BY ABS(exp_minus_th_keV) DESC""",
            [max_diff_keV]
        ).df()

    def summary(self) -> dict[str, int]:
        """
        Get summary statistics for the database.

        Returns:
            Dictionary with counts:
            - ame2020_count: Number of nuclides in AME2020
            - frdm2012_count: Number of nuclides in FRDM2012
            - nubase2020_count: Number of entries in NUBASE2020 (if loaded)
            - total_nuclides: Total unique nuclides
            - both_exp_and_th: Nuclides with both experimental and theoretical data
            - predicted_only: Nuclides with only theoretical predictions
            - with_decay_data: Nuclides with decay information

        Example:
            >>> db = NuclearDatabase()
            >>> stats = db.summary()
            >>> for key, value in stats.items():
            ...     print(f"{key}: {value:,}")
            ame2020_count: 3,558
            frdm2012_count: 9,318
            nubase2020_count: 5,656
            total_nuclides: 9,420
            both_exp_and_th: 3,456
            predicted_only: 5,862
            with_decay_data: 4,195
        """
        stats: dict[str, int] = {}
        stats["ame2020_count"] = self.conn.execute(
            "SELECT COUNT(*) FROM ame2020"
        ).fetchone()[0]
        stats["frdm2012_count"] = self.conn.execute(
            "SELECT COUNT(*) FROM frdm2012"
        ).fetchone()[0]

        # Check if nubase2020 table exists
        tables = self.conn.execute("SHOW TABLES").df()
        if "nubase2020" in tables["name"].values:
            stats["nubase2020_count"] = self.conn.execute(
                "SELECT COUNT(*) FROM nubase2020"
            ).fetchone()[0]

        stats["total_nuclides"] = self.conn.execute(
            "SELECT COUNT(*) FROM nuclides"
        ).fetchone()[0]
        stats["both_exp_and_th"] = self.conn.execute(
            "SELECT COUNT(*) FROM nuclides WHERE has_experimental AND has_theoretical"
        ).fetchone()[0]
        stats["predicted_only"] = self.conn.execute(
            "SELECT COUNT(*) FROM nuclides WHERE NOT has_experimental AND has_theoretical"
        ).fetchone()[0]
        stats["with_decay_data"] = self.conn.execute(
            "SELECT COUNT(*) FROM nuclides WHERE has_decay_data"
        ).fetchone()[0]
        return stats

    def close(self) -> None:
        """
        Close the database connection.

        Call this when you're done with the database to release resources.
        The connection will be automatically reopened if needed.

        In thread-safe mode, only closes the current thread's connection.
        """
        if self._thread_safe:
            # Close thread-local connection
            thread_conn = getattr(self._thread_local, 'conn', None)
            if thread_conn is not None:
                thread_conn.close()
                self._thread_local.conn = None
        else:
            # Close single shared connection
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def __del__(self) -> None:
        """Clean up connection on garbage collection."""
        try:
            self.close()
        except Exception as e:
            # Log at debug level - object may be partially destroyed during shutdown
            # but we want visibility into closure failures for debugging
            try:
                logger.debug(f"Exception during connection cleanup: {type(e).__name__}: {e}")
            except Exception:
                # Logger itself may be unavailable during interpreter shutdown
                pass

    def clear_cache(self) -> None:
        """Clear cached mass excess values for this database (thread-safe)."""
        db_path_str = str(self.db_path)
        with NuclearDatabase._cache_lock:
            keys_to_remove = [k for k in NuclearDatabase._mass_cache if k[0] == db_path_str]
            for k in keys_to_remove:
                del NuclearDatabase._mass_cache[k]


if __name__ == "__main__":
    # Demonstration of database usage
    db = NuclearDatabase()

    print("\n" + "=" * 60)
    print("DATABASE SUMMARY")
    print("=" * 60)
    for key, value in db.summary().items():
        print(f"  {key}: {value:,}")

    print("\n" + "=" * 60)
    print("SAMPLE QUERIES")
    print("=" * 60)

    print("\nFe-56 (Z=26, N=30) - Most tightly bound nucleus:")
    fe56 = db.get_nuclide(26, 30)
    print(f"  Experimental mass excess: {fe56['mass_excess_exp_keV']:.1f} keV")
    print(f"  Theoretical mass excess:  {fe56['mass_excess_th_keV']:.1f} keV")
    print(f"  Difference: {fe56['exp_minus_th_keV']:.1f} keV")
    print(f"  Deformation β2: {fe56['beta2']:.3f}")

    print("\n" + "=" * 60)
    print("SEPARATION ENERGIES")
    print("=" * 60)
    print(f"\nFe-56 separation energies:")
    print(f"  S_n  = {db.get_separation_energy_n(26, 30):.3f} MeV")
    print(f"  S_p  = {db.get_separation_energy_p(26, 30):.3f} MeV")
    print(f"  S_2n = {db.get_separation_energy_2n(26, 30):.3f} MeV")
    print(f"  S_2p = {db.get_separation_energy_2p(26, 30):.3f} MeV")
    print(f"  S_α  = {db.get_separation_energy_alpha(26, 30):.3f} MeV")

    print("\nMost deformed nuclei (|β2| > 0.35):")
    deformed = db.get_deformed(min_beta2=0.35)
    print(deformed[["Z", "N", "A", "beta2"]].head(5).to_string(index=False))

    print("\nPredicted-only nuclides (no experimental data):")
    predicted = db.get_predicted_only()
    print(f"  Total: {len(predicted):,}")
    superheavy = predicted[predicted["Z"] > 118]
    print(f"  Superheavy (Z > 118): {len(superheavy):,}")
