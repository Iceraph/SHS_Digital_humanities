"""
Spatial statistical analysis for shamanic features and clusters.

This module implements spatial autocorrelation tests (Moran's I), distance decay analysis,
and spatial coherence testing to assess whether shamanic features cluster geographically
(supporting diffusion hypothesis) or are globally distributed (supporting universalism).

Author: Phase 6 Implementation
Date: April 2026
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict, Optional, Union, List
from scipy.spatial.distance import cdist, squareform, pdist
from scipy.stats import pearsonr, spearmanr
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics.pairwise import pairwise_distances


# ============================================================================
# HELPER FUNCTIONS: Distance Matrices
# ============================================================================

def geographic_distance_matrix(
    coords: np.ndarray,
    metric: str = "haversine"
) -> np.ndarray:
    """
    Compute pairwise geographic distances between cultures.
    
    Parameters
    ----------
    coords : np.ndarray
        Array of shape (N, 2) with columns [latitude, longitude] in decimal degrees.
    metric : str, default "haversine"
        Distance metric. Options:
        - "haversine": Great-circle distance (for long distances)
        - "euclidean": Planar distance (for small distances or when lat/lon are projected)
    
    Returns
    -------
    np.ndarray
        Symmetric N×N distance matrix where entry [i,j] is the distance in km.
    
    Raises
    ------
    ValueError
        If coords shape is invalid or metric is not recognized.
    
    Examples
    --------
    >>> coords = np.array([[0, 0], [0, 1], [1, 0]])
    >>> dist_matrix = geographic_distance_matrix(coords)
    >>> assert dist_matrix.shape == (3, 3)
    >>> assert np.allclose(dist_matrix, dist_matrix.T)  # Symmetric
    >>> assert np.allclose(np.diag(dist_matrix), 0)  # Diagonal is zero
    """
    if coords.ndim != 2 or coords.shape[1] != 2:
        raise ValueError(f"coords must have shape (N, 2), got {coords.shape}")
    
    if metric == "haversine":
        # Haversine formula: great-circle distance
        # Convert to radians
        coords_rad = np.radians(coords)
        lat1, lon1 = coords_rad[:, 0:1], coords_rad[:, 1:2]
        lat2, lon2 = coords_rad[:, 0:1].T, coords_rad[:, 1:2].T
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        c = 2 * np.arcsin(np.sqrt(a))
        
        # Earth radius in km
        R = 6371.0
        distances = R * c
    elif metric == "euclidean":
        distances = cdist(coords, coords, metric="euclidean")
    else:
        raise ValueError(f"metric must be 'haversine' or 'euclidean', got {metric}")
    
    return distances


def feature_distance_matrix(
    feature_matrix: np.ndarray,
    metric: str = "jaccard"
) -> np.ndarray:
    """
    Compute pairwise feature distances between cultures.
    
    Parameters
    ----------
    feature_matrix : np.ndarray
        Array of shape (N, K) where N is number of cultures, K is number of features.
        Values should be 0, 1 (binary) or ordinal (0-max_value).
    metric : str, default "jaccard"
        Distance metric. Options:
        - "jaccard": Jaccard distance for binary features (1 - intersection/union)
        - "euclidean": Euclidean distance
        - "manhattan": Manhattan (L1) distance
    
    Returns
    -------
    np.ndarray
        Symmetric N×N distance matrix.
    
    Examples
    --------
    >>> feature_matrix = np.array([[0, 1], [1, 1], [0, 0]])
    >>> dist_matrix = feature_distance_matrix(feature_matrix)
    >>> assert dist_matrix.shape == (3, 3)
    >>> assert np.allclose(dist_matrix, dist_matrix.T)
    """
    distances = cdist(feature_matrix, feature_matrix, metric=metric)
    return distances


def phylogenetic_distance_matrix(
    tree,
    culture_ids: List[str]
) -> np.ndarray:
    """
    Compute pairwise phylogenetic distances from a language tree.
    
    Parameters
    ----------
    tree : dendropy.Tree
        Phylogenetic tree object (Dendropy format).
    culture_ids : List[str]
        Culture IDs corresponding to leaves of the tree (must be in order).
    
    Returns
    -------
    np.ndarray
        Symmetric N×N distance matrix where N = len(culture_ids).
    
    Notes
    -----
    This is a placeholder for full implementation in phylogenetic.py.
    Distance is measured as the branch-length distance between leaf nodes.
    """
    n = len(culture_ids)
    distances = np.zeros((n, n))
    # Implementation to be completed with dendropy tree traversal
    return distances


# ============================================================================
# CORE SPATIAL ANALYSIS FUNCTIONS
# ============================================================================

def create_weight_matrix(
    coords: np.ndarray,
    weight_type: str = "distance_band",
    threshold_km: float = 500,
    k_neighbors: int = 5,
    bandwidth: float = 1000
) -> np.ndarray:
    """
    Create a spatial weight matrix for Moran's I and related tests.
    
    Parameters
    ----------
    coords : np.ndarray
        Array of shape (N, 2) with [latitude, longitude] in decimal degrees.
    weight_type : str, default "distance_band"
        Type of weight matrix:
        - "distance_band": W[i,j] = 1 if distance < threshold, else 0
        - "knn": W[i,j] = 1 if j in k nearest neighbors of i
        - "inverse_distance": W[i,j] = 1 / distance[i,j] (with self-weights = 0)
        - "gaussian_kernel": W[i,j] = exp(-distance[i,j]² / bandwidth²)
    threshold_km : float, default 500
        Distance threshold in km (used for "distance_band").
    k_neighbors : int, default 5
        Number of nearest neighbors (used for "knn").
    bandwidth : float, default 1000
        Bandwidth parameter for Gaussian kernel (used for "gaussian_kernel").
    
    Returns
    -------
    np.ndarray
        Spatial weight matrix W of shape (N, N). Diagonal is 0 (no self-weights).
        Typically row-standardized but returned as-is unless specified.
    
    Raises
    ------
    ValueError
        If weight_type not recognized or threshold_km <= 0.
    
    Notes
    -----
    - Weight matrices should have row sums > 0 (every location has ≥1 neighbor).
    - For small datasets, "knn" is recommended. For large datasets, "distance_band" is faster.
    
    Examples
    --------
    >>> coords = np.array([[0, 0], [0, 0.1], [0.1, 0]])
    >>> W = create_weight_matrix(coords, weight_type="distance_band", threshold_km=50)
    >>> assert W.shape == (3, 3)
    >>> assert np.allclose(np.diag(W), 0)  # Diagonal is zero
    """
    if weight_type not in ["distance_band", "knn", "inverse_distance", "gaussian_kernel"]:
        raise ValueError(f"weight_type must be one of distance_band, knn, inverse_distance, gaussian_kernel")
    
    # Compute distance matrix
    distances = geographic_distance_matrix(coords, metric="haversine")
    n = distances.shape[0]
    W = np.zeros((n, n))
    
    if weight_type == "distance_band":
        if threshold_km <= 0:
            raise ValueError(f"threshold_km must be > 0, got {threshold_km}")
        W = (distances < threshold_km).astype(float)
        np.fill_diagonal(W, 0)  # No self-weights
    
    elif weight_type == "knn":
        for i in range(n):
            # Get k nearest neighbors (excluding self)
            neighbors_idx = np.argsort(distances[i])[1:k_neighbors + 1]
            W[i, neighbors_idx] = 1.0
    
    elif weight_type == "inverse_distance":
        with np.errstate(divide="ignore", invalid="ignore"):
            W = 1.0 / distances
        W[np.isinf(W) | np.isnan(W)] = 0.0
        np.fill_diagonal(W, 0)  # No self-weights
    
    elif weight_type == "gaussian_kernel":
        W = np.exp(-distances ** 2 / bandwidth ** 2)
        np.fill_diagonal(W, 0)  # No self-weights
    
    # Validate that all locations have at least one neighbor
    row_sums = W.sum(axis=1)
    if (row_sums == 0).any():
        zero_indices = np.where(row_sums == 0)[0]
        raise ValueError(
            f"Weight matrix has isolated locations (indices {zero_indices}). "
            f"Increase threshold_km or use knn weighting."
        )
    
    return W


def morans_i(
    feature_vector: np.ndarray,
    coords: np.ndarray,
    weight_type: str = "distance_band",
    threshold_km: float = 500,
    n_permutations: int = 999,
    random_state: Optional[int] = None
) -> Dict[str, Union[float, str]]:
    """
    Compute Moran's I spatial autocorrelation statistic and permutation p-value.
    
    Parameters
    ----------
    feature_vector : np.ndarray
        Array of shape (N,) with feature values (binary 0/1, or continuous).
    coords : np.ndarray
        Array of shape (N, 2) with [latitude, longitude].
    weight_type : str, default "distance_band"
        Type of spatial weight matrix (see create_weight_matrix).
    threshold_km : float, default 500
        Distance threshold for weight matrix.
    n_permutations : int, default 999
        Number of permutations for significance testing.
    random_state : int, optional
        Random seed for reproducibility.
    
    Returns
    -------
    Dict[str, Union[float, str]]
        Dictionary with keys:
        - "statistic": Moran's I value (typically -1 to 1, unbounded)
        - "p_value": Two-tailed permutation p-value
        - "z_score": Standardized I (z = (I - E[I]) / sd[I])
        - "interpretation": Text interpretation of result
    
    Notes
    -----
    Moran's I formula:
        I = (n / S₀) * Σᵢ Σⱼ wᵢⱼ(xᵢ - x̄)(xⱼ - x̄) / Σᵢ(xᵢ - x̄)²
    
    where S₀ = Σᵢ Σⱼ wᵢⱼ
    
    Interpretation:
    - I > 0, p < 0.05: Positive spatial autocorrelation (features cluster geographically)
    - I < 0, p < 0.05: Negative spatial autocorrelation (features repel each other)
    - I ≈ 0, p > 0.05: Random spatial distribution
    
    References
    ----------
    Moran, P. A. P. (1950). "Notes on continuous stochastic phenomena."
    Biometrika, 37(1-2), 17-23.
    
    Examples
    --------
    >>> coords = np.random.uniform(-90, 90, (100, 2))
    >>> feature = np.random.binomial(1, 0.5, 100)
    >>> result = morans_i(feature, coords)
    >>> assert "statistic" in result
    >>> assert 0 <= result["p_value"] <= 1
    """
    if random_state is not None:
        np.random.seed(random_state)
    
    # Remove NaN values
    mask = ~np.isnan(feature_vector)
    feature_clean = feature_vector[mask]
    coords_clean = coords[mask]
    
    if len(feature_clean) < 3:
        raise ValueError(f"Insufficient non-NaN values: {len(feature_clean)} < 3")
    
    # Create weight matrix
    W = create_weight_matrix(coords_clean, weight_type=weight_type, threshold_km=threshold_km)
    
    # Standardize feature
    x = feature_clean - feature_clean.mean()
    
    # Compute Moran's I
    n = len(x)
    S0 = W.sum()
    
    # Numerator: Σᵢ Σⱼ wᵢⱼ(xᵢ - x̄)(xⱼ - x̄)
    numerator = np.sum(W * np.outer(x, x))
    
    # Denominator: Σᵢ(xᵢ - x̄)²
    denominator = np.sum(x ** 2)
    
    if denominator == 0:
        raise ValueError("Feature vector has zero variance")
    
    I_observed = (n / S0) * (numerator / denominator)
    
    # Permutation test
    perm_values = np.zeros(n_permutations)
    for perm in range(n_permutations):
        x_perm = np.random.permutation(x)
        numerator_perm = np.sum(W * np.outer(x_perm, x_perm))
        I_perm = (n / S0) * (numerator_perm / denominator)
        perm_values[perm] = I_perm
    
    # Calculate p-value (two-tailed)
    p_value = np.mean(np.abs(perm_values) >= np.abs(I_observed))
    
    # Expected value under null hypothesis (random distribution)
    E_I = -1.0 / (n - 1)
    
    # Standard deviation (variance under null)
    b2 = np.sum(x ** 4) / (n * (np.sum(x ** 2) ** 2 / n))
    W2 = np.sum(W ** 2)
    S1 = 0.5 * np.sum((W + W.T) ** 2)
    
    var_I = ((n * S1 - b2 * S0 ** 2) / ((n - 1) * (S0 ** 2))) - E_I ** 2
    sd_I = np.sqrt(max(0, var_I))  # Avoid negative variance from rounding
    
    if sd_I > 0:
        z_score = (I_observed - E_I) / sd_I
    else:
        z_score = 0.0
    
    # Interpretation
    if p_value < 0.05:
        if I_observed > 0:
            interpretation = "Significant positive spatial autocorrelation (clustering)"
        else:
            interpretation = "Significant negative spatial autocorrelation (dispersal)"
    else:
        interpretation = "Random spatial distribution (no significant autocorrelation)"
    
    return {
        "statistic": float(I_observed),
        "p_value": float(p_value),
        "z_score": float(z_score),
        "expected_value": float(E_I),
        "std_deviation": float(sd_I),
        "interpretation": interpretation
    }


def distance_decay_analysis(
    feature_matrix: np.ndarray,
    coords: np.ndarray,
    distance_bins: Optional[np.ndarray] = None,
    method: str = "pearson"
) -> pd.DataFrame:
    """
    Analyze how feature similarity decays with geographic distance.
    
    Parameters
    ----------
    feature_matrix : np.ndarray
        Array of shape (N, K) with binary/ordinal features for N cultures, K features.
    coords : np.ndarray
        Array of shape (N, 2) with [latitude, longitude].
    distance_bins : np.ndarray, optional
        Bin edges in km. Default: [0, 100, 500, 1000, 2000, 5000, 25000].
    method : str, default "pearson"
        Correlation method: "pearson" or "spearman".
    
    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        - "distance_bin": Bin label (e.g., "0-100 km")
        - "distance_min": Minimum distance in bin (km)
        - "distance_max": Maximum distance in bin (km)
        - "mean_similarity": Mean pairwise feature correlation in bin
        - "std_similarity": Standard deviation
        - "n_pairs": Number of culture pairs in bin
        - "se_similarity": Standard error of mean
    
    Notes
    -----
    Method:
    1. Compute geographic distance between all culture pairs
    2. Compute feature similarity (correlation) for all pairs
    3. Bin pairs by distance
    4. Calculate mean similarity per bin
    
    Interpretation:
    - Steep decay (rapid drop in similarity with distance) → diffusion signal
    - Flat curve (no change in similarity with distance) → universalism signal
    
    Examples
    --------
    >>> feature_matrix = np.random.binomial(1, 0.5, (50, 10))
    >>> coords = np.random.uniform(-90, 90, (50, 2))
    >>> decay = distance_decay_analysis(feature_matrix, coords)
    >>> assert "mean_similarity" in decay.columns
    >>> assert decay["n_pairs"].sum() > 0
    """
    if distance_bins is None:
        distance_bins = np.array([0, 100, 500, 1000, 2000, 5000, 25000])
    
    # Compute distance matrix
    distances = geographic_distance_matrix(coords, metric="haversine")
    
    # Compute feature similarity (correlation) for all pairs
    n = feature_matrix.shape[0]
    similarities = np.zeros((n, n))
    
    for i in range(n):
        for j in range(i + 1, n):
            if method == "pearson":
                corr, _ = pearsonr(feature_matrix[i], feature_matrix[j])
            elif method == "spearman":
                corr, _ = spearmanr(feature_matrix[i], feature_matrix[j])
            else:
                raise ValueError(f"method must be 'pearson' or 'spearman', got {method}")
            
            similarities[i, j] = corr
            similarities[j, i] = corr
    
    # Bin pairs by distance
    results = []
    for k in range(len(distance_bins) - 1):
        bin_min = distance_bins[k]
        bin_max = distance_bins[k + 1]
        
        # Find pairs in this bin
        mask = (distances >= bin_min) & (distances < bin_max)
        
        if mask.sum() > 0:
            bin_similarities = similarities[mask]
            
            results.append({
                "distance_bin": f"{int(bin_min)}-{int(bin_max)} km",
                "distance_min": bin_min,
                "distance_max": bin_max,
                "mean_similarity": np.nanmean(bin_similarities),
                "std_similarity": np.nanstd(bin_similarities),
                "n_pairs": mask.sum(),
                "se_similarity": np.nanstd(bin_similarities) / np.sqrt(np.sum(~np.isnan(bin_similarities)))
            })
    
    return pd.DataFrame(results)


def spatial_cluster_test(
    cluster_labels: np.ndarray,
    coords: np.ndarray,
    weight_type: str = "distance_band",
    threshold_km: float = 500
) -> Dict[str, Union[float, str]]:
    """
    Test whether clusters are spatially coherent (geographically concentrated).
    
    Parameters
    ----------
    cluster_labels : np.ndarray
        Array of shape (N,) with cluster assignment per culture (0, 1, ..., K-1).
    coords : np.ndarray
        Array of shape (N, 2) with [latitude, longitude].
    weight_type : str, default "distance_band"
        Type of spatial weight matrix.
    threshold_km : float, default 500
        Distance threshold for weight matrix.
    
    Returns
    -------
    Dict[str, Union[float, str]]
        Dictionary with keys:
        - "global_moran_i": Moran's I for cluster labels (continuous encoding)
        - "p_value": Significance of global I
        - "n_clusters": Number of clusters
        - "local_morans_i": Array of per-location contributions to global I
        - "spatial_fragmentation_score": 0-1 score (0=scattered, 1=concentrated)
        - "interpretation": Text interpretation
    
    Notes
    -----
    Spatial fragmentation score is computed as the proportion of same-cluster
    neighbors for each location. High score indicates geographically coherent clusters.
    
    Examples
    --------
    >>> cluster_labels = np.array([0, 0, 1, 1, 2, 2])
    >>> coords = np.random.uniform(-90, 90, (6, 2))
    >>> result = spatial_cluster_test(cluster_labels, coords)
    >>> assert "global_moran_i" in result
    """
    # Encode cluster labels as continuous values for Moran's I
    result = morans_i(cluster_labels.astype(float), coords, weight_type=weight_type, threshold_km=threshold_km)
    
    # Compute spatial fragmentation score
    W = create_weight_matrix(coords, weight_type=weight_type, threshold_km=threshold_km)
    W_normalized = W / (W.sum(axis=1, keepdims=True) + 1e-10)
    
    fragmentation_scores = []
    for i, label in enumerate(cluster_labels):
        same_cluster_neighbors = (cluster_labels == label).astype(float)
        same_cluster_prop = np.sum(W_normalized[i] * same_cluster_neighbors)
        fragmentation_scores.append(same_cluster_prop)
    
    fragmentation_score = np.mean(fragmentation_scores)
    
    # Interpretation
    if result["p_value"] < 0.05 and result["statistic"] > 0:
        spatial_type = "Clusters are spatially coherent (geographically concentrated)"
    elif result["p_value"] < 0.05 and result["statistic"] < 0:
        spatial_type = "Clusters are spatially dispersed (geographically scattered)"
    else:
        spatial_type = "Clusters show no significant spatial pattern"
    
    return {
        "global_moran_i": result["statistic"],
        "p_value": result["p_value"],
        "z_score": result["z_score"],
        "n_clusters": len(np.unique(cluster_labels)),
        "spatial_fragmentation_score": float(fragmentation_score),
        "interpretation": spatial_type
    }


# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def plot_distance_decay(
    decay_df: pd.DataFrame,
    ax: Optional[plt.Axes] = None,
    figsize: Tuple[int, int] = (10, 6),
    title: str = "Feature Similarity Decay with Geographic Distance"
) -> plt.Figure:
    """
    Plot feature similarity decay with distance.
    
    Parameters
    ----------
    decay_df : pd.DataFrame
        Output from distance_decay_analysis().
    ax : plt.Axes, optional
        Matplotlib axes to plot on. If None, creates new figure.
    figsize : Tuple[int, int], default (10, 6)
        Figure size if ax is None.
    title : str
        Plot title.
    
    Returns
    -------
    plt.Figure
        Matplotlib figure object.
    
    Notes
    -----
    Plots mean similarity with error bars (±1 SE), and fits an exponential
    decay model: similarity(d) = a * exp(-b*d).
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.get_figure()
    
    # Calculate bin centers for x-axis
    decay_df["bin_center"] = (decay_df["distance_min"] + decay_df["distance_max"]) / 2
    
    # Plot with error bars
    ax.errorbar(
        decay_df["bin_center"],
        decay_df["mean_similarity"],
        yerr=decay_df["se_similarity"],
        fmt="o-",
        capsize=5,
        markersize=8,
        linewidth=2,
        label="Mean similarity"
    )
    
    # Fit exponential decay model (optional)
    try:
        from scipy.optimize import curve_fit
        
        def exponential_decay(d, a, b):
            return a * np.exp(-b * d)
        
        popt, _ = curve_fit(
            exponential_decay,
            decay_df["bin_center"],
            decay_df["mean_similarity"],
            p0=[1, 0.001],
            maxfev=10000
        )
        
        x_fit = np.linspace(decay_df["distance_min"].min(), decay_df["distance_max"].max(), 100)
        y_fit = exponential_decay(x_fit, *popt)
        
        ax.plot(x_fit, y_fit, "r--", alpha=0.7, label=f"Fit: {popt[0]:.2f}*exp(-{popt[1]:.4f}*d)")
    except Exception as e:
        print(f"Warning: Could not fit exponential decay model: {e}")
    
    ax.set_xlabel("Geographic Distance (km)", fontsize=12)
    ax.set_ylabel("Mean Feature Similarity (Correlation)", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    return fig


def plot_morans_i_significant_features(
    feature_matrix: np.ndarray,
    coords: np.ndarray,
    feature_names: List[str],
    weight_type: str = "distance_band",
    threshold_km: float = 500,
    ax: Optional[plt.Axes] = None,
    figsize: Tuple[int, int] = (12, 8)
) -> Tuple[plt.Figure, pd.DataFrame]:
    """
    Plot Moran's I per feature with significance color-coding.
    
    Parameters
    ----------
    feature_matrix : np.ndarray
        Array of shape (N, K) with N cultures, K features.
    coords : np.ndarray
        Array of shape (N, 2) with [latitude, longitude].
    feature_names : List[str]
        Names of K features (for axis labels).
    weight_type : str, default "distance_band"
        Spatial weight matrix type.
    threshold_km : float, default 500
        Distance threshold for weight matrix.
    ax : plt.Axes, optional
        Matplotlib axes to plot on. If None, creates new figure.
    figsize : Tuple[int, int], default (12, 8)
        Figure size if ax is None.
    
    Returns
    -------
    Tuple[plt.Figure, pd.DataFrame]
        - Figure object
        - DataFrame with columns: feature, I, p_value, interpretation, color
    
    Notes
    -----
    Color code:
    - Red: Significant positive autocorrelation (p < 0.05)
    - Blue: Significant negative autocorrelation (p < 0.05)
    - Gray: Not significant (p >= 0.05)
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.get_figure()
    
    # Compute Moran's I for each feature
    results = []
    for k, feature_name in enumerate(feature_names):
        result = morans_i(
            feature_matrix[:, k],
            coords,
            weight_type=weight_type,
            threshold_km=threshold_km
        )
        
        if result["p_value"] < 0.05:
            if result["statistic"] > 0:
                color = "red"
            else:
                color = "blue"
        else:
            color = "gray"
        
        results.append({
            "feature": feature_name,
            "I": result["statistic"],
            "p_value": result["p_value"],
            "z_score": result["z_score"],
            "interpretation": result["interpretation"],
            "color": color
        })
    
    results_df = pd.DataFrame(results)
    
    # Plot
    colors = results_df["color"].tolist()
    ax.barh(results_df["feature"], results_df["I"], color=colors, alpha=0.7)
    ax.axvline(x=0, color="black", linestyle="-", linewidth=0.8)
    ax.set_xlabel("Moran's I", fontsize=12)
    ax.set_title("Spatial Autocorrelation per Feature", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="x")
    
    # Add significance stars
    for idx, (feature, pval) in enumerate(zip(results_df["feature"], results_df["p_value"])):
        if pval < 0.001:
            sig_text = "***"
        elif pval < 0.01:
            sig_text = "**"
        elif pval < 0.05:
            sig_text = "*"
        else:
            sig_text = "ns"
        ax.text(0.02, idx, sig_text, va="center", fontsize=10, fontweight="bold")
    
    return fig, results_df
