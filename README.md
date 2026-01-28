# nucmass

**Nuclear Mass Data Toolkit for Researchers**

A Python toolkit providing easy access to nuclear mass data from two authoritative sources:

| Dataset | Nuclides | Type | Z Range | Description |
|---------|----------|------|---------|-------------|
| **AME2020** | 3,558 | Experimental | 0–118 | Atomic Mass Evaluation 2020 |
| **FRDM2012** | 9,318 | Theoretical | 8–136 | Finite Range Droplet Model predictions |

## Why This Toolkit?

Getting nuclear mass data shouldn't be hard. The official FRDM2012 data file is hosted on servers with SSL/TLS issues, making it inaccessible via standard downloads. The AME2020 data uses a complex fixed-width format that requires careful parsing.

**This toolkit solves these problems:**
- Pre-extracted and validated data ready to use
- Simple Python interface (no SQL knowledge required)
- Combined database with both experimental and theoretical masses
- Includes 516 superheavy element predictions (Z > 118)

## Quick Start

### For Researchers (Recommended)

```bash
# 1. Download and extract
#    Option A: Clone from GitHub
git clone https://github.com/unixtime/nucmass.git
cd nucmass

#    Option B: Download ZIP and extract
#    Download from: https://github.com/unixtime/nucmass/archive/main.zip
#    Then: unzip nucmass-main.zip && cd nucmass-main

# 2. Install Python package manager (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # or restart terminal

# 3. Create environment and install
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e "."

# 4. Start using!
python -c "from nucmass import NuclearDatabase; print(NuclearDatabase().summary())"
```

### Python Usage

```python
from nucmass import NuclearDatabase

# Connect to the database
db = NuclearDatabase()

# Look up a specific nuclide
fe56 = db.get_nuclide(z=26, n=30)  # Iron-56
print(f"Fe-56 mass excess: {fe56['mass_excess_exp_keV']:.0f} keV")
print(f"Fe-56 deformation: {fe56['beta2']:.3f}")

# Get all isotopes of an element
uranium = db.get_isotopes(z=92)
print(f"Found {len(uranium)} uranium isotopes")

# Find deformed nuclei
deformed = db.get_deformed(min_beta2=0.3)
print(f"Found {len(deformed)} highly deformed nuclei")

# Get superheavy predictions (no experimental data)
predicted = db.get_predicted_only()
superheavy = predicted[predicted['Z'] > 118]
print(f"Superheavy predictions: {len(superheavy)}")
```

## Installation Options

### Option 1: Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package manager.

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Alternative methods:**
```bash
# macOS with Homebrew
brew install uv

# With pip (any platform)
pip install uv
```

Then install nucmass:
```bash
uv venv
source .venv/bin/activate
uv pip install -e "."
```

### Option 2: Using pip

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e "."
```

### Option 3: Using conda

```bash
conda create -n nucmass python=3.12
conda activate nucmass
pip install -e "."
```

## Data Sources & Citations

### AME2020 (Experimental Masses)

> Wang, M., Huang, W.J., Kondev, F.G., Audi, G., & Naimi, S. (2021).
> **The AME 2020 atomic mass evaluation (II). Tables, graphs and references.**
> *Chinese Physics C*, 45(3), 030003.
> DOI: [10.1088/1674-1137/abddb0](https://doi.org/10.1088/1674-1137/abddb0)

- Source: [IAEA Atomic Mass Data Center](https://www-nds.iaea.org/amdc/)
- Contains: Experimental atomic masses, binding energies, decay energies
- Coverage: Z = 0–118 (neutron to Oganesson)

### FRDM2012 (Theoretical Masses)

> Möller, P., Sierk, A.J., Ichikawa, T., & Sagawa, H. (2016).
> **Nuclear ground-state masses and deformations: FRDM(2012).**
> *Atomic Data and Nuclear Data Tables*, 109-110, 1-204.
> DOI: [10.1016/j.adt.2015.10.002](https://doi.org/10.1016/j.adt.2015.10.002)
> arXiv: [1508.06294](https://arxiv.org/abs/1508.06294)

- Contains: Theoretical masses, deformation parameters (β₂–β₆), shell corrections
- Coverage: Z = 8–136 (Oxygen to element 136)
- Includes 516 predictions for superheavy elements beyond Oganesson

## Available Data

### Database Columns

| Column | Description | Unit | Source |
|--------|-------------|------|--------|
| `Z` | Proton number (atomic number) | — | Both |
| `N` | Neutron number | — | Both |
| `A` | Mass number (Z + N) | — | Both |
| `Element` | Chemical symbol | — | AME2020 |
| `mass_excess_exp_keV` | Experimental mass excess | keV | AME2020 |
| `mass_excess_th_keV` | Theoretical mass excess | keV | FRDM2012 |
| `beta2` | Quadrupole deformation | — | FRDM2012 |
| `beta3`, `beta4`, `beta6` | Higher-order deformations | — | FRDM2012 |
| `shell_pairing_MeV` | Shell-plus-pairing correction | MeV | FRDM2012 |
| `has_experimental` | Has AME2020 data | bool | — |
| `has_theoretical` | Has FRDM2012 data | bool | — |

### Understanding Deformation (β₂)

The quadrupole deformation parameter β₂ describes nuclear shape:
- **β₂ ≈ 0**: Spherical (like a ball) — typically near magic numbers
- **β₂ > 0**: Prolate (like a rugby ball) — stretched along symmetry axis
- **β₂ < 0**: Oblate (like a frisbee) — flattened

Magic numbers (Z or N = 2, 8, 20, 28, 50, 82, 126) produce spherical nuclei with enhanced stability.

## Common Research Queries

### Example 1: Find all doubly-magic nuclei

```python
from nucmass import NuclearDatabase

db = NuclearDatabase()

# Doubly magic: both Z and N are magic numbers
magic_Z = [8, 20, 28, 50, 82]
magic_N = [8, 20, 28, 50, 82, 126]

doubly_magic = db.query(f'''
    SELECT Z, N, A, Element, beta2, shell_pairing_MeV
    FROM nuclides
    WHERE Z IN {tuple(magic_Z)} AND N IN {tuple(magic_N)}
    ORDER BY A
''')
print(doubly_magic)
```

### Example 2: Compare experiment vs theory

```python
from nucmass import NuclearDatabase
import numpy as np

db = NuclearDatabase()
comparison = db.compare_masses()

# Calculate statistics
mean_diff = comparison['exp_minus_th_keV'].mean() / 1000  # MeV
rms_diff = np.sqrt((comparison['exp_minus_th_keV']**2).mean()) / 1000

print(f"Nuclides compared: {len(comparison)}")
print(f"Mean difference: {mean_diff:.3f} MeV")
print(f"RMS deviation: {rms_diff:.3f} MeV")
```

### Example 3: Get r-process path nuclei

```python
from nucmass import NuclearDatabase

db = NuclearDatabase()

# Neutron-rich nuclei far from stability
r_process = db.query('''
    SELECT Z, N, A, mass_excess_th_keV, beta2
    FROM nuclides
    WHERE has_theoretical
      AND NOT has_experimental
      AND N > Z + 20
    ORDER BY Z, N
''')
print(f"Predicted neutron-rich nuclei: {len(r_process)}")
```

### Example 4: Export to CSV for Excel

```python
from nucmass import NuclearDatabase

db = NuclearDatabase()

# Get all data and export
all_nuclides = db.query("SELECT * FROM nuclides")
all_nuclides.to_csv("nuclear_masses.csv", index=False)
print("Saved to nuclear_masses.csv")
```

## Jupyter Notebook

For interactive exploration:

```bash
uv pip install -e ".[notebook]"
jupyter lab notebooks/explore_nuclear_data.ipynb
```

## Generate Figures

Reproduce key visualizations from the FRDM(2012) paper:

```bash
python scripts/reproduce_frdm2012_figures.py
# Output saved to figures/
```

Generated figures:
1. Nuclear chart colored by deformation (β₂)
2. Mass model accuracy (experiment vs theory)
3. Shell effects visualization
4. Binding energy per nucleon
5. Two-neutron separation energies

## Run Tests

```bash
uv pip install -e ".[dev]"
pytest tests/ -v
```

## Project Structure

```
nucmass/
├── src/nucmass/           # Python package
│   ├── __init__.py        # Package exports
│   ├── ame2020.py         # AME2020 parser
│   ├── frdm2012.py        # FRDM2012 PDF extractor
│   └── database.py        # DuckDB interface
├── data/
│   ├── ame2020_masses.csv    # Experimental data (3,558 nuclides)
│   ├── frdm2012_masses.csv   # Theoretical data (9,318 nuclides)
│   └── nuclear_masses.duckdb # Combined database
├── scripts/
│   ├── download_nuclear_data.py       # Data pipeline
│   └── reproduce_frdm2012_figures.py  # Generate figures
├── notebooks/
│   └── explore_nuclear_data.ipynb     # Interactive exploration
├── figures/               # Generated plots
├── tests/                 # Validation tests (29 tests)
└── docs/                  # Documentation
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'nucmass'"

Make sure you've activated the virtual environment:
```bash
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

### Database not found

Run the data initialization:
```bash
python scripts/download_nuclear_data.py
```

### PDF extraction issues

If you need to re-extract FRDM2012 data from the original PDF:
```bash
# Download PDF from arXiv
curl -L -o data/frdm2012.pdf "https://arxiv.org/pdf/1508.06294.pdf"

# Extract with full page range
python scripts/download_nuclear_data.py --frdm-pdf data/frdm2012.pdf
```

## License

MIT License - See [LICENSE](LICENSE) for details.

The data itself is subject to the terms of the original publishers:
- AME2020: IAEA Atomic Mass Data Center
- FRDM2012: Published under academic use terms

## Contributing

Contributions are welcome! Please open an issue or pull request on GitHub.

## Acknowledgments

This toolkit was created to make nuclear mass data more accessible to researchers worldwide. Special thanks to the IAEA AMDC and the FRDM collaboration for making their data available.
