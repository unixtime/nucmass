# Data Pipeline

This document explains how nuclear mass data is acquired, processed, and stored.

## Prerequisites

**Python 3.12+** and **uv** package manager are required.

Install uv if not already installed:
```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Alternative: Homebrew (macOS), AUR (Arch), or pip
brew install uv    # macOS
yay -S uv          # Arch
pip install uv     # Any platform
```

## Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Data Source   │ ──► │     Parser      │ ──► │    DuckDB       │
└─────────────────┘     └─────────────────┘     └─────────────────┘

AME2020:  IAEA AMDC ──► AME2020Parser ──► ame2020 table
FRDM2012: arXiv PDF ──► FRDM2012Extractor ──► frdm2012 table
                                          └──► nuclides view (combined)
```

## Step 1: AME2020 (Experimental Masses)

### Data Source

The Atomic Mass Evaluation 2020 is the standard reference for experimental nuclear masses.

- **Primary URL:** `https://www-nds.iaea.org/amdc/ame2020/mass_1.mas20.txt`
- **Backup URLs:** ANL mirrors (may require institutional access)
- **Format:** Fixed-width ASCII (Fortran format)

### Download Process

```python
from nucmass import download_ame2020

# Downloads from IAEA AMDC, saves to data/mass.mas20.txt
filepath = download_ame2020()
```

The downloader:
1. Tries IAEA AMDC first (most reliable)
2. Falls back to ANL mirrors if needed
3. Uses proper HTTP headers to avoid 403 errors
4. Caches the file locally

### Parsing

The AME2020 file uses a fixed-width format with 36 header lines:

```
Format: a1,i3,i5,i5,i5,1x,a3,a4,1x,f14.6,f12.6,f13.5,1x,f10.5,...
```

Key parsing steps:
1. Skip header lines (comments and column labels)
2. Parse fixed-width columns using pandas `read_fwf`
3. Handle estimated values marked with `#` (extrapolated masses)
4. Convert units (keV for mass excess, micro-u for atomic mass)
5. Validate A = Z + N for all entries

### Output Columns

| Column | Description | Unit |
|--------|-------------|------|
| Z | Proton number | - |
| N | Neutron number | - |
| A | Mass number | - |
| Element | Chemical symbol | - |
| Mass_excess_keV | Mass excess | keV |
| Mass_excess_unc_keV | Uncertainty | keV |
| Binding_energy_per_A_keV | B/A | keV |
| Atomic_mass_micro_u | Atomic mass | μu |
| *_estimated | Flag for extrapolated values | bool |

## Step 2: FRDM2012 (Theoretical Masses)

### Data Source

The FRDM2012 data is published as tables within the PDF paper. The official data file (`ADNDT-FRDM2012-TABLE.dat`) is hosted on LANL servers with TLS compatibility issues.

**Workaround:** Extract data directly from the arXiv PDF.

- **PDF URL:** `https://arxiv.org/pdf/1508.06294.pdf`
- **Alternative:** IHEP mirror, ScienceDirect (institutional access)

### Download Process

```bash
# Download PDF from arXiv
curl -L -o data/frdm2012.pdf "https://arxiv.org/pdf/1508.06294.pdf"
```

### PDF Extraction

The extraction process handles the unique format of the FRDM2012 tables:

1. **Page scanning:** Find pages containing data tables (pages 68–233)
2. **Z header detection:** Each element section starts with `Z=8(O)` format
3. **Data row parsing:** Extract N, A, and all numerical columns
4. **Validation:** Verify A = Z + N, discard malformed rows

```python
from nucmass.frdm2012 import FRDM2012Extractor

extractor = FRDM2012Extractor("data/frdm2012.pdf")

# Inspect a page to understand structure
extractor.inspect_page(70, show_lines=20)

# Extract all data
df = extractor.extract_text_based(start_page=68, end_page=233)
```

### Table Structure

The FRDM2012 table has this format on each page:

```
Z=26(Fe)
N   A   ε2    ε3    ε4    ε6    β2     β3     β4     β6    E_s+p  E_mic  E_bind  M_th  ...
30  56  0.12  0.00  0.02 -0.02  0.117  0.000 -0.024  0.020  -0.83  1.08   492.19 -60.53
```

### Output Columns

| Column | Description | Unit |
|--------|-------------|------|
| Z | Proton number | - |
| N | Neutron number | - |
| A | Mass number | - |
| eps2–eps6 | Nilsson deformations | - |
| beta2–beta6 | Spherical harmonic deformations | - |
| E_s+p | Shell-plus-pairing correction | MeV |
| E_mic | Microscopic correction | MeV |
| E_bind | Total binding energy | MeV |
| M_th | Theoretical mass excess | MeV |
| M_exp | Experimental mass excess (if known) | MeV |

### Extraction Statistics

- **Total rows extracted:** 9,318
- **Valid nuclides:** 9,318 (Z=8–136)
- **Superheavy predictions (Z > 118):** 516 nuclides

## Step 3: DuckDB Database

### Initialization

```python
from nucmass import init_database

# Creates nuclear_masses.duckdb with both datasets
conn = init_database()
```

### Tables Created

1. **ame2020** — Raw AME2020 data
2. **frdm2012** — Raw FRDM2012 data
3. **nuclides** — Combined view joining both datasets

### The `nuclides` View

```sql
CREATE VIEW nuclides AS
SELECT
    COALESCE(a.Z, f.Z) AS Z,
    COALESCE(a.N, f.N) AS N,
    COALESCE(a.A, f.A) AS A,
    a.Element,
    -- Experimental (AME2020)
    a.Mass_excess_keV AS mass_excess_exp_keV,
    -- Theoretical (FRDM2012)
    f.M_th * 1000 AS mass_excess_th_keV,
    f.beta2, f.beta3, f.beta4, f.beta6,
    f."E_s+p" AS shell_pairing_MeV,
    -- Comparison
    a.Mass_excess_keV - f.M_th * 1000 AS exp_minus_th_keV,
    -- Flags
    a.Mass_excess_keV IS NOT NULL AS has_experimental,
    f.M_th IS NOT NULL AS has_theoretical
FROM ame2020 a
FULL OUTER JOIN frdm2012 f ON a.Z = f.Z AND a.N = f.N
```

### Database Statistics

| Metric | Value |
|--------|-------|
| AME2020 nuclides | 3,558 |
| FRDM2012 nuclides | 9,318 |
| Combined (unique) | 9,420 |
| Both exp + theory | 3,456 |
| Theory only | 5,862 |
| Experiment only | 102 |

## Step 4: Validation

The pipeline includes 29 automated tests:

```bash
pytest tests/test_nuclear_data.py -v
```

### Key Validations

1. **Data integrity:** A = Z + N for all nuclides
2. **No duplicates:** Unique (Z, N, A) combinations
3. **Physical values:** Fe-56 mass excess ≈ -60,607 keV
4. **Magic nuclei:** Pb-208 is spherical (β₂ ≈ 0)
5. **Model accuracy:** >90% agree within 2 MeV

## Running the Full Pipeline

```bash
# 0. Setup (if not done)
uv venv && source .venv/bin/activate && uv pip install -e ".[dev]"

# 1. Download AME2020 and parse
python scripts/download_nuclear_data.py

# 2. Download FRDM2012 PDF (if not already present)
curl -L -o data/frdm2012.pdf "https://arxiv.org/pdf/1508.06294.pdf"

# 3. Extract FRDM2012 and rebuild database
python scripts/download_nuclear_data.py --frdm-pdf data/frdm2012.pdf

# 4. Verify
pytest tests/test_nuclear_data.py -v
```

## Troubleshooting

### AME2020 download fails with 403
The ANL servers may block requests without proper headers. The code automatically falls back to IAEA mirrors.

### FRDM2012 extraction yields few rows
1. Check page range with `inspect_page()`
2. Try different PDF source (arXiv vs IHEP)
3. Use `extract_text_based()` instead of `extract()`

### DuckDB connection issues
```python
# Force re-initialization
from nucmass.database import init_database
init_database()  # Recreates database from CSVs
```
