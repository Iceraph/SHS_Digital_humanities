#!/usr/bin/env python3
"""
Phase 4: Clustering & Phylogenetic Analysis - Implementation Script

Generates Phase 4 deliverables:
- Phylogenetically-filtered dataset
- Primary clustering (k-means + hierarchical)
- Validation metrics
- Robustness analysis
- Cluster profiles and interpretation

Execute: python scripts/phase4_clustering.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from analysis.phylogenetic import (
    filter_one_per_language_family,
    create_robustness_dataset_pair,
)
from analysis.clustering import (
    load_and_prepare_features,
    optimal_k_selection,
    kmeans_clustering,
    hierarchical_clustering,
    validate_clusters,
    compare_clustering_methods,
    extract_cluster_profiles,
    temporal_cluster_composition,
    geographic_cluster_composition,
    stability_analysis,
)
from analysis.config import CLUSTERING_FEATURES


def preprocess_harmonised_data(harmonised_path: Path, societies_path: Path) -> pd.DataFrame:
    """
    Transform harmonised long-format data to wide format with language families.
    
    Args:
        harmonised_path: Path to harmonised.parquet (long format)
        societies_path: Path to D-PLACE societies.csv (metadata)
        
    Returns:
        Wide-format DataFrame with cultures as rows, features as columns
    """
    # Load harmonised data (long format: rows = features per culture)
    print(f"Loading harmonised data from: {harmonised_path.name}")
    harmonised_df = pd.read_parquet(harmonised_path)
    print(f"  Shape: {harmonised_df.shape} (long format)")
    
    # Load D-PLACE societies for metadata (culture names, coordinates, Glottocodes)
    print(f"Loading D-PLACE societies metadata...")
    societies = pd.read_csv(societies_path)
    
    # Extract language family from Glottocode (use first part as proxy)
    # Glottocodes are hierarchical: family-subfamily-language
    # E.g., "indo1319" (Indo-European), "aust1305" (Austronesian)
    societies['language_family'] = societies['Glottocode'].fillna('unknown').str.split('-').str[0]
    
    # Keep only needed metadata columns
    societies_meta = societies[['ID', 'Name', 'Latitude', 'Longitude', 'Glottocode', 'language_family']].copy()
    societies_meta.columns = ['culture_id', 'culture_name', 'lat', 'lon', 'glottocode', 'language_family']
    
    # Pivot harmonised data: long -> wide
    # This transforms from (N_features * N_cultures) rows to N_cultures rows
    print("Pivoting data from long to wide format...")
    
    # First, aggregate by culture_id and feature_name (take mean of feature_value_binarised)
    pivot_data = harmonised_df.groupby(['culture_id', 'feature_name'])['feature_value_binarised'].mean().reset_index()
    
    # Now pivot to wide format
    wide_df = pivot_data.pivot(index='culture_id', columns='feature_name', values='feature_value_binarised')
    wide_df = wide_df.reset_index()
    
    print(f"  Shape after pivoting: {wide_df.shape} (wide format)")
    
    # Merge with societies metadata
    print("Merging with societies metadata...")
    wide_df = wide_df.merge(
        societies_meta,
        left_on='culture_id',
        right_on='culture_id',
        how='left'
    )
    
    # Fill missing metadata values
    wide_df['language_family'] = wide_df['language_family'].fillna('unknown')
    wide_df['culture_name'] = wide_df['culture_name'].fillna(wide_df['culture_id'])
    
    print(f"Final shape: {wide_df.shape}")
    print(f"Language families: {wide_df['language_family'].nunique()}")
    print(f"Cultures: {len(wide_df)}")
    
    return wide_df


def main():
    """Execute Phase 4 clustering pipeline."""
    
    print("=" * 80)
    print("PHASE 4: CLUSTERING & PHYLOGENETIC ANALYSIS")
    print("=" * 80)
    
    # Setup paths
    project_root = Path(__file__).parent.parent
    data_path = project_root / 'data' / 'processed' / 'harmonised'
    raw_path = project_root / 'data' / 'raw' / 'dplace'
    outputs_path = project_root / 'data' / 'processed' / 'clusters'
    viz_path = project_root / 'data' / 'visualizations' / 'clusters'
    outputs_path.mkdir(parents=True, exist_ok=True)
    viz_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n✓ Workspace: {project_root}")
    print(f"✓ Output directories created")
    
    # ============================================================================
    # STEP 1: Load & Phylogenetically Filter Data
    # ============================================================================
    print("\n" + "-" * 80)
    print("STEP 1: Data Preprocessing & Phylogenetic Filtering")
    print("-" * 80)
    
    # Preprocess: convert long-format harmonised data to wide format with metadata
    dplace_harmonised_path = data_path / 'dplace_harmonised.parquet'
    dplace_societies_path = raw_path / 'societies.csv'
    
    dplace_df = preprocess_harmonised_data(dplace_harmonised_path, dplace_societies_path)
    
    print(f"\n✓ Data preprocessed and ready for clustering")
    print(f"  Loaded {len(dplace_df):,} D-PLACE cultures from {dplace_df['language_family'].nunique():,} language families")
    
    # Generate paired datasets
    dplace_filtered, dplace_full = create_robustness_dataset_pair(dplace_df)
    
    print(f"\n✓ Phylogenetic Filtering Complete:")
    print(f"  Primary dataset (phylo-filtered):  {len(dplace_filtered):>6,} cultures (1 per language family)")
    print(f"  Robustness dataset (full dataset): {len(dplace_full):>6,} cultures")
    print(f"  Reduction ratio: {len(dplace_filtered)/len(dplace_full):>6.1%}")
    
    # ============================================================================
    # STEP 2: Feature Preparation
    # ============================================================================
    print("\n" + "-" * 80)
    print("STEP 2: Feature Preparation & Standardisation")
    print("-" * 80)
    
    # Get available features that exist in data
    available_features = [f for f in CLUSTERING_FEATURES if f in dplace_filtered.columns]
    print(f"\nClustering features available: {len(available_features)}")
    
    # Prepare features for primary (filtered) dataset
    X_filtered, df_filtered_clean = load_and_prepare_features(
        dplace_filtered,
        available_features,
        standardize=True
    )
    print(f"✓ Primary dataset prepared: {X_filtered.shape[0]} cultures × {X_filtered.shape[1]} features")
    print(f"  Features z-scaled: mean ≈ {X_filtered.mean():.3f}, std ≈ {X_filtered.std():.3f}")
    
    # ============================================================================
    # STEP 3: Optimal k Selection
    # ============================================================================
    print("\n" + "-" * 80)
    print("STEP 3: Optimal k Selection (Silhouette + Elbow Analysis)")
    print("-" * 80)
    
    k_selection = optimal_k_selection(X_filtered, k_range=range(2, 10))
    optimal_k = k_selection['recommended_k']
    
    print(f"\n✓ Optimal k Analysis:")
    print(f"  Silhouette scores: {[f'{s:.3f}' for s in k_selection['silhouette_scores']]}")
    print(f"  Optimal k (silhouette method): {optimal_k}")
    print(f"  Best silhouette score: {k_selection['best_silhouette']:.3f}")
    
    # ============================================================================
    # STEP 4: Primary Clustering
    # ============================================================================
    print("\n" + "-" * 80)
    print(f"STEP 4: Primary Clustering (k={optimal_k})")
    print("-" * 80)
    
    # K-means
    print(f"\nApplying k-means clustering...")
    kmeans_result = kmeans_clustering(X_filtered, k=optimal_k, random_state=42)
    labels_kmeans = kmeans_result['labels']
    val_kmeans = validate_clusters(X_filtered, labels_kmeans)
    
    print(f"✓ K-means clustering complete:")
    print(f"  Silhouette score: {val_kmeans['silhouette_score_global']:.3f}")
    print(f"  Davies-Bouldin index: {val_kmeans['davies_bouldin_index']:.3f}")
    print(f"  Calinski-Harabasz index: {val_kmeans['calinski_harabasz_index']:.1f}")
    print(f"  Cluster sizes: {val_kmeans['cluster_sizes']}")
    
    # Hierarchical
    print(f"\nApplying hierarchical clustering (Ward's linkage)...")
    hier_result = hierarchical_clustering(X_filtered, k=optimal_k, linkage_method='ward')
    labels_hierarchical = hier_result['labels']
    val_hierarchical = validate_clusters(X_filtered, labels_hierarchical)
    
    print(f"✓ Hierarchical clustering complete:")
    print(f"  Silhouette score: {val_hierarchical['silhouette_score_global']:.3f}")
    print(f"  Davies-Bouldin index: {val_hierarchical['davies_bouldin_index']:.3f}")
    
    # Compare methods
    ari = kmeans_result.get('ari', 0) if isinstance(kmeans_result, dict) and 'ari' in kmeans_result else 0.0
    print(f"\nMethod comparison (ARI): {ari:.3f} → methods {'agree well' if ari > 0.7 else 'differ'}")
    
    # ============================================================================
    # STEP 5: Extract Cluster Profiles
    # ============================================================================
    print("\n" + "-" * 80)
    print("STEP 5: Cluster Profiles & Interpretation")
    print("-" * 80)
    
    # Add cluster labels to dataframe
    df_filtered_with_clusters = df_filtered_clean.copy()
    df_filtered_with_clusters['cluster'] = labels_kmeans
    
    # Extract profiles
    profiles = extract_cluster_profiles(df_filtered_with_clusters, labels_kmeans, available_features)
    print(f"\n✓ Cluster profiles extracted:")
    print(f"  Shape: {profiles.shape}")
    print(f"\nTop features per cluster:")
    for cluster_id in range(optimal_k):
        if cluster_id in profiles.index:
            top_features = profiles.loc[cluster_id, available_features].nlargest(3)
            print(f"  Cluster {cluster_id}: {', '.join(f'{feat}({val:.2f})' for feat, val in top_features.items())}")
    
    # ============================================================================
    # STEP 6: Save Outputs
    # ============================================================================
    print("\n" + "-" * 80)
    print("STEP 6: Saving Outputs")
    print("-" * 80)
    
    # Save cluster assignments
    cluster_assignments = pd.DataFrame({
        'culture_id': df_filtered_clean['culture_id'] if 'culture_id' in df_filtered_clean.columns else range(len(labels_kmeans)),
        'cluster_id': labels_kmeans,
        'method': 'kmeans'
    })
    assignments_path = outputs_path / 'culture_cluster_membership.csv'
    cluster_assignments.to_csv(assignments_path, index=False)
    print(f"✓ Saved: {assignments_path.name}")
    
    # Save cluster profiles
    profiles_path = outputs_path / 'cluster_profiles.csv'
    profiles.to_csv(profiles_path)
    print(f"✓ Saved: {profiles_path.name}")
    
    # Save validation metrics
    metrics = {
        'phylogenetic_filtering': {
            'n_filtered': int(len(dplace_filtered)),
            'n_full': int(len(dplace_full)),
            'method': 'one_per_language_family'
        },
        'clustering_kmeans': {
            'k': int(optimal_k),
            'silhouette_score': float(val_kmeans['silhouette_score_global']),
            'davies_bouldin_index': float(val_kmeans['davies_bouldin_index']),
            'calinski_harabasz_index': float(val_kmeans['calinski_harabasz_index']),
            'cluster_sizes': {int(k): int(v) for k, v in val_kmeans['cluster_sizes'].items()}
        },
        'k_selection_analysis': {
            'k_range': [int(k) for k in k_selection['k_range']],
            'optimal_k': int(k_selection['recommended_k']),
            'best_silhouette': float(k_selection['best_silhouette'])
        }
    }
    
    metrics_path = outputs_path / 'validation_metrics.json'
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"✓ Saved: {metrics_path.name}")
    
    # ============================================================================
    # SUMMARY
    # ============================================================================
    print("\n" + "=" * 80)
    print("✓ PHASE 4 IMPLEMENTATION COMPLETE")
    print("=" * 80)
    print(f"\nGenerated outputs:")
    print(f"  • Cluster assignments: {assignments_path.name}")
    print(f"  • Cluster profiles: {profiles_path.name}")
    print(f"  • Validation metrics: {metrics_path.name}")
    print(f"\nKey metrics:")
    print(f"  • Optimal clusters (k): {optimal_k}")
    print(f"  • Silhouette score: {val_kmeans['silhouette_score_global']:.3f} (target > 0.4)")
    print(f"  • Phylogenetically-independent cultures: {len(dplace_filtered):,}")
    print(f"\nNext steps:")
    print(f"  1. Run notebook 10_robustness_analysis.ipynb for full dataset comparison")
    print(f"  2. Run notebook 11_cluster_interpretation.ipynb for hypothesis evaluation")
    print(f"  3. Review cluster profiles and geographic/temporal distributions")


if __name__ == '__main__':
    main()
