"""Tests for nuclear mass data parsing and validation."""

import pytest
import pandas as pd
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nucmass.database import NuclearDatabase

DATA_DIR = Path(__file__).parent.parent / "data"


class TestAME2020:
    """Tests for AME2020 experimental mass data."""

    @pytest.fixture
    def ame_df(self):
        return pd.read_csv(DATA_DIR / "ame2020_masses.csv")

    def test_data_loaded(self, ame_df):
        """Test that AME2020 data is loaded with expected size."""
        assert len(ame_df) > 3000, "Should have >3000 nuclides"
        assert len(ame_df) < 4000, "Should have <4000 nuclides"

    def test_required_columns(self, ame_df):
        """Test that required columns exist."""
        required = ["Z", "N", "A", "Element", "Mass_excess_keV", "Binding_energy_per_A_keV"]
        for col in required:
            assert col in ame_df.columns, f"Missing column: {col}"

    def test_mass_number_consistency(self, ame_df):
        """Test that A = Z + N for all nuclides."""
        invalid = ame_df[ame_df["A"] != ame_df["Z"] + ame_df["N"]]
        assert len(invalid) == 0, f"Found {len(invalid)} nuclides with A != Z+N"

    def test_fe56_mass_excess(self, ame_df):
        """Test Fe-56 mass excess (well-known value)."""
        fe56 = ame_df[(ame_df["Z"] == 26) & (ame_df["N"] == 30)]
        assert len(fe56) == 1, "Should find exactly one Fe-56"
        # Fe-56 mass excess is approximately -60.6 MeV = -60600 keV
        mass_excess = fe56.iloc[0]["Mass_excess_keV"]
        assert -60700 < mass_excess < -60500, f"Fe-56 mass excess {mass_excess} out of range"

    def test_fe56_binding_energy(self, ame_df):
        """Test Fe-56 has highest binding energy per nucleon."""
        fe56 = ame_df[(ame_df["Z"] == 26) & (ame_df["N"] == 30)]
        ba = fe56.iloc[0]["Binding_energy_per_A_keV"]
        # Fe-56 B/A ~ 8.79 MeV = 8790 keV
        assert 8750 < ba < 8850, f"Fe-56 B/A {ba} out of expected range"

    def test_z_range(self, ame_df):
        """Test Z range covers expected elements."""
        assert ame_df["Z"].min() >= 0, "Z should be non-negative"
        assert ame_df["Z"].max() >= 100, "Should include superheavy elements"

    def test_neutron_data(self, ame_df):
        """Test that neutron (Z=0, N=1) exists."""
        neutron = ame_df[(ame_df["Z"] == 0) & (ame_df["N"] == 1)]
        assert len(neutron) == 1, "Should have neutron data"

    def test_no_duplicate_nuclides(self, ame_df):
        """Test no duplicate Z,N,A combinations."""
        duplicates = ame_df.duplicated(subset=["Z", "N", "A"], keep=False)
        assert duplicates.sum() == 0, f"Found {duplicates.sum()} duplicate entries"


class TestFRDM2012:
    """Tests for FRDM2012 theoretical mass data."""

    @pytest.fixture
    def frdm_df(self):
        return pd.read_csv(DATA_DIR / "frdm2012_masses.csv")

    def test_data_loaded(self, frdm_df):
        """Test that FRDM2012 data is loaded with expected size."""
        assert len(frdm_df) > 8000, "Should have >8000 nuclides"
        assert len(frdm_df) < 10000, "Should have <10000 nuclides"

    def test_required_columns(self, frdm_df):
        """Test that required columns exist."""
        required = ["Z", "N", "A", "M_th", "E_bind", "beta2"]
        for col in required:
            assert col in frdm_df.columns, f"Missing column: {col}"

    def test_mass_number_consistency(self, frdm_df):
        """Test that A = Z + N for all nuclides."""
        invalid = frdm_df[frdm_df["A"] != frdm_df["Z"] + frdm_df["N"]]
        assert len(invalid) == 0, f"Found {len(invalid)} nuclides with A != Z+N"

    def test_fe56_theoretical_mass(self, frdm_df):
        """Test Fe-56 theoretical mass excess."""
        fe56 = frdm_df[(frdm_df["Z"] == 26) & (frdm_df["N"] == 30)]
        assert len(fe56) == 1, "Should find exactly one Fe-56"
        # FRDM2012 M_th is in MeV, should be ~-60.5 MeV
        m_th = fe56.iloc[0]["M_th"]
        assert -61 < m_th < -60, f"Fe-56 M_th {m_th} out of range"

    def test_deformation_parameters(self, frdm_df):
        """Test deformation parameters are present and reasonable."""
        # beta2 values typically range from -0.4 to 0.6
        assert frdm_df["beta2"].min() > -1, "beta2 min out of range"
        assert frdm_df["beta2"].max() < 1, "beta2 max out of range"

    def test_z_range(self, frdm_df):
        """Test Z range starts at O (Z=8) as per FRDM2012."""
        assert frdm_df["Z"].min() == 8, "FRDM2012 should start at Z=8 (Oxygen)"
        assert frdm_df["Z"].max() >= 110, "Should include superheavy elements"

    def test_pb208_doubly_magic(self, frdm_df):
        """Test Pb-208 (doubly magic nucleus) has small deformation."""
        pb208 = frdm_df[(frdm_df["Z"] == 82) & (frdm_df["N"] == 126)]
        assert len(pb208) == 1, "Should find Pb-208"
        # Doubly magic nuclei are spherical (beta2 ~ 0)
        beta2 = pb208.iloc[0]["beta2"]
        assert abs(beta2) < 0.1, f"Pb-208 should be spherical, got beta2={beta2}"

    def test_no_duplicate_nuclides(self, frdm_df):
        """Test no duplicate Z,N,A combinations."""
        duplicates = frdm_df.duplicated(subset=["Z", "N", "A"], keep=False)
        assert duplicates.sum() == 0, f"Found {duplicates.sum()} duplicate entries"


class TestDatasetComparison:
    """Tests comparing AME2020 and FRDM2012 datasets."""

    @pytest.fixture
    def both_df(self):
        ame = pd.read_csv(DATA_DIR / "ame2020_masses.csv")
        frdm = pd.read_csv(DATA_DIR / "frdm2012_masses.csv")
        return ame, frdm

    def test_overlap_exists(self, both_df):
        """Test that datasets have significant overlap."""
        ame, frdm = both_df
        merged = pd.merge(ame[["Z", "N", "A"]], frdm[["Z", "N", "A"]], on=["Z", "N", "A"])
        assert len(merged) > 3000, f"Expected >3000 overlapping nuclides, got {len(merged)}"

    def test_frdm_extends_ame(self, both_df):
        """Test that FRDM2012 predicts nuclides beyond AME2020."""
        ame, frdm = both_df
        frdm_only = frdm[~frdm.set_index(["Z", "N", "A"]).index.isin(
            ame.set_index(["Z", "N", "A"]).index
        )]
        assert len(frdm_only) > 4000, "FRDM should predict many unmeasured nuclides"

    def test_mass_agreement(self, both_df):
        """Test that masses agree within FRDM2012 uncertainty (~0.6 MeV)."""
        ame, frdm = both_df

        # Merge on Z, N, A
        merged = pd.merge(
            ame[["Z", "N", "A", "Mass_excess_keV"]],
            frdm[["Z", "N", "A", "M_th"]],
            on=["Z", "N", "A"]
        )

        # Convert AME keV to MeV for comparison
        merged["M_exp_MeV"] = merged["Mass_excess_keV"] / 1000
        merged["diff_MeV"] = abs(merged["M_exp_MeV"] - merged["M_th"])

        # Most should agree within 2 MeV (3.5 sigma for FRDM)
        within_2mev = (merged["diff_MeV"] < 2).mean()
        assert within_2mev > 0.9, f"Only {within_2mev:.1%} agree within 2 MeV"


class TestDuckDB:
    """Tests for DuckDB database interface."""

    @pytest.fixture
    def db(self):
        db = NuclearDatabase()
        yield db
        db.close()

    def test_database_exists(self, db):
        """Test that database file is created when accessed."""
        # Access the connection to trigger lazy initialization
        _ = db.conn
        assert db.db_path.exists(), "Database file should exist after connection"

    def test_summary_counts(self, db):
        """Test summary statistics."""
        stats = db.summary()
        assert stats["ame2020_count"] > 3000
        assert stats["frdm2012_count"] > 8000
        assert stats["total_nuclides"] > 8000
        assert stats["both_exp_and_th"] > 3000
        assert stats["predicted_only"] > 5000

    def test_get_nuclide(self, db):
        """Test getting a specific nuclide."""
        fe56 = db.get_nuclide(26, 30)
        assert fe56 is not None
        assert fe56["Z"] == 26
        assert fe56["N"] == 30
        assert fe56["A"] == 56
        assert fe56["has_experimental"] == True
        assert fe56["has_theoretical"] == True

    def test_get_isotopes(self, db):
        """Test getting isotopes of an element."""
        # Iron isotopes
        fe_isotopes = db.get_isotopes(26)
        assert len(fe_isotopes) > 20, "Should have many Fe isotopes"
        assert (fe_isotopes["Z"] == 26).all(), "All should be Fe"

    def test_get_isotones(self, db):
        """Test getting isotones (same N)."""
        n50 = db.get_isotones(50)  # N=50 magic number
        assert len(n50) > 20, "Should have many N=50 isotones"
        assert (n50["N"] == 50).all(), "All should have N=50"

    def test_get_isobars(self, db):
        """Test getting isobars (same A)."""
        a100 = db.get_isobars(100)
        assert len(a100) > 5, "Should have several A=100 isobars"
        assert (a100["A"] == 100).all(), "All should have A=100"

    def test_get_deformed(self, db):
        """Test getting highly deformed nuclei."""
        deformed = db.get_deformed(min_beta2=0.3)
        assert len(deformed) > 100, "Should have many deformed nuclei"
        assert (deformed["beta2"].abs() >= 0.3).all(), "All should be deformed"

    def test_get_predicted_only(self, db):
        """Test getting predicted-only nuclides."""
        predicted = db.get_predicted_only()
        assert len(predicted) > 5000, "Should have >5000 predicted-only nuclides"
        assert (predicted["has_experimental"] == False).all()
        assert (predicted["has_theoretical"] == True).all()

    def test_sql_query(self, db):
        """Test raw SQL query capability."""
        result = db.query("SELECT COUNT(*) as cnt FROM nuclides WHERE Z = 92")
        assert result.iloc[0]["cnt"] > 30, "Should have many uranium isotopes"

    def test_mass_comparison_view(self, db):
        """Test the combined nuclides view has correct columns."""
        result = db.query("SELECT * FROM nuclides LIMIT 1")
        required_cols = [
            "Z", "N", "A", "mass_excess_exp_keV", "mass_excess_th_keV",
            "beta2", "has_experimental", "has_theoretical"
        ]
        for col in required_cols:
            assert col in result.columns, f"Missing column in view: {col}"
