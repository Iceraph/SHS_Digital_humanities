"""
Cross-source feature alignment for Phase 3.

Transforms the three long-format harmonised parquets produced by Phase 2 into
a single wide-format feature matrix suitable for clustering (Phase 4).

Design decisions (documented in PROJECT_CONTEXT.md §8):
- Any-source presence rule: within a source, if any record for a culture reports
  feature = 1, the feature is coded 1 for that culture.
- Units of observation are kept separate: D-PLACE societies, DRH traditions,
  and Seshat polities each occupy their own rows.  There is no cross-source
  merging of culture identities (linkage tables are used only for conflict
  analysis in src/analysis/comparison.py, not here).
- language_family is attached to D-PLACE rows from data/raw/dplace/societies.csv
  (Glottocode prefix used as a proxy for top-level family).  DRH and Seshat
  rows each get a unique synthetic language_family so the phylogenetic filter
  treats them as independent observations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np

from .schema import CANONICAL_FEATURES, METADATA_COLS


def _pivot_source(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """Pivot long-format harmonised DataFrame to wide (one row per culture).

    Applies the any-source rule within the source: for each (culture_id,
    feature_name) pair, takes the maximum binarised value across all records
    (i.e. 1 if any record reports presence).
    """
    df = df.dropna(subset=["feature_name"]).copy()
    if df.empty:
        return pd.DataFrame(columns=METADATA_COLS + CANONICAL_FEATURES)

    # Wide pivot: max = any-source rule within this source's records
    wide = (
        df.groupby(["culture_id", "feature_name"])["feature_value_binarised"]
        .max()
        .reset_index()
        .pivot(index="culture_id", columns="feature_name", values="feature_value_binarised")
        .reset_index()
    )
    wide.columns.name = None

    # Attach metadata (first value per culture is sufficient — all records for
    # the same culture share the same metadata in the harmonised schema).
    meta_fields = [
        "culture_name", "source", "unit_type", "temporal_mode",
        "lat", "lon", "time_start", "time_end",
    ]
    meta = (
        df.groupby("culture_id")[meta_fields]
        .first()
        .reset_index()
    )
    wide = wide.merge(meta, on="culture_id", how="left")

    # Ensure source column has the canonical name (harmonised data already has
    # this, but be explicit in case of stale parquets).
    wide["source"] = source_name

    return wide


def _attach_language_families(dplace_wide: pd.DataFrame, societies_path: Path) -> pd.DataFrame:
    """Add language_family and glottocode columns to the D-PLACE wide matrix."""
    if not societies_path.exists():
        dplace_wide["language_family"] = "unknown"
        dplace_wide["glottocode"] = pd.NA
        return dplace_wide

    societies = pd.read_csv(societies_path, usecols=["ID", "Glottocode"])
    societies = societies.rename(columns={"ID": "culture_id", "Glottocode": "glottocode"})

    # Use the first four characters of the Glottocode as the top-level family
    # proxy (Glottolog family codes follow a 4-char + 4-digit pattern).
    # This replicates the logic in scripts/phase4_clustering_multisource.py.
    societies["language_family"] = (
        societies["glottocode"].fillna("unknown").str.split("-").str[0]
    )

    # culture_id in harmonised D-PLACE is an integer stored as int/str; coerce
    # both sides to str before merging to avoid type mismatches.
    dplace_wide["culture_id"] = dplace_wide["culture_id"].astype(str)
    societies["culture_id"] = societies["culture_id"].astype(str)

    dplace_wide = dplace_wide.merge(
        societies[["culture_id", "glottocode", "language_family"]],
        on="culture_id",
        how="left",
    )
    dplace_wide["language_family"] = dplace_wide["language_family"].fillna("unknown")
    return dplace_wide


def build_feature_matrix(
    harmonised_dir: str | Path,
    societies_path: Optional[str | Path] = None,
) -> pd.DataFrame:
    """Build the canonical wide-format feature matrix from Phase 2 outputs.

    Loads all three harmonised parquets, pivots each to wide format, attaches
    language-family metadata to D-PLACE rows, assigns synthetic unique
    language_family values to DRH/Seshat rows (so the phylogenetic filter
    treats them as independent), and concatenates all sources.

    Args:
        harmonised_dir: Directory containing ``*_harmonised.parquet`` files.
        societies_path: Path to ``data/raw/dplace/societies.csv``.  Required
            for real Glottocode-based language families; falls back to
            "unknown" if omitted or missing.

    Returns:
        DataFrame with columns METADATA_COLS + CANONICAL_FEATURES.
        One row per culture/polity/tradition.  Feature values are 0.0, 1.0,
        or NaN (never imputed here — see impute.py).
    """
    harmonised_dir = Path(harmonised_dir)

    # --- Load and pivot each source ---
    dplace_long = pd.read_parquet(harmonised_dir / "dplace_harmonised.parquet")
    drh_long    = pd.read_parquet(harmonised_dir / "drh_harmonised.parquet")
    seshat_long = pd.read_parquet(harmonised_dir / "seshat_harmonised.parquet")

    dplace = _pivot_source(dplace_long, "dplace")
    drh    = _pivot_source(drh_long,    "drh")
    seshat = _pivot_source(seshat_long, "seshat")

    # --- Language families ---
    if societies_path is not None:
        dplace = _attach_language_families(dplace, Path(societies_path))
    else:
        dplace["language_family"] = "unknown"
        dplace["glottocode"] = pd.NA

    # DRH and Seshat: each row is a unique observation unit — no phylogenetic
    # pseudoreplication within these sources, so give each a unique tag so the
    # one-per-family filter keeps them all.
    drh["language_family"]    = "drh:"    + drh["culture_id"].astype(str)
    drh["glottocode"]         = pd.NA
    seshat["language_family"] = "seshat:" + seshat["culture_id"].astype(str)
    seshat["glottocode"]      = pd.NA

    # --- Stack ---
    combined = pd.concat([dplace, drh, seshat], ignore_index=True, sort=False)

    # --- Enforce canonical column order ---
    # Keep only features that actually exist in the combined matrix (some may
    # have been dropped if a source had zero non-null values).
    feature_cols = [f for f in CANONICAL_FEATURES if f in combined.columns]
    missing_features = [f for f in CANONICAL_FEATURES if f not in combined.columns]
    for f in missing_features:
        combined[f] = np.nan

    output_cols = METADATA_COLS + CANONICAL_FEATURES
    # Add any metadata columns that are present but not yet in METADATA_COLS
    extra_meta = [c for c in combined.columns if c not in output_cols]
    combined = combined.reindex(columns=output_cols)

    # Ensure culture_id is always str (D-PLACE uses int IDs, DRH uses str)
    combined["culture_id"] = combined["culture_id"].astype(str)

    # Cast feature columns to float (parquet-friendly, NaN-compatible)
    for col in CANONICAL_FEATURES:
        combined[col] = pd.to_numeric(combined[col], errors="coerce")

    return combined
