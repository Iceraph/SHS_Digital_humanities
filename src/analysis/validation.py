"""
Ethnographic Validation Module

Cross-validates harmonised data against published ethnographic narratives
and theoretical expectations for shamanic practices.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

from .config import ETHNOGRAPHIC_SHAMANIC_PROFILE, MAJOR_CULTURES


def load_ethnographic_narratives() -> Dict[str, Dict]:
    """
    Load expected ethnographic profiles for major shamanic cultures.
    
    These are based on published literature in PROJECT_CONTEXT.md.
    
    Returns:
        Dictionary mapping culture_id to expected feature profiles
    """
    narratives = {
        "DRH_001": {
            "name": "Siberian Shamanism",
            "description": "Core shamanic practices of Siberian indigenous peoples",
            "expected_features": {
                "trance_induction": 1,
                "soul_flight": 1,
                "spirit_possession": 1,
                "dedicated_specialist": 1,
                "initiatory_crisis": 1,
                "rhythmic_percussion": 1,
                "healing_function": 1,
                "layered_cosmology": 1,
                "animal_transformation": 1,
            },
            "sources": [
                "Eliade (1964) Shamanism: Archaic Techniques of Ecstasy",
                "Vitebsky (1995) The Shaman",
            ],
        },
        "DRH_004": {
            "name": "Korean Shamanism",
            "description": "Shamanic mudang traditions of Korea",
            "expected_features": {
                "trance_induction": 1,
                "spirit_possession": 1,
                "dedicated_specialist": 1,
                "healing_function": 1,
                "rhythmic_percussion": 1,
                "public_performance": 1,
            },
            "sources": [
                "Kendall (1996) Getting Married in Korea",
                "Korean cultural studies on spirit possession",
            ],
        },
    }
    
    return narratives


def validate_against_ethnography(
    harmonised_df: pd.DataFrame,
    culture_id: str,
) -> Dict[str, any]:
    """
    Validate a culture's feature profile against ethnographic expectations.
    
    Args:
        harmonised_df: Harmonised DataFrame
        culture_id: Culture to validate
        
    Returns:
        Validation report
    """
    narratives = load_ethnographic_narratives()
    
    if culture_id not in narratives:
        return {"error": f"No ethnographic data for {culture_id}"}
    
    narrative = narratives[culture_id]
    expected_features = narrative["expected_features"]
    
    # Get culture's actual features
    culture_data = harmonised_df[harmonised_df["culture_id"] == culture_id]
    
    actual_features = {}
    for feature in expected_features.keys():
        feature_records = culture_data[culture_data["feature_name"] == feature]
        if len(feature_records) > 0:
            actual_features[feature] = feature_records["feature_value_binarised"].max()
        else:
            actual_features[feature] = np.nan
    
    # Compare
    agreements = 0
    conflicts = 0
    unknowns = 0
    
    for feature, expected_value in expected_features.items():
        actual_value = actual_features.get(feature, np.nan)
        
        if pd.isna(actual_value):
            unknowns += 1
        elif actual_value == expected_value:
            agreements += 1
        else:
            conflicts += 1
    
    agreement_rate = agreements / (agreements + conflicts) if (agreements + conflicts) > 0 else 0
    
    return {
        "culture_id": culture_id,
        "culture_name": narrative["name"],
        "expected_features": expected_features,
        "actual_features": actual_features,
        "agreements": agreements,
        "conflicts": conflicts,
        "unknowns": unknowns,
        "agreement_rate": agreement_rate,
        "validation_status": "PASS" if agreement_rate >= 0.7 else "REVIEW" if agreement_rate >= 0.5 else "FAIL",
        "ethnographic_sources": narrative["sources"],
    }


def cross_validate_all_cultures(
    harmonised_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Cross-validate all major cultures against ethnographic expectations.
    
    Args:
        harmonised_df: Harmonised DataFrame
        
    Returns:
        Validation results DataFrame
    """
    results = []
    
    for culture in MAJOR_CULTURES:
        culture_id = culture["id"]
        if culture_id in harmonised_df["culture_id"].values:
            validation = validate_against_ethnography(harmonised_df, culture_id)
            results.append(validation)
    
    return pd.DataFrame(results)


def identify_theoretical_inconsistencies(
    harmonised_df: pd.DataFrame,
) -> List[Dict]:
    """
    Identify records that contradict shamanism theory expectations.
    
    Based on neurobiological universalism hypothesis, shamanic features
    should co-occur in characteristic patterns.
    
    Args:
        harmonised_df: Harmonised DataFrame
        
    Returns:
        List of inconsistency reports
    """
    inconsistencies = []
    
    # Expected co-occurrences per shamanism theory
    theory_assertions = [
        {
            "name": "Trance + Healing",
            "features": ["trance_induction", "healing_function"],
            "expected": True,  # Both should be present together
            "confidence": 0.8,
        },
        {
            "name": "Specialist + Initiation",
            "features": ["dedicated_specialist", "initiatory_crisis"],
            "expected": True,
            "confidence": 0.7,
        },
        {
            "name": "Cosmology + Spirit_Possession",
            "features": ["layered_cosmology", "spirit_possession"],
            "expected": True,
            "confidence": 0.8,
        },
    ]
    
    # Check each theory assertion
    for assertion in theory_assertions:
        features = assertion["features"]
        
        # Get co-occurrence in data
        for culture_id in harmonised_df["culture_id"].unique():
            culture_df = harmonised_df[harmonised_df["culture_id"] == culture_id]
            
            feature_values = {}
            for feature in features:
                feature_df = culture_df[culture_df["feature_name"] == feature]
                if len(feature_df) > 0:
                    feature_values[feature] = feature_df["feature_value_binarised"].max()
            
            # Check if pattern matches expectation
            if len(feature_values) == len(features):
                all_present = all(v == 1 for v in feature_values.values())
                
                if assertion["expected"] and not all_present:
                    inconsistencies.append({
                        "culture_id": culture_id,
                        "assertion": assertion["name"],
                        "type": "missing_expected_cooccurrence",
                        "expected_features": features,
                        "actual_values": feature_values,
                        "confidence": assertion["confidence"],
                    })
    
    return inconsistencies


def document_validation_evidence(
    validation_results: pd.DataFrame,
    output_path: str = "data/processed/analysis/ethnographic_validation.csv",
) -> None:
    """
    Save ethnographic validation results to file.
    
    Args:
        validation_results: DataFrame from cross_validate_all_cultures()
        output_path: Where to save validation results
    """
    # Flatten nested structures
    output_df = validation_results[[
        "culture_id",
        "culture_name",
        "agreements",
        "conflicts",
        "unknowns",
        "agreement_rate",
        "validation_status",
    ]].copy()
    
    output_df.to_csv(output_path, index=False)
    
    print(f"✓ Ethnographic validation saved to {output_path}")
    print(f"  Cultures validated: {len(output_df)}")
    print(f"  Pass status: {(output_df['validation_status'] == 'PASS').sum()}")
    print(f"  Review needed: {(output_df['validation_status'] == 'REVIEW').sum()}")


def compare_with_theoretical_predictions(
    harmonised_df: pd.DataFrame,
) -> Dict[str, any]:
    """
    Compare data with two competing theoretical hypotheses.
    
    1. Neurobiological universalism: All shamanic features cluster globally
    2. Regional diffusion: Shamanism fragments into regional clusters
    
    Args:
        harmonised_df: Harmonised DataFrame
        
    Returns:
        Comparison report supporting each hypothesis
    """
    # This will be developed in Phase 4/clustering analysis
    # For now, setup infrastructure
    
    return {
        "hypothesis_1_neurobiological": {
            "name": "Global Shamanic Cluster",
            "prediction": "Cultures with shamanic features cluster together globally",
            "evidence": "To be analyzed in Phase 4 clustering",
            "support_level": "Unknown",
        },
        "hypothesis_2_regional_diffusion": {
            "name": "Regional Fragmentation",
            "prediction": "Shamanic features fragment into 3-5 regional clusters",
            "evidence": "To be analyzed in Phase 4 clustering",
            "support_level": "Unknown",
        },
    }


def validate_field_notes(
    harmonised_df: pd.DataFrame,
    notes_column: str = "notes",
) -> Dict[str, any]:
    """
    Analyze field notes for additional context supporting or contradicting features.
    
    Args:
        harmonised_df: Harmonised DataFrame
        notes_column: Column containing field notes
        
    Returns:
        Summary of field note insights
    """
    notes_with_data = harmonised_df[harmonised_df[notes_column].notna()]
    
    if len(notes_with_data) == 0:
        return {"note_count": 0, "coverage": "No notes available"}
    
    return {
        "note_count": len(notes_with_data),
        "coverage_percent": len(notes_with_data) / len(harmonised_df) * 100,
        "notes_summary": "Field notes available for additional context",
        "next_step": "Manual review of notes for narrative validation",
    }
