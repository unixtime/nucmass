"""
AME2020 (Atomic Mass Evaluation 2020) parser.

Downloads and parses the official mass table from Argonne National Laboratory.
Reference: Wang et al., Chinese Physics C 45, 030003 (2021)
"""

import re
import time
from pathlib import Path

import pandas as pd
import requests

from .config import Config, get_logger

# Module logger
logger = get_logger("ame2020")

# Rate limiting from config
_last_request_time: dict[str, float] = {}

AME2020_URL = "https://www.anl.gov/sites/www/files/2021-03/mass.mas20.txt"
DATA_DIR = Config.DATA_DIR


AME2020_MIRRORS = [
    "https://www.anl.gov/sites/www/files/2021-03/mass.mas20.txt",
    "https://www.anl.gov/sites/www/files/2021-04/mass_1.mas20.txt",
    # IAEA AMDC mirrors
    "https://www-nds.iaea.org/amdc/ame2020/mass_1.mas20.txt",
]


def download_ame2020(output_path: Path | None = None) -> Path:
    """Download AME2020 mass table from ANL or mirrors."""
    if output_path is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        output_path = DATA_DIR / "mass.mas20.txt"

    if output_path.exists():
        logger.info(f"File already exists: {output_path}")
        return output_path

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/plain,*/*",
    }

    last_error = None
    for url in AME2020_MIRRORS:
        try:
            # Rate limiting: respect server by waiting between requests
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            if domain in _last_request_time:
                elapsed = time.time() - _last_request_time[domain]
                if elapsed < Config.REQUEST_DELAY:
                    time.sleep(Config.REQUEST_DELAY - elapsed)

            logger.info(f"Trying {url}...")
            response = requests.get(url, timeout=Config.DOWNLOAD_TIMEOUT, headers=headers)
            _last_request_time[domain] = time.time()
            response.raise_for_status()

            # Validate downloaded content
            content = response.text
            if len(content) < 1000:
                logger.warning(f"Downloaded file too small ({len(content)} bytes), skipping")
                continue
            if "<html" in content[:500].lower():
                logger.warning("Received HTML instead of data (likely blocked), skipping")
                continue
            # Check for expected AME2020 data markers
            if "Mass Excess" not in content[:5000] and "mass" not in content[:5000].lower():
                logger.warning("Downloaded content doesn't appear to be AME2020 data, skipping")
                continue

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content)
            logger.info(f"Saved to {output_path} ({len(content):,} bytes)")
            return output_path
        except requests.RequestException as e:
            logger.warning(f"Failed to download from {url}: {e}")
            last_error = e
            continue

    raise RuntimeError(
        f"Could not download AME2020 from any mirror. Last error: {last_error}\n"
        "Please download manually from https://www.anl.gov/phy/atomic-mass-data-resources\n"
        f"and save to {output_path}"
    )


class AME2020Parser:
    """
    Parser for AME2020 mass.mas20.txt format.

    The file uses fixed-width columns with the following structure:
    - Lines starting with '1' or '0' are data lines
    - First ~36 lines are header comments

    Columns (from AME2020 documentation):
        NZ: N-Z (neutron excess)
        N: Neutron number
        Z: Proton number
        A: Mass number
        El: Element symbol
        O: Origin flag (indicates how mass was determined)
        Mass_excess: Mass excess in keV
        Mass_excess_unc: Uncertainty in mass excess
        Binding_energy: Binding energy per nucleon in keV
        Binding_energy_unc: Uncertainty in binding energy
        Beta_decay_energy: Beta-decay energy in keV
        Beta_decay_energy_unc: Uncertainty in beta-decay energy
        Atomic_mass: Atomic mass in micro-u
        Atomic_mass_unc: Uncertainty in atomic mass
    """

    # Column specifications: (start, end) positions (0-indexed)
    # Based on AME2020 format: a1,i3,i5,i5,i5,1x,a3,a4,1x,f14.6,f12.6,f13.5,1x,f10.5,1x,a2,f13.5,f11.5,1x,i3,1x,f13.6,f12.6
    COLSPECS = [
        (0, 1),    # cc (continuation character)
        (1, 4),    # NZ
        (4, 9),    # N
        (9, 14),   # Z
        (14, 19),  # A
        (20, 23),  # El (element)
        (23, 27),  # O (origin)
        (28, 42),  # Mass excess (keV)
        (42, 54),  # Mass excess uncertainty
        (54, 67),  # Binding energy/A (keV)
        (68, 78),  # Binding energy/A uncertainty
        (79, 81),  # Beta-decay type
        (81, 94),  # Beta-decay energy (keV)
        (94, 105), # Beta-decay energy uncertainty
        (106, 109), # Atomic mass integer part
        (110, 123), # Atomic mass decimal (micro-u)
        (123, 135), # Atomic mass uncertainty
    ]

    COLUMN_NAMES = [
        "cc", "NZ", "N", "Z", "A", "Element", "Origin",
        "Mass_excess_keV", "Mass_excess_unc_keV",
        "Binding_energy_per_A_keV", "Binding_energy_per_A_unc_keV",
        "Beta_type", "Beta_decay_energy_keV", "Beta_decay_energy_unc_keV",
        "Atomic_mass_int", "Atomic_mass_micro_u", "Atomic_mass_unc_micro_u"
    ]

    HEADER_LINES = 36  # Number of header lines to skip

    def __init__(self, filepath: Path | str):
        self.filepath = Path(filepath)
        self._df: pd.DataFrame | None = None

    def parse(self) -> pd.DataFrame:
        """Parse the AME2020 file and return a cleaned DataFrame."""
        if self._df is not None:
            return self._df

        # Read with fixed-width format
        df = pd.read_fwf(
            self.filepath,
            colspecs=self.COLSPECS,
            names=self.COLUMN_NAMES,
            skiprows=self.HEADER_LINES,
            dtype=str,
        )

        # Clean and convert data
        df = self._clean_dataframe(df)
        self._df = df
        return df

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and convert columns to appropriate types."""
        # Remove rows that are clearly not data (e.g., blank or header repeats)
        df = df.dropna(subset=["Z", "N", "A"])

        # Strip whitespace from all string columns
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].str.strip()

        # Convert integer columns
        for col in ["NZ", "N", "Z", "A"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

        # Handle values with '#' (estimated/extrapolated values)
        # In AME, '#' indicates estimated values - we keep them but flag them
        numeric_cols = [
            "Mass_excess_keV", "Mass_excess_unc_keV",
            "Binding_energy_per_A_keV", "Binding_energy_per_A_unc_keV",
            "Beta_decay_energy_keV", "Beta_decay_energy_unc_keV",
            "Atomic_mass_micro_u", "Atomic_mass_unc_micro_u"
        ]

        for col in numeric_cols:
            if col in df.columns:
                # Mark estimated values
                estimated_col = f"{col}_estimated"
                df[estimated_col] = df[col].str.contains("#", na=False)
                # Remove '#' and convert to numeric
                df[col] = df[col].str.replace("#", "", regex=False)
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Combine atomic mass integer and decimal parts
        df["Atomic_mass_int"] = pd.to_numeric(df["Atomic_mass_int"], errors="coerce")
        df["Atomic_mass_micro_u"] = (
            df["Atomic_mass_int"] * 1e6 + df["Atomic_mass_micro_u"]
        )

        # Drop intermediate columns
        df = df.drop(columns=["cc", "Atomic_mass_int"], errors="ignore")

        # Remove rows with no valid Z
        df = df.dropna(subset=["Z"])

        return df.reset_index(drop=True)

    def to_csv(self, output_path: Path | str) -> None:
        """Export parsed data to CSV."""
        df = self.parse()
        df.to_csv(output_path, index=False)
        logger.info(f"Exported {len(df)} nuclides to {output_path}")

    def get_nuclide(self, z: int, n: int) -> pd.Series | None:
        """Get data for a specific nuclide by Z and N."""
        df = self.parse()
        mask = (df["Z"] == z) & (df["N"] == n)
        result = df[mask]
        if len(result) == 0:
            return None
        return result.iloc[0]

    def get_element(self, z: int) -> pd.DataFrame:
        """Get all isotopes of an element by Z."""
        df = self.parse()
        return df[df["Z"] == z]


if __name__ == "__main__":
    # Example usage
    filepath = download_ame2020()
    parser = AME2020Parser(filepath)
    df = parser.parse()

    print(f"\nParsed {len(df)} nuclides")
    print(f"\nColumns: {list(df.columns)}")
    print(f"\nSample data (Fe-56, Z=26, N=30):")
    fe56 = parser.get_nuclide(z=26, n=30)
    if fe56 is not None:
        print(fe56)

    # Export to CSV
    parser.to_csv(DATA_DIR / "ame2020_masses.csv")
