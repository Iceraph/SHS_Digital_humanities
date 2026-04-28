#!/usr/bin/env python3
"""
Calculate Moran's I spatial autocorrelation for ALL 64 shamanic features.

This extends the Phase 6 analysis (19 features) to the complete feature set,
enabling comprehensive spatial analysis across the entire dataset.

Output: Updates phase7_visualization/data/analysis_results.json with complete coverage
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
import sys
from scipy.spatial.distance import cdist
from scipy import stats

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def load_data():
    """Load culture data and feature matrix."""
    print("Loading data...")
    
    # Load raw parquet
    dplace = pd.read_parquet('data/processed/dplace_real.parquet')
    
    # Create feature matrix (N cultures × K features)
    features_matrix = dplace.pivot_table(
        index='culture_id',
        columns='variable_name',
        values='variable_value',
        aggfunc='first'
    ).fillna(0).astype(int)
    
    # Get culture coordinates
    culture_meta = dplace.drop_duplicates(
        subset=['culture_id'],
        keep='first'
    )[['culture_id', 'lat', 'lon']].set_index('culture_id')
    
    # Align coordinates with features (same row order)
    coords = culture_meta.loc[features_matrix.index][['lat', 'lon']].values
    
    print(f"✓ Loaded {len(features_matrix)} cultures")
    print(f"✓ Loaded {features_matrix.shape[1]} features")
    print(f"✓ Coordinates: shape {coords.shape}")
    
    return features_matrix, coords


def create_spatial_weights(coords, threshold_km=500):
    """
    Create distance-band spatial weight matrix.
    
    Uses Haversine distance to identify neighbors within threshold_km.
    Row-standardizes weights for valid autocorrelation calculation.
    """
    print(f"\nCreating spatial weights (threshold: {threshold_km} km)...")
    
    def haversine_distances(coords):
        """Compute pairwise Haversine distances in km."""
        from math import radians, sin, cos, sqrt, atan2
        
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371  # Earth radius in km
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
            # Clamp a to [0, 1] to handle floating-point precision errors
            a = max(0, min(1, a))
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            return R * c
        
        n = len(coords)
        distances = np.zeros((n, n))
        for i in range(n):
            for j in range(i+1, n):
                dist = haversine(coords[i, 0], coords[i, 1],
                               coords[j, 0], coords[j, 1])
                distances[i, j] = dist
                distances[j, i] = dist
        return distances
    
    # Calculate distances
    distances = haversine_distances(coords)
    
    # Create binary weight matrix (1 if within threshold, 0 otherwise)
    W = (distances <= threshold_km).astype(float)
    np.fill_diagonal(W, 0)  # Remove self-weights
    
    # Row-standardize weights
    row_sums = W.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1  # Avoid division by zero
    W = W / row_sums
    
    # Count neighbors
    neighbor_counts = (distances <= threshold_km).sum(axis=1) - 1  # Exclude self
    avg_neighbors = neighbor_counts.mean()
    
    print(f"✓ Weight matrix created: shape {W.shape}")
    print(f"✓ Average neighbors per culture: {avg_neighbors:.1f}")
    print(f"✓ Sparsity: {(W == 0).sum() / W.size * 100:.1f}% zeros")
    
    return W


def calculate_morans_i(feature_values, W):
    """
    Calculate Moran's I and associated statistics.
    
    Args:
        feature_values: Binary array (0/1) for feature presence
        W: Row-standardized spatial weight matrix
        
    Returns:
        dict with statistic, p_value, z_score, significant, interpretation
    """
    x = feature_values.astype(float)
    n = len(x)
    
    # Skip if no variance or all zeros
    if x.std() == 0 or x.sum() < 2:
        return {
            'statistic': np.nan,
            'p_value': np.nan,
            'z_score': np.nan,
            'significant': False,
            'interpretation': 'Insufficient data (no variance or too few cases)'
        }
    
    # Demean
    x_dev = x - x.mean()
    
    # Moran's I calculation
    # I = (n / sum(W)) * (sum_ij w_ij * x_i * x_j) / sum_i x_i^2
    numerator = (x_dev @ W @ x_dev)
    denominator = (x_dev @ x_dev)
    I = (n / W.sum()) * (numerator / denominator)
    
    # Expected value under null hypothesis
    E_I = -1.0 / (n - 1)
    
    # Variance calculation (simplified but robust version)
    # Following Cliff & Ord (1981)
    b2 = (x_dev**2).sum() / (x_dev**2).mean()
    
    S1 = (W + W.T)**2 / 2  # Symmetric part
    S1 = S1.sum()
    
    S2 = (W.sum(axis=1) ** 2).sum()
    S3 = (x_dev**4).sum() / (x_dev**2).mean() ** 2
    S4 = (x_dev**2).sum() ** 2
    S5 = (x_dev**4).sum()
    
    var_I = ((n * S1 - b2 * S2 + 3 * S4) / (S4**2)) - (E_I ** 2)
    
    # Ensure positive variance
    if var_I <= 0:
        var_I = ((1.0 / (n - 1)) * ((n - b2/n)**2 / (n - 1))) ** 2
    
    # Z-score and p-value
    z_score = (I - E_I) / np.sqrt(var_I) if var_I > 0 else 0
    p_value = 2 * (1 - stats.norm.cdf(np.abs(z_score)))  # Two-tailed
    
    # Interpretation
    interpretation = _interpret_morans_i(I, p_value)
    
    return {
        'statistic': float(I),
        'p_value': float(p_value),
        'z_score': float(z_score),
        'significant': bool(p_value < 0.05),
        'interpretation': interpretation
    }


def _interpret_morans_i(I, p_value):
    """Generate human-readable interpretation."""
    if np.isnan(I):
        return "Insufficient data"
    
    if p_value >= 0.05:
        return "Random spatial distribution (no significant autocorrelation)"
    elif I > 0.2:
        return "Significant positive spatial autocorrelation (strong clustering)"
    elif I > 0.05:
        return "Significant positive spatial autocorrelation (clustering)"
    elif I < -0.2:
        return "Significant negative spatial autocorrelation (strong dispersal)"
    elif I < -0.05:
        return "Significant negative spatial autocorrelation (dispersal)"
    return "Ambiguous pattern"


def calculate_all_features(features_matrix, W):
    """Calculate Moran's I for all features."""
    print(f"\nCalculating Moran's I for {features_matrix.shape[1]} features...")
    print("(This may take 2-5 minutes)...\n")
    
    results = []
    
    for idx, feature_name in enumerate(features_matrix.columns, 1):
        if idx % 10 == 0:
            print(f"  Progress: {idx}/{features_matrix.shape[1]} features processed...")
        
        feature_values = features_matrix[feature_name].values
        result = calculate_morans_i(feature_values, W)
        
        result['feature'] = feature_name
        result['n_ones'] = int(feature_values.sum())
        result['n_zeros'] = int((1 - feature_values).sum())
        
        results.append(result)
    
    return pd.DataFrame(results)


def update_phase7_analysis_results(morans_results_df):
    """
    Update phase7_visualization/data/analysis_results.json with new Moran's I data.
    
    Preserves existing data (mantel, phylogenetic_signal, distance_decay, hypothesis_synthesis)
    and replaces/extends morans_i array.
    """
    print("\nUpdating Phase 7 analysis_results.json...")
    
    analysis_path = Path('phase7_visualization/data/analysis_results.json')
    
    # Load existing data
    with open(analysis_path, 'r') as f:
        analysis_data = json.load(f)
    
    # Convert new results to records (dicts)
    morans_records = morans_results_df.to_dict('records')
    
    # Update morans_i in analysis data
    analysis_data['morans_i'] = morans_records
    
    # Save updated file
    with open(analysis_path, 'w') as f:
        json.dump(analysis_data, f, indent=2)
    
    print(f"✓ Updated {analysis_path}")
    print(f"  - Moran's I coverage: {len(morans_records)} features")
    
    # Also save detailed results as CSV for reference
    csv_path = Path('data/processed/spatial_analysis_phase6/morans_i_all_features.csv')
    morans_results_df.to_csv(csv_path, index=False)
    print(f"✓ Saved detailed results to {csv_path}")
    
    return morans_records


def print_summary(morans_results_df):
    """Print summary statistics."""
    print("\n" + "="*70)
    print("MORAN'S I ANALYSIS SUMMARY")
    print("="*70)
    
    # Filter valid results (not NaN)
    valid = morans_results_df[~morans_results_df['statistic'].isna()]
    
    print(f"\nTotal features analyzed: {len(valid)}")
    
    # Count by significance
    sig_positive = ((valid['p_value'] < 0.05) & (valid['statistic'] > 0.05)).sum()
    sig_negative = ((valid['p_value'] < 0.05) & (valid['statistic'] < -0.05)).sum()
    not_sig = (valid['p_value'] >= 0.05).sum()
    
    print(f"\nSignificant Positive (Clustering): {sig_positive} features ({sig_positive/len(valid)*100:.1f}%)")
    print(f"Significant Negative (Dispersal): {sig_negative} features ({sig_negative/len(valid)*100:.1f}%)")
    print(f"Not Significant (Random): {not_sig} features ({not_sig/len(valid)*100:.1f}%)")
    
    print(f"\nMoran's I Statistics:")
    print(f"  Mean: {valid['statistic'].mean():.4f}")
    print(f"  Std:  {valid['statistic'].std():.4f}")
    print(f"  Min:  {valid['statistic'].min():.4f}")
    print(f"  Max:  {valid['statistic'].max():.4f}")
    
    print(f"\nMost Clustered Features (top 5):")
    top_clustered = valid.nlargest(5, 'statistic')[['feature', 'statistic', 'p_value']]
    for idx, row in top_clustered.iterrows():
        print(f"  {row['feature']:30s} I={row['statistic']:7.4f} p={row['p_value']:.4f}")
    
    print(f"\nMost Dispersed Features (top 5):")
    top_dispersed = valid.nsmallest(5, 'statistic')[['feature', 'statistic', 'p_value']]
    for idx, row in top_dispersed.iterrows():
        print(f"  {row['feature']:30s} I={row['statistic']:7.4f} p={row['p_value']:.4f}")
    
    print("\n" + "="*70)


def main():
    """Main execution."""
    print("\n" + "="*70)
    print("PHASE 7 MORAN'S I EXTENSION - ALL 64 FEATURES")
    print("="*70)
    
    try:
        # Load data
        features_matrix, coords = load_data()
        
        # Create spatial weights
        W = create_spatial_weights(coords, threshold_km=500)
        
        # Calculate Moran's I for all features
        morans_results = calculate_all_features(features_matrix, W)
        
        # Update Phase 7 visualization data
        update_phase7_analysis_results(morans_results)
        
        # Print summary
        print_summary(morans_results)
        
        print("\n✅ COMPLETE: Moran's I calculated for all features")
        print("   Phase 7 visualization will now display spatial statistics for all features")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
