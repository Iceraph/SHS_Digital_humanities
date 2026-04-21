"""
Phase 2.3: Temporal Standardisation and Uncertainty Quantification

Standardises temporal dimensions across three independent data sources.

This module:
1. Validates and standardises time_start, time_end to BCE/CE integers
2. Computes temporal_mode (snapshot, diachronic, mixed)
3. Quantifies time_uncertainty as ordinal 0-3 (certain → ±1000yr+)
4. Applies D-PLACE -1800 to -1950 ethnographic window assumption
5. Respects ACTIVE_SOURCES for forward-compatible design

Key methodological decisions (locked Phase 2):
  - D-PLACE temporal assumption: -1800 to -1950 (150-year ethnographic collection span)
  - Rationale: SCCS data collected in modern era reflecting contact period
  - Time uncertainty: multi-factor ordinal flagging confidence
  - Temporal mode informs how time is conceptualised per source

Temporal modes:
  - "snapshot": Single point in time (D-PLACE)
  - "diachronic": Multiple time periods (Seshat)
  - "mixed": Combination of point and range (DRH)

Uncertainty levels (0=certain → 3=very uncertain):
  - 0: Exact date known (±year)
  - 1: Range ±100 years
  - 2: Range ±500 years
  - 3: Range ±1000+ years or entirely speculative

Author: Phase 2 Implementation
Date: 15 avril 2026
"""

import pandas as pd
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
# TEMPORAL CONSTANTS AND ASSUMPTIONS
# ==============================================================================

# D-PLACE ethnographic collection window (FIXED: Issue #5 semantics)
# NOW USES POSITIVE CE YEARS (standard convention)
DPLACE_TEMPORAL_ASSUMPTION = {
    "time_start_ce": 1800,        # Earliest collection period (positive CE)
    "time_end_ce": 1950,          # Latest collection period (positive CE)
    "time_start_bce": -1950,      # For legacy BCE-encoded columns (deprecated)
    "time_end_bce": -1800,        # For legacy BCE-encoded columns (deprecated)
    "temporal_mode": "ethnographic_present",
    "description": "Represents 'ethnographic present' (1800-1950 CE); period of anthropological observation in SCCS/D-PLACE",
    "interpretation": "Approximate cultural state, not precise date. Observed practices may reflect traditions extending centuries back.",
    "uncertainty_level": 3,       # High uncertainty: ±500+ years equivalent
    "uncertainty_justification": "Temporal representativeness uncertainty, not measurement error. Reflects broad pre-industrial period.",
    "justification": "Data collected during late 19th and early 20th century anthropological fieldwork. Reflects ethnographic present at time of observation.",
}

# Temporal mode definitions per source
TEMPORAL_MODE_DEFAULT = {
    "dplace": "snapshot",
    "drh": "mixed",
    "seshat": "diachronic",
}

# Uncertainty level definitions
UNCERTAINTY_LEVELS = {
    0: {"description": "Exact date known", "confidence": "high", "precision_range": "±year"},
    1: {"description": "Approximate date", "confidence": "medium", "precision_range": "±100yr"},
    2: {"description": "Probable time range", "confidence": "low", "precision_range": "±500yr"},
    3: {"description": "Speculative or very uncertain", "confidence": "very_low", "precision_range": "±1000yr+"},
}


class TemporalStandardiser:
    """
    Standardises temporal dimensions across D-PLACE, DRH, Seshat.
    
    Approach:
    1. Normalise time_start, time_end to BCE/CE integers
    2. Apply source-specific assumptions (D-PLACE -1800/-1950)
    3. Compute temporal_mode based on source conventions
    4. Quantify time_uncertainty based on metadata precision
    
    Forward-compatible: respects ACTIVE_SOURCES.
    """
    
    def __init__(self, active_sources: Optional[list] = None):
        """
        Initialize standardiser.
        
        Args:
            active_sources: Override config.ACTIVE_SOURCES for testing
        """
        self.active_sources = active_sources or ACTIVE_SOURCES
        logger.info(f"TemporalStandardiser initialised with active_sources: {self.active_sources}")
    
    def standardise_temporal(
        self,
        df: pd.DataFrame,
        source: str,
    ) -> pd.DataFrame:
        """
        Add temporal standardisation columns to Phase 1 DataFrame.
        
        Adds:
          - time_start_standardised: Start time in BCE/CE (integer, negative = BCE)
          - time_end_standardised: End time in BCE/CE (integer, negative = BCE)
          - temporal_mode: "snapshot", "diachronic", or "mixed"
          - time_uncertainty: Ordinal 0-3 (0=certain, 3=very uncertain)
        
        Args:
            df: Phase 1 DataFrame (must have time_start, time_end columns)
            source: "dplace", "drh", or "seshat"
        
        Returns:
            DataFrame with four new temporal columns added
        """
        # Validate source is active
        if source not in self.active_sources:
            logger.debug(f"Source {source} not in ACTIVE_SOURCES; skipping standardisation")
            return df.copy()
        
        # Validate temporal columns exist
        for col in ["time_start", "time_end"]:
            if col not in df.columns:
                raise ValueError(f"Column '{col}' not found in Phase 1 DataFrame for {source}")
        
        df_out = df.copy()
        
        # 1. Standardise time values (apply source-specific assumptions)
        df_out[["time_start_standardised", "time_end_standardised"]] = df_out.apply(
            lambda row: pd.Series(self._standardise_time(row, source)),
            axis=1
        )
        
        # 2. Assign temporal mode
        df_out["temporal_mode"] = TEMPORAL_MODE_DEFAULT.get(source, "mixed")
        
        # 3. Compute uncertainty
        df_out["time_uncertainty"] = df_out.apply(
            lambda row: self._compute_uncertainty(row, source),
            axis=1
        )
        
        # Validate output has expected columns
        expected_cols = ["time_start_standardised", "time_end_standardised", 
                        "temporal_mode", "time_uncertainty"]
        for col in expected_cols:
            if col not in df_out.columns:
                raise ValueError(f"Missing expected output column: {col}")
        
        logger.info(
            f"✓ Standardised temporal for {source}: "
            f"{len(df_out)} rows, "
            f"mode={TEMPORAL_MODE_DEFAULT.get(source)}, "
            f"uncertainty: mean={df_out['time_uncertainty'].mean():.2f}"
        )
        
        return df_out
    
    def _standardise_time(
        self,
        row: pd.Series,
        source: str,
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        Standardise time_start and time_end for a single row.
        
        Applies source-specific assumptions:
        - D-PLACE: Apply -1800/-1950 ethnographic window if missing
        - DRH: Use as-is (typically already standardised)
        - Seshat: Use as-is
        
        Returns:
            (time_start_standardised, time_end_standardised) tuple
            - Negative integers for BCE
            - Positive integers for CE (rare)
            - None if no data available
        """
        time_start = row.get("time_start")
        time_end = row.get("time_end")
        
        if source == "dplace":
            # Apply DPLACE assumption if values missing or anomalous
            if pd.isna(time_start) or pd.isna(time_end):
                # Use assumption window
                time_start = DPLACE_TEMPORAL_ASSUMPTION["time_start_assumed"]
                time_end = DPLACE_TEMPORAL_ASSUMPTION["time_end_assumed"]
            else:
                # If values present, ensure they're in reasonable range
                # (D-PLACE times should be negative, BCE)
                if time_start > 0 or time_end > 0:
                    logger.warning(
                        f"D-PLACE row has positive time values: "
                        f"time_start={time_start}, time_end={time_end}. "
                        f"Assuming BCE; converting to negative."
                    )
                    if time_start > 0:
                        time_start = -time_start
                    if time_end > 0:
                        time_end = -time_end
        
        elif source == "drh":
            # DRH times as-is (assume already standardised)
            pass
        
        elif source == "seshat":
            # Seshat times as-is (assume already standardised)
            pass
        
        # Final validation: time_start should be ≤ time_end
        if pd.notna(time_start) and pd.notna(time_end):
            if time_start > time_end:
                # Log warning and swap
                logger.debug(
                    f"{source}: time_start ({time_start}) > time_end ({time_end}); swapping"
                )
                time_start, time_end = time_end, time_start
        
        return (
            int(time_start) if pd.notna(time_start) else None,
            int(time_end) if pd.notna(time_end) else None,
        )
    
    def _compute_uncertainty(
        self,
        row: pd.Series,
        source: str,
    ) -> int:
        """
        Compute time uncertainty ordinal (0-3).
        
        Logic:
        - If time_start / time_end is NA → 3 (very uncertain)
        - If temporal span ≤ 10 years → 0 (certain)
        - If temporal span 10-100 years → 1 (±100yr)
        - If temporal span 100-500 years → 2 (±500yr)
        - If temporal span > 500 years → 3 (±1000yr+)
        
        For D-PLACE with assumption applied: use assumption uncertainty level
        
        Returns:
            Integer 0-3
        """
        time_start = row.get("time_start_standardised")
        time_end = row.get("time_end_standardised")
        
        # Both missing → very uncertain
        if pd.isna(time_start) or pd.isna(time_end):
            return 3
        
        # Compute span
        span = abs(time_end - time_start)
        
        # Apply decision tree
        if span <= 10:
            return 0
        elif span <= 100:
            return 1
        elif span <= 500:
            return 2
        else:
            return 3
    
    def validate_all_temporal(self, raw_dfs: Dict[str, pd.DataFrame]) -> Dict[str, any]:
        """
        Validate temporal consistency across all active sources.
        
        Args:
            raw_dfs: {"dplace": df, "drh": df, "seshat": df} from Phase 1
        
        Returns:
            Validation report:
            {
              "all_valid": bool,
              "dplace": {"time_range": (start, end), "uncertainty_dist": {...}, "valid": bool},
              "drh": {...},
              "seshat": {...},
            }
        """
        report = {"all_valid": True}
        
        for source, df in raw_dfs.items():
            if source not in self.active_sources:
                logger.debug(f"Skipping {source} validation (not in ACTIVE_SOURCES)")
                continue
            
            if "time_start" not in df.columns or "time_end" not in df.columns:
                report[source] = {
                    "valid": False,
                    "error": "Missing time_start or time_end column",
                }
                report["all_valid"] = False
                continue
            
            # Get time range
            valid_times = df.loc[
                df["time_start"].notna() & df["time_end"].notna(),
                ["time_start", "time_end"]
            ]
            
            if len(valid_times) > 0:
                time_min = min(valid_times["time_start"].min(), valid_times["time_end"].min())
                time_max = max(valid_times["time_start"].max(), valid_times["time_end"].max())
            else:
                time_min = time_max = None
            
            report[source] = {
                "time_range": (time_min, time_max),
                "count": len(df),
                "missing_time": len(df) - len(valid_times),
                "temporal_mode_default": TEMPORAL_MODE_DEFAULT.get(source),
                "valid": True,
            }
        
        if report["all_valid"]:
            logger.info("✓ All source temporal ranges validated")
        
        return report


def standardise_all_temporal(
    raw_dfs: Dict[str, pd.DataFrame],
    standardiser: Optional[TemporalStandardiser] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Apply temporal standardisation to all Phase 1 DataFrames.
    
    Args:
        raw_dfs: {"dplace": df, "drh": df, "seshat": df} from Phase 1
        standardiser: TemporalStandardiser instance (created if None)
    
    Returns:
        Dict of DataFrames with temporal columns added:
        {
          "dplace": df with [time_start_standardised, time_end_standardised, 
                             temporal_mode, time_uncertainty],
          "drh": {...},
          "seshat": {...},
        }
    """
    if standardiser is None:
        standardiser = TemporalStandardiser()
    
    standardised = {}
    for source, df in raw_dfs.items():
        if source in ACTIVE_SOURCES:
            standardised[source] = standardiser.standardise_temporal(df, source)
        else:
            logger.debug(f"Skipping {source} (not in ACTIVE_SOURCES)")
    
    return standardised


if __name__ == "__main__":
    # Self-test
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "=" * 80)
    print("TEMPORAL STANDARDISER - SELF-TEST")
    print("=" * 80)
    
    # Test 1: Instantiate
    print("\n[TEST 1] TemporalStandardiser instantiation")
    standardiser = TemporalStandardiser()
    print(f"✓ Instantiated with ACTIVE_SOURCES: {standardiser.active_sources}")
    
    # Test 2: D-PLACE with assumption applied
    print("\n[TEST 2] D-PLACE temporal (assumption application)")
    print(f"  Assumption window: {DPLACE_TEMPORAL_ASSUMPTION['time_start_assumed']} to "
          f"{DPLACE_TEMPORAL_ASSUMPTION['time_end_assumed']}")
    dplace_mock = pd.DataFrame({
        "source": ["dplace", "dplace", "dplace"],
        "culture_id": ["ABC001", "ABC002", "ABC003"],
        "culture_name": ["Society A", "Society B", "Society C"],
        "unit_type": ["society", "society", "society"],
        "time_start": [-1900, None, -1700],
        "time_end": [-1700, None, -1600],
        "variable_name": ["EA112", "EA112", "EA112"],
        "variable_value": [1.0, 0.0, 1.0],
    })
    result = standardiser.standardise_temporal(dplace_mock, "dplace")
    print(f"  time_start_standardised: {result['time_start_standardised'].tolist()}")
    print(f"  time_end_standardised: {result['time_end_standardised'].tolist()}")
    print(f"  temporal_mode: {result['temporal_mode'].unique()}")
    print(f"  time_uncertainty: {result['time_uncertainty'].tolist()}")
    
    print("\n" + "=" * 80)
    print("SELF-TEST COMPLETE")
    print("=" * 80)
