# Database Schema

The nuclear mass data is stored in a DuckDB database (`data/nuclear_masses.duckdb`) with two tables and one combined view.

## Tables

### `ame2020` — Experimental Masses

Source: Atomic Mass Evaluation 2020 (IAEA AMDC)

| Column | Type | Description |
|--------|------|-------------|
| NZ | INTEGER | N - Z (neutron excess) |
| N | INTEGER | Neutron number |
| Z | INTEGER | Proton number |
| A | INTEGER | Mass number |
| Element | VARCHAR | Chemical symbol |
| Origin | VARCHAR | Data origin flag |
| Mass_excess_keV | DOUBLE | Mass excess (keV) |
| Mass_excess_unc_keV | DOUBLE | Mass excess uncertainty (keV) |
| Binding_energy_per_A_keV | DOUBLE | Binding energy per nucleon (keV) |
| Binding_energy_per_A_unc_keV | DOUBLE | B/A uncertainty (keV) |
| Beta_type | VARCHAR | Beta decay type |
| Beta_decay_energy_keV | DOUBLE | Q-value for beta decay (keV) |
| Beta_decay_energy_unc_keV | DOUBLE | Beta decay energy uncertainty |
| Atomic_mass_micro_u | DOUBLE | Atomic mass (micro-u) |
| Atomic_mass_unc_micro_u | DOUBLE | Atomic mass uncertainty |
| *_estimated | BOOLEAN | True if value is extrapolated |

### `frdm2012` — Theoretical Masses

Source: Finite Range Droplet Model 2012 (Möller et al.)

| Column | Type | Description |
|--------|------|-------------|
| Z | INTEGER | Proton number |
| N | INTEGER | Neutron number |
| A | INTEGER | Mass number |
| eps2 | DOUBLE | ε₂ Nilsson quadrupole deformation |
| eps3 | DOUBLE | ε₃ Nilsson octupole deformation |
| eps4 | DOUBLE | ε₄ Nilsson hexadecapole deformation |
| eps6 | DOUBLE | ε₆ Higher-order Nilsson deformation |
| beta2 | DOUBLE | β₂ Quadrupole deformation (spherical harmonics) |
| beta3 | DOUBLE | β₃ Octupole deformation |
| beta4 | DOUBLE | β₄ Hexadecapole deformation |
| beta6 | DOUBLE | β₆ Higher-order deformation |
| E_s+p | DOUBLE | Shell-plus-pairing correction (MeV) |
| E_mic | DOUBLE | Microscopic correction (MeV) |
| E_bind | DOUBLE | Total binding energy (MeV) |
| M_th | DOUBLE | Theoretical mass excess (MeV) |
| M_exp | DOUBLE | Experimental mass excess if available (MeV) |
| sigma_exp | DOUBLE | Experimental uncertainty (MeV) |
| E_mic_FL | DOUBLE | FRLDM microscopic correction (MeV) |
| M_th_FL | DOUBLE | FRLDM mass excess (MeV) |

## Views

### `nuclides` — Combined View

Joins experimental and theoretical data with computed comparisons.

| Column | Type | Description |
|--------|------|-------------|
| Z | INTEGER | Proton number |
| N | INTEGER | Neutron number |
| A | INTEGER | Mass number |
| Element | VARCHAR | Chemical symbol (from AME2020) |
| mass_excess_exp_keV | DOUBLE | Experimental mass excess (keV) |
| mass_excess_exp_unc_keV | DOUBLE | Experimental uncertainty (keV) |
| binding_per_A_exp_keV | DOUBLE | Experimental B/A (keV) |
| mass_excess_th_keV | DOUBLE | Theoretical mass excess (keV) |
| binding_total_th_MeV | DOUBLE | Total binding energy (MeV) |
| beta2 | DOUBLE | Quadrupole deformation |
| beta3 | DOUBLE | Octupole deformation |
| beta4 | DOUBLE | Hexadecapole deformation |
| beta6 | DOUBLE | Higher-order deformation |
| shell_pairing_MeV | DOUBLE | Shell-plus-pairing correction (MeV) |
| microscopic_MeV | DOUBLE | Microscopic correction (MeV) |
| exp_minus_th_keV | DOUBLE | M_exp - M_th (keV) |
| has_experimental | BOOLEAN | True if AME2020 data exists |
| has_theoretical | BOOLEAN | True if FRDM2012 data exists |

## Example Queries

### Get a specific nuclide

```sql
SELECT * FROM nuclides WHERE Z = 26 AND N = 30;  -- Fe-56
```

### Get all isotopes of an element

```sql
SELECT * FROM nuclides WHERE Z = 92 ORDER BY N;  -- Uranium isotopes
```

### Get isotones (same N)

```sql
SELECT * FROM nuclides WHERE N = 82 ORDER BY Z;  -- N=82 magic number
```

### Get isobars (same A)

```sql
SELECT * FROM nuclides WHERE A = 208 ORDER BY Z;  -- A=208 isobars
```

### Find deformed nuclei

```sql
SELECT Z, N, A, beta2
FROM nuclides
WHERE ABS(beta2) > 0.3
ORDER BY ABS(beta2) DESC;
```

### Find doubly-magic nuclei

```sql
SELECT Z, N, A, Element, beta2, shell_pairing_MeV
FROM nuclides
WHERE Z IN (8, 20, 28, 50, 82)
  AND N IN (8, 20, 28, 50, 82, 126)
ORDER BY A;
```

### Nuclides with only theoretical predictions

```sql
SELECT Z, N, A, mass_excess_th_keV, beta2
FROM nuclides
WHERE has_experimental = FALSE AND has_theoretical = TRUE
ORDER BY Z, N;
```

### Compare experiment vs theory

```sql
SELECT Z, N, A, Element,
       mass_excess_exp_keV,
       mass_excess_th_keV,
       exp_minus_th_keV
FROM nuclides
WHERE has_experimental AND has_theoretical
ORDER BY ABS(exp_minus_th_keV) DESC
LIMIT 20;
```

### Mass model statistics

```sql
SELECT
    COUNT(*) as n_compared,
    AVG(exp_minus_th_keV) / 1000 as mean_diff_MeV,
    SQRT(AVG(exp_minus_th_keV * exp_minus_th_keV)) / 1000 as rms_MeV
FROM nuclides
WHERE has_experimental AND has_theoretical;
```

### Heaviest predicted nuclides

```sql
SELECT Z, N, A, mass_excess_th_keV / 1000 as M_th_MeV, beta2
FROM nuclides
WHERE has_theoretical
ORDER BY A DESC
LIMIT 10;
```

## Python Interface

The `NuclearDatabase` class provides convenient methods:

```python
from nucmass import NuclearDatabase

db = NuclearDatabase()

# High-level methods
fe56 = db.get_nuclide(z=26, n=30)
uranium = db.get_isotopes(z=92)
n82 = db.get_isotones(n=82)
a208 = db.get_isobars(a=208)
deformed = db.get_deformed(min_beta2=0.3)
unmeasured = db.get_predicted_only()
comparison = db.compare_masses(max_diff_keV=2000)

# Raw SQL
df = db.query("SELECT * FROM nuclides WHERE Z > 100")

# Summary
stats = db.summary()
# Returns: {'ame2020_count': 3558, 'frdm2012_count': 9318, ...}
```

## Indexes

The database includes indexes for efficient lookups:

```sql
CREATE INDEX idx_ame_zna ON ame2020(Z, N, A);
CREATE INDEX idx_frdm_zna ON frdm2012(Z, N, A);
```
