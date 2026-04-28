"""
Phase 3 Analysis Configuration

Defines constants, eras, regions, and quality thresholds for Phase 3 analysis.
"""

import pandas as pd
from typing import Dict, List, Tuple
from dataclasses import dataclass

# ============================================================================
# TEMPORAL CONFIGURATION
# ============================================================================

# Era definitions (Prehistoric to Modern)
ERAS = {
    "Prehistoric": {"start": -2000, "end": -1000, "label": "Prehistoric (-2000 to -1000)"},
    "Ancient": {"start": -1000, "end": 500, "label": "Ancient (-1000 to 500 CE)"},
    "Medieval": {"start": 500, "end": 1500, "label": "Medieval (500-1500 CE)"},
    "Early_Modern": {"start": 1500, "end": 1800, "label": "Early Modern (1500-1800 CE)"},
    "Industrial": {"start": 1800, "end": 1900, "label": "Industrial (1800-1900 CE)"},
    "Modern": {"start": 1900, "end": 2026, "label": "Modern (1900-present)"},
}

# Time bins for trend detection (500-year windows)
TIME_BIN_WIDTH = 500
TIME_BINS = [
    (start, start + TIME_BIN_WIDTH) 
    for start in range(-2000, 2026, TIME_BIN_WIDTH)
]

# Temporal uncertainty thresholds
TEMPORAL_CERTAINTY_LEVELS = {
    0: "Certain (specific year)",
    1: "±100 years",
    2: "±500 years",
    3: "±1000+ years",
}

# ============================================================================
# GEOGRAPHIC CONFIGURATION
# ============================================================================

# Regional definitions for analysis
REGIONS = {
    "Africa": {"code": "AFR", "description": "Africa"},
    "Americas": {"code": "AMR", "description": "North & South Americas"},
    "Asia-Pacific": {"code": "ASP", "description": "Asia, Pacific, Australia"},
    "Europe": {"code": "EUR", "description": "Europe, Middle East"},
    "Other": {"code": "OTH", "description": "Unclassified"},
}

# Geographic bounds for coordinate validation
COORD_BOUNDS = {
    "lat_min": -90,
    "lat_max": 90,
    "lon_min": -180,
    "lon_max": 180,
}

# Regional density thresholds (records per 1000 km²)
DENSITY_THRESHOLDS = {
    "high": 50.0,
    "medium": 10.0,
    "low": 1.0,
    "sparse": 0.1,
}

# Gap severity classification
GAP_THRESHOLDS = {
    "GREEN": 10,      # >=10 records: adequate coverage
    "YELLOW": 5,      # 5-9 records: moderate gaps
    "RED": 0,         # <5 records: severe gaps
}

# ============================================================================
# DATA QUALITY CONFIGURATION
# ============================================================================

# Note: Quality scores retained for uncertainty tracking, but NOT used for weighting
# (Decision: Issue #3 - removed source weighting to avoid hidden bias)
# Each source is treated equally; all-source rule determines presence

# Minimum quality score for inclusion in analysis
MIN_QUALITY_SCORE = 0.1

# Confidence thresholds for feature presence
CONFIDENCE_LEVELS = {
    "high": 0.8,
    "medium": 0.5,
    "low": 0.2,
    "unknown": 0.0,
}

# ============================================================================
# CONFLICT RESOLUTION CONFIGURATION
# ============================================================================

# Conflict resolution strategies
CONFLICT_STRATEGIES = {
    "any_source": "If any source reports feature → 1 (RECOMMENDED - no weighting bias)",
    "majority": "Majority vote across sources",
    "manual_inspection": "Flagged for manual review",
}

# Default conflict strategy (DECISION: Removed source weighting per Issue #3)
# Rationale: Any-source rule avoids hidden bias from quality assumptions
DEFAULT_CONFLICT_STRATEGY = "any_source"

# Conflict severity thresholds
AGREEMENT_THRESHOLDS = {
    "perfect": 1.0,    # All sources agree perfectly
    "strong": 0.75,    # 75%+ agreement
    "weak": 0.5,       # 50-75% agreement
    "conflict": 0.0,   # Substantial disagreement
}

# ============================================================================
# FEATURE SYNTHESIS CONFIGURATION
# ============================================================================

# Composite indicator definitions
COMPOSITE_INDICATORS = {
    "shamanic_complex": {
        "description": "Presence of core shamanic features",
        "components": [
            "trance_induction",
            "spirit_possession",
            "dedicated_specialist",
            "initiatory_crisis",
        ],
        "logic": "ANY 2+ of: (trance, possession, specialist, initiation)",
        "rationale": "Requires 2+ shamanic features; less restrictive than AND-gated version",
        "uncertainty_penalty": 1,  # +1 to uncertainty if any component is NA
    },
    "ritual_specialisation": {
        "description": "Professional ritual specialist role",
        "components": ["dedicated_specialist", "hereditary_transmission"],
        "logic": "(specialist >= 2) OR hereditary",
        "rationale": "Full-time role or hereditary transmission indicates specialisation",
        "uncertainty_penalty": 0.5,
    },
    "cosmological_framework": {
        "description": "Structured belief in spiritual realms",
        "components": [
            "layered_cosmology",
            "animal_transformation",
            "nature_spirits",
        ],
        "logic": "ANY 2+ of cosmology components present",
        "rationale": "At least 2 cosmological elements indicate structured framework",
        "uncertainty_penalty": 1,
    },
    "healing_technology": {
        "description": "Healing-focused ritual technology",
        "components": ["healing_function", "rhythmic_percussion"],
        "logic": "healing_function OR rhythmic_percussion",
        "rationale": "Either healing focus or percussion technique indicates healing technology",
        "uncertainty_penalty": 0.5,
    },
}

# ============================================================================
# ETHNOGRAPHIC VALIDATION CONFIGURATION
# ============================================================================

# Major culture groups for ethnographic validation
MAJOR_CULTURES = [
    {"id": "DRH_001", "name": "Siberian Shamanism"},
    {"id": "DRH_004", "name": "Korean Shamanism"},
    {"id": "DRH_007", "name": "Sami Shamanism (if available)"},
]

# Expected ethnographic features for shamanic cultures
ETHNOGRAPHIC_SHAMANIC_PROFILE = {
    "trance_induction": 1,
    "spirit_possession": 1,
    "dedicated_specialist": 1,
    "soul_flight": 1,
    "healing_function": 1,
    "rhythmic_percussion": 1,
}

# ============================================================================
# ANALYSIS OUTPUT PATHS
# ============================================================================

OUTPUT_PATHS = {
    "conflicts": "data/processed/harmonised/conflicts.csv",
    "era_analysis": "data/processed/analysis/era_analysis.csv",
    "region_analysis": "data/processed/analysis/region_analysis.csv",
    "comparison_matrix": "data/processed/analysis/comparison_matrix.csv",
    "composite_indicators": "data/processed/analysis/composite_indicators.csv",
    "ethnographic_validation": "data/processed/analysis/ethnographic_validation.csv",
}

# ============================================================================
# CONSTANTS FOR ANALYSIS
# ============================================================================

# Minimum sample size for statistical analysis
MIN_SAMPLE_SIZE = 3

# Bootstrap resampling parameters
BOOTSTRAP_N_ITER = 1000
BOOTSTRAP_SAMPLE_SIZE = 0.8

# Spatial autocorrelation analysis
SPATIAL_WEIGHT_TYPE = "knn"  # "knn" or "distance"
SPATIAL_N_NEIGHBORS = 5

# Phylogenetic signal analysis (D-PLACE societies)
PHYLOGENETIC_METHODS = ["pagel_lambda", "blomberg_k"]

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_era_for_timepoint(year: int) -> str:
    """
    Assign a timepoint (year) to an era.
    
    Args:
        year: Year in (negative for BCE, positive for CE)
        
    Returns:
        Era name or "Unknown" if outside defined ranges
    """
    for era_name, era_bounds in ERAS.items():
        if era_bounds["start"] <= year <= era_bounds["end"]:
            return era_name
    return "Unknown"


def get_time_bin_for_year(year: int) -> Tuple[int, int]:
    """
    Assign a year to a time bin.
    
    Args:
        year: Year (negative for BCE, positive for CE)
        
    Returns:
        Tuple of (bin_start, bin_end)
    """
    for bin_start, bin_end in TIME_BINS:
        if bin_start <= year <= bin_end:
            return (bin_start, bin_end)
    return None


def classify_gap_severity(record_count: int) -> str:
    """
    Classify coverage gap severity by record count.
    
    Args:
        record_count: Number of records in region/time bin
        
    Returns:
        Severity level: "GREEN" (good), "YELLOW" (sparse), "RED" (critical)
    """
    if record_count >= GAP_THRESHOLDS["GREEN"]:
        return "GREEN"
    elif record_count >= GAP_THRESHOLDS["YELLOW"]:
        return "YELLOW"
    else:
        return "RED"


# ============================================================================
# CLUSTERING CONFIGURATION (PHASE 4)
# ============================================================================

# Features for k-means and hierarchical clustering analysis
CLUSTERING_FEATURES = [
    'ancestor_mediation',
    'animal_transformation',
    'chanting_singing',
    'dedicated_specialist',
    'divination',
    'entheogen_use',
    'healing_function',
    'hereditary_transmission',
    'initiatory_crisis',
    'initiatory_ordeal',
    'layered_cosmology',
    'nature_spirits',
    'possession_crisis',
    'public_performance',
    'rhythmic_percussion',
    'ritual_performance',
    'soul_flight',
    'specialist_presence',
    'spirit_possession',
    'trance_induction',
    'unmapped_shamanic_indicators',
]

# K-means clustering parameters
KMEANS_PARAMS = {
    'k_range': range(2, 11),  # Test k from 2 to 10
    'n_init': 10,             # Number of initializations
    'random_state': 42,       # Reproducibility
    'silhouette_threshold': 0.4,  # Quality threshold for publishing
}

# Hierarchical clustering parameters
HIERARCHICAL_PARAMS = {
    'linkage_method': 'ward',  # Ward's linkage (minimum variance)
    'distance_metric': 'euclidean',
}

# Validation thresholds (Phase 4)
VALIDATION_THRESHOLDS = {
    'silhouette_score_min': 0.4,      # Publishable quality
    'davies_bouldin_max': 2.0,        # Good separation
    'calinski_harabasz_min': 20.0,    # Cluster definition
    'ari_agreement_threshold': 0.6,   # K-means vs hierarchical agreement
}


# ============================================================================
# DATA CLASSES FOR TYPE SAFETY
# ============================================================================

@dataclass
class ConflictRecord:
    """Record of a cross-source conflict or agreement."""
    culture_id: str
    culture_name: str
    feature: str
    source1: str
    value1: float
    quality1: float
    source2: str
    value2: float
    quality2: float
    agreement: bool
    conflict_type: str  # "agreement", "minor_conflict", "major_conflict"
    resolution_method: str
    resolved_value: float


@dataclass
class CompositeIndicatorRecord:
    """Record of a synthesised composite indicator."""
    culture_id: str
    culture_name: str
    indicator_name: str
    components: List[str]
    component_values: List[float]
    composite_value: float
    uncertainty: int
    data_quality_mean: float
