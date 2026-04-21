#!/usr/bin/env python
"""
Generate Conflicts Registry (Issue #4 Fix)

Standalone script to detect, resolve, and log all cross-source conflicts.
Run this after Phase 2 harmonisation to generate conflicts.csv.

Usage:
    python scripts/generate_conflicts.py
    
Output:
    data/processed/harmonised/conflicts.csv (cross-source comparison)
"""

import sys
from pathlib import Path

# Add workspace to path
workspace_root = Path(__file__).parent.parent
sys.path.insert(0, str(workspace_root))

from src.analysis.conflicts import generate_conflicts_registry


def main():
    """Generate conflicts registry."""
    print("=" * 70)
    print("GENERATING CONFLICTS REGISTRY (Issue #4 Fix)")
    print("=" * 70)
    print()
    
    # Generate conflicts
    agreement_df, registry = generate_conflicts_registry(
        dplace_path="data/processed/harmonised/dplace_harmonised.parquet",
        drh_path="data/processed/harmonised/drh_harmonised.parquet",
        seshat_path="data/processed/harmonised/seshat_harmonised.parquet",
        output_path="data/processed/harmonised/conflicts.csv",
        strategy="quality_weighted",
    )
    
    print()
    print("=" * 70)
    print(f"✓ Conflicts registry generation complete")
    print(f"  Output: data/processed/harmonised/conflicts.csv")
    print("=" * 70)


if __name__ == "__main__":
    main()
