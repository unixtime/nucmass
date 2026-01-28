#!/usr/bin/env python3
"""
Interactive helper for extracting FRDM2012 data from PDF.

Since the FRDM2012 PDF varies in table layout, this script helps you:
1. Find which pages contain the mass table
2. Inspect sample pages to understand the structure
3. Extract with the correct page range

Usage:
    python scripts/inspect_frdm2012_pdf.py path/to/frdm2012.pdf
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nucmass.frdm2012 import FRDM2012Extractor, DATA_DIR


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nTo get the PDF, try one of these sources:")
        print("  1. arXiv: https://arxiv.org/abs/1508.06294 (click PDF)")
        print("  2. IHEP: http://hermes.ihep.su:8001/pool/mass/jou/frdm2012.pdf")
        print("  3. ScienceDirect with institutional access")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    extractor = FRDM2012Extractor(pdf_path)
    total_pages = extractor.get_page_count()

    print(f"PDF loaded: {pdf_path}")
    print(f"Total pages: {total_pages}")
    print()

    while True:
        print("=" * 50)
        print("Options:")
        print("  1. Inspect a specific page")
        print("  2. Search for table start (scan pages)")
        print("  3. Extract table with page range")
        print("  4. Quick extract (auto-detect, experimental)")
        print("  q. Quit")
        print()

        choice = input("Choice: ").strip().lower()

        if choice == "q":
            break

        elif choice == "1":
            try:
                page = int(input(f"Page number (1-{total_pages}): "))
                lines = int(input("Lines to show (default 30): ") or "30")
                extractor.inspect_page(page, show_lines=lines)
            except ValueError as e:
                print(f"Invalid input: {e}")

        elif choice == "2":
            print("\nScanning for pages with numeric data patterns...")
            print("Looking for rows with Z, N, A values...")

            import pdfplumber
            import re

            data_pattern = re.compile(r"^\s*\d+\s+\d+\s+\d+")
            found_pages = []

            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    lines = text.split("\n")
                    data_lines = sum(1 for line in lines if data_pattern.match(line))
                    if data_lines > 10:
                        found_pages.append((i + 1, data_lines))
                        if len(found_pages) <= 5:
                            print(f"  Page {i+1}: {data_lines} data rows")

            if found_pages:
                print(f"\nFound {len(found_pages)} pages with data")
                print(f"Table likely spans pages {found_pages[0][0]} to {found_pages[-1][0]}")
            else:
                print("No obvious data pages found. Try inspecting individual pages.")

        elif choice == "3":
            try:
                start = int(input("Start page: "))
                end = int(input("End page: "))
                print(f"\nExtracting pages {start}-{end}...")

                df = extractor.extract(start, end)
                print(f"\nExtracted {len(df)} rows")

                if len(df) > 0:
                    print("\nFirst 5 rows:")
                    print(df.head())

                    save = input("\nSave to CSV? (y/n): ").strip().lower()
                    if save == "y":
                        DATA_DIR.mkdir(parents=True, exist_ok=True)
                        output = DATA_DIR / "frdm2012_extracted.csv"
                        df.to_csv(output, index=False)
                        print(f"Saved to {output}")
            except ValueError as e:
                print(f"Invalid input: {e}")

        elif choice == "4":
            print("\nAttempting auto-detection (this may take a while)...")
            print("Trying text-based extraction on pages 50-250...")

            df = extractor.extract_text_based(50, min(250, total_pages))
            print(f"\nExtracted {len(df)} rows")

            if len(df) > 100:
                print("\nSample:")
                print(df.head(10))

                save = input("\nSave to CSV? (y/n): ").strip().lower()
                if save == "y":
                    DATA_DIR.mkdir(parents=True, exist_ok=True)
                    output = DATA_DIR / "frdm2012_extracted.csv"
                    df.to_csv(output, index=False)
                    print(f"Saved to {output}")
            else:
                print("Too few rows extracted. Try manual page range with option 3.")


if __name__ == "__main__":
    main()
