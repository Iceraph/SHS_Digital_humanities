"""
Phase 3, Notebook 04: Temporal Pattern Analysis

This notebook performs temporal analysis:
- Stratify data by historical era (Prehistoric to Modern)
- Analyze feature presence per era
- Detect temporal trends
- Generate era_analysis.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

from src.analysis.temporal import (
    stratify_by_era,
    compute_era_feature_presence,
    detect_temporal_trends,
    create_temporal_profile,
    analyze_feature_persistence,
    compute_era_statistics,
)

# ============================================================================
# 1. LOAD DATA
# ============================================================================

# Combine harmonised data
df_dplace = pd.read_parquet("data/processed/harmonised/dplace_harmonised.parquet")
df_drh = pd.read_parquet("data/processed/harmonised/drh_harmonised.parquet")
df_seshat = pd.read_parquet("data/processed/harmonised/seshat_harmonised.parquet")
harmonised_df = pd.concat([df_dplace, df_drh, df_seshat], ignore_index=True)

print(f"Loaded {len(harmonised_df):,} harmonised records")
print(f"Time range: {harmonised_df['time_start'].min()} to {harmonised_df['time_end'].max()}")

# ============================================================================
# 2. ERA STRATIFICATION
# ============================================================================

stratified = stratify_by_era(harmonised_df)

print("\nEra Stratification:")
for era, df in stratified.items():
    if len(df) > 0:
        print(f"  {era}: {len(df):,} records")

# ============================================================================
# 3. ERA FEATURE PRESENCE
# ============================================================================

era_features = compute_era_feature_presence(stratified)

print("\nFeature Presence by Era:")
print(era_features[["era", "feature_name", "record_count", "presence_rate"]].head(15))

# Save era analysis
Path("data/processed/analysis").mkdir(parents=True, exist_ok=True)
era_features.to_csv("data/processed/analysis/era_analysis.csv", index=False)

# ============================================================================
# 4. FEATURE PERSISTENCE
# ============================================================================

persistence = analyze_feature_persistence(stratified)

print("\nFeature Persistence Across Eras:")
print(persistence[["feature_name", "era_count_present", "persistence_type"]].head(10))

# ============================================================================
# 5. TEMPORAL PROFILE
# ============================================================================

profiles = create_temporal_profile(harmonised_df)

print(f"\nTemporal Profiles Created: {len(profiles)} cultures")
print(f"  Cultures spanning multiple eras: {(profiles['era_presence_count'] > 1).sum()}")

print("\n✓ Temporal analysis complete")
print("  Output: data/processed/analysis/era_analysis.csv")
