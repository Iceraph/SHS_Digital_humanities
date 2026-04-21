"""
Phase 4: Clustering & Phylogenetic-Independent Analysis

Unsupervised clustering on phylogenetically-filtered and full datasets.
Supports k-means and hierarchical clustering with validation metrics.

References:
- Mace & Pagel (1994): "The comparative method in anthropology" Current Anthropology
- Kaufman & Rousseeuw (1990): Finding Groups in Data
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, List, Optional, Any
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import (
    silhouette_score,
    silhouette_samples,
    davies_bouldin_score,
    calinski_harabasz_score,
    adjusted_rand_score,
    fowlkes_mallows_score,
)
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
import warnings

warnings.filterwarnings("ignore")


def load_and_prepare_features(
    df: pd.DataFrame,
    feature_columns: List[str],
    standardize: bool = True,
) -> Tuple[np.ndarray, pd.DataFrame]:
    """
    Load features and standardise for clustering.
    
    Args:
        df: Input DataFrame
        feature_columns: List of feature column names to cluster on
        standardize: Whether to apply z-score standardisation
        
    Returns:
        Tuple of (standardised feature matrix, DataFrame with valid rows)
    """
    # Start with input features
    df_clean = df[['culture_id', 'culture_name'] + feature_columns].copy()
    
    # Fill missing values with 0 (missing = not present for binary shamanic features)
    # This is justified because: (1) binary features (0/1), (2) sparse data is common in ethnographic work
    df_clean[feature_columns] = df_clean[feature_columns].fillna(0)
    
    if len(df_clean) == 0:
        raise ValueError("No data available for clustering")
    
    X = df_clean[feature_columns].values.astype(float)
    
    if standardize:
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
    else:
        X_scaled = X
    
    return X_scaled, df_clean


def optimal_k_selection(
    X: np.ndarray,
    k_range: range = range(2, 10),
    method: str = "silhouette",
    random_state: int = 42,
) -> Dict[str, Any]:
    """
    Determine optimal number of clusters using multiple methods.
    
    Args:
        X: Standardised feature matrix (n_samples, n_features)
        k_range: Range of k values to test
        method: 'silhouette', 'elbow', or 'both'
        random_state: Random seed for reproducibility
        
    Returns:
        Dictionary with optimal k and all scores
    """
    silhouette_scores_list = []
    davies_bouldin_scores_list = []
    calinski_harabasz_scores_list = []
    inertias = []
    
    for k in k_range:
        kmeans = KMeans(
            n_clusters=k,
            random_state=random_state,
            n_init=15,
            max_iter=500,
        )
        labels = kmeans.fit_predict(X)
        
        silhouette_scores_list.append(silhouette_score(X, labels))
        davies_bouldin_scores_list.append(davies_bouldin_score(X, labels))
        calinski_harabasz_scores_list.append(calinski_harabasz_score(X, labels))
        inertias.append(kmeans.inertia_)
    
    optimal_k_silhouette = list(k_range)[np.argmax(silhouette_scores_list)]
    optimal_k_davies_bouldin = list(k_range)[np.argmin(davies_bouldin_scores_list)]
    optimal_k_calinski = list(k_range)[np.argmax(calinski_harabasz_scores_list)]
    
    return {
        "k_range": list(k_range),
        "silhouette_scores": silhouette_scores_list,
        "davies_bouldin_scores": davies_bouldin_scores_list,
        "calinski_harabasz_scores": calinski_harabasz_scores_list,
        "inertias": inertias,
        "optimal_k_silhouette": optimal_k_silhouette,
        "optimal_k_davies_bouldin": optimal_k_davies_bouldin,
        "optimal_k_calinski": optimal_k_calinski,
        "best_silhouette": max(silhouette_scores_list),
        "recommended_k": optimal_k_silhouette,  # Use silhouette as primary metric
    }


def kmeans_clustering(
    X: np.ndarray,
    k: int = 5,
    random_state: int = 42,
    n_init: int = 15,
) -> Dict[str, Any]:
    """
    Perform k-means clustering.
    
    Args:
        X: Standardised feature matrix
        k: Number of clusters
        random_state: Random seed
        n_init: Number of initializations
        
    Returns:
        Dictionary with cluster labels, centroids, and inertia
    """
    kmeans = KMeans(
        n_clusters=k,
        random_state=random_state,
        n_init=n_init,
        max_iter=500,
    )
    labels = kmeans.fit_predict(X)
    
    return {
        "method": "kmeans",
        "k": k,
        "labels": labels,
        "centroids": kmeans.cluster_centers_,
        "inertia": kmeans.inertia_,
        "n_iter": kmeans.n_iter_,
        "model": kmeans,
    }


def hierarchical_clustering(
    X: np.ndarray,
    k: int = 5,
    linkage_method: str = "ward",
) -> Dict[str, Any]:
    """
    Perform hierarchical clustering with dendrogram linkage.
    
    Args:
        X: Standardised feature matrix
        k: Number of clusters
        linkage_method: 'ward', 'single', 'complete', 'average'
        
    Returns:
        Dictionary with cluster labels and linkage matrix
    """
    Z = linkage(X, method=linkage_method)
    labels = fcluster(Z, k, criterion="maxclust") - 1  # Convert to 0-indexed
    
    return {
        "method": "hierarchical",
        "linkage_method": linkage_method,
        "k": k,
        "labels": labels,
        "linkage_matrix": Z,
    }


def validate_clusters(
    X: np.ndarray,
    labels: np.ndarray,
) -> Dict[str, float]:
    """
    Comprehensive cluster validation metrics.
    
    Args:
        X: Feature matrix
        labels: Cluster assignments
        
    Returns:
        Dictionary of validation metrics
    """
    # Silhouette coefficient (per-sample and global)
    silhouette_global = silhouette_score(X, labels)
    silhouette_samples_array = silhouette_samples(X, labels)
    
    # Davies-Bouldin Index (lower = better)
    db_index = davies_bouldin_score(X, labels)
    
    # Calinski-Harabasz Index (higher = better)
    ch_index = calinski_harabasz_score(X, labels)
    
    # Cluster sizes
    unique_labels, counts = np.unique(labels, return_counts=True)
    cluster_sizes = dict(zip(unique_labels, counts))
    
    return {
        "silhouette_score_global": float(silhouette_global),
        "silhouette_samples": silhouette_samples_array.tolist(),
        "davies_bouldin_index": float(db_index),
        "calinski_harabasz_index": float(ch_index),
        "cluster_sizes": cluster_sizes,
        "n_clusters": len(unique_labels),
    }


def compare_clustering_methods(
    X: np.ndarray,
    k: int = 5,
    random_state: int = 42,
) -> Dict[str, Any]:
    """
    Compare k-means vs hierarchical clustering results.
    
    Args:
        X: Standardised feature matrix
        k: Number of clusters
        random_state: Random seed
        
    Returns:
        Comparison dictionary with ARI, Fowlkes-Mallows, and individual metrics
    """
    # K-means
    kmeans_result = kmeans_clustering(X, k=k, random_state=random_state)
    labels_kmeans = kmeans_result["labels"]
    
    # Hierarchical
    hierarchical_result = hierarchical_clustering(X, k=k, linkage_method="ward")
    labels_hierarchical = hierarchical_result["labels"]
    
    # Validation metrics
    val_kmeans = validate_clusters(X, labels_kmeans)
    val_hierarchical = validate_clusters(X, labels_hierarchical)
    
    # Comparison metrics
    ari = adjusted_rand_score(labels_kmeans, labels_hierarchical)
    fowlkes_mallows = fowlkes_mallows_score(labels_kmeans, labels_hierarchical)
    
    return {
        "kmeans": {
            **kmeans_result,
            "validation": val_kmeans,
        },
        "hierarchical": {
            **hierarchical_result,
            "validation": val_hierarchical,
        },
        "comparison": {
            "adjusted_rand_score": float(ari),
            "fowlkes_mallows_index": float(fowlkes_mallows),
            "methods_agreement": "high" if ari > 0.7 else "medium" if ari > 0.4 else "low",
        },
    }


def extract_cluster_profiles(
    df: pd.DataFrame,
    cluster_labels: np.ndarray,
    feature_columns: List[str],
) -> pd.DataFrame:
    """
    Extract feature presence rates per cluster.
    
    Args:
        df: Original DataFrame (before feature extraction)
        cluster_labels: Cluster assignments
        feature_columns: Columns to summarise
        
    Returns:
        DataFrame with cluster profiles (mean feature values per cluster)
    """
    df_with_clusters = df.copy()
    df_with_clusters["cluster"] = cluster_labels
    
    profiles = df_with_clusters.groupby("cluster")[feature_columns].mean()
    profiles["n_cultures"] = df_with_clusters.groupby("cluster").size()
    
    return profiles


def temporal_cluster_composition(
    df: pd.DataFrame,
    cluster_labels: np.ndarray,
    time_col: str = "time_start_ce",
) -> pd.DataFrame:
    """
    Analyse temporal composition of clusters.
    
    Args:
        df: DataFrame with temporal info
        cluster_labels: Cluster assignments
        time_col: Column name for time
        
    Returns:
        DataFrame with temporal statistics per cluster
    """
    df_with_clusters = df.copy()
    df_with_clusters["cluster"] = cluster_labels
    
    temporal_stats = df_with_clusters.groupby("cluster")[time_col].agg([
        "mean", "std", "min", "max", "count"
    ])
    temporal_stats.columns = ["mean_time", "std_time", "min_time", "max_time", "n_cultures"]
    
    return temporal_stats


def geographic_cluster_composition(
    df: pd.DataFrame,
    cluster_labels: np.ndarray,
    region_col: str = "region",
) -> pd.DataFrame:
    """
    Analyse geographic composition of clusters.
    
    Args:
        df: DataFrame with geographic info
        cluster_labels: Cluster assignments
        region_col: Column name for region
        
    Returns:
        DataFrame with region distribution per cluster
    """
    df_with_clusters = df.copy()
    df_with_clusters["cluster"] = cluster_labels
    
    # Cross-tabulation: clusters × regions
    geographic_dist = pd.crosstab(
        df_with_clusters["cluster"],
        df_with_clusters[region_col],
        margins=True
    )
    
    # Calculate percentages
    geographic_pct = geographic_dist.div(geographic_dist["All"], axis=0) * 100
    
    return geographic_pct


def stability_analysis(
    X: np.ndarray,
    k: int = 5,
    n_iterations: int = 100,
    random_state: int = 42,
) -> Dict[str, Any]:
    """
    Bootstrap stability analysis: cluster on random subsamples and measure stability.
    
    Args:
        X: Feature matrix
        k: Number of clusters
        n_iterations: Number of bootstrap resamples
        random_state: Random seed
        
    Returns:
        Stability statistics
    """
    np.random.seed(random_state)
    n_samples = len(X)
    sample_size = int(0.8 * n_samples)  # 80% bootstrap samples
    
    silhouette_scores_bootstrap = []
    
    for i in range(n_iterations):
        # Bootstrap sample
        indices = np.random.choice(n_samples, sample_size, replace=False)
        X_sample = X[indices]
        
        # Cluster
        kmeans = KMeans(n_clusters=k, random_state=i, n_init=10, max_iter=300)
        labels = kmeans.fit_predict(X_sample)
        
        # Score
        if len(np.unique(labels)) > 1:
            score = silhouette_score(X_sample, labels)
            silhouette_scores_bootstrap.append(score)
    
    return {
        "n_bootstrap_resamples": n_iterations,
        "sample_size_pct": 80,
        "mean_silhouette": float(np.mean(silhouette_scores_bootstrap)),
        "std_silhouette": float(np.std(silhouette_scores_bootstrap)),
        "min_silhouette": float(np.min(silhouette_scores_bootstrap)),
        "max_silhouette": float(np.max(silhouette_scores_bootstrap)),
        "stability_score": float(np.mean(silhouette_scores_bootstrap)),  # Mean stability
    }
