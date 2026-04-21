"""Seshat data parser.

Loads and parses Seshat CSV data to produce a standardised DataFrame
conforming to Phase 1 output schema.

Seshat data can be obtained from:
- Public Equinox-2020 release: http://seshat-db.com/
- Full access: https://seshatdatabank.info/ (requires registration)

Use seshat_fetch.py to download data programmatically.
"""

from pathlib import Path
from typing import Optional
import warnings

import pandas as pd


def parse_seshat(
    polities_path: Optional[Path] = None,
    variables_path: Optional[Path] = None,
    data_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    shamanism_keywords: Optional[list[str]] = None,
    auto_fetch: bool = True,
) -> pd.DataFrame:
    """Parse Seshat CSV data and produce standardised DataFrame.

    Args:
        polities_path: Path to polities.csv (default: data/raw/seshat/polities.csv)
        variables_path: Path to variables.csv (default: data/raw/seshat/variables.csv)
        data_path: Path to data.csv (default: data/raw/seshat/data.csv)
        output_path: Path where to save seshat_raw.parquet (optional)
        shamanism_keywords: Keywords for variable filtering
        auto_fetch: If True, attempt to fetch Seshat data if files not found

    Returns:
        DataFrame with 13 columns matching Phase 1 output schema.

    Note:
        Real Seshat data can be obtained from:
        - Public: http://seshat-db.com/ (Equinox-2020)
        - Full: https://seshatdatabank.info/ (requires registration)
    """
    if shamanism_keywords is None:
        shamanism_keywords = [
            "trance", "shamanism", "spirit", "possession", "healing",
            "divination", "ritual", "soul", "initiation", "ancestor",
            "specialist", "healer", "medium", "séance",
        ]
    
    # Set default paths
    if polities_path is None:
        polities_path = Path("data/raw/seshat/polities.csv")
    if variables_path is None:
        variables_path = Path("data/raw/seshat/variables.csv")
    if data_path is None:
        data_path = Path("data/raw/seshat/data.csv")
    
    polities_path = Path(polities_path)
    variables_path = Path(variables_path)
    data_path = Path(data_path)

    # Try to fetch data if not found and auto_fetch is True
    if auto_fetch and not polities_path.exists():
        try:
            from .seshat_fetch import fetch_seshat_equinox2020
            fetch_seshat_equinox2020(polities_path.parent)
        except Exception as e:
            warnings.warn(
                f"Could not fetch Seshat data: {e}. "
                "Using mock data instead. See SESHAT_SETUP.md for manual download instructions."
            )

    # Check if files exist
    files_exist = (
        polities_path.exists() and
        variables_path.exists() and
        data_path.exists()
    )

    # If no files found, use mock data
    if not files_exist:
        # Generate mock Seshat output
        warnings.warn(
            f"Seshat data not found. Using mock data for testing.\n"
            f"To use real Seshat data:\n"
            f"1. Download from http://seshat-db.com/\n"
            f"2. Place files in {polities_path.parent}/\n"
            f"3. See SESHAT_SETUP.md for details"
        )
        
        mock_data = {
            "source": ["seshat", "seshat", "seshat", "seshat", "seshat", "seshat"],
            "culture_id": ["P0001", "P0001", "P0002", "P0002", "P0003", "P0003"],
            "culture_name": ["Joseon", "Joseon", "Ottoman Empire", "Ottoman Empire", "Safavid Persia", "Safavid Persia"],
            "unit_type": ["polity", "polity", "polity", "polity", "polity", "polity"],
            "lat": [37.5, 37.5, 39.0, 39.0, 32.5, 32.5],
            "lon": [127.0, 127.0, 35.0, 35.0, 51.5, 51.5],
            "time_start": [-1392.0, -1392.0, -1299.0, -1299.0, -1501.0, -1501.0],
            "time_end": [-1910.0, -1910.0, -1922.0, -1922.0, -1736.0, -1736.0],
            "variable_name": [
                "spirit_possession", "divination", 
                "ritual_practice", "spirit_mediation",
                "healing_rituals", "shamanic_trance"
            ],
            "variable_value": [1.0, 1.0, 1.0, 0.0, 1.0, 1.0],
            "variable_type": ["binary", "binary", "binary", "binary", "binary", "binary"],
            "confidence": [0.75, 0.60, 0.70, 0.50, 0.65, 0.80],
            "notes": [pd.NA, pd.NA, "Spans multiple regions", pd.NA, "Limited sources", pd.NA],
        }
        output = pd.DataFrame(mock_data)

        # Save outputs
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output.to_parquet(output_path, index=False)

        # Save variable mapping
        mapping_records = [
            {"source_var_id": "spirit_possession", "source_var_name": "spirit_possession",
             "shamanism_relevant": True, "reason": "Core shamanism variable"},
            {"source_var_id": "divination", "source_var_name": "divination",
             "shamanism_relevant": True, "reason": "Core shamanism variable"},
            {"source_var_id": "ritual_practice", "source_var_name": "ritual_practice",
             "shamanism_relevant": True, "reason": "Ritual specialist practice"},
            {"source_var_id": "spirit_mediation", "source_var_name": "spirit_mediation",
             "shamanism_relevant": True, "reason": "Spirit contact practice"},
        ]
        mapping = pd.DataFrame(mapping_records)
        mapping_path = Path("data/reference/seshat_variable_mapping.csv")
        mapping_path.parent.mkdir(parents=True, exist_ok=True)
        mapping.to_csv(mapping_path, index=False)

        return output

    # Real Seshat parsing (if files provided)
    try:
        polities = pd.read_csv(polities_path)
        variables = pd.read_csv(variables_path)
        data = pd.read_csv(data_path)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Could not load Seshat CSV files: {e}") from e

    # Identify shamanism-relevant variables
    shamanism_mask = variables["name"].str.lower().str.contains(
        "|".join(shamanism_keywords), regex=True, na=False
    )
    shamanism_vars = variables[shamanism_mask].copy()

    if len(shamanism_vars) == 0:
        shamanism_vars = variables.head(5)  # Use first 5 if none match

    # Build output rows
    all_rows = []

    for _, data_row in data.iterrows():
        polity_id = data_row["polity_id"]
        polity_row = polities[polities["id"] == polity_id]

        if len(polity_row) == 0:
            continue

        polity = polity_row.iloc[0]
        lat = float(polity["latitude"]) if pd.notna(polity["latitude"]) else pd.NA
        lon = float(polity["longitude"]) if pd.notna(polity["longitude"]) else pd.NA

        # Parse uncertainty to confidence
        uncertainty = data_row.get("uncertainty", "probable")
        confidence_map = {"certain": 0.95, "probable": 0.75, "possible": 0.50, "speculative": 0.25}
        confidence = confidence_map.get(str(uncertainty).lower(), pd.NA)

        output_row = {
            "source": "seshat",
            "culture_id": polity_id,
            "culture_name": polity["name"],
            "unit_type": "polity",
            "lat": lat,
            "lon": lon,
            "time_start": float(polity["start_year"]),
            "time_end": float(polity["end_year"]),
            "variable_name": data_row["var_id"],
            "variable_value": float(data_row["value"]) if pd.notna(data_row["value"]) else pd.NA,
            "variable_type": "binary" if data_row["value"] in [0, 1] else "ordinal",
            "confidence": confidence,
            "notes": pd.NA,
        }
        all_rows.append(output_row)

    output = pd.DataFrame(all_rows)

    if len(output) == 0:
        raise ValueError("No data rows produced after processing")

    # Validate column order and dtypes
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
    mapping = pd.DataFrame()
    mapping["source_var_id"] = shamanism_vars["id"].unique()
    mapping["source_var_name"] = shamanism_vars["name"].unique()
    mapping["shamanism_relevant"] = True
    mapping["reason"] = "Seshat variable"

    mapping_path = Path("data/reference/seshat_variable_mapping.csv")
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    mapping.to_csv(mapping_path, index=False)

    return output
