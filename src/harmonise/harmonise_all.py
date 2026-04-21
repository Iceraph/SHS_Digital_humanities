"""
Harmonisation Assembly Script
================================

Orchestrates the complete data harmonisation pipeline:
1. Load Phase 1 parquets (raw ingested data)
2. Apply crosswalk mapping (variables → features)
3. Standardise units & flag ambiguity
4. Standardise temporal dimensions
5. Apply binarisation rules & compute data quality
6. Audit space-time coverage
7. Output 3 harmonised parquets (one per source) + auxiliary files

All outputs follow unified 18-column schema ensuring consistency across sources.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, Tuple
import sys
from pathlib import Path as PathlibPath

# Add workspace to path
workspace_root = PathlibPath(__file__).parent.parent.parent
sys.path.insert(0, str(workspace_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)

# Import harmonisation modules
from src.harmonise.config import (
    DPLACE_RAW, DRH_RAW, SESHAT_RAW,
    DPLACE_HARMONISED, DRH_HARMONISED, SESHAT_HARMONISED,
    HARMONISED_SCHEMA, HARMONISED_COLUMN_ORDER, ACTIVE_SOURCES
)
from src.harmonise.crosswalk import CrosswalkMapper, apply_crosswalk
from src.harmonise.units import UnitStandardiser
from src.harmonise.temporal import TemporalStandardiser
from src.harmonise.scale import ScaleStandardiser
from src.harmonise.coverage import CoverageAuditor


class HarmonisationPipeline:
    """Orchestrates complete harmonisation workflow."""
    
    def __init__(self):
        """Initialise pipeline components."""
        self.crosswalk = CrosswalkMapper()
        self.units = UnitStandardiser()
        self.temporal = TemporalStandardiser()
        self.scale = ScaleStandardiser()
        self.coverage = CoverageAuditor()
        
        self.phase1_data = {}
        self.harmonised_data = {}
        self.coverage_audit = None
        
        logger.info(f"Pipeline initialised | ACTIVE_SOURCES: {ACTIVE_SOURCES}")
    
    def load_phase1_data(self) -> Dict[str, pd.DataFrame]:
        """Load Phase 1 parquet files."""
        logger.info("=" * 80)
        logger.info("PHASE 1: LOAD RAW DATA")
        logger.info("=" * 80)
        
        data = {}
        
        # Load D-PLACE
        if "dplace" in ACTIVE_SOURCES:
            dplace_path = Path(DPLACE_RAW)
            if dplace_path.exists():
                data["dplace"] = pd.read_parquet(dplace_path)
                logger.info(f"✓ Loaded D-PLACE: {len(data['dplace'])} rows, {len(data['dplace'].columns)} columns")
            else:
                logger.warning(f"✗ D-PLACE file not found: {dplace_path}")
        
        # Load DRH
        if "drh" in ACTIVE_SOURCES:
            drh_path = Path(DRH_RAW)
            if drh_path.exists():
                data["drh"] = pd.read_parquet(drh_path)
                logger.info(f"✓ Loaded DRH: {len(data['drh'])} rows, {len(data['drh'].columns)} columns")
            else:
                logger.warning(f"✗ DRH file not found: {drh_path}")
        
        # Load Seshat (if active in future)
        if "seshat" in ACTIVE_SOURCES:
            seshat_path = Path(SESHAT_RAW)
            if seshat_path.exists():
                data["seshat"] = pd.read_parquet(seshat_path)
                logger.info(f"✓ Loaded Seshat: {len(data['seshat'])} rows, {len(data['seshat'].columns)} columns")
            else:
                logger.warning(f"✗ Seshat file not found: {seshat_path}")
        
        self.phase1_data = data
        return data
    
    def harmonise_source(self, source_name: str, df: pd.DataFrame) -> pd.DataFrame:
        """Apply harmonisation steps 1-3 to a single source."""
        logger.info(f"\n{'='*80}")
        logger.info(f"HARMONISING: {source_name.upper()}")
        logger.info(f"{'='*80}")
        logger.info(f"Input rows: {len(df)}")
        
        # Step 1: Crosswalk mapping
        logger.info("\n[1/3] Crosswalk: mapping variables → features")
        df = apply_crosswalk(df, source_name, self.crosswalk)
        logger.info(f"  ✓ Added columns: feature_name, feature_value")
        
        # Step 2: Units standardisation
        logger.info("\n[2/3] Units: standardise unit-of-observation")
        df = self.units.standardise_units(df, source_name)
        logger.info(f"  ✓ Added columns: unit_type_standardised, unit_ambiguous, unit_note")
        
        # Step 3: Temporal standardisation
        logger.info("\n[3/3] Temporal: standardise time dimensions")
        df = self.temporal.standardise_temporal(df, source_name)
        logger.info(f"  ✓ Added columns: time_start_standardised, time_end_standardised,")
        logger.info(f"                    temporal_mode, time_uncertainty")
        logger.info(f"  ✓ Output rows: {len(df)}")
        
        return df
    
    def _enforce_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enforce unified 18-column schema."""
        # Check all expected columns present
        missing_cols = set(HARMONISED_COLUMN_ORDER) - set(df.columns)
        if missing_cols:
            logger.error(f"✗ Missing columns: {missing_cols}")
            raise ValueError(f"Schema mismatch - missing: {missing_cols}")
        
        # Reorder to match schema
        df = df[HARMONISED_COLUMN_ORDER]
        
        # Add dtypes to match schema
        for col_name in HARMONISED_COLUMN_ORDER:
            expected_type = HARMONISED_SCHEMA.get(col_name, "object")
            
            if expected_type == "int" and df[col_name].isna().any():
                # Integer columns with NAs -> convert to Float
                df[col_name] = df[col_name].astype("float64")
            elif expected_type in ["bool", "int", "float"]:
                try:
                    type_map = {"bool": "bool", "int": "int64", "float": "float64", "str": "object"}
                    df[col_name] = df[col_name].astype(type_map[expected_type])
                except Exception as e:
                    logger.warning(f"  Could not convert {col_name} to {expected_type}: {e}")
        
        return df
    
    def run(self) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame]:
        """Execute full harmonisation pipeline."""
        logger.info("\n\n")
        logger.info("╔" + "="*78 + "╗")
        logger.info("║" + " "*78 + "║")
        logger.info("║" + "DATA HARMONISATION PIPELINE - FULL EXECUTION".center(78) + "║")
        logger.info("║" + " "*78 + "║")
        logger.info("╚" + "="*78 + "╝")
        
        # Load Phase 1
        try:
            phase1_data = self.load_phase1_data()
        except Exception as e:
            logger.error(f"Failed to load Phase 1 data: {e}")
            raise
        
        # Harmonise each source (steps 1-3)
        self.harmonised_data = {}
        for source_name, df in phase1_data.items():
            try:
                self.harmonised_data[source_name] = self.harmonise_source(source_name, df)
            except Exception as e:
                logger.error(f"Failed to harmonise {source_name}: {e}")
                raise
        
        # Step 4: Scale & binarisation (all sources at once)
        logger.info(f"\n{'='*80}")
        logger.info(f"SCALE & BINARISATION (all sources)")
        logger.info(f"{'='*80}")
        self.harmonised_data = self.scale.apply_binarisation_and_score(
            self.harmonised_data, 
            self.crosswalk
        )
        for source_name in self.harmonised_data:
            logger.info(f"  ✓ {source_name}: Added feature_value_binarised, data_quality_score")
        
        # Step 5: Coverage audit (all sources at once)
        logger.info(f"\n{'='*80}")
        logger.info(f"COVERAGE AUDIT (all sources)")
        logger.info(f"{'='*80}")
        self.coverage_audit = self.coverage.audit_coverage(self.harmonised_data)
        logger.info(f"✓ Coverage audit completed: {len(self.coverage_audit)} region×time×source cells")
        
        # Step 6: Enforce schema
        logger.info(f"\n{'='*80}")
        logger.info(f"ENFORCE SCHEMA (18-column unified output)")
        logger.info(f"{'='*80}")
        for source_name in self.harmonised_data:
            self.harmonised_data[source_name] = self._enforce_schema(
                self.harmonised_data[source_name]
            )
            logger.info(f"  ✓ {source_name}: {len(self.harmonised_data[source_name].columns)} columns")
        
        # Save outputs
        logger.info(f"\n{'='*80}")
        logger.info(f"SAVE OUTPUTS")
        logger.info(f"{'='*80}")
        self._save_outputs()
        
        logger.info("\n" + "╔" + "="*78 + "╗")
        logger.info("║" + " "*78 + "║")
        logger.info("║" + "✓ HARMONISATION COMPLETE".center(78) + "║")
        logger.info("║" + " "*78 + "║")
        logger.info("╚" + "="*78 + "╝\n")
        
        return self.harmonised_data, self.coverage_audit
    
    def _save_outputs(self):
        """Save harmonised parquets and auxiliary files."""
        output_mapping = {
            "dplace": DPLACE_HARMONISED,
            "drh": DRH_HARMONISED,
            "seshat": SESHAT_HARMONISED,
        }
        
        for source_name, df in self.harmonised_data.items():
            output_path = Path(output_mapping[source_name])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            df.to_parquet(output_path)
            logger.info(f"✓ Saved {source_name}: {output_path}")
        
        # Save coverage audit
        if self.coverage_audit is not None:
            coverage_path = Path("data/processed/harmonised/coverage_audit.csv")
            coverage_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.coverage_audit.to_csv(coverage_path, index=False)
            logger.info(f"✓ Saved coverage audit: {coverage_path}")


def main():
    """Entry point."""
    pipeline = HarmonisationPipeline()
    
    try:
        harmonised_data, coverage_audit = pipeline.run()
        
        # Print final summary
        logger.info("\n" + "="*80)
        logger.info("SUMMARY")
        logger.info("="*80)
        for source_name, df in harmonised_data.items():
            logger.info(f"  {source_name:10s}: {len(df):6d} rows × {len(df.columns):2d} columns")
        logger.info(f"  coverage:  {len(coverage_audit)} cells audited")
        
        return 0
    
    except Exception as e:
        logger.error(f"\n✗ Pipeline failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
