"""
Phase 2.5: Coverage Audit and Gap Detection

Audits space-time coverage and flags data gaps.

This module:
1. Creates region x time_bin x source matrix
2. Counts records per cell
3. Flags gaps: < 5 records/cell = high severity
4. Generates coverage_audit.csv with gap analysis
5. Computes coverage statistics per region/time/source
6. Respects ACTIVE_SOURCES for forward-compatible design

Key methodological decision:
  - Time bins: 500 years (locked in Phase 2)
  - Gap threshold: < 5 records per region/time_bin
  - Rationale: Conservative threshold flags undersampled space-times

Gap severity:
  - Green: >= 5 records (adequate)
  - Yellow: 2-4 records (limited)
  - Red: < 2 records (concerning)

Author: Phase 2 Implementation
Date: 15 avril 2026
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, List
import logging
from pathlib import Path

from .config import (
    ACTIVE_SOURCES,
    PROJECT_ROOT,
    DATA_PROCESSED,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# COVERAGE AUDIT CONSTANTS
# ==============================================================================

TIME_BIN_WIDTH = 500  # years (locked decision)
GAP_THRESHOLD = 5  # records per cell (locked decision)

# Natural Earth regions (simplified for Phase 2)
WORLD_REGIONS = {
    "Africa": {"lat_range": (-40, 40), "lon_range": (-20, 60)},
    "Asia-Pacific": {"lat_range": (-55, 50), "lon_range": (60, 180)},
    "Europe": {"lat_range": (35, 70), "lon_range": (-15, 50)},
    "Americas": {"lat_range": (-55, 75), "lon_range": (-170, -30)},
    "Other": {"lat_range": (-90, 90), "lon_range": (-180, 180)},  # Fallback
}


class CoverageAuditor:
    """
    Audits space-time coverage of harmonised dataset.
    
    Generates coverage_audit.csv showing:
    - region, time_bin, source
    - record_count, gap_severity, data_quality_mean
    
    Forward-compatible: respects ACTIVE_SOURCES.
    """
    
    def __init__(self, active_sources: Optional[list] = None):
        """
        Initialize auditor.
        
        Args:
            active_sources: Override config.ACTIVE_SOURCES for testing
        """
        self.active_sources = active_sources or ACTIVE_SOURCES
        self.time_bin_width = TIME_BIN_WIDTH
        self.gap_threshold = GAP_THRESHOLD
        logger.info(
            f"CoverageAuditor initialised: "
            f"active_sources={self.active_sources}, "
            f"time_bin_width={self.time_bin_width}, "
            f"gap_threshold={self.gap_threshold}"
        )
    
    def audit_coverage(
        self,
        df_dict: Dict[str, pd.DataFrame],
    ) -> pd.DataFrame:
        """
        Audit space-time coverage across all sources.
        
        Args:
            df_dict: {"dplace": df, "drh": df, "seshat": df} with columns:
                    lat, lon, time_start_standardised, source, data_quality_score
        
        Returns:
            DataFrame with coverage audit:
            - region, time_bin, source, record_count, gap_severity, data_quality_mean
        """
        audit_rows = []
        
        for source, df in df_dict.items():
            if source not in self.active_sources:
                logger.debug(f"Skipping {source} (not in ACTIVE_SOURCES)")
                continue
            
            # Validate required columns
            for col in ["lat", "lon", "time_start_standardised", "data_quality_score"]:
                if col not in df.columns:
                    logger.warning(f"Missing column '{col}' in {source}; skipping coverage audit")
                    continue
            
            # Remove rows with missing location/time
            df_valid = df.dropna(subset=["lat", "lon", "time_start_standardised"])
            
            # Compute bins
            df_valid = df_valid.copy()
            df_valid["region"] = df_valid.apply(
                lambda row: self._assign_region(row["lat"], row["lon"]),
                axis=1
            )
            df_valid["time_bin"] = df_valid["time_start_standardised"].apply(
                self._compute_time_bin
            )
            
            # Group by region x time_bin x source
            grouped = df_valid.groupby(["region", "time_bin"], as_index=False).agg({
                "lat": "count",  # Record count
                "data_quality_score": "mean",
            }).rename(columns={
                "lat": "record_count",
                "data_quality_score": "data_quality_mean",
            })
            
            grouped["source"] = source
            grouped["gap_severity"] = grouped["record_count"].apply(self._classify_gap_severity)
            
            audit_rows.append(grouped)
        
        if audit_rows:
            audit_df = pd.concat(audit_rows, ignore_index=True)
        else:
            audit_df = pd.DataFrame()
        
        logger.info(
            f"✓ Coverage audit complete: {len(audit_df)} region x time_bin cells, "
            f"{(audit_df['gap_severity'] == 'RED').sum()} gaps"
        )
        
        return audit_df
    
    def _assign_region(self, lat: float, lon: float) -> str:
        """
        Assign geographic region based on lat/lon.
        
        Returns:
            Region name from WORLD_REGIONS
        """
        for region, bounds in WORLD_REGIONS.items():
            lat_range = bounds["lat_range"]
            lon_range = bounds["lon_range"]
            
            if (lat_range[0] <= lat <= lat_range[1] and 
                lon_range[0] <= lon <= lon_range[1]):
                if region != "Other":  # Other is fallback
                    return region
        
        return "Other"
    
    def _compute_time_bin(self, time_value: int) -> str:
        """
        Compute time bin label from time value.
        
        Bins are 500-year windows (e.g., "-2000 to -1500", "-1500 to -1000", etc.)
        
        Args:
            time_value: Time in BCE/CE (negative = BCE, positive = CE)
        
        Returns:
            String label "START_to_END" or "NA"
        """
        if pd.isna(time_value):
            return "NA"
        
        # Find bin start (round down to nearest bin_width)
        bin_start = (int(time_value) // self.time_bin_width) * self.time_bin_width
        bin_end = bin_start + self.time_bin_width
        
        return f"{bin_start}_to_{bin_end}"
    
    def _classify_gap_severity(self, record_count: int) -> str:
        """
        Classify gap severity based on record count.
        
        Returns:
            "GREEN" (>= 5), "YELLOW" (2-4), or "RED" (< 2)
        """
        if record_count >= self.gap_threshold:
            return "GREEN"
        elif record_count >= 2:
            return "YELLOW"
        else:
            return "RED"
    
    def generate_coverage_report(
        self,
        audit_df: pd.DataFrame,
    ) -> Dict:
        """
        Generate coverage statistics report.
        
        Args:
            audit_df: Output from audit_coverage()
        
        Returns:
            Dict with coverage statistics:
            {
              "total_cells": N,
              "green_cells": N, "yellow_cells": N, "red_cells": N,
              "records_per_source": {...},
              "coverage_by_region": {...},
              "coverage_by_time": {...},
            }
        """
        if audit_df.empty:
            return {
                "total_cells": 0,
                "error": "Empty audit DataFrame",
            }
        
        green_count = (audit_df["gap_severity"] == "GREEN").sum()
        yellow_count = (audit_df["gap_severity"] == "YELLOW").sum()
        red_count = (audit_df["gap_severity"] == "RED").sum()
        
        report = {
            "total_cells": len(audit_df),
            "green_cells": green_count,
            "yellow_cells": yellow_count,
            "red_cells": red_count,
            "gap_percentage": round(100 * (red_count + yellow_count) / len(audit_df), 1),
        }
        
        # By source
        sources_stats = {}
        for source in self.active_sources:
            source_df = audit_df[audit_df["source"] == source]
            if len(source_df) > 0:
                sources_stats[source] = {
                    "total_records": source_df["record_count"].sum(),
                    "cells": len(source_df),
                    "mean_records_per_cell": round(source_df["record_count"].mean(), 1),
                    "gap_cells": (source_df["gap_severity"].isin(["RED", "YELLOW"])).sum(),
                }
        report["by_source"] = sources_stats
        
        # By region
        region_stats = {}
        for region in audit_df["region"].unique():
            if pd.notna(region):
                region_df = audit_df[audit_df["region"] == region]
                region_stats[region] = {
                    "total_records": region_df["record_count"].sum(),
                    "cells": len(region_df),
                    "gap_cells": (region_df["gap_severity"].isin(["RED", "YELLOW"])).sum(),
                }
        report["by_region"] = region_stats
        
        return report


def audit_all_coverage(
    df_dict: Dict[str, pd.DataFrame],
    auditor: Optional[CoverageAuditor] = None,
) -> Tuple[pd.DataFrame, Dict]:
    """
    Audit coverage for all sources and generate report.
    
    Args:
        df_dict: Dict of DataFrames with geographic/temporal columns
        auditor: CoverageAuditor instance (created if None)
    
    Returns:
        (audit_df, report_dict) tuple
    """
    if auditor is None:
        auditor = CoverageAuditor()
    
    audit_df = auditor.audit_coverage(df_dict)
    report = auditor.generate_coverage_report(audit_df)
    
    return audit_df, report


if __name__ == "__main__":
    # Self-test
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "=" * 80)
    print("COVERAGE AUDITOR - SELF-TEST")
    print("=" * 80)
    
    # Test 1: Instantiate
    print("\n[TEST 1] CoverageAuditor instantiation")
    auditor = CoverageAuditor()
    print(f"✓ ACTIVE_SOURCES: {auditor.active_sources}")
    print(f"✓ TIME_BIN_WIDTH: {auditor.time_bin_width}")
    print(f"✓ GAP_THRESHOLD: {auditor.gap_threshold}")
    
    # Test 2: Region assignment
    print("\n[TEST 2] Region assignment")
    test_coords = [
        (10.5, 40.2, "Africa"),
        (51.5, -0.1, "Europe"),
        (40.7, -74.0, "Americas"),
        (35.7, 139.7, "Asia-Pacific"),
    ]
    for lat, lon, expected_region in test_coords:
        assigned = auditor._assign_region(lat, lon)
        match = "✓" if assigned == expected_region else "✗"
        print(f"  {match} ({lat}, {lon}) → {assigned}")
    
    # Test 3: Time bin computation
    print("\n[TEST 3] Time bin computation")
    test_times = [-1900, -1500, -1000, -50, 0, 500]
    for t in test_times:
        bin_label = auditor._compute_time_bin(t)
        print(f"  {t:5d} → {bin_label}")
    
    # Test 4: Gap severity classification
    print("\n[TEST 4] Gap severity classification")
    test_counts = [10, 5, 4, 2, 1, 0]
    for count in test_counts:
        severity = auditor._classify_gap_severity(count)
        print(f"  {count} records → {severity}")
    
    print("\n" + "=" * 80)
    print("SELF-TEST COMPLETE")
    print("=" * 80)
