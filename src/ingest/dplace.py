"""D-PLACE data parser (updated for real data).

Loads and parses raw D-PLACE CSV files (societies, variables, data) to produce
a standardised DataFrame conforming to Phase 1 output schema.
"""

from pathlib import Path
from typing import Optional

import pandas as pd


def parse_dplace(
    societies_path: Path,
    variables_path: Path,
    data_path: Path,
    output_path: Optional[Path] = None,
    shamanism_keywords: Optional[list[str]] = None,
    temporal_start: int = -1850,
    temporal_end: int = -1950,
    limit: int = None,
    codes_path: Optional[Path] = None,
) -> pd.DataFrame:
    """Parse D-PLACE raw CSVs and produce standardised DataFrame."""
    if shamanism_keywords is None:
        shamanism_keywords = [
            "trance", "shamanism", "soul", "spirit", "healing",
            "divination", "percussion", "chanting", "ritual",
            "possession", "initiation", "ancestor",
        ]

    # Load metadata files
    try:
        societies = pd.read_csv(societies_path)
        variables = pd.read_csv(variables_path)
        data = pd.read_csv(data_path, nrows=limit, low_memory=False)
        
        # Load codes if path provided (for value lookups)
        codes = None
        if codes_path is None and (societies_path.parent / "codes.csv").exists():
            codes_path = societies_path.parent / "codes.csv"
        if codes_path:
            codes = pd.read_csv(codes_path)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Could not load D-PLACE CSV files: {e}") from e

    # Identify shamanism-relevant variables
    shamanism_mask = variables["Name"].str.lower().str.contains(
        "|".join(shamanism_keywords), regex=True, na=False
    )
    shamanism_vars = variables[shamanism_mask].copy()

    if len(shamanism_vars) == 0:
        raise ValueError("No shamanism-relevant variables found")

    # Create variable mapping reference
    mapping = shamanism_vars[["ID", "Name"]].copy()
    mapping.columns = ["source_var_id", "source_var_name"]
    mapping["shamanism_relevant"] = True
    mapping["reason"] = "Matched shamanism keyword"

    # Filter data to shamanism-relevant variables
    shamanism_data = data[data["Var_ID"].isin(shamanism_vars["ID"])].copy()

    if shamanism_data.empty:
        raise ValueError("No data records found for shamanism-relevant variables")

    # Merge with societies - use separate merge to avoid suffix issues
    shamanism_data = shamanism_data.merge(
        societies[["ID", "Name", "Latitude", "Longitude"]],
        left_on="Soc_ID",
        right_on="ID",
        how="left",
        suffixes=(None, "_y")
    )

    # Drop rows with missing coordinates
    shamanism_data = shamanism_data.dropna(subset=["Latitude", "Longitude"])

    # Function to get numeric value from Code_ID or direct Value
    def get_numeric_value(row, codes_df):
        """Convert value to numeric, using Code_ID lookup if available."""
        code_id = row.get("Code_ID")
        value = row.get("Value")
        
        # If Code_ID present, use codes lookup
        if pd.notna(code_id) and codes_df is not None and str(code_id).strip():
            code_match = codes_df[codes_df["ID"] == str(code_id)]
            if not code_match.empty:
                return float(code_match.iloc[0]["ord"])
        
        # Otherwise try to convert value directly
        if pd.notna(value):
            try:
                return float(value)
            except (ValueError, TypeError):
                return pd.NA
        
        return pd.NA
    def get_var_type(var_id):
        var_vals = shamanism_data[shamanism_data["Var_ID"] == var_id]["Value"]
        unique_vals = var_vals.dropna().unique()
        if all(v in [0, 1] or pd.isna(v) for v in unique_vals):
            return "binary"
        return "ordinal"

    # Build output rows
    all_rows = []
    for _, row in shamanism_data.iterrows():
        numeric_value = get_numeric_value(row, codes)
        output_row = {
            "source": "dplace",
            "culture_id": str(row["Soc_ID"]),
            "culture_name": str(row["Name"]),  # After merge, this is the society Name
            "unit_type": "society",
            "lat": float(row["Latitude"]),
            "lon": float(row["Longitude"]),
            "time_start": float(temporal_start),
            "time_end": float(temporal_end),
            "variable_name": str(row["Var_ID"]),
            "variable_value": numeric_value,
            "variable_type": get_var_type(row["Var_ID"]),
            "confidence": pd.NA,
            "notes": pd.NA,
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
        "time_start": "int64",
        "time_end": "int64",
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
    mapping_path = Path("data/reference/dplace_variable_mapping.csv")
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    mapping.to_csv(mapping_path, index=False)

    return output
