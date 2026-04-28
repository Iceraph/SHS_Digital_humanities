#!/usr/bin/env python3
"""Phase 3 — Build canonical feature matrix.

Reads the three Phase 2 harmonised parquets and produces:
    data/processed/feature_matrix.parquet   — wide-format, all cultures
    data/processed/analysis/missingness.csv — per-feature NA rates by source

Usage::

    PYTHONPATH=. python scripts/build_matrix.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from features.align import build_feature_matrix  # noqa: E402
from features.impute import complete_case_filter  # noqa: E402
from features.schema import CANONICAL_FEATURES, METADATA_COLS  # noqa: E402


HARMONISED_DIR  = PROJECT_ROOT / "data" / "processed" / "harmonised"
SOCIETIES_PATH  = PROJECT_ROOT / "data" / "raw" / "dplace" / "societies.csv"
OUTPUT_PARQUET  = PROJECT_ROOT / "data" / "processed" / "feature_matrix.parquet"
ANALYSIS_DIR    = PROJECT_ROOT / "data" / "processed" / "analysis"


def print_summary(matrix: pd.DataFrame) -> None:
    print(f"\n{'='*60}")
    print(f"Feature matrix shape: {matrix.shape}")
    print(f"  Cultures total: {len(matrix)}")
    print()

    src_counts = matrix["source"].value_counts()
    print("Cultures by source:")
    for src, n in src_counts.items():
        print(f"  {src:10s}: {n:5d}")
    print()

    feat_cols = [f for f in CANONICAL_FEATURES if f in matrix.columns]
    coverage = matrix[feat_cols].notna().mean().sort_values(ascending=False)
    print(f"Feature coverage (non-NA rate across all {len(matrix)} rows):")
    for feat, rate in coverage.items():
        bar = "#" * int(rate * 30)
        print(f"  {feat:35s} {rate:5.1%}  {bar}")
    print(f"{'='*60}\n")


def save_missingness_report(matrix: pd.DataFrame, out_dir: Path) -> None:
    feat_cols = [f for f in CANONICAL_FEATURES if f in matrix.columns]
    rows = []
    for source, grp in matrix.groupby("source"):
        for feat in feat_cols:
            n_total = len(grp)
            n_present = grp[feat].notna().sum()
            rows.append({
                "source": source,
                "feature": feat,
                "n_total": n_total,
                "n_present": int(n_present),
                "coverage_pct": round(n_present / n_total * 100, 1) if n_total else 0,
            })
    df = pd.DataFrame(rows)
    path = out_dir / "missingness.csv"
    df.to_csv(path, index=False)
    print(f"Missingness report → {path.relative_to(PROJECT_ROOT)}")


def main() -> int:
    print("=" * 60)
    print("PHASE 3 — Build Feature Matrix")
    print("=" * 60)

    # Build full matrix (all sources, all cultures, no filtering)
    print("\nBuilding feature matrix from harmonised parquets ...")
    matrix = build_feature_matrix(
        harmonised_dir=HARMONISED_DIR,
        societies_path=SOCIETIES_PATH if SOCIETIES_PATH.exists() else None,
    )

    print_summary(matrix)

    # Save full (unfiltered) matrix
    OUTPUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    matrix.to_parquet(OUTPUT_PARQUET, index=False)
    print(f"Feature matrix → {OUTPUT_PARQUET.relative_to(PROJECT_ROOT)}")

    # Missingness report
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    save_missingness_report(matrix, ANALYSIS_DIR)

    # Quick filtered stats (Phase 4 will use this filtered version)
    filtered = complete_case_filter(matrix, min_features=1)
    print(f"\nAfter complete-case filter (min 1 feature): {len(filtered)} rows")
    by_src = filtered["source"].value_counts()
    for src, n in by_src.items():
        print(f"  {src:10s}: {n:5d}")

    print("\nPhase 3 complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
