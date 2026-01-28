#!/usr/bin/env python3
"""
Download and process nuclear mass data.

This script:
1. Downloads AME2020 experimental mass data from ANL
2. Optionally extracts FRDM2012 theoretical masses from PDF

Usage:
    python scripts/download_nuclear_data.py
    python scripts/download_nuclear_data.py --frdm-pdf path/to/frdm2012.pdf
"""

import argparse
import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nucmass.ame2020 import AME2020Parser, download_ame2020

DATA_DIR = Path(__file__).parent.parent / "data"


def main():
    parser = argparse.ArgumentParser(description="Download nuclear mass data")
    parser.add_argument(
        "--frdm-pdf",
        type=Path,
        help="Path to FRDM2012 PDF for extraction",
    )
    parser.add_argument(
        "--frdm-start-page",
        type=int,
        default=68,
        help="Start page for FRDM2012 table (default: 68)",
    )
    parser.add_argument(
        "--frdm-end-page",
        type=int,
        default=233,
        help="End page for FRDM2012 table (default: 233)",
    )
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Download and parse AME2020
    print("=" * 60)
    print("AME2020 - Atomic Mass Evaluation 2020")
    print("=" * 60)

    ame_file = download_ame2020(DATA_DIR / "mass.mas20.txt")
    ame_parser = AME2020Parser(ame_file)
    ame_df = ame_parser.parse()

    print(f"\nParsed {len(ame_df)} nuclides from AME2020")
    print(f"Z range: {ame_df['Z'].min()} - {ame_df['Z'].max()}")
    print(f"N range: {ame_df['N'].min()} - {ame_df['N'].max()}")

    # Export to CSV
    ame_csv = DATA_DIR / "ame2020_masses.csv"
    ame_parser.to_csv(ame_csv)

    # Show sample data
    print("\nSample: Fe-56 (Z=26, N=30)")
    fe56 = ame_parser.get_nuclide(z=26, n=30)
    if fe56 is not None:
        print(f"  Mass excess: {fe56['Mass_excess_keV']:.3f} keV")
        print(f"  Binding energy/A: {fe56['Binding_energy_per_A_keV']:.3f} keV")

    # Extract FRDM2012 if PDF provided
    if args.frdm_pdf:
        print("\n" + "=" * 60)
        print("FRDM2012 - Finite Range Droplet Model 2012")
        print("=" * 60)

        from nucmass.frdm2012 import extract_frdm2012_from_pdf

        frdm_df = extract_frdm2012_from_pdf(
            args.frdm_pdf,
            start_page=args.frdm_start_page,
            end_page=args.frdm_end_page,
            output_csv=DATA_DIR / "frdm2012_masses.csv",
        )

        print(f"\nExtracted {len(frdm_df)} nuclides from FRDM2012")
        if len(frdm_df) > 0:
            print(f"Z range: {frdm_df['Z'].min()} - {frdm_df['Z'].max()}")

    print("\n" + "=" * 60)
    print("Data files saved to:", DATA_DIR)
    print("=" * 60)


if __name__ == "__main__":
    main()
