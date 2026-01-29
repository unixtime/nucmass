"""
Command-line interface for nucmass.

Provides easy access to nuclear mass data from the terminal.

Usage:
    nucmass lookup 26 30          # Get Fe-56 data
    nucmass isotopes 92           # List all uranium isotopes
    nucmass separation 26 30      # Calculate separation energies
    nucmass export -o masses.csv  # Export all data to CSV
    nucmass summary               # Show database summary
"""

from __future__ import annotations

import sys

import click
import pandas as pd

from .config import Config
from .database import NuclearDatabase, init_database, DB_PATH
from .exceptions import NuclideNotFoundError, InvalidNuclideError, DataFileNotFoundError

__all__ = [
    "cli",
]


def get_element_symbol(z: int) -> str:
    """
    Get element symbol from atomic number Z.

    Example:
        >>> get_element_symbol(26)
        'Fe'
        >>> get_element_symbol(92)
        'U'
    """
    return Config.get_element_symbol(z)


def format_nuclide_name(z: int, a: int) -> str:
    """
    Format nuclide name like 'Fe-56'.

    Example:
        >>> format_nuclide_name(26, 56)
        'Fe-56'
        >>> format_nuclide_name(92, 238)
        'U-238'
    """
    return f"{get_element_symbol(z)}-{a}"


def format_value(value: float | None, precision: int = 3, unit: str = "") -> str:
    """
    Format a numeric value with optional unit.

    Example:
        >>> format_value(123.456, precision=2, unit='keV')
        '123.46 keV'
        >>> format_value(None)
        'N/A'
    """
    if value is None or pd.isna(value):
        return "N/A"
    if unit:
        return f"{value:.{precision}f} {unit}"
    return f"{value:.{precision}f}"


def validate_output_path(path_str: str) -> bool:
    """
    Validate an output path to prevent path traversal attacks.

    Args:
        path_str: The path string to validate.

    Returns:
        True if path is safe, False otherwise.
    """
    from pathlib import Path

    path = Path(path_str)

    # Resolve to absolute path to detect traversal
    try:
        resolved = path.resolve()
    except (OSError, ValueError):
        return False

    # Check for path traversal attempts
    if '..' in path.parts:
        return False

    # Don't allow writing to system directories
    forbidden_prefixes = ['/etc', '/bin', '/sbin', '/usr', '/var', '/tmp/../']
    resolved_str = str(resolved)
    for prefix in forbidden_prefixes:
        if resolved_str.startswith(prefix):
            return False

    # Don't allow symlinks in the path that point outside current directory
    # (only check if path exists)
    if path.exists() and path.is_symlink():
        try:
            real_path = path.resolve(strict=True)
            cwd = Path.cwd().resolve()
            # Allow symlinks within the project or to data directories
            if not (str(real_path).startswith(str(cwd)) or
                    str(real_path).startswith(str(Path.home()))):
                return False
        except (OSError, ValueError):
            return False

    return True


def validate_input_path(path_str: str) -> bool:
    """
    Validate an input path for safe file reading.

    Args:
        path_str: The path string to validate.

    Returns:
        True if path is safe to read, False otherwise.
    """
    from pathlib import Path

    path = Path(path_str)

    # Check for path traversal attempts
    if '..' in path.parts:
        return False

    # Check if it's a symlink pointing to sensitive locations
    if path.is_symlink():
        try:
            real_path = path.resolve(strict=True)
            # Don't allow reading system files via symlinks
            sensitive_paths = ['/etc/passwd', '/etc/shadow', '/etc/hosts',
                              '.ssh', '.gnupg', '.aws', 'credentials']
            real_str = str(real_path)
            for sensitive in sensitive_paths:
                if sensitive in real_str:
                    return False
        except (OSError, ValueError):
            return False

    return True


@click.group()
@click.version_option(version="1.1.0", prog_name="nucmass")
def cli():
    """
    Nuclear Mass Data Toolkit - Access AME2020 and FRDM2012 data.

    Examples:

        nucmass lookup 26 30        # Look up Iron-56 (Z=26, N=30)

        nucmass isotopes 92         # List uranium isotopes

        nucmass separation 82 126   # Separation energies for Pb-208

        nucmass export -o data.csv  # Export all nuclides to CSV
    """
    pass


@cli.command()
@click.option('--rebuild', is_flag=True, help='Force rebuild even if database exists')
@click.option('--db-path', type=click.Path(), default=None, help='Custom database path')
def init(rebuild: bool, db_path: str | None):
    """
    Initialize or rebuild the nuclear mass database.

    This command creates the DuckDB database from the source CSV files.
    The database is created automatically on first use, but this command
    is useful for rebuilding after data updates or troubleshooting.

    Examples:

        nucmass init              # Initialize if not exists

        nucmass init --rebuild    # Force rebuild
    """
    from pathlib import Path

    if db_path:
        # Validate path to prevent path traversal attacks
        if not validate_output_path(db_path):
            click.echo("Error: Invalid database path (path traversal not allowed)", err=True)
            sys.exit(1)
        target_path = Path(db_path)
    else:
        target_path = DB_PATH

    if target_path.exists() and not rebuild:
        click.echo(f"Database already exists at {target_path}")
        click.echo("Use --rebuild to force recreation")

        # Show summary
        db = NuclearDatabase(target_path)
        stats = db.summary()
        click.echo("\nCurrent database contains:")
        click.echo(f"  {stats['total_nuclides']:,} nuclides")
        click.echo(f"  {stats['ame2020_count']:,} from AME2020")
        click.echo(f"  {stats['frdm2012_count']:,} from FRDM2012")
        if 'nubase2020_count' in stats:
            click.echo(f"  {stats['nubase2020_count']:,} from NUBASE2020")
        return

    if rebuild and target_path.exists():
        click.echo(f"Removing existing database: {target_path}")
        target_path.unlink()

    click.echo(f"Initializing database at {target_path}...")
    try:
        conn = init_database(target_path, show_progress=True)
        conn.close()
        click.echo("\nDatabase initialized successfully!")
    except DataFileNotFoundError as e:
        click.echo(f"\nError: {e}", err=True)
        click.echo("\nTo download the required data files, run:", err=True)
        click.echo("  python scripts/download_nuclear_data.py", err=True)
        sys.exit(1)
    except PermissionError as e:
        click.echo(f"\nPermission denied: {e}", err=True)
        click.echo("Check write permissions for the database directory.", err=True)
        sys.exit(1)
    except OSError as e:
        # Catches disk full, IO errors, etc.
        click.echo(f"\nFilesystem error: {e}", err=True)
        click.echo("Check disk space and file system health.", err=True)
        sys.exit(1)
    except MemoryError:
        click.echo("\nOut of memory while building database.", err=True)
        click.echo("Try closing other applications or using a machine with more RAM.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"\nUnexpected error initializing database: {type(e).__name__}: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('z', type=int)
@click.argument('n', type=int)
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
def lookup(z: int, n: int, output_json: bool):
    """
    Look up a specific nuclide by Z (protons) and N (neutrons).

    Examples:

        nucmass lookup 26 30   # Iron-56

        nucmass lookup 82 126  # Lead-208 (doubly magic)

        nucmass lookup 92 146  # Uranium-238
    """
    db = NuclearDatabase()

    try:
        nuclide = db.get_nuclide(z, n)
    except NuclideNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except InvalidNuclideError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    a = z + n
    name = format_nuclide_name(z, a)

    if output_json:
        import json
        data = nuclide.to_dict()
        # Convert numpy types to Python types
        for k, v in data.items():
            if pd.isna(v):
                data[k] = None
            elif hasattr(v, 'item'):
                data[k] = v.item()
        click.echo(json.dumps(data, indent=2))
    else:
        click.echo(f"\n{name} (Z={z}, N={n}, A={a})")
        click.echo("=" * 40)

        # Mass data
        click.echo("\nMass Excess:")
        if pd.notna(nuclide.get('mass_excess_exp_keV')):
            click.echo(f"  Experimental: {nuclide['mass_excess_exp_keV']:.1f} keV")
        if pd.notna(nuclide.get('mass_excess_th_keV')):
            click.echo(f"  Theoretical:  {nuclide['mass_excess_th_keV']:.1f} keV")
        if pd.notna(nuclide.get('exp_minus_th_keV')):
            click.echo(f"  Difference:   {nuclide['exp_minus_th_keV']:.1f} keV")

        # Deformation
        if pd.notna(nuclide.get('beta2')):
            click.echo("\nDeformation:")
            click.echo(f"  β₂ = {nuclide['beta2']:.3f}", nl=False)
            if abs(nuclide['beta2']) < 0.05:
                click.echo("  (spherical)")
            elif nuclide['beta2'] > 0:
                click.echo("  (prolate)")
            else:
                click.echo("  (oblate)")

            if pd.notna(nuclide.get('beta4')):
                click.echo(f"  β₄ = {nuclide['beta4']:.3f}")

        # Shell correction
        if pd.notna(nuclide.get('shell_pairing_MeV')):
            click.echo(f"\nShell+Pairing: {nuclide['shell_pairing_MeV']:.2f} MeV")

        # Data availability
        click.echo("\nData sources:", nl=False)
        sources = []
        if nuclide.get('has_experimental'):
            sources.append("AME2020")
        if nuclide.get('has_theoretical'):
            sources.append("FRDM2012")
        click.echo(f" {', '.join(sources)}")
        click.echo()


@cli.command()
@click.argument('z', type=int)
@click.option('--limit', '-n', default=50, help='Maximum number of isotopes to show')
@click.option('--format', 'fmt', type=click.Choice(['table', 'csv', 'json']),
              default='table', help='Output format')
def isotopes(z: int, limit: int, fmt: str):
    """
    List all isotopes of an element (same Z).

    Examples:

        nucmass isotopes 50         # Tin isotopes (most stable isotopes)

        nucmass isotopes 92 -n 10   # First 10 uranium isotopes

        nucmass isotopes 26 --format csv  # Iron isotopes as CSV
    """
    db = NuclearDatabase()

    try:
        df = db.get_isotopes(z)
    except InvalidNuclideError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if df.empty:
        click.echo(f"No isotopes found for Z={z}")
        sys.exit(1)

    element = get_element_symbol(z)
    click.echo(f"\n{element} isotopes (Z={z}): {len(df)} found\n")

    # Select columns for display
    display_cols = ['N', 'A', 'mass_excess_exp_keV', 'mass_excess_th_keV', 'beta2']
    df_display = df[display_cols].head(limit).copy()

    if fmt == 'csv':
        click.echo(df_display.to_csv(index=False))
    elif fmt == 'json':
        click.echo(df_display.to_json(orient='records', indent=2))
    else:
        # Table format
        df_display.columns = ['N', 'A', 'M_exp (keV)', 'M_th (keV)', 'β₂']
        click.echo(df_display.to_string(index=False, na_rep='---'))

    if len(df) > limit:
        click.echo(f"\n... and {len(df) - limit} more (use -n to show more)")


@cli.command()
@click.argument('n', type=int)
@click.option('--limit', '-n', default=50, help='Maximum number to show')
def isotones(n: int, limit: int):
    """
    List all isotones (same N, different Z).

    Examples:

        nucmass isotones 82   # N=82 magic number

        nucmass isotones 126  # N=126 magic number
    """
    db = NuclearDatabase()

    try:
        df = db.get_isotones(n)
    except InvalidNuclideError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if df.empty:
        click.echo(f"No isotones found for N={n}")
        sys.exit(1)

    click.echo(f"\nN={n} isotones: {len(df)} found\n")

    display_cols = ['Z', 'Element', 'A', 'mass_excess_exp_keV', 'beta2']
    df_display = df[display_cols].head(limit).copy()
    df_display.columns = ['Z', 'El', 'A', 'M_exp (keV)', 'β₂']
    click.echo(df_display.to_string(index=False, na_rep='---'))

    if len(df) > limit:
        click.echo(f"\n... and {len(df) - limit} more")


@cli.command()
@click.argument('z', type=int)
@click.argument('n', type=int)
def separation(z: int, n: int):
    """
    Calculate separation energies for a nuclide.

    Shows S_n, S_p, S_2n, S_2p, and S_α (alpha) separation energies.

    Examples:

        nucmass separation 26 30   # Fe-56 separation energies

        nucmass separation 82 126  # Pb-208 (doubly magic)
    """
    db = NuclearDatabase()

    # First check the nuclide exists
    try:
        db.get_nuclide(z, n)
    except (NuclideNotFoundError, InvalidNuclideError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    a = z + n
    name = format_nuclide_name(z, a)

    click.echo(f"\nSeparation energies for {name} (Z={z}, N={n})")
    click.echo("=" * 45)

    # Calculate all separation energies
    s_n = db.get_separation_energy_n(z, n)
    s_p = db.get_separation_energy_p(z, n)
    s_2n = db.get_separation_energy_2n(z, n)
    s_2p = db.get_separation_energy_2p(z, n)
    s_alpha = db.get_separation_energy_alpha(z, n)

    click.echo(f"\n  S_n  (one neutron):   {format_value(s_n, 3, 'MeV')}")
    click.echo(f"  S_p  (one proton):    {format_value(s_p, 3, 'MeV')}")
    click.echo(f"  S_2n (two neutrons):  {format_value(s_2n, 3, 'MeV')}")
    click.echo(f"  S_2p (two protons):   {format_value(s_2p, 3, 'MeV')}")
    click.echo(f"  S_α  (alpha):         {format_value(s_alpha, 3, 'MeV')}")

    # Add interpretation
    click.echo("\nInterpretation:")
    if s_n is not None and s_n < 0:
        click.echo("  ⚠ S_n < 0: Neutron unbound (drip line)")
    if s_p is not None and s_p < 0:
        click.echo("  ⚠ S_p < 0: Proton unbound (drip line)")
    if s_alpha is not None and s_alpha < 0:
        click.echo("  ⚠ S_α < 0: Alpha decay energetically favored")

    # Check for magic numbers (from Config for consistency)
    if n in Config.MAGIC_NUMBERS:
        click.echo(f"  ★ N={n} is a magic number (neutron shell closure)")
    if z in Config.MAGIC_NUMBERS:
        click.echo(f"  ★ Z={z} is a magic number (proton shell closure)")

    click.echo()


@cli.command()
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json', 'parquet']),
              default='csv', help='Output format')
@click.option('--experimental-only', is_flag=True, help='Only export nuclides with experimental data')
@click.option('--theoretical-only', is_flag=True, help='Only export nuclides with only theoretical data')
def export(output: str | None, fmt: str, experimental_only: bool, theoretical_only: bool):
    """
    Export nuclear mass data to a file.

    Examples:

        nucmass export -o masses.csv

        nucmass export -o predicted.csv --theoretical-only

        nucmass export --format json -o masses.json
    """
    # Validate output path if specified
    if output and not validate_output_path(output):
        click.echo("Error: Invalid output path (path traversal not allowed)", err=True)
        sys.exit(1)

    db = NuclearDatabase()

    # Build query based on filters
    if experimental_only:
        df = db.query("SELECT * FROM nuclides WHERE has_experimental ORDER BY Z, N")
        filter_desc = "experimental"
    elif theoretical_only:
        df = db.get_predicted_only()
        filter_desc = "predicted-only"
    else:
        df = db.query("SELECT * FROM nuclides ORDER BY Z, N")
        filter_desc = "all"

    click.echo(f"Exporting {len(df)} nuclides ({filter_desc})...")

    # Determine output path
    if output is None:
        output = f"nuclear_masses_{filter_desc}.{fmt}"

    # Export
    if fmt == 'csv':
        df.to_csv(output, index=False)
    elif fmt == 'json':
        df.to_json(output, orient='records', indent=2)
    elif fmt == 'parquet':
        df.to_parquet(output, index=False)

    click.echo(f"Saved to {output}")


@cli.command()
def summary():
    """
    Show database summary statistics.
    """
    db = NuclearDatabase()
    stats = db.summary()

    click.echo("\nNuclear Mass Database Summary")
    click.echo("=" * 40)
    click.echo(f"\n  AME2020 (experimental):   {stats['ame2020_count']:,} nuclides")
    click.echo(f"  FRDM2012 (theoretical):   {stats['frdm2012_count']:,} nuclides")
    click.echo(f"  Combined (unique):        {stats['total_nuclides']:,} nuclides")
    click.echo(f"\n  Both exp & theory:        {stats['both_exp_and_th']:,} nuclides")
    click.echo(f"  Predicted only:           {stats['predicted_only']:,} nuclides")

    # Add some extra info
    predicted = db.get_predicted_only()
    superheavy = len(predicted[predicted['Z'] > 118])
    click.echo(f"  Superheavy (Z > 118):     {superheavy:,} predictions")

    click.echo("\nData sources:")
    click.echo("  AME2020: Wang et al., Chin. Phys. C 45, 030003 (2021)")
    click.echo("  FRDM2012: Möller et al., ADNDT 109-110, 1-204 (2016)")
    click.echo()


@cli.command()
@click.argument('z', type=int)
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
def element(z: int, output_json: bool):
    """
    Look up element information by atomic number Z.

    Provides educational reference including element name, category,
    discovery history, and Wikipedia summary with etymology.

    Examples:

        nucmass element 26   # Iron

        nucmass element 92   # Uranium

        nucmass element 118  # Oganesson

        nucmass element 26 --json  # JSON output
    """
    db = NuclearDatabase()
    info = db.get_element_info(z)

    if info is None:
        click.echo(f"Error: No element information for Z={z}", err=True)
        sys.exit(1)

    if output_json:
        import json
        # Convert None values properly
        data = {k: v for k, v in info.items()}
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        click.echo(f"\n{info['name']} ({info['symbol']})")
        click.echo("=" * 50)

        click.echo(f"\n  Atomic number (Z):  {info['Z']}")
        if info.get('atomic_mass'):
            click.echo(f"  Atomic mass:        {info['atomic_mass']:.4f} u")
        if info.get('category'):
            click.echo(f"  Category:           {info['category']}")
        if info.get('phase'):
            click.echo(f"  Standard state:     {info['phase']}")
        if info.get('appearance'):
            click.echo(f"  Appearance:         {info['appearance']}")

        if info.get('electron_configuration'):
            click.echo(f"\n  Electron config:    {info['electron_configuration']}")

        if info.get('discovered_by'):
            click.echo(f"\n  Discovered by:      {info['discovered_by']}")
        if info.get('named_by'):
            click.echo(f"  Named by:           {info['named_by']}")

        if info.get('summary'):
            click.echo(f"\nDescription:")
            # Word wrap the summary at ~70 chars
            summary = info['summary']
            words = summary.split()
            lines = []
            current_line = "  "
            for word in words:
                if len(current_line) + len(word) + 1 > 72:
                    lines.append(current_line)
                    current_line = "  " + word
                else:
                    current_line += " " + word if current_line != "  " else word
            if current_line.strip():
                lines.append(current_line)
            click.echo("\n".join(lines))

        if info.get('source'):
            click.echo(f"\nSource: {info['source']}")
        click.echo()


@cli.command()
@click.argument('z', type=int)
@click.argument('n', type=int)
@click.argument('z_final', type=int)
@click.argument('n_final', type=int)
@click.option('--ejectile-z', default=0, help='Ejectile proton number (default: 0)')
@click.option('--ejectile-n', default=0, help='Ejectile neutron number (default: 0)')
def qvalue(z: int, n: int, z_final: int, n_final: int, ejectile_z: int, ejectile_n: int):
    """
    Calculate Q-value for a nuclear reaction.

    Arguments: Z_initial N_initial Z_final N_final

    Examples:

        nucmass qvalue 26 30 26 31          # Fe-56(n,γ)Fe-57

        nucmass qvalue 92 146 90 144        # U-238 alpha decay
    """
    db = NuclearDatabase()

    q = db.get_q_value(z, n, z_final, n_final, ejectile_z, ejectile_n)

    if q is None:
        click.echo("Error: Could not calculate Q-value (missing mass data)", err=True)
        sys.exit(1)

    # Determine reaction type
    initial_name = format_nuclide_name(z, z + n)
    final_name = format_nuclide_name(z_final, z_final + n_final)

    z_proj = z_final + ejectile_z - z
    n_proj = n_final + ejectile_n - n

    click.echo(f"\nReaction: {initial_name} + ({z_proj}p,{n_proj}n) → {final_name} + ({ejectile_z}p,{ejectile_n}n)")
    click.echo(f"Q-value: {q:.3f} MeV")

    if q > 0:
        click.echo("  → Exothermic (energy released)")
    else:
        click.echo("  → Endothermic (threshold energy needed)")

    click.echo()


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file path (default: stdout)')
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json', 'table']),
              default='csv', help='Output format')
@click.option('--sep-energies', is_flag=True, help='Include separation energies')
def batch(input_file: str, output: str | None, fmt: str, sep_energies: bool):
    """
    Query multiple nuclides from an input file.

    The input file should have one nuclide per line, with Z and N
    separated by whitespace or comma. Lines starting with # are ignored.

    Examples:

        nucmass batch nuclides.txt -o results.csv

        nucmass batch nuclides.txt --sep-energies --format json

    Input file format:

        # Z N (comments ignored)
        26 30
        82 126
        92,146
    """
    import json
    from pathlib import Path

    # Validate input path to prevent reading sensitive files via symlinks
    if not validate_input_path(input_file):
        click.echo("Error: Invalid input file path", err=True)
        sys.exit(1)

    # Validate output path if specified
    if output and not validate_output_path(output):
        click.echo("Error: Invalid output path (path traversal not allowed)", err=True)
        sys.exit(1)

    db = NuclearDatabase()
    results = []
    errors = []

    # Parse input file
    with open(input_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Parse Z, N (supports space, tab, or comma separator)
            parts = line.replace(',', ' ').split()
            if len(parts) < 2:
                errors.append(f"Line {line_num}: Invalid format '{line}'")
                continue

            try:
                z, n = int(parts[0]), int(parts[1])
            except ValueError:
                errors.append(f"Line {line_num}: Invalid numbers '{line}'")
                continue

            # Query the nuclide
            nuclide = db.get_nuclide_or_none(z, n)
            if nuclide is None:
                errors.append(f"Line {line_num}: Nuclide Z={z}, N={n} not found")
                continue

            # Build result dict
            a = z + n
            result = {
                'Z': z,
                'N': n,
                'A': a,
                'Element': get_element_symbol(z),
                'Name': format_nuclide_name(z, a),
                'mass_excess_exp_keV': nuclide.get('mass_excess_exp_keV'),
                'mass_excess_th_keV': nuclide.get('mass_excess_th_keV'),
                'beta2': nuclide.get('beta2'),
            }

            # Add separation energies if requested
            if sep_energies:
                result['S_n_MeV'] = db.get_separation_energy_n(z, n)
                result['S_p_MeV'] = db.get_separation_energy_p(z, n)
                result['S_2n_MeV'] = db.get_separation_energy_2n(z, n)
                result['S_2p_MeV'] = db.get_separation_energy_2p(z, n)
                result['S_alpha_MeV'] = db.get_separation_energy_alpha(z, n)

            results.append(result)

    # Report errors
    if errors:
        click.echo(f"Warnings ({len(errors)} issues):", err=True)
        for err in errors[:5]:  # Show first 5 errors
            click.echo(f"  {err}", err=True)
        if len(errors) > 5:
            click.echo(f"  ... and {len(errors) - 5} more", err=True)

    if not results:
        click.echo("No valid nuclides found in input file", err=True)
        sys.exit(1)

    click.echo(f"Processed {len(results)} nuclides", err=True)

    # Format output
    if fmt == 'json':
        # Convert NaN to None for JSON
        for r in results:
            for k, v in r.items():
                if pd.isna(v):
                    r[k] = None
        output_str = json.dumps(results, indent=2)
    elif fmt == 'csv':
        df = pd.DataFrame(results)
        output_str = df.to_csv(index=False)
    else:  # table
        df = pd.DataFrame(results)
        output_str = df.to_string(index=False, na_rep='---')

    # Write output
    if output:
        Path(output).write_text(output_str)
        click.echo(f"Results saved to {output}", err=True)
    else:
        click.echo(output_str)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()
