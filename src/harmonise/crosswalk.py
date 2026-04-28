"""
Phase 2.1: Crosswalk Definition and Variable Mapping

Maps raw source variables (D-PLACE, DRH, Seshat) to harmonised feature schema.

This module:
1. Loads embedded crosswalk mappings (Python dictionary)
2. Provides functions to map raw variables → feature names + binarised values
3. Tracks conflicts when sources disagree (logs to conflicts.csv)
4. Validates coverage: ensures all source variables are mapped
5. Respects ACTIVE_SOURCES configuration for forward-compatible design

Key decision: "any-source" validation threshold
  - If any source reports a feature present → code 1
  - If all sources say absent / missing → code 0 / NA
  - Log disagreements for transparency

Key design decision: ACTIVE_SOURCES forward-compatibility
  - All source-related logic checks: if source in ACTIVE_SOURCES
  - NEVER hardcode source exclusions
  - When Seshat becomes real, simply add "seshat" to ACTIVE_SOURCES in config.py
  - Zero code changes required in this module

Author: Phase 2 Implementation
Date: 15 avril 2026
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import logging

from .config import (
    ACTIVE_SOURCES,
    FEATURE_SCHEMA,
    HARMONISED_COLUMN_ORDER,
    DPLACE_RAW,
    DRH_RAW,
    SESHAT_RAW,
)

logger = logging.getLogger(__name__)

# ==============================================================================
# EMBEDDED CROSSWALK MAPPING (theory-driven, from PROJECT_CONTEXT.md Section 3)
# Forward-compatible: includes ALL sources, respects ACTIVE_SOURCES at runtime
# ==============================================================================
# Structure: feature_name -> {
#   "d_place": {"var_ids": ["EA112"], "include_codes": [1,2,3,4,5], "confidence": "high"},
#   "drh": {"columns": ["trance_question_1"], "confidence": "high"},
#   "seshat": {"var_names": ["spirit_possession"], "confidence": "high"},
#   "notes": "..."
# }

EMBEDDED_CROSSWALK = {
    # ========== ALTERED STATES OF CONSCIOUSNESS (3.1) ==========
    "trance_induction": {
        "d_place": {"var_ids": ["EA112"], "include_codes": [1,2,3,4,5], "confidence": "high"},
        "drh": {"columns": ["In trance possession:"], "confidence": "high"},
        "seshat": {},
        "notes": "EA112 codes 1-5 (trance induction phenomena). DRH Q4944/Q4861 trance possession. "
                 "SPLIT from spirit_possession (codes 6-8): different state types.",
    },
    "spirit_possession": {
        "d_place": {"var_ids": ["EA112"], "include_codes": [6,7,8], "confidence": "high"},
        "drh": {"columns": ["Is a spirit-body distinction present:", "Other spirit-body relationship:",
                            "Spirit distinct powers:", "Spirit non-material:"], "confidence": "high"},
        "seshat": {"var_names": ["spirit_possession"], "confidence": "high"},
        "notes": "EA112 codes 6-8 (spirit possession forms). DRH Q4776/Q4777/Q4778/Q4779 spirit-body distinction. "
                 "Seshat explicit spirit_possession. SPLIT from trance_induction (codes 1-5): different state types.",
    },
    "soul_flight": {
        "d_place": {"var_ids": ["SCCS1170"], "include_codes": [1], "confidence": "medium"},
        "drh": {"columns": ["Belief in afterlife:"], "confidence": "low"},
        "seshat": {"var_names": ["spirit_mediation"], "confidence": "medium"},
        "notes": "SCCS1170 shamanism index. Seshat spirit_mediation as proxy. "
                 "DRH Q4780 belief in afterlife as low-confidence proxy for soul concept.",
    },
    "entheogen_use": {
        "d_place": {"var_ids": ["WNAI390"], "include_codes": [1], "confidence": "high"},
        "drh": {},
        "seshat": {},
        "notes": "WNAI390 psychoactive substance use. Explicit code; D-PLACE only.",
    },
    
    # ========== SPECIALIST ROLE AND INITIATION (3.2) ==========
    "dedicated_specialist": {
        "d_place": {"var_ids": ["EA34"], "include_codes": [3,4,5], "confidence": "high"},
        "drh": {"columns": ["Physical healing"], "confidence": "high"},
        "seshat": {
            "var_names": ["professional_priesthood"],          # binary 0/1
            "var_codes": {"religious_level": [3,4,5,6,7,8,9,10]},  # ordinal ≥3 → 1
            "confidence": "high",
        },
        "notes": "EA34: 0/1/2→0 (part-time/none); 3/4/5→1 (full-time specialists). "
                 "Seshat professional_priesthood: binary 0/1. "
                 "Seshat religious_level: ordinal 0-10, threshold ≥3 → 1 (Murdock/Seshat coding). "
                 "Theory-driven threshold: shamanism requires full-time commitment.",
    },
    "initiatory_crisis": {
        "d_place": {"var_ids": ["SCCS580"], "include_codes": [1], "confidence": "high"},
        "drh": {},
        "seshat": {},
        "notes": "SCCS580 explicit initiation crisis marker. D-PLACE only; other sources NA.",
    },
    "hereditary_transmission": {
        "d_place": {"var_ids": ["SCCS673"], "include_codes": [1], "confidence": "high"},
        "drh": {},
        "seshat": {},
        "notes": "SCCS673 hereditary transmission of role. D-PLACE only; other sources NA.",
    },
    
    # ========== COSMOLOGY AND SPIRIT WORLD (3.3) ==========
    "layered_cosmology": {
        "d_place": {"var_ids": ["WNAI169", "WNAI381"], "include_codes": [1], "confidence": "medium"},
        "drh": {},
        "seshat": {},
        "notes": "WNAI codes for cosmological beliefs (multiple worlds, axis mundi). "
                 "D-PLACE only; other sources NA.",
    },
    "animal_transformation": {
        "d_place": {"var_ids": ["SCCS536"], "include_codes": [1], "confidence": "high"},
        "drh": {},
        "seshat": {},
        "notes": "SCCS536 animal transformation/shape-shifting. D-PLACE only; other sources NA.",
    },
    "ancestor_mediation": {
        "d_place": {"var_ids": ["SCCS530"], "include_codes": [1], "confidence": "high"},
        "drh": {},
        "seshat": {},
        "notes": "SCCS530 ancestor communication/channeling. D-PLACE only; DRH lacks direct ancestor column.",
    },
    "nature_spirits": {
        "d_place": {"var_ids": ["WNAI389", "WNAI391"], "include_codes": [1], "confidence": "medium"},
        "drh": {},
        "seshat": {"var_names": ["spirit_mediation"], "confidence": "low"},
        "notes": "WNAI codes for nature spirits. Seshat spirit_mediation as proxy (implicit). "
                 "Limited cross-source coverage.",
    },
    
    # ========== TECHNIQUE AND PERFORMANCE (3.4) ==========
    "rhythmic_percussion": {
        "d_place": {"var_ids": ["SCCS535"], "include_codes": [1], "confidence": "high"},
        "drh": {},
        "seshat": {},
        "notes": "SCCS535 rhythm/percussion central to practice. D-PLACE only; other sources NA.",
    },
    "healing_function": {
        "d_place": {"var_ids": ["EA34"], "include_codes": [3,4,5], "confidence": "high"},
        "drh": {"columns": ["Physical healing"], "confidence": "high"},
        "seshat": {},
        "notes": "EA34 specialist presence (proxy). DRH Q4776 Physical healing. Multi-source.",
    },
    "divination": {
        "d_place": {"var_ids": ["SCCS532"], "include_codes": [1], "confidence": "medium"},
        "drh": {"columns": ["Through divination practices:", "Through divination processes:"], "confidence": "high"},
        "seshat": {"var_names": ["divination"], "confidence": "high"},
        "notes": "Strong multi-source coverage: foretelling/hidden knowledge discovery.",
    },
    "public_performance": {
        "d_place": {"var_ids": ["SCCS1823"], "include_codes": [1], "confidence": "high"},
        "drh": {},
        "seshat": {},
        "notes": "SCCS1823 ritual performance before community. D-PLACE only; other sources NA.",
    },
    "chanting_singing": {
        "d_place": {"var_ids": ["SCCS654"], "include_codes": [1], "confidence": "high"},
        "drh": {},
        "seshat": {},
        "notes": "SCCS654 vocal techniques (icaros, singing, chanting). D-PLACE only; other sources NA.",
    },
    
    # ========== AUXILIARY / COMPOSITE FEATURES ==========
    "initiatory_ordeal": {
        "d_place": {"var_ids": ["SCCS1172", "SCCS1173", "SCCS1949", "SCCS1962"], 
                    "include_codes": [1], "confidence": "medium"},
        "drh": {},
        "seshat": {},
        "notes": "SCCS codes for initiation rites, trials, ordeals. D-PLACE only; other sources NA.",
    },
    "possession_crisis": {
        "d_place": {"var_ids": ["SCCS1171"], "include_codes": [1], "confidence": "medium"},
        "drh": {},
        "seshat": {},
        "notes": "SCCS1171 shamanism crisis/possession events. D-PLACE only; other sources NA.",
    },
    "ritual_performance": {
        "d_place": {"var_ids": ["SCCS1170", "SCCS573", "SCCS576", "SCCS580", "SCCS623"], 
                    "include_codes": [1], "confidence": "medium"},
        "drh": {},
        "seshat": {},
        "notes": "SCCS codes for shamanism rituals, trance rituals, shaman social role. "
                 "D-PLACE only; other sources NA.",
    },
    "specialist_presence": {
        "d_place": {"var_ids": ["SCCS200", "WNAI392", "WNAI393"], 
                    "include_codes": [1, 2, 3], "confidence": "medium"},
        "drh": {},
        "seshat": {},
        "notes": "SCCS/WNAI codes for religious specialist presence, shaman role. "
                 "D-PLACE only; other sources NA.",
    },
    "unmapped_shamanic_indicators": {
        "d_place": {
            "var_ids": ["CARNEIRO4_182", "CARNEIRO4_276", "CARNEIRO6_319", "CARNEIRO6_450",
                       "CARNEIRO6_469", "CARNEIRO6_477", "CARNEIRO6_478", "CARNEIRO6_481",
                       "WNAI394", "WNAI395", "WNAI396", "WNAI397", "WNAI398", "WNAI399",
                       "WNAI408", "WNAI409", "WNAI410", "WNAI411", "WNAI412", "WNAI413",
                       "WNAI414", "WNAI416", "WNAI418", "WNAI422", "WNAI423", "WNAI424",
                       "WNAI425", "SCCS1838", "SCCS1948", "SCCS529", "SCCS531", "SCCS633",
                       "SCCS635", "SCCS653", "SCCS674", "SCCS694", "SCCS792", "SCCS905"],
            "include_codes": [1], "confidence": "low"},
        "drh": {},
        "seshat": {},
        "notes": "Residual CARNEIRO/WNAI/SCCS codes that map loosely to shamanism-related presence. "
                 "Low signal; kept to preserve data. Considered 'meta' features.",
    },

    # ========== SESHAT-SPECIFIC FEATURES ==========
    "moralizing_supernatural": {
        "d_place": {},
        "drh": {},
        "seshat": {
            "var_names": ["moralizing_supernatural", "moralizing_agentic"],
            "confidence": "high",
        },
        "notes": "Seshat moralizing_supernatural + moralizing_agentic: binary 0/1. "
                 "Presence of supernatural beings with moral concerns. "
                 "Any-source rule: if either variable = 1 → feature = 1. "
                 "Theoretically relevant: high moralizing religion may crowd out shamanism.",
    },
}


class CrosswalkMapper:
    """
    Maps raw source variables to harmonised features via embedded crosswalk.
    
    Forward-compatible design: respects ACTIVE_SOURCES parameter.
    - All source validation checks: if source in ACTIVE_SOURCES
    - When Seshat added to config.ACTIVE_SOURCES, coverage automatically recomputes
    - Zero code refactoring required
    
    Example:
        mapper = CrosswalkMapper()
        feature_name, harmonised_value = mapper.map_variable(
            source="dplace",
            variable_name="EA112",
            variable_value=1.0
        )
        # Returns: ("trance_induction", 1.0) if EA112=1 is in trance_induction codes
    """

    def __init__(self, active_sources: Optional[List[str]] = None):
        """
        Initialize mapper by setting up lookup tables from embedded crosswalk.
        
        Args:
            active_sources: Optionally override config.ACTIVE_SOURCES for testing
                          Default: uses ACTIVE_SOURCES from config
        """
        self.active_sources = active_sources or ACTIVE_SOURCES
        self.embedded_crosswalk = EMBEDDED_CROSSWALK
        self._build_lookup_tables()
        self.conflicts: List[Dict] = []  # Track conflicts for later logging
        
        logger.debug(f"CrosswalkMapper initialised with active_sources: {self.active_sources}")
        
    def _build_lookup_tables(self) -> None:
        """
        Build fast lookup tables: source var → feature name + binarisation rule.
        
        Respects ACTIVE_SOURCES: only builds lookups for active sources.
        
        Special handling: D-PLACE vars may map to MULTIPLE features (EA112 dual mapping).
        Store list of features per var_id to handle code ranges.
        
        Creates up to three lookup dicts:
          - dplace_lookup: {"EA112": [{"feature": "trance_induction", "codes": [1,2,3,4,5]}, 
                                       {"feature": "spirit_possession", "codes": [6,7,8]}]}
          - drh_lookup: {"trance_question_1": {"feature": "trance_induction", ...}}
          - seshat_lookup: {"spirit_possession": {"feature": "spirit_possession", ...}}
        """
        self.dplace_lookup: Dict[str, List[Dict]] = {}  # Multiple features per var
        self.drh_lookup: Dict[str, Dict] = {}
        self.seshat_lookup: Dict[str, Dict] = {}
        
        for feature, sources in self.embedded_crosswalk.items():
            # D-PLACE variables (only if "dplace" in ACTIVE_SOURCES)
            if "dplace" in self.active_sources and sources.get("d_place"):
                for var_id in sources["d_place"].get("var_ids", []):
                    entry = {
                        "feature": feature,
                        "include_codes": sources["d_place"].get("include_codes", []),
                        "confidence": sources["d_place"].get("confidence", "medium"),
                        "notes": sources.get("notes", ""),
                    }
                    if var_id not in self.dplace_lookup:
                        self.dplace_lookup[var_id] = []
                    self.dplace_lookup[var_id].append(entry)
            
            # DRH variables (only if "drh" in ACTIVE_SOURCES)
            if "drh" in self.active_sources and sources.get("drh"):
                for col_name in sources["drh"].get("columns", []):
                    self.drh_lookup[col_name] = {
                        "feature": feature,
                        "confidence": sources["drh"].get("confidence", "medium"),
                        "notes": sources.get("notes", ""),
                    }
            
            # Seshat variables (only if "seshat" in ACTIVE_SOURCES)
            if "seshat" in self.active_sources and sources.get("seshat"):
                seshat_def = sources["seshat"]
                base_entry = {
                    "feature": feature,
                    "include_codes": None,   # None = binary passthrough (0/1)
                    "confidence": seshat_def.get("confidence", "medium"),
                    "notes": sources.get("notes", ""),
                }
                # Binary variables (0/1 passthrough)
                for var_name in seshat_def.get("var_names", []):
                    self.seshat_lookup[var_name] = dict(base_entry)
                # Ordinal variables with explicit include_codes
                for var_name, codes in seshat_def.get("var_codes", {}).items():
                    entry = dict(base_entry)
                    entry["include_codes"] = codes
                    self.seshat_lookup[var_name] = entry
        
        logger.info(
            f"✓ Built lookup tables (active_sources={self.active_sources}): "
            f"{len(self.dplace_lookup)} D-PLACE vars, "
            f"{len(self.drh_lookup)} DRH vars, "
            f"{len(self.seshat_lookup)} Seshat vars mapped"
        )
    
    def map_variable(
        self,
        source: str,
        variable_name: str,
        variable_value: Optional[float],
    ) -> Tuple[Optional[str], Optional[float]]:
        """
        Map a raw source variable to harmonised feature + binarised value.
        
        Args:
            source: "dplace", "drh", or "seshat"
            variable_name: Raw variable name from source
            variable_value: Raw value from source (may be NA/None/NaN)
        
        Returns:
            (feature_name, harmonised_value) tuple
            - feature_name: Name of harmonised feature, or None if unmapped
            - harmonised_value: Binarised value (0.0, 1.0) or None (NA)
            
        Notes:
            - NA / None / NaN input → (feature, None) output
            - Returns (None, None) if variable is unmapped (error condition)
            - Respects ACTIVE_SOURCES: only maps if source in active_sources
        """
        # Validate source is active
        if source not in self.active_sources:
            logger.debug(f"Source {source} not in ACTIVE_SOURCES; skipping map_variable")
            return (None, None)
        
        # Missing input → feature present but value is NA
        if pd.isna(variable_value):
            feature = self._get_feature_for_variable(source, variable_name)
            return (feature, None)
        
        if source == "dplace":
            return self._map_dplace(variable_name, variable_value)
        elif source == "drh":
            return self._map_drh(variable_name, variable_value)
        elif source == "seshat":
            return self._map_seshat(variable_name, variable_value)
        else:
            raise ValueError(f"Unknown source: {source}")
    
    def _map_dplace(self, var_name: str, value: float) -> Tuple[Optional[str], Optional[float]]:
        """
        Map D-PLACE variable using include_codes logic.
        
        Handles dual mappings (e.g., EA112 → trance_induction OR spirit_possession).
        
        Binarisation logic:
        - Check each feature mapping for this var_id
        - If value in any feature's include_codes → match that feature with 1.0
        - If value == 99 (D-PLACE NA placeholder) → return first feature with None value
        - Otherwise → return first feature with 0.0
        """
        if var_name not in self.dplace_lookup:
            logger.warning(f"Unmapped D-PLACE variable: {var_name}")
            return (None, None)
        
        # Multiple features may map to this variable (e.g., EA112)
        entries = self.dplace_lookup[var_name]
        
        if value == 99:  # D-PLACE NA placeholder
            # Return first feature with NA value
            return (entries[0]["feature"], None)
        
        # Check each feature's include_codes
        for entry in entries:
            include_codes = entry["include_codes"]
            if value in include_codes:
                return (entry["feature"], 1.0)
        
        # Value not in any include_codes → 0.0 for first feature
        return (entries[0]["feature"], 0.0)
    
    def _map_drh(self, var_name: str, value: float) -> Tuple[Optional[str], Optional[float]]:
        """
        Map DRH variable (typically binary: 0 = no, 1 = yes, NA = uncertain).
        """
        if var_name not in self.drh_lookup:
            logger.warning(f"Unmapped DRH variable: {var_name}")
            return (None, None)
        
        entry = self.drh_lookup[var_name]
        feature = entry["feature"]
        
        # DRH binarisation: typically already binary 0/1
        if value in [0.0, 1.0]:
            harmonised_value = value
        else:
            logger.warning(
                f"Unexpected DRH value for {var_name}: {value}. "
                f"Expected 0.0 or 1.0. Treating as NA."
            )
            harmonised_value = None
        
        return (feature, harmonised_value)
    
    def _map_seshat(self, var_name: str, value: float) -> Tuple[Optional[str], Optional[float]]:
        """
        Map Seshat variable.

        Two modes depending on how the variable was registered:
        - Binary passthrough (include_codes=None): restrict to 0/1.
        - Code-based binarisation (include_codes=[...]): 1.0 if value in codes, else 0.0.
          Used for ordinal variables like religious_level (threshold ≥3).
        """
        if var_name not in self.seshat_lookup:
            logger.warning(f"Unmapped Seshat variable: {var_name}")
            return (None, None)

        entry = self.seshat_lookup[var_name]
        feature = entry["feature"]
        include_codes = entry.get("include_codes")

        if include_codes is not None:
            # Ordinal variable: code-based binarisation
            harmonised_value = 1.0 if value in include_codes else 0.0
        else:
            # Binary passthrough: only accept 0/1
            if value in [0.0, 1.0]:
                harmonised_value = value
            else:
                logger.warning(
                    f"Unexpected Seshat value for {var_name}: {value}. "
                    f"Expected 0.0 or 1.0. Treating as NA."
                )
                harmonised_value = None

        return (feature, harmonised_value)
    
    def _get_feature_for_variable(self, source: str, variable_name: str) -> Optional[str]:
        """
        Get feature name for a variable without binarising value.
        
        For D-PLACE vars with multiple mappings (e.g., EA112), returns first feature.
        """
        if source == "dplace":
            if variable_name in self.dplace_lookup:
                # D-PLACE lookup returns list; get first entry's feature
                entries = self.dplace_lookup[variable_name]
                return entries[0]["feature"] if entries else None
            return None
        elif source == "drh" and variable_name in self.drh_lookup:
            return self.drh_lookup[variable_name]["feature"]
        elif source == "seshat" and variable_name in self.seshat_lookup:
            return self.seshat_lookup[variable_name]["feature"]
        else:
            return None
    
    def validate_coverage(self, raw_dfs: Dict[str, pd.DataFrame]) -> Dict[str, List[str]]:
        """
        Validate that all source variables are mapped in crosswalk.
        
        Respects ACTIVE_SOURCES: only validates sources in active_sources.
        
        Args:
            raw_dfs: {"dplace": df, "drh": df, "seshat": df} from Phase 1
        
        Returns:
            Dictionary of unmapped variables per source:
            {
              "dplace": ["UNKNOWN_VAR1", "UNKNOWN_VAR2"],
              "drh": [],
              "seshat": []
            }
            
        Note: Empty lists for inactive sources indicate they were skipped, not complete coverage.
        """
        unmapped = {"dplace": [], "drh": [], "seshat": []}
        
        for source, df in raw_dfs.items():
            # Only validate active sources
            if source not in self.active_sources:
                logger.debug(f"Skipping coverage validation for {source} (not in ACTIVE_SOURCES)")
                continue
            
            unique_vars = df["variable_name"].unique()
            
            for var in unique_vars:
                if source == "dplace":
                    if var not in self.dplace_lookup:
                        unmapped["dplace"].append(var)
                elif source == "drh":
                    if var not in self.drh_lookup:
                        unmapped["drh"].append(var)
                elif source == "seshat":
                    if var not in self.seshat_lookup:
                        unmapped["seshat"].append(var)
        
        # Report only for active sources
        active_unmapped = {k: v for k, v in unmapped.items() if k in self.active_sources}
        
        if any(active_unmapped.values()):
            logger.warning(
                f"⚠ Unmapped variables found in ACTIVE_SOURCES:\n"
                f"  D-PLACE: {len(unmapped['dplace'])} unmapped\n"
                f"  DRH: {len(unmapped['drh'])} unmapped\n"
                f"  Seshat: {len(unmapped['seshat'])} unmapped"
            )
        else:
            logger.info("✓ All source variables in ACTIVE_SOURCES are mapped in crosswalk")
        
        return unmapped
    
    def get_crosswalk_summary(self) -> Dict:
        """Return the embedded crosswalk dictionary for inspection."""
        return self.embedded_crosswalk.copy()


def apply_crosswalk(
    raw_df: pd.DataFrame,
    source: str,
    mapper: Optional[CrosswalkMapper] = None,
) -> pd.DataFrame:
    """
    Apply crosswalk mapping to a Phase 1 raw DataFrame.
    
    Adds columns:
      - feature_name: Harmonised feature (from crosswalk mapping)
      - feature_value: Binarised feature value (0.0, 1.0, or None/NA)
    
    Args:
        raw_df: Phase 1 output DataFrame (dplace_real.parquet, drh_raw.parquet, etc.)
        source: "dplace", "drh", or "seshat"
        mapper: CrosswalkMapper instance (created if None, uses default ACTIVE_SOURCES)
    
    Returns:
        DataFrame with added feature_name + feature_value columns
    """
    if mapper is None:
        mapper = CrosswalkMapper()
    
    # Apply mapping row-by-row
    def map_row(row: pd.Series) -> Tuple[Optional[str], Optional[float]]:
        return mapper.map_variable(
            source=source,
            variable_name=row["variable_name"],
            variable_value=row["variable_value"],
        )
    
    # Vectorise mapping (map each row)
    mapped = raw_df.apply(map_row, axis=1, result_type="expand")
    mapped.columns = ["feature_name", "feature_value"]
    
    return pd.concat([raw_df, mapped], axis=1)


if __name__ == "__main__":
    # Self-test
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "=" * 80)
    print("CROSSWALK MODULE - SELF-TEST")
    print("=" * 80)
    
    # Test 1: Default mapper (uses config.ACTIVE_SOURCES)
    print(f"\n[TEST 1] Default mapper (ACTIVE_SOURCES={ACTIVE_SOURCES})")
    mapper = CrosswalkMapper()
    print(f"✓ Embedded crosswalk loaded: {len(EMBEDDED_CROSSWALK)} features")
    print(f"✓ D-PLACE lookups: {len(mapper.dplace_lookup)}")
    print(f"✓ DRH lookups: {len(mapper.drh_lookup)}")
    print(f"✓ Seshat lookups: {len(mapper.seshat_lookup)}")
    
    # Test 2: EA112 dual mapping (split: 1-5→trance, 6-8→possession)
    print("\n[TEST 2] EA112 dual mapping (codes 1-5 vs 6-8)")
    mappings = [
        ("dplace", "EA112", 1.0),  # → trance_induction
        ("dplace", "EA112", 5.0),  # → trance_induction
        ("dplace", "EA112", 6.0),  # → spirit_possession
        ("dplace", "EA112", 8.0),  # → spirit_possession
        ("dplace", "EA112", 0.0),  # → 0 (unmapped code)
        ("dplace", "EA112", 99.0),  # → NA
    ]
    for source, var, val in mappings:
        feature, harmonised = mapper.map_variable(source, var, val)
        print(f"  EA112={val:1.0f} → ({feature}, {harmonised})")
    
    # Test 3: DRH removal of spirit_question (should be unmapped now)
    print("\n[TEST 3] DRH mapping (spirit_question removal check)")
    try:
        feature, harmonised = mapper.map_variable("drh", "spirit_question_1", 1.0)
        if feature is None:
            print(f"  ✓ spirit_question_1 correctly unmapped (removed per decision)")
        else:
            print(f"  ✗ WARNING: spirit_question_1 still mapped to {feature}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Test 4: Other DRH mappings (trance, divination, etc.)
    print("\n[TEST 4] DRH correct mappings (trance, divination, healing, ancestor)")
    drh_tests = [
        ("trance_question_1", 1.0),
        ("divination_question_1", 1.0),
        ("healing_question_1", 1.0),
        ("ancestor_question_1", 1.0),
    ]
    for var, val in drh_tests:
        feature, harmonised = mapper.map_variable("drh", var, val)
        print(f"  {var}={val:1.0f} → {feature}")
    
    # Test 5: Seshat mapping (spirit_possession should work)
    print("\n[TEST 5] Seshat mapping")
    seshat_tests = [
        ("spirit_possession", 1.0),
        ("divination", 1.0),
    ]
    for var, val in seshat_tests:
        feature, harmonised = mapper.map_variable("seshat", var, val)
        print(f"  {var}={val:1.0f} → {feature}")
    
    print("\n" + "=" * 80)
    print("SELF-TEST COMPLETE")
    print("=" * 80)
