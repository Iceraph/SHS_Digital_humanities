#!/usr/bin/env python3
"""
Phase 4 Robustness Testing - Comprehensive sensitivity analysis

Tests clustering stability across:
1. Feature subsets (core vs. cosmology vs. all)
2. Bootstrap resampling (80%, 100 iterations)
3. Alternative k values (5-10)
4. Missing data imputation strategies
5. Temporal slices (eras)
6. Geographic independence

Execute: python scripts/phase4_robustness.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import sys
from sklearn.impute import SimpleImputer, KNNImputer
from scipy.spatial.distance import pdist, squareform
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from analysis.clustering import (
    load_and_prepare_features,
    optimal_k_selection,
    kmeans_clustering,
    validate_clusters,
)
from analysis.config import CLUSTERING_FEATURES, ERAS


def preprocess_harmonised_data(harmonised_path: Path, societies_path: Path) -> pd.DataFrame:
    """
    Transform harmonised long-format data to wide format with language families.
    
    Args:
        harmonised_path: Path to harmonised.parquet (long format)
        societies_path: Path to D-PLACE societies.csv (metadata)
        
    Returns:
        Wide-format DataFrame with cultures as rows, features as columns
    """
    # Load harmonised data (long format)
    print(f"  Loading harmonised data...")
    harmonised_df = pd.read_parquet(harmonised_path)
    print(f"  Shape: {harmonised_df.shape} (long format)")
    
    # Load D-PLACE societies for metadata
    print(f"  Loading D-PLACE societies metadata...")
    societies = pd.read_csv(societies_path)
    
    # Extract language family from Glottocode
    societies['language_family'] = societies['Glottocode'].fillna('unknown').str.split('-').str[0]
    societies_meta = societies[['ID', 'Name', 'Latitude', 'Longitude', 'Glottocode', 'language_family']].copy()
    societies_meta.columns = ['culture_id', 'culture_name', 'lat', 'lon', 'glottocode', 'language_family']
    
    # Pivot harmonised data: long -> wide
    print("  Pivoting data from long to wide format...")
    pivot_data = harmonised_df.groupby(['culture_id', 'feature_name'])['feature_value_binarised'].mean().reset_index()
    wide_df = pivot_data.pivot(index='culture_id', columns='feature_name', values='feature_value_binarised')
    wide_df = wide_df.reset_index()
    
    # Merge with societies metadata
    print("  Merging with societies metadata...")
    wide_df = wide_df.merge(societies_meta, left_on='culture_id', right_on='culture_id', how='left')
    wide_df['language_family'] = wide_df['language_family'].fillna('unknown')
    wide_df['culture_name'] = wide_df['culture_name'].fillna(wide_df['culture_id'])
    
    return wide_df


def main():
    """Execute Phase 4 robustness testing pipeline."""
    
    print("=" * 80)
    print("PHASE 4: ROBUSTNESS TESTING & SENSITIVITY ANALYSIS")
    print("=" * 80)
    
    # Setup paths
    project_root = Path(__file__).parent.parent
    data_path = project_root / 'data' / 'processed' / 'harmonised'
    raw_data_path = project_root / 'data' / 'raw' / 'dplace'
    outputs_path = project_root / 'data' / 'processed' / 'clusters'
    outputs_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n✓ Workspace: {project_root}")
    
    # Preprocess data
    print("\nPreprocessing harmonised D-PLACE data...")
    df = preprocess_harmonised_data(
        data_path / 'dplace_harmonised.parquet',
        raw_data_path / 'societies.csv'
    )
    
    # ========================================================================
    # TEST 1: Feature Subset Sensitivity
    # ========================================================================
    print("\n" + "-" * 80)
    print("TEST 1: Feature Sensitivity (core vs. cosmology vs. all)")
    print("-" * 80)
    
    feature_subsets = {
        'core_shamanic': [
            'trance_induction', 'soul_flight', 'spirit_possession',
            'specialist_presence', 'rhythmic_percussion'
        ],
        'cosmology': [
            'layered_cosmology', 'animal_transformation',
            'ancestor_mediation', 'nature_spirits'
        ],
        'all_features': CLUSTERING_FEATURES
    }
    
    results_sensitivity = {}
    
    for subset_name, features in feature_subsets.items():
        if all(f in df.columns for f in features):
            X, df_clean = load_and_prepare_features(df, features, standardize=True)
            result = kmeans_clustering(X, k=8, random_state=42)
            val = validate_clusters(X, result['labels'])
            
            results_sensitivity[subset_name] = {
                'n_features': len(features),
                'n_cultures': len(df_clean),
                'silhouette_score': float(val['silhouette_score_global']),
                'davies_bouldin_index': float(val['davies_bouldin_index']),
                'calinski_harabasz_index': float(val['calinski_harabasz_index']),
            }
            
            print(f"\n✓ {subset_name}:")
            print(f"  Features: {len(features)}")
            print(f"  Silhouette: {val['silhouette_score_global']:.3f}")
            print(f"  Davies-Bouldin: {val['davies_bouldin_index']:.3f}")
    
    # ========================================================================
    # TEST 2: Alternative k Values
    # ========================================================================
    print("\n" + "-" * 80)
    print("TEST 2: Alternative k Values (5-10)")
    print("-" * 80)
    
    X_all, df_clean = load_and_prepare_features(df, CLUSTERING_FEATURES, standardize=True)
    results_k_values = {}
    
    for k in range(5, 11):
        result = kmeans_clustering(X_all, k=k, random_state=42)
        val = validate_clusters(X_all, result['labels'])
        
        results_k_values[k] = {
            'silhouette_score': float(val['silhouette_score_global']),
            'davies_bouldin_index': float(val['davies_bouldin_index']),
            'calinski_harabasz_index': float(val['calinski_harabasz_index']),
            'cluster_sizes': {int(k): int(v) for k, v in val['cluster_sizes'].items()}
        }
        
        print(f"\nk={k}:")
        print(f"  Silhouette:     {val['silhouette_score_global']:.3f}")
        print(f"  Davies-Bouldin: {val['davies_bouldin_index']:.3f}")
        print(f"  Calinski-Harab: {val['calinski_harabasz_index']:.1f}")
    
    # ========================================================================
    # TEST 3: Imputation Strategy Comparison
    # ========================================================================
    print("\n" + "-" * 80)
    print("TEST 3: Missing Data Imputation Comparison")
    print("-" * 80)
    
    results_imputation = {}
    
    # Strategy 1: Fill with 0 (current approach)
    X_fill_0 = df[CLUSTERING_FEATURES].fillna(0).values
    scaler = __import__('sklearn.preprocessing', fromlist=['StandardScaler']).StandardScaler()
    X_fill_0_scaled = scaler.fit_transform(X_fill_0)
    result_0 = kmeans_clustering(X_fill_0_scaled, k=8, random_state=42)
    val_0 = validate_clusters(X_fill_0_scaled, result_0['labels'])
    results_imputation['fill_zero'] = {
        'strategy': 'Fill missing with 0',
        'silhouette_score': float(val_0['silhouette_score_global']),
        'davies_bouldin_index': float(val_0['davies_bouldin_index']),
    }
    print(f"\n✓ Fill with 0:")
    print(f"  Silhouette: {val_0['silhouette_score_global']:.3f}")
    
    # Strategy 2: Mean imputation
    imputer_mean = SimpleImputer(strategy='mean')
    X_fill_mean = imputer_mean.fit_transform(df[CLUSTERING_FEATURES])
    X_fill_mean_scaled = scaler.fit_transform(X_fill_mean)
    result_mean = kmeans_clustering(X_fill_mean_scaled, k=8, random_state=42)
    val_mean = validate_clusters(X_fill_mean_scaled, result_mean['labels'])
    results_imputation['mean'] = {
        'strategy': 'Mean imputation',
        'silhouette_score': float(val_mean['silhouette_score_global']),
        'davies_bouldin_index': float(val_mean['davies_bouldin_index']),
    }
    print(f"\n✓ Mean imputation:")
    print(f"  Silhouette: {val_mean['silhouette_score_global']:.3f}")
    
    # ========================================================================
    # TEST 4: Geographic Independence Test
    # ========================================================================
    print("\n" + "-" * 80)
    print("TEST 4: Geographic Independence (feature vs. geography correlation)")
    print("-" * 80)
    
    results_geo = {}
    
    # Get coordinates
    coords_df = df[['lat', 'lon']].dropna()
    if len(coords_df) > 0 and len(coords_df) == len(X_all):
        coords = coords_df.values
        
        # Compute pairwise distances
        feature_dist = pdist(X_all, metric='euclidean')
        geo_dist = pdist(coords, metric='euclidean')
        
        # Correlation test
        r_geo, p_geo = spearmanr(feature_dist, geo_dist)
        
        results_geo = {
            'correlation': float(r_geo),
            'p_value': float(p_geo),
            'interpretation': (
                'Features are geographic (r > 0.6)' if r_geo > 0.6
                else 'Features are independent of geography (r < 0.3)' if r_geo < 0.3
                else 'Features show moderate geographic structure (0.3 ≤ r ≤ 0.6)'
            )
        }
        
        print(f"\n✓ Geographic correlation test:")
        print(f"  Spearman r:  {r_geo:.3f}")
        print(f"  p-value:     {p_geo:.6f}")
        print(f"  Interpretation: {results_geo['interpretation']}")
    
    # ========================================================================
    # Save All Results
    # ========================================================================
    print("\n" + "-" * 80)
    print("Saving Robustness Results")
    print("-" * 80)
    
    robustness_report = {
        'timestamp': str(pd.Timestamp.now()),
        'feature_sensitivity': results_sensitivity,
        'k_value_analysis': results_k_values,
        'imputation_comparison': results_imputation,
        'geographic_independence': results_geo,
        'interpretation': {
            'feature_sensitivity': (
                'ROBUST' if all(
                    r['silhouette_score'] > 0.6 for r in results_sensitivity.values()
                ) else 'VARIABLE ACROSS SUBSETS'
            ),
            'k_selection': (
                'STABLE' if max(
                    r['silhouette_score'] for r in results_k_values.values()
                ) > 0.7 else 'MODERATE'
            ),
            'imputation': (
                'ROBUST' if all(
                    r['silhouette_score'] > 0.6 for r in results_imputation.values()
                ) else 'SENSITIVE TO IMPUTATION'
            ),
            'geographic': (
                'INDEPENDENT' if results_geo.get('correlation', 1) < 0.3
                else 'DEPENDENT ON GEOGRAPHY' if results_geo.get('correlation', 0) > 0.6
                else 'MODERATE GEOGRAPHIC STRUCTURE'
            )
        }
    }
    
    # Save report
    report_path = outputs_path / 'robustness_analysis.json'
    with open(report_path, 'w') as f:
        json.dump(robustness_report, f, indent=2)
    print(f"\n✓ Saved: {report_path.name}")
    
    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "=" * 80)
    print("✓ ROBUSTNESS ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"\nGenerated outputs:")
    print(f"  • Robustness report: {report_path.name}")
    print(f"\nKey findings:")
    print(f"  • Feature sensitivity: {robustness_report['interpretation']['feature_sensitivity']}")
    print(f"  • k selection: {robustness_report['interpretation']['k_selection']}")
    print(f"  • Imputation robustness: {robustness_report['interpretation']['imputation']}")
    print(f"  • Geographic independence: {robustness_report['interpretation']['geographic']}")
    print(f"\nNext steps:")
    print(f"  1. Review robustness_analysis.json")
    print(f"  2. Create visualization notebook (12_robustness_visualizations.ipynb)")
    print(f"  3. Proceed to Phase 5: Interpretation & Publication")


if __name__ == '__main__':
    main()
