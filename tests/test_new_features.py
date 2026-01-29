"""Tests for new nucmass features: validation, calculations, CLI, plotting."""

import pytest
import pandas as pd
from pathlib import Path
from click.testing import CliRunner

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nucmass import NuclearDatabase
from nucmass.exceptions import (
    NucmassError,
    NuclideNotFoundError,
    InvalidNuclideError,
)
from nucmass.cli import cli


class TestExceptions:
    """Tests for custom exception classes."""

    def test_nuclide_not_found_error(self):
        """Test NuclideNotFoundError message formatting."""
        err = NuclideNotFoundError(z=26, n=999)
        assert "Z=26" in str(err)
        assert "N=999" in str(err)

    def test_nuclide_not_found_with_suggestions(self):
        """Test NuclideNotFoundError includes suggestions."""
        suggestions = [(26, 28), (26, 29), (26, 30)]
        err = NuclideNotFoundError(z=26, n=999, suggestions=suggestions)
        assert "N=28" in str(err) or "N=29" in str(err) or "N=30" in str(err)

    def test_invalid_nuclide_error(self):
        """Test InvalidNuclideError message."""
        err = InvalidNuclideError("Z must be positive", z=-1)
        assert "Z must be positive" in str(err)
        assert err.z == -1

    def test_exception_hierarchy(self):
        """Test that all exceptions inherit from NucmassError."""
        assert issubclass(NuclideNotFoundError, NucmassError)
        assert issubclass(InvalidNuclideError, NucmassError)


class TestValidation:
    """Tests for input validation."""

    @pytest.fixture
    def db(self):
        db = NuclearDatabase()
        yield db
        db.close()

    def test_invalid_z_negative(self, db):
        """Test that negative Z raises InvalidNuclideError."""
        with pytest.raises(InvalidNuclideError):
            db.get_nuclide(z=-1, n=10)

    def test_invalid_z_too_large(self, db):
        """Test that Z > 140 raises InvalidNuclideError."""
        with pytest.raises(InvalidNuclideError):
            db.get_nuclide(z=200, n=10)

    def test_invalid_n_negative(self, db):
        """Test that negative N raises InvalidNuclideError."""
        with pytest.raises(InvalidNuclideError):
            db.get_nuclide(z=26, n=-5)

    def test_nuclide_not_found(self, db):
        """Test that non-existent nuclide raises NuclideNotFoundError."""
        # Use a valid N value (within range) but one that doesn't exist for this Z
        with pytest.raises(NuclideNotFoundError) as exc_info:
            db.get_nuclide(z=26, n=100)  # Fe with N=100 doesn't exist
        # Should include suggestions
        assert exc_info.value.z == 26
        assert exc_info.value.n == 100

    def test_get_nuclide_or_none_not_found(self, db):
        """Test get_nuclide_or_none returns None for missing nuclide."""
        result = db.get_nuclide_or_none(z=26, n=100)  # Fe with N=100 doesn't exist
        assert result is None

    def test_get_nuclide_or_none_found(self, db):
        """Test get_nuclide_or_none returns data for existing nuclide."""
        result = db.get_nuclide_or_none(z=26, n=30)
        assert result is not None
        assert result["Z"] == 26
        assert result["N"] == 30

    def test_invalid_deformation_threshold(self, db):
        """Test that negative min_beta2 raises ValueError."""
        with pytest.raises(ValueError):
            db.get_deformed(min_beta2=-0.5)


class TestContextManager:
    """Tests for context manager functionality."""

    def test_context_manager_basic(self):
        """Test that context manager opens and closes connection."""
        with NuclearDatabase() as db:
            result = db.summary()
            assert "ame2020_count" in result
        # Connection should be closed after exiting
        assert db._conn is None

    def test_context_manager_exception(self):
        """Test that connection is closed even if exception occurs."""
        try:
            with NuclearDatabase() as db:
                _ = db.summary()  # Make sure connection is open
                raise ValueError("Test exception")
        except ValueError:
            pass
        assert db._conn is None

    def test_repr(self):
        """Test string representation."""
        db = NuclearDatabase()
        assert "NuclearDatabase" in repr(db)
        assert "not connected" in repr(db)
        _ = db.conn  # Force connection
        assert "connected" in repr(db)
        db.close()


class TestSeparationEnergies:
    """Tests for separation energy calculations."""

    @pytest.fixture
    def db(self):
        db = NuclearDatabase()
        yield db
        db.close()

    def test_s_n_fe56(self, db):
        """Test one-neutron separation energy for Fe-56."""
        s_n = db.get_separation_energy_n(z=26, n=30)
        assert s_n is not None
        # S_n for Fe-56 should be around 11 MeV
        assert 8 < s_n < 14

    def test_s_p_fe56(self, db):
        """Test one-proton separation energy for Fe-56."""
        s_p = db.get_separation_energy_p(z=26, n=30)
        assert s_p is not None
        # S_p for Fe-56 should be positive
        assert s_p > 0

    def test_s_2n_fe56(self, db):
        """Test two-neutron separation energy for Fe-56."""
        s_2n = db.get_separation_energy_2n(z=26, n=30)
        assert s_2n is not None
        # S_2n should be roughly 2*S_n
        assert 15 < s_2n < 25

    def test_s_2p_fe56(self, db):
        """Test two-proton separation energy for Fe-56."""
        s_2p = db.get_separation_energy_2p(z=26, n=30)
        assert s_2p is not None
        assert s_2p > 0

    def test_s_alpha_fe56(self, db):
        """Test alpha separation energy for Fe-56."""
        s_alpha = db.get_separation_energy_alpha(z=26, n=30)
        assert s_alpha is not None

    def test_s_n_boundary(self, db):
        """Test S_n returns None for N=0."""
        result = db.get_separation_energy_n(z=26, n=0)
        assert result is None

    def test_s_2n_boundary(self, db):
        """Test S_2n returns None for N < 2."""
        result = db.get_separation_energy_2n(z=26, n=1)
        assert result is None

    def test_s_alpha_boundary(self, db):
        """Test S_alpha returns None when daughter doesn't exist."""
        # For very light nuclei
        result = db.get_separation_energy_alpha(z=2, n=1)
        # He-3 -> nothing (Z=0, N=-1 is invalid)
        assert result is None


class TestQValue:
    """Tests for Q-value calculations."""

    @pytest.fixture
    def db(self):
        db = NuclearDatabase()
        yield db
        db.close()

    def test_q_value_neutron_capture(self, db):
        """Test Q-value for Fe-56(n,γ)Fe-57."""
        # initial: Fe-56 (Z=26, N=30)
        # final: Fe-57 (Z=26, N=31) + gamma (Z=0, N=0)
        q = db.get_q_value(26, 30, 26, 31, z_ejectile=0, n_ejectile=0)
        assert q is not None
        # Neutron capture typically has positive Q
        assert q > 0

    def test_q_value_alpha_decay(self, db):
        """Test Q-value for U-238 alpha decay."""
        # U-238 (Z=92, N=146) -> Th-234 (Z=90, N=144) + alpha (Z=2, N=2)
        q = db.get_q_value(92, 146, 90, 144, z_ejectile=2, n_ejectile=2)
        assert q is not None
        # U-238 alpha decay is energetically favorable
        assert q > 0

    def test_q_value_missing_data(self, db):
        """Test Q-value returns None for missing nuclides."""
        # Use a valid but non-existent nuclide (Fe with N=100)
        q = db.get_q_value(26, 30, 26, 100)
        assert q is None


class TestMassExcess:
    """Tests for mass excess retrieval."""

    @pytest.fixture
    def db(self):
        db = NuclearDatabase()
        yield db
        db.close()

    def test_get_mass_excess_experimental(self, db):
        """Test getting experimental mass excess."""
        m = db.get_mass_excess(26, 30, prefer="experimental")
        assert m is not None
        # Fe-56 mass excess is around -60607 keV
        assert -61000 < m < -60000

    def test_get_mass_excess_theoretical(self, db):
        """Test getting theoretical mass excess."""
        m = db.get_mass_excess(26, 30, prefer="theoretical")
        assert m is not None
        assert -61000 < m < -60000

    def test_get_mass_excess_invalid_prefer(self, db):
        """Test that invalid prefer value raises ValueError."""
        with pytest.raises(ValueError):
            db.get_mass_excess(26, 30, prefer="invalid")

    def test_get_binding_energy(self, db):
        """Test binding energy calculation."""
        b = db.get_binding_energy(26, 30)
        assert b is not None
        # Fe-56 total binding energy is around 492 MeV
        assert 480 < b < 510


class TestCLI:
    """Tests for command-line interface."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_cli_help(self, runner):
        """Test CLI help output."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Nuclear Mass Data Toolkit" in result.output

    def test_cli_version(self, runner):
        """Test CLI version output."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "1.1.0" in result.output

    def test_cli_lookup_fe56(self, runner):
        """Test CLI lookup command for Fe-56."""
        result = runner.invoke(cli, ["lookup", "26", "30"])
        assert result.exit_code == 0
        assert "Fe-56" in result.output
        assert "Mass Excess" in result.output

    def test_cli_lookup_invalid(self, runner):
        """Test CLI lookup with non-existent nuclide."""
        result = runner.invoke(cli, ["lookup", "26", "999"])
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_cli_lookup_json(self, runner):
        """Test CLI lookup with JSON output."""
        result = runner.invoke(cli, ["lookup", "26", "30", "--json"])
        assert result.exit_code == 0
        # Should be valid JSON
        import json
        data = json.loads(result.output)
        assert data["Z"] == 26
        assert data["N"] == 30

    def test_cli_isotopes(self, runner):
        """Test CLI isotopes command."""
        result = runner.invoke(cli, ["isotopes", "26", "-n", "5"])
        assert result.exit_code == 0
        assert "Fe isotopes" in result.output

    def test_cli_isotones(self, runner):
        """Test CLI isotones command."""
        result = runner.invoke(cli, ["isotones", "82", "-n", "5"])
        assert result.exit_code == 0
        assert "N=82 isotones" in result.output

    def test_cli_separation(self, runner):
        """Test CLI separation command."""
        result = runner.invoke(cli, ["separation", "82", "126"])
        assert result.exit_code == 0
        assert "Pb-208" in result.output
        assert "S_n" in result.output
        assert "magic number" in result.output.lower()

    def test_cli_summary(self, runner):
        """Test CLI summary command."""
        result = runner.invoke(cli, ["summary"])
        assert result.exit_code == 0
        assert "AME2020" in result.output
        assert "FRDM2012" in result.output

    def test_cli_qvalue(self, runner):
        """Test CLI qvalue command."""
        result = runner.invoke(cli, ["qvalue", "26", "30", "26", "31"])
        assert result.exit_code == 0
        assert "Q-value" in result.output


class TestPlotting:
    """Tests for plotting functions."""

    @pytest.fixture
    def db(self):
        db = NuclearDatabase()
        yield db
        db.close()

    def test_plot_chart(self, db):
        """Test nuclear chart plotting."""
        from nucmass.plotting import plot_chart
        fig = plot_chart(db, color_by="beta2", figsize=(8, 6))
        assert fig is not None
        # Check it has axes
        assert len(fig.axes) > 0

    def test_plot_chart_mass_excess(self, db):
        """Test chart with mass excess coloring."""
        from nucmass.plotting import plot_chart
        fig = plot_chart(db, color_by="mass_excess")
        assert fig is not None

    def test_plot_chart_invalid_color(self, db):
        """Test that invalid color_by raises ValueError."""
        from nucmass.plotting import plot_chart
        with pytest.raises(ValueError):
            plot_chart(db, color_by="invalid_property")

    def test_plot_isotope_chain(self, db):
        """Test isotope chain plotting."""
        from nucmass.plotting import plot_isotope_chain
        fig = plot_isotope_chain(db, z=50, y="mass_excess")
        assert fig is not None

    def test_plot_isotope_chain_s2n(self, db):
        """Test isotope chain with S_2n."""
        from nucmass.plotting import plot_isotope_chain
        fig = plot_isotope_chain(db, z=50, y="S_2n")
        assert fig is not None

    def test_plot_binding_energy_curve(self, db):
        """Test binding energy curve plotting."""
        from nucmass.plotting import plot_binding_energy_curve
        fig = plot_binding_energy_curve(db)
        assert fig is not None

    def test_plot_mass_residuals(self, db):
        """Test mass residuals plotting."""
        from nucmass.plotting import plot_mass_residuals
        fig = plot_mass_residuals(db)
        assert fig is not None
        # Should have 2 subplots (plus potentially a colorbar axes)
        assert len(fig.axes) >= 2


class TestPhysicalConsistency:
    """Tests for physical consistency of calculations."""

    @pytest.fixture
    def db(self):
        db = NuclearDatabase()
        yield db
        db.close()

    def test_doubly_magic_spherical(self, db):
        """Test that doubly-magic nuclei are spherical."""
        doubly_magic = [
            (8, 8),    # O-16
            (20, 20),  # Ca-40
            (20, 28),  # Ca-48
            (50, 82),  # Sn-132
            (82, 126), # Pb-208
        ]
        for z, n in doubly_magic:
            nuclide = db.get_nuclide_or_none(z, n)
            if nuclide is not None and pd.notna(nuclide.get("beta2")):
                assert abs(nuclide["beta2"]) < 0.1, f"Z={z}, N={n} should be spherical"

    def test_fe56_most_bound(self, db):
        """Test that Fe-56 has among the highest B/A."""
        fe56 = db.get_nuclide(26, 30)
        fe56_ba = fe56["binding_per_A_exp_keV"]

        # Check a few other nuclei have lower B/A
        he4 = db.get_nuclide(2, 2)
        u238 = db.get_nuclide_or_none(92, 146)

        assert fe56_ba > he4["binding_per_A_exp_keV"]
        if u238 is not None and pd.notna(u238.get("binding_per_A_exp_keV")):
            assert fe56_ba > u238["binding_per_A_exp_keV"]

    def test_shell_closure_effect(self, db):
        """Test that shell closures show enhanced S_2n drop."""
        # S_2n should drop after crossing magic number N=82
        # Test for Sn isotopes
        s2n_before = db.get_separation_energy_2n(50, 82)  # Sn-132
        s2n_after = db.get_separation_energy_2n(50, 84)   # Sn-134

        if s2n_before is not None and s2n_after is not None:
            # S_2n should be lower after crossing shell closure
            assert s2n_after < s2n_before

    def test_mass_number_consistency(self, db):
        """Test that A = Z + N for all queries."""
        fe56 = db.get_nuclide(26, 30)
        assert fe56["A"] == fe56["Z"] + fe56["N"]

        isotopes = db.get_isotopes(50)
        assert (isotopes["A"] == isotopes["Z"] + isotopes["N"]).all()


class TestNUBASEParser:
    """Tests for NUBASE2020 nuclear properties parser."""

    @pytest.fixture
    def nubase_file(self):
        """Get NUBASE 2020 file path, skip if not available.

        The NUBASEParser is designed for the NUBASE 2020 format (.mas20.txt).
        Older formats have different column structures and won't work correctly.
        """
        from nucmass.nubase2020 import DATA_DIR
        # Only accept NUBASE 2020 format files
        possible_paths = [
            DATA_DIR / "nubase_4.mas20.txt",  # NUBASE 2020
            DATA_DIR / "nubase.mas20.txt",
        ]
        for filepath in possible_paths:
            if filepath.exists():
                return filepath
        pytest.skip("NUBASE 2020 file not available (nubase_4.mas20.txt required)")
        return None

    def test_parse_half_life_seconds(self):
        """Test half-life parsing for seconds."""
        from nucmass.nubase2020 import parse_half_life
        hl_str, hl_sec = parse_half_life("4.5 s")
        assert hl_str == "4.5 s"
        assert abs(hl_sec - 4.5) < 0.01

    def test_parse_half_life_milliseconds(self):
        """Test half-life parsing for milliseconds."""
        from nucmass.nubase2020 import parse_half_life
        _, hl_sec = parse_half_life("2.3 ms")
        assert abs(hl_sec - 0.0023) < 0.0001

    def test_parse_half_life_years(self):
        """Test half-life parsing for years."""
        from nucmass.nubase2020 import parse_half_life
        _, hl_sec = parse_half_life("1.0 y")
        assert abs(hl_sec - 31557600.0) < 1.0

    def test_parse_half_life_stable(self):
        """Test half-life parsing for stable nuclides."""
        from nucmass.nubase2020 import parse_half_life
        hl_str, hl_sec = parse_half_life("stbl")
        assert hl_str == "stable"
        assert hl_sec is None

    def test_parse_half_life_scientific(self):
        """Test half-life parsing with scientific notation."""
        from nucmass.nubase2020 import parse_half_life
        _, hl_sec = parse_half_life("4.47e9 y")
        # U-238 half-life is about 4.47 billion years
        assert hl_sec is not None
        assert hl_sec > 1e17  # Greater than 1e17 seconds

    def test_parser_initialization(self, nubase_file):
        """Test parser can be initialized with file."""
        from nucmass.nubase2020 import NUBASEParser
        parser = NUBASEParser(nubase_file)
        assert parser.filepath.exists()

    def test_parser_parse(self, nubase_file):
        """Test parsing returns DataFrame with expected columns."""
        from nucmass.nubase2020 import NUBASEParser
        parser = NUBASEParser(nubase_file)
        df = parser.parse()
        assert len(df) > 0
        assert "Z" in df.columns
        assert "N" in df.columns
        assert "A" in df.columns
        assert "half_life_str" in df.columns
        assert "is_stable" in df.columns

    def test_get_nuclide_fe56(self, nubase_file):
        """Test getting Fe-56 data."""
        from nucmass.nubase2020 import NUBASEParser
        parser = NUBASEParser(nubase_file)
        fe56 = parser.get_nuclide(z=26, n=30)
        if fe56 is not None:
            assert fe56["Z"] == 26
            assert fe56["N"] == 30
            assert fe56["A"] == 56
            assert fe56["is_stable"]

    def test_get_stable_nuclides(self, nubase_file):
        """Test getting stable nuclides."""
        from nucmass.nubase2020 import NUBASEParser
        parser = NUBASEParser(nubase_file)
        stable = parser.get_stable()
        # There should be about 190-260 stable nuclides
        # (number varies slightly based on file format and filtering)
        assert len(stable) > 180
        assert len(stable) < 300
        assert stable["is_stable"].all()

    def test_get_isomers(self, nubase_file):
        """Test getting isomeric states."""
        from nucmass.nubase2020 import NUBASEParser
        parser = NUBASEParser(nubase_file)
        isomers = parser.get_isomers()
        assert len(isomers) > 0
        assert (isomers["isomer"] != "").all()

    def test_get_by_decay_mode_alpha(self, nubase_file):
        """Test filtering by alpha decay mode."""
        from nucmass.nubase2020 import NUBASEParser
        parser = NUBASEParser(nubase_file)
        # In ASCII format, alpha decay is represented as "A=" not "α"
        alpha_decayers = parser.get_by_decay_mode("A=")
        # There should be many alpha emitters
        assert len(alpha_decayers) > 100

    def test_mass_number_consistency(self, nubase_file):
        """Test that A = Z + N for all nuclides."""
        from nucmass.nubase2020 import NUBASEParser
        parser = NUBASEParser(nubase_file)
        df = parser.parse()
        # Filter out rows with valid Z, N, A
        valid = df.dropna(subset=["Z", "N", "A"])
        assert (valid["A"] == valid["Z"] + valid["N"]).all()


class TestParametricNuclides:
    """Parametric tests covering multiple well-known nuclides beyond Fe-56."""

    @pytest.fixture
    def db(self):
        db = NuclearDatabase()
        yield db
        db.close()

    @pytest.mark.parametrize("z,n,name,expected_mass_range", [
        (26, 30, "Fe-56", (-60700, -60500)),   # Iron-56: most tightly bound
        (82, 126, "Pb-208", (-21800, -21600)), # Lead-208: doubly magic
        (92, 146, "U-238", (47200, 47400)),    # Uranium-238: heavy actinide (positive mass excess)
        (50, 70, "Sn-120", (-91200, -91000)),  # Tin-120: stable, even-even
        (2, 2, "He-4", (2400, 2600)),          # Helium-4: alpha particle
    ])
    def test_mass_excess_known_nuclides(self, db, z, n, name, expected_mass_range):
        """Test mass excess values for well-known nuclides."""
        nuclide = db.get_nuclide(z, n)
        assert nuclide is not None, f"{name} should exist in database"
        mass_excess = nuclide.get("mass_excess_exp_keV")
        assert mass_excess is not None, f"{name} should have experimental mass"
        assert expected_mass_range[0] < mass_excess < expected_mass_range[1], \
            f"{name} mass excess {mass_excess} outside expected range"

    @pytest.mark.parametrize("z,n,name,is_spherical", [
        (82, 126, "Pb-208", True),   # Doubly magic: spherical
        (8, 8, "O-16", True),        # Doubly magic: spherical
        (20, 20, "Ca-40", True),     # Doubly magic: spherical
        (66, 96, "Dy-162", False),   # Deformed rare earth
        (92, 146, "U-238", False),   # Deformed actinide
    ])
    def test_deformation_known_nuclides(self, db, z, n, name, is_spherical):
        """Test deformation for nuclides with known shapes."""
        nuclide = db.get_nuclide_or_none(z, n)
        if nuclide is not None and pd.notna(nuclide.get("beta2")):
            beta2 = abs(nuclide["beta2"])
            if is_spherical:
                assert beta2 < 0.1, f"{name} should be spherical (|β₂| < 0.1), got {beta2}"
            else:
                assert beta2 > 0.15, f"{name} should be deformed (|β₂| > 0.15), got {beta2}"

    @pytest.mark.parametrize("z,n,name,s2n_range", [
        (82, 126, "Pb-208", (14, 16)),   # Shell closure: higher S_2n
        (82, 128, "Pb-210", (9, 12)),    # After shell: lower S_2n
        (50, 82, "Sn-132", (12, 15)),    # Doubly magic: high S_2n
        (26, 30, "Fe-56", (18, 22)),     # Stable: positive S_2n
    ])
    def test_s2n_known_nuclides(self, db, z, n, name, s2n_range):
        """Test two-neutron separation energies for specific nuclides."""
        s2n = db.get_separation_energy_2n(z, n)
        if s2n is not None:
            assert s2n_range[0] < s2n < s2n_range[1], \
                f"{name} S_2n={s2n:.2f} MeV outside expected range {s2n_range}"

    @pytest.mark.parametrize("z,n,name,expected_stable", [
        (26, 30, "Fe-56", True),
        (92, 146, "U-238", False),  # Radioactive (alpha)
        (6, 8, "C-14", False),      # Radioactive (beta-)
    ])
    def test_stability_known_nuclides(self, db, z, n, name, expected_stable):
        """Test stability flags for known nuclides (where decay data is available)."""
        nuclide = db.get_nuclide_or_none(z, n)
        if nuclide is not None and nuclide.get("has_decay_data") and pd.notna(nuclide.get("is_stable")):
            assert nuclide["is_stable"] == expected_stable, \
                f"{name} stability should be {expected_stable}"

    @pytest.mark.parametrize("z,expected_isotope_count_min", [
        (1, 3),    # Hydrogen: at least H, D, T
        (26, 20),  # Iron: many isotopes
        (50, 30),  # Tin: most stable isotopes of any element
        (92, 20),  # Uranium: many isotopes
    ])
    def test_isotope_counts(self, db, z, expected_isotope_count_min):
        """Test that elements have expected minimum number of isotopes."""
        isotopes = db.get_isotopes(z)
        assert len(isotopes) >= expected_isotope_count_min, \
            f"Z={z} should have at least {expected_isotope_count_min} isotopes"


class TestCLIInit:
    """Tests for the new init CLI command."""

    def test_cli_init_help(self):
        """Test init command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['init', '--help'])
        assert result.exit_code == 0
        assert 'Initialize' in result.output or 'rebuild' in result.output

    def test_cli_init_existing(self):
        """Test init command when database exists."""
        runner = CliRunner()
        result = runner.invoke(cli, ['init'])
        # Should not fail, just inform database exists
        assert result.exit_code == 0
        assert 'exists' in result.output.lower() or 'nuclides' in result.output.lower()


class TestCLIBatch:
    """Tests for batch CLI command."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_cli_batch_help(self, runner):
        """Test batch command help."""
        result = runner.invoke(cli, ['batch', '--help'])
        assert result.exit_code == 0
        assert 'Query multiple nuclides' in result.output

    def test_cli_batch_file(self, runner, tmp_path):
        """Test batch command with input file."""
        # Create input file
        input_file = tmp_path / "nuclides.txt"
        input_file.write_text("# Test nuclides\n26 30\n82 126\n")

        result = runner.invoke(cli, ['batch', str(input_file)])
        assert result.exit_code == 0
        assert 'Fe-56' in result.output or '26' in result.output
        assert 'Processed 2 nuclides' in result.output or '2' in result.output

    def test_cli_batch_with_sep_energies(self, runner, tmp_path):
        """Test batch command with separation energies."""
        input_file = tmp_path / "nuclides.txt"
        input_file.write_text("26 30\n")

        result = runner.invoke(cli, ['batch', str(input_file), '--sep-energies'])
        assert result.exit_code == 0
        assert 'S_n' in result.output or 'S_n_MeV' in result.output

    def test_cli_batch_json_output(self, runner, tmp_path):
        """Test batch command with JSON output to file."""
        input_file = tmp_path / "nuclides.txt"
        input_file.write_text("26 30\n")
        output_file = tmp_path / "output.json"

        # Write JSON to file to avoid mixing with stderr messages
        result = runner.invoke(cli, ['batch', str(input_file), '--format', 'json', '-o', str(output_file)])
        assert result.exit_code == 0
        import json
        data = json.loads(output_file.read_text())
        assert len(data) == 1
        assert data[0]['Z'] == 26

    def test_cli_batch_comma_separator(self, runner, tmp_path):
        """Test batch command with comma-separated input."""
        input_file = tmp_path / "nuclides.txt"
        input_file.write_text("26,30\n82,126\n")

        result = runner.invoke(cli, ['batch', str(input_file)])
        assert result.exit_code == 0
        assert 'Processed 2 nuclides' in result.output


class TestThreadSafety:
    """Tests for thread-safe database access."""

    def test_thread_safe_mode_initialization(self):
        """Test creating database in thread-safe mode."""
        db = NuclearDatabase(thread_safe=True)
        assert db._thread_safe is True
        _ = db.conn  # Force connection
        db.close()

    def test_thread_safe_basic_query(self):
        """Test basic query in thread-safe mode."""
        db = NuclearDatabase(thread_safe=True)
        nuclide = db.get_nuclide(26, 30)
        assert nuclide is not None
        assert nuclide['Z'] == 26
        db.close()

    def test_concurrent_queries(self):
        """Test concurrent queries from multiple threads."""
        import threading

        results = []
        errors = []
        db = NuclearDatabase(thread_safe=True)

        def query_nuclide(z, n, index):
            try:
                nuclide = db.get_nuclide_or_none(z, n)
                results.append((index, nuclide is not None))
            except Exception as e:
                errors.append((index, str(e)))

        # Create multiple threads querying different nuclides
        threads = []
        test_nuclides = [
            (26, 30), (82, 126), (50, 70), (92, 146), (2, 2),
            (28, 30), (14, 14), (8, 8), (20, 20), (6, 6),
        ]

        for i, (z, n) in enumerate(test_nuclides):
            t = threading.Thread(target=query_nuclide, args=(z, n, i))
            threads.append(t)

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join(timeout=10)

        db.close()

        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == len(test_nuclides)
        assert all(success for _, success in results)

    def test_thread_local_connections(self):
        """Test that different threads get separate connections."""
        import threading

        connection_ids = {}
        barrier = threading.Barrier(3)  # Ensure threads run concurrently
        db = NuclearDatabase(thread_safe=True)

        def get_connection_id(thread_num):
            barrier.wait()  # Synchronize thread start
            conn = db.conn
            # Hold connection while other threads get theirs
            connection_ids[thread_num] = id(conn)
            barrier.wait()  # Wait for all threads to get their connections

        threads = [threading.Thread(target=get_connection_id, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        db.close()

        # Verify each thread got a connection
        assert len(connection_ids) == 3
        # In thread-safe mode, concurrent threads should have different connections
        # At minimum we expect more than one unique connection
        assert len(set(connection_ids.values())) >= 2, \
            f"Expected multiple connections but got: {connection_ids}"


class TestCacheStress:
    """Stress tests for the mass excess cache."""

    @pytest.fixture
    def db(self):
        db = NuclearDatabase()
        db.clear_cache()  # Start with clean cache
        yield db
        db.close()

    def test_cache_population(self, db):
        """Test that cache is populated on queries."""
        # Clear any existing cache
        db.clear_cache()

        # Query several nuclides
        for z in range(20, 30):
            for n in range(20, 30):
                db.get_mass_excess(z, n)

        # Check cache has entries
        db_path_str = str(db.db_path)
        cache_entries = [k for k in NuclearDatabase._mass_cache if k[0] == db_path_str]
        assert len(cache_entries) > 0

    def test_cache_eviction(self, db):
        """Test cache eviction when full."""
        # This is a mild stress test - verify cache doesn't grow unbounded
        original_max = NuclearDatabase._CACHE_MAX_SIZE

        # Query many nuclides
        for z in range(10, 80):
            for n in range(10, 80):
                db.get_mass_excess(z, n)

        # Cache should be within bounds
        assert len(NuclearDatabase._mass_cache) <= original_max

    def test_cache_hit_performance(self, db):
        """Test that cached queries are faster."""
        import time

        # First query (cache miss)
        db.clear_cache()
        start = time.perf_counter()
        for _ in range(100):
            db.get_mass_excess(26, 30)
            db.clear_cache()  # Force cache miss
        cold_time = time.perf_counter() - start

        # Second query (cache hit)
        db.get_mass_excess(26, 30)  # Prime cache
        start = time.perf_counter()
        for _ in range(100):
            db.get_mass_excess(26, 30)
        warm_time = time.perf_counter() - start

        # Cached should be faster (at least 2x)
        assert warm_time < cold_time / 2, f"Cache not effective: warm={warm_time:.4f}s, cold={cold_time:.4f}s"


class TestBatchQueryPerformance:
    """Tests for batch query performance."""

    @pytest.fixture
    def db(self):
        db = NuclearDatabase()
        yield db
        db.close()

    def test_isotope_chain_query(self, db):
        """Test querying full isotope chains."""
        import time

        # Time querying all isotopes for several elements
        start = time.perf_counter()
        total_nuclides = 0
        for z in [26, 50, 82, 92]:
            isotopes = db.get_isotopes(z)
            total_nuclides += len(isotopes)
        elapsed = time.perf_counter() - start

        assert total_nuclides > 100  # Should get many isotopes
        assert elapsed < 2.0  # Should complete within 2 seconds

    def test_separation_energy_batch(self, db):
        """Test computing separation energies for many nuclides."""
        import time

        # Compute S_2n for all Sn isotopes
        start = time.perf_counter()
        s2n_values = []
        for n in range(50, 90):
            s2n = db.get_separation_energy_2n(50, n)
            if s2n is not None:
                s2n_values.append((n, s2n))
        elapsed = time.perf_counter() - start

        assert len(s2n_values) > 20  # Should get many values
        assert elapsed < 5.0  # Should complete within 5 seconds
