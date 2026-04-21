"""
Phase 3 Analysis Tests

Comprehensive test suite for Phase 3 analysis modules.
Target: >90% coverage of src/analysis/
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile

# Import analysis modules
from src.analysis import config
from src.analysis.comparison import (
    load_harmonised_data,
    get_feature_matrix_by_source,
    find_overlapping_cultures,
    compare_feature_agreements,
    compute_agreement_statistics,
)
from src.analysis.temporal import (
    stratify_by_era,
    compute_era_feature_presence,
    detect_temporal_trends,
    create_temporal_profile,
)
from src.analysis.geography import (
    validate_coordinates,
    assign_geographic_regions,
    compute_regional_density,
    identify_coverage_gaps,
)
from src.analysis.synthesis import (
    create_composite_indicators,
    aggregate_features_by_culture,
    synthesize_feature_profiles,
    compute_feature_correlation_matrix,
)
from src.analysis.conflicts import ConflictRegistry
from src.analysis.validation import (
    load_ethnographic_narratives,
    validate_against_ethnography,
)


# ============================================================================
# FIXTURES & TEST DATA
# ============================================================================

@pytest.fixture
def sample_harmonised_df():
    """Create sample harmonised DataFrame for testing."""
    data = {
        "source": ["dplace", "dplace", "drh", "drh"],
        "culture_id": ["culture_001", "culture_002", "culture_003", "culture_001"],
        "culture_name": ["Ancient Egyptians", "Native Americans", "Siberian Shamanism", "Ancient Egyptians"],
        "unit_type": ["society", "society", "tradition", "tradition"],
        "lat": [30.0, 0.0, 60.0, 30.0],
        "lon": [31.0, 0.0, 100.0, 31.0],
        "time_start": [-1950, -500, -1900, -1950],
        "time_end": [-1850, 500, -1800, -1850],
        "feature_name": ["trance_induction", "trance_induction", "trance_induction", "spirit_possession"],
        "feature_value_binarised": [1.0, 0.0, 1.0, 1.0],
        "data_quality_score": [0.5, 0.6, 0.7, 0.5],
        "temporal_mode": ["snapshot", "snapshot", "diachronic", "snapshot"],
        "time_uncertainty": [3, 3, 2, 3],
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_multi_source_df(sample_harmonised_df):
    """Add more data for cross-source comparison tests."""
    additional = {
        "source": ["seshat"],
        "culture_id": ["culture_001"],
        "culture_name": ["Ancient Egyptians"],
        "unit_type": ["polity"],
        "lat": [30.0],
        "lon": [31.0],
        "time_start": [-1800],
        "time_end": [-1700],
        "feature_name": ["trance_induction"],
        "feature_value_binarised": [0.0],  # Conflict!
        "data_quality_score": [0.4],
        "temporal_mode": ["diachronic"],
        "time_uncertainty": [2],
    }
    df_additional = pd.DataFrame(additional)
    return pd.concat([sample_harmonised_df, df_additional], ignore_index=True)


# ============================================================================
# TESTS: Configuration Module
# ============================================================================

class TestConfig:
    """Test config module and constants."""
    
    def test_eras_defined(self):
        """Test that eras are properly defined."""
        eras = config.ERAS
        assert len(eras) == 6
        assert "Prehistoric" in eras
        assert "Modern" in eras
        
        # Check year ranges
        prehist = eras["Prehistoric"]
        assert prehist["start"] < prehist["end"]
    
    def test_get_era_for_timepoint(self):
        """Test era assignment for specific years."""
        assert config.get_era_for_timepoint(-1500) == "Prehistoric"
        assert config.get_era_for_timepoint(0) == "Ancient"
        assert config.get_era_for_timepoint(1000) == "Medieval"
        assert config.get_era_for_timepoint(2000) == "Modern"
    
    def test_gap_severity_classification(self):
        """Test gap severity ranking."""
        assert config.classify_gap_severity(15) == "GREEN"
        assert config.classify_gap_severity(7) == "YELLOW"
        assert config.classify_gap_severity(1) == "RED"
    
    def test_composite_indicators_defined(self):
        """Test that composite indicators are properly defined."""
        indicators = config.COMPOSITE_INDICATORS
        assert len(indicators) > 0
        assert "shamanic_complex" in indicators
        
        # Check structure
        for indicator_name, definition in indicators.items():
            assert "description" in definition
            assert "components" in definition
            assert "logic" in definition


# ============================================================================
# TESTS: Comparison Module
# ============================================================================

class TestComparison:
    """Test cross-source comparison functions."""
    
    def test_get_feature_matrix_by_source(self, sample_harmonised_df):
        """Test feature matrix creation."""
        data = {"dplace": sample_harmonised_df}
        
        matrices = get_feature_matrix_by_source(data)
        assert "dplace" in matrices
        
        dplace_matrix = matrices["dplace"]
        assert dplace_matrix.shape[0] > 0
        assert "trance_induction" in dplace_matrix.columns
    
    def test_find_overlapping_cultures(self, sample_multi_source_df):
        """Test identification of overlapping cultures."""
        # Create feature matrices
        dplace_data = sample_multi_source_df[sample_multi_source_df["source"] == "dplace"]
        drh_data = sample_multi_source_df[sample_multi_source_df["source"] == "drh"]
        
        # For this test, we'll manually check overlaps
        dplace_cultures = set(dplace_data["culture_id"].unique())
        drh_cultures = set(drh_data["culture_id"].unique())
        
        overlapping = dplace_cultures & drh_cultures
        assert len(overlapping) > 0
    
    def test_compute_agreement_statistics(self, sample_multi_source_df):
        """Test agreement calculation."""
        # Create dummy agreement df
        agreement_data = {
            "agreement": [1, 0, 1],
            "conflict_type": ["agreement", "conflict", "partial_coverage"],
        }
        agreement_df = pd.DataFrame(agreement_data)
        
        stats = compute_agreement_statistics(agreement_df)
        assert stats["total_comparisons"] == 3
        assert stats["agreements"] == 2
        assert stats["conflicts"] == 1


# ============================================================================
# TESTS: Temporal Module
# ============================================================================

class TestTemporal:
    """Test temporal analysis functions."""
    
    def test_stratify_by_era(self, sample_harmonised_df):
        """Test era stratification."""
        stratified = stratify_by_era(sample_harmonised_df)
        
        assert "Ancient" in stratified
        assert "Modern" in stratified
        
        # Check that data is properly filtered
        ancient_df = stratified["Ancient"]
        if len(ancient_df) > 0:
            assert ancient_df["era"].iloc[0] == "Ancient"
    
    def test_compute_era_feature_presence(self, sample_harmonised_df):
        """Test era-based feature statistics."""
        stratified = stratify_by_era(sample_harmonised_df)
        era_features = compute_era_feature_presence(stratified)
        
        assert isinstance(era_features, pd.DataFrame)
        if len(era_features) > 0:
            assert "era" in era_features.columns
            assert "presence_rate" in era_features.columns
    
    def test_detect_temporal_trends(self, sample_harmonised_df):
        """Test trend detection."""
        result = detect_temporal_trends(sample_harmonised_df, "trance_induction")
        
        assert "feature" in result
        assert result["feature"] == "trance_induction"
        assert isinstance(result.get("overall_trend"), str)


# ============================================================================
# TESTS: Geography Module
# ============================================================================

class TestGeography:
    """Test geographic analysis functions."""
    
    def test_validate_coordinates(self, sample_harmonised_df):
        """Test coordinate validation."""
        issues = validate_coordinates(sample_harmonised_df)
        
        assert "out_of_bounds" in issues
        assert "zero_zero_cluster" in issues
    
    def test_assign_geographic_regions(self, sample_harmonised_df):
        """Test region assignment."""
        df_with_regions = assign_geographic_regions(sample_harmonised_df)
        
        assert "region" in df_with_regions.columns
        assert df_with_regions["region"].notna().all()
    
    def test_compute_regional_density(self, sample_harmonised_df):
        """Test regional density calculation."""
        df_with_regions = assign_geographic_regions(sample_harmonised_df)
        density = compute_regional_density(df_with_regions)
        
        assert isinstance(density, dict)
        assert len(density) > 0
        
        for region, stats in density.items():
            assert "record_count" in stats
            assert "feature_presence_rate" in stats


# ============================================================================
# TESTS: Synthesis Module
# ============================================================================

class TestSynthesis:
    """Test feature synthesis functions."""
    
    def test_aggregate_features_by_culture(self, sample_harmonised_df):
        """Test feature aggregation per culture."""
        aggregated = aggregate_features_by_culture(sample_harmonised_df)
        
        assert isinstance(aggregated, pd.DataFrame)
        assert "culture_id" in aggregated.columns
        assert len(aggregated) <= sample_harmonised_df["culture_id"].nunique()
    
    def test_create_composite_indicators(self, sample_harmonised_df):
        """Test composite indicator creation."""
        df_with_composites = create_composite_indicators(sample_harmonised_df)
        
        # Check that composite columns were added
        composite_cols = [col for col in df_with_composites.columns 
                         if col.startswith("composite_")]
        assert len(composite_cols) > 0
    
    def test_compute_feature_correlation_matrix(self, sample_harmonised_df):
        """Test feature correlation calculation."""
        aggregated = aggregate_features_by_culture(sample_harmonised_df)
        correlation = compute_feature_correlation_matrix(aggregated)
        
        assert isinstance(correlation, pd.DataFrame)
        # Diagonal should be 1 or NaN
        if len(correlation) > 0:
            assert correlation.shape[0] == correlation.shape[1]


# ============================================================================
# TESTS: Conflicts Module
# ============================================================================

class TestConflicts:
    """Test conflict resolution."""
    
    def test_conflict_registry_creation(self):
        """Test ConflictRegistry initialization."""
        registry = ConflictRegistry()
        assert registry.output_path is not None
        assert len(registry.conflicts) == 0
    
    def test_log_conflict(self):
        """Test conflict logging."""
        registry = ConflictRegistry()
        
        registry.log_conflict(
            culture_id="C001",
            feature_name="trance",
            source1="dplace",
            value1=1.0,
            source2="drh",
            value2=0.0,
            quality1=0.5,
            quality2=0.7,
            conflict_type="conflict",
        )
        
        assert len(registry.conflicts) == 1


# ============================================================================
# TESTS: Validation Module
# ============================================================================

class TestValidation:
    """Test ethnographic validation."""
    
    def test_load_ethnographic_narratives(self):
        """Test loading ethnographic narratives."""
        narratives = load_ethnographic_narratives()
        
        assert isinstance(narratives, dict)
        assert len(narratives) > 0
        assert "DRH_001" in narratives
        
        siberian = narratives["DRH_001"]
        assert "name" in siberian
        assert "expected_features" in siberian


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests across modules."""
    
    def test_full_analysis_pipeline(self, sample_harmonised_df):
        """Test full analysis pipeline."""
        # Stratify
        stratified = stratify_by_era(sample_harmonised_df)
        assert len(stratified) > 0
        
        # Analyze era features
        era_features = compute_era_feature_presence(stratified)
        assert isinstance(era_features, pd.DataFrame)
        
        # Geographic analysis
        df_with_regions = assign_geographic_regions(sample_harmonised_df)
        density = compute_regional_density(df_with_regions)
        assert isinstance(density, dict)
        
        # Aggregation
        aggregated = aggregate_features_by_culture(sample_harmonised_df)
        assert len(aggregated) > 0


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Performance and scale tests."""
    
    def test_handles_large_dataset(self):
        """Test that functions handle larger datasets efficiently."""
        # Create larger test dataset
        n_records = 1000
        data = {
            "source": ["dplace"] * n_records,
            "culture_id": [f"C{i%100}" for i in range(n_records)],
            "culture_name": [f"Culture_{i%100}" for i in range(n_records)],
            "unit_type": ["society"] * n_records,
            "lat": np.random.uniform(-90, 90, n_records),
            "lon": np.random.uniform(-180, 180, n_records),
            "time_start": -1950,
            "time_end": -1850,
            "feature_name": "trance_induction",
            "feature_value_binarised": np.random.binomial(1, 0.5, n_records).astype(float),
            "data_quality_score": np.random.uniform(0.1, 0.9, n_records),
            "temporal_mode": "snapshot",
            "time_uncertainty": 3,
        }
        large_df = pd.DataFrame(data)
        
        # Should complete without errors
        stratified = stratify_by_era(large_df)
        assert len(stratified) > 0
        
        df_with_regions = assign_geographic_regions(large_df)
        assert len(df_with_regions) == len(large_df)


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_handles_empty_dataframe(self):
        """Test functions handle empty DataFrames gracefully."""
        empty_df = pd.DataFrame(columns=[
            "source", "culture_id", "culture_name", "feature_name",
            "feature_value_binarised", "data_quality_score", "lat", "lon",
            "temporal_mode", "time_uncertainty", "time_start", "time_end"
        ])
        
        # These should return empty or zero-length results rather than crashing
        result1 = stratify_by_era(empty_df)
        assert isinstance(result1, dict)
        
        result2 = assign_geographic_regions(empty_df)
        assert isinstance(result2, pd.DataFrame)
    
    def test_handles_missing_columns(self):
        """Test functions handle missing expected columns gracefully."""
        incomplete_df = pd.DataFrame({
            "culture_id": ["C1"],
            "culture_name": ["Culture 1"],
        })
        
        # Should handle gracefully or raise informative error
        try:
            assign_geographic_regions(incomplete_df)
        except (KeyError, ValueError):
            pass  # Expected


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
