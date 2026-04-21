"""
Phase 3, Notebook 06: Feature Synthesis & Composite Indicators

This notebook creates synthesised features:
- Aggregate features by culture
- Create composite indicators
- Analyze feature co-occurrence patterns
- Generate composite_indicators.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

from src.analysis.synthesis import (
    create_composite_indicators,
    aggregate_features_by_culture,
    synthesize_feature_profiles,
    compute_feature_correlation_matrix,
    create_indicator_distribution_summary,
)

# ============================================================================
# 1. LOAD DATA
# ============================================================================

df_dplace = pd.read_parquet("data/processed/harmonised/dplace_harmonised.parquet")
df_drh = pd.read_parquet("data/processed/harmonised/drh_harmonised.parquet")
harmonised_df = pd.concat([df_dplace, df_drh], ignore_index=True)

print(f"Loaded {len(harmonised_df):,} records from {harmonised_df['culture_id'].nunique()} cultures")

# ============================================================================
# 2. FEATURE AGGREGATION
# ============================================================================

aggregated = aggregate_features_by_culture(harmonised_df)

print(f"\n✓ Aggregated features for {len(aggregated)} cultures")
print(f"  Feature columns: {len([c for c in aggregated.columns if c not in ['culture_id', 'culture_name', 'source', 'lat', 'lon', 'region']])}")

# ============================================================================
# 3. COMPOSITE INDICATORS
# ============================================================================

print("\nCreating composite indicators...")

composites = create_composite_indicators(harmonised_df)

# Get only composite columns
composite_cols = [c for c in composites.columns if c.startswith("composite_")]
print(f"✓ {len(composite_cols)} composite indicators created:")
for col in composite_cols:
    indicator_name = col.replace("composite_", "")
    presence_rate = (composites[col] == 1).sum() / composites[col].notna().sum()
    print(f"  - {indicator_name}: {presence_rate:.1%} presence")

# ============================================================================
# 4. FEATURE PROFILES
# ============================================================================

profiles = synthesize_feature_profiles(aggregated)

print("\nIdentified Culture Profiles:")
for profile_name, profile_data in profiles.items():
    print(f"  {profile_name}: {profile_data['culture_count']} cultures")

# ============================================================================
# 5. FEATURE CORRELATION
# ============================================================================

correlation = compute_feature_correlation_matrix(aggregated)

print(f"\nFeature Correlation Matrix: {correlation.shape}")

# ============================================================================
# 6. INDICATOR SUMMARY
# ============================================================================

indicator_summary = create_indicator_distribution_summary(composites)

print("\nComposite Indicator Distributions:")
print(indicator_summary[["indicator", "presence_rate", "mean_value"]])

# ============================================================================
# 7. SAVE OUTPUTS
# ============================================================================

Path("data/processed/analysis").mkdir(parents=True, exist_ok=True)

indicator_summary.to_csv("data/processed/analysis/composite_indicators.csv", index=False)
correlation.to_csv("data/processed/analysis/feature_correlation.csv")

print("\n✓ Feature synthesis complete")
print("  Output: data/processed/analysis/composite_indicators.csv")
