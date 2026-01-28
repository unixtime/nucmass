"""
Plotting utilities for nuclear mass data visualization.

This module provides convenient functions for creating common nuclear physics plots.
All functions return matplotlib Figure objects for further customization.

Example:
    >>> from nucmass import NuclearDatabase
    >>> from nucmass.plotting import plot_chart, plot_isotope_chain
    >>>
    >>> db = NuclearDatabase()
    >>> fig = plot_chart(db, color_by='beta2')
    >>> fig.savefig('nuclear_chart.png')
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from matplotlib.axes import Axes
    from .database import NuclearDatabase


# Set default font for better Unicode support
plt.rcParams["font.family"] = "DejaVu Sans"


def plot_chart(
    db: "NuclearDatabase",
    color_by: Literal["beta2", "mass_excess", "shell_pairing", "binding_per_A"] = "beta2",
    cmap: str | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
    figsize: tuple[float, float] = (14, 10),
    title: str | None = None,
    show_magic: bool = True,
    marker_size: float = 8,
    ax: Optional["Axes"] = None,
) -> "Figure":
    """
    Plot the nuclear chart (Segrè chart) colored by a property.

    Args:
        db: NuclearDatabase instance.
        color_by: Property to color by. Options:
            - "beta2": Quadrupole deformation (default)
            - "mass_excess": Mass excess (experimental if available, else theoretical)
            - "shell_pairing": Shell-plus-pairing correction
            - "binding_per_A": Binding energy per nucleon
        cmap: Matplotlib colormap name. Default depends on color_by.
        vmin: Minimum value for color scale. Auto-determined if None.
        vmax: Maximum value for color scale. Auto-determined if None.
        figsize: Figure size in inches.
        title: Plot title. Auto-generated if None.
        show_magic: Whether to show magic number lines.
        marker_size: Size of the markers.
        ax: Optional existing axes to plot on.

    Returns:
        matplotlib Figure object.

    Example:
        >>> db = NuclearDatabase()
        >>> fig = plot_chart(db, color_by='beta2')
        >>> fig.savefig('deformation_chart.png', dpi=150)
    """
    # Get all nuclides with theoretical data (for deformation) or all data
    if color_by in ("beta2", "shell_pairing"):
        df = db.query("SELECT * FROM nuclides WHERE has_theoretical")
    else:
        df = db.query("SELECT * FROM nuclides")

    # Determine color values and defaults
    if color_by == "beta2":
        color_values = df["beta2"]
        default_cmap = "RdBu_r"
        default_vmin, default_vmax = -0.4, 0.4
        colorbar_label = "β₂ (quadrupole deformation)"
        default_title = "Nuclear Chart: Ground-State Deformation"
    elif color_by == "mass_excess":
        # Use experimental if available, else theoretical
        color_values = df["mass_excess_exp_keV"].fillna(df["mass_excess_th_keV"]) / 1000
        default_cmap = "viridis"
        default_vmin, default_vmax = None, None
        colorbar_label = "Mass Excess (MeV)"
        default_title = "Nuclear Chart: Mass Excess"
    elif color_by == "shell_pairing":
        color_values = df["shell_pairing_MeV"]
        default_cmap = "RdBu"
        default_vmin, default_vmax = -15, 5
        colorbar_label = "Shell+Pairing Correction (MeV)"
        default_title = "Nuclear Chart: Shell Effects"
    elif color_by == "binding_per_A":
        color_values = df["binding_per_A_exp_keV"] / 1000
        default_cmap = "plasma"
        default_vmin, default_vmax = 0, 9
        colorbar_label = "Binding Energy per Nucleon (MeV)"
        default_title = "Nuclear Chart: Binding Energy"
    else:
        raise ValueError(f"Unknown color_by: {color_by}")

    # Apply defaults
    cmap = cmap or default_cmap
    vmin = vmin if vmin is not None else default_vmin
    vmax = vmax if vmax is not None else default_vmax
    title = title or default_title

    # Create figure
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.get_figure()

    # Plot nuclides
    scatter = ax.scatter(
        df["N"], df["Z"],
        c=color_values,
        cmap=cmap,
        s=marker_size,
        vmin=vmin,
        vmax=vmax,
        edgecolors="none",
        rasterized=True,
    )

    # Colorbar
    cbar = plt.colorbar(scatter, ax=ax, shrink=0.8)
    cbar.set_label(colorbar_label)

    # Magic number lines
    if show_magic:
        magic_n = [8, 20, 28, 50, 82, 126]
        magic_z = [8, 20, 28, 50, 82]

        for n in magic_n:
            ax.axvline(n, color="gray", linestyle="--", alpha=0.5, linewidth=0.5)
        for z in magic_z:
            ax.axhline(z, color="gray", linestyle="--", alpha=0.5, linewidth=0.5)

    # Labels and title
    ax.set_xlabel("Neutron Number (N)")
    ax.set_ylabel("Proton Number (Z)")
    ax.set_title(title)

    # Set limits with small padding
    ax.set_xlim(df["N"].min() - 2, df["N"].max() + 2)
    ax.set_ylim(df["Z"].min() - 2, df["Z"].max() + 2)

    plt.tight_layout()
    return fig


def plot_isotope_chain(
    db: "NuclearDatabase",
    z: int,
    y: Literal["mass_excess", "S_n", "S_2n", "S_p", "S_2p", "beta2"] = "mass_excess",
    show_experimental: bool = True,
    show_theoretical: bool = True,
    figsize: tuple[float, float] = (10, 6),
    title: str | None = None,
    ax: Optional["Axes"] = None,
) -> "Figure":
    """
    Plot a property along an isotope chain (fixed Z, varying N).

    Args:
        db: NuclearDatabase instance.
        z: Proton number of the element.
        y: Property to plot on y-axis. Options:
            - "mass_excess": Mass excess in MeV
            - "S_n": One-neutron separation energy
            - "S_2n": Two-neutron separation energy
            - "S_p": One-proton separation energy
            - "S_2p": Two-proton separation energy
            - "beta2": Quadrupole deformation
        show_experimental: Whether to show experimental data points.
        show_theoretical: Whether to show theoretical predictions.
        figsize: Figure size.
        title: Plot title.
        ax: Optional existing axes.

    Returns:
        matplotlib Figure object.

    Example:
        >>> db = NuclearDatabase()
        >>> fig = plot_isotope_chain(db, z=50, y='S_2n')  # Sn isotopes
        >>> fig.savefig('sn_s2n.png')
    """
    # Import here to avoid circular imports
    from .cli import get_element_symbol

    df = db.get_isotopes(z)
    element = get_element_symbol(z)

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.get_figure()

    # Get y values based on selection
    if y == "mass_excess":
        if show_experimental:
            exp_mask = df["mass_excess_exp_keV"].notna()
            ax.plot(df.loc[exp_mask, "N"], df.loc[exp_mask, "mass_excess_exp_keV"] / 1000,
                    "o-", label="Experimental", markersize=6)
        if show_theoretical:
            th_mask = df["mass_excess_th_keV"].notna()
            ax.plot(df.loc[th_mask, "N"], df.loc[th_mask, "mass_excess_th_keV"] / 1000,
                    "s--", label="FRDM2012", markersize=4, alpha=0.7)
        ylabel = "Mass Excess (MeV)"
        default_title = f"{element} Isotopes: Mass Excess"

    elif y in ("S_n", "S_2n", "S_p", "S_2p"):
        # Calculate separation energies using batch query (avoids N+1 query pattern)
        n_values = df["N"].values

        # Physical constants (keV)
        M_n = 8071.32   # neutron mass excess
        M_H = 7288.97   # hydrogen mass excess

        # Batch fetch all needed masses in a single query
        # For S_n/S_2n we need masses at N and N-1/N-2
        # For S_p/S_2p we need masses at Z and Z-1/Z-2
        if y in ("S_n", "S_2n"):
            # Get all masses for this Z (parent isotopes and daughters)
            masses_df = db.conn.execute(
                """SELECT N, mass_excess_exp_keV, mass_excess_th_keV
                   FROM nuclides WHERE Z = ? ORDER BY N""", [z]
            ).df()
            # Create lookup dict: N -> mass_excess (prefer experimental)
            mass_lookup = {}
            for _, row in masses_df.iterrows():
                n_val = int(row["N"])
                if pd.notna(row["mass_excess_exp_keV"]):
                    mass_lookup[n_val] = float(row["mass_excess_exp_keV"])
                elif pd.notna(row["mass_excess_th_keV"]):
                    mass_lookup[n_val] = float(row["mass_excess_th_keV"])

            # Compute separation energies
            s_values = []
            delta_n = 1 if y == "S_n" else 2
            for n in n_values:
                n_int = int(n)
                if n_int in mass_lookup and (n_int - delta_n) in mass_lookup:
                    m_parent = mass_lookup[n_int]
                    m_daughter = mass_lookup[n_int - delta_n]
                    s = (m_daughter + delta_n * M_n - m_parent) / 1000.0
                    s_values.append(s)
                else:
                    s_values.append(None)
        else:
            # S_p or S_2p: need masses for Z-1 or Z-2
            delta_z = 1 if y == "S_p" else 2
            # Batch fetch masses for Z and Z-delta_z
            masses_df = db.conn.execute(
                """SELECT Z, N, mass_excess_exp_keV, mass_excess_th_keV
                   FROM nuclides WHERE Z IN (?, ?) ORDER BY N""",
                [z, z - delta_z]
            ).df()
            # Create lookup dict: (Z, N) -> mass_excess
            mass_lookup = {}
            for _, row in masses_df.iterrows():
                key = (int(row["Z"]), int(row["N"]))
                if pd.notna(row["mass_excess_exp_keV"]):
                    mass_lookup[key] = float(row["mass_excess_exp_keV"])
                elif pd.notna(row["mass_excess_th_keV"]):
                    mass_lookup[key] = float(row["mass_excess_th_keV"])

            # Compute separation energies
            s_values = []
            for n in n_values:
                n_int = int(n)
                parent_key = (z, n_int)
                daughter_key = (z - delta_z, n_int)
                if parent_key in mass_lookup and daughter_key in mass_lookup:
                    m_parent = mass_lookup[parent_key]
                    m_daughter = mass_lookup[daughter_key]
                    s = (m_daughter + delta_z * M_H - m_parent) / 1000.0
                    s_values.append(s)
                else:
                    s_values.append(None)

        # Convert to array and mask None values
        s_array = np.array([s if s is not None else np.nan for s in s_values])
        valid = ~np.isnan(s_array)

        ax.plot(n_values[valid], s_array[valid], "o-", markersize=6)

        ylabel_map = {
            "S_n": "One-Neutron Separation Energy (MeV)",
            "S_2n": "Two-Neutron Separation Energy (MeV)",
            "S_p": "One-Proton Separation Energy (MeV)",
            "S_2p": "Two-Proton Separation Energy (MeV)",
        }
        ylabel = ylabel_map[y]
        default_title = f"{element} Isotopes: {y.replace('_', ' ')}"

        # Add zero line for separation energies
        ax.axhline(0, color="gray", linestyle="--", alpha=0.5)

    elif y == "beta2":
        mask = df["beta2"].notna()
        ax.plot(df.loc[mask, "N"], df.loc[mask, "beta2"], "o-", markersize=6)
        ylabel = "β₂ (Quadrupole Deformation)"
        default_title = f"{element} Isotopes: Deformation"

        # Add zero line
        ax.axhline(0, color="gray", linestyle="--", alpha=0.5)

    else:
        raise ValueError(f"Unknown y: {y}")

    # Mark magic neutron numbers
    magic_n = [8, 20, 28, 50, 82, 126]
    n_range = df["N"].values
    for magic in magic_n:
        if n_range.min() <= magic <= n_range.max():
            ax.axvline(magic, color="red", linestyle=":", alpha=0.5, label=f"N={magic}" if magic == magic_n[0] else "")

    ax.set_xlabel("Neutron Number (N)")
    ax.set_ylabel(ylabel)
    ax.set_title(title or default_title)

    if y == "mass_excess" and (show_experimental or show_theoretical):
        ax.legend()

    plt.tight_layout()
    return fig


def plot_separation_energies(
    db: "NuclearDatabase",
    quantity: Literal["S_2n", "S_2p"] = "S_2n",
    figsize: tuple[float, float] = (14, 10),
    cmap: str = "viridis",
    vmin: float | None = None,
    vmax: float | None = None,
    title: str | None = None,
    ax: Optional["Axes"] = None,
) -> "Figure":
    """
    Plot separation energies on the nuclear chart.

    Two-neutron and two-proton separation energies are particularly useful
    for identifying shell closures.

    Args:
        db: NuclearDatabase instance.
        quantity: Which separation energy to plot ("S_2n" or "S_2p").
        figsize: Figure size.
        cmap: Colormap name.
        vmin: Minimum value for color scale.
        vmax: Maximum value for color scale.
        title: Plot title.
        ax: Optional existing axes.

    Returns:
        matplotlib Figure object.

    Example:
        >>> db = NuclearDatabase()
        >>> fig = plot_separation_energies(db, quantity='S_2n')
        >>> fig.savefig('s2n_chart.png', dpi=150)
    """
    # Batch calculation of separation energies (avoids N+1 query pattern)
    # Fetch all masses in a single query
    masses_df = db.query("""
        SELECT Z, N, mass_excess_exp_keV, mass_excess_th_keV
        FROM nuclides WHERE has_experimental OR has_theoretical
    """)

    # Create lookup dict: (Z, N) -> mass_excess (prefer experimental)
    mass_lookup = {}
    for _, row in masses_df.iterrows():
        key = (int(row["Z"]), int(row["N"]))
        if pd.notna(row["mass_excess_exp_keV"]):
            mass_lookup[key] = float(row["mass_excess_exp_keV"])
        elif pd.notna(row["mass_excess_th_keV"]):
            mass_lookup[key] = float(row["mass_excess_th_keV"])

    # Physical constants (keV)
    M_n = 8071.32   # neutron mass excess
    M_H = 7288.97   # hydrogen mass excess

    # Calculate separation energies for all nuclides
    z_list = []
    n_list = []
    s_list = []

    for (z, n), m_parent in mass_lookup.items():
        if quantity == "S_2n":
            daughter_key = (z, n - 2)
            if n < 2 or daughter_key not in mass_lookup:
                continue
            m_daughter = mass_lookup[daughter_key]
            s = (m_daughter + 2 * M_n - m_parent) / 1000.0
        elif quantity == "S_2p":
            daughter_key = (z - 2, n)
            if z < 2 or daughter_key not in mass_lookup:
                continue
            m_daughter = mass_lookup[daughter_key]
            s = (m_daughter + 2 * M_H - m_parent) / 1000.0
        else:
            raise ValueError(f"Unknown quantity: {quantity}")

        z_list.append(z)
        n_list.append(n)
        s_list.append(s)

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.get_figure()

    # Set defaults
    if vmin is None:
        vmin = 0
    if vmax is None:
        vmax = 30

    scatter = ax.scatter(
        n_list, z_list,
        c=s_list,
        cmap=cmap,
        s=8,
        vmin=vmin,
        vmax=vmax,
        edgecolors="none",
        rasterized=True,
    )

    cbar = plt.colorbar(scatter, ax=ax, shrink=0.8)
    label_map = {"S_2n": "S₂ₙ (MeV)", "S_2p": "S₂ₚ (MeV)"}
    cbar.set_label(label_map.get(quantity, quantity))

    # Magic number lines
    magic_n = [8, 20, 28, 50, 82, 126]
    magic_z = [8, 20, 28, 50, 82]

    for n in magic_n:
        ax.axvline(n, color="red", linestyle="--", alpha=0.7, linewidth=1)
    for z in magic_z:
        ax.axhline(z, color="red", linestyle="--", alpha=0.7, linewidth=1)

    ax.set_xlabel("Neutron Number (N)")
    ax.set_ylabel("Proton Number (Z)")

    title_map = {
        "S_2n": "Two-Neutron Separation Energy S₂ₙ",
        "S_2p": "Two-Proton Separation Energy S₂ₚ",
    }
    ax.set_title(title or title_map.get(quantity, quantity))

    plt.tight_layout()
    return fig


def plot_mass_residuals(
    db: "NuclearDatabase",
    figsize: tuple[float, float] = (12, 8),
    max_residual_MeV: float = 5.0,
    ax: Optional["Axes"] = None,
) -> "Figure":
    """
    Plot residuals between experimental and theoretical masses.

    Creates a 2-panel figure:
    - Top: Histogram of residuals
    - Bottom: Residuals on the nuclear chart

    Args:
        db: NuclearDatabase instance.
        figsize: Figure size.
        max_residual_MeV: Maximum residual to show (filters outliers).
        ax: Not used (creates multi-panel figure).

    Returns:
        matplotlib Figure object.

    Example:
        >>> db = NuclearDatabase()
        >>> fig = plot_mass_residuals(db)
        >>> fig.savefig('mass_accuracy.png', dpi=150)
    """
    comparison = db.compare_masses(max_diff_keV=max_residual_MeV * 1000)
    residuals_MeV = comparison["exp_minus_th_keV"] / 1000

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, height_ratios=[1, 2])

    # Top panel: Histogram
    ax1.hist(residuals_MeV, bins=50, edgecolor="black", alpha=0.7)
    ax1.axvline(0, color="red", linestyle="--", label="Perfect agreement")
    ax1.axvline(residuals_MeV.mean(), color="green", linestyle="-",
                label=f"Mean = {residuals_MeV.mean():.3f} MeV")

    rms = np.sqrt((residuals_MeV**2).mean())
    ax1.set_xlabel("M_exp - M_th (MeV)")
    ax1.set_ylabel("Count")
    ax1.set_title(f"Mass Model Accuracy (n={len(comparison)}, RMS={rms:.3f} MeV)")
    ax1.legend()

    # Bottom panel: Chart view
    scatter = ax2.scatter(
        comparison["N"], comparison["Z"],
        c=residuals_MeV,
        cmap="RdBu_r",
        s=8,
        vmin=-2,
        vmax=2,
        edgecolors="none",
        rasterized=True,
    )
    cbar = plt.colorbar(scatter, ax=ax2, shrink=0.8)
    cbar.set_label("M_exp - M_th (MeV)")

    ax2.set_xlabel("Neutron Number (N)")
    ax2.set_ylabel("Proton Number (Z)")
    ax2.set_title("Residuals on Nuclear Chart")

    plt.tight_layout()
    return fig


def plot_binding_energy_curve(
    db: "NuclearDatabase",
    figsize: tuple[float, float] = (10, 6),
    highlight_fe56: bool = True,
    ax: Optional["Axes"] = None,
) -> "Figure":
    """
    Plot the classic binding energy per nucleon vs mass number curve.

    This is one of the most famous plots in nuclear physics, showing
    why iron-56 is at the peak of nuclear stability.

    Args:
        db: NuclearDatabase instance.
        figsize: Figure size.
        highlight_fe56: Whether to highlight Iron-56 (peak of curve).
        ax: Optional existing axes.

    Returns:
        matplotlib Figure object.

    Example:
        >>> db = NuclearDatabase()
        >>> fig = plot_binding_energy_curve(db)
        >>> fig.savefig('binding_curve.png', dpi=150)
    """
    df = db.query("""
        SELECT A, binding_per_A_exp_keV
        FROM nuclides
        WHERE binding_per_A_exp_keV IS NOT NULL
        ORDER BY A
    """)

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.get_figure()

    # Plot all data points
    ax.scatter(
        df["A"], df["binding_per_A_exp_keV"] / 1000,
        s=3, alpha=0.5, label="All nuclides"
    )

    # Highlight Fe-56 if requested
    if highlight_fe56:
        fe56 = db.get_nuclide_or_none(26, 30)
        if fe56 is not None and pd.notna(fe56.get("binding_per_A_exp_keV")):
            ax.scatter(
                [56], [fe56["binding_per_A_exp_keV"] / 1000],
                s=100, c="red", marker="*", zorder=5,
                label="Fe-56 (most tightly bound)"
            )
            ax.annotate(
                "Fe-56",
                xy=(56, fe56["binding_per_A_exp_keV"] / 1000),
                xytext=(70, fe56["binding_per_A_exp_keV"] / 1000 + 0.3),
                arrowprops=dict(arrowstyle="->", color="red"),
                fontsize=10,
            )

    ax.set_xlabel("Mass Number (A)")
    ax.set_ylabel("Binding Energy per Nucleon (MeV)")
    ax.set_title("Nuclear Binding Energy Curve")
    ax.set_xlim(0, df["A"].max() + 10)
    ax.set_ylim(0, 9.5)
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig
