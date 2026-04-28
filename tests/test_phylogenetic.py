"""
Unit and integration tests for phylogenetic.py module.

Tests cover:
- Galton's correction: filtering to one per language family
- Phylogenetic signal tests: Pagel's lambda, Blomberg's K
- Mantel and partial Mantel tests
- Composite phylogenetic signal analysis

Run with: pytest tests/test_phylogenetic.py -v
"""

import pytest
import numpy as np
import pandas as pd
from src.analysis.phylogenetic import (
    filter_one_per_language_family,
    compute_phylogenetic_summary,
    create_robustness_dataset_pair,
    pagels_lambda,
    blombergs_k,
    mantel_test,
    partial_mantel_test,
    compute_all_phylogenetic_signals
)


# ============================================================================
# FIXTURES: Test Data
# ============================================================================

@pytest.fixture
def sample_dataframe():
    """Sample DataFrame with cultures and language families."""
    return pd.DataFrame({
        "culture_id": [f"C{i:03d}" for i in range(20)],
        "culture_name": [f"Culture_{i}" for i in range(20)],
        "language_family": ["LF_A"] * 5 + ["LF_B"] * 5 + ["LF_C"] * 5 + ["LF_D"] * 5,
        "lat": np.random.uniform(-90, 90, 20),
        "lon": np.random.uniform(-180, 180, 20),
        "feature_1": np.random.binomial(1, 0.5, 20)
    })


@pytest.fixture
def sample_distance_matrix():
    """5×5 sample phylogenetic distance matrix."""
    D = np.array([
        [0.0, 0.5, 1.0, 2.0, 3.0],
        [0.5, 0.0, 0.8, 2.1, 2.9],
        [1.0, 0.8, 0.0, 1.5, 3.1],
        [2.0, 2.1, 1.5, 0.0, 1.2],
        [3.0, 2.9, 3.1, 1.2, 0.0]
    ])
    return D


@pytest.fixture
def sample_feature_vector():
    """Sample feature vector (5 values)."""
    return np.array([1.0, 1.0, 0.0, 0.0, 0.0])


@pytest.fixture
def large_feature_matrix():
    """10×5 feature matrix for composite analysis."""
    np.random.seed(42)
    return np.random.binomial(1, 0.5, (10, 5))


@pytest.fixture
def large_distance_matrix():
    """10×10 phylogenetic distance matrix."""
    np.random.seed(42)
    D = np.random.uniform(0, 5, (10, 10))
    return (D + D.T) / 2  # Make symmetric


# ============================================================================
# TESTS: Galton's Correction
# ============================================================================

class TestGaltonsCorrection:
    """Test phylogenetic independence filtering."""
    
    def test_filter_one_per_language_family(self, sample_dataframe):
        """Should filter to one culture per language family."""
        filtered = filter_one_per_language_family(sample_dataframe)
        
        # Should have 4 language families
        assert len(filtered) == 4
        
        # Each language family should have exactly 1 culture
        for lf in sample_dataframe["language_family"].unique():
            count = (filtered["language_family"] == lf).sum()
            assert count == 1, f"Language family {lf} has {count} cultures"
    
    def test_filter_preserves_columns(self, sample_dataframe):
        """Filtered DataFrame should have same columns."""
        filtered = filter_one_per_language_family(sample_dataframe)
        
        assert set(filtered.columns) == set(sample_dataframe.columns)
    
    def test_filter_reproducibility(self, sample_dataframe):
        """Same random seed should give same results."""
        filtered1 = filter_one_per_language_family(sample_dataframe, random_state=42)
        filtered2 = filter_one_per_language_family(sample_dataframe, random_state=42)
        
        assert filtered1.equals(filtered2)
    
    def test_filter_missing_column(self, sample_dataframe):
        """Should raise error if language_family column missing."""
        bad_df = sample_dataframe.drop("language_family", axis=1)
        
        with pytest.raises(ValueError):
            filter_one_per_language_family(bad_df, language_family_col="language_family")
    
    def test_filter_custom_column_name(self, sample_dataframe):
        """Should accept custom language family column name."""
        sample_dataframe["language_group"] = sample_dataframe["language_family"]
        
        filtered = filter_one_per_language_family(
            sample_dataframe,
            language_family_col="language_group"
        )
        
        assert len(filtered) == 4


# ============================================================================
# TESTS: Phylogenetic Summary
# ============================================================================

class TestPhylogeneticSummary:
    """Test phylogenetic comparison metrics."""
    
    def test_summary_output_format(self, sample_dataframe):
        """Should return dict with comparison metrics."""
        filtered = filter_one_per_language_family(sample_dataframe)
        summary = compute_phylogenetic_summary(sample_dataframe, filtered)
        
        assert isinstance(summary, dict)
        assert "full_dataset" in summary
        assert "filtered_dataset" in summary
        assert "reduction_ratio" in summary
    
    def test_summary_reduction_ratio(self, sample_dataframe):
        """Reduction ratio should be < 1."""
        filtered = filter_one_per_language_family(sample_dataframe)
        summary = compute_phylogenetic_summary(sample_dataframe, filtered)
        
        assert 0 < summary["reduction_ratio"] <= 1
        assert summary["reduction_ratio"] == len(filtered) / len(sample_dataframe)


# ============================================================================
# TESTS: Robustness Dataset Pair
# ============================================================================

class TestRobustnessDatasetPair:
    """Test paired dataset generation."""
    
    def test_create_robustness_pair(self, sample_dataframe):
        """Should return tuple of (filtered, full)."""
        filtered, full = create_robustness_dataset_pair(sample_dataframe)
        
        assert isinstance(filtered, pd.DataFrame)
        assert isinstance(full, pd.DataFrame)
        assert len(filtered) <= len(full)
    
    def test_dataset_type_marking(self, sample_dataframe):
        """Both datasets should have dataset_type column."""
        filtered, full = create_robustness_dataset_pair(sample_dataframe)
        
        assert "dataset_type" in filtered.columns
        assert "dataset_type" in full.columns
        assert (filtered["dataset_type"] == "phylo_filtered").all()
        assert (full["dataset_type"] == "full_dataset").all()


# ============================================================================
# TESTS: Pagel's Lambda
# ============================================================================

class TestPagelsLambda:
    """Test Pagel's lambda phylogenetic signal."""
    
    def test_pagels_lambda_output(self, sample_feature_vector, sample_distance_matrix):
        """Should return dict with required keys."""
        result = pagels_lambda(sample_feature_vector, sample_distance_matrix)
        
        assert isinstance(result, dict)
        assert "lambda" in result
        assert "ci_lower" in result
        assert "ci_upper" in result
        assert "p_value" in result
        assert "interpretation" in result
    
    def test_pagels_lambda_bounds(self, sample_feature_vector, sample_distance_matrix):
        """Lambda should be in [0, 1]."""
        result = pagels_lambda(sample_feature_vector, sample_distance_matrix)
        
        assert 0 <= result["lambda"] <= 1
        assert 0 <= result["ci_lower"] <= 1
        assert 0 <= result["ci_upper"] <= 1
    
    def test_pagels_lambda_ci_ordering(self, sample_feature_vector, sample_distance_matrix):
        """Confidence interval should have ci_lower < lambda < ci_upper."""
        result = pagels_lambda(sample_feature_vector, sample_distance_matrix)
        
        assert result["ci_lower"] <= result["lambda"] <= result["ci_upper"]
    
    def test_pagels_lambda_p_value_range(self, sample_feature_vector, sample_distance_matrix):
        """P-value should be in [0, 1]."""
        result = pagels_lambda(sample_feature_vector, sample_distance_matrix)
        
        assert 0 <= result["p_value"] <= 1
    
    def test_pagels_lambda_nan_handling(self, sample_distance_matrix):
        """Should handle NaN values."""
        feature = np.array([1.0, np.nan, 0.0, 0.0, 0.0])
        result = pagels_lambda(feature, sample_distance_matrix)
        
        assert not np.isnan(result["lambda"])
    
    def test_pagels_lambda_insufficient_data(self):
        """Should raise error for too few observations."""
        feature = np.array([1.0, 0.0])
        distance = np.array([[0, 1], [1, 0]])
        
        with pytest.raises(ValueError):
            pagels_lambda(feature, distance)


# ============================================================================
# TESTS: Blomberg's K
# ============================================================================

class TestBlombergsK:
    """Test Blomberg's K phylogenetic signal."""
    
    def test_blombergs_k_output(self, sample_feature_vector, sample_distance_matrix):
        """Should return dict with required keys."""
        result = blombergs_k(sample_feature_vector, sample_distance_matrix)
        
        assert isinstance(result, dict)
        assert "k" in result
        assert "p_value" in result
        assert "interpretation" in result
    
    def test_blombergs_k_positive(self, sample_feature_vector, sample_distance_matrix):
        """K should be positive."""
        result = blombergs_k(sample_feature_vector, sample_distance_matrix)
        
        assert result["k"] > 0
    
    def test_blombergs_k_p_value(self, sample_feature_vector, sample_distance_matrix):
        """P-value should be in [0, 1]."""
        result = blombergs_k(sample_feature_vector, sample_distance_matrix)
        
        assert 0 <= result["p_value"] <= 1
    
    def test_blombergs_k_insufficient_data(self):
        """Should raise error for too few observations."""
        feature = np.array([1.0, 0.0])
        distance = np.array([[0, 1], [1, 0]])
        
        with pytest.raises(ValueError):
            blombergs_k(feature, distance)


# ============================================================================
# TESTS: Mantel Test
# ============================================================================

class TestMantelTest:
    """Test Mantel correlation test."""
    
    def test_mantel_output(self):
        """Should return dict with correlation and p-value."""
        # Create two distance matrices
        D1 = np.array([[0, 1, 2], [1, 0, 1], [2, 1, 0]])
        D2 = np.array([[0, 1, 2], [1, 0, 1], [2, 1, 0]])
        
        result = mantel_test(D1, D2, n_permutations=99)
        
        assert isinstance(result, dict)
        assert "correlation" in result
        assert "p_value" in result
        assert "z_score" in result
    
    def test_mantel_identical_matrices(self):
        """Identical matrices should have r ≈ 1."""
        rng = np.random.default_rng(42)
        D = rng.uniform(0, 1, (8, 8))
        D = (D + D.T) / 2
        np.fill_diagonal(D, 0)

        result = mantel_test(D, D, n_permutations=999)

        assert result["correlation"] > 0.99
        assert result["p_value"] < 0.05  # Significant
    
    def test_mantel_p_value_range(self):
        """P-value should be in [0, 1]."""
        D1 = np.random.uniform(0, 1, (5, 5))
        D1 = (D1 + D1.T) / 2
        np.fill_diagonal(D1, 0)
        
        D2 = np.random.uniform(0, 1, (5, 5))
        D2 = (D2 + D2.T) / 2
        np.fill_diagonal(D2, 0)
        
        result = mantel_test(D1, D2, n_permutations=99)
        
        assert 0 <= result["p_value"] <= 1
    
    def test_mantel_correlation_bounds(self):
        """Correlation should be in [-1, 1]."""
        D1 = np.random.uniform(0, 1, (5, 5))
        D1 = (D1 + D1.T) / 2
        np.fill_diagonal(D1, 0)
        
        D2 = np.random.uniform(0, 1, (5, 5))
        D2 = (D2 + D2.T) / 2
        np.fill_diagonal(D2, 0)
        
        result = mantel_test(D1, D2, n_permutations=99)
        
        assert -1 <= result["correlation"] <= 1
    
    def test_mantel_dimension_mismatch(self):
        """Should raise error for mismatched matrix sizes."""
        D1 = np.array([[0, 1], [1, 0]])
        D2 = np.array([[0, 1, 2], [1, 0, 1], [2, 1, 0]])
        
        with pytest.raises(ValueError):
            mantel_test(D1, D2)
    
    def test_mantel_reproducibility(self):
        """Same random seed should give same results."""
        D1 = np.random.RandomState(42).uniform(0, 1, (5, 5))
        D1 = (D1 + D1.T) / 2
        np.fill_diagonal(D1, 0)
        
        D2 = np.random.RandomState(42).uniform(0, 1, (5, 5))
        D2 = (D2 + D2.T) / 2
        np.fill_diagonal(D2, 0)
        
        result1 = mantel_test(D1, D2, n_permutations=99, random_state=42)
        result2 = mantel_test(D1, D2, n_permutations=99, random_state=42)
        
        assert result1["correlation"] == result2["correlation"]
        assert result1["p_value"] == result2["p_value"]


# ============================================================================
# TESTS: Partial Mantel Test
# ============================================================================

class TestPartialMantelTest:
    """Test partial Mantel test (controlling for third matrix)."""
    
    def test_partial_mantel_output(self):
        """Should return dict with partial correlation and p-value."""
        D1 = np.random.uniform(0, 1, (5, 5))
        D1 = (D1 + D1.T) / 2
        np.fill_diagonal(D1, 0)
        
        D2 = np.random.uniform(0, 1, (5, 5))
        D2 = (D2 + D2.T) / 2
        np.fill_diagonal(D2, 0)
        
        D3 = np.random.uniform(0, 1, (5, 5))
        D3 = (D3 + D3.T) / 2
        np.fill_diagonal(D3, 0)
        
        result = partial_mantel_test(D1, D2, D3, n_permutations=99)
        
        assert isinstance(result, dict)
        assert "partial_correlation" in result
        assert "p_value" in result
    
    def test_partial_mantel_correlation_bounds(self):
        """Partial correlation should be in [-1, 1]."""
        D1 = np.random.RandomState(42).uniform(0, 1, (5, 5))
        D1 = (D1 + D1.T) / 2
        np.fill_diagonal(D1, 0)
        
        D2 = np.random.RandomState(43).uniform(0, 1, (5, 5))
        D2 = (D2 + D2.T) / 2
        np.fill_diagonal(D2, 0)
        
        D3 = np.random.RandomState(44).uniform(0, 1, (5, 5))
        D3 = (D3 + D3.T) / 2
        np.fill_diagonal(D3, 0)
        
        result = partial_mantel_test(D1, D2, D3, n_permutations=99)
        
        assert -1 <= result["partial_correlation"] <= 1


# ============================================================================
# TESTS: Composite Phylogenetic Signals
# ============================================================================

class TestComputeAllPhylogeneticSignals:
    """Test composite phylogenetic signal analysis."""
    
    def test_composite_output_format(self, large_feature_matrix, large_distance_matrix):
        """Should return DataFrame with all signal measures."""
        feature_names = [f"feature_{i}" for i in range(large_feature_matrix.shape[1])]
        
        result = compute_all_phylogenetic_signals(
            large_feature_matrix,
            large_distance_matrix,
            feature_names
        )
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(feature_names)
        assert "pagels_lambda" in result.columns
        assert "blombergs_k" in result.columns
        assert "signal_strength" in result.columns
    
    def test_composite_signal_categories(self, large_feature_matrix, large_distance_matrix):
        """Signal strength should be categorical."""
        feature_names = [f"feature_{i}" for i in range(large_feature_matrix.shape[1])]
        
        result = compute_all_phylogenetic_signals(
            large_feature_matrix,
            large_distance_matrix,
            feature_names
        )
        
        valid_categories = {"Strong", "Moderate", "Weak", "Inconclusive"}
        assert all(s in valid_categories for s in result["signal_strength"])


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple functions."""
    
    def test_galtons_to_phylogenetic_signals(self, sample_dataframe):
        """Test workflow: filter → prepare → compute signals."""
        # 1. Filter to one per language family
        filtered = filter_one_per_language_family(sample_dataframe)
        assert len(filtered) == 4
        
        # 2. Create robustness pair
        filt, full = create_robustness_dataset_pair(sample_dataframe)
        assert len(filt) <= len(full)
    
    def test_mantel_and_partial_mantel(self):
        """Test both Mantel tests together."""
        # Create three distance matrices
        D_geo = np.random.RandomState(42).uniform(0, 1, (8, 8))
        D_geo = (D_geo + D_geo.T) / 2
        np.fill_diagonal(D_geo, 0)
        
        D_feat = np.random.RandomState(43).uniform(0, 1, (8, 8))
        D_feat = (D_feat + D_feat.T) / 2
        np.fill_diagonal(D_feat, 0)
        
        D_phylo = np.random.RandomState(44).uniform(0, 1, (8, 8))
        D_phylo = (D_phylo + D_phylo.T) / 2
        np.fill_diagonal(D_phylo, 0)
        
        # Standard Mantel
        result_mantel = mantel_test(D_geo, D_feat, n_permutations=99)
        assert 0 <= result_mantel["p_value"] <= 1
        
        # Partial Mantel
        result_partial = partial_mantel_test(D_geo, D_feat, D_phylo, n_permutations=99)
        assert -1 <= result_partial["partial_correlation"] <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
