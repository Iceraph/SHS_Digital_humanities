"""
Configuration and constants for Phase 2 harmonisation.

This module centralizes all methodological decisions and schema definitions
to ensure consistency across all harmonisation modules.

Reference: PROJECT_CONTEXT.md Section 8 (Methodological Decisions)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Literal
from pathlib import Path

# ==============================================================================
# ACTIVE SOURCES (FORWARD-COMPATIBLE DESIGN)
# ==============================================================================
# Controls which sources contribute to analytical logic.
# Current state: Seshat is mocked/excluded
# Future state: Simply add "seshat" to this list to reintegrate without refactoring
# 
# Architecture constraint:
#   - ALL source-related logic must check: if source in ACTIVE_SOURCES
#   - NEVER hardcode exclusion of any source
#   - When Seshat becomes real, toggle here and recompute (no code changes needed)

ACTIVE_SOURCES = ["dplace", "drh"]  # Future: ["dplace", "drh", "seshat"]

# ==============================================================================
# METHODOLOGICAL DECISIONS (locked in 15 April 2026)
# ==============================================================================

METHODOLOGICAL_DECISIONS = {
    "unit_of_observation_strategy": "keep_all",  # "keep_all", "collapse_to_finest", "polity_only"
    "crosswalk_validation_threshold": "any_source",  # "any_source", "majority_vote", "all_sources"
    "scale_harmonisation_rule": "theory_driven",  # "theory_driven", "majority_vote", "source_weighted"
    "galton_correction_primary": "one_per_language_family",  # "none", "one_per_language_family", "phylogenetic_weights"
    "galton_correction_robustness": "full_dataset",  # Always run full dataset as sensitivity check
    "region_definition": "natural_earth",  # "natural_earth", "custom", "other"
    "time_bin_width_years": 500,  # 200, 500, 1000
    "gap_threshold_records": 5,  # <5 records per region/time_bin = high gap severity
    "data_quality_scoring": True,  # Enable multi-factor data_quality_score
    "forward_compatible_sources": True,  # CRITICAL: Use ACTIVE_SOURCES for all source logic
}

# D-PLACE temporal standardisation assumption
DPLACE_TEMPORAL_ASSUMPTION = {
    "time_start": -1800,  # Ethnographic present window start (BCE)
    "time_end": -1950,  # Ethnographic present window end (BCE)
    "time_uncertainty": 3,  # High uncertainty ordinal: 0=certain, 1=±100yr, 2=±500yr, 3=±1000yr+
    "temporal_mode": "snapshot",
    "rationale": "150-year collection span (~1750–1950 CE) reflects ethnographic contact era",
}

# Galton's problem correction strategy
GALTON_STRATEGY = {
    "primary_method": "one_per_language_family",
    "via_source": "d_place",
    "linkage": "glottolog_code",
    "robustness_check": "full_dataset",
    "output_columns_primary": ["culture_id_galton", "language_family", "is_galton_representative"],
    "output_columns_robustness": ["culture_id_full", "galton_weight"],
}

# ==============================================================================
# HARMONISED SCHEMA (identical across all three sources)
# ==============================================================================

HARMONISED_SCHEMA = {
    # Phase 1 preserved columns
    "source": "str",  # "dplace", "seshat", "drh"
    "culture_id": "str",  # Unique per source
    "culture_name": "str",  # Non-empty
    "unit_type": "str",  # "society", "polity", "tradition"
    "lat": "float",  # Latitude [-90, 90] or NA
    "lon": "float",  # Longitude [-180, 180] or NA
    "time_start": "int",  # Calendar year (BCE = negative)
    "time_end": "int",  # Calendar year (BCE = negative)
    "variable_name": "str",  # Source-native variable name
    "variable_value": "float",  # Raw value from source
    "confidence": "float",  # Confidence/coder certainty [0.0, 1.0] or NA
    "notes": "str",  # Conflict flags, coder remarks (nullable)
    # Phase 2 added columns
    "unit_ambiguous": "int",  # Flag if unit boundaries uncertain (0/1)
    "unit_note": "str",  # Explanation of ambiguity (nullable)
    "time_start_standardised": "int",  # Standardised start time BCE/CE
    "time_end_standardised": "int",  # Standardised end time BCE/CE
    "temporal_mode": "str",  # "snapshot", "diachronic", or "mixed"
    "time_uncertainty": "int",  # Ordinal 0-3 (0=certain, 3=very uncertain)
    "feature_name": "str",  # Harmonised feature name (nullable)
    "feature_value": "float",  # Raw harmonised value (nullable)
    "feature_value_binarised": "float",  # Binarised 0/1 (nullable)
    "data_quality_score": "float",  # Multi-factor score [0.0, 1.5+]
}

# Column order (must be identical across all three harmonised outputs - 22 columns)
HARMONISED_COLUMN_ORDER = [
    # Phase 1 preserved
    "source",
    "culture_id",
    "culture_name",
    "unit_type",
    "lat",
    "lon",
    "time_start",
    "time_end",
    "variable_name",
    "variable_value",
    "confidence",
    "notes",
    # Phase 2 added
    "unit_ambiguous",
    "unit_note",
    "time_start_standardised",
    "time_end_standardised",
    "temporal_mode",
    "time_uncertainty",
    "feature_name",
    "feature_value",
    "feature_value_binarised",
    "data_quality_score",
]

# ==============================================================================
# FEATURE SCHEMA (from PROJECT_CONTEXT.md Section 3)
# Crosswalk maps source variables → these features
# ==============================================================================

FEATURE_SCHEMA = {
    # Altered states of consciousness (3.1)
    "trance_induction": {"type": "binary", "definition": "Practitioner deliberately enters non-ordinary mental state"},
    "soul_flight": {"type": "binary", "definition": "Soul/spirit travels to other realms while body remains"},
    "spirit_possession": {"type": "binary", "definition": "Spirit enters and controls the practitioner's body"},
    "entheogen_use": {"type": "binary", "definition": "Psychoactive substances used ritually for altered states"},
    # Specialist role and initiation (3.2)
    "dedicated_specialist": {
        "type": "ordinal",
        "scale": "0/1/2",
        "definition": "Recognized social role (0=none, 1=part-time, 2=full-time)",
    },
    "initiatory_crisis": {
        "type": "binary",
        "definition": "Illness, death-rebirth, or ordeal required before becoming specialist",
    },
    "hereditary_transmission": {"type": "binary", "definition": "Role passed within family/lineage"},
    # Cosmology and spirit world (3.3)
    "layered_cosmology": {
        "type": "binary",
        "definition": "Belief in upper/lower/middle worlds or axis mundi",
    },
    "animal_transformation": {"type": "binary", "definition": "Practitioner becomes or merges with animal spirit"},
    "ancestor_mediation": {
        "type": "binary",
        "definition": "Communication with or channeling of deceased ancestors",
    },
    "nature_spirits": {
        "type": "binary",
        "definition": "Interaction with spirits of natural features (rivers, mountains, forests)",
    },
    # Technique and performance (3.4)
    "rhythmic_percussion": {
        "type": "binary",
        "definition": "Drumming, rattling, or rhythmic sound central to trance induction",
    },
    "healing_function": {"type": "binary", "definition": "Primary purpose is curing illness or removing affliction"},
    "divination": {"type": "binary", "definition": "Foretelling future or discovering hidden knowledge"},
    "public_performance": {"type": "binary", "definition": "Ritual performed before community audience"},
    "chanting_singing": {
        "type": "binary",
        "definition": "Vocal techniques (icaros, throat singing, chanting) central to practice",
    },
}

# ==============================================================================
# DATA QUALITY SCORE PARAMETERS
# ==============================================================================

@dataclass
class DataQualityScoreWeights:
    """Weights for multi-factor data quality score computation.
    
    Formula: dqs = (1 - unit_ambiguous_penalty) * (1 - time_uncertainty_penalty) * source_count_boost
    where each component is normalized to [0, 1].
    """
    # Penalties: reduce score for ambiguity/uncertainty
    unit_ambiguous_penalty: float = 0.3  # -30% if unit is ambiguous
    time_uncertainty_max: int = 3  # Max uncertainty level
    
    # Boost: increase score for multiple sources
    # (source_count refers to how many sources contain this observation)
    source_count_weights: Dict[int, float] = field(default_factory=lambda: {
        1: 0.6,  # Single source: score * 0.6
        2: 0.9,  # Two sources: score * 0.9
        3: 1.0,  # All three sources: score * 1.0
    })

DATA_QUALITY_WEIGHTS = DataQualityScoreWeights()

# ==============================================================================
# CROSSWALK STRUCTURE
# ==============================================================================

CROSSWALK_COLUMNS = [
    "feature",  # Harmonised feature name (from FEATURE_SCHEMA)
    "d_place_var_id",  # D-PLACE variable ID(s) (pipe-separated if multiple)
    "d_place_code",  # D-PLACE code values (pipe-separated if multiple, e.g., "1|2|3")
    "drh_column",  # DRH column name or question text
    "seshat_var_id",  # Seshat variable ID(s)
    "primary_source",  # "d_place", "drh", "seshat", or "multiple"
    "binarisation_rule",  # Detailed rule for converting to binary (filled in scale.py)
    "confidence_level",  # "high", "medium", "low" - how confidently this mapping covers the feature
    "notes",  # Documentation of mapping decisions, conflicts, edge cases
]

# ==============================================================================
# SCALE DECISIONS STRUCTURE
# ==============================================================================

SCALE_DECISIONS_COLUMNS = [
    "feature",  # Feature name
    "d_place_scale",  # Scale in D-PLACE source ("binary", "ordinal_0-5", etc.)
    "drh_scale",  # Scale in DRH source
    "seshat_scale",  # Scale in Seshat source
    "harmonised_scale",  # Target scale after harmonisation ("binary" or "ordinal")
    "binarisation_rule",  # How ordinal values map to binary (e.g., "0/1 → 0; 2/3/4/5 → 1")
    "theory_justification",  # Why this binarisation rule makes theoretical sense
    "conflicts_detected",  # Boolean - were there source disagreements?
    "resolution_method",  # How conflicts were resolved ("majority_vote", "theory_driven", "flagged")
]

# ==============================================================================
# COVERAGE AUDIT STRUCTURE
# ==============================================================================

COVERAGE_AUDIT_COLUMNS = [
    "region",  # Natural Earth region name
    "time_bin_start",  # Start of 500-year time bin (BCE)
    "time_bin_end",  # End of 500-year time bin (BCE)
    "dplace_count",  # Number of D-PLACE records in this region/time bin
    "drh_count",  # Number of DRH records in this region/time bin
    "seshat_count",  # Number of Seshat records in this region/time bin
    "total_count",  # Sum of all sources
    "gap_severity",  # "low" (≥5), "high" (<5)
    "primary_source",  # Which source dominates ("d_place", "drh", "seshat", "mixed")
    "coverage_note",  # Free text explanation of gaps or patterns
]

# ==============================================================================
# CONFLICTS LOG STRUCTURE
# ==============================================================================

CONFLICTS_COLUMNS = [
    "culture_id_pair",  # "source1:id1-source2:id2" format for paired conflicts
    "culture_name",  # Readable name
    "variable_name",  # Which variable has conflict
    "source_a",  # First source ("dplace", "drh", "seshat")
    "value_a",  # Value from source A
    "confidence_a",  # Confidence in source A
    "source_b",  # Second source
    "value_b",  # Value from source B
    "confidence_b",  # Confidence in source B
    "conflict_type",  # "direct_contradiction", "one_na_other_not", "scale_mismatch", "unit_mismatch"
    "resolution",  # How conflict was resolved ("majority_vote", "high_confidence_wins", "flagged_for_review")
    "resolved_value",  # Final value used in harmonised output
    "notes",  # Additional context
]

# ==============================================================================
# PATH CONFIGURATION
# ==============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent  # Navigate to project root

DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_PROCESSED_HARMONISED = DATA_PROCESSED / "harmonised"
DATA_REFERENCE = PROJECT_ROOT / "data" / "reference"

NOTEBOOKS = PROJECT_ROOT / "notebooks"
SRC = PROJECT_ROOT / "src"
TESTS = PROJECT_ROOT / "tests"

# Raw Phase 1 outputs
DPLACE_RAW = DATA_PROCESSED / "dplace_real.parquet"
DRH_RAW = DATA_PROCESSED / "drh_raw.parquet"
SESHAT_RAW = DATA_PROCESSED / "seshat_raw.parquet"

# Harmonised Phase 2 outputs
DPLACE_HARMONISED = DATA_PROCESSED_HARMONISED / "dplace_harmonised.parquet"
DRH_HARMONISED = DATA_PROCESSED_HARMONISED / "drh_harmonised.parquet"
SESHAT_HARMONISED = DATA_PROCESSED_HARMONISED / "seshat_harmonised.parquet"

# Reference files
CROSSWALK = DATA_REFERENCE / "crosswalk.csv"
SCALE_DECISIONS = DATA_PROCESSED_HARMONISED / "scale_decisions.csv"
COVERAGE_AUDIT = DATA_PROCESSED_HARMONISED / "coverage_audit.csv"
CONFLICTS_LOG = DATA_PROCESSED_HARMONISED / "conflicts.csv"

# ==============================================================================
# VALIDATION & SANITY CHECKS
# ==============================================================================

def validate_schema() -> bool:
    """Ensure harmonised schema is internally consistent."""
    # All required columns present
    assert "source" in HARMONISED_SCHEMA
    assert "culture_id" in HARMONISED_SCHEMA
    assert len(HARMONISED_COLUMN_ORDER) == len(HARMONISED_SCHEMA)
    
    # All columns in order list exist in schema
    for col in HARMONISED_COLUMN_ORDER:
        assert col in HARMONISED_SCHEMA, f"Column {col} in order but not in schema"
    
    return True


if __name__ == "__main__":
    # Self-test
    print("✓ Harmonisation config loaded")
    print(f"✓ Harmonised schema: {len(HARMONISED_SCHEMA)} columns")
    print(f"✓ Feature schema: {len(FEATURE_SCHEMA)} features")
    print(f"✓ Crosswalk columns: {len(CROSSWALK_COLUMNS)}")
    print(f"✓ Methodological decisions locked: {len(METHODOLOGICAL_DECISIONS)} choices")
    validate_schema()
    print("✓ Schema validation passed")
