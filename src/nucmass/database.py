"""
DuckDB Database Interface for Nuclear Mass Data.

This module provides a user-friendly interface to query nuclear mass data
stored in a DuckDB database. It combines experimental data (AME2020) and
theoretical predictions (FRDM2012) into a unified queryable format.

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
"""

from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DB_PATH = DATA_DIR / "nuclear_masses.duckdb"


def get_connection(db_path: Optional[Path | str] = None) -> duckdb.DuckDBPyConnection:
    """
    Get a connection to the nuclear mass database.

    Args:
        db_path: Path to the DuckDB database file. If None, uses the default
            location (data/nuclear_masses.duckdb).

    Returns:
        A DuckDB connection object that can be used for SQL queries.

    Example:
        >>> conn = get_connection()
        >>> result = conn.execute("SELECT COUNT(*) FROM nuclides").fetchone()
        >>> print(f"Total nuclides: {result[0]}")
    """
    if db_path is None:
        db_path = DB_PATH
    return duckdb.connect(str(db_path))


def init_database(db_path: Optional[Path | str] = None) -> duckdb.DuckDBPyConnection:
    """
    Initialize or rebuild the nuclear mass database from CSV files.

    This function creates a DuckDB database with three components:
    - **ame2020 table**: Experimental atomic masses (3,558 nuclides)
    - **frdm2012 table**: Theoretical masses and deformations (9,318 nuclides)
    - **nuclides view**: Combined view joining both datasets

    Args:
        db_path: Where to save the database. If None, uses the default
            location (data/nuclear_masses.duckdb).

    Returns:
        A DuckDB connection to the newly created database.

    Note:
        This function expects CSV files to exist in the data/ directory.
        Run `python scripts/download_nuclear_data.py` first to generate them.

    Example:
        >>> conn = init_database()
        Loading AME2020 from data/ame2020_masses.csv...
          Loaded 3558 nuclides into ame2020 table
        Loading FRDM2012 from data/frdm2012_masses.csv...
          Loaded 9318 nuclides into frdm2012 table
        Creating combined nuclides view...
          Combined view has 9420 nuclides
    """
    if db_path is None:
        db_path = DB_PATH

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(db_path))

    # Load AME2020 experimental data
    ame_csv = DATA_DIR / "ame2020_masses.csv"
    if ame_csv.exists():
        print(f"Loading AME2020 from {ame_csv}...")
        conn.execute("""
            CREATE OR REPLACE TABLE ame2020 AS
            SELECT * FROM read_csv_auto(?)
        """, [str(ame_csv)])
        count = conn.execute("SELECT COUNT(*) FROM ame2020").fetchone()[0]
        print(f"  Loaded {count} nuclides into ame2020 table")

    # Load FRDM2012 theoretical data
    frdm_csv = DATA_DIR / "frdm2012_masses.csv"
    if frdm_csv.exists():
        print(f"Loading FRDM2012 from {frdm_csv}...")
        conn.execute("""
            CREATE OR REPLACE TABLE frdm2012 AS
            SELECT * FROM read_csv_auto(?)
        """, [str(frdm_csv)])
        count = conn.execute("SELECT COUNT(*) FROM frdm2012").fetchone()[0]
        print(f"  Loaded {count} nuclides into frdm2012 table")

    # Create combined view joining experimental and theoretical data
    print("Creating combined nuclides view...")
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
            f.M_th * 1000 AS mass_excess_th_keV,  -- Convert MeV to keV
            f.E_bind AS binding_total_th_MeV,
            f.beta2,
            f.beta3,
            f.beta4,
            f.beta6,
            f."E_s+p" AS shell_pairing_MeV,
            f.E_mic AS microscopic_MeV,
            -- Comparison
            CASE WHEN a.Mass_excess_keV IS NOT NULL AND f.M_th IS NOT NULL
                 THEN a.Mass_excess_keV - f.M_th * 1000
                 ELSE NULL END AS exp_minus_th_keV,
            -- Flags
            a.Mass_excess_keV IS NOT NULL AS has_experimental,
            f.M_th IS NOT NULL AS has_theoretical
        FROM ame2020 a
        FULL OUTER JOIN frdm2012 f ON a.Z = f.Z AND a.N = f.N AND a.A = f.A
    """)

    count = conn.execute("SELECT COUNT(*) FROM nuclides").fetchone()[0]
    print(f"  Combined view has {count} nuclides")

    # Create indexes for faster lookups
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ame_zna ON ame2020(Z, N, A)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_frdm_zna ON frdm2012(Z, N, A)")

    print(f"\nDatabase saved to {db_path}")
    return conn


class NuclearDatabase:
    """
    High-level interface for querying nuclear mass data.

    This class provides simple Python methods for common research queries,
    without requiring SQL knowledge. For advanced users, raw SQL queries
    are also supported via the `query()` method.

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

    def __init__(self, db_path: Optional[Path | str] = None):
        """
        Initialize the database connection.

        Args:
            db_path: Path to the DuckDB database file. If None, uses the
                default location (data/nuclear_masses.duckdb).
        """
        if db_path is None:
            db_path = DB_PATH
        self.db_path = Path(db_path)
        self._conn: Optional[duckdb.DuckDBPyConnection] = None

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        """Get the database connection, initializing if needed."""
        if self._conn is None:
            if not self.db_path.exists():
                self._conn = init_database(self.db_path)
            else:
                self._conn = duckdb.connect(str(self.db_path))
        return self._conn

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

    def get_nuclide(self, z: int, n: int) -> Optional[pd.Series]:
        """
        Get all data for a specific nuclide.

        Args:
            z: Proton number (atomic number). Example: 26 for Iron.
            n: Neutron number. Example: 30 for Iron-56.

        Returns:
            pandas Series with all columns for this nuclide, or None if not found.
            Key columns include:
            - mass_excess_exp_keV: Experimental mass excess (keV)
            - mass_excess_th_keV: Theoretical mass excess (keV)
            - beta2: Quadrupole deformation parameter
            - has_experimental: True if AME2020 data exists
            - has_theoretical: True if FRDM2012 data exists

        Example:
            >>> db = NuclearDatabase()
            >>> pb208 = db.get_nuclide(z=82, n=126)  # Lead-208 (doubly magic)
            >>> print(f"Pb-208 is spherical: beta2 = {pb208['beta2']:.3f}")
            Pb-208 is spherical: beta2 = 0.000
        """
        df = self.query(f"SELECT * FROM nuclides WHERE Z = {z} AND N = {n}")
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

        Example:
            >>> db = NuclearDatabase()
            >>> tin = db.get_isotopes(z=50)  # Tin has the most stable isotopes
            >>> print(f"Tin has {len(tin)} known isotopes")
            >>> print(f"N range: {tin['N'].min()} to {tin['N'].max()}")
        """
        return self.query(f"SELECT * FROM nuclides WHERE Z = {z} ORDER BY N")

    def get_isotones(self, n: int) -> pd.DataFrame:
        """
        Get all isotones (same N, different Z).

        Isotones share the same neutron number. Magic neutron numbers
        (N = 2, 8, 20, 28, 50, 82, 126) produce more stable isotones.

        Args:
            n: Neutron number.

        Returns:
            DataFrame with all isotones, sorted by proton number.

        Example:
            >>> db = NuclearDatabase()
            >>> n82 = db.get_isotones(n=82)  # N=82 magic number
            >>> print(f"Found {len(n82)} N=82 isotones")
        """
        return self.query(f"SELECT * FROM nuclides WHERE N = {n} ORDER BY Z")

    def get_isobars(self, a: int) -> pd.DataFrame:
        """
        Get all isobars (same mass number A).

        Isobars have the same total number of nucleons (A = Z + N).

        Args:
            a: Mass number (total nucleons).

        Returns:
            DataFrame with all isobars, sorted by proton number.

        Example:
            >>> db = NuclearDatabase()
            >>> a56 = db.get_isobars(a=56)  # A=56 includes Fe-56
            >>> print(a56[['Z', 'Element', 'N', 'mass_excess_exp_keV']])
        """
        return self.query(f"SELECT * FROM nuclides WHERE A = {a} ORDER BY Z")

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

        Example:
            >>> db = NuclearDatabase()
            >>> deformed = db.get_deformed(min_beta2=0.3)
            >>> print(f"Found {len(deformed)} highly deformed nuclei")
            >>> # Most deformed are in rare earth and actinide regions
            >>> print(deformed[['Z', 'N', 'A', 'beta2']].head(10))
        """
        return self.query(f"""
            SELECT * FROM nuclides
            WHERE ABS(beta2) >= {min_beta2}
            ORDER BY ABS(beta2) DESC
        """)

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
        return self.query(f"""
            SELECT Z, N, A, Element,
                   mass_excess_exp_keV,
                   mass_excess_th_keV,
                   exp_minus_th_keV,
                   beta2
            FROM nuclides
            WHERE has_experimental AND has_theoretical
              AND ABS(exp_minus_th_keV) <= {max_diff_keV}
            ORDER BY ABS(exp_minus_th_keV) DESC
        """)

    def summary(self) -> dict:
        """
        Get summary statistics for the database.

        Returns:
            Dictionary with counts:
            - ame2020_count: Number of nuclides in AME2020
            - frdm2012_count: Number of nuclides in FRDM2012
            - total_nuclides: Total unique nuclides
            - both_exp_and_th: Nuclides with both experimental and theoretical data
            - predicted_only: Nuclides with only theoretical predictions

        Example:
            >>> db = NuclearDatabase()
            >>> stats = db.summary()
            >>> for key, value in stats.items():
            ...     print(f"{key}: {value:,}")
            ame2020_count: 3,558
            frdm2012_count: 9,318
            total_nuclides: 9,420
            both_exp_and_th: 3,456
            predicted_only: 5,862
        """
        stats = {}
        stats["ame2020_count"] = self.conn.execute(
            "SELECT COUNT(*) FROM ame2020"
        ).fetchone()[0]
        stats["frdm2012_count"] = self.conn.execute(
            "SELECT COUNT(*) FROM frdm2012"
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
        return stats

    def close(self):
        """
        Close the database connection.

        Call this when you're done with the database to release resources.
        The connection will be automatically reopened if needed.
        """
        if self._conn is not None:
            self._conn.close()
            self._conn = None


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
    if fe56 is not None:
        print(f"  Experimental mass excess: {fe56['mass_excess_exp_keV']:.1f} keV")
        print(f"  Theoretical mass excess:  {fe56['mass_excess_th_keV']:.1f} keV")
        print(f"  Difference: {fe56['exp_minus_th_keV']:.1f} keV")
        print(f"  Deformation β2: {fe56['beta2']:.3f}")

    print("\nMost deformed nuclei (|β2| > 0.35):")
    deformed = db.get_deformed(min_beta2=0.35)
    print(deformed[["Z", "N", "A", "beta2"]].head(5).to_string(index=False))

    print("\nPredicted-only nuclides (no experimental data):")
    predicted = db.get_predicted_only()
    print(f"  Total: {len(predicted):,}")
    superheavy = predicted[predicted["Z"] > 118]
    print(f"  Superheavy (Z > 118): {len(superheavy):,}")
