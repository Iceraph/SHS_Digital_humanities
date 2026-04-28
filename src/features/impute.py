"""
Missing data strategies for the feature matrix.

Two strategies are provided, matching the decisions in PROJECT_CONTEXT.md §8:
- complete_case_filter: primary analysis — drop rows below a feature threshold.
- mean_impute: sensitivity check — replace NAs with column means.

Neither function modifies the metadata columns.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from .schema import CANONICAL_FEATURES


def complete_case_filter(
    matrix: pd.DataFrame,
    min_features: int = 1,
    features: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Drop rows that have fewer than *min_features* non-NA feature values.

    Args:
        matrix: Wide feature matrix from build_feature_matrix().
        min_features: Minimum number of non-NA features a row must have.
            Rows below this threshold are dropped.
        features: Feature columns to count.  Defaults to CANONICAL_FEATURES.

    Returns:
        Filtered DataFrame (index reset).
    """
    if features is None:
        features = [f for f in CANONICAL_FEATURES if f in matrix.columns]

    n_present = matrix[features].notna().sum(axis=1)
    mask = n_present >= min_features
    dropped = (~mask).sum()
    if dropped:
        by_source = (
            matrix.assign(_keep=mask)
            .groupby("source")["_keep"]
            .agg(kept="sum", total="count")
        )
        print(f"complete_case_filter: dropping {dropped} rows with < {min_features} non-NA features")
        print(by_source.to_string())

    return matrix[mask].reset_index(drop=True)


def mean_impute(
    matrix: pd.DataFrame,
    features: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Replace NAs in feature columns with the column mean.

    Intended for sensitivity checks only.  The imputed values are continuous
    (column mean), not binarised — downstream clustering should be aware of
    this if hard binary values are expected.

    Args:
        matrix: Wide feature matrix from build_feature_matrix().
        features: Feature columns to impute.  Defaults to CANONICAL_FEATURES.

    Returns:
        Copy of matrix with NAs filled.
    """
    if features is None:
        features = [f for f in CANONICAL_FEATURES if f in matrix.columns]

    result = matrix.copy()
    for col in features:
        col_mean = result[col].mean(skipna=True)
        if pd.isna(col_mean):
            col_mean = 0.0
        result[col] = result[col].fillna(col_mean)

    return result
