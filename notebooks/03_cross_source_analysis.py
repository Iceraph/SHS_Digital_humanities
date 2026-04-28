"""
Phase 3, Notebook 03: Cross-Source Analysis & Conflict Resolution

This notebook demonstrates Phase 3 analysis:
- Load harmonised data from Phase 2
- Perform cross-source comparison 
- Detect and resolve conflicts
- Generate conflict registry (conflicts.csv)
- Analyze source concordance patterns
"""

# ============================================================================
# 1. SETUP AND IMPORTS
# ============================================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

from src.analysis.comparison import (
    load_harmonised_data,
    get_feature_matrix_by_source,
    apply_linkage_to_matrices,
    find_overlapping_cultures,
    compare_feature_agreements,
    compute_agreement_statistics,
    resolve_conflicts_quality_weighted,
    create_conflict_registry,
)

sns.set_style("whitegrid")
print("✓ Phase 3 analysis modules imported")

# ============================================================================
# 2. LOAD AND VALIDATE DATA
# ============================================================================

harmonised_data = load_harmonised_data(
    dplace_path="data/processed/harmonised/dplace_harmonised.parquet",
    drh_path="data/processed/harmonised/drh_harmonised.parquet",
    seshat_path="data/processed/harmonised/seshat_harmonised.parquet",
)

print("\nData Summary:")
for source, df in harmonised_data.items():
    print(f"{source.upper()}: {len(df):,} records, "
          f"{df['culture_id'].nunique()} cultures, "
          f"{df['feature_name'].nunique()} features")
    print(f"  Quality: {df['data_quality_score'].mean():.3f} (mean)")

# ============================================================================
# 3. CROSS-SOURCE COMPARISON
# ============================================================================

# Create feature matrices
feature_matrices = get_feature_matrix_by_source(harmonised_data)

# Alias D-PLACE culture_ids to their linked DRH ids (Phase 2.5 linkage)
linkage_df = pd.read_csv("data/reference/dplace_drh_linkage.csv")
feature_matrices = apply_linkage_to_matrices(feature_matrices, linkage_df)
print(f"\n✓ Applied {len(linkage_df)} DRH↔D-PLACE linkages")

# Find overlapping cultures
all_cultures, overlapping = find_overlapping_cultures(feature_matrices)
print(f"\n✓ {len(overlapping)} cultures in multiple sources")

# Compare features across sources
agreement_df = compare_feature_agreements(
    feature_matrices,
    overlapping,
    harmonised_data,
)

print(f"✓ {len(agreement_df)} cross-source feature comparisons")

# ============================================================================
# 4. CONFLICT STATISTICS
# ============================================================================

if len(agreement_df) > 0:
    stats = compute_agreement_statistics(agreement_df)

    print("\nCross-Source Concordance:")
    print(f"  Agreements: {stats['agreements']} ({stats['agreement_rate']*100:.1f}%)")
    print(f"  Conflicts: {stats['conflicts']}")
    print(f"  Partial coverage: {stats['partial_coverage']}")

    # ============================================================================
    # 5. CONFLICT RESOLUTION
    # ============================================================================

    # Resolve conflicts using quality-weighted averaging
    resolutions_df = resolve_conflicts_quality_weighted(agreement_df)

    print(f"\n✓ {len(resolutions_df)} conflicts resolved")
else:
    print("\n⚠  No overlapping cultures found - cross-source comparison skipped")
    print("   (D-PLACE and DRH use different culture ID schemes in this dataset)")
    resolutions_df = pd.DataFrame()

# ============================================================================
# 6. SAVE CONFLICT REGISTRY
# ============================================================================

Path("data/processed/harmonised").mkdir(parents=True, exist_ok=True)

if len(agreement_df) > 0:
    create_conflict_registry(
        agreement_df,
        resolutions_df,
        output_path="data/processed/harmonised/conflicts.csv",
    )
else:
    print("\n✓ No conflicts to register (no overlapping cultures)")

print("\n✓ Phase 3 cross-source analysis complete")
print("  Output: data/processed/harmonised/conflicts.csv")
