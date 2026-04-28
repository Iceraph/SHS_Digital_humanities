# Moran's I Spatial Autocorrelation Analysis
**Phase 7 Documentation** | Priority 3b

## Overview

Moran's I is a spatial autocorrelation statistic that measures whether a feature's distribution across geographic space is **clustered**, **dispersed**, or **random**. This is critical for understanding cultural patterns in shamanism research.

## Current Coverage

**Status**: 19/64 features analyzed (29.7% coverage)

### Features with Moran's I Data
The following features have pre-calculated spatial statistics (stored as `feature_0` through `feature_18` in `analysis_results.json`):

```
feature_0, feature_1, feature_2, ..., feature_18
(Total: 19 features)
```

**Mapping Note**: The current analysis uses generic indices (`feature_0` to `feature_18`) rather than the actual feature names. A feature mapping CSV exists at:
- `data/processed/spatial_analysis_phase6/morans_i_per_feature.csv`

### Features Pending Analysis
45 features from the complete dataset (57 total features with presence data) do not yet have spatial statistics calculated. These are displayed with a "Spatial analysis data pending..." message in the UI.

## Methodology

### 1. Moran's I Statistic

**Definition**:
$$I = \frac{n}{\sum_{i,j} w_{ij}} \cdot \frac{\sum_{i,j} w_{ij}(x_i - \bar{x})(x_j - \bar{x})}{\sum_i (x_i - \bar{x})^2}$$

Where:
- $n$ = number of observations (cultures)
- $w_{ij}$ = spatial weight between cultures $i$ and $j$
- $x_i$ = feature value for culture $i$ (1 = present, 0 = absent)
- $\bar{x}$ = mean feature value

### 2. Spatial Weights

The analysis uses **distance-band weights** with a threshold of **500 km**:

```python
# Weight calculation (simplified)
w[i,j] = 1 if distance(i,j) <= 500 km else 0
```

This means two cultures "count as neighbors" if they're within 500 km of each other.

### 3. Interpretation

#### Moran's I Value Range: [-1.0, +1.0]

| Range | Interpretation | Meaning |
|-------|---|---|
| **I > 0.3** | Strong positive autocorrelation | Cultures with feature cluster together; geographic proximity predicts feature presence |
| **I > 0.1** | Moderate positive autocorrelation | Some clustering tendency |
| **-0.1 < I < 0.1** | No autocorrelation | Random spatial distribution; presence is independent of geography |
| **I < -0.1** | Negative autocorrelation | Dispersion: cultures with feature avoid each other spatially |
| **I < -0.3** | Strong negative autocorrelation | Strong checkerboard pattern |

#### Significance Testing

**P-value Interpretation**:
- **p < 0.01**: Highly significant (★★) - Pattern is unlikely to occur by chance
- **p < 0.05**: Significant (★) - Pattern has <5% probability of random occurrence
- **p ≥ 0.05**: Not significant - Pattern could easily occur by chance

**Z-score**:
- Z = (I - E[I]) / √Var(I)
- |Z| > 1.96 indicates significance at p < 0.05 level

### 4. Current Implementation

The calculation is performed in `src/analysis/spatial.py`:

```python
def morans_i(feature_vector: np.ndarray, coords: np.ndarray, 
             weight_type: str = "distance_band", 
             threshold_km: float = 500) -> dict:
    """
    Calculate Moran's I for a binary feature.
    
    Args:
        feature_vector: Array of 0/1 values for cultures
        coords: Array of [latitude, longitude] coordinates
        weight_type: "distance_band" or other weight matrix type
        threshold_km: Distance threshold for neighbors
        
    Returns:
        {
            "statistic": float,      # Moran's I value
            "p_value": float,        # Significance level
            "z_score": float,        # Standardized score
            "significant": bool,     # p < 0.05
            "interpretation": str    # Human-readable description
        }
    """
```

## Phase 6 Analysis Results

### Sample Output

```json
{
  "feature": "feature_4",
  "n_ones": 150,
  "n_zeros": 1700,
  "statistic": 0.2845,
  "p_value": 0.0023,
  "z_score": 3.0845,
  "significant": true,
  "interpretation": "Significant positive spatial autocorrelation (cultures with this feature cluster together geographically)"
}
```

### Key Findings (from 19 features analyzed)

- **Significant Clustering** (p < 0.05, I > 0.1): ~4-5 features show geographic clustering of shamanic traits
- **Random Distribution** (~70% of analyzed features): Most shamanic features show no geographic pattern
- **Dispersed Patterns** (I < -0.1): Rare; suggests active avoidance or ecological specialization

## Extending Coverage to All 64 Features

### Prerequisites
```python
# Required libraries
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.spatial.distance import cdist
```

### Implementation Steps

#### Step 1: Load Data
```python
import pandas as pd
from pathlib import Path

# Load cultures with coordinates
cultures_df = pd.read_parquet('data/processed/dplace_real.parquet')

# Extract feature matrix (binary: 0/1)
features_matrix = cultures_df.pivot_table(
    index='culture_id',
    columns='variable_name',
    values='variable_value',
    aggfunc='first'
).fillna(0)

# Extract coordinates
coords = cultures_df.drop_duplicates(subset=['culture_id'])[
    ['culture_id', 'lat', 'lon']
].set_index('culture_id')

# Align with features
coords = coords.loc[features_matrix.index]
```

#### Step 2: Calculate Spatial Weights
```python
def create_distance_band_weights(coords, threshold_km=500):
    """Create weight matrix for distance-band spatial weights."""
    from scipy.spatial.distance import cdist
    
    # Convert lat/lon to approximate km distances
    # (simplified Haversine approximation)
    def haversine(lat1, lon1, lat2, lon2):
        from math import radians, sin, cos, sqrt, atan2
        R = 6371  # Earth radius in km
        
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c
    
    n = len(coords)
    weights = np.zeros((n, n))
    
    for i in range(n):
        for j in range(i+1, n):
            dist = haversine(
                coords.iloc[i, 0], coords.iloc[i, 1],
                coords.iloc[j, 0], coords.iloc[j, 1]
            )
            if dist <= threshold_km:
                weights[i, j] = 1.0
                weights[j, i] = 1.0
    
    # Row-standardize weights
    row_sums = weights.sum(axis=1)
    weights = weights / row_sums[:, np.newaxis]
    
    return weights
```

#### Step 3: Calculate Moran's I
```python
def morans_i_vectorized(feature_matrix, weights):
    """
    Calculate Moran's I for all features efficiently.
    
    Returns DataFrame with results.
    """
    results = []
    
    for feature_name in feature_matrix.columns:
        x = feature_matrix[feature_name].values
        
        # Skip if no variance
        if x.std() == 0:
            continue
        
        # Demean
        x_dev = x - x.mean()
        
        # Moran's I calculation
        numerator = (x_dev @ weights @ x_dev)
        denominator = (x_dev @ x_dev)
        
        # Calculate I
        n = len(x)
        I = (n / weights.sum().sum()) * (numerator / denominator)
        
        # Expected value under null hypothesis
        E_I = -1 / (n - 1)
        
        # Variance (complex calculation - simplified version)
        b2 = (x_dev**2).sum() / (x_dev**2).mean()
        var_I = (n * ((n**2 - 3*n + 3) * weights.sum().sum()**2 - 
                     (n**2 - n) * (weights**2).sum().sum() + 3 * (weights.sum(axis=1)**2).sum()) -
                b2 * ((n**2 - 3*n + 3) * weights.sum().sum()**2 -
                      2 * (n**2 - n) * (weights**2).sum().sum() + 6 * (weights.sum(axis=1)**2).sum())) / \
               ((n-1) * (n-2) * (n-3) * (weights.sum().sum()**2))
        
        # Z-score and p-value
        z_score = (I - E_I) / np.sqrt(var_I)
        p_value = 2 * (1 - stats.norm.cdf(np.abs(z_score)))  # Two-tailed test
        
        results.append({
            'feature': feature_name,
            'statistic': I,
            'p_value': p_value,
            'z_score': z_score,
            'significant': p_value < 0.05,
            'interpretation': _interpret_morans_i(I, p_value)
        })
    
    return pd.DataFrame(results)

def _interpret_morans_i(I, p_value):
    """Generate human-readable interpretation."""
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
    return "Unclear pattern"
```

#### Step 4: Export Results
```python
# Calculate for all features
weights = create_distance_band_weights(coords, threshold_km=500)
results_df = morans_i_vectorized(features_matrix, weights)

# Export to JSON for visualization
import json
results_json = json.loads(results_df.to_json(orient='records'))

with open('data/processed/spatial_analysis_phase6/morans_i_all_features.json', 'w') as f:
    json.dump(results_json, f, indent=2)

print(f"✓ Calculated Moran's I for {len(results_df)} features")
print(f"  - Significant positive (clustered): {(results_df['I'] > 0.1).sum()}")
print(f"  - Not significant: {(results_df['p_value'] >= 0.05).sum()}")
print(f"  - Significant negative (dispersed): {(results_df['I'] < -0.1).sum()}")
```

## UI Integration

### Phase 7 Visualization Display

The `updateStatsPanel()` function in `js/featurePanel.js` displays Moran's I data:

```javascript
// When Moran's I data is available:
const moransI = DataLoader.getModransI(featureName);
if (moransI && moransI.statistic !== undefined) {
    // Display:
    // - Moran's I statistic
    // - Z-score
    // - Pattern interpretation
    // - Significance badge (★★ p<0.01 or ★ p<0.05)
    // - P-value with significance level
}
```

### Feature Mapping Update

To connect the generic `feature_0` indices to actual feature names:

```python
# Load the feature mapping
morans_csv = pd.read_csv('data/processed/spatial_analysis_phase6/morans_i_per_feature.csv')
feature_mapping = dict(zip(
    [f'feature_{i}' for i in range(len(morans_csv))],
    morans_csv['feature']
))

# Update analysis_results.json to use actual names instead of feature_N
```

## Limitations & Future Work

### Current Limitations
1. **Feature Coverage**: Only 19/64 features analyzed (29.7%)
2. **Weight Matrix**: Uses simple distance-band (500 km threshold)
   - Could be improved with inverse-distance or exponential decay
3. **Multiple Testing**: No correction for multiple comparisons (p-values may be inflated)
4. **Temporal Dimension**: Current analysis is cross-sectional; temporal patterns not captured

### Recommended Improvements
1. **Expand Coverage**: Calculate for all 64 features using vectorized implementation (~30 min computation)
2. **Multiple Testing Correction**: Apply Bonferroni or FDR correction
   - Bonferroni: p < 0.05/64 = p < 0.00078 for significance
3. **Local Indicators of Spatial Autocorrelation (LISA)**: Identify clustering hotspots
4. **Alternative Weights**: Test distance-decay weights
5. **Sensitivity Analysis**: Vary threshold from 300-1000 km to test robustness

## References

- **Moran's I (Wikipedia)**: https://en.wikipedia.org/wiki/Moran%27s_I
- **PySAL Documentation** (Python Spatial Analysis Library): https://pysal.org/
- **Anselin, L. (1995)**: "Local Indicators of Spatial Association" - Statistical Geography *27*:15-33
- **Cliff, A. D., & Ord, J. K. (1981)**: *Spatial Processes* - Pion, London

## Related Files

- **Calculation Code**: `src/analysis/spatial.py` (morans_i function)
- **Phase 6 Results**: `data/processed/spatial_analysis_phase6/morans_i_per_feature.csv`
- **Feature Mapping**: `data/processed/spatial_analysis_phase6/morans_i_per_feature.csv` (column: feature)
- **UI Implementation**: `phase7_visualization/js/featurePanel.js` (updateStatsPanel)
- **Phase 7 Data**: `phase7_visualization/data/analysis_results.json`

---

**Last Updated**: April 21, 2026  
**Author**: Phase 7 Development Team
