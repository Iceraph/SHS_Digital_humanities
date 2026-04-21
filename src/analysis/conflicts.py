"""
Conflict Handling Module

Implements conflict detection, logging, and resolution strategies.
Creates comprehensive conflict registry for manual review and adjudication.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from pathlib import Path

from .config import (
    CONFLICT_STRATEGIES,
    DEFAULT_CONFLICT_STRATEGY,
)
from .comparison import (
    load_harmonised_data,
    get_feature_matrix_by_source,
    find_overlapping_cultures,
    compare_feature_agreements,
    resolve_conflicts_quality_weighted,
)


def generate_conflicts_registry(
    dplace_path: str = "data/processed/harmonised/dplace_harmonised.parquet",
    drh_path: str = "data/processed/harmonised/drh_harmonised.parquet",
    seshat_path: Optional[str] = "data/processed/harmonised/seshat_harmonised.parquet",
    output_path: str = "data/processed/harmonised/conflicts.csv",
    strategy: str = DEFAULT_CONFLICT_STRATEGY,
) -> Tuple[pd.DataFrame, ConflictRegistry]:
    """
    Full pipeline: Load data, detect conflicts, resolve, and save registry.
    
    FIXED (Issue 4): This function enables conflicts.csv generation in main pipeline.
    
    Args:
        dplace_path: Path to D-PLACE harmonised parquet
        drh_path: Path to DRH harmonised parquet
        seshat_path: Optional Seshat parquet path
        output_path: Where to save conflicts.csv
        strategy: Conflict resolution strategy (quality_weighted recommended)
        
    Returns:
        Tuple of (conflicts_df, registry)
    """
    # Load harmonised data
    try:
        harmonised_data = load_harmonised_data(dplace_path, drh_path, seshat_path)
    except FileNotFoundError as e:
        print(f"ERROR loading harmonised data: {e}")
        return pd.DataFrame(), ConflictRegistry(output_path)
    
    # Get feature matrices per source
    feature_matrices = get_feature_matrix_by_source(harmonised_data)
    
    # Find overlapping cultures
    all_cultures, overlapping_cultures = find_overlapping_cultures(feature_matrices)
    
    print(f"📊 Conflict Detection Summary:")
    print(f"   Total cultures: {len(all_cultures)}")
    print(f"   Cultures in multiple sources: {len(overlapping_cultures)}")
    
    # If no overlaps, return empty registry
    if len(overlapping_cultures) == 0:
        print("   ⚠️  No overlapping cultures; no conflicts to detect")
        empty_df = pd.DataFrame(columns=[
            "culture_id", "feature_name", "source1", "value1", "quality1",
            "source2", "value2", "quality2", "conflict_type",
            "resolved_value", "resolution_method", "resolution_status"
        ])
        empty_df.to_csv(output_path, index=False)
        print(f"   ✓ Empty conflicts registry written to {output_path}")
        return empty_df, ConflictRegistry(output_path)
    
    # Compare feature agreements
    agreement_df = compare_feature_agreements(
        feature_matrices, overlapping_cultures, harmonised_data
    )
    
    # Initialize registry and process conflicts
    registry = ConflictRegistry(output_path)
    conflicts = registry.detect_conflicts(agreement_df)
    
    print(f"\n🔍 Conflict Analysis:")
    print(f"   Total comparisons: {len(agreement_df)}")
    print(f"   Conflicts: {len(agreement_df[agreement_df['conflict_type'] == 'conflict'])}")
    print(f"   Agreements: {len(agreement_df[agreement_df['conflict_type'] == 'agreement'])}")
    
    # Resolve conflicts using specified strategy
    if len(conflicts) > 0:
        resolved = registry.apply_resolution_strategy(strategy)
        print(f"   Resolution method: {strategy}")
    
    # Save registry
    registry.save_conflict_registry()
    
    return agreement_df, registry


class ConflictRegistry:
    """Manager for conflict detection, logging, and resolution."""
    
    def __init__(self, output_path: str = "data/processed/harmonised/conflicts.csv"):
        self.output_path = output_path
        self.conflicts = []
        self.resolutions = []
        self.agreement_stats = {}
    
    def detect_conflicts(
        self,
        agreement_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Identify all significant conflicts.
        
        Args:
            agreement_df: From comparison.compare_feature_agreements()
            
        Returns:
            Filtered conflicts DataFrame
        """
        conflicts = agreement_df[agreement_df["conflict_type"] == "conflict"].copy()
        
        # Add resolution status
        conflicts["resolution_status"] = "pending_review"
        conflicts["resolution_method"] = ""
        conflicts["resolved_value"] = np.nan
        conflicts["reviewer_notes"] = ""
        
        self.conflicts = conflicts
        return conflicts
    
    def log_conflict(
        self,
        culture_id: str,
        feature_name: str,
        source1: str,
        value1: float,
        source2: str,
        value2: float,
        quality1: float,
        quality2: float,
        conflict_type: str,
    ) -> None:
        """Log a single conflict."""
        self.conflicts.append({
            "timestamp": datetime.now().isoformat(),
            "culture_id": culture_id,
            "feature_name": feature_name,
            "source1": source1,
            "value1": value1,
            "quality1": quality1,
            "source2": source2,
            "value2": value2,
            "quality2": quality2,
            "conflict_type": conflict_type,
            "resolution_status": "pending_review",
            "resolution_method": "",
            "resolved_value": np.nan,
        })
    
    def resolve_conflict_quality_weighted(
        self,
        conflict_row: pd.Series,
    ) -> Tuple[float, str]:
        """
        Resolve a conflict using quality-weighted averaging.
        
        Args:
            conflict_row: Row from conflicts DataFrame
            
        Returns:
            Tuple of (resolved_value, resolution_method)
        """
        val1 = conflict_row["value1"]
        val2 = conflict_row["value2"]
        quality1 = conflict_row["quality1"]
        quality2 = conflict_row["quality2"]
        
        total_quality = quality1 + quality2
        
        if total_quality > 0:
            resolved_value = (val1 * quality1 + val2 * quality2) / total_quality
        else:
            resolved_value = np.mean([val1, val2])
        
        return resolved_value, "quality_weighted"
    
    def resolve_conflict_majority(
        self,
        conflict_row: pd.Series,
    ) -> Tuple[float, str]:
        """
        Resolve a conflict using majority vote.
        
        Args:
            conflict_row: Row from conflicts DataFrame
            
        Returns:
            Tuple of (resolved_value, resolution_method)
        """
        val1 = conflict_row["value1"]
        val2 = conflict_row["value2"]
        
        if val1 == val2:
            resolved_value = val1
        else:
            # For binary, arbitrarily pick val1
            resolved_value = val1
        
        return resolved_value, "majority"
    
    def apply_resolution_strategy(
        self,
        strategy: str = DEFAULT_CONFLICT_STRATEGY,
    ) -> pd.DataFrame:
        """
        Apply conflict resolution strategy to all conflicts.
        
        Args:
            strategy: One of "quality_weighted", "majority", "manual_inspection"
            
        Returns:
            Conflicts DataFrame with resolved values
        """
        if len(self.conflicts) == 0:
            return pd.DataFrame()
        
        conflicts = self.conflicts.copy()
        
        resolved_vals = []
        methods = []
        
        for _, row in conflicts.iterrows():
            if strategy == "quality_weighted":
                val, method = self.resolve_conflict_quality_weighted(row)
            elif strategy == "majority":
                val, method = self.resolve_conflict_majority(row)
            else:  # manual_inspection
                val, method = np.nan, "manual_inspection"
            
            resolved_vals.append(val)
            methods.append(method)
        
        conflicts["resolved_value"] = resolved_vals
        conflicts["resolution_method"] = methods
        conflicts["resolution_status"] = [
            "resolved" if method != "manual_inspection" else "pending_review"
            for method in methods
        ]
        
        self.conflicts = conflicts
        return conflicts
    
    def generate_conflict_report(self) -> Dict[str, any]:
        """
        Generate summary statistics of conflicts and resolutions.
        
        Returns:
            Report dictionary
        """
        if len(self.conflicts) == 0:
            return {
                "total_conflicts": 0,
                "report": "No conflicts detected",
            }
        
        conflicts = self.conflicts
        
        report = {
            "total_conflicts": len(conflicts),
            "conflicts_by_feature": conflicts.groupby("feature_name").size().to_dict(),
            "conflicts_by_source_pair": conflicts.groupby(
                ["source1", "source2"]
            ).size().to_dict(),
            "resolution_summary": {
                "resolved": (conflicts["resolution_status"] == "resolved").sum(),
                "pending_review": (conflicts["resolution_status"] == "pending_review").sum(),
            },
            "resolution_methods": conflicts["resolution_method"].value_counts().to_dict(),
        }
        
        return report
    
    def save_conflict_registry(self) -> None:
        """Save conflict registry to CSV."""
        if len(self.conflicts) == 0:
            print("No conflicts to save.")
            return
        
        # Prepare output
        output_df = self.conflicts[[
            "culture_id",
            "feature_name",
            "source1",
            "value1",
            "quality1",
            "source2",
            "value2",
            "quality2",
            "conflict_type",
            "resolved_value",
            "resolution_method",
            "resolution_status",
        ]].copy()
        
        output_df.to_csv(self.output_path, index=False)
        
        print(f"✓ Conflict registry saved to {self.output_path}")
        print(f"  Total conflicts: {len(output_df)}")
        print(f"  Resolved: {(output_df['resolution_status'] == 'resolved').sum()}")
        print(f"  Pending review: {(output_df['resolution_status'] == 'pending_review').sum()}")
    
    def export_for_manual_review(
        self,
        output_path: Optional[str] = None,
    ) -> None:
        """
        Export pending conflicts for manual review in spreadsheet.
        
        Args:
            output_path: Where to save review file
        """
        if output_path is None:
            output_path = self.output_path.replace(".csv", "_review.xlsx")
        
        pending = self.conflicts[self.conflicts["resolution_status"] == "pending_review"]
        
        if len(pending) == 0:
            print("No pending conflicts to export.")
            return
        
        # Format for review
        review_df = pending[[
            "culture_id",
            "feature_name",
            "source1",
            "value1",
            "quality1",
            "source2",
            "value2",
            "quality2",
            "conflict_type",
        ]].copy()
        
        # Add recommendation column
        review_df["recommended_value"] = pending.apply(
            lambda row: self.resolve_conflict_quality_weighted(row)[0],
            axis=1,
        )
        
        # Add column for reviewer decision
        review_df["reviewer_decision"] = ""
        review_df["reviewer_notes"] = ""
        
        try:
            review_df.to_excel(output_path, index=False)
            print(f"✓ Manual review file exported to {output_path}")
        except ImportError:
            # Fallback to CSV if openpyxl not available
            review_df.to_csv(output_path.replace(".xlsx", ".csv"), index=False)
            print(f"✓ Manual review file exported to {output_path.replace('.xlsx', '.csv')}")


def flag_high_uncertainty_records(
    df: pd.DataFrame,
    uncertainty_threshold: int = 2,
) -> pd.DataFrame:
    """
    Flag records with high temporal or geographic uncertainty.
    
    Args:
        df: Harmonised DataFrame
        uncertainty_threshold: Minimum uncertainty level to flag
        
    Returns:
        Flagged records
    """
    flagged = df[df["time_uncertainty"] >= uncertainty_threshold].copy()
    flagged["uncertainty_flag"] = "HIGH_TEMPORAL_UNCERTAINTY"
    
    return flagged


def create_adjudication_checklist(
    conflict_registry: ConflictRegistry,
) -> pd.DataFrame:
    """
    Create a prioritized checklist for human adjudication of conflicts.
    
    Prioritizes by:
    1. Number of cultures affected
    2. Number of sources involved
    3. Severity of disagreement
    
    Args:
        conflict_registry: Initialized ConflictRegistry
        
    Returns:
        Prioritized checklist
    """
    conflicts = conflict_registry.conflicts
    
    if len(conflicts) == 0:
        return pd.DataFrame()
    
    # Group by feature
    feature_priority = conflicts.groupby("feature_name").agg({
        "culture_id": "nunique",
        "source1": lambda x: len(set(x) | {y for y in x}),  # Unique sources
    }).rename(columns={
        "culture_id": "cultures_affected",
        "source1": "sources_involved",
    })
    
    feature_priority["priority_score"] = (
        feature_priority["cultures_affected"] * 2 +
        feature_priority["sources_involved"]
    )
    
    return feature_priority.sort_values("priority_score", ascending=False)
