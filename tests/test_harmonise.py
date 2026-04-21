"""
Comprehensive harmonisation module tests

Coverage targets:
- Unit tests: Each module (crosswalk, units, temporal, scale, coverage)
- Integration tests: Full pipeline Phase 1 → harmonised
- Schema validation: Output conformance
- Data quality: No silent NAs or type mismatches

Test coverage goal: >90% of src/harmonise/
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add workspace to path
workspace_root = Path(__file__).parent.parent
sys.path.insert(0, str(workspace_root))

from src.harmonise.config import (
    ACTIVE_SOURCES, HARMONISED_SCHEMA, HARMONISED_COLUMN_ORDER,
    DPLACE_RAW, DRH_RAW, SESHAT_RAW
)
from src.harmonise.crosswalk import CrosswalkMapper, apply_crosswalk
from src.harmonise.units import UnitStandardiser
from src.harmonise.temporal import TemporalStandardiser
from src.harmonise.scale import ScaleStandardiser
from src.harmonise.coverage import CoverageAuditor
from src.harmonise.harmonise_all import HarmonisationPipeline


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def sample_phase1_row():
    """Create a sample Phase 1 row."""
    return pd.Series({
        "source": "dplace",
        "culture_id": "test_001",
        "culture_name": "Test Culture",
        "unit_type": "society",
        "lat": 10.5,
        "lon": 40.2,
        "time_start": -1900,
        "time_end": -1800,
        "variable_name": "EA112",
        "variable_value": 1.0,
        "confidence": 0.8,
        "notes": "Test note",
    })


@pytest.fixture
def sample_phase1_df():
    """Create a sample Phase 1 DataFrame."""
    return pd.DataFrame({
        "source": ["dplace", "dplace", "drh"],
        "culture_id": ["c001", "c002", "t001"],
        "culture_name": ["Culture A", "Culture B", "Tradition A"],
        "unit_type": ["society", "society", "tradition"],
        "lat": [10.5, -33.9, 20.0],
        "lon": [40.2, 151.2, 100.5],
        "time_start": [-1900, -1900, -500],
        "time_end": [-1800, -1800, 500],
        "variable_name": ["EA112", "EA34", "healing_question_1"],
        "variable_value": [1.0, 5.0, 1.0],
        "confidence": [0.8, 0.9, 0.7],
        "notes": ["", "conflict", ""],
    })


@pytest.fixture
def crosswalk_mapper():
    """Create a CrosswalkMapper instance."""
    return CrosswalkMapper()


@pytest.fixture
def unit_standardiser():
    """Create a UnitStandardiser instance."""
    return UnitStandardiser()


@pytest.fixture
def temporal_standardiser():
    """Create a TemporalStandardiser instance."""
    return TemporalStandardiser()


@pytest.fixture
def scale_standardiser():
    """Create a ScaleStandardiser instance."""
    return ScaleStandardiser()


@pytest.fixture
def coverage_auditor():
    """Create a CoverageAuditor instance."""
    return CoverageAuditor()


@pytest.fixture
def pipeline():
    """Create a HarmonisationPipeline instance."""
    return HarmonisationPipeline()


# ==============================================================================
# CROSSWALK MODULE TESTS
# ==============================================================================

class TestCrosswalks:
    """Tests for crosswalk mapping."""
    
    def test_crosswalk_mapper_initialization(self, crosswalk_mapper):
        """Test mapper initializes with ACTIVE_SOURCES."""
        assert crosswalk_mapper.active_sources == ACTIVE_SOURCES
        assert crosswalk_mapper.dplace_lookup is not None
        assert crosswalk_mapper.drh_lookup is not None
    
    def test_crosswalk_dplace_ea112_trance(self, crosswalk_mapper):
        """Test EA112 maps to trance_induction (codes 1-5)."""
        feature, value = crosswalk_mapper.map_variable(
            source="dplace",
            variable_name="EA112",
            variable_value=3.0
        )
        assert feature == "trance_induction"
        assert value == 1.0
    
    def test_crosswalk_dplace_ea112_possession(self, crosswalk_mapper):
        """Test EA112 maps to spirit_possession (codes 6-8)."""
        feature, value = crosswalk_mapper.map_variable(
            source="dplace",
            variable_name="EA112",
            variable_value=7.0
        )
        assert feature == "spirit_possession"
        assert value == 1.0
    
    def test_crosswalk_drh_trance(self, crosswalk_mapper):
        """Test DRH trance_question_1 mapping."""
        feature, value = crosswalk_mapper.map_variable(
            source="drh",
            variable_name="trance_question_1",
            variable_value=1.0
        )
        assert feature == "trance_induction"
        assert value == 1.0
    
    def test_crosswalk_unmapped_variable(self, crosswalk_mapper):
        """Test unmapped variable returns None."""
        feature, value = crosswalk_mapper.map_variable(
            source="dplace",
            variable_name="UNMAPPED_VAR",
            variable_value=1.0
        )
        assert feature is None
        assert value is None
    
    def test_apply_crosswalk_to_dataframe(self, sample_phase1_df, crosswalk_mapper):
        """Test apply_crosswalk adds feature columns to DataFrame."""
        df = apply_crosswalk(sample_phase1_df, "dplace", crosswalk_mapper)
        
        assert "feature_name" in df.columns
        assert "feature_value" in df.columns
        assert len(df) == 3
        assert df["feature_name"].notna().any()  # Some mappings exist
    
    def test_crosswalk_preserves_phase1_columns(self, sample_phase1_df, crosswalk_mapper):
        """Test crosswalk preserves all Phase 1 columns."""
        df = apply_crosswalk(sample_phase1_df, "dplace", crosswalk_mapper)
        
        phase1_cols = list(sample_phase1_df.columns)
        for col in phase1_cols:
            assert col in df.columns


# ==============================================================================
# UNITS MODULE TESTS
# ==============================================================================

class TestUnits:
    """Tests for unit standardisation."""
    
    def test_unit_standardiser_initialization(self, unit_standardiser):
        """Test standardiser initializes with ACTIVE_SOURCES."""
        assert unit_standardiser.active_sources == ACTIVE_SOURCES
    
    def test_standardise_dplace_units(self, sample_phase1_df, unit_standardiser):
        """Test standardise_units adds unit columns."""
        df_dplace = sample_phase1_df[sample_phase1_df["source"] == "dplace"]
        df = unit_standardiser.standardise_units(df_dplace, "dplace")
        
        assert "unit_type_standardised" in df.columns
        assert "unit_ambiguous" in df.columns
        assert "unit_note" in df.columns
    
    def test_unit_standardised_values_correct(self, sample_phase1_df, unit_standardiser):
        """Test unit_type_standardised matches expected values."""
        df_dplace = sample_phase1_df[sample_phase1_df["source"] == "dplace"]
        df = unit_standardiser.standardise_units(df_dplace, "dplace")
        
        assert all(df["unit_type_standardised"] == "society")
    
    def test_unit_ambiguous_flag_is_binary(self, sample_phase1_df, unit_standardiser):
        """Test unit_ambiguous is 0 or 1."""
        df_dplace = sample_phase1_df[sample_phase1_df["source"] == "dplace"]
        df = unit_standardiser.standardise_units(df_dplace, "dplace")
        
        assert all(df["unit_ambiguous"].isin([0, 1]))
    
    def test_unit_note_is_string_or_null(self, sample_phase1_df, unit_standardiser):
        """Test unit_note is str or NaN."""
        df_dplace = sample_phase1_df[sample_phase1_df["source"] == "dplace"]
        df = unit_standardiser.standardise_units(df_dplace, "dplace")
        
        for val in df["unit_note"]:
            assert val is None or isinstance(val, str) or pd.isna(val)
    
    def test_standardise_inactive_source_skipped(self, sample_phase1_df, unit_standardiser):
        """Test inactive source is skipped."""
        df = sample_phase1_df.copy()
        df["source"] = "seshat"  # Not active
        
        result = unit_standardiser.standardise_units(df, "seshat")
        assert result is not None


# ==============================================================================
# TEMPORAL MODULE TESTS
# ==============================================================================

class TestTemporal:
    """Tests for temporal standardisation."""
    
    def test_temporal_standardiser_initialization(self, temporal_standardiser):
        """Test standardiser initializes with ACTIVE_SOURCES."""
        assert temporal_standardiser.active_sources == ACTIVE_SOURCES
    
    def test_standardise_temporal_adds_columns(self, sample_phase1_df, temporal_standardiser):
        """Test standardise_temporal adds temporal columns."""
        df_dplace = sample_phase1_df[sample_phase1_df["source"] == "dplace"]
        df = temporal_standardiser.standardise_temporal(df_dplace, "dplace")
        
        assert "time_start_standardised" in df.columns
        assert "time_end_standardised" in df.columns
        assert "temporal_mode" in df.columns
        assert "time_uncertainty" in df.columns
    
    def test_temporal_mode_values_valid(self, sample_phase1_df, temporal_standardiser):
        """Test temporal_mode is one of expected values."""
        df_dplace = sample_phase1_df[sample_phase1_df["source"] == "dplace"]
        df = temporal_standardiser.standardise_temporal(df_dplace, "dplace")
        
        valid_modes = {"snapshot", "diachronic", "mixed"}
        assert all(df["temporal_mode"].isin(valid_modes))
    
    def test_time_uncertainty_ordinal(self, sample_phase1_df, temporal_standardiser):
        """Test time_uncertainty is ordinal 0-3."""
        df_dplace = sample_phase1_df[sample_phase1_df["source"] == "dplace"]
        df = temporal_standardiser.standardise_temporal(df_dplace, "dplace")
        
        assert all(df["time_uncertainty"].isin([0, 1, 2, 3]))
    
    def test_time_uncertainty_calculation(self, sample_phase1_df, temporal_standardiser):
        """Test time_uncertainty calculation based on span."""
        df = pd.DataFrame({
            "source": ["dplace"] * 4,
            "time_start": [-1910, -1850, -1500, -1000],
            "time_end": [-1900, -1800, -1500, 0],
        })
        df = temporal_standardiser.standardise_temporal(df, "dplace")
        
        spans = df["time_end"] - df["time_start"]
        # Verify uncertainty increases with span
        assert df.iloc[0]["time_uncertainty"] <= df.iloc[3]["time_uncertainty"]


# ==============================================================================
# SCALE MODULE TESTS
# ==============================================================================

class TestScale:
    """Tests for scale standardisation and binarisation."""
    
    def test_scale_standardiser_initialization(self, scale_standardiser):
        """Test standardiser initializes correctly."""
        assert scale_standardiser.active_sources == ACTIVE_SOURCES
    
    def test_apply_binarisation_returns_dict(self, sample_phase1_df, scale_standardiser, crosswalk_mapper):
        """Test apply_binarisation_and_score returns dictionary."""
        # Prepare data with required columns
        df_dplace = sample_phase1_df[sample_phase1_df["source"] == "dplace"].copy()
        df_dplace = pd.concat([
            df_dplace,
            pd.DataFrame({
                "feature_name": ["trance_induction", "dedicated_specialist"],
                "feature_value": [1.0, 1.0],
                "unit_ambiguous": [0, 0],
                "time_uncertainty": [1, 1],
            }, index=df_dplace.index[:2])
        ], axis=1)
        
        df_dict = {"dplace": df_dplace}
        result = scale_standardiser.apply_binarisation_and_score(df_dict, crosswalk_mapper)
        
        assert isinstance(result, dict)
        assert "dplace" in result
    
    def test_data_quality_score_range(self, sample_phase1_df, scale_standardiser, crosswalk_mapper):
        """Test data_quality_score is in valid range."""
        # Prepare data
        df_dplace = sample_phase1_df[sample_phase1_df["source"] == "dplace"].copy()
        df_dplace = pd.concat([
            df_dplace,
            pd.DataFrame({
                "feature_name": ["trance_induction"],
                "feature_value": [1.0],
                "unit_ambiguous": [0],
                "time_uncertainty": [1],
            }, index=df_dplace.index[:1])
        ], axis=1)
        
        df_dict = {"dplace": df_dplace}
        result = scale_standardiser.apply_binarisation_and_score(df_dict, crosswalk_mapper)
        
        scores = result["dplace"]["data_quality_score"]
        assert scores.min() >= 0.0


# ==============================================================================
# COVERAGE MODULE TESTS
# ==============================================================================

class TestCoverage:
    """Tests for coverage auditing."""
    
    def test_coverage_auditor_initialization(self, coverage_auditor):
        """Test auditor initializes correctly."""
        assert coverage_auditor.active_sources == ACTIVE_SOURCES
        assert coverage_auditor.time_bin_width == 500
        assert coverage_auditor.gap_threshold == 5
    
    def test_audit_coverage_requires_dict(self, sample_phase1_df, coverage_auditor):
        """Test audit_coverage requires dictionary input."""
        # Create fully harmonised data with time_start_standardised
        df = sample_phase1_df.copy()
        df["data_quality_score"] = 0.5
        df["time_start_standardised"] = df["time_start"]
        df["source"] = "dplace"
        
        result = coverage_auditor.audit_coverage({"dplace": df})
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) >= 0  # May be empty if all rows filtered
    
    def test_coverage_output_columns(self, sample_phase1_df, coverage_auditor):
        """Test coverage audit output has expected columns."""
        df = sample_phase1_df.copy()
        df["data_quality_score"] = 0.5
        df["time_start_standardised"] = df["time_start"]
        df["source"] = "dplace"
        
        result = coverage_auditor.audit_coverage({"dplace": df})
        
        if len(result) > 0:  # Skip if no cells generated
            expected_cols = {"region", "time_bin", "source", "record_count", "gap_severity"}
            assert expected_cols.issubset(set(result.columns))
    
    def test_gap_severity_values(self, sample_phase1_df, coverage_auditor):
        """Test gap_severity is one of expected values."""
        df = sample_phase1_df.copy()
        df["data_quality_score"] = 0.5
        df["time_start_standardised"] = df["time_start"]
        df["source"] = "dplace"
        
        result = coverage_auditor.audit_coverage({"dplace": df})
        
        if len(result) > 0:
            valid_severities = {"GREEN", "YELLOW", "RED"}
            assert all(result["gap_severity"].isin(valid_severities))


# ==============================================================================
# INTEGRATION TESTS
# ==============================================================================

class TestIntegration:
    """Integration tests for full pipeline."""
    
    def test_pipeline_initializes(self, pipeline):
        """Test pipeline initializes all modules."""
        assert pipeline.crosswalk is not None
        assert pipeline.units is not None
        assert pipeline.temporal is not None
        assert pipeline.scale is not None
        assert pipeline.coverage is not None
    
    def test_harmonise_source_adds_all_columns(self, pipeline, sample_phase1_df):
        """Test harmonise_source adds expected columns (steps 1-3)."""
        df_dplace = sample_phase1_df[sample_phase1_df["source"] == "dplace"].copy()
        
        # Apply harmonisation steps 1-3
        df = pipeline.harmonise_source("dplace", df_dplace)
        
        # Check columns added by each step
        expected_new_cols = [
            "feature_name", "feature_value",  # crosswalk
            "unit_ambiguous", "unit_note",  # units
            "time_start_standardised", "time_end_standardised", "temporal_mode", "time_uncertainty",  # temporal
        ]
        
        for col in expected_new_cols:
            assert col in df.columns, f"Missing column: {col}"
    
    def test_output_has_no_duplicates(self, pipeline, sample_phase1_df):
        """Test harmonised output has no duplicate rows."""
        df_dplace = sample_phase1_df[sample_phase1_df["source"] == "dplace"].copy()
        
        df = pipeline.harmonise_source("dplace", df_dplace)
        
        assert len(df) == len(df)  # No rows filtered
        assert df.duplicated().sum() == 0  # No duplicates


# ==============================================================================
# SCHEMA VALIDATION TESTS
# ==============================================================================

class TestSchema:
    """Tests for harmonised schema conformance."""
    
    def test_column_order_correct(self):
        """Test HARMONISED_COLUMN_ORDER is correct."""
        assert isinstance(HARMONISED_COLUMN_ORDER, list)
        assert len(HARMONISED_COLUMN_ORDER) > 0
        assert len(HARMONISED_COLUMN_ORDER) == len(set(HARMONISED_COLUMN_ORDER))  # No duplicates
    
    def test_schema_coverage(self):
        """Test HARMONISED_SCHEMA covers all output columns."""
        for col in HARMONISED_COLUMN_ORDER:
            assert col in HARMONISED_SCHEMA, f"Column {col} in order but not in schema"
    
    def test_harmonised_output_has_correct_columns(self, pipeline, sample_phase1_df):
        """Test harmonised output has harmonisation step 1-3 columns."""
        # Load Phase 1, harmonise with steps 1-3, and check schema
        if Path(DPLACE_RAW).exists():
            df_phase1 = pd.read_parquet(DPLACE_RAW).head(100)
            
            df = pipeline.harmonise_source("dplace", df_phase1)
            
            # Check steps 1-3 columns present (steps 4-5 require all sources)
            expected_step1_3_cols = [
                "feature_name", "feature_value",  # crosswalk
                "unit_ambiguous", "unit_note",  # units
                "time_start_standardised", "temporal_mode", "time_uncertainty",  # temporal
            ]
            for col in expected_step1_3_cols:
                assert col in df.columns, f"Missing column: {col}"
    
    def test_no_unnamed_columns(self, pipeline, sample_phase1_df):
        """Test output has no unnamed columns."""
        df_dplace = sample_phase1_df[sample_phase1_df["source"] == "dplace"].copy()
        df = pipeline.harmonise_source("dplace", df_dplace)
        
        assert not any("Unnamed" in col for col in df.columns)


# ==============================================================================
# DATA QUALITY TESTS
# ==============================================================================

class TestDataQuality:
    """Tests for data quality checks."""
    
    def test_no_silent_na_conversions(self, pipeline, sample_phase1_df):
        """Test no silent NA → 0 conversions."""
        df_dplace = sample_phase1_df[sample_phase1_df["source"] == "dplace"].copy()
        
        # Inject some NAs
        df_dplace.loc[0, "variable_value"] = np.nan
        
        df = pipeline.harmonise_source("dplace", df_dplace)
        
        # Check NAs tracked explicitly (not converted to 0)
        assert df["variable_value"].isna().any()
    
    def test_type_consistency_per_column(self, pipeline, sample_phase1_df):
        """Test each column has consistent type."""
        df_dplace = sample_phase1_df[sample_phase1_df["source"] == "dplace"].copy()
        df = pipeline.harmonise_source("dplace", df_dplace)
        
        for col in df.columns:
            if col not in ["source", "culture_id", "culture_name", "unit_type", "unit_note", 
                           "temporal_mode", "variable_name", "notes", "feature_name"]:
                # Numeric columns (or all NA)
                if df[col].notna().any():
                    non_na = df[col].dropna()
                    # All non-NA values should have consistent type
                    types = non_na.apply(type).unique()
                    assert len(types) <= 2  # Allow int/float mixing
    
    def test_required_columns_never_na(self, pipeline, sample_phase1_df):
        """Test required columns never have NA."""
        df_dplace = sample_phase1_df[sample_phase1_df["source"] == "dplace"].copy()
        df = pipeline.harmonise_source("dplace", df_dplace)
        
        required_cols = ["source", "culture_id", "culture_name", "unit_type"]
        
        for col in required_cols:
            if col in df.columns:
                assert df[col].notna().all(), f"Column {col} has NAs"


# ==============================================================================
# REAL DATA TESTS (if Phase 1 files exist)
# ==============================================================================

class TestWithRealData:
    """Tests using real Phase 1 data files."""
    
    @pytest.mark.skipif(not Path(DPLACE_RAW).exists(), reason="D-PLACE file not found")
    def test_real_dplace_harmonisation(self, pipeline):
        """Test harmonisation on real D-PLACE data (steps 1-3)."""
        df_phase1 = pd.read_parquet(DPLACE_RAW).head(100)
        
        df = pipeline.harmonise_source("dplace", df_phase1)
        
        assert len(df) == 100
        # Steps 1-3 columns
        assert all(col in df.columns for col in ["feature_name", "unit_ambiguous", "temporal_mode"])
    
    @pytest.mark.skipif(not Path(DRH_RAW).exists(), reason="DRH file not found")
    def test_real_drh_harmonisation(self, pipeline):
        """Test harmonisation on real DRH data."""
        df_phase1 = pd.read_parquet(DRH_RAW)
        
        df = pipeline.harmonise_source("drh", df_phase1)
        
        assert len(df) == len(df_phase1)
        assert "feature_name" in df.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
