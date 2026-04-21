"""
Temporal Analysis Module

Performs temporal stratification, era-based analysis, and diachronic trend detection.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

from .config import ERAS, TIME_BINS, TIME_BIN_WIDTH, get_era_for_timepoint, get_time_bin_for_year


def stratify_by_era(
    df: pd.DataFrame,
) -> Dict[str, pd.DataFrame]:
    """
    Stratify harmonised data by historical era.
    
    Args:
        df: Harmonised DataFrame with time_start and time_end columns
        
    Returns:
        Dictionary mapping era names to subset DataFrames
    """
    stratified = {}
    
    for era_name, era_bounds in ERAS.items():
        era_start = era_bounds["start"]
        era_end = era_bounds["end"]
        
        # Filter records that overlap with era
        era_records = df[
            (df["time_end"] >= era_start) &
            (df["time_start"] <= era_end)
        ].copy()
        
        # Assign era label
        era_records["era"] = era_name
        stratified[era_name] = era_records
    
    return stratified


def compute_era_feature_presence(
    stratified_data: Dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Compute feature presence and co-occurrence patterns across eras.
    
    Args:
        stratified_data: Dictionary from stratify_by_era()
        
    Returns:
        DataFrame with columns:
        - era, feature_name, record_count, presence_rate, mean_value, sources
    """
    results = []
    
    for era_name, era_df in stratified_data.items():
        for feature in era_df["feature_name"].unique():
            feature_records = era_df[era_df["feature_name"] == feature]
            
            # Aggregate across cultures and sources
            values = feature_records["feature_value_binarised"].dropna()
            
            if len(values) == 0:
                continue
            
            results.append({
                "era": era_name,
                "feature_name": feature,
                "record_count": len(values),
                "presence_rate": values.mean(),
                "mean_value": values.mean(),
                "std_value": values.std(),
                "sources": feature_records["source"].unique().tolist(),
            })
    
    return pd.DataFrame(results)


def detect_temporal_trends(
    df: pd.DataFrame,
    feature_name: str,
) -> Dict[str, float]:
    """
    Detect temporal trends for a specific feature across time bins.
    
    Computes feature presence rate in each 500-year window.
    Flags statistically significant changes (trend or shift).
    
    Args:
        df: Harmonised DataFrame
        feature_name: Feature to analyze
        
    Returns:
        Dictionary with trend analysis results:
        - time_bins_data: List of (bin, presence_rate) tuples
        - overall_trend: "increasing", "decreasing", "stable", "unknown"
        - tempo changes: List of periods with significant shifts
    """
    feature_df = df[df["feature_name"] == feature_name].copy()
    
    if len(feature_df) == 0:
        return {"error": f"No records found for feature {feature_name}"}
    
    # Assign time bins
    feature_df["time_bin"] = feature_df["time_start"].apply(get_time_bin_for_year)
    
    # Group by bin and compute presence rate
    bin_stats = feature_df.groupby("time_bin").agg({
        "feature_value_binarised": ["mean", "count"],
    }).reset_index()
    
    bin_stats.columns = ["time_bin", "presence_rate", "record_count"]
    bin_stats = bin_stats.sort_values("time_bin")
    
    # Compute trend (linear regression)
    if len(bin_stats) >= 3:
        x = np.arange(len(bin_stats))
        y = bin_stats["presence_rate"].values
        
        # Simple linear trend
        coeffs = np.polyfit(x, y, 1)
        slope = coeffs[0]
        
        if slope > 0.05:
            trend = "increasing"
        elif slope < -0.05:
            trend = "decreasing"
        else:
            trend = "stable"
    else:
        trend = "unknown"
    
    return {
        "feature": feature_name,
        "time_bins_data": bin_stats.to_dict("records"),
        "overall_trend": trend,
        "record_count": len(feature_df),
        "era_coverage": feature_df["era"].unique().tolist() if "era" in feature_df.columns else [],
    }


def create_temporal_profile(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create temporal profile for all cultures and features.
    
    Args:
        df: Harmonised DataFrame
        
    Returns:
        DataFrame with temporal metadata per culture:
        - culture_id, era_presence, time_coverage_percent, max_temporal_gap,
          temporal_mode, time_uncertainty_mean
    """
    profiles = []
    
    for culture_id in df["culture_id"].unique():
        culture_records = df[df["culture_id"] == culture_id]
        
        # Temporal coverage
        if "era" in culture_records.columns:
            era_presence = culture_records["era"].unique().tolist()
        else:
            era_presence = []
        
        # Time span
        time_start_range = culture_records["time_start"].min()
        time_end_range = culture_records["time_end"].max()
        time_span = time_end_range - time_start_range if pd.notna(time_end_range) else 0
        
        # Temporal uncertainty average
        temporal_uncertainty_mean = culture_records["time_uncertainty"].mean()
        
        # Temporal mode (most common)
        temporal_modes = culture_records["temporal_mode"].value_counts()
        temporal_mode = temporal_modes.index[0] if len(temporal_modes) > 0 else "unknown"
        
        profiles.append({
            "culture_id": culture_id,
            "culture_name": culture_records["culture_name"].iloc[0],
            "era_presence_count": len(era_presence),
            "era_presence": era_presence,
            "time_span": time_span,
            "time_uncertainty_mean": temporal_uncertainty_mean,
            "temporal_mode": temporal_mode,
            "record_count": len(culture_records),
        })
    
    return pd.DataFrame(profiles)


def analyze_feature_persistence(
    stratified_data: Dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Analyze which features persist across multiple eras.
    
    Args:
        stratified_data: Dictionary from stratify_by_era()
        
    Returns:
        DataFrame with:
        - feature_name, era_count_present, eras_present, persistence_type
    """
    feature_eras = {}
    
    for era_name, era_df in stratified_data.items():
        for feature in era_df["feature_name"].unique():
            feature_records = era_df[era_df["feature_name"] == feature]
            
            # Only count if feature is actually present
            if feature_records["feature_value_binarised"].mean() > 0.5:
                if feature not in feature_eras:
                    feature_eras[feature] = []
                feature_eras[feature].append(era_name)
    
    results = []
    for feature, eras in feature_eras.items():
        eras_sorted = sorted(eras)
        
        # Classify persistence
        if len(eras) >= 5:
            persistence = "highly_persistent"
        elif len(eras) >= 3:
            persistence = "moderately_persistent"
        elif len(eras) >= 2:
            persistence = "episodic"
        else:
            persistence = "rare"
        
        results.append({
            "feature_name": feature,
            "era_count_present": len(eras),
            "eras_present": eras_sorted,
            "persistence_type": persistence,
        })
    
    return pd.DataFrame(results).sort_values("era_count_present", ascending=False)


def compute_era_statistics(
    stratified_data: Dict[str, pd.DataFrame],
) -> Dict[str, Dict]:
    """
    Compute summary statistics per era.
    
    Args:
        stratified_data: Dictionary from stratify_by_era()
        
    Returns:
        Dictionary with era statistics
    """
    stats = {}
    
    for era_name, era_df in stratified_data.items():
        if len(era_df) == 0:
            continue
        
        stats[era_name] = {
            "record_count": len(era_df),
            "culture_count": era_df["culture_id"].nunique(),
            "feature_count": era_df["feature_name"].nunique(),
            "source_distribution": era_df["source"].value_counts().to_dict(),
            "mean_data_quality": era_df["data_quality_score"].mean(),
            "geographic_coverage": {
                "regions": era_df.groupby("latitude", "longitude").size().shape[0],
            },
            "features_present": (era_df["feature_value_binarised"] == 1).sum(),
            "features_absent": (era_df["feature_value_binarised"] == 0).sum(),
            "features_unknown": era_df["feature_value_binarised"].isna().sum(),
        }
    
    return stats
