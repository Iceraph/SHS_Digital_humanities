"""
Geographic Analysis Module

Analyzes geographic distribution, regional bias, coordinate validation,
and geographic clustering of shamanic features.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

from .config import REGIONS, COORD_BOUNDS, GAP_THRESHOLDS, classify_gap_severity


def validate_coordinates(
    df: pd.DataFrame,
) -> Dict[str, any]:
    """
    Validate latitude/longitude coordinates.
    
    Identifies:
    - Out-of-bounds coordinates
    - Suspicious clusters (e.g., at 0,0)
    - Likely data-entry errors
    
    Args:
        df: Harmonised DataFrame with lat/lon columns
        
    Returns:
        Validation report with identified issues
    """
    issues = {
        "out_of_bounds": [],
        "zero_zero_cluster": [],
        "suspicious_patterns": [],
    }
    
    for idx, row in df.iterrows():
        lat, lon = row["lat"], row["lon"]
        
        # Skip NAs
        if pd.isna(lat) or pd.isna(lon):
            continue
        
        # Bounds check
        if (lat < COORD_BOUNDS["lat_min"] or lat > COORD_BOUNDS["lat_max"] or
            lon < COORD_BOUNDS["lon_min"] or lon > COORD_BOUNDS["lon_max"]):
            issues["out_of_bounds"].append({
                "culture_id": row["culture_id"],
                "coordinates": (lat, lon),
            })
        
        # Zero check
        if lat == 0 and lon == 0:
            issues["zero_zero_cluster"].append({
                "culture_id": row["culture_id"],
                "culture_name": row["culture_name"],
            })
    
    return issues


def assign_geographic_regions(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Assign geographic region labels based on lat/lon coordinates.
    
    Args:
        df: DataFrame with lat/lon columns
        
    Returns:
        DataFrame with added 'region' column
    """
    def get_region(lat, lon):
        if pd.isna(lat) or pd.isna(lon):
            return "Unknown"
        
        # Simple heuristic assignment
        if -40 <= lat <= 75 and -20 <= lon <= 70:
            return "Africa" if 15 <= lon else "Europe"
        elif lat > 0 and -130 <= lon <= -50:
            return "Americas"
        elif lat < 0 and -130 <= lon <= -50:
            return "Americas"
        elif -60 <= lat <= 55 and 70 <= lon <= 180:
            return "Asia-Pacific"
        elif -60 <= lat <= 55 and -180 <= lon < -130:
            return "Asia-Pacific"
        else:
            return "Other"
    
    df = df.copy()
    df["region"] = df.apply(lambda row: get_region(row["lat"], row["lon"]), axis=1)
    
    return df


def compute_regional_density(
    df: pd.DataFrame,
) -> Dict[str, Dict]:
    """
    Compute record and feature density per region.
    
    Args:
        df: DataFrame with 'region' column (from assign_geographic_regions)
        
    Returns:
        Dictionary with regional statistics
    """
    density = {}
    
    for region in df["region"].unique():
        region_df = df[df["region"] == region]
        
        # Count records and cultures
        record_count = len(region_df)
        culture_count = region_df["culture_id"].nunique()
        
        # Feature coverage (% of records with feature present)
        features_present = (region_df["feature_value_binarised"] == 1).sum()
        total_features = region_df["feature_value_binarised"].count()
        
        # Source distribution
        source_dist = region_df["source"].value_counts().to_dict()
        
        # Data quality
        mean_quality = region_df["data_quality_score"].mean()
        
        density[region] = {
            "record_count": record_count,
            "culture_count": culture_count,
            "feature_presence_rate": features_present / total_features if total_features > 0 else 0,
            "features_present": features_present,
            "features_absent": (region_df["feature_value_binarised"] == 0).sum(),
            "features_unknown": region_df["feature_value_binarised"].isna().sum(),
            "source_distribution": source_dist,
            "mean_data_quality": mean_quality,
        }
    
    return density


def identify_coverage_gaps(
    regional_density: Dict[str, Dict],
) -> pd.DataFrame:
    """
    Identify geographic regions and features with sparse coverage.
    
    Args:
        regional_density: Dictionary from compute_regional_density()
        
    Returns:
        DataFrame with gap severity classifications
    """
    gaps = []
    
    for region, stats in regional_density.items():
        record_count = stats["record_count"]
        severity = classify_gap_severity(record_count)
        
        gaps.append({
            "region": region,
            "record_count": record_count,
            "culture_count": stats["culture_count"],
            "feature_coverage": stats["feature_presence_rate"],
            "gap_severity": severity,
            "recommendation": _get_gap_recommendation(severity),
        })
    
    return pd.DataFrame(gaps).sort_values("record_count")


def _get_gap_recommendation(severity: str) -> str:
    """Gap severity recommendation text."""
    recommendations = {
        "GREEN": "Adequate coverage; proceed with regional analysis",
        "YELLOW": "Moderate gaps; use with caution in conclusions",
        "RED": "Critical gaps; flag results as speculative",
    }
    return recommendations.get(severity, "Unknown gap severity")


def compute_geographic_bias(
    dplace_density: Dict,
    drh_density: Dict,
    seshat_density: Optional[Dict] = None,
) -> pd.DataFrame:
    """
    Quantify D-PLACE oversampling by comparing regional distributions.
    
    Args:
        dplace_density: From compute_regional_density() for D-PLACE
        drh_density: From compute_regional_density() for DRH
        seshat_density: Optional from compute_regional_density() for Seshat
        
    Returns:
        Bias report DataFrame
    """
    report = []
    
    all_regions = set(dplace_density.keys()) | set(drh_density.keys())
    if seshat_density:
        all_regions |= set(seshat_density.keys())
    
    for region in all_regions:
        row = {"region": region}
        
        dplace_recs = dplace_density.get(region, {}).get("record_count", 0)
        drh_recs = drh_density.get(region, {}).get("record_count", 0)
        seshat_recs = seshat_density.get(region, {}).get("record_count", 0) if seshat_density else 0
        
        total_recs = dplace_recs + drh_recs + seshat_recs
        
        row["dplace_count"] = dplace_recs
        row["dplace_percent"] = (dplace_recs / total_recs * 100) if total_recs > 0 else 0
        row["drh_count"] = drh_recs
        row["drh_percent"] = (drh_recs / total_recs * 100) if total_recs > 0 else 0
        row["seshat_count"] = seshat_recs
        row["seshat_percent"] = (seshat_recs / total_recs * 100) if total_recs > 0 else 0
        row["total_count"] = total_recs
        
        # Bias indicator: if D-PLACE > 80% of records, flag oversampling
        if total_recs > 0:
            dplace_bias = dplace_recs / total_recs
            if dplace_bias > 0.8:
                row["bias_indicator"] = "HIGH_DPLACE_BIAS"
            elif dplace_bias > 0.5:
                row["bias_indicator"] = "MODERATE_DPLACE_BIAS"
            else:
                row["bias_indicator"] = "BALANCED"
        else:
            row["bias_indicator"] = "NO_DATA"
        
        report.append(row)
    
    return pd.DataFrame(report).sort_values("total_count", ascending=False)


def create_geographic_profile(
    df: pd.DataFrame,
) -> Dict[str, any]:
    """
    Create summary geographic profile of dataset.
    
    Args:
        df: Harmonised DataFrame with geographic columns
        
    Returns:
        Profile dictionary with geographic statistics
    """
    # Validation
    coord_issues = validate_coordinates(df)
    
    # Regional assignment
    df = assign_geographic_regions(df)
    
    # Density
    regional_density = compute_regional_density(df)
    
    # Gaps
    coverage_gaps = identify_coverage_gaps(regional_density)
    
    return {
        "coordinate_validation": coord_issues,
        "regions_represented": list(regional_density.keys()),
        "regional_statistics": regional_density,
        "coverage_gaps": coverage_gaps.to_dict("records"),
        "geographic_extent": {
            "lat_range": (df["lat"].min(), df["lat"].max()),
            "lon_range": (df["lon"].min(), df["lon"].max()),
        },
    }


def detect_geographic_clusters(
    df: pd.DataFrame,
    eps_km: float = 500.0,
) -> pd.DataFrame:
    """
    Detect geographic clusters of cultures using simple distance-based grouping.
    
    Args:
        df: DataFrame with lat/lon coordinates
        eps_km: Distance threshold in kilometers
        
    Returns:
        DataFrame with cluster assignments
    """
    from scipy.spatial.distance import cdist
    
    coords = df[["lat", "lon"]].values
    
    # Approximate km per degree at equator
    km_per_degree_lat = 111
    km_per_degree_lon = 111 * np.cos(np.radians(coords[:, 0]))
    
    # Normalize coordinates
    coords_normalized = coords.copy()
    coords_normalized[:, 0] *= km_per_degree_lat
    coords_normalized[:, 1] *= km_per_degree_lon
    
    # Simple clustering: assign to clusters
    distances = cdist(coords_normalized, coords_normalized)
    
    clusters = -np.ones(len(coords), dtype=int)
    cluster_id = 0
    
    for i in range(len(coords)):
        if clusters[i] == -1:
            # Find all points within eps_km
            neighbors = np.where(distances[i] <= eps_km)[0]
            clusters[neighbors] = cluster_id
            cluster_id += 1
    
    df = df.copy()
    df["geographic_cluster"] = clusters
    
    return df
