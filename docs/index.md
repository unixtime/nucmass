# nucmass Documentation

Welcome to the nucmass documentation — a toolkit for working with nuclear mass data.

## Contents

1. **[Data Pipeline](data_pipeline.md)**
   - How AME2020 and FRDM2012 data is acquired
   - Parsing and validation steps
   - Troubleshooting common issues

2. **[Database Schema](database_schema.md)**
   - DuckDB table structure
   - Column descriptions
   - Example SQL queries

3. **[Reproducing Results](reproducing_results.md)**
   - Generate figures from FRDM(2012) paper
   - Key findings and statistics
   - Customization options

## Quick Reference

### Installation

```bash
# Install uv first (if needed): curl -LsSf https://astral.sh/uv/install.sh | sh

git clone <repo-url>
cd nucmass
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

### Download Data

```bash
python scripts/download_nuclear_data.py
```

### Python Usage

```python
from nucmass import NuclearDatabase

db = NuclearDatabase()
fe56 = db.get_nuclide(z=26, n=30)
print(f"Fe-56 mass excess: {fe56['mass_excess_exp_keV']:.0f} keV")
```

### Generate Figures

```bash
python scripts/reproduce_frdm2012_figures.py
```

### Run Tests

```bash
pytest tests/ -v
```

## Data Sources

| Dataset | Source | Reference |
|---------|--------|-----------|
| AME2020 | [IAEA AMDC](https://www-nds.iaea.org/amdc/) | Wang et al., Chin. Phys. C 45, 030003 (2021) |
| FRDM2012 | [arXiv:1508.06294](https://arxiv.org/abs/1508.06294) | Möller et al., ADNDT 109-110, 1-204 (2016) |

## Project Structure

```
nucmass/
├── src/nucmass/         # Python package
│   ├── ame2020.py       # AME2020 parser
│   ├── frdm2012.py      # FRDM2012 PDF extractor
│   └── database.py      # DuckDB interface
├── scripts/             # Command-line tools
├── notebooks/           # Jupyter notebooks
├── data/                # Downloaded data (CSV files included)
├── figures/             # Generated plots
├── tests/               # Validation tests (29 tests)
└── docs/                # This documentation
```

## Support

For issues or questions, please open an issue on the repository.
