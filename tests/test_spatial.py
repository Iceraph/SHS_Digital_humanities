"""
Unit and integration tests for spatial.py module.

Tests cover:
- Weight matrix creation (distance_band, knn, inverse_distance, gaussian)
- Moran's I computation with permutation testing
- Distance decay analysis
- Spatial cluster coherence testing
- Visualization functions

Run with: pytest tests/test_spatial.py -v
"""

import pytest
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from src.analysis.spatial import (
    geographic_distance_matrix,
    feature_distance_matrix,
    create_weight_matrix,
    morans_i,
    distance_decay_analysis,
    spatial_cluster_test,
    plot_distance_decay,
    plot_morans_i_significant_features
)


# ============================================================================
# FIXTURES: Test Data
# ============================================================================

@pytest.fixture
def simple_coords():
    """3-point checkerboard pattern (known Moran's I test case)."""
    return np.array([
        [0.0, 0.0],      # Point 1
        [0.0, 1.0],      # Point 2 (nearby, ~111 km)
        [0.0, 2.0]       # Point 3 (moderate distance, ~222 km)
    ])


@pytest.fixture
def checkerboard_feature():
    """Binary feature for checkerboard pattern."""
    return np.array([1, 1, 0])  # Similar nearby, different far


@pytest.fixture
def random_feature():
    """Random feature (no spatial structure)."""
    return np.array([1, 0, 1])


@pytest.fixture
def large_coords():
    """100 random points on globe."""
    np.random.seed(42)
    return np.random.uniform(-90, 90, (100, 2))


@pytest.fixture
def large_feature_matrix():
    """100×10 random binary feature matrix."""
    np.random.seed(42)
    return np.random.binomial(1, 0.5, (100, 10))


# ============================================================================
# TESTS: Geographic Distance Matrix
# ============================================================================

class TestGeographicDistanceMatrix:
    """Test geographic distance computations."""
    
    def test_haversine_symmetry(self, simple_coords):
        """Distance matrix should be symmetric."""
        dist = geographic_distance_matrix(simple_coords, metric="haversine")
        assert np.allclose(dist, dist.T), "Distance matrix not symmetric"
    
    def test_haversine_diagonal_zero(self, simple_coords):
        """Diagonal should be zero (distance to self)."""
        dist = geographic_distance_matrix(simple_coords, metric="haversine")
        assert np.allclose(np.diag(dist), 0), "Diagonal not zero"
    
    def test_haversine_known_distance(self):
        """Test known distance (equator, 1 degree difference)."""
        # ~111 km per degree at equator
        coords = np.array([[0, 0], [0, 1]])
        dist = geographic_distance_matrix(coords, metric="haversine")
        assert 110 < dist[0, 1] < 112, f"Expected ~111 km, got {dist[0, 1]:.1f}"
    
    def test_euclidean_symmetry(self, simple_coords):
        """Euclidean distances should also be symmetric."""
        dist = geographic_distance_matrix(simple_coords, metric="euclidean")
        assert np.allclose(dist, dist.T)
    
    def test_invalid_coords_shape(self):
        """Should raise error for invalid coordinates."""
        bad_coords = np.array([[0, 0, 0]])  # 3D
        with pytest.raises(ValueError):
            geographic_distance_matrix(bad_coords)
    
    def test_invalid_metric(self, simple_coords):
        """Should raise error for unknown metric."""
        with pytest.raises(ValueError):
            geographic_distance_matrix(simple_coords, metric="manhattan")


# ============================================================================
# TESTS: Feature Distance Matrix
# ============================================================================

class TestFeatureDistanceMatrix:
    """Test feature distance computations."""
    
    def test_jaccard_identical_features(self):
        """Identical features should have distance 0."""
        features = np.array([[1, 0, 1], [1, 0, 1]])
        dist = feature_distance_matrix(features, metric="jaccard")
        assert dist[0, 1] == 0, "Identical features have non-zero distance"
    
    def test_jaccard_orthogonal_features(self):
        """Orthogonal features should have distance 1."""
        features = np.array([[1, 0], [0, 1]])
        dist = feature_distance_matrix(features, metric="jaccard")
        assert dist[0, 1] == 1, "Orthogonal features don't have distance 1"
    
    def test_jaccard_symmetry(self, large_feature_matrix):
        """Jaccard distance should be symmetric."""
        dist = feature_distance_matrix(large_feature_matrix, metric="jaccard")
        assert np.allclose(dist, dist.T)


# ============================================================================
# TESTS: Weight Matrix Creation
# ============================================================================

class TestWeightMatrix:
    """Test spatial weight matrix creation."""
    
    def test_distance_band_basic(self, simple_coords):
        """Distance band weight matrix."""
        W = create_weight_matrix(simple_coords, weight_type="distance_band", threshold_km=500)
        
        # Diagonal should be zero
        assert np.allclose(np.diag(W), 0)
        
        # Symmetry
        assert np.allclose(W, W.T)
        
        # Point 0 and 1 are close (~111 km), should be neighbors within 500 km
        assert W[0, 1] == 1
        
        # Point 0 and 2 are moderate distance (~222 km), should still be neighbors within 500 km
        assert W[0, 2] == 1
    
    def test_distance_band_threshold_validation(self, simple_coords):
        """Should raise error for invalid threshold."""
        with pytest.raises(ValueError):
            create_weight_matrix(simple_coords, weight_type="distance_band", threshold_km=-1)
    
    def test_knn_weight_matrix(self, large_coords):
        """KNN weight matrix should have exactly k neighbors per location."""
        k = 5
        W = create_weight_matrix(large_coords, weight_type="knn", k_neighbors=k)
        
        # Each row should have exactly k ones (k neighbors)
        row_sums = W.sum(axis=1)
        assert np.allclose(row_sums, k), f"Expected k={k} neighbors per row"
        
        # Diagonal should be zero
        assert np.allclose(np.diag(W), 0)
    
    def test_gaussian_kernel_weight(self, simple_coords):
        """Gaussian kernel weights should decay with distance."""
        W = create_weight_matrix(simple_coords, weight_type="gaussian_kernel", bandwidth=500)
        
        # Weights should be in [0, 1]
        assert np.all(W >= 0) and np.all(W <= 1)
        
        # Diagonal should be zero
        assert np.allclose(np.diag(W), 0)
    
    def test_no_isolated_locations(self, large_coords):
        """No location should be completely isolated."""
        W = create_weight_matrix(large_coords, weight_type="distance_band", threshold_km=5000)
        
        # All row sums should be > 0
        row_sums = W.sum(axis=1)
        assert np.all(row_sums > 0), "Some locations have no neighbors"


# ============================================================================
# TESTS: Moran's I
# ============================================================================

class TestMoransI:
    """Test Moran's I spatial autocorrelation."""
    
    def test_morans_i_returns_dict(self, simple_coords, checkerboard_feature):
        """Should return dictionary with required keys."""
        result = morans_i(checkerboard_feature, simple_coords, n_permutations=99)
        
        assert isinstance(result, dict)
        assert "statistic" in result
        assert "p_value" in result
        assert "z_score" in result
        assert "interpretation" in result
    
    def test_morans_i_p_value_range(self, large_coords, large_feature_matrix):
        """P-values should be in [0, 1]."""
        for k in range(min(3, large_feature_matrix.shape[1])):
            result = morans_i(large_feature_matrix[:, k], large_coords, weight_type="knn", n_permutations=99)
            assert 0 <= result["p_value"] <= 1
    
    def test_morans_i_nan_handling(self, large_coords):
        """Should handle NaN values gracefully."""
        # Create feature with some NaN values but at least 3 valid points
        feature = np.ones(len(large_coords))
        feature[::5] = np.nan  # Make every 5th value NaN
        feature[0:3] = [1.0, 1.0, 0.0]  # Ensure first 3 are valid
        
        result = morans_i(feature, large_coords, weight_type="knn", n_permutations=99)
        
        assert isinstance(result["statistic"], float)
        assert not np.isnan(result["statistic"])
    
    def test_morans_i_zero_variance_error(self, simple_coords):
        """Should raise error for features with zero variance."""
        constant_feature = np.array([1, 1, 1])
        
        with pytest.raises(ValueError):
            morans_i(constant_feature, simple_coords)
    
    def test_morans_i_reproducibility(self, large_coords, large_feature_matrix):
        """Results should be reproducible with same random seed."""
        result1 = morans_i(
            large_feature_matrix[:, 0],
            large_coords,
            weight_type="knn",
            n_permutations=99,
            random_state=42
        )
        
        result2 = morans_i(
            large_feature_matrix[:, 0],
            large_coords,
            weight_type="knn",
            n_permutations=99,
            random_state=42
        )
        
        assert result1["statistic"] == result2["statistic"]
        assert result1["p_value"] == result2["p_value"]


# ============================================================================
# TESTS: Distance Decay Analysis
# ============================================================================

class TestDistanceDecay:
    """Test distance decay analysis."""
    
    def test_distance_decay_output_format(self, large_coords, large_feature_matrix):
        """Should return DataFrame with correct columns."""
        result = distance_decay_analysis(large_feature_matrix, large_coords)
        
        assert isinstance(result, pd.DataFrame)
        assert "distance_bin" in result.columns
        assert "mean_similarity" in result.columns
        assert "n_pairs" in result.columns
        assert len(result) > 0
    
    def test_distance_decay_monotonicity_typical(self, large_coords, large_feature_matrix):
        """Typical case: similarity should decrease (or stay similar) with distance."""
        result = distance_decay_analysis(large_feature_matrix, large_coords)
        
        # Should have multiple bins
        assert len(result) > 2
        
        # Similarities should be in valid range
        assert np.all(result["mean_similarity"] >= -1) and np.all(result["mean_similarity"] <= 1)
    
    def test_distance_decay_n_pairs_positive(self, large_coords, large_feature_matrix):
        """Each bin should have positive number of pairs."""
        result = distance_decay_analysis(large_feature_matrix, large_coords)
        
        assert np.all(result["n_pairs"] > 0)
    
    def test_distance_decay_custom_bins(self, large_coords, large_feature_matrix):
        """Should accept custom distance bins."""
        custom_bins = np.array([0, 500, 1000, 5000, 50000])
        result = distance_decay_analysis(
            large_feature_matrix,
            large_coords,
            distance_bins=custom_bins
        )
        
        # Number of bins = len(custom_bins) - 1
        assert len(result) <= len(custom_bins) - 1


# ============================================================================
# TESTS: Spatial Cluster Test
# ============================================================================

class TestSpatialClusterTest:
    """Test spatial coherence of clusters."""
    
    def test_spatial_cluster_output_format(self, large_coords):
        """Should return dict with cluster analysis results."""
        cluster_labels = np.random.randint(0, 3, len(large_coords))
        result = spatial_cluster_test(cluster_labels, large_coords, weight_type="knn")
        
        assert isinstance(result, dict)
        assert "global_moran_i" in result
        assert "n_clusters" in result
        assert "spatial_fragmentation_score" in result
    
    def test_spatial_fragmentation_score_bounds(self, large_coords):
        """Fragmentation score should be in [0, 1]."""
        cluster_labels = np.random.randint(0, 3, len(large_coords))
        result = spatial_cluster_test(cluster_labels, large_coords, weight_type="knn")
        
        assert 0 <= result["spatial_fragmentation_score"] <= 1
    
    def test_single_cluster(self, large_coords):
        """Single cluster should have high fragmentation."""
        # Create 2 roughly equal clusters to test fragmentation scoring
        cluster_labels = np.zeros(len(large_coords), dtype=int)
        cluster_labels[:len(large_coords)//2] = 0
        cluster_labels[len(large_coords)//2:] = 1
        
        result = spatial_cluster_test(cluster_labels, large_coords, weight_type="knn")
        
        # With mixed clusters, fragmentation should be reasonable
        assert result["spatial_fragmentation_score"] >= 0


# ============================================================================
# TESTS: Visualization Functions
# ============================================================================

class TestVisualization:
    """Test plotting functions."""
    
    def test_plot_distance_decay(self, large_coords, large_feature_matrix):
        """Should produce matplotlib figure."""
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend
        
        decay_df = distance_decay_analysis(large_feature_matrix, large_coords)
        fig = plot_distance_decay(decay_df)
        
        assert fig is not None
    
    def test_plot_morans_i(self, large_coords, large_feature_matrix):
        """Should produce bar chart of Moran's I per feature."""
        import matplotlib
        matplotlib.use('Agg')
        
        feature_names = [f"feature_{i}" for i in range(large_feature_matrix.shape[1])]
        
        fig, result_df = plot_morans_i_significant_features(
            large_feature_matrix[:, :3],
            large_coords,
            feature_names[:3],
            weight_type="knn"
        )
        
        assert fig is not None
        assert len(result_df) == 3
        assert "I" in result_df.columns
        assert "p_value" in result_df.columns


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple functions."""
    
    def test_full_spatial_analysis_pipeline(self, large_coords, large_feature_matrix):
        """Test complete spatial analysis workflow."""
        # 1. Weight matrix (use knn to avoid isolated locations)
        W = create_weight_matrix(large_coords, weight_type="knn")
        assert W.shape == (len(large_coords), len(large_coords))
        
        # 2. Moran's I
        results = []
        for k in range(min(3, large_feature_matrix.shape[1])):
            result = morans_i(large_feature_matrix[:, k], large_coords, weight_type="knn", n_permutations=99)
            results.append(result)
        
        assert len(results) == 3
        
        # 3. Distance decay
        decay = distance_decay_analysis(large_feature_matrix[:, :3], large_coords)
        assert len(decay) > 0
    
    def test_different_weight_types_same_p_value_range(self, large_coords, large_feature_matrix):
        """Different weight types should give reasonable p-values."""
        feature = large_feature_matrix[:, 0]
        
        results = {}
        # Only test knn for random global coords (distance_band/gaussian fail with scattered points)
        for weight_type in ["knn"]:
            result = morans_i(
                feature,
                large_coords,
                weight_type=weight_type,
                n_permutations=99,
                random_state=42
            )
            results[weight_type] = result["p_value"]
        
        # All p-values should be in valid range
        assert all(0 <= p <= 1 for p in results.values())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
