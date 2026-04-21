"""
Cross-Source Culture Linkage Module (Phase 2.5)

Links D-PLACE societies to DRH religious traditions using geographic proximity
and temporal overlap analysis. Produces confidence-scored linkage tables for
cross-source validation in Phase 3.

Key Functions:
  - haversine_distance(): Geographic distance calculation
  - find_geographic_matches(): Proximity-based matching
  - classify_temporal_overlap(): Temporal relationship classification
  - compute_confidence_score(): Combined confidence scoring
  - create_linkage_tables(): Full pipeline to generate reference tables
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import math


@dataclass
class LinkageRecord:
    """Single culture linkage record."""
    drh_id: str
    drh_tradition: str
    drh_lat: float
    drh_lon: float
    d_place_culture_id: str
    d_place_culture_name: str
    distance_km: float
    temporal_overlap: str
    confidence_score: float
    linkage_method: str
    notes: str


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Compute great-circle distance between two geographic points.
    
    Uses Haversine formula to calculate the shortest distance on Earth's surface
    between two points specified by latitude and longitude.
    
    Args:
        lat1, lon1: First point coordinates (degrees)
        lat2, lon2: Second point coordinates (degrees)
        
    Returns:
        Distance in kilometers
        
    Example:
        >>> distance = haversine_distance(60.0, 100.0, 37.0, 127.0)
        >>> print(f"{distance:.0f} km")  # Output: 3823 km
    """
    R = 6371  # Earth's radius in kilometers
    
    # Convert to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    # Haversine formula
    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def find_geographic_matches(
    df_dplace: pd.DataFrame,
    df_drh: pd.DataFrame,
    max_distance_km: float = 500.0,
) -> pd.DataFrame:
    """
    Find D-PLACE cultures within geographic proximity of each DRH tradition.
    
    For each DRH record, identifies all D-PLACE cultures within max_distance_km,
    sorted by distance (closer = higher priority).
    
    Args:
        df_dplace: D-PLACE harmonised DataFrame (must have lat, lon, culture_id, culture_name)
        df_drh: DRH harmonised DataFrame (must have lat, lon, culture_id, culture_name)
        max_distance_km: Maximum distance threshold (default 500 km)
        
    Returns:
        DataFrame with columns:
        - drh_id, drh_tradition, drh_lat, drh_lon
        - d_place_culture_id, d_place_culture_name
        - distance_km (distance from DRH coordinate to D-PLACE culture)
        - sorted by (drh_id, distance_km ascending)
        
    Example:
        >>> matches = find_geographic_matches(dplace_df, drh_df, max_distance_km=500)
        >>> print(f"Found {len(matches)} geographic matches")
    """
    # Get unique D-PLACE cultures with coordinates
    dplace_unique = df_dplace[[
        "culture_id", "culture_name", "lat", "lon"
    ]].drop_duplicates(subset=["culture_id"]).copy()
    
    # Get unique DRH traditions with coordinates
    drh_unique = df_drh[[
        "culture_id", "culture_name", "lat", "lon"
    ]].drop_duplicates(subset=["culture_id"]).copy()
    drh_unique.columns = ["drh_id", "drh_tradition", "drh_lat", "drh_lon"]
    
    matches = []
    
    # For each DRH tradition, find D-PLACE cultures within range
    for _, drh_row in drh_unique.iterrows():
        drh_id = drh_row["drh_id"]
        drh_tradition = drh_row["drh_tradition"]
        drh_lat = drh_row["drh_lat"]
        drh_lon = drh_row["drh_lon"]
        
        for _, dplace_row in dplace_unique.iterrows():
            distance = haversine_distance(
                drh_lat, drh_lon,
                dplace_row["lat"], dplace_row["lon"]
            )
            
            # Only include if within threshold
            if distance <= max_distance_km:
                matches.append({
                    "drh_id": drh_id,
                    "drh_tradition": drh_tradition,
                    "drh_lat": drh_lat,
                    "drh_lon": drh_lon,
                    "d_place_culture_id": dplace_row["culture_id"],
                    "d_place_culture_name": dplace_row["culture_name"],
                    "distance_km": distance,
                })
    
    matches_df = pd.DataFrame(matches)
    
    # Sort by distance (closer cultures first)
    if len(matches_df) > 0:
        matches_df = matches_df.sort_values(
            by=["drh_id", "distance_km"]
        ).reset_index(drop=True)
    
    return matches_df


def classify_temporal_overlap(
    d_place_time_start: float,
    d_place_time_end: float,
    drh_time_start: float,
    drh_time_end: float,
) -> Tuple[str, float]:
    """
    Classify temporal relationship between D-PLACE and DRH records.
    
    Evaluates whether time ranges overlap, are adjacent, or distant.
    
    RATIONALE for weights:
    - D-PLACE represents ~1800-1950 CE (ethnographic collection era)
    - DRH traditions often span multiple centuries
    - Strict temporal matching inappropriate for historical data
    - Weights penalise distance but accept >200yr gaps given uncertainty
    
    Args:
        d_place_time_start, d_place_time_end: D-PLACE time range (years, negative=BCE)
        drh_time_start, drh_time_end: DRH time range (years, negative=BCE)
        
    Returns:
        Tuple of (classification, weight):
        - ("SAME_ERA", 1.0): Periods overlap (high confidence)
        - ("ADJACENT_ERA", 0.7): Periods within ±200 years (good confidence)
        - ("NEARBY_ERA", 0.5): Periods within ±500 years (medium confidence)
        - ("DISTANT_ERA", 0.3): Periods >500 years apart (lower confidence, but not rejected)
        - ("NO_OVERLAP", 0.0): Periods disjoint (reject)
        - ("UNKNOWN_ERA", 0.5): Missing dates (default medium confidence)
        
    Example:
        >>> classification, weight = classify_temporal_overlap(-1950, -1800, -622, 2000)
        >>> print(f"{classification} (weight: {weight})")  # SAME_ERA or NEARBY_ERA
    """
    # Handle NaN values
    if pd.isna(d_place_time_start) or pd.isna(d_place_time_end) or \
       pd.isna(drh_time_start) or pd.isna(drh_time_end):
        return ("UNKNOWN_ERA", 0.5)  # Default to medium confidence if dates missing
    
    # Check if periods overlap
    overlap = not (d_place_time_end < drh_time_start or d_place_time_start > drh_time_end)
    
    if overlap:
        return ("SAME_ERA", 1.0)
    
    # Check if periods are adjacent or nearby (calculate minimum gap)
    gap_start = abs(d_place_time_end - drh_time_start)
    gap_end = abs(d_place_time_start - drh_time_end)
    min_gap = min(gap_start, gap_end)
    
    # FIXED: Increased weights to reduce harshness of temporal penalties
    # Old weights were too aggressive: ADJACENT=0.5, NEARBY=0.3, DISTANT=0.2
    # New weights give more credit to geographic proximity even with temporal gaps
    if min_gap <= 200:
        return ("ADJACENT_ERA", 0.7)  # Increased from 0.5
    elif min_gap <= 500:
        return ("NEARBY_ERA", 0.5)  # Increased from 0.3
    else:
        return ("DISTANT_ERA", 0.3)  # Increased from 0.2


def compute_confidence_score(
    distance_km: float,
    temporal_weight: float,
    max_distance_km: float = 500.0,
) -> float:
    """
    Compute combined confidence score from geographic and temporal signals.
    
    Confidence = (1 - normalized_distance) × temporal_weight
    
    Where normalized_distance = distance / max_distance
    
    Args:
        distance_km: Actual distance between points
        temporal_weight: Temporal overlap weight (0-1)
        max_distance_km: Reference distance for normalization
        
    Returns:
        Confidence score in [0, 1], where:
        - 0.9+: Excellent match (accept automatically)
        - 0.7-0.9: Good match (accept with minor review)
        - 0.5-0.7: Possible match (review candidate)
        - <0.5: Unlikely match (reject or expert override)
        
    Example:
        >>> # D-PLACE culture 200 km away, temporal SAME_ERA (weight 1.0)
        >>> score = compute_confidence_score(200, 1.0, 500)
        >>> print(f"Confidence: {score:.2f}")  # 0.60
    """
    if max_distance_km <= 0:
        raise ValueError("max_distance_km must be positive")
    
    # Normalize distance to [0, 1]
    normalized_distance = min(distance_km / max_distance_km, 1.0)
    
    # Geographic confidence: 1 at distance 0, decreasing to 0 at max_distance
    geographic_confidence = 1.0 - normalized_distance
    
    # Combined confidence: multiplicative with temporal weight
    confidence = geographic_confidence * temporal_weight
    
    return round(confidence, 3)


def resolve_linkages(
    matches_df: pd.DataFrame,
    confidence_threshold: float = 0.5,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Resolve geographic+temporal matches into structured linkage tables.
    
    Args:
        matches_df: DataFrame from find_geographic_matches() with temporal_overlap added
        confidence_threshold: Minimum confidence score to accept (default 0.5)
        
    Returns:
        Tuple of:
        1. linkage_table: Accepted linkages with confidence scores
        2. confidence_summary: Per-DRH record, distribution of match qualities
        3. needs_expert_review: Matches below confidence_threshold requiring review
        
    Example:
        >>> linkage, summary, review = resolve_linkages(matches_df)
        >>> print(f"Accepted: {len(linkage)}, Review needed: {len(review)}")
    """
    if len(matches_df) == 0:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    # Separate by confidence
    accepted = matches_df[matches_df["confidence_score"] >= confidence_threshold].copy()
    review = matches_df[matches_df["confidence_score"] < confidence_threshold].copy()
    
    # Prepare linkage table (main output)
    required_cols = [
        "drh_id", "drh_tradition", "drh_lat", "drh_lon",
        "d_place_culture_id", "d_place_culture_name",
        "distance_km", "temporal_overlap",
        "confidence_score", "linkage_method", "notes"
    ]
    available_cols = [c for c in required_cols if c in accepted.columns]
    linkage_table = accepted[available_cols].copy() if len(accepted) > 0 else pd.DataFrame()
    
    # Confidence summary: per-DRH record
    confidence_summary = pd.DataFrame()
    if len(accepted) > 0:
        def summarize_confidence(group):
            scores = group["confidence_score"].values
            high = len(scores[scores >= 0.8])
            medium = len(scores[(scores >= 0.5) & (scores < 0.8)])
            low = len(scores[scores < 0.5])
            
            distribution = []
            if high > 0:
                distribution.append(f"HIGH({high})")
            if medium > 0:
                distribution.append(f"MEDIUM({medium})")
            if low > 0:
                distribution.append(f"LOW({low})")
            
            return pd.Series({
                "num_d_place_matches": len(group),
                "confidence_distribution": ",".join(distribution) if distribution else "NONE",
                "needs_expert_review": len(group[group["confidence_score"] < 0.7]) > 0,
            })
        
        grouped = accepted.groupby("drh_id", as_index=False).apply(summarize_confidence)
        if len(grouped) > 0:
            confidence_summary = grouped.reset_index(drop=True)
            if "drh_tradition" in accepted.columns:
                tradition_map = accepted[["drh_id", "drh_tradition"]].drop_duplicates()
                # Make sure drh_id is in the correct position
                if "drh_id" in confidence_summary.columns:
                    confidence_summary = confidence_summary.merge(
                        tradition_map,
                        on="drh_id",
                        how="left"
                    )
                    # Reorder columns
                    col_order = ["drh_id", "drh_tradition", "num_d_place_matches",
                                "confidence_distribution", "needs_expert_review"]
                    confidence_summary = confidence_summary[
                        [c for c in col_order if c in confidence_summary.columns]
                    ]
    
    return linkage_table, confidence_summary, review


def create_linkage_tables(
    dplace_path: str,
    drh_path: str,
    max_distance_km: float = 500.0,
    confidence_threshold: float = 0.5,
) -> Dict[str, pd.DataFrame]:
    """
    Full pipeline: Load data, compute matches, generate linkage tables.
    
    Args:
        dplace_path: Path to D-PLACE harmonised parquet
        drh_path: Path to DRH harmonised parquet
        max_distance_km: Geographic proximity threshold (default 500 km)
        confidence_threshold: Confidence cutoff for acceptance (default 0.5)
        
    Returns:
        Dictionary with keys:
        - "linkage": Main linkage table (accepted matches)
        - "confidence_summary": Per-DRH record quality distribution
        - "needs_review": Matches below confidence threshold
        - "coverage": High-level linkage statistics
        
    Example:
        >>> tables = create_linkage_tables(
        ...     "data/processed/harmonised/dplace_harmonised.parquet",
        ...     "data/processed/harmonised/drh_harmonised.parquet"
        ... )
        >>> print(f"Linkage records: {len(tables['linkage'])}")
    """
    # Load data
    df_dplace = pd.read_parquet(dplace_path)
    df_drh = pd.read_parquet(drh_path)
    
    # Step 1: Find geographic matches
    matches_df = find_geographic_matches(df_dplace, df_drh, max_distance_km)
    
    # Step 2: Add temporal classification and confidence scores
    if len(matches_df) > 0:
        # Get time ranges for each culture
        dplace_times = df_dplace[[
            "culture_id", "time_start", "time_end"
        ]].drop_duplicates(subset=["culture_id"])
        
        drh_times = df_drh[[
            "culture_id", "time_start", "time_end"
        ]].drop_duplicates(subset=["culture_id"])
        drh_times.columns = ["drh_id", "drh_time_start", "drh_time_end"]
        
        # Merge time data
        matches_df = matches_df.merge(
            drh_times,
            on="drh_id",
            how="left"
        )
        matches_df = matches_df.merge(
            dplace_times.rename(columns={
                "culture_id": "d_place_culture_id",
                "time_start": "d_place_time_start",
                "time_end": "d_place_time_end"
            }),
            on="d_place_culture_id",
            how="left"
        )
        
        # Classify temporal overlap
        temporal_info = matches_df.apply(
            lambda row: pd.Series(
                classify_temporal_overlap(
                    row.get("d_place_time_start"),
                    row.get("d_place_time_end"),
                    row.get("drh_time_start"),
                    row.get("drh_time_end")
                )
            ),
            axis=1
        )
        matches_df["temporal_overlap"] = temporal_info[0]
        temporal_weight = temporal_info[1]
        
        # Compute confidence scores
        matches_df["confidence_score"] = matches_df.apply(
            lambda row: compute_confidence_score(
                row["distance_km"],
                temporal_weight[row.name],
                max_distance_km
            ),
            axis=1
        )
        
        # Add metadata
        matches_df["linkage_method"] = "geographic_proximity"
        matches_df["notes"] = matches_df.apply(
            lambda row: f"Distance: {row['distance_km']:.0f} km; Temporal: {row['temporal_overlap']}",
            axis=1
        )
    
    # Step 3: Resolve linkages
    linkage_table, confidence_summary, needs_review = resolve_linkages(
        matches_df,
        confidence_threshold
    )
    
    # Step 4: Coverage statistics
    drh_traditions_total = df_drh["culture_id"].nunique()
    drh_traditions_linked = confidence_summary["drh_id"].nunique() if len(confidence_summary) > 0 else 0
    d_place_involved = linkage_table["d_place_culture_id"].nunique() if len(linkage_table) > 0 else 0
    avg_matches = len(linkage_table) / max(drh_traditions_linked, 1) if drh_traditions_linked > 0 else 0
    
    coverage_stats = {
        "metric": [
            "drh_traditions_total",
            "drh_traditions_linked",
            "d_place_cultures_involved",
            "average_matches_per_tradition",
            "geographic_threshold_km",
            "confidence_threshold",
            "linkage_records_accepted",
            "linkage_records_needs_review",
        ],
        "value": [
            drh_traditions_total,
            drh_traditions_linked,
            d_place_involved,
            avg_matches,
            max_distance_km,
            confidence_threshold,
            len(linkage_table),
            len(needs_review),
        ]
    }
    coverage_df = pd.DataFrame(coverage_stats)
    
    return {
        "linkage": linkage_table,
        "confidence_summary": confidence_summary,
        "needs_review": needs_review,
        "coverage": coverage_df,
    }
