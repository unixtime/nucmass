#!/usr/bin/env python3
"""
Reproduce key figures and analyses from FRDM(2012) paper.

Reference: Möller et al., Atomic Data and Nuclear Data Tables 109-110 (2016) 1-204

This script generates:
1. Nuclear chart colored by deformation (β2)
2. Mass model accuracy: experiment vs theory comparison
3. Shell effects visualization
4. Binding energy per nucleon across the chart
5. Two-neutron separation energies (S2n)
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nucmass import NuclearDatabase

# Set up plotting style
plt.style.use("seaborn-v0_8-whitegrid")
sns.set_palette("viridis")

# Use DejaVu Sans which has better Unicode support (subscripts, Greek letters)
plt.rcParams["font.family"] = "DejaVu Sans"

OUTPUT_DIR = Path(__file__).parent.parent / "figures"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_data():
    """Load data from DuckDB."""
    db = NuclearDatabase()

    # Get all nuclides with theoretical data
    frdm = db.query("""
        SELECT Z, N, A, beta2, beta3, beta4, beta6,
               mass_excess_th_keV, binding_total_th_MeV,
               shell_pairing_MeV, microscopic_MeV,
               mass_excess_exp_keV, exp_minus_th_keV,
               has_experimental
        FROM nuclides
        WHERE has_theoretical = TRUE
    """)

    # Calculate additional quantities
    frdm["binding_per_A_MeV"] = frdm["binding_total_th_MeV"] / frdm["A"]

    return frdm, db


def figure1_nuclear_chart_deformation(df):
    """
    Figure: Nuclear chart colored by quadrupole deformation β2.

    This is similar to Figure 1 in the FRDM(2012) paper showing
    ground-state deformations across the nuclear chart.
    """
    fig, ax = plt.subplots(figsize=(14, 10))

    # Create scatter plot
    scatter = ax.scatter(
        df["N"], df["Z"],
        c=df["beta2"],
        cmap="RdBu_r",
        s=8,
        vmin=-0.4,
        vmax=0.4,
        marker="s"
    )

    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax, label="β₂ (quadrupole deformation)")

    # Mark magic numbers
    magic_Z = [8, 20, 28, 50, 82, 126]
    magic_N = [8, 20, 28, 50, 82, 126, 184]

    for z in magic_Z:
        if z <= df["Z"].max():
            ax.axhline(y=z, color="black", linestyle="--", alpha=0.3, linewidth=0.5)
    for n in magic_N:
        if n <= df["N"].max():
            ax.axvline(x=n, color="black", linestyle="--", alpha=0.3, linewidth=0.5)

    ax.set_xlabel("Neutron Number N", fontsize=12)
    ax.set_ylabel("Proton Number Z", fontsize=12)
    ax.set_title("FRDM(2012): Ground-State Quadrupole Deformation β₂", fontsize=14)

    # Add annotations for regions
    ax.annotate("Rare earths\n(deformed)", xy=(95, 65), fontsize=9, ha="center")
    ax.annotate("Actinides\n(deformed)", xy=(145, 92), fontsize=9, ha="center")
    ax.annotate("Spherical\n(magic)", xy=(126, 82), fontsize=9, ha="center",
                arrowprops=dict(arrowstyle="->", color="gray"))

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig1_deformation_chart.png", dpi=150)
    plt.savefig(OUTPUT_DIR / "fig1_deformation_chart.pdf")
    print(f"Saved: fig1_deformation_chart.png")
    return fig


def figure2_mass_residuals(df):
    """
    Figure: Mass model residuals (Experiment - Theory).

    Shows the accuracy of FRDM(2012) predictions compared to experimental masses.
    """
    # Filter to nuclides with both exp and theory
    compared = df[df["has_experimental"] & df["mass_excess_exp_keV"].notna()].copy()
    compared["residual_MeV"] = compared["exp_minus_th_keV"] / 1000

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Panel A: Residuals vs A
    ax = axes[0, 0]
    ax.scatter(compared["A"], compared["residual_MeV"], s=5, alpha=0.5)
    ax.axhline(y=0, color="red", linestyle="-", linewidth=1)
    ax.axhline(y=0.56, color="red", linestyle="--", alpha=0.5, label="±σ = 0.56 MeV")
    ax.axhline(y=-0.56, color="red", linestyle="--", alpha=0.5)
    ax.set_xlabel("Mass Number A")
    ax.set_ylabel("M_exp - M_th (MeV)")
    ax.set_title("A) Mass Residuals vs Mass Number")
    ax.set_ylim(-3, 3)
    ax.legend()

    # Panel B: Histogram of residuals
    ax = axes[0, 1]
    ax.hist(compared["residual_MeV"], bins=50, edgecolor="black", alpha=0.7)
    rms = np.sqrt((compared["residual_MeV"] ** 2).mean())
    mean = compared["residual_MeV"].mean()
    ax.axvline(x=mean, color="red", linestyle="-", label=f"Mean: {mean:.3f} MeV")
    ax.axvline(x=0, color="black", linestyle="--")
    ax.set_xlabel("M_exp - M_th (MeV)")
    ax.set_ylabel("Count")
    ax.set_title(f"B) Residual Distribution (RMS = {rms:.3f} MeV)")
    ax.legend()

    # Panel C: Residuals on nuclear chart
    ax = axes[1, 0]
    scatter = ax.scatter(
        compared["N"], compared["Z"],
        c=compared["residual_MeV"],
        cmap="RdBu_r",
        s=10,
        vmin=-1.5,
        vmax=1.5,
        marker="s"
    )
    plt.colorbar(scatter, ax=ax, label="M_exp - M_th (MeV)")
    ax.set_xlabel("Neutron Number N")
    ax.set_ylabel("Proton Number Z")
    ax.set_title("C) Residuals on Nuclear Chart")

    # Panel D: Residuals vs N-Z
    ax = axes[1, 1]
    compared["NmZ"] = compared["N"] - compared["Z"]
    ax.scatter(compared["NmZ"], compared["residual_MeV"], s=5, alpha=0.5)
    ax.axhline(y=0, color="red", linestyle="-")
    ax.set_xlabel("N - Z (neutron excess)")
    ax.set_ylabel("M_exp - M_th (MeV)")
    ax.set_title("D) Residuals vs Neutron Excess")
    ax.set_ylim(-3, 3)

    plt.suptitle("FRDM(2012): Mass Model Accuracy", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig2_mass_residuals.png", dpi=150)
    plt.savefig(OUTPUT_DIR / "fig2_mass_residuals.pdf")
    print(f"Saved: fig2_mass_residuals.png")

    # Print statistics
    print(f"\nMass Model Statistics (n={len(compared)} nuclides):")
    print(f"  Mean residual: {mean:.4f} MeV")
    print(f"  RMS deviation: {rms:.4f} MeV")
    print(f"  Std deviation: {compared['residual_MeV'].std():.4f} MeV")

    return fig


def figure3_shell_effects(df):
    """
    Figure: Shell and microscopic corrections.

    Visualizes the shell-plus-pairing corrections that are
    key to FRDM's accuracy.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Panel A: Shell corrections on chart
    ax = axes[0]
    valid = df[df["shell_pairing_MeV"].notna()]
    scatter = ax.scatter(
        valid["N"], valid["Z"],
        c=valid["shell_pairing_MeV"],
        cmap="RdBu_r",
        s=8,
        vmin=-8,
        vmax=4,
        marker="s"
    )
    cbar = plt.colorbar(scatter, ax=ax, label="E_shell+pairing (MeV)")

    # Mark magic numbers
    for z in [20, 28, 50, 82]:
        ax.axhline(y=z, color="black", linestyle="--", alpha=0.3, linewidth=0.5)
    for n in [20, 28, 50, 82, 126]:
        ax.axvline(x=n, color="black", linestyle="--", alpha=0.3, linewidth=0.5)

    ax.set_xlabel("Neutron Number N")
    ax.set_ylabel("Proton Number Z")
    ax.set_title("A) Shell-Plus-Pairing Correction")

    # Panel B: Shell correction vs N for specific Z
    ax = axes[1]
    for z in [50, 82]:  # Sn and Pb isotope chains
        chain = df[df["Z"] == z].sort_values("N")
        if len(chain) > 0:
            ax.plot(chain["N"], chain["shell_pairing_MeV"],
                   "o-", markersize=4, label=f"Z={z}")

    ax.axhline(y=0, color="black", linestyle="--", alpha=0.5)
    ax.axvline(x=50, color="gray", linestyle=":", alpha=0.5, label="N=50")
    ax.axvline(x=82, color="gray", linestyle=":", alpha=0.5, label="N=82")
    ax.axvline(x=126, color="gray", linestyle=":", alpha=0.5, label="N=126")

    ax.set_xlabel("Neutron Number N")
    ax.set_ylabel("E_shell+pairing (MeV)")
    ax.set_title("B) Shell Effects in Sn and Pb Isotopes")
    ax.legend()
    ax.set_xlim(40, 180)

    plt.suptitle("FRDM(2012): Shell Effects", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig3_shell_effects.png", dpi=150)
    plt.savefig(OUTPUT_DIR / "fig3_shell_effects.pdf")
    print(f"Saved: fig3_shell_effects.png")
    return fig


def figure4_binding_energy(df):
    """
    Figure: Binding energy per nucleon.

    Shows the famous curve peaking near Fe-56.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Panel A: B/A vs A
    ax = axes[0]
    valid = df[df["binding_per_A_MeV"].notna() & (df["binding_per_A_MeV"] > 0)]
    ax.scatter(valid["A"], valid["binding_per_A_MeV"], s=3, alpha=0.5)

    # Highlight Fe-56
    fe56 = valid[(valid["Z"] == 26) & (valid["N"] == 30)]
    if len(fe56) > 0:
        ax.scatter(fe56["A"], fe56["binding_per_A_MeV"],
                  s=100, c="red", marker="*", zorder=5, label="Fe-56")

    ax.set_xlabel("Mass Number A")
    ax.set_ylabel("Binding Energy per Nucleon (MeV)")
    ax.set_title("A) Binding Energy Curve")
    ax.legend()
    ax.set_ylim(0, 9)

    # Panel B: Stability valley (B/A on Z-N plane)
    ax = axes[1]
    scatter = ax.scatter(
        valid["N"], valid["Z"],
        c=valid["binding_per_A_MeV"],
        cmap="plasma",
        s=8,
        vmin=6,
        vmax=8.8,
        marker="s"
    )
    plt.colorbar(scatter, ax=ax, label="B/A (MeV)")
    ax.set_xlabel("Neutron Number N")
    ax.set_ylabel("Proton Number Z")
    ax.set_title("B) Binding Energy per Nucleon on Nuclear Chart")

    plt.suptitle("FRDM(2012): Nuclear Binding", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig4_binding_energy.png", dpi=150)
    plt.savefig(OUTPUT_DIR / "fig4_binding_energy.pdf")
    print(f"Saved: fig4_binding_energy.png")
    return fig


def figure5_separation_energies(df, db):
    """
    Figure: Two-neutron separation energies S2n.

    S2n shows shell closures clearly as sudden drops.
    """
    # Calculate S2n = M(Z, N-2) - M(Z, N) + 2*M_n
    # In terms of binding energy: S2n = B(Z,N) - B(Z,N-2)

    # Get binding energies
    nuclides = df[["Z", "N", "A", "binding_total_th_MeV"]].copy()
    nuclides = nuclides.rename(columns={"binding_total_th_MeV": "B"})

    # Create shifted dataframe for N-2
    shifted = nuclides.copy()
    shifted["N"] = shifted["N"] + 2
    shifted = shifted.rename(columns={"B": "B_Nm2"})

    # Merge to calculate S2n
    merged = pd.merge(nuclides, shifted[["Z", "N", "B_Nm2"]], on=["Z", "N"], how="inner")
    merged["S2n"] = merged["B"] - merged["B_Nm2"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Panel A: S2n on nuclear chart
    ax = axes[0]
    valid = merged[(merged["S2n"] > 0) & (merged["S2n"] < 30)]
    scatter = ax.scatter(
        valid["N"], valid["Z"],
        c=valid["S2n"],
        cmap="viridis",
        s=8,
        vmin=0,
        vmax=25,
        marker="s"
    )
    plt.colorbar(scatter, ax=ax, label="S₂ₙ (MeV)")

    # Mark magic numbers
    for n in [50, 82, 126]:
        ax.axvline(x=n, color="red", linestyle="--", alpha=0.7, linewidth=1)

    ax.set_xlabel("Neutron Number N")
    ax.set_ylabel("Proton Number Z")
    ax.set_title("A) Two-Neutron Separation Energy S₂ₙ")

    # Panel B: S2n vs N for specific Z
    ax = axes[1]
    for z in [50, 82]:  # Sn and Pb
        chain = merged[merged["Z"] == z].sort_values("N")
        if len(chain) > 0:
            ax.plot(chain["N"], chain["S2n"], "o-", markersize=4, label=f"Z={z}")

    # Mark shell closures
    for n in [50, 82, 126]:
        ax.axvline(x=n, color="gray", linestyle="--", alpha=0.5)

    ax.set_xlabel("Neutron Number N")
    ax.set_ylabel("S₂ₙ (MeV)")
    ax.set_title("B) S₂ₙ for Sn and Pb Isotope Chains")
    ax.legend()
    ax.set_xlim(40, 180)
    ax.set_ylim(0, 25)

    plt.suptitle("FRDM(2012): Two-Neutron Separation Energies", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig5_separation_energies.png", dpi=150)
    plt.savefig(OUTPUT_DIR / "fig5_separation_energies.pdf")
    print(f"Saved: fig5_separation_energies.png")
    return fig


def create_summary_table(df):
    """Create summary statistics table."""
    print("\n" + "=" * 70)
    print("FRDM(2012) DATA SUMMARY")
    print("=" * 70)

    print(f"\nTotal nuclides: {len(df)}")
    print(f"Z range: {df['Z'].min()} - {df['Z'].max()}")
    print(f"N range: {df['N'].min()} - {df['N'].max()}")
    print(f"A range: {df['A'].min()} - {df['A'].max()}")

    # Deformation statistics
    print("\nDeformation Statistics (β₂):")
    print(f"  Spherical (|β₂| < 0.05): {(df['beta2'].abs() < 0.05).sum()} nuclides")
    print(f"  Oblate (β₂ < -0.15): {(df['beta2'] < -0.15).sum()} nuclides")
    print(f"  Prolate (β₂ > 0.15): {(df['beta2'] > 0.15).sum()} nuclides")
    print(f"  Most oblate: β₂ = {df['beta2'].min():.3f}")
    print(f"  Most prolate: β₂ = {df['beta2'].max():.3f}")

    # Comparison with experiment
    compared = df[df["has_experimental"]]
    if len(compared) > 0:
        residuals = compared["exp_minus_th_keV"] / 1000
        print(f"\nComparison with Experiment (n={len(compared)}):")
        print(f"  Mean deviation: {residuals.mean():.4f} MeV")
        print(f"  RMS deviation: {np.sqrt((residuals**2).mean()):.4f} MeV")
        print(f"  Max deviation: {residuals.abs().max():.2f} MeV")

    return df.describe()


def main():
    print("Loading nuclear mass data...")
    df, db = load_data()

    print(f"Loaded {len(df)} nuclides")
    print(f"Saving figures to {OUTPUT_DIR}/")
    print()

    # Generate all figures
    figure1_nuclear_chart_deformation(df)
    figure2_mass_residuals(df)
    figure3_shell_effects(df)
    figure4_binding_energy(df)
    figure5_separation_energies(df, db)

    # Summary table
    create_summary_table(df)

    print("\n" + "=" * 70)
    print(f"All figures saved to {OUTPUT_DIR}/")
    print("=" * 70)

    db.close()


if __name__ == "__main__":
    main()
