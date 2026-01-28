# Reproducing Results

This guide explains how to reproduce key figures and analyses from the FRDM(2012) paper using the extracted data.

## Quick Start

```bash
# Generate all figures
python scripts/reproduce_frdm2012_figures.py

# Output saved to figures/
ls figures/
```

## Generated Figures

### Figure 1: Nuclear Chart Deformation

**File:** `figures/fig1_deformation_chart.png`

Shows ground-state quadrupole deformation β₂ for all 9,318 nuclides in FRDM2012.

**Color scheme:**
- **Red (β₂ > 0):** Prolate nuclei (cigar-shaped)
- **Blue (β₂ < 0):** Oblate nuclei (disc-shaped)
- **White (β₂ ≈ 0):** Spherical nuclei

**Key features visible:**
- Spherical regions near magic numbers (N, Z = 8, 20, 28, 50, 82, 126)
- Rare earth deformation (Z ≈ 60–70, N ≈ 90–100)
- Actinide deformation (Z ≈ 90–100, N ≈ 140–150)
- Superheavy region predictions (Z > 100)

**Reproduce:**
```python
from nucmass import NuclearDatabase
import matplotlib.pyplot as plt

db = NuclearDatabase()
df = db.query("SELECT * FROM nuclides WHERE has_theoretical")

plt.scatter(df['N'], df['Z'], c=df['beta2'], cmap='RdBu_r',
            s=5, vmin=-0.4, vmax=0.4)
plt.colorbar(label='β₂')
plt.xlabel('N')
plt.ylabel('Z')
```

### Figure 2: Mass Model Accuracy

**File:** `figures/fig2_mass_residuals.png`

Four-panel analysis of FRDM2012 mass predictions vs experiment.

**Panel A:** Residuals (M_exp - M_th) vs mass number A
- Dashed lines show ±σ = 0.56 MeV (FRDM published accuracy)

**Panel B:** Histogram of residuals
- RMS ≈ 0.99 MeV (includes all 3,456 compared nuclides)
- Mean ≈ 0.25 MeV (slight positive bias)

**Panel C:** Residuals on nuclear chart
- Shows where model performs well/poorly

**Panel D:** Residuals vs neutron excess (N - Z)

**Statistics from our extraction:**
```
Mass Model Statistics (n=3456 nuclides):
  Mean residual: 0.251 MeV
  RMS deviation: 0.988 MeV
  Std deviation: 0.955 MeV
```

**Note:** The published RMS of 0.56 MeV is for a selected subset of 2,149 nuclides used in the fit. Our value includes all nuclides with experimental data.

### Figure 3: Shell Effects

**File:** `figures/fig3_shell_effects.png`

Visualizes the shell-plus-pairing correction E_s+p.

**Panel A:** Shell corrections on nuclear chart
- Deep blue indicates strong shell closures (magic numbers)
- Shell effects range from about -14 MeV to +4 MeV

**Panel B:** Shell effects in Sn (Z=50) and Pb (Z=82) isotope chains
- Clear minima at N = 50, 82, 126 (neutron magic numbers)
- Sn-132 (Z=50, N=82): Doubly magic, ~-13 MeV correction
- Pb-208 (Z=82, N=126): Doubly magic, ~-14 MeV correction

**Physical interpretation:**
Negative shell corrections indicate enhanced stability. Doubly-magic nuclei are "waiting points" in the r-process nucleosynthesis where neutron capture slows down.

### Figure 4: Binding Energy Curve

**File:** `figures/fig4_binding_energy.png`

Classic binding energy per nucleon (B/A) visualization.

**Panel A:** B/A vs mass number
- Peak at Fe-56 (marked with star): B/A ≈ 8.79 MeV
- Explains why iron is the end product of stellar fusion
- Heavy nuclei have lower B/A → can release energy via fission

**Panel B:** B/A on nuclear chart
- Shows the valley of stability
- Brightest (yellow) region around iron

### Figure 5: Two-Neutron Separation Energies

**File:** `figures/fig5_separation_energies.png`

S₂ₙ = B(Z, N) - B(Z, N-2)

**Panel A:** S₂ₙ on nuclear chart
- Red vertical lines mark N = 50, 82, 126 (magic numbers)
- Sudden drop in S₂ₙ after magic numbers indicates shell closure

**Panel B:** S₂ₙ for Sn and Pb isotopes
- Sharp drops immediately after crossing N = 50, 82, 126
- Indicates extra stability of magic configurations

## Jupyter Notebook

For interactive exploration:

```bash
jupyter lab notebooks/explore_nuclear_data.ipynb
```

The notebook includes:
1. Database connection and summary
2. Nuclear chart visualization
3. Specific nuclide lookups (Fe-56, Pb-208)
4. Isotope chain analysis
5. Experiment vs theory comparison
6. Deformed nuclei exploration
7. Unmeasured nuclide predictions
8. Custom SQL queries

## Key Results Summary

### Deformation Statistics

```
Total nuclides: 9,318
Z range: 8 - 136
N range: 8 - 236

Deformation Statistics (β₂):
  Spherical (|β₂| < 0.05): 1,577 nuclides (17%)
  Oblate (β₂ < -0.15): 724 nuclides (8%)
  Prolate (β₂ > 0.15): 5,020 nuclides (54%)
  Most oblate: β₂ = -0.630 (superheavy region)
  Most prolate: β₂ = +0.553 (rare earths)
```

### Notable Nuclides

| Nuclide | Z | N | β₂ | Shell Correction | Notes |
|---------|---|---|----|------------------|-------|
| O-16 | 8 | 8 | -0.01 | -0.6 MeV | Doubly magic |
| Ca-48 | 20 | 28 | 0.00 | -5.8 MeV | Doubly magic |
| Ni-78 | 28 | 50 | 0.00 | -10.4 MeV | Doubly magic |
| Sn-132 | 50 | 82 | 0.00 | -12.8 MeV | Doubly magic, r-process waiting point |
| Pb-208 | 82 | 126 | 0.00 | -13.8 MeV | Doubly magic, most stable heavy nucleus |
| U-238 | 92 | 146 | 0.27 | -0.3 MeV | Deformed actinide |

### Data Coverage

```
AME2020 only (light nuclei, Z < 8): 102 nuclides
Both experimental and theoretical: 3,456 nuclides
FRDM2012 only (predictions): 5,862 nuclides
  - Including 516 superheavy nuclides (Z > 118)

The 5,862 predicted-only nuclides are crucial for:
- r-process nucleosynthesis calculations
- Superheavy element predictions (Z=119–136)
- Nuclear structure far from stability
- Island of stability searches around Z≈114, N≈184
```

## Customizing Figures

The script `scripts/reproduce_frdm2012_figures.py` can be modified to:

1. **Change color maps:** Edit `cmap` parameter in scatter plots
2. **Adjust ranges:** Modify `vmin`, `vmax` for color scaling
3. **Add annotations:** Use `ax.annotate()` for specific nuclides
4. **Export formats:** Change `.png` to `.pdf`, `.svg`, etc.

Example customization:

```python
# In reproduce_frdm2012_figures.py

# Use different colormap for deformation
scatter = ax.scatter(df['N'], df['Z'], c=df['beta2'],
                     cmap='coolwarm',  # Changed from RdBu_r
                     s=10,             # Larger markers
                     vmin=-0.5, vmax=0.5)  # Wider range

# Highlight a specific isotope chain
uranium = df[df['Z'] == 92]
ax.plot(uranium['N'], uranium['Z'], 'k-', linewidth=2, label='Uranium')
```

## Validation Against Published Values

To verify our extraction against the original paper:

```python
from nucmass import NuclearDatabase

db = NuclearDatabase()

# Table I from paper: Selected mass excesses
test_cases = [
    (8, 8, -4.74),    # O-16
    (26, 30, -60.60), # Fe-56 (paper gives -60.60, we get -60.53)
    (82, 126, -21.75), # Pb-208
]

for z, n, published_mth in test_cases:
    nuclide = db.get_nuclide(z, n)
    extracted = nuclide['mass_excess_th_keV'] / 1000  # Convert to MeV
    diff = extracted - published_mth
    print(f"Z={z}, N={n}: Published={published_mth:.2f}, Extracted={extracted:.2f}, Diff={diff:.2f} MeV")
```

Small differences (~0.1 MeV) are expected due to:
- PDF text extraction precision
- Rounding in the published tables
- Unicode minus sign handling
