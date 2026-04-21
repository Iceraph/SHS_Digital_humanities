"""
Phase 2: Data Harmonisation
Transforms three independent raw datasets (D-PLACE, DRH, Seshat) into a unified,
structurally comparable set of DataFrames with resolved cross-database conflicts
and transparent harmonisation decisions.

Key outputs:
  - dplace_harmonised.parquet
  - drh_harmonised.parquet
  - seshat_harmonised.parquet
  - data/reference/crosswalk.csv
  - data/processed/harmonised/scale_decisions.csv
  - data/processed/harmonised/coverage_audit.csv
  - data/processed/harmonised/conflicts.csv

Methodological decisions (locked in PROJECT_CONTEXT.md Section 8):
  1. Unit of observation: Keep all (society/tradition/polity)
  2. Crosswalk validation: Any-source presence; log conflicts
  3. D-PLACE temporal: -1800 to -1950 (high uncertainty)
  4. Scale harmonisation: Theory-driven binarisation
  5. Galton's problem: One-per-language-family (primary)
  6. Regions: Natural Earth (reproducible)
  7. Time bins: 500-year windows
  8. Gap threshold: <5 records per region/time_bin
  9. Data quality score: f(unit_ambiguous, time_uncertainty, source_count)

Author: Phase 2 Implementation
Date: 15 avril 2026
"""

from .config import (
    HARMONISED_SCHEMA,
    METHODOLOGICAL_DECISIONS,
    DPLACE_TEMPORAL_ASSUMPTION,
    GALTON_STRATEGY,
)

__all__ = [
    "HARMONISED_SCHEMA",
    "METHODOLOGICAL_DECISIONS",
    "DPLACE_TEMPORAL_ASSUMPTION",
    "GALTON_STRATEGY",
]
