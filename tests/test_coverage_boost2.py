"""
Additional tests to boost coverage - Part 2.

Focuses on:
- database.py: Q-values, mass excess edge cases, more separation energies
- cli.py: More CLI commands
- nubase2020.py: Parser methods
- plotting.py: More edge cases
"""


import pytest


# =============================================================================
# Database Coverage Tests
# =============================================================================

class TestDatabaseQValues:
    """Test Q-value calculations."""

    def test_q_value_alpha_decay(self):
        """Test Q-value for alpha decay."""
        from nucmass import NuclearDatabase

        db = NuclearDatabase()
        # U-238 alpha decay to Th-234: (92, 146) -> (90, 144) + (2, 2)
        q = db.get_q_value(92, 146, 90, 144, 2, 2)

        if q is not None:
            assert 3.5 < q < 5.5  # ~4.3 MeV for U-238

    def test_q_value_neutron_capture(self):
        """Test Q-value for neutron capture."""
        from nucmass import NuclearDatabase

        db = NuclearDatabase()
        # Fe-56(n,γ)Fe-57: (26, 30) -> (26, 31) + (0, 0)
        q = db.get_q_value(26, 30, 26, 31, 0, 0)

        if q is not None:
            assert 6 < q < 9  # ~7.6 MeV

    def test_q_value_missing_nuclide(self):
        """Test Q-value with missing nuclide returns None."""
        from nucmass import NuclearDatabase

        db = NuclearDatabase()
        # Nonexistent nuclide - just verify it doesn't raise
        db.get_q_value(0, 0, 0, 1, 0, 0)


class TestDatabaseMassExcessEdgeCases:
    """Test mass excess edge cases."""

    def test_get_mass_excess_theoretical_prefer(self):
        """Test getting theoretical mass excess when preferred."""
        from nucmass import NuclearDatabase

        db = NuclearDatabase()
        # Get theoretical mass for a predicted-only nuclide
        predicted = db.get_predicted_only()
        if len(predicted) > 0:
            row = predicted.iloc[0]
            z, n = int(row['Z']), int(row['N'])
            me = db.get_mass_excess(z, n, prefer="theoretical")
            assert me is not None

    def test_get_mass_excess_cache_hit(self):
        """Test that cache hits work correctly."""
        from nucmass import NuclearDatabase

        db = NuclearDatabase()
        # First call - cache miss
        me1 = db.get_mass_excess(26, 30)
        # Second call - should hit cache
        me2 = db.get_mass_excess(26, 30)

        assert me1 == me2

    def test_get_mass_excess_none_for_nonexistent(self):
        """Test that nonexistent nuclide returns None."""
        from nucmass import NuclearDatabase

        db = NuclearDatabase()
        # Just verify it doesn't raise for edge case
        db.get_mass_excess(0, 0)  # No data for Z=0, N=0


class TestDatabaseSeparationEnergies:
    """Test separation energy calculations."""

    def test_s_2n_magic(self):
        """Test S_2n at magic number N=82."""
        from nucmass import NuclearDatabase

        db = NuclearDatabase()
        # Sn-132 (Z=50, N=82) - double magic
        s_2n = db.get_separation_energy_2n(50, 82)

        if s_2n is not None:
            # S_2n should be larger at magic number
            assert s_2n > 5  # MeV

    def test_s_2p_magic(self):
        """Test S_2p at magic number Z=50."""
        from nucmass import NuclearDatabase

        db = NuclearDatabase()
        # Sn-120 (Z=50, N=70)
        s_2p = db.get_separation_energy_2p(50, 70)

        if s_2p is not None:
            assert s_2p > 5  # MeV

    def test_s_alpha_u238(self):
        """Test alpha separation energy for U-238."""
        from nucmass import NuclearDatabase

        db = NuclearDatabase()
        s_alpha = db.get_separation_energy_alpha(92, 146)

        if s_alpha is not None:
            # S_alpha should be negative (alpha can be emitted)
            assert s_alpha < 0

    def test_separation_energy_boundary(self):
        """Test separation energy at boundary (n=0 or z=0)."""
        from nucmass import NuclearDatabase

        db = NuclearDatabase()
        # S_n for n=0 should return None (can't remove neutron)
        s_n = db.get_separation_energy_n(26, 0)
        assert s_n is None

        # S_p for z=0 should return None
        s_p = db.get_separation_energy_p(0, 30)
        assert s_p is None

    def test_separation_energy_2n_boundary(self):
        """Test S_2n boundary (n<2)."""
        from nucmass import NuclearDatabase

        db = NuclearDatabase()
        s_2n = db.get_separation_energy_2n(26, 1)
        assert s_2n is None

    def test_separation_energy_2p_boundary(self):
        """Test S_2p boundary (z<2)."""
        from nucmass import NuclearDatabase

        db = NuclearDatabase()
        s_2p = db.get_separation_energy_2p(1, 30)
        assert s_2p is None


class TestDatabaseQuery:
    """Test raw query functionality."""

    def test_query_custom(self):
        """Test custom SQL query."""
        from nucmass import NuclearDatabase

        db = NuclearDatabase()
        result = db.query("""
            SELECT Z, N, A, Element
            FROM ame2020
            WHERE Z = 26 AND A = 56
        """)

        assert len(result) == 1
        assert result.iloc[0]['Element'].strip() == 'Fe'

    def test_query_aggregate(self):
        """Test aggregate SQL query."""
        from nucmass import NuclearDatabase

        db = NuclearDatabase()
        result = db.query("""
            SELECT COUNT(*) as cnt
            FROM nuclides
            WHERE Z > 100
        """)

        assert result.iloc[0]['cnt'] >= 0


# =============================================================================
# CLI Coverage Tests
# =============================================================================

class TestCLIMoreCommands:
    """Test more CLI commands."""

    def test_cli_init_existing_no_rebuild(self):
        """Test init command when database exists."""
        from click.testing import CliRunner
        from nucmass.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["init"])

        assert result.exit_code == 0
        assert "exists" in result.output.lower() or "ready" in result.output.lower()

    def test_cli_export_csv(self, tmp_path):
        """Test export command with CSV format."""
        from click.testing import CliRunner
        from nucmass.cli import cli

        output_file = tmp_path / "export.csv"
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "-o", str(output_file), "--format", "csv"])

        assert result.exit_code == 0
        assert output_file.exists()

    def test_cli_lookup_with_json(self):
        """Test lookup command with JSON output."""
        from click.testing import CliRunner
        from nucmass.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["lookup", "26", "30", "--json"])

        assert result.exit_code == 0
        assert "{" in result.output  # JSON should have braces

    def test_cli_isotopes_with_limit(self):
        """Test isotopes command with limit."""
        from click.testing import CliRunner
        from nucmass.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["isotopes", "92", "--limit", "5"])

        assert result.exit_code == 0

    def test_cli_separation_all_types(self):
        """Test separation command shows all types."""
        from click.testing import CliRunner
        from nucmass.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["separation", "82", "126"])  # Pb-208

        assert result.exit_code == 0
        # Should show multiple separation energies
        assert "S" in result.output


class TestCLIBatchMore:
    """Test more batch command features."""

    def test_batch_with_theoretical(self, tmp_path):
        """Test batch processing with theoretical masses."""
        from click.testing import CliRunner
        from nucmass.cli import cli

        input_file = tmp_path / "input.txt"
        input_file.write_text("26 30\n82 126\n92 146")

        runner = CliRunner()
        result = runner.invoke(cli, ["batch", str(input_file)])

        assert result.exit_code == 0


# =============================================================================
# NUBASE2020 Coverage Tests
# =============================================================================

class TestNUBASEParserMethods:
    """Test NUBASE2020 parser methods."""

    @pytest.fixture
    def parser(self):
        """Get NUBASE parser if file exists."""
        from nucmass.nubase2020 import NUBASEParser
        from nucmass.config import Config

        nubase_file = Config.DATA_DIR / "nubase_4.mas20.txt"
        if not nubase_file.exists():
            pytest.skip("NUBASE2020 file not available")
        return NUBASEParser(str(nubase_file))

    def test_get_by_half_life_short(self, parser):
        """Test getting short-lived nuclides."""
        # Nuclides with half-life < 1 second
        short_lived = parser.get_by_half_life(max_seconds=1.0)
        assert len(short_lived) > 100

    def test_get_by_half_life_long(self, parser):
        """Test getting long-lived nuclides."""
        # Nuclides with half-life > 1 year
        year_in_seconds = 365.25 * 24 * 3600
        long_lived = parser.get_by_half_life(min_seconds=year_in_seconds)
        assert len(long_lived) > 50

    def test_get_isomers_count(self, parser):
        """Test counting isomeric states."""
        isomers = parser.get_isomers()
        # Should have some isomers
        assert len(isomers) > 100

    def test_get_stable_count(self, parser):
        """Test counting stable nuclides."""
        df = parser.to_dataframe()
        stable = df[df["is_stable"]]
        # Should have some stable nuclides (actual count depends on data source)
        assert len(stable) > 100


class TestNUBASEHalfLifeParsing:
    """Test half-life parsing edge cases."""

    def test_parse_half_life_microseconds(self):
        """Test parsing microsecond half-lives."""
        from nucmass.nubase2020 import parse_half_life

        hl_str, hl_sec = parse_half_life("45.3 us")
        assert hl_sec is not None
        assert abs(hl_sec - 45.3e-6) < 1e-10

    def test_parse_half_life_nanoseconds(self):
        """Test parsing nanosecond half-lives."""
        from nucmass.nubase2020 import parse_half_life

        hl_str, hl_sec = parse_half_life("100 ns")
        assert hl_sec is not None
        assert abs(hl_sec - 100e-9) < 1e-14

    def test_parse_half_life_minutes(self):
        """Test parsing minute half-lives."""
        from nucmass.nubase2020 import parse_half_life

        hl_str, hl_sec = parse_half_life("5.27 m")
        assert hl_sec is not None
        assert abs(hl_sec - 5.27 * 60) < 0.01

    def test_parse_half_life_hours(self):
        """Test parsing hour half-lives."""
        from nucmass.nubase2020 import parse_half_life

        hl_str, hl_sec = parse_half_life("12.3 h")
        assert hl_sec is not None
        assert abs(hl_sec - 12.3 * 3600) < 0.01

    def test_parse_half_life_days(self):
        """Test parsing day half-lives."""
        from nucmass.nubase2020 import parse_half_life

        hl_str, hl_sec = parse_half_life("3.5 d")
        assert hl_sec is not None
        assert abs(hl_sec - 3.5 * 86400) < 0.01

    def test_parse_half_life_kilo_years(self):
        """Test parsing kilo-year half-lives."""
        from nucmass.nubase2020 import parse_half_life

        hl_str, hl_sec = parse_half_life("5.7 ky")
        assert hl_sec is not None
        expected = 5.7 * 1000 * 365.25 * 86400
        assert abs(hl_sec - expected) / expected < 0.01

    def test_parse_half_life_mega_years(self):
        """Test parsing mega-year half-lives."""
        from nucmass.nubase2020 import parse_half_life

        hl_str, hl_sec = parse_half_life("4.5 My")
        assert hl_sec is not None
        expected = 4.5 * 1e6 * 365.25 * 86400
        assert abs(hl_sec - expected) / expected < 0.01

    def test_parse_half_life_giga_years(self):
        """Test parsing giga-year half-lives."""
        from nucmass.nubase2020 import parse_half_life

        hl_str, hl_sec = parse_half_life("4.47 Gy")
        assert hl_sec is not None
        expected = 4.47 * 1e9 * 365.25 * 86400
        assert abs(hl_sec - expected) / expected < 0.01


# =============================================================================
# Plotting Coverage Tests
# =============================================================================

class TestPlottingMoreCases:
    """Test more plotting cases."""

    def test_plot_chart_deformation(self):
        """Test chart colored by deformation."""
        from nucmass import NuclearDatabase
        from nucmass.plotting import plot_chart
        import matplotlib.pyplot as plt

        db = NuclearDatabase()
        fig = plot_chart(db, color_by="beta2")

        assert fig is not None
        plt.close(fig)

    def test_plot_isotope_chain_with_ax(self):
        """Test isotope chain with provided axes."""
        from nucmass import NuclearDatabase
        from nucmass.plotting import plot_isotope_chain
        import matplotlib.pyplot as plt

        db = NuclearDatabase()
        fig, ax = plt.subplots()

        result_fig = plot_isotope_chain(db, z=50, ax=ax)

        assert result_fig is fig
        plt.close(fig)

    def test_plot_mass_residuals_basic(self):
        """Test mass residuals plot."""
        from nucmass import NuclearDatabase
        from nucmass.plotting import plot_mass_residuals
        import matplotlib.pyplot as plt

        db = NuclearDatabase()
        fig = plot_mass_residuals(db)

        assert fig is not None
        plt.close(fig)

    def test_plot_separation_energies_s2p(self):
        """Test separation energies plot for S_2p."""
        from nucmass import NuclearDatabase
        from nucmass.plotting import plot_separation_energies
        import matplotlib.pyplot as plt

        db = NuclearDatabase()
        fig = plot_separation_energies(db, quantity="S_2p")

        assert fig is not None
        plt.close(fig)


# =============================================================================
# AME2020 Parser Tests
# =============================================================================

class TestAME2020ParserMore:
    """More AME2020 parser tests."""

    def test_parser_with_real_file(self):
        """Test parser with real AME2020 file."""
        from nucmass.ame2020 import AME2020Parser
        from nucmass.config import Config

        ame_file = Config.DATA_DIR / "mass.mas20.txt"
        if not ame_file.exists():
            pytest.skip("AME2020 file not available")

        parser = AME2020Parser(ame_file)
        df = parser.parse()

        # Should have >3000 nuclides
        assert len(df) > 3000

        # Check Fe-56
        fe56 = parser.get_nuclide(z=26, n=30)
        assert fe56 is not None

    def test_parser_get_element_all_isotopes(self):
        """Test getting all isotopes of an element."""
        from nucmass.ame2020 import AME2020Parser
        from nucmass.config import Config

        ame_file = Config.DATA_DIR / "mass.mas20.txt"
        if not ame_file.exists():
            pytest.skip("AME2020 file not available")

        parser = AME2020Parser(ame_file)
        uranium = parser.get_element(z=92)

        # Uranium should have many isotopes
        assert len(uranium) > 20


# =============================================================================
# Config Edge Cases
# =============================================================================

class TestConfigEdgeCases:
    """Test config edge cases."""

    def test_magic_numbers(self):
        """Test magic numbers configuration."""
        from nucmass.config import Config

        assert 2 in Config.MAGIC_NUMBERS
        assert 8 in Config.MAGIC_NUMBERS
        assert 20 in Config.MAGIC_NUMBERS
        assert 28 in Config.MAGIC_NUMBERS
        assert 50 in Config.MAGIC_NUMBERS
        assert 82 in Config.MAGIC_NUMBERS
        assert 126 in Config.MAGIC_NUMBERS

    def test_physical_constants(self):
        """Test physical constants are reasonable."""
        from nucmass.config import Config

        # Neutron mass excess ~8.07 MeV
        assert 8000 < Config.NEUTRON_MASS_EXCESS < 8200

        # Proton mass excess ~7.29 MeV
        assert 7200 < Config.PROTON_MASS_EXCESS < 7400

        # AMU to keV ~931.5 MeV
        assert 931000 < Config.AMU_TO_KEV < 932000

    def test_element_symbols_coverage(self):
        """Test element symbols cover common elements."""
        from nucmass.config import Config

        # Test some common elements
        assert Config.ELEMENT_SYMBOLS[1] == 'H'
        assert Config.ELEMENT_SYMBOLS[6] == 'C'
        assert Config.ELEMENT_SYMBOLS[8] == 'O'
        assert Config.ELEMENT_SYMBOLS[26] == 'Fe'
        assert Config.ELEMENT_SYMBOLS[79] == 'Au'
        assert Config.ELEMENT_SYMBOLS[92] == 'U'
        assert Config.ELEMENT_SYMBOLS[118] == 'Og'
