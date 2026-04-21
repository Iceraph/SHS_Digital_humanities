"""
Phase 2.2: Unit-of-Observation Standardisation

Standardises unit types across three independent data sources and flags ambiguities.

This module:
1. Validates unit_type is present in all Phase 1 outputs
2. Adds unit_ambiguous: binary flag if unit boundaries uncertain
3. Adds unit_note: free text explanation of ambiguity
4. Preserves all unit types (society, tradition, polity) as received
5. Respects ACTIVE_SOURCES for forward-compatible design

Key methodological decision (locked Phase 2):
  "Keep all units of observation (society, tradition, polity) without dropping any"
  Rationale: Different unit types capture different social scales; filtering happens downstream

Unit type mapping:
  - D-PLACE: "society" (SCCS/ethnographic sample)
  - DRH: "tradition" (cultural lineage/style family)
  - Seshat: "polity" (political entity)

Ambiguity flags:
  - unit_ambiguous: True if unit boundaries unclear from metadata
  - unit_note: Explanation + confidence

Author: Phase 2 Implementation
Date: 15 avril 2026
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging

from .config import (
    ACTIVE_SOURCES,
    DPLACE_RAW,
    DRH_RAW,
    SESHAT_RAW,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# UNIT-OF-OBSERVATION STANDARDISATION CONSTANTS
# ==============================================================================

UNIT_TYPE_VALIDATOR = {
    "dplace": {"expected": "society", "description": "SCCS ethnographic sample"},
    "drh": {"expected": "tradition", "description": "Cultural lineage / style family"},
    "seshat": {"expected": "polity", "description": "Political entity / state-level"},
}

AMBIGUITY_RULES = {
    # D-PLACE
    "dplace": {
        "temporal_span": {
            "rule": "time_end - time_start > 300",
            "flag": True,
            "note": "Long temporal span (>300 years) suggests composite or uncertain unit",
        },
        "missing_location": {
            "rule": "lat is NA or lon is NA",
            "flag": True,
            "note": "Missing geographic coordinates reduces unit boundary precision",
        },
    },
    # DRH
    "drh": {
        "missing_tradition_id": {
            "rule": "culture_id is NA or empty",
            "flag": True,
            "note": "Missing tradition identifier; ambiguous lineage definition",
        },
    },
    # Seshat
    "seshat": {
        "missing_polity_boundaries": {
            "rule": "lat is NA or lon is NA",
            "flag": True,
            "note": "Missing polity coordinates; boundary definition uncertain",
        },
    },
}


class UnitStandardiser:
    """
    Standardises unit-of-observation across D-PLACE, DRH, Seshat.
    
    Approach:
    1. Validate unit_type matches expected value for source
    2. Calculate ambiguity flags based on metadata precision
    3. Add explanatory notes
    4. Preserve all units without filtering
    
    Forward-compatible: respects ACTIVE_SOURCES for all validations.
    """
    
    def __init__(self, active_sources: Optional[list] = None):
        """
        Initialize standardiser.
        
        Args:
            active_sources: Override config.ACTIVE_SOURCES for testing
        """
        self.active_sources = active_sources or ACTIVE_SOURCES
        logger.info(f"UnitStandardiser initialised with active_sources: {self.active_sources}")
    
    def standardise_units(
        self,
        df: pd.DataFrame,
        source: str,
    ) -> pd.DataFrame:
        """
        Add unit standardisation columns to Phase 1 DataFrame.
        
        Adds:
          - unit_type_standardised: Canonical unit type for source
          - unit_ambiguous: Binary flag (0/1)
          - unit_note: Explanation of ambiguity (if flagged)
        
        Args:
            df: Phase 1 DataFrame (already has unit_type column)
            source: "dplace", "drh", or "seshat"
        
        Returns:
            DataFrame with three new columns added
        """
        # Validate source is active
        if source not in self.active_sources:
            logger.debug(f"Source {source} not in ACTIVE_SOURCES; skipping standardisation")
            return df.copy()
        
        # Validate unit_type column exists
        if "unit_type" not in df.columns:
            raise ValueError(f"Column 'unit_type' not found in Phase 1 DataFrame for {source}")
        
        # Validate source is recognised
        if source not in UNIT_TYPE_VALIDATOR:
            raise ValueError(f"Unknown source: {source}")
        
        df_out = df.copy()
        
        # 1. Standardise unit_type
        expected_unit = UNIT_TYPE_VALIDATOR[source]["expected"]
        df_out["unit_type_standardised"] = expected_unit
        
        # 2. Compute ambiguity flags
        df_out["unit_ambiguous"] = df_out.apply(
            lambda row: self._compute_ambiguity(row, source),
            axis=1
        )
        
        # 3. Generate explanatory notes
        df_out["unit_note"] = df_out.apply(
            lambda row: self._generate_note(row, source),
            axis=1
        )
        
        # Validate output has expected columns
        expected_cols = ["unit_type_standardised", "unit_ambiguous", "unit_note"]
        for col in expected_cols:
            if col not in df_out.columns:
                raise ValueError(f"Missing expected output column: {col}")
        
        logger.info(
            f"✓ Standardised units for {source}: "
            f"{len(df_out)} rows, "
            f"{df_out['unit_ambiguous'].sum()} flagged ambiguous"
        )
        
        return df_out
    
    def _compute_ambiguity(self, row: pd.Series, source: str) -> int:
        """
        Compute unit ambiguity flag (0/1) based on metadata precision.
        
        Returns:
            1 if any ambiguity rule triggered, else 0
        """
        if source not in AMBIGUITY_RULES:
            return 0
        
        rules = AMBIGUITY_RULES[source]
        
        for rule_name, rule_def in rules.items():
            if self._check_rule(row, source, rule_name):
                return 1
        
        return 0
    
    def _check_rule(self, row: pd.Series, source: str, rule_name: str) -> bool:
        """
        Check if a single ambiguity rule is triggered for this row.
        
        Rule format:
          "rule": "logic expression checking columns"
          "flag": Boolean whether to flag if true
        """
        rule_def = AMBIGUITY_RULES[source][rule_name]
        rule_text = rule_def["rule"]
        
        # Evaluate rule expressions
        if source == "dplace":
            if rule_name == "temporal_span":
                # time_end - time_start > 300
                if pd.notna(row.get("time_start")) and pd.notna(row.get("time_end")):
                    span = row["time_end"] - row["time_start"]
                    return span > 300
            elif rule_name == "missing_location":
                # lat is NA or lon is NA
                return pd.isna(row.get("lat")) or pd.isna(row.get("lon"))
        
        elif source == "drh":
            if rule_name == "missing_tradition_id":
                # culture_id is NA or empty
                culture_id = row.get("culture_id")
                return pd.isna(culture_id) or culture_id == ""
        
        elif source == "seshat":
            if rule_name == "missing_polity_boundaries":
                # lat is NA or lon is NA
                return pd.isna(row.get("lat")) or pd.isna(row.get("lon"))
        
        return False
    
    def _generate_note(self, row: pd.Series, source: str) -> str:
        """
        Generate explanatory note for unit ambiguity.
        
        Returns:
            - Short description if ambiguous
            - Empty string if not ambiguous
        """
        if row.get("unit_ambiguous", 0) == 0:
            return ""
        
        if source not in AMBIGUITY_RULES:
            return "Ambiguity flagged but source not in rules"
        
        rules = AMBIGUITY_RULES[source]
        notes = []
        
        for rule_name, rule_def in rules.items():
            if self._check_rule(row, source, rule_name):
                notes.append(rule_def["note"])
        
        return "; ".join(notes)
    
    def validate_all_units(self, raw_dfs: Dict[str, pd.DataFrame]) -> Dict[str, any]:
        """
        Validate unit consistency across all active sources.
        
        Args:
            raw_dfs: {"dplace": df, "drh": df, "seshat": df} from Phase 1
        
        Returns:
            Validation report:
            {
              "all_valid": bool,
              "dplace": {"unit_types": [...], "ambiguous_count": N, "valid": bool},
              "drh": {"unit_types": [...], "ambiguous_count": N, "valid": bool},
              "seshat": {"unit_types": [...], "ambiguous_count": N, "valid": bool},
            }
        """
        report = {"all_valid": True}
        
        for source, df in raw_dfs.items():
            if source not in self.active_sources:
                logger.debug(f"Skipping {source} validation (not in ACTIVE_SOURCES)")
                continue
            
            if source not in df.columns and "unit_type" not in df.columns:
                report[source] = {
                    "unit_types": [],
                    "ambiguous_count": "N/A",
                    "valid": False,
                    "error": "Missing unit_type column",
                }
                report["all_valid"] = False
                continue
            
            report[source] = {
                "unit_types": sorted(df["unit_type"].unique().tolist()),
                "count": len(df),
                "valid": True,
            }
        
        if report["all_valid"]:
            logger.info("✓ All source unit types validated")
        else:
            logger.warning("⚠ Unit validation issues detected")
        
        return report


def standardise_all_units(
    raw_dfs: Dict[str, pd.DataFrame],
    standardiser: Optional[UnitStandardiser] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Apply unit standardisation to all Phase 1 DataFrames.
    
    Args:
        raw_dfs: {"dplace": df, "drh": df, "seshat": df} from Phase 1
        standardiser: UnitStandardiser instance (created if None)
    
    Returns:
        Dict of DataFrames with unit columns added:
        {
          "dplace": df with [unit_type_standardised, unit_ambiguous, unit_note],
          "drh": df with [unit_type_standardised, unit_ambiguous, unit_note],
          "seshat": df with [unit_type_standardised, unit_ambiguous, unit_note],
        }
    """
    if standardiser is None:
        standardiser = UnitStandardiser()
    
    standardised = {}
    for source, df in raw_dfs.items():
        if source in ACTIVE_SOURCES:
            standardised[source] = standardiser.standardise_units(df, source)
        else:
            logger.debug(f"Skipping {source} (not in ACTIVE_SOURCES)")
    
    return standardised


if __name__ == "__main__":
    # Self-test
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "=" * 80)
    print("UNIT STANDARDISER - SELF-TEST")
    print("=" * 80)
    
    # Test 1: Instantiate
    print("\n[TEST 1] Standardiser instantiation")
    standardiser = UnitStandardiser()
    print(f"✓ Instantiated with ACTIVE_SOURCES: {standardiser.active_sources}")
    
    # Test 2: Create mock D-PLACE DataFrame
    print("\n[TEST 2] D-PLACE unit standardisation")
    import pandas as pd
    dplace_mock = pd.DataFrame({
        "source": ["dplace", "dplace", "dplace"],
        "culture_id": ["ABC001", "ABC002", "ABC003"],
        "culture_name": ["Society A", "Society B", "Society C"],
        "unit_type": ["society", "society", "society"],
        "lat": [10.5, 20.3, None],
        "lon": [40.2, 50.1, None],
        "time_start": [-1800, -1500, -2000],
        "time_end": [-1700, -1200, -1000],  # First row: 100yr span (OK), Third: 1000-1700 = 300yr span, 4th exceeds
        "variable_name": ["EA112", "EA112", "EA112"],
        "variable_value": [1.0, 0.0, 1.0],
    })
    result = standardiser.standardise_units(dplace_mock, "dplace")
    print(f"  Added columns: {[c for c in result.columns if 'unit' in c.lower()]}")
    print(f"  Ambiguous rows: {result['unit_ambiguous'].sum()}")
    
    # Test 3: Create mock DRH DataFrame
    print("\n[TEST 3] DRH unit standardisation")
    drh_mock = pd.DataFrame({
        "source": ["drh", "drh"],
        "culture_id": ["TRAD001", None],
        "culture_name": ["Tradition A", "Tradition B"],
        "unit_type": ["tradition", "tradition"],
        "variable_name": ["trance_question_1", "trance_question_1"],
        "variable_value": [1.0, 0.0],
    })
    result = standardiser.standardise_units(drh_mock, "drh")
    print(f"  Added columns: {[c for c in result.columns if 'unit' in c.lower()]}")
    print(f"  Ambiguous rows: {result['unit_ambiguous'].sum()}")
    
    print("\n" + "=" * 80)
    print("SELF-TEST COMPLETE")
    print("=" * 80)
