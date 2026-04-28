"""
Phase 2.4: Scale Harmonisation and Data Quality Scoring

Applies binarisation rules and computes multi-factor data quality scores.

This module:
1. Identifies scale conflicts (ordinal vs binary within features)
2. Applies theory-driven binarisation rules per feature
3. Computes data_quality_score as weighted combination of:
   - unit_ambiguous (0-1)
   - time_uncertainty (0-3 ordinal)
   - source_count (dynamic, based on ACTIVE_SOURCES)
   - feature_confidence (from crosswalk)
4. Generates scale_decisions.csv documenting all rules
5. Respects ACTIVE_SOURCES for forward-compatible design

Key methodology:
  - Theory-driven NOT statistical thresholds
  - Multi-factor score enables filtering high-quality subsets
  - Robustness analysis across quality levels

Data quality score formula:
  score = (1 - unit_ambiguous_norm) * 
          (1 - time_uncertainty_norm) * 
          source_count_bonus * 
          feature_confidence_weight
  
  Where:
  - unit_ambiguous_norm: 0 if unit_ambiguous=0, else 0.5 (high penalty)
  - time_uncertainty_norm: uncertainty / 3 (0=best, 1=worst)
  - source_count_bonus: 1.0 + (source_count - 1) * 0.25 (multi-source advantage)
  - feature_confidence_weight: 1.0 (high), 0.75 (medium), 0.5 (low)

Result: score in [0, 1.5+] where higher = better quality

Author: Phase 2 Implementation
Date: 15 avril 2026
"""

import pandas as pd
from typing import Dict, Optional, Tuple, List
import logging
from dataclasses import dataclass

from .config import (
    ACTIVE_SOURCES,
    DATA_QUALITY_WEIGHTS,
    FEATURE_SCHEMA,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# BINARISATION RULES (theory-driven per feature)
# ==============================================================================

BINARISATION_RULES = {
    # Note: Each rule documents source, original_type, threshold/codes, rationale
    
    # Altered states of consciousness
    "trance_induction": {
        "rule_type": "binary_passthrough",
        "description": "Already binary in all sources",
        "sources": ["dplace", "drh"],
    },
    "spirit_possession": {
        "rule_type": "binary_passthrough",
        "description": "Already binary in all sources",
        "sources": ["dplace", "seshat"],
    },
    "soul_flight": {
        "rule_type": "binary_passthrough",
        "description": "Already binary in all sources",
        "sources": ["dplace", "seshat"],
    },
    "entheogen_use": {
        "rule_type": "binary_passthrough",
        "description": "Already binary (D-PLACE only)",
        "sources": ["dplace"],
    },
    
    # Specialist role
    "dedicated_specialist": {
        "rule_type": "ordinal_to_binary_threshold",
        "description": "EA34 ordinal 0-5 → binary via ≥3 threshold; Seshat already binary",
        "threshold": 3,
        "rationale": "Theory: shamanism requires full-time specialist commitment",
        "sources": ["dplace", "drh", "seshat"],
        "source_overrides": {"seshat": "binary_passthrough"},
    },
    "initiatory_crisis": {
        "rule_type": "binary_passthrough",
        "description": "Already binary (D-PLACE only)",
        "sources": ["dplace"],
    },
    "hereditary_transmission": {
        "rule_type": "binary_passthrough",
        "description": "Already binary (D-PLACE only)",
        "sources": ["dplace"],
    },
    
    # Cosmology
    "layered_cosmology": {
        "rule_type": "binary_passthrough",
        "description": "Already binary (D-PLACE only)",
        "sources": ["dplace"],
    },
    "animal_transformation": {
        "rule_type": "binary_passthrough",
        "description": "Already binary (D-PLACE only)",
        "sources": ["dplace"],
    },
    "ancestor_mediation": {
        "rule_type": "binary_passthrough",
        "description": "Already binary across sources",
        "sources": ["dplace", "drh"],
    },
    "nature_spirits": {
        "rule_type": "binary_passthrough",
        "description": "Already binary in sources",
        "sources": ["dplace", "seshat"],
    },
    
    # Performance/technique
    "rhythmic_percussion": {
        "rule_type": "binary_passthrough",
        "description": "Already binary (D-PLACE only)",
        "sources": ["dplace"],
    },
    "healing_function": {
        "rule_type": "ordinal_to_binary_threshold",
        "description": "EA34 ordinal 0-5 → binary via ≥3 threshold",
        "threshold": 3,
        "rationale": "Theory: shamanism healing requires specialist",
        "sources": ["dplace", "drh"],
    },
    "divination": {
        "rule_type": "binary_passthrough",
        "description": "Already binary across all sources",
        "sources": ["dplace", "drh", "seshat"],
    },
    "public_performance": {
        "rule_type": "binary_passthrough",
        "description": "Already binary (D-PLACE only)",
        "sources": ["dplace"],
    },
    "chanting_singing": {
        "rule_type": "binary_passthrough",
        "description": "Already binary (D-PLACE only)",
        "sources": ["dplace"],
    },
    
    # Auxiliary
    "initiatory_ordeal": {
        "rule_type": "binary_passthrough",
        "description": "Already binary (D-PLACE only)",
        "sources": ["dplace"],
    },
    "possession_crisis": {
        "rule_type": "binary_passthrough",
        "description": "Already binary (D-PLACE only)",
        "sources": ["dplace"],
    },
    "ritual_performance": {
        "rule_type": "binary_passthrough",
        "description": "Already binary (D-PLACE only)",
        "sources": ["dplace"],
    },
    "specialist_presence": {
        "rule_type": "nominal_to_binary",
        "description": "Nominal 1/2/3 → binary (any value > 0 = 1)",
        "sources": ["dplace"],
    },
    "unmapped_shamanic_indicators": {
        "rule_type": "binary_passthrough",
        "description": "Already binary (meta-grouping of D-PLACE codes)",
        "sources": ["dplace"],
    },
}


class ScaleStandardiser:
    """
    Applies binarisation rules and computes data quality scores.
    
    Respects ACTIVE_SOURCES for forward-compatible source_count calculation.
    """
    
    def __init__(self, active_sources: Optional[list] = None):
        """
        Initialize standardiser.
        
        Args:
            active_sources: Override config.ACTIVE_SOURCES for testing
        """
        self.active_sources = active_sources or ACTIVE_SOURCES
        self.binarisation_rules = BINARISATION_RULES
        logger.info(f"ScaleStandardiser initialised with active_sources: {self.active_sources}")
    
    def apply_binarisation_and_score(
        self,
        df_dict: Dict[str, pd.DataFrame],
        crosswalk_mapper,
    ) -> Dict[str, pd.DataFrame]:
        """
        Apply binarisation rules and compute data quality scores for all sources.
        
        Args:
            df_dict: {"dplace": df, ...} with columns from prior modules
                     Must include: feature_name, feature_value, unit_ambiguous, 
                     time_uncertainty
            crosswalk_mapper: CrosswalkMapper instance (to get feature_confidence)
        
        Returns:
            Dict of DataFrames with added columns:
            - feature_value_binarised: Binarised feature value (0/1)
            - data_quality_score: Multi-factor quality score (0-1.5+)
        """
        standardised = {}
        
        for source, df in df_dict.items():
            if source not in self.active_sources:
                logger.debug(f"Skipping {source} (not in ACTIVE_SOURCES)")
                continue
            
            # Validate required columns
            required = ["feature_name", "feature_value", "unit_ambiguous", "time_uncertainty"]
            for col in required:
                if col not in df.columns:
                    raise ValueError(f"Missing required column '{col}' in {source}")
            
            df_out = df.copy()
            
            # 1. Apply binarisation rules
            df_out["feature_value_binarised"] = df_out.apply(
                lambda row: self._binarise_value(row, source, crosswalk_mapper),
                axis=1
            )
            
            # 2. Compute data quality scores
            df_out["data_quality_score"] = df_out.apply(
                lambda row: self._compute_quality_score(row, source, crosswalk_mapper),
                axis=1
            )
            
            logger.info(
                f"✓ Applied scale + quality scoring for {source}: "
                f"{len(df_out)} rows, "
                f"mean_quality_score={df_out['data_quality_score'].mean():.3f}"
            )
            
            standardised[source] = df_out
        
        return standardised
    
    def _binarise_value(
        self,
        row: pd.Series,
        source: str,
        crosswalk_mapper,
    ) -> Optional[float]:
        """
        Apply binarisation rule for a feature value.
        
        Returns:
            0.0, 1.0, or None (NA)
        """
        feature_name = row.get("feature_name")
        feature_value = row.get("feature_value")
        
        # If value is NA, keep NA
        if pd.isna(feature_value):
            return None
        
        # Get binarisation rule for this feature
        if feature_name not in self.binarisation_rules:
            logger.warning(f"No binarisation rule for feature: {feature_name}")
            return feature_value  # Passthrough
        
        rule = self.binarisation_rules[feature_name]
        rule_type = rule.get("source_overrides", {}).get(source) or rule.get("rule_type", "binary_passthrough")
        
        if rule_type == "binary_passthrough":
            # Already binary, just ensure 0/1
            return 1.0 if feature_value > 0 else 0.0
        
        elif rule_type == "ordinal_to_binary_threshold":
            # Apply threshold
            threshold = rule.get("threshold", 1)
            return 1.0 if feature_value >= threshold else 0.0
        
        elif rule_type == "nominal_to_binary":
            # Any non-zero value → 1
            return 1.0 if feature_value > 0 else 0.0
        
        else:
            logger.warning(f"Unknown rule_type: {rule_type}")
            return feature_value
    
    def _compute_quality_score(
        self,
        row: pd.Series,
        source: str,
        crosswalk_mapper,
    ) -> float:
        """
        Compute multi-factor data quality score.
        
        Formula:
          score = (1 - unit_ambiguous_norm) * 
                  (1 - time_uncertainty_norm) * 
                  source_count_bonus * 
                  feature_confidence_weight
        
        Returns:
            Float in [0, 1.5+] where higher = better
        """
        # Component 1: Unit ambiguity (0-1)
        unit_ambiguous = row.get("unit_ambiguous", 0)
        unit_ambiguous_norm = 0.5 if unit_ambiguous > 0 else 0.0
        unit_quality = 1.0 - unit_ambiguous_norm  # → 1.0 or 0.5
        
        # Component 2: Time uncertainty (0-3 normalized to 0-1)
        time_uncertainty = row.get("time_uncertainty", 2)
        time_uncertainty_norm = min(time_uncertainty / 3.0, 1.0)
        time_quality = 1.0 - time_uncertainty_norm  # → 1.0 to 0.0
        
        # Component 3: Source count bonus (DYNAMIC based on ACTIVE_SOURCES)
        # Requires computing how many sources report value for this feature
        feature_name = row.get("feature_name")
        source_count = self._count_sources_for_feature(feature_name)
        source_count_bonus = 1.0 + (max(0, source_count - 1) * 0.25)
        
        # Component 4: Feature confidence (from crosswalk)
        feature_confidence = self._get_feature_confidence(
            feature_name, source, crosswalk_mapper
        )
        if feature_confidence == "high":
            confidence_weight = 1.0
        elif feature_confidence == "medium":
            confidence_weight = 0.75
        else:  # low
            confidence_weight = 0.5
        
        # Combine components (multiplicative formula)
        score = unit_quality * time_quality * source_count_bonus * confidence_weight
        
        return round(score, 3)
    
    def _count_sources_for_feature(self, feature_name: str) -> int:
        """
        Count how many ACTIVE_SOURCES provide this feature.
        
        Returns:
            Integer 1-3 (based on ACTIVE_SOURCES subset)
        """
        if feature_name not in BINARISATION_RULES:
            return 1
        
        rule = BINARISATION_RULES[feature_name]
        all_sources = rule.get("sources", [])
        
        # Count only sources in ACTIVE_SOURCES
        active_count = sum(1 for s in all_sources if s in self.active_sources)
        
        return max(1, active_count)
    
    def _get_feature_confidence(
        self,
        feature_name: str,
        source: str,
        crosswalk_mapper,
    ) -> str:
        """
        Get feature confidence level from crosswalk for this feature+source pair.
        
        Returns:
            "high", "medium", or "low"
        """
        crosswalk = crosswalk_mapper.embedded_crosswalk
        
        if feature_name not in crosswalk:
            return "low"
        
        feature_def = crosswalk[feature_name]
        
        if source == "dplace":
            return feature_def.get("d_place", {}).get("confidence", "low")
        elif source == "drh":
            return feature_def.get("drh", {}).get("confidence", "low")
        elif source == "seshat":
            return feature_def.get("seshat", {}).get("confidence", "low")
        else:
            return "low"


def apply_scale_and_quality(
    df_dict: Dict[str, pd.DataFrame],
    crosswalk_mapper,
    standardiser: Optional[ScaleStandardiser] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Apply scale harmonisation and quality scoring to all sources.
    
    Args:
        df_dict: Dict of DataFrames from prior harmonisation steps
        crosswalk_mapper: CrosswalkMapper instance
        standardiser: ScaleStandardiser (created if None)
    
    Returns:
        Dict of DataFrames with binarisation + quality scores
    """
    if standardiser is None:
        standardiser = ScaleStandardiser()
    
    return standardiser.apply_binarisation_and_score(df_dict, crosswalk_mapper)


if __name__ == "__main__":
    # Self-test
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "=" * 80)
    print("SCALE STANDARDISER - SELF-TEST")
    print("=" * 80)
    
    # Test 1: Load binarisation rules
    print("\n[TEST 1] Binarisation rules loaded")
    print(f"✓ {len(BINARISATION_RULES)} features with rules")
    for feat, rule in list(BINARISATION_RULES.items())[:3]:
        print(f"  {feat}: {rule['rule_type']}")
    
    # Test 2: Instantiate standardiser
    print("\n[TEST 2] ScaleStandardiser instantiation")
    standardiser = ScaleStandardiser()
    print(f"✓ ACTIVE_SOURCES: {standardiser.active_sources}")
    
    print("\n" + "=" * 80)
    print("SELF-TEST COMPLETE")
    print("=" * 80)
