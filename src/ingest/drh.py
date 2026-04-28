"""DRH (Database of Religious History) data parser.

Loads and parses DRH sample CSV data to produce a standardised DataFrame
conforming to Phase 1 output schema.
"""

from pathlib import Path
from typing import Optional

import pandas as pd


def parse_drh(
    source_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    shamanism_keywords: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Parse DRH CSV data and produce standardised DataFrame."""
    if source_path is None:
        source_path = Path("data/raw/drh/drh_sample.csv")

    if shamanism_keywords is None:
        shamanism_keywords = [
            "trance", "shamanism", "spirit", "possession", "healing",
            "divination", "ritual", "soul", "initiation", "ancestor", "supernatural",
            "afterlife", "belief in afterlife",
        ]

    # Load data
    try:
        df = pd.read_csv(source_path, low_memory=False)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Could not load DRH file: {e}") from e

    # Identify shamanism-relevant columns
    metadata_cols = ["Entry name", "Start Date", "End Date", "Region"]
    all_question_cols = [col for col in df.columns if col not in metadata_cols]

    shamanism_cols = []
    for col in all_question_cols:
        if any(kw.lower() in col.lower() for kw in shamanism_keywords):
            shamanism_cols.append(col)

    if not shamanism_cols:
        shamanism_cols = all_question_cols[:5]

    # Create variable mapping
    mapping_records = []
    for col in shamanism_cols:
        mapping_records.append({
            "source_var_id": col,
            "source_var_name": col,
            "shamanism_relevant": any(kw.lower() in col.lower() for kw in shamanism_keywords),
            "reason": "Religious question from DRH survey",
        })

    mapping = pd.DataFrame(mapping_records)

    # Build output rows
    all_rows = []

    for idx, row in df.iterrows():
        entry_name = str(row["Entry name"])
        
        # Parse dates - handle NAType
        try:
            start_date_val = row["Start Date"]
            if pd.isna(start_date_val) or start_date_val is pd.NA:
                start_date = None
            else:
                start_date = int(start_date_val)
        except (ValueError, TypeError):
            start_date = None
            
        try:
            end_date_val = row["End Date"]
            if pd.isna(end_date_val) or end_date_val is pd.NA:
                end_date = None
            else:
                end_date = int(end_date_val)
        except (ValueError, TypeError):
            end_date = None

        # Assume dates > 1500 are CE, else potentially BCE
        if start_date:
            time_start = float(start_date) if start_date > 1500 else float(-start_date)
        else:
            time_start = pd.NA

        if end_date:
            time_end = float(end_date) if end_date > 1500 else float(-end_date)
        else:
            time_end = pd.NA

        # For each shamanism question, create a record
        for col in shamanism_cols:
            value = row[col]

            # Convert responses to binary
            if pd.isna(value) or value is pd.NA:
                var_value = pd.NA
            elif str(value).lower() in ["yes", "y", "true", "1", "present"]:
                var_value = 1.0
            elif str(value).lower() in ["no", "n", "false", "0", "absent"]:
                var_value = 0.0
            else:
                var_value = pd.NA

            output_row = {
                "source": "drh",
                "culture_id": f"DRH_{idx}",
                "culture_name": entry_name,
                "unit_type": "tradition",
                "lat": pd.NA,
                "lon": pd.NA,
                "time_start": time_start,
                "time_end": time_end,
                "variable_name": col,
                "variable_value": var_value,
                "variable_type": "binary",
                "confidence": pd.NA,
                "notes": f"Region: {row.get('Region', 'Unknown')}",
            }
            all_rows.append(output_row)

    output = pd.DataFrame(all_rows)

    if len(output) == 0:
        raise ValueError("No data rows produced after processing")

    # Validate column order
    expected_columns = [
        "source", "culture_id", "culture_name", "unit_type",
        "lat", "lon", "time_start", "time_end",
        "variable_name", "variable_value", "variable_type", "confidence", "notes",
    ]
    output = output[expected_columns].reset_index(drop=True)

    # Replace NAType with np.nan for numeric columns to allow dtype conversion
    import numpy as np
    float_cols = ["lat", "lon", "time_start", "time_end", "variable_value", "confidence"]
    for col in float_cols:
        output[col] = output[col].apply(lambda x: np.nan if pd.isna(x) or x is pd.NA else x)

    # Ensure correct dtypes
    output = output.astype({
        "source": "object",
        "culture_id": "object",
        "culture_name": "object",
        "unit_type": "object",
        "lat": "float64",
        "lon": "float64",
        "time_start": "float64",
        "time_end": "float64",
        "variable_name": "object",
        "variable_value": "float64",
        "variable_type": "object",
        "confidence": "float64",
        "notes": "object",
    })

    # Save outputs
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output.to_parquet(output_path, index=False)

    # Save variable mapping
    mapping_path = Path("data/reference/drh_variable_mapping.csv")
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    mapping.to_csv(mapping_path, index=False)

    return output
