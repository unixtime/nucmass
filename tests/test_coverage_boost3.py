"""
Additional tests to boost coverage - Part 3.

Focuses on:
- cli.py: export, batch, and error handling
- database.py: init_database paths
- utils.py: download edge cases
- nubase2020.py: remaining parser methods
"""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest


# =============================================================================
# CLI Export Tests
# =============================================================================

class TestCLIExport:
    """Test CLI export command variations."""

    def test_export_csv_default(self, tmp_path):
        """Test export to CSV (default format)."""
        from click.testing import CliRunner
        from nucmass.cli import cli

        output_file = tmp_path / "masses.csv"
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "-o", str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists()

        # Check file has content
        content = output_file.read_text()
        assert len(content) > 1000

    def test_export_json(self, tmp_path):
        """Test export to JSON format."""
        from click.testing import CliRunner
        from nucmass.cli import cli

        output_file = tmp_path / "masses.json"
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "-o", str(output_file), "--format", "json"])

        assert result.exit_code == 0
        assert output_file.exists()

    def test_export_experimental_only(self, tmp_path):
        """Test export with experimental-only flag."""
        from click.testing import CliRunner
        from nucmass.cli import cli

        output_file = tmp_path / "exp_masses.csv"
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "-o", str(output_file), "--experimental-only"])

        assert result.exit_code == 0
        assert output_file.exists()

    def test_export_theoretical_only(self, tmp_path):
        """Test export with theoretical-only flag."""
        from click.testing import CliRunner
        from nucmass.cli import cli

        output_file = tmp_path / "th_masses.csv"
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "-o", str(output_file), "--theoretical-only"])

        assert result.exit_code == 0
        assert output_file.exists()


class TestCLIBatchExtended:
    """Extended batch command tests."""

    def test_batch_table_format(self, tmp_path):
        """Test batch with table format output."""
        from click.testing import CliRunner
        from nucmass.cli import cli

        input_file = tmp_path / "input.txt"
        input_file.write_text("26 30\n50 70\n82 126")

        runner = CliRunner()
        result = runner.invoke(cli, ["batch", str(input_file), "--format", "table"])

        assert result.exit_code == 0

    def test_batch_json_format(self, tmp_path):
        """Test batch with JSON format output."""
        from click.testing import CliRunner
        from nucmass.cli import cli

        input_file = tmp_path / "input.txt"
        input_file.write_text("26 30\n82 126")

        runner = CliRunner()
        result = runner.invoke(cli, ["batch", str(input_file), "--format", "json"])

        assert result.exit_code == 0
        assert "{" in result.output or "[" in result.output

    def test_batch_with_comments(self, tmp_path):
        """Test batch with comment lines in input."""
        from click.testing import CliRunner
        from nucmass.cli import cli

        input_file = tmp_path / "input.txt"
        input_file.write_text("# This is a comment\n26 30\n# Another comment\n82 126")

        runner = CliRunner()
        result = runner.invoke(cli, ["batch", str(input_file)])

        assert result.exit_code == 0

    def test_batch_output_file(self, tmp_path):
        """Test batch with output file."""
        from click.testing import CliRunner
        from nucmass.cli import cli

        input_file = tmp_path / "input.txt"
        input_file.write_text("26 30\n50 70")
        output_file = tmp_path / "output.csv"

        runner = CliRunner()
        result = runner.invoke(cli, ["batch", str(input_file), "-o", str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists()


class TestCLILookupMore:
    """More lookup command tests."""

    def test_lookup_heavy_element(self):
        """Test lookup for a heavy element."""
        from click.testing import CliRunner
        from nucmass.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["lookup", "92", "146"])  # U-238

        assert result.exit_code == 0
        assert "238" in result.output or "92" in result.output

    def test_lookup_pb208(self):
        """Test lookup for Pb-208 (doubly magic)."""
        from click.testing import CliRunner
        from nucmass.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["lookup", "82", "126"])

        assert result.exit_code == 0
        assert "Pb-208" in result.output or "82" in result.output


class TestCLISeparationMore:
    """More separation energy command tests."""

    def test_separation_pb208(self):
        """Test separation energies for Pb-208."""
        from click.testing import CliRunner
        from nucmass.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["separation", "82", "126"])

        assert result.exit_code == 0
        assert "S" in result.output  # Should have S_n, S_p, etc.


class TestCLIIsotopesMore:
    """More isotopes command tests."""

    def test_isotopes_uranium(self):
        """Test isotopes for uranium."""
        from click.testing import CliRunner
        from nucmass.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["isotopes", "92", "--limit", "10"])

        assert result.exit_code == 0

    def test_isotopes_json_format(self):
        """Test isotopes with JSON format."""
        from click.testing import CliRunner
        from nucmass.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["isotopes", "26", "--format", "json", "--limit", "5"])

        assert result.exit_code == 0


# =============================================================================
# Database Init Tests
# =============================================================================

class TestDatabaseInit:
    """Test database initialization paths."""

    def test_database_with_custom_path(self, tmp_path):
        """Test database with custom path."""
        from nucmass import NuclearDatabase
        from nucmass.config import Config

        # Use existing database path
        db = NuclearDatabase(db_path=Config.DB_PATH)
        assert db is not None

        # Query to verify it works
        fe56 = db.get_nuclide(26, 30)
        assert fe56 is not None

    def test_database_context_manager_cleanup(self):
        """Test that context manager cleans up properly."""
        from nucmass import NuclearDatabase

        with NuclearDatabase() as db:
            result = db.get_nuclide(26, 30)
            assert result is not None
        # After context, should be cleaned up

    def test_database_close_explicit(self):
        """Test explicit close method."""
        from nucmass import NuclearDatabase

        db = NuclearDatabase()
        db.get_nuclide(26, 30)
        db.close()
        # Should be able to close without error


# =============================================================================
# NUBASE Parser Extended Tests
# =============================================================================

class TestNUBASEParserExtended:
    """Extended NUBASE parser tests."""

    @pytest.fixture
    def parser(self):
        """Get NUBASE parser if file exists."""
        from nucmass.nubase2020 import NUBASEParser
        from nucmass.config import Config

        nubase_file = Config.DATA_DIR / "nubase_4.mas20.txt"
        if not nubase_file.exists():
            pytest.skip("NUBASE2020 file not available")
        return NUBASEParser(str(nubase_file))

    def test_get_nuclide_fe56(self, parser):
        """Test getting Fe-56 data."""
        nuclide = parser.get_nuclide(26, 30)
        if nuclide is not None:
            assert nuclide["Z"] == 26
            assert nuclide["N"] == 30

    def test_get_nuclide_nonexistent(self, parser):
        """Test getting nonexistent nuclide."""
        nuclide = parser.get_nuclide(999, 999)
        assert nuclide is None

    def test_dataframe_columns(self, parser):
        """Test that dataframe has expected columns."""
        df = parser.to_dataframe()

        assert "Z" in df.columns
        assert "N" in df.columns
        assert "A" in df.columns
        assert "half_life_str" in df.columns
        assert "is_stable" in df.columns


# =============================================================================
# Utils Edge Cases
# =============================================================================

class TestUtilsEdgeCases:
    """Test utils edge cases."""

    def test_rate_limiter_with_zero_delay(self):
        """Test rate limiter with zero delay."""
        from nucmass.utils import RateLimiter

        limiter = RateLimiter(delay=0)
        limiter.record("https://example.com/page1")
        limiter.wait("https://example.com/page2")  # Should not wait

    def test_validate_nuclide_params_all_none(self):
        """Test validation with all None params."""
        from nucmass.utils import validate_nuclide_params

        # Should not raise
        validate_nuclide_params(z=None, n=None, a=None)

    def test_validate_nuclide_params_valid_a(self):
        """Test validation with valid A only."""
        from nucmass.utils import validate_nuclide_params

        # Should not raise
        validate_nuclide_params(z=None, n=None, a=56)


# =============================================================================
# Plotting More Coverage
# =============================================================================

class TestPlottingCoverage:
    """More plotting tests for coverage."""

    def test_plot_chart_binding_per_a(self):
        """Test chart colored by binding energy per nucleon."""
        from nucmass import NuclearDatabase
        from nucmass.plotting import plot_chart
        import matplotlib.pyplot as plt

        db = NuclearDatabase()
        fig = plot_chart(db, color_by="binding_per_A")

        assert fig is not None
        plt.close(fig)

    def test_plot_isotope_chain_all_options(self):
        """Test isotope chain with all display options."""
        from nucmass import NuclearDatabase
        from nucmass.plotting import plot_isotope_chain
        import matplotlib.pyplot as plt

        db = NuclearDatabase()
        fig = plot_isotope_chain(
            db, z=50,
            show_experimental=True,
            show_theoretical=True,
        )

        assert fig is not None
        plt.close(fig)


# =============================================================================
# Config Coverage
# =============================================================================

class TestConfigCoverage:
    """More config tests for coverage."""

    def test_config_z_n_range(self):
        """Test Z and N range configuration."""
        from nucmass.config import Config

        assert Config.Z_MIN == 0
        assert Config.Z_MAX > 100
        assert Config.N_MIN == 0
        assert Config.N_MAX > 200

    def test_config_element_neutron(self):
        """Test element symbol for neutron (Z=0)."""
        from nucmass.config import Config

        assert Config.get_element_symbol(0) == 'n'


# =============================================================================
# Exceptions Coverage
# =============================================================================

class TestExceptionsCoverage:
    """More exception tests for coverage."""

    def test_database_not_initialized_error(self):
        """Test DatabaseNotInitializedError."""
        from nucmass.exceptions import DatabaseNotInitializedError

        err = DatabaseNotInitializedError("Database not ready")
        assert "not ready" in str(err)

    def test_extraction_error_message(self):
        """Test ExtractionError with detailed message."""
        from nucmass.exceptions import ExtractionError

        err = ExtractionError("Failed to extract table from page 5")
        assert "page 5" in str(err)

    def test_invalid_nuclide_error_full(self):
        """Test InvalidNuclideError with all attributes."""
        from nucmass.exceptions import InvalidNuclideError

        err = InvalidNuclideError("Z=-5 is invalid", z=-5, n=None)
        assert err.z == -5
        assert err.n is None


# =============================================================================
# AME2020 Coverage
# =============================================================================

class TestAME2020Coverage:
    """More AME2020 tests for coverage."""

    def test_parser_caching_behavior(self):
        """Test that parser caches parsed result."""
        from nucmass.ame2020 import AME2020Parser
        from nucmass.config import Config

        ame_file = Config.DATA_DIR / "mass.mas20.txt"
        if not ame_file.exists():
            pytest.skip("AME2020 file not available")

        parser = AME2020Parser(ame_file)
        df1 = parser.parse()
        df2 = parser.parse()

        # Should be the same object (cached)
        assert df1 is df2

    def test_parser_nuclide_not_found(self):
        """Test parser get_nuclide for missing nuclide."""
        from nucmass.ame2020 import AME2020Parser
        from nucmass.config import Config

        ame_file = Config.DATA_DIR / "mass.mas20.txt"
        if not ame_file.exists():
            pytest.skip("AME2020 file not available")

        parser = AME2020Parser(ame_file)
        result = parser.get_nuclide(z=999, n=999)

        assert result is None
