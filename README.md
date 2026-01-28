# nucmass

**Nuclear Mass Data Toolkit for Researchers**

A Python toolkit providing easy access to nuclear mass and decay data from three authoritative sources:

| Dataset | Nuclides | Type | Z Range | Description |
|---------|----------|------|---------|-------------|
| **AME2020** | 3,558 | Experimental | 0–118 | Atomic Mass Evaluation 2020 |
| **FRDM2012** | 9,318 | Theoretical | 8–136 | Finite Range Droplet Model predictions |
| **NUBASE2020** | 5,843 | Experimental | 0–118 | Half-lives, decay modes, spin/parity |

## Features

- **Unified Database**: Query experimental and theoretical masses through a single interface
- **Physical Calculations**: Separation energies (S_n, S_p, S_2n, S_2p, S_α), Q-values, binding energies
- **Decay Properties**: Half-lives, decay modes, spin/parity from NUBASE2020
- **Visualization**: Publication-quality nuclear charts and isotope chain plots
- **CLI Interface**: Quick lookups from the command line
- **DuckDB Backend**: Fast SQL-based queries for complex analyses

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/unixtime/nucmass.git
cd nucmass

# Install with uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv && source .venv/bin/activate
uv pip install -e "."

# Or with pip
pip install -e "."
```

### Python Usage

```python
from nucmass import NuclearDatabase

# Use context manager for automatic cleanup
with NuclearDatabase() as db:
    # Look up a specific nuclide
    fe56 = db.get_nuclide(z=26, n=30)  # Iron-56
    print(f"Fe-56 mass excess: {fe56['mass_excess_exp_keV']:.0f} keV")
    print(f"Fe-56 deformation: {fe56['beta2']:.3f}")

    # Calculate separation energies
    s2n = db.get_separation_energy_2n(z=82, n=126)  # Pb-208
    print(f"Pb-208 S_2n = {s2n:.2f} MeV")

    # Get all isotopes of an element
    uranium = db.get_isotopes(z=92)
    print(f"Found {len(uranium)} uranium isotopes")
```

### Decay Data (NUBASE2020)

```python
from nucmass import NUBASEParser

parser = NUBASEParser("data/nubase_4.mas20.txt")

# Get Fe-56 properties
fe56 = parser.get_nuclide(z=26, n=30)
print(f"Fe-56 is stable: {fe56['is_stable']}")
print(f"Spin/parity: {fe56['spin_parity']}")

# Find all stable nuclides
stable = parser.get_stable()
print(f"Found {len(stable)} stable nuclides")

# Get alpha emitters
alpha = parser.get_by_decay_mode("A=")
print(f"Found {len(alpha)} alpha emitters")
```

### Command-Line Interface

```bash
# Look up a nuclide
nucmass lookup 26 30          # Fe-56
nucmass lookup 82 126 --json  # Pb-208 as JSON

# Separation energies
nucmass separation 82 126     # Shows S_n, S_2n, S_p, S_2p, S_α

# List isotopes
nucmass isotopes 92 -n 10     # First 10 uranium isotopes

# Q-value calculation
nucmass qvalue 26 30 26 31    # Fe-56(n,γ)Fe-57

# Database summary
nucmass summary
```

### Plotting

```python
from nucmass import NuclearDatabase, plot_chart, plot_isotope_chain

with NuclearDatabase() as db:
    # Nuclear chart colored by deformation
    fig = plot_chart(db, color_by="beta2")
    fig.savefig("nuclear_chart.png", dpi=150)

    # Sn isotope chain with S_2n
    fig = plot_isotope_chain(db, z=50, y="S_2n")
    fig.savefig("sn_chain.png", dpi=150)
```

## Data Sources & Citations

### AME2020 (Experimental Masses)

> Wang, M., Huang, W.J., Kondev, F.G., Audi, G., & Naimi, S. (2021).
> **The AME 2020 atomic mass evaluation (II). Tables, graphs and references.**
> *Chinese Physics C*, 45(3), 030003.
> DOI: [10.1088/1674-1137/abddb0](https://doi.org/10.1088/1674-1137/abddb0)

### FRDM2012 (Theoretical Masses)

> Möller, P., Sierk, A.J., Ichikawa, T., & Sagawa, H. (2016).
> **Nuclear ground-state masses and deformations: FRDM(2012).**
> *Atomic Data and Nuclear Data Tables*, 109-110, 1-204.
> DOI: [10.1016/j.adt.2015.10.002](https://doi.org/10.1016/j.adt.2015.10.002)
> arXiv: [1508.06294](https://arxiv.org/abs/1508.06294)

### NUBASE2020 (Nuclear Properties)

> Kondev, F.G., Wang, M., Huang, W.J., Naimi, S., & Audi, G. (2021).
> **The NUBASE2020 evaluation of nuclear physics properties.**
> *Chinese Physics C*, 45(3), 030001.
> DOI: [10.1088/1674-1137/abddae](https://doi.org/10.1088/1674-1137/abddae)

Data files available from: [ANL Atomic Mass Data Resources](https://www.anl.gov/phy/atomic-mass-data-resources)

## Available Data

The unified `nuclides` view in the DuckDB database combines all three data sources with the following columns:

### Mass & Structure Columns

| Column | Description | Unit | Source |
|--------|-------------|------|--------|
| `Z` | Proton number | — | All |
| `N` | Neutron number | — | All |
| `A` | Mass number (Z + N) | — | All |
| `Element` | Chemical symbol | — | AME2020/NUBASE |
| `mass_excess_exp_keV` | Experimental mass excess | keV | AME2020 |
| `mass_excess_th_keV` | Theoretical mass excess | keV | FRDM2012 |
| `binding_per_A_exp_keV` | Binding energy per nucleon | keV | AME2020 |
| `beta2` | Quadrupole deformation | — | FRDM2012 |
| `beta3`, `beta4`, `beta6` | Higher-order deformations | — | FRDM2012 |
| `has_experimental` | Has AME2020 data | bool | — |
| `has_theoretical` | Has FRDM2012 data | bool | — |
| `has_decay_data` | Has NUBASE2020 data | bool | — |

### Decay Columns (from NUBASE2020)

| Column | Description | Unit |
|--------|-------------|------|
| `half_life_str` | Half-life with unit (e.g., "4.463 Gy") | — |
| `half_life_sec` | Half-life in seconds | s |
| `is_stable` | Stability flag | bool |
| `spin_parity` | Nuclear spin and parity (e.g., "0+") | — |
| `decay_modes` | Decay mode string (e.g., "A=100;SF=5e-5") | — |
| `discovery_year` | Year of discovery | — |

## Physical Calculations

### Separation Energies

```python
with NuclearDatabase() as db:
    # One-neutron separation energy
    s_n = db.get_separation_energy_n(z=82, n=126)

    # Two-neutron separation energy
    s_2n = db.get_separation_energy_2n(z=82, n=126)

    # Proton separation energies
    s_p = db.get_separation_energy_p(z=82, n=126)
    s_2p = db.get_separation_energy_2p(z=82, n=126)

    # Alpha separation energy
    s_alpha = db.get_separation_energy_alpha(z=92, n=146)
```

### Q-Values

```python
with NuclearDatabase() as db:
    # Neutron capture Q-value: Fe-56(n,γ)Fe-57
    q = db.get_q_value(26, 30, 26, 31, z_ejectile=0, n_ejectile=0)

    # Alpha decay Q-value: U-238 → Th-234 + α
    q = db.get_q_value(92, 146, 90, 144, z_ejectile=2, n_ejectile=2)
```

## Project Structure

```
nucmass/
├── src/nucmass/           # Python package
│   ├── __init__.py        # Package exports
│   ├── ame2020.py         # AME2020 parser
│   ├── frdm2012.py        # FRDM2012 PDF extractor
│   ├── nubase2020.py      # NUBASE parser
│   ├── database.py        # DuckDB interface
│   ├── cli.py             # Command-line interface
│   ├── plotting.py        # Visualization functions
│   └── exceptions.py      # Custom exceptions
├── data/
│   ├── ame2020_masses.csv    # Experimental masses
│   ├── frdm2012_masses.csv   # Theoretical masses
│   ├── nubase_4.mas20.txt    # NUBASE2020 decay data
│   └── nuclear_masses.duckdb # Combined database
├── scripts/
│   ├── download_nuclear_data.py
│   └── reproduce_frdm2012_figures.py
├── notebooks/
│   └── explore_nuclear_data.ipynb
├── tests/                 # 91 tests
├── docs/                  # Sphinx documentation
└── figures/               # Generated plots
```

## Run Tests

```bash
uv pip install -e ".[dev]"
pytest tests/ -v
```

## Jupyter Notebook

```bash
uv pip install -e ".[notebook]"
jupyter lab notebooks/explore_nuclear_data.ipynb
```

## License

MIT License - See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please open an issue or pull request on GitHub.

## Acknowledgments

This toolkit was created to make nuclear mass data more accessible to researchers worldwide. Special thanks to the IAEA AMDC, the FRDM collaboration, and Argonne National Laboratory for making their data available.
