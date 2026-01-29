"""
NUBASE (Nuclear Properties Evaluation) parser.

Parses nuclear decay properties from NUBASE2020 tables.
Reference:
    NUBASE2020: Kondev et al., Chinese Physics C 45, 030001 (2021)
    NUBASE2012: Audi et al., Chinese Physics C 36, 1157 (2012)

NUBASE contains:
- Half-lives and decay modes
- Spin and parity assignments
- Isomeric states
- Year of discovery

Data Columns:
    A: Mass number
    Z: Proton number
    N: Neutron number
    Element: Element symbol
    isomer: Isomeric state flag ('', 'm', 'n', 'p', 'q', 'r', 'x', 'i', 'j')
    mass_excess_keV: Mass excess in keV
    mass_excess_unc_keV: Uncertainty in mass excess
    excitation_energy_keV: Isomer excitation energy (for isomeric states)
    half_life: Half-life with unit (e.g., '4.5 s', '2.3 ms', 'stable')
    half_life_sec: Half-life converted to seconds (None for stable)
    spin_parity: Spin and parity (e.g., '0+', '1/2-')
    decay_modes: Decay mode string (e.g., 'β-=100', 'α=90;β+=10')
    discovery_year: Year the nuclide was discovered
"""

import re
from pathlib import Path

import pandas as pd

from .config import Config, get_logger
from .utils import download_with_mirrors

# Module logger
logger = get_logger("nubase2020")

__all__ = [
    "NUBASEParser",
    "download_nubase2020",
]

DATA_DIR = Config.DATA_DIR

# Pre-compiled regex patterns for performance (avoid recompilation in loops)
_HALF_LIFE_PATTERN = re.compile(r"([0-9.eE+\-]+)\s*(?:\([^)]*\))?\s*([a-zA-Zμ]+)")
_ELEMENT_PATTERN = re.compile(r'\d*\s*([A-Za-z]{1,2})')
_YEAR_PATTERN = re.compile(r'^(\d{4})\s+')

# Multiple mirror URLs for NUBASE2020
NUBASE2020_MIRRORS = [
    "https://www.anl.gov/sites/www/files/2021-03/nubase_4.mas20.txt",
    "https://www-nds.iaea.org/amdc/ame2020/nubase_4.mas20.txt",
    "https://www-nds.iaea.org/amdc/ame2020/nubase.mas20.txt",
]

# Half-life unit conversions to seconds
HALF_LIFE_UNITS = {
    "ys": 1e-24,      # yoctoseconds
    "zs": 1e-21,      # zeptoseconds
    "as": 1e-18,      # attoseconds
    "fs": 1e-15,      # femtoseconds
    "ps": 1e-12,      # picoseconds
    "ns": 1e-9,       # nanoseconds
    "us": 1e-6,       # microseconds
    "μs": 1e-6,       # microseconds (unicode)
    "ms": 1e-3,       # milliseconds
    "s": 1.0,         # seconds
    "m": 60.0,        # minutes
    "h": 3600.0,      # hours
    "d": 86400.0,     # days
    "y": 31557600.0,  # years (Julian year)
    "ky": 31557600e3, # kiloyears
    "My": 31557600e6, # megayears
    "Gy": 31557600e9, # gigayears
    "Ty": 31557600e12, # terayears
    "Py": 31557600e15, # petayears
    "Ey": 31557600e18, # exayears
    "Zy": 31557600e21, # zettayears
    "Yy": 31557600e24, # yottayears
}


def download_nubase2020(output_path: Path | None = None) -> Path:
    """
    Download NUBASE2020 nuclear properties table from ANL or mirrors.

    Args:
        output_path: Where to save the file. Defaults to data/nubase.mas20.txt

    Returns:
        Path to the downloaded file.

    Raises:
        RuntimeError: If download fails from all mirrors.

    Note:
        If automatic download fails due to Cloudflare protection,
        download manually from https://www.anl.gov/phy/atomic-mass-data-resources
        and save to data/nubase.mas20.txt
    """
    if output_path is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        output_path = DATA_DIR / "nubase.mas20.txt"

    # NUBASE-specific content validators
    def validate_nubase_markers(content: str) -> tuple[bool, str]:
        """Check for expected NUBASE data markers (element symbols)."""
        # NUBASE files contain lines like "  1 0010   1   H"
        if any(elem in content[:10000] for elem in ["   H", "  He", "  Li"]):
            return (True, "")
        return (False, "Content doesn't appear to be NUBASE data")

    validators = [
        lambda c: (len(c) >= 1000, f"File too small ({len(c)} bytes)"),
        lambda c: ("<html" not in c[:500].lower(), "Blocked by Cloudflare protection"),
        validate_nubase_markers,
    ]

    return download_with_mirrors(
        mirrors=NUBASE2020_MIRRORS,
        output_path=output_path,
        validators=validators,
        data_name="NUBASE2020",
    )


def parse_half_life(hl_str: str) -> tuple[str, float | None]:
    """
    Parse a half-life string and convert to seconds.

    Args:
        hl_str: Half-life string like '4.5 s', '2.3e6 y', 'stbl', etc.

    Returns:
        Tuple of (original string, half-life in seconds or None if stable/unknown)
    """
    if not hl_str or pd.isna(hl_str):
        return ("", None)

    hl_str = str(hl_str).strip()

    # Handle stable nuclides
    if hl_str.lower() in ("stbl", "stable"):
        return ("stable", None)

    # Handle unknown or special cases
    if hl_str in ("", "?", "*") or "unst" in hl_str.lower():
        return (hl_str, None)

    # Pattern: number (possibly scientific) followed by unit
    # Examples: "4.5 s", "2.3e-6 ms", "1.2(3) Gy", "613.9    s"
    # Also handles: "12.32   y"
    match = _HALF_LIFE_PATTERN.search(hl_str)

    if match:
        try:
            value = float(match.group(1))
            unit = match.group(2)
            if unit in HALF_LIFE_UNITS:
                return (hl_str, value * HALF_LIFE_UNITS[unit])
        except (ValueError, KeyError):
            pass

    return (hl_str, None)


class NUBASEParser:
    """
    Parser for NUBASE2020 format files.

    The file uses fixed-width columns with nuclear properties data.
    No header lines in the data file.

    Format (NUBASE2012/2020):
        Cols 0-2: A (mass number)
        Cols 4-7: Encoded Z and isomer (ZZZS where S is isomer state)
        Cols 11-13: Z (proton number)
        Cols 14-18: Element symbol + isomer flag
        Cols 18-29: Mass excess (keV)
        Cols 29-39: Mass excess uncertainty
        Cols 39-60: Excitation energy (for isomers)
        Cols 60-69: Half-life value
        Cols 69-78: Half-life unit and uncertainty
        Cols 78-88: Spin and parity
        Cols 88-98: Reference
        Cols 98-102: Discovery year
        Cols 102+: Decay modes

    Usage:
        >>> parser = NUBASEParser("data/nubase.mas12.txt")
        >>> df = parser.parse()
        >>> fe56 = parser.get_nuclide(z=26, n=30)
    """

    def __init__(self, filepath: Path | str):
        """
        Initialize the parser.

        Args:
            filepath: Path to the NUBASE data file.
        """
        self.filepath = Path(filepath)
        self._df: pd.DataFrame | None = None

    def parse(self) -> pd.DataFrame:
        """
        Parse the NUBASE file and return a cleaned DataFrame.

        Returns:
            DataFrame with nuclear properties for all nuclides.
        """
        if self._df is not None:
            return self._df

        if not self.filepath.exists():
            raise FileNotFoundError(
                f"NUBASE file not found: {self.filepath}\n"
                "Download from https://www.anl.gov/phy/atomic-mass-data-resources"
            )

        # Read file and parse each line
        rows = []
        total_lines = 0
        short_lines = 0
        parse_failures = 0
        with open(self.filepath, 'r') as f:
            for line_num, line in enumerate(f, 1):
                total_lines += 1
                if len(line) < 50:  # Skip short lines
                    short_lines += 1
                    continue
                row = self._parse_line(line)
                if row is not None:
                    rows.append(row)
                else:
                    parse_failures += 1
                    # Log only at debug level to avoid spam, but warn if unusual
                    logger.debug(f"Line {line_num} failed to parse: {line[:60].strip()!r}...")

        # Log parsing statistics
        logger.info(
            f"Parsed {len(rows)} nuclides from {total_lines} lines "
            f"(skipped {short_lines} short, {parse_failures} unparseable)"
        )
        if parse_failures > 100:
            logger.warning(
                f"High number of parse failures ({parse_failures}). "
                "Consider checking file format compatibility."
            )

        # Create DataFrame
        df = pd.DataFrame(rows)

        # Calculate N = A - Z
        df["N"] = df["A"] - df["Z"]

        # Parse half-life
        half_life_data = df["half_life_raw"].apply(parse_half_life)
        df["half_life_str"] = half_life_data.apply(lambda x: x[0])
        df["half_life_sec"] = half_life_data.apply(lambda x: x[1])
        df["is_stable"] = df["half_life_str"].str.lower() == "stable"

        # Clean up
        df = df.drop(columns=["half_life_raw"], errors="ignore")

        # Reorder columns
        cols = [
            "Z", "N", "A", "Element", "isomer",
            "mass_excess_keV", "mass_excess_unc_keV", "mass_excess_estimated",
            "excitation_keV", "excitation_unc_keV",
            "half_life_str", "half_life_sec", "is_stable",
            "spin_parity", "decay_modes", "discovery_year"
        ]
        df = df[[c for c in cols if c in df.columns]]

        self._df = df
        return df

    def _parse_line(self, line: str) -> dict | None:
        """Parse a single line from NUBASE format."""
        try:
            # A (mass number) - cols 0-2
            a_str = line[0:3].strip()
            if not a_str.isdigit():
                return None
            a = int(a_str)

            # Z (proton number) and isomer from encoded value in cols 4-7
            # Format: ZZZS where ZZZ is Z*10 and S is isomer state (0=ground, 1=m, 2=n, etc.)
            code_str = line[4:8].strip()
            if code_str.isdigit():
                code = int(code_str)
                z = code // 10
                isomer_code = code % 10
                # Decode isomer: 0=ground, 1=m, 2=n, 3=p, 4=q, 5=r, 6=x, 7=w, 8=i, 9=j
                isomer_map = {0: "", 1: "m", 2: "n", 3: "p", 4: "q", 5: "r", 6: "x", 7: "w", 8: "i", 9: "j"}
                isomer = isomer_map.get(isomer_code, "")
            else:
                # Fallback: try to extract from explicit Z position
                z_str = line[9:12].strip()
                if z_str.isdigit():
                    z = int(z_str)
                else:
                    return None
                isomer = ""

            # Element symbol - around cols 11-18
            elem_part = line[11:19].strip()
            # Extract element symbol (1-2 letters only)
            elem_match = _ELEMENT_PATTERN.match(elem_part)
            if elem_match:
                element = elem_match.group(1)
            else:
                # Try harder to find element
                for i, c in enumerate(elem_part):
                    if c.isalpha():
                        element = elem_part[i:i+2].strip()
                        element = ''.join(c for c in element if c.isalpha())
                        break
                else:
                    element = ""

            # Mass excess - cols 18-29
            mass_str = line[18:29].strip()
            mass_estimated = '#' in mass_str
            mass_str = mass_str.replace('#', '')
            try:
                mass_excess = float(mass_str) if mass_str else None
            except ValueError:
                mass_excess = None

            # Mass excess uncertainty - cols 29-39
            mass_unc_str = line[29:39].strip().replace('#', '')
            try:
                mass_unc = float(mass_unc_str) if mass_unc_str else None
            except ValueError:
                mass_unc = None

            # Excitation energy (for isomers) - cols 39-50
            exc_str = line[39:50].strip().replace('#', '')
            try:
                excitation = float(exc_str) if exc_str else None
            except ValueError:
                excitation = None

            # Excitation uncertainty - cols 50-59
            exc_unc_str = line[50:59].strip().replace('#', '').replace('RQ', '')
            try:
                exc_unc = float(exc_unc_str) if exc_unc_str else None
            except ValueError:
                exc_unc = None

            # Half-life - cols 69-88 (value, unit, uncertainty combined)
            # The field is wider than documented - extend to capture units
            half_life_raw = line[69:88].strip()

            # Spin/parity - cols 88-98
            spin_parity = line[88:98].strip()

            # Reference - cols 98-109 (skipped)
            # reference = line[98:109].strip()

            # Decay modes - cols 110+ (includes discovery year at start)
            decay_part = line[110:].strip() if len(line) > 110 else ""

            # Extract discovery year from start of decay field
            discovery_year = None
            decay_modes = decay_part
            year_match = _YEAR_PATTERN.match(decay_part)
            if year_match:
                discovery_year = int(year_match.group(1))
                decay_modes = decay_part[year_match.end():].strip()

            return {
                "A": a,
                "Z": z,
                "Element": element,
                "isomer": isomer,
                "mass_excess_keV": mass_excess,
                "mass_excess_unc_keV": mass_unc,
                "mass_excess_estimated": mass_estimated,
                "excitation_keV": excitation,
                "excitation_unc_keV": exc_unc,
                "half_life_raw": half_life_raw,
                "spin_parity": spin_parity,
                "discovery_year": discovery_year,
                "decay_modes": decay_modes,
            }

        except (ValueError, IndexError, KeyError, AttributeError, TypeError):
            return None

    def to_csv(self, output_path: Path | str) -> None:
        """Export parsed data to CSV."""
        df = self.parse()
        df.to_csv(output_path, index=False)
        logger.info(f"Exported {len(df)} nuclides/isomers to {output_path}")

    def to_dataframe(self) -> pd.DataFrame:
        """
        Return a DataFrame suitable for database import.

        Returns a cleaned DataFrame with standardized column names
        compatible with the NuclearDatabase schema.

        Returns:
            DataFrame with columns: Z, N, A, symbol, isomer_flag,
            half_life_str, half_life_sec, is_stable, spin_parity,
            decay_modes, discovery_year
        """
        df = self.parse().copy()

        # Filter out invalid entries (empty half_life_str and no stability info)
        # Keep entries that have either a half-life string or are marked stable
        valid_mask = (df["half_life_str"].str.strip() != "") | df["is_stable"]
        df = df[valid_mask]

        # Rename columns for database compatibility
        df = df.rename(columns={
            "Element": "symbol",
            "isomer": "isomer_flag",
        })

        # Select columns for database
        cols = [
            "Z", "N", "A", "symbol", "isomer_flag",
            "half_life_str", "half_life_sec", "is_stable",
            "spin_parity", "decay_modes", "discovery_year"
        ]
        return df[[c for c in cols if c in df.columns]]

    def get_nuclide(
        self,
        z: int,
        n: int,
        isomer: str = ""
    ) -> pd.Series | None:
        """
        Get data for a specific nuclide by Z and N.

        Args:
            z: Proton number
            n: Neutron number
            isomer: Isomer flag ('', 'm', 'n', etc.). Default is ground state.

        Returns:
            Series with nuclide properties, or None if not found.
        """
        df = self.parse()
        mask = (df["Z"] == z) & (df["N"] == n) & (df["isomer"] == isomer)
        result = df[mask]
        if len(result) == 0:
            return None
        return result.iloc[0]

    def get_element(self, z: int, include_isomers: bool = False) -> pd.DataFrame:
        """
        Get all isotopes of an element by Z.

        Args:
            z: Proton number
            include_isomers: If True, include isomeric states

        Returns:
            DataFrame with all isotopes.
        """
        df = self.parse()
        mask = df["Z"] == z
        if not include_isomers:
            mask &= df["isomer"] == ""
        return df[mask]

    def get_isomers(self, z: int | None = None) -> pd.DataFrame:
        """
        Get isomeric states.

        Args:
            z: If provided, return only isomers for this element.
               If None, return all isomers.

        Returns:
            DataFrame with isomeric states.
        """
        df = self.parse()
        mask = df["isomer"] != ""
        if z is not None:
            mask &= df["Z"] == z
        return df[mask]

    def get_stable(self) -> pd.DataFrame:
        """Get all stable nuclides."""
        df = self.parse()
        return df[df["is_stable"]]

    def get_by_half_life(
        self,
        min_seconds: float | None = None,
        max_seconds: float | None = None,
        include_stable: bool = False
    ) -> pd.DataFrame:
        """
        Get nuclides filtered by half-life range.

        Args:
            min_seconds: Minimum half-life in seconds
            max_seconds: Maximum half-life in seconds
            include_stable: Include stable nuclides (half_life_sec is None)

        Returns:
            DataFrame with nuclides in the specified half-life range.
        """
        df = self.parse()
        mask = pd.Series([True] * len(df))

        if min_seconds is not None:
            mask &= (df["half_life_sec"] >= min_seconds) | (include_stable & df["is_stable"])
        if max_seconds is not None:
            mask &= (df["half_life_sec"] <= max_seconds)
        if not include_stable:
            mask &= ~df["is_stable"]

        return df[mask]

    def get_by_decay_mode(self, mode: str) -> pd.DataFrame:
        """
        Get nuclides that decay via a specific mode.

        Args:
            mode: Decay mode to search for (e.g., 'β-', 'α', 'β+', 'EC', 'SF')

        Returns:
            DataFrame with nuclides that have the specified decay mode.
        """
        df = self.parse()
        # Case-insensitive search in decay_modes column
        mask = df["decay_modes"].str.contains(mode, case=False, na=False)
        return df[mask]


# Alias for backwards compatibility
NUBASE2020Parser = NUBASEParser


if __name__ == "__main__":
    from .config import setup_logging
    setup_logging("INFO")

    # Example usage - try different file locations
    possible_paths = [
        DATA_DIR / "nubase.mas20.txt",
        DATA_DIR / "nubase.mas12.txt",
        DATA_DIR / "amdc_ame2012_nubase_mas12.csv",
    ]

    filepath = None
    for p in possible_paths:
        if p.exists():
            filepath = p
            break

    if filepath is None:
        logger.error("No NUBASE file found. Download from:")
        logger.error("https://www.anl.gov/phy/atomic-mass-data-resources")
        exit(1)

    logger.info(f"Using: {filepath}")
    parser = NUBASEParser(filepath)

    try:
        df = parser.parse()
        logger.info(f"Parsed {len(df)} nuclides/isomers")

        # Summary statistics
        ground_states = df[df["isomer"] == ""]
        isomers = df[df["isomer"] != ""]
        stable = df[df["is_stable"]]

        logger.info(f"Ground states: {len(ground_states)}")
        logger.info(f"Isomeric states: {len(isomers)}")
        logger.info(f"Stable nuclides: {len(stable)}")

        logger.info("Sample data (Fe-56, Z=26, N=30):")
        fe56 = parser.get_nuclide(z=26, n=30)
        if fe56 is not None:
            logger.info(str(fe56))
        else:
            logger.warning("Fe-56 not found")

        # Export to CSV
        parser.to_csv(DATA_DIR / "nubase_properties.csv")

    except Exception as e:
        logger.error(f"Error: {e}")
