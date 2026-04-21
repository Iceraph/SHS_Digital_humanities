"""
Cross-Source Comparison Module

Analyzes agreements and conflicts across D-PLACE, DRH, and Seshat data.
Implements conflict detection, agreement tracking, and resolution strategies.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

from .config import (
    QUALITY_WEIGHTS,
    DEFAULT_CONFLICT_STRATEGY,
    AGREEMENT_THRESHOLDS,
    ConflictRecord,
)


def load_harmonised_data(
    dplace_path: str,
    drh_path: str,
    seshat_path: Optional[str] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Load all harmonised data sources.
    
    Args:
        dplace_path: Path to D-PLACE harmonised parquet
        drh_path: Path to DRH harmonised parquet
        seshat_path: Optional path to Seshat harmonised parquet
        
    Returns:
        Dictionary with keys "dplace", "drh", "seshat" (if available)
    """
    data = {
        "dplace": pd.read_parquet(dplace_path),
        "drh": pd.read_parquet(drh_path),
    }
    
    if seshat_path:
        try:
            data["seshat"] = pd.read_parquet(seshat_path)
        except FileNotFoundError:
            pass
    
    return data


def get_feature_matrix_by_source(
    harmonised_data: Dict[str, pd.DataFrame]
) -> Dict[str, pd.DataFrame]:
    """
    Pivot each harmonised dataset into feature matrix (cultures × features).
    
    Args:
        harmonised_data: Dictionary from load_harmonised_data()
        
    Returns:
        Dictionary with source names as keys, feature matrices as values
    """
    matrices = {}
    
    for source, df in harmonised_data.items():
        # Group by culture_id and pivot features
        feature_matrix = df.pivot_table(
            index="culture_id",
            columns="feature_name",
            values="feature_value_binarised",
            aggfunc="first",
        )
        
        # Add metadata columns
        metadata_cols = ["culture_name", "lat", "lon", "time_start", "time_end", "source"]
        for col in metadata_cols:
            if col in df.columns:
                feature_matrix[col] = df.groupby("culture_id")[col].first()
        
        matrices[source] = feature_matrix
    
    return matrices


def find_overlapping_cultures(
    feature_matrices: Dict[str, pd.DataFrame]
) -> Tuple[List[str], Dict[str, List[str]]]:
    """
    Identify cultures present in multiple sources.
    
    Args:
        feature_matrices: Dictionary from get_feature_matrix_by_source()
        
    Returns:
        Tuple of:
        - List of all unique culture IDs
        - Dictionary mapping culture_id → list of sources it appears in
    """
    culture_sources = defaultdict(list)
    
    for source, matrix in feature_matrices.items():
        for culture_id in matrix.index:
            culture_sources[culture_id].append(source)
    
    all_cultures = list(culture_sources.keys())
    
    # Filter to cultures in multiple sources only
    overlapping = {
        cid: sources for cid, sources in culture_sources.items()
        if len(sources) > 1
    }
    
    return all_cultures, overlapping


def compare_feature_agreements(
    feature_matrices: Dict[str, pd.DataFrame],
    overlapping_cultures: Dict[str, List[str]],
    harmonised_data: Dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Compute feature-by-feature agreements across sources for overlapping cultures.
    
    Args:
        feature_matrices: Dictionary from get_feature_matrix_by_source()
        overlapping_cultures: Dictionary from find_overlapping_cultures()
        harmonised_data: Original harmonised data for quality scores
        
    Returns:
        DataFrame with columns:
        - culture_id, feature_name, source1, value1, quality1, source2, value2, quality2,
          agreement (0/1), agreement_strength (0-1), conflict_type
    """
    comparisons = []
    
    for culture_id, sources in overlapping_cultures.items():
        # Get all features available for this culture
        features_per_source = {}
        for source in sources:
            matrix = feature_matrices[source]
            if culture_id in matrix.index:
                row = matrix.loc[culture_id]
                features_per_source[source] = row[~row.isna()].index.tolist()
        
        # Find common features
        all_features = set()
        for features in features_per_source.values():
            all_features.update(features)
        
        # Compare each pair of sources
        source_list = sorted(sources)
        for i, source1 in enumerate(source_list):
            for source2 in source_list[i+1:]:
                for feature in all_features:
                    # Get values from both sources
                    val1 = np.nan
                    val2 = np.nan
                    
                    if culture_id in feature_matrices[source1].index:
                        val1 = feature_matrices[source1].loc[culture_id, feature]
                    
                    if culture_id in feature_matrices[source2].index:
                        val2 = feature_matrices[source2].loc[culture_id, feature]
                    
                    # Skip if both are null
                    if pd.isna(val1) and pd.isna(val2):
                        continue
                    
                    # Get quality scores
                    quality1 = _get_quality_score(
                        harmonised_data[source1],
                        culture_id,
                        feature,
                    )
                    quality2 = _get_quality_score(
                        harmonised_data[source2],
                        culture_id,
                        feature,
                    )
                    
                    # Determine agreement
                    if pd.isna(val1) or pd.isna(val2):
                        agreement = 0  # One source missing
                        agreement_strength = 0.5 if not (pd.isna(val1) and pd.isna(val2)) else 0
                    else:
                        agreement = int(val1 == val2)
                        agreement_strength = 1.0 if agreement else 0.0
                    
                    # Classify conflict type
                    if pd.isna(val1) or pd.isna(val2):
                        conflict_type = "partial_coverage"
                    elif agreement:
                        conflict_type = "agreement"
                    else:
                        conflict_type = "conflict"
                    
                    comparisons.append({
                        "culture_id": culture_id,
                        "culture_name": feature_matrices[source1].loc[culture_id, "culture_name"]
                        if "culture_name" in feature_matrices[source1].columns else culture_id,
                        "feature_name": feature,
                        "source1": source1,
                        "value1": val1,
                        "quality1": quality1,
                        "source2": source2,
                        "value2": val2,
                        "quality2": quality2,
                        "agreement": agreement,
                        "agreement_strength": agreement_strength,
                        "conflict_type": conflict_type,
                    })
    
    return pd.DataFrame(comparisons)


def compute_conflict_summary(
    agreement_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute summary statistics of conflicts and agreements.
    
    Args:
        agreement_df: DataFrame from compare_feature_agreements()
        
    Returns:
        Summary DataFrame with:
        - feature_name, agreement_count, conflict_count, partial_coverage_count,
          agreement_rate, total_comparisons
    """
    summary = agreement_df.groupby("feature_name").agg({
        "agreement": ["sum", "count"],
        "conflict_type": lambda x: (x == "conflict").sum(),
    }).reset_index()
    
    summary.columns = ["feature_name", "agreement_count", "total_comparisons", "conflict_count"]
    
    summary["agreement_rate"] = summary["agreement_count"] / summary["total_comparisons"]
    summary["conflict_rate"] = summary["conflict_count"] / summary["total_comparisons"]
    
    return summary.sort_values("conflict_count", ascending=False)


def resolve_conflicts_quality_weighted(
    agreement_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Resolve conflicts using quality-weighted averaging (RECOMMENDED).
    
    When sources disagree on a feature, weighted average by data_quality_score.
    
    Args:
        agreement_df: DataFrame from compare_feature_agreements()
        
    Returns:
        DataFrame with columns:
        - culture_id, feature_name, source1, value1, source2, value2,
          resolved_value, weighted_confidence, resolution_method
    """
    resolutions = []
    
    for _, row in agreement_df[agreement_df["conflict_type"] != "agreement"].iterrows():
        val1 = row["value1"]
        val2 = row["value2"]
        quality1 = row["quality1"]
        quality2 = row["quality2"]
        
        # Skip partial coverage for now
        if pd.isna(val1) or pd.isna(val2):
            continue
        
        # Weighted combination
        total_quality = quality1 + quality2
        if total_quality > 0:
            resolved_value = (val1 * quality1 + val2 * quality2) / total_quality
        else:
            resolved_value = np.nan
        
        weighted_confidence = total_quality / 2.0  # Average confidence
        
        resolutions.append({
            "culture_id": row["culture_id"],
            "feature_name": row["feature_name"],
            "source1": row["source1"],
            "value1": val1,
            "source2": row["source2"],
            "value2": val2,
            "resolved_value": resolved_value,
            "weighted_confidence": weighted_confidence,
            "resolution_method": "quality_weighted",
        })
    
    return pd.DataFrame(resolutions)


def _get_quality_score(
    df: pd.DataFrame,
    culture_id: str,
    feature_name: str,
) -> float:
    """
    Get data quality score for a feature in a culture.
    
    Args:
        df: Harmonised DataFrame
        culture_id: Culture identifier
        feature_name: Feature name
        
    Returns:
        Quality score (0-1) or NaN if not found
    """
    subset = df[
        (df["culture_id"] == culture_id) &
        (df["feature_name"] == feature_name)
    ]
    
    if len(subset) == 0:
        return np.nan
    
    return subset["data_quality_score"].iloc[0]


def create_conflict_registry(
    agreement_df: pd.DataFrame,
    resolutions_df: pd.DataFrame,
    output_path: str,
) -> None:
    """
    Create a comprehensive conflict registry for manual review.
    
    Args:
        agreement_df: DataFrame from compare_feature_agreements()
        resolutions_df: DataFrame from resolve_conflicts_quality_weighted()
        output_path: Path to save conflicts.csv
    """
    conflicts = agreement_df[agreement_df["conflict_type"] == "conflict"].copy()
    
    # Add resolution info
    for _, resolution in resolutions_df.iterrows():
        mask = (
            (conflicts["culture_id"] == resolution["culture_id"]) &
            (conflicts["feature_name"] == resolution["feature_name"])
        )
        conflicts.loc[mask, "resolved_value"] = resolution["resolved_value"]
        conflicts.loc[mask, "resolution_method"] = resolution["resolution_method"]
    
    # Reorder columns
    output_cols = [
        "culture_id",
        "culture_name",
        "feature_name",
        "source1",
        "value1",
        "quality1",
        "source2",
        "value2",
        "quality2",
        "resolved_value",
        "conflict_type",
    ]
    
    conflicts = conflicts[output_cols]
    
    conflicts.to_csv(output_path, index=False)
    print(f"✓ Conflict registry saved to {output_path}")
    print(f"  Total conflicts documented: {len(conflicts)}")


def compute_agreement_statistics(
    agreement_df: pd.DataFrame,
) -> Dict[str, float]:
    """
    Compute overall agreement statistics across all sources.
    
    Args:
        agreement_df: DataFrame from compare_feature_agreements()
        
    Returns:
        Dictionary with agreement statistics
    """
    stats = {
        "total_comparisons": len(agreement_df),
        "agreements": (agreement_df["agreement"] == 1).sum(),
        "conflicts": (agreement_df["conflict_type"] == "conflict").sum(),
        "partial_coverage": (agreement_df["conflict_type"] == "partial_coverage").sum(),
        "agreement_rate": (agreement_df["agreement"] == 1).sum() / len(agreement_df)
        if len(agreement_df) > 0 else 0,
    }
    
    return stats
