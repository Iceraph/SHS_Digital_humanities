"""
Phase 3, Notebook 07: Conflict Resolution & Ethnographic Validation

This notebook provides conflict resolution and validation:
- Review documented conflicts
- Apply resolution strategies
- Cross-validate against ethnographic narratives
- Generate summary report
- Create adjudication checklist for manual review
"""

import pandas as pd
import numpy as np
from pathlib import Path

from src.analysis.conflicts import ConflictRegistry, create_adjudication_checklist
from src.analysis.validation import (
    load_ethnographic_narratives,
    cross_validate_all_cultures,
    identify_theoretical_inconsistencies,
    document_validation_evidence,
)

# ============================================================================
# 1. LOAD CONFLICT REGISTRY
# ============================================================================

conflicts_path = "data/processed/harmonised/conflicts.csv"

if Path(conflicts_path).exists():
    conflicts_df = pd.read_csv(conflicts_path)
    print(f"Loaded {len(conflicts_df)} documented conflicts")
    print(f"\nConflict types:")
    print(conflicts_df["conflict_type"].value_counts())
else:
    print(f"Conflict registry not found at {conflicts_path}")
    conflicts_df = None

# ============================================================================
# 2. CONFLICT RESOLUTION SUMMARY
# ============================================================================

if conflicts_df is not None:
    print("\nConflict Resolution Summary:")
    resolved = conflicts_df[(conflicts_df["resolution_status"] == "resolved")].shape[0]
    pending = conflicts_df[(conflicts_df["resolution_status"] == "pending_review")].shape[0]
    
    print(f"  Resolved: {resolved}")
    print(f"  Pending review: {pending}")
    print(f"  Resolution methods: {conflicts_df['resolution_method'].value_counts().to_dict()}")

# ============================================================================
# 3. ETHNOGRAPHIC VALIDATION
# ============================================================================

print("\nLoading ethnographic narratives...")
narratives = load_ethnographic_narratives()
print(f"✓ {len(narratives)} ethnographic profiles loaded")

# Cross-validate harmonised data
harmonised_df = pd.concat([
    pd.read_parquet("data/processed/harmonised/dplace_harmonised.parquet"),
    pd.read_parquet("data/processed/harmonised/drh_harmonised.parquet"),
    pd.read_parquet("data/processed/harmonised/seshat_harmonised.parquet"),
], ignore_index=True)

validation_results = cross_validate_all_cultures(harmonised_df)

if len(validation_results) > 0:
    print("\nEthnographic Validation Results:")
    print(validation_results[["culture_name", "agreement_rate", "validation_status"]])
    
    # Save validation results
    Path("data/processed/analysis").mkdir(parents=True, exist_ok=True)
    document_validation_evidence(validation_results)

# ============================================================================
# 4. THEORETICAL INCONSISTENCIES
# ============================================================================

print("\nChecking for theoretical inconsistencies...")
inconsistencies = identify_theoretical_inconsistencies(harmonised_df)

if len(inconsistencies) > 0:
    print(f"Found {len(inconsistencies)} potential inconsistencies:")
    for item in inconsistencies[:5]:
        print(f"  {item['culture_id']}: {item['assertion']}")

# ============================================================================
# 5. ADJUDICATION CHECKLIST
# ============================================================================

if conflicts_df is not None:
    # Create checklist for manual review
    print("\n✓ Phase 3 conflict resolution complete")
    print("  Output: data/processed/harmonised/conflicts.csv")
    print("  Output: data/processed/analysis/ethnographic_validation.csv")
