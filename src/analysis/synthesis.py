"""
Feature Synthesis Module

Creates composite indicators, aggregates features, and synthesizes higher-level constructs.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional

from .config import COMPOSITE_INDICATORS


def create_composite_indicators(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create composite indicators by aggregating base features.
    
    Uses the definitions from config.COMPOSITE_INDICATORS.
    
    Args:
        df: Harmonised DataFrame
        
    Returns:
        DataFrame with composite indicator columns
    """
    result = df.copy()
    
    for indicator_name, definition in COMPOSITE_INDICATORS.items():
        result[f"composite_{indicator_name}"] = _compute_composite(
            df,
            indicator_name,
            definition,
        )
    
    return result


def _compute_composite(
    df: pd.DataFrame,
    indicator_name: str,
    definition: Dict,
) -> pd.Series:
    """
    Compute a single composite indicator.
    
    Args:
        df: DataFrame with feature columns
        indicator_name: Name of composite indicator
        definition: Definition dict from COMPOSITE_INDICATORS
        
    Returns:
        Series with composite values
    """
    logic = definition["logic"]
    components = definition["components"]
    
    # Extract component values
    component_cols = []
    for component in components:
        # Look for feature column matching component
        for col in df.columns:
            if component in col and "composite" not in col:
                component_cols.append(col)
                break
    
    if not component_cols:
        return pd.Series(np.nan, index=df.index)
    
    # Extract values
    component_values = df[component_cols].fillna(0)
    
    # Apply logic
    if indicator_name == "shamanic_complex":
        # FIXED: Changed from AND (too restrictive) to presence of ANY 2+ shamanic features
        # Original: (trance OR possession) AND (specialist OR initiation) → 0 cultures
        # New: Any 2+ of these features indicates shamanic complex
        num_features = (component_values == 1).sum(axis=1)
        return (num_features >= 2).astype(float)
    
    elif indicator_name == "ritual_specialisation":
        # FIXED: Changed from AND to OR for inclusivity
        # specialist >= 2 (full-time) OR hereditary transmission
        specialist_fulltime = component_values.iloc[:, 0] >= 2
        hereditary = component_values.iloc[:, 1] == 1
        return (specialist_fulltime | hereditary).astype(float)
    
    elif indicator_name == "cosmological_framework":
        # FIXED: Changed from ALL to ANY 2+ cosmological features
        # Original: ALL components present (layered cosmology AND animal transform AND nature spirits)
        # New: Any 2+ components indicate strong cosmological framework
        num_features = (component_values == 1).sum(axis=1)
        return (num_features >= 2).astype(float)
    
    elif indicator_name == "healing_technology":
        # FIXED: Changed from AND to OR (healing OR percussion, not both required)
        # Either healing function OR rhythmic percussion indicates healing technology
        return (component_values == 1).any(axis=1).astype(float)
    
    else:
        return pd.Series(np.nan, index=df.index)


def aggregate_features_by_culture(
    df: pd.DataFrame,
    features: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Aggregate feature values per culture across all records and sources.
    
    Uses quality-weighted averaging for values from multiple sources.
    
    Args:
        df: Harmonised DataFrame
        features: Optional list of features to aggregate; None = all
        
    Returns:
        DataFrame with one row per culture
    """
    if features is None:
        features = df[~df["feature_name"].str.contains("composite")]["feature_name"].unique()
    
    aggregated = []
    
    for culture_id in df["culture_id"].unique():
        culture_df = df[df["culture_id"] == culture_id]
        
        row = {
            "culture_id": culture_id,
            "culture_name": culture_df["culture_name"].iloc[0],
            "source": culture_df["source"].iloc[0],
            "lat": culture_df["lat"].iloc[0],
            "lon": culture_df["lon"].iloc[0],
            "region": culture_df.get("region", ["Unknown"])[0] if "region" in culture_df.columns else "Unknown",
        }
        
        # Aggregate features
        for feature in features:
            feature_records = culture_df[culture_df["feature_name"] == feature]
            
            if len(feature_records) == 0:
                row[feature] = np.nan
                row[f"{feature}_uncertainty"] = np.nan
                continue
            
            # Quality-weighted average
            values = feature_records["feature_value_binarised"].values
            qualities = feature_records["data_quality_score"].values
            
            valid_idx = ~pd.isna(values)
            if valid_idx.sum() == 0:
                row[feature] = np.nan
                row[f"{feature}_uncertainty"] = np.nan
            else:
                values_valid = values[valid_idx]
                qualities_valid = qualities[valid_idx]
                
                total_quality = qualities_valid.sum()
                if total_quality > 0:
                    weighted_value = np.average(values_valid, weights=qualities_valid)
                else:
                    weighted_value = np.mean(values_valid)
                
                # Binarize with threshold
                row[feature] = 1.0 if weighted_value >= 0.5 else 0.0
                
                # Uncertainty: count of different values
                row[f"{feature}_uncertainty"] = len(set(values_valid[values_valid >= 0]))
        
        aggregated.append(row)
    
    return pd.DataFrame(aggregated)


def synthesize_feature_profiles(
    df: pd.DataFrame,
) -> Dict[str, any]:
    """
    Create typological 'profiles' of cultures based on feature co-occurrence.
    
    Identifies commonly co-occurring feature sets.
    
    Args:
        df: DataFrame with aggregated features per culture
        
    Returns:
        Dictionary with profile definitions and culture assignments
    """
    # Extract feature columns (not metadata)
    feature_cols = [col for col in df.columns if col not in 
                   ["culture_id", "culture_name", "source", "lat", "lon", "region"]
                   and isinstance(col, str)]  # Filter out NaN column names
    
    feature_matrix = df[feature_cols].fillna(0)
    
    # Find dominant patterns using simple co-occurrence
    profiles = {}
    
    # Profile 1: Classic shamanism (all major features present)
    classic_features = [col for col in feature_cols if any(
        keyword in col.lower() 
        for keyword in ["trance", "spirit", "specialist", "healing"]
    )]
    
    if classic_features:
        classic_mask = (feature_matrix[classic_features] == 1).all(axis=1)
        profiles["classic_shamanism"] = {
            "description": "All core shamanic features present",
            "defining_features": classic_features,
            "culture_count": classic_mask.sum(),
            "cultures": df[classic_mask]["culture_id"].tolist(),
        }
    
    # Profile 2: Healing-focused (healing + percussion)
    healing_features = [col for col in feature_cols if "healing" in col.lower()]
    percussion_features = [col for col in feature_cols if "percussion" in col.lower()]
    
    if healing_features and percussion_features:
        healing_mask = (
            (feature_matrix[healing_features] == 1).any(axis=1) &
            (feature_matrix[percussion_features] == 1).any(axis=1)
        )
        profiles["healing_focused"] = {
            "description": "Healing and percussion-based practice",
            "defining_features": healing_features + percussion_features,
            "culture_count": healing_mask.sum(),
            "cultures": df[healing_mask]["culture_id"].tolist(),
        }
    
    # Profile 3: Cosmological (layered worlds + spirits)
    cosmology_features = [col for col in feature_cols if any(
        keyword in col.lower()
        for keyword in ["cosmology", "layered", "transformation", "spirits"]
    )]
    
    if cosmology_features:
        cosmos_mask = (feature_matrix[cosmology_features] == 1).mean(axis=1) >= 0.5
        profiles["cosmologically_focused"] = {
            "description": "Emphasis on cosmological framework",
            "defining_features": cosmology_features,
            "culture_count": cosmos_mask.sum(),
            "cultures": df[cosmos_mask]["culture_id"].tolist(),
        }
    
    return profiles


def compute_feature_correlation_matrix(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute co-occurrence correlation between features.
    
    Args:
        df: DataFrame with aggregated features per culture
        
    Returns:
        Correlation matrix
    """
    feature_cols = [col for col in df.columns if col not in 
                   ["culture_id", "culture_name", "source", "lat", "lon", "region"]]
    
    return df[feature_cols].corr()


def propagate_uncertainty(
    component_uncertainties: List[float],
    aggregation_method: str = "additive",
) -> float:
    """
    Propagate uncertainty from components to composite indicators.
    
    Args:
        component_uncertainties: List of uncertainty values for components
        aggregation_method: "additive" or "quadratic"
        
    Returns:
        Composite uncertainty
    """
    component_uncertainties = [u for u in component_uncertainties if u is not None]
    
    if not component_uncertainties:
        return np.nan
    
    if aggregation_method == "additive":
        return sum(component_uncertainties)
    elif aggregation_method == "quadratic":
        return np.sqrt(sum(u**2 for u in component_uncertainties))
    else:
        return np.mean(component_uncertainties)


def create_indicator_distribution_summary(
    df: pd.DataFrame,
    indicators: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Create distribution summary for composite indicators.
    
    Args:
        df: DataFrame with composite indicator columns
        indicators: Optional; list of indicator names (subset)
        
    Returns:
        Summary DataFrame with indicator distributions
    """
    if indicators is None:
        indicators = [col.replace("composite_", "") for col in df.columns 
                     if col.startswith("composite_")]
    
    summaries = []
    
    for indicator in indicators:
        col_name = f"composite_{indicator}" if not indicator.startswith("composite_") else indicator
        
        if col_name not in df.columns:
            continue
        
        values = df[col_name].dropna()
        
        summaries.append({
            "indicator": indicator,
            "total_cultures": len(df),
            "cultures_present": (values == 1).sum(),
            "cultures_absent": (values == 0).sum(),
            "presence_rate": (values == 1).sum() / len(values) if len(values) > 0 else np.nan,
            "mean_value": values.mean(),
            "std_value": values.std(),
            "min_value": values.min(),
            "max_value": values.max(),
        })
    
    return pd.DataFrame(summaries)
