"""
FRDM2012 (Finite Range Droplet Model 2012) PDF extractor.

Extracts nuclear mass and deformation data from the FRDM2012 PDF publication.
Reference: Möller et al., Atomic Data and Nuclear Data Tables 109-110 (2016) 1-204

The data table contains 9318 nuclei with the following columns:
- Z: Proton number
- N: Neutron number
- A: Mass number
- M_th: Calculated mass excess (MeV)
- E_mic: Microscopic correction (MeV)
- E_s+p: Shell-plus-pairing correction (MeV)
- beta2...beta6: Ground-state deformation parameters
"""

import re
from pathlib import Path

import pandas as pd

from .config import Config, get_logger

# Module logger
logger = get_logger("frdm2012")

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

DATA_DIR = Config.DATA_DIR

# Expected columns based on FRDM2012 arXiv PDF table (page 68+)
# Table has: N A ε2 ε3 ε4 ε6 β2 β3 β4 β6 E_s+p E_mic E_bind M_th M_exp σ_exp E_mic_FL M_th_FL
# Z is given as a header row like "Z=8(O)"
FRDM2012_COLUMNS = [
    "N",           # Neutron number
    "A",           # Mass number
    "eps2",        # ε2 - Nilsson quadrupole deformation
    "eps3",        # ε3 - Nilsson octupole deformation
    "eps4",        # ε4 - Nilsson hexadecapole deformation
    "eps6",        # ε6 - Higher-order Nilsson deformation
    "beta2",       # β2 - Quadrupole deformation (spherical harmonics)
    "beta3",       # β3 - Octupole deformation
    "beta4",       # β4 - Hexadecapole deformation
    "beta6",       # β6 - Higher-order deformation
    "E_s+p",       # Shell-plus-pairing correction (MeV)
    "E_mic",       # Microscopic correction (MeV)
    "E_bind",      # Binding energy (MeV)
    "M_th",        # Theoretical mass excess (MeV)
    "M_exp",       # Experimental mass excess (MeV), blank if unknown
    "sigma_exp",   # Experimental uncertainty (MeV)
    "E_mic_FL",    # Microscopic correction FRLDM (MeV)
    "M_th_FL",     # Theoretical mass excess FRLDM (MeV)
]


class FRDM2012Extractor:
    """
    Extracts FRDM2012 mass table from PDF.

    Usage:
        extractor = FRDM2012Extractor("path/to/frdm2012.pdf")
        # First, discover which pages contain the table
        extractor.inspect_page(70)  # Check a specific page
        # Then extract the full table
        df = extractor.extract(start_page=68, end_page=200)
        df.to_csv("frdm2012.csv", index=False)
    """

    def __init__(self, pdf_path: Path | str):
        if pdfplumber is None:
            raise ImportError("pdfplumber is required. Install with: uv add pdfplumber")
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")

    def inspect_page(self, page_num: int, show_lines: int = 20) -> None:
        """
        Inspect a single page to understand table structure.

        Args:
            page_num: Page number (1-indexed, as shown in PDF viewer)
            show_lines: Number of lines to display
        """
        with pdfplumber.open(self.pdf_path) as pdf:
            if page_num < 1 or page_num > len(pdf.pages):
                logger.error(f"Invalid page. PDF has {len(pdf.pages)} pages.")
                return

            page = pdf.pages[page_num - 1]  # Convert to 0-indexed

            # Try table extraction
            tables = page.extract_tables()
            if tables:
                logger.info(f"Found {len(tables)} table(s) on page {page_num}")
                for i, table in enumerate(tables):
                    logger.info(f"Table {i+1} ({len(table)} rows):")
                    for row in table[:show_lines]:
                        logger.info(str(row))
            else:
                # Fall back to text extraction
                logger.info(f"No tables detected. Raw text from page {page_num}:")
                text = page.extract_text()
                if text:
                    lines = text.split("\n")
                    for line in lines[:show_lines]:
                        logger.info(line)

    def get_page_count(self) -> int:
        """Return total number of pages in PDF."""
        with pdfplumber.open(self.pdf_path) as pdf:
            return len(pdf.pages)

    def _is_header_row(self, row: list) -> bool:
        """Check if row is a header (contains column labels, not data)."""
        if not row:
            return True
        text = " ".join(str(c) for c in row if c).upper()
        # Header indicators
        header_keywords = ["PROTON", "NEUTRON", "MASS", "BETA", "SHELL", "BINDING"]
        # Data rows should have mostly numbers
        has_header_word = any(kw in text for kw in header_keywords)
        # Count numeric-looking cells
        numeric_count = sum(1 for c in row if c and re.match(r"^-?\d+\.?\d*$", str(c).strip()))
        return has_header_word or numeric_count < 3

    def _clean_row(self, row: list) -> list:
        """Clean a row: strip whitespace, handle empty cells."""
        cleaned = []
        for cell in row:
            if cell is None:
                cleaned.append(None)
            elif isinstance(cell, str):
                cell = cell.strip()
                cleaned.append(cell if cell else None)
            else:
                cleaned.append(cell)
        return cleaned

    def _parse_numeric(self, value: str | None) -> float | None:
        """Parse a numeric value, handling various formats."""
        if value is None or value == "":
            return None
        try:
            # Remove any non-numeric characters except minus and decimal
            cleaned = re.sub(r"[^\d.\-]", "", str(value))
            return float(cleaned) if cleaned else None
        except ValueError:
            return None

    def extract(
        self,
        start_page: int,
        end_page: int,
        column_names: list[str] | None = None,
    ) -> pd.DataFrame:
        """
        Extract mass table from specified page range.

        Args:
            start_page: First page containing table data (1-indexed)
            end_page: Last page containing table data (1-indexed)
            column_names: Custom column names (uses FRDM2012_COLUMNS if None)

        Returns:
            DataFrame with extracted nuclear data
        """
        if column_names is None:
            column_names = FRDM2012_COLUMNS

        all_rows = []

        with pdfplumber.open(self.pdf_path) as pdf:
            total_pages = len(pdf.pages)
            start_page = max(1, start_page)
            end_page = min(total_pages, end_page)

            page_range = range(start_page - 1, end_page)
            if tqdm is not None:
                page_range = tqdm(
                    page_range,
                    desc="Extracting pages",
                    unit="page",
                    total=end_page - start_page + 1,
                )
            else:
                logger.info(f"Extracting pages {start_page}-{end_page} of {total_pages}...")

            for page_num in page_range:
                page = pdf.pages[page_num]
                tables = page.extract_tables()

                for table in tables:
                    for row in table:
                        row = self._clean_row(row)
                        # Skip empty rows and headers
                        if not any(row):
                            continue
                        if self._is_header_row(row):
                            continue
                        all_rows.append(row)

        logger.info(f"Extracted {len(all_rows)} raw rows")

        # Build DataFrame
        df = self._build_dataframe(all_rows, column_names)
        return df

    def _build_dataframe(self, rows: list[list], column_names: list[str]) -> pd.DataFrame:
        """Convert raw rows to a cleaned DataFrame."""
        if not rows:
            return pd.DataFrame(columns=column_names)

        # Normalize row lengths to expected columns
        expected_len = len(column_names)
        normalized = []
        for r in rows:
            if len(r) >= 3:  # Must have at least Z, N, A
                # Trim or pad to expected length
                if len(r) > expected_len:
                    normalized.append(r[:expected_len])
                else:
                    normalized.append(r + [None] * (expected_len - len(r)))

        # Create DataFrame
        df = pd.DataFrame(normalized, columns=column_names)

        # Convert Z, N, A to integers
        for col in ["Z", "N", "A"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

        # Convert numeric columns (all except Z, N, A)
        numeric_cols = [c for c in df.columns if c not in ["Z", "N", "A"]]
        for col in numeric_cols:
            if col in df.columns:
                # Handle any remaining unicode minus signs
                if df[col].dtype == object:
                    df[col] = df[col].astype(str).str.replace("−", "-", regex=False)
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Filter valid nuclides (must have Z, N, A)
        df = df.dropna(subset=["Z", "N", "A"])

        # Validate: A should equal Z + N
        if "Z" in df.columns and "N" in df.columns and "A" in df.columns:
            valid_mask = df["A"] == df["Z"] + df["N"]
            invalid_count = (~valid_mask).sum()
            if invalid_count > 0:
                logger.warning(f"{invalid_count} rows have A != Z+N (checking for parsing errors)")
                # Keep only valid rows
                df = df[valid_mask]

        return df.reset_index(drop=True)

    def extract_text_based(
        self,
        start_page: int,
        end_page: int,
    ) -> pd.DataFrame:
        """
        Alternative extraction using text parsing instead of table detection.
        Handles FRDM2012 format where Z is in header rows like "Z=8(O)".
        """
        all_rows = []
        current_z = None

        # Pattern for Z header: "Z=8(O)", "Z=26(Fe)", or "Z=117" (no symbol for superheavy)
        z_pattern = re.compile(r"Z\s*=\s*(\d+)")

        # Pattern for data rows: starts with N A then numbers
        # Example: "8 16 −0.03 0.20 0.12 −0.02 −0.010 ..."
        # Note: may have Unicode minus signs
        data_pattern = re.compile(r"^\s*(\d+)\s+(\d+)\s+([-−\d.]+)")

        with pdfplumber.open(self.pdf_path) as pdf:
            total_pages = len(pdf.pages)
            start_page = max(1, start_page)
            end_page = min(total_pages, end_page)

            page_range = range(start_page - 1, end_page)
            if tqdm is not None:
                page_range = tqdm(
                    page_range,
                    desc="Extracting (text)",
                    unit="page",
                    total=end_page - start_page + 1,
                )
            else:
                logger.info(f"Text-based extraction, pages {start_page}-{end_page}...")

            for page_num in page_range:
                page = pdf.pages[page_num]
                text = page.extract_text()

                if not text:
                    continue

                for line in text.split("\n"):
                    # Check for Z header
                    z_match = z_pattern.search(line)
                    if z_match:
                        current_z = int(z_match.group(1))
                        continue

                    # Check for data row
                    if current_z is not None:
                        data_match = data_pattern.match(line)
                        if data_match:
                            # Normalize minus signs and split
                            line = line.replace("−", "-")
                            values = line.split()
                            # Prepend Z to the row
                            row = [current_z] + values
                            all_rows.append(row)

        logger.info(f"Extracted {len(all_rows)} rows via text parsing")

        # Build DataFrame with Z as first column
        columns = ["Z"] + FRDM2012_COLUMNS
        return self._build_dataframe(all_rows, columns)

    def to_csv(self, df: pd.DataFrame, output_path: Path | str | None = None) -> Path:
        """Export DataFrame to CSV."""
        if output_path is None:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            output_path = DATA_DIR / "frdm2012_extracted.csv"

        output_path = Path(output_path)
        df.to_csv(output_path, index=False)
        logger.info(f"Saved {len(df)} nuclides to {output_path}")
        return output_path


def extract_frdm2012_from_pdf(
    pdf_path: str | Path,
    start_page: int = 68,
    end_page: int = 233,
    output_csv: str | Path | None = None,
) -> pd.DataFrame:
    """
    Convenience function to extract FRDM2012 data from PDF.

    Args:
        pdf_path: Path to the FRDM2012 PDF
        start_page: First page of data table (adjust after inspection)
        end_page: Last page of data table
        output_csv: Optional path for CSV output

    Returns:
        DataFrame with nuclear mass and deformation data
    """
    extractor = FRDM2012Extractor(pdf_path)

    # Try table extraction first
    df = extractor.extract(start_page, end_page)

    # Fall back to text-based if too few rows
    if len(df) < 1000:  # FRDM2012 should have ~9318 nuclides
        logger.info("Table extraction yielded few results, trying text-based extraction...")
        df = extractor.extract_text_based(start_page, end_page)

    if output_csv:
        extractor.to_csv(df, output_csv)

    return df


if __name__ == "__main__":
    import sys
    from .config import setup_logging
    setup_logging("INFO")

    if len(sys.argv) < 2:
        logger.error("Usage: python frdm2012.py <path_to_pdf> [start_page] [end_page]")
        logger.info("Example workflow:")
        logger.info("  1. First inspect pages to find the table:")
        logger.info("     python -c \"from hasna.frdm2012 import FRDM2012Extractor; e = FRDM2012Extractor('frdm2012.pdf'); e.inspect_page(70)\"")
        logger.info("  2. Then extract with correct page range:")
        logger.info("     python frdm2012.py frdm2012.pdf 68 200")
        sys.exit(1)

    pdf_path = sys.argv[1]
    start_page = int(sys.argv[2]) if len(sys.argv) > 2 else 68
    end_page = int(sys.argv[3]) if len(sys.argv) > 3 else 200

    df = extract_frdm2012_from_pdf(
        pdf_path,
        start_page=start_page,
        end_page=end_page,
        output_csv=DATA_DIR / "frdm2012_extracted.csv",
    )

    logger.info(f"Extracted {len(df)} nuclides")
    logger.info(f"Columns: {list(df.columns)}")
    logger.info(f"Sample (first 5 rows):")
    logger.info(str(df.head()))
