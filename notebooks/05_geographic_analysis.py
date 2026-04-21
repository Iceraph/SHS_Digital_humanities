"""
Phase 3, Notebook 05: Geographic Analysis & Coverage Assessment

This notebook performs geographic analysis:
- Validate coordinate data
- Assign geographic regions
- Calculate regional density and coverage
- Identify data gaps and biases
- Generate region_analysis.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

from src.analysis.geography import (
    validate_coordinates,
    assign_geographic_regions,
    compute_regional_density,
    identify_coverage_gaps,
    compute_geographic_bias,
    create_geographic_profile,
)

# ============================================================================
# 1. LOAD DATA
# ============================================================================

df_dplace = pd.read_parquet("data/processed/harmonised/dplace_harmonised.parquet")
df_drh = pd.read_parquet("data/processed/harmonised/drh_harmonised.parquet")

print(f"D-PLACE: {len(df_dplace):,} records")
print(f"DRH: {len(df_drh):,} records")

# ============================================================================
# 2. COORDINATE VALIDATION
# ============================================================================

print("\nCoordinate Validation:")

dplace_issues = validate_coordinates(df_dplace)
print(f"  D-PLACE: {len(dplace_issues['out_of_bounds'])} invalid coordinates")

drh_issues = validate_coordinates(df_drh)
print(f"  DRH: {len(drh_issues['out_of_bounds'])} invalid coordinates")

# ============================================================================
# 3. REGIONAL ASSIGNMENT
# ============================================================================

df_dplace = assign_geographic_regions(df_dplace)
df_drh = assign_geographic_regions(df_drh)

print("\nRegional Distribution (D-PLACE):")
print(df_dplace["region"].value_counts())

# ============================================================================
# 4. REGIONAL DENSITY
# ============================================================================

dplace_density = compute_regional_density(df_dplace)
drh_density = compute_regional_density(df_drh)

print("\nRegional Density (D-PLACE):")
for region, stats in dplace_density.items():
    print(f"  {region}: {stats['record_count']} records, "
          f"{stats['feature_presence_rate']:.1%} coverage")

# ============================================================================
# 5. COVERAGE GAPS
# ============================================================================

gaps = identify_coverage_gaps(dplace_density)

print("\nCoverage Assessment:")
print(gaps[["region", "record_count", "gap_severity"]])

# ============================================================================
# 6. GEOGRAPHIC BIAS
# ============================================================================

bias = compute_geographic_bias(dplace_density, drh_density)

print("\nSource Distribution by Region:")
print(bias[["region", "dplace_count", "drh_count", "bias_indicator"]])

# Save regional analysis
Path("data/processed/analysis").mkdir(parents=True, exist_ok=True)
gaps.to_csv("data/processed/analysis/region_analysis.csv", index=False)
bias.to_csv("data/processed/analysis/geographic_bias.csv", index=False)

print("\n✓ Geographic analysis complete")
print("  Output: data/processed/analysis/region_analysis.csv")
