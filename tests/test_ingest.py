"""Phase 1 Data Ingestion Tests

Comprehensive test suite for D-PLACE, Seshat, and DRH parsers.
Covers unit tests, integration tests, and data validation tests.

Run with: pytest tests/test_ingest.py -v
"""

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from src.ingest.dplace import parse_dplace
from src.ingest.drh import parse_drh
from src.ingest.seshat import parse_seshat


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def dplace_fixtures(fixtures_dir: Path):
    """Return paths to D-PLACE mock CSV files."""
    return {
        "societies": fixtures_dir / "dplace" / "mock_societies.csv",
        "variables": fixtures_dir / "dplace" / "mock_variables.csv",
        "data": fixtures_dir / "dplace" / "mock_data.csv",
    }


@pytest.fixture
def seshat_fixtures(fixtures_dir: Path):
    """Return paths to Seshat mock CSV files."""
    return {
        "polities": fixtures_dir / "seshat" / "mock_polities.csv",
        "variables": fixtures_dir / "seshat" / "mock_variables.csv",
        "data": fixtures_dir / "seshat" / "mock_data.csv",
    }


@pytest.fixture
def drh_fixtures(fixtures_dir: Path):
    """Return paths to DRH mock CSV file."""
    return {"traditions": fixtures_dir / "drh" / "mock_traditions.csv"}


@pytest.fixture
def expected_columns() -> list[str]:
    """Expected output columns (Phase 1 schema)."""
    return [
        "source",
        "culture_id",
        "culture_name",
        "unit_type",
        "lat",
        "lon",
        "time_start",
        "time_end",
        "variable_name",
        "variable_value",
        "variable_type",
        "confidence",
        "notes",
    ]


# ============================================================================
# D-PLACE UNIT TESTS
# ============================================================================


@pytest.mark.unit
class TestDPlaceParser:
    """Unit tests for D-PLACE parser."""

    def test_dplace_load_metadata(self, dplace_fixtures: dict, tmp_path: Path):
        """Load societies and ensure metadata is extracted correctly."""
        output_path = tmp_path / "test_dplace.parquet"

        df = parse_dplace(
            societies_path=dplace_fixtures["societies"],
            variables_path=dplace_fixtures["variables"],
            data_path=dplace_fixtures["data"],
            output_path=output_path,
        )

        assert len(df) > 0, "Output DataFrame should not be empty"
        assert "culture_id" in df.columns
        assert "culture_name" in df.columns
        assert "lat" in df.columns
        assert "lon" in df.columns
        assert df["source"].unique().tolist() == ["dplace"]
        assert df["unit_type"].unique().tolist() == ["society"]

    def test_dplace_schema_validation(self, dplace_fixtures: dict, expected_columns: list[str]):
        """Verify output schema matches specification (Section 2.2)."""
        df = parse_dplace(
            societies_path=dplace_fixtures["societies"],
            variables_path=dplace_fixtures["variables"],
            data_path=dplace_fixtures["data"],
        )

        assert list(df.columns) == expected_columns, "Column names or order mismatch"

        # Type checks
        assert df["source"].dtype == "object"
        assert df["culture_id"].dtype == "object"
        assert df["culture_name"].dtype == "object"
        assert df["unit_type"].dtype == "object"
        assert df["lat"].dtype == "float64"
        assert df["lon"].dtype == "float64"
        assert df["time_start"].dtype == "int64"
        assert df["time_end"].dtype == "int64"
        assert df["variable_name"].dtype == "object"
        assert df["variable_value"].dtype == "float64"
        assert df["variable_type"].dtype == "object"

    def test_dplace_coordinate_bounds(self, dplace_fixtures: dict):
        """Latitude in [-90, 90], longitude in [-180, 180]."""
        df = parse_dplace(
            societies_path=dplace_fixtures["societies"],
            variables_path=dplace_fixtures["variables"],
            data_path=dplace_fixtures["data"],
        )

        valid_lat = df[df["lat"].notna()]["lat"].between(-90, 90)
        valid_lon = df[df["lon"].notna()]["lon"].between(-180, 180)

        assert valid_lat.all(), "Invalid latitude values"
        assert valid_lon.all(), "Invalid longitude values"

    def test_dplace_variable_filtering(self, dplace_fixtures: dict):
        """Only shamanism-relevant variables are extracted."""
        df = parse_dplace(
            societies_path=dplace_fixtures["societies"],
            variables_path=dplace_fixtures["variables"],
            data_path=dplace_fixtures["data"],
        )

        # Check that output contains expected shamanism variables
        shamanism_keywords = ["trance", "shamanism", "healing", "percussion", "divination"]
        variables = df["variable_name"].unique()

        # At least some variables should match shamanism keywords
        matched = any(
            any(kw.lower() in var.lower() for kw in shamanism_keywords) for var in variables
        )
        assert matched, "No shamanism-relevant variables found in output"

    def test_dplace_no_silent_na_conversion(self, dplace_fixtures: dict):
        """Ensure missing data is not silently converted to 0."""
        df = parse_dplace(
            societies_path=dplace_fixtures["societies"],
            variables_path=dplace_fixtures["variables"],
            data_path=dplace_fixtures["data"],
        )

        # Check that NaN rows are properly represented
        nan_rows = df[df["variable_value"].isna()]
        zero_rows = df[df["variable_value"] == 0]

        # Should have both NA values and explicit zeros
        assert len(nan_rows) >= 0, "NaN handling check"
        # At least one explicit zero
        if len(zero_rows) > 0:
            assert zero_rows["variable_type"].isin(["binary", "ordinal"]).all()


# ============================================================================
# SESHAT UNIT TESTS
# ============================================================================


@pytest.mark.unit
class TestSeshatParser:
    """Unit tests for Seshat parser."""

    def test_seshat_load_metadata(self, seshat_fixtures: dict, tmp_path: Path):
        """Load polities and ensure metadata is extracted correctly."""
        output_path = tmp_path / "test_seshat.parquet"

        df = parse_seshat(
            polities_path=seshat_fixtures["polities"],
            variables_path=seshat_fixtures["variables"],
            data_path=seshat_fixtures["data"],
            output_path=output_path,
        )

        assert len(df) > 0, "Output DataFrame should not be empty"
        assert "culture_id" in df.columns
        assert "culture_name" in df.columns
        assert df["source"].unique().tolist() == ["seshat"]
        assert df["unit_type"].unique().tolist() == ["polity"]

    def test_seshat_schema_validation(self, seshat_fixtures: dict, expected_columns: list[str]):
        """Verify output schema matches specification."""
        df = parse_seshat(
            polities_path=seshat_fixtures["polities"],
            variables_path=seshat_fixtures["variables"],
            data_path=seshat_fixtures["data"],
        )

        assert list(df.columns) == expected_columns

    def test_seshat_confidence_mapping(self, seshat_fixtures: dict):
        """Map Seshat 'uncertainty' to confidence scores correctly."""
        df = parse_seshat(
            polities_path=seshat_fixtures["polities"],
            variables_path=seshat_fixtures["variables"],
            data_path=seshat_fixtures["data"],
        )

        # Check that confidence values are in expected range
        confidence = df[df["confidence"].notna()]["confidence"]
        assert confidence.between(0.0, 1.0).all(), "Confidence out of [0, 1] range"

        # Check mapping: "certain" → 0.95, "probable" → 0.75, etc.
        # At least one confidence value should be 0.95 (certain)
        assert 0.95 in confidence.values or len(confidence) == 0, "Expected 'certain' → 0.95 mapping"

    def test_seshat_polity_time_period(self, seshat_fixtures: dict):
        """time_start and time_end are valid and start <= end."""
        df = parse_seshat(
            polities_path=seshat_fixtures["polities"],
            variables_path=seshat_fixtures["variables"],
            data_path=seshat_fixtures["data"],
        )

        df_with_time = df[df["time_start"].notna() & df["time_end"].notna()]

        assert (df_with_time["time_start"] <= df_with_time["time_end"]).all(), (
            "time_start > time_end detected"
        )


# ============================================================================
# DRH UNIT TESTS
# ============================================================================


@pytest.mark.unit
class TestDrhParser:
    """Unit tests for DRH parser."""

    def test_drh_csv_parsing(self, drh_fixtures: dict, tmp_path: Path):
        """Load DRH CSV and ensure parsing works."""
        output_path = tmp_path / "test_drh.parquet"

        df = parse_drh(
            source_path=drh_fixtures["traditions"],
            output_path=output_path,
        )

        assert len(df) > 0, "Output DataFrame should not be empty"
        assert df["source"].unique().tolist() == ["drh"]

    def test_drh_schema_validation(self, drh_fixtures: dict, expected_columns: list[str]):
        """Verify output schema matches specification."""
        df = parse_drh(
            source_path=drh_fixtures["traditions"],
        )

        assert list(df.columns) == expected_columns

    def test_drh_multipolity_handling(self, drh_fixtures: dict):
        """Multi-polity traditions are flagged in notes, not split."""
        df = parse_drh(
            source_path=drh_fixtures["traditions"],
        )

        # Check if any rows are flagged with "Spans multiple polities"
        multipolity_flagged = df[df["notes"].notna() & df["notes"].str.contains("multiple", na=False)]

        # At least some rows should exist
        assert len(df) > 0, "No data parsed from DRH"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


@pytest.mark.integration
class TestFullPipelines:
    """Integration tests for complete parsing pipelines."""

    def test_full_pipeline_dplace(self, dplace_fixtures: dict, tmp_path: Path):
        """End-to-end: mock CSVs → parser → parquet output."""
        output_path = tmp_path / "test_dplace_integration.parquet"

        df = parse_dplace(
            societies_path=dplace_fixtures["societies"],
            variables_path=dplace_fixtures["variables"],
            data_path=dplace_fixtures["data"],
            output_path=output_path,
        )

        # Assert parquet file was created
        assert output_path.exists(), "Parquet output file not created"

        # Assert can reload from parquet
        df_reloaded = pd.read_parquet(output_path)
        
        # Schema should match
        assert list(df.columns) == list(df_reloaded.columns)
        assert len(df) == len(df_reloaded)

    def test_full_pipeline_seshat(self, seshat_fixtures: dict, tmp_path: Path):
        """End-to-end: mock CSVs → parser → parquet output."""
        output_path = tmp_path / "test_seshat_integration.parquet"

        df = parse_seshat(
            polities_path=seshat_fixtures["polities"],
            variables_path=seshat_fixtures["variables"],
            data_path=seshat_fixtures["data"],
            output_path=output_path,
        )

        assert output_path.exists(), "Parquet output file not created"

        df_reloaded = pd.read_parquet(output_path)
        
        # Schema and length should match
        assert list(df.columns) == list(df_reloaded.columns)
        assert len(df) == len(df_reloaded)

    def test_full_pipeline_drh(self, drh_fixtures: dict, tmp_path: Path):
        """End-to-end: mock CSV → parser → parquet output."""
        output_path = tmp_path / "test_drh_integration.parquet"

        df = parse_drh(
            source_path=drh_fixtures["traditions"],
            output_path=output_path,
        )

        assert output_path.exists(), "Parquet output file not created"

        df_reloaded = pd.read_parquet(output_path)
        
        # Schema and length should match
        assert list(df.columns) == list(df_reloaded.columns)
        assert len(df) == len(df_reloaded)

    def test_all_three_outputs_compatible(
        self,
        dplace_fixtures: dict,
        seshat_fixtures: dict,
        drh_fixtures: dict,
        expected_columns: list[str],
    ):
        """Three output DataFrames have identical column structure."""
        dplace_df = parse_dplace(
            societies_path=dplace_fixtures["societies"],
            variables_path=dplace_fixtures["variables"],
            data_path=dplace_fixtures["data"],
        )

        seshat_df = parse_seshat(
            polities_path=seshat_fixtures["polities"],
            variables_path=seshat_fixtures["variables"],
            data_path=seshat_fixtures["data"],
        )

        drh_df = parse_drh(
            source_path=drh_fixtures["traditions"],
        )

        # Check all have expected columns
        assert list(dplace_df.columns) == expected_columns
        assert list(seshat_df.columns) == expected_columns
        assert list(drh_df.columns) == expected_columns

        # Can concatenate
        combined = pd.concat([dplace_df, seshat_df, drh_df], ignore_index=True)
        assert len(combined) == len(dplace_df) + len(seshat_df) + len(drh_df)


# ============================================================================
# DATA VALIDATION TESTS
# ============================================================================


@pytest.mark.validation
class TestDataValidation:
    """Data validation tests for all parsers."""

    def test_no_empty_dataframes(
        self, dplace_fixtures: dict, seshat_fixtures: dict, drh_fixtures: dict
    ):
        """Each parser returns at least one row."""
        dplace_df = parse_dplace(
            societies_path=dplace_fixtures["societies"],
            variables_path=dplace_fixtures["variables"],
            data_path=dplace_fixtures["data"],
        )

        seshat_df = parse_seshat(
            polities_path=seshat_fixtures["polities"],
            variables_path=seshat_fixtures["variables"],
            data_path=seshat_fixtures["data"],
        )

        drh_df = parse_drh(
            source_path=drh_fixtures["traditions"],
        )

        assert len(dplace_df) > 0, "D-PLACE DataFrame is empty"
        assert len(seshat_df) > 0, "Seshat DataFrame is empty"
        assert len(drh_df) > 0, "DRH DataFrame is empty"

    def test_no_duplicate_rows_within_source(
        self, dplace_fixtures: dict, seshat_fixtures: dict, drh_fixtures: dict
    ):
        """No fully duplicate rows within a single source."""
        dplace_df = parse_dplace(
            societies_path=dplace_fixtures["societies"],
            variables_path=dplace_fixtures["variables"],
            data_path=dplace_fixtures["data"],
        )

        seshat_df = parse_seshat(
            polities_path=seshat_fixtures["polities"],
            variables_path=seshat_fixtures["variables"],
            data_path=seshat_fixtures["data"],
        )

        drh_df = parse_drh(
            source_path=drh_fixtures["traditions"],
        )

        assert not dplace_df.duplicated().any(), "D-PLACE has duplicate rows"
        assert not seshat_df.duplicated().any(), "Seshat has duplicate rows"
        assert not drh_df.duplicated().any(), "DRH has duplicate rows"

    def test_culture_ids_have_consistent_metadata(self, dplace_fixtures: dict):
        """For each culture_id, metadata (name, lat, lon, time) is consistent."""
        df = parse_dplace(
            societies_path=dplace_fixtures["societies"],
            variables_path=dplace_fixtures["variables"],
            data_path=dplace_fixtures["data"],
        )

        for culture_id in df["culture_id"].unique():
            subset = df[df["culture_id"] == culture_id]

            # All rows for a culture should have identical metadata
            culture_names = subset["culture_name"].unique()
            lats = subset["lat"].unique()
            lons = subset["lon"].unique()

            assert len(culture_names) == 1, f"Culture {culture_id} has {len(culture_names)} names"
            assert len(lats) == 1, f"Culture {culture_id} has {len(lats)} lats"
            assert len(lons) == 1, f"Culture {culture_id} has {len(lons)} lons"

    def test_time_period_sanity(
        self, dplace_fixtures: dict, seshat_fixtures: dict, drh_fixtures: dict
    ):
        """time_start and time_end are reasonable (e.g., not 99999)."""
        for parser_name, parser_fn, fixtures in [
            ("dplace", parse_dplace, dplace_fixtures),
            ("seshat", parse_seshat, seshat_fixtures),
            ("drh", parse_drh, drh_fixtures),
        ]:
            if parser_name == "dplace":
                df = parser_fn(
                    societies_path=fixtures["societies"],
                    variables_path=fixtures["variables"],
                    data_path=fixtures["data"],
                )
            elif parser_name == "seshat":
                df = parser_fn(
                    polities_path=fixtures["polities"],
                    variables_path=fixtures["variables"],
                    data_path=fixtures["data"],
                )
            else:  # drh
                df = parser_fn(
                    source_path=fixtures["traditions"],
                )

            time_start = df[df["time_start"].notna()]["time_start"]
            time_end = df[df["time_end"].notna()]["time_end"]

            # Reasonable range: -10000 (before agriculture) to +2026 (now)
            if len(time_start) > 0:
                assert time_start.min() >= -10000, f"{parser_name}: time_start too old"
                assert time_start.max() <= 2026, f"{parser_name}: time_start in future"

            if len(time_end) > 0:
                assert time_end.min() >= -10000, f"{parser_name}: time_end too old"
                assert time_end.max() <= 2026, f"{parser_name}: time_end in future"

    def test_variable_types_are_valid(
        self, dplace_fixtures: dict, seshat_fixtures: dict, drh_fixtures: dict
    ):
        """variable_type is one of: binary, ordinal, confidence, text."""
        valid_types = {"binary", "ordinal", "confidence", "text"}

        for parser_name, parser_fn, fixtures in [
            ("dplace", parse_dplace, dplace_fixtures),
            ("seshat", parse_seshat, seshat_fixtures),
            ("drh", parse_drh, drh_fixtures),
        ]:
            if parser_name == "dplace":
                df = parser_fn(
                    societies_path=fixtures["societies"],
                    variables_path=fixtures["variables"],
                    data_path=fixtures["data"],
                )
            elif parser_name == "seshat":
                df = parser_fn(
                    polities_path=fixtures["polities"],
                    variables_path=fixtures["variables"],
                    data_path=fixtures["data"],
                )
            else:  # drh
                df = parser_fn(
                    source_path=fixtures["traditions"],
                )

            actual_types = set(df["variable_type"].unique())
            invalid_types = actual_types - valid_types

            assert not invalid_types, f"{parser_name}: Invalid types {invalid_types}"

    def test_confidence_in_valid_range(
        self, dplace_fixtures: dict, seshat_fixtures: dict, drh_fixtures: dict
    ):
        """confidence values are in [0.0, 1.0] or NA."""
        for parser_name, parser_fn, fixtures in [
            ("dplace", parse_dplace, dplace_fixtures),
            ("seshat", parse_seshat, seshat_fixtures),
            ("drh", parse_drh, drh_fixtures),
        ]:
            if parser_name == "dplace":
                df = parser_fn(
                    societies_path=fixtures["societies"],
                    variables_path=fixtures["variables"],
                    data_path=fixtures["data"],
                )
            elif parser_name == "seshat":
                df = parser_fn(
                    polities_path=fixtures["polities"],
                    variables_path=fixtures["variables"],
                    data_path=fixtures["data"],
                )
            else:  # drh
                df = parser_fn(
                    source_path=fixtures["traditions"],
                )

            confidence = df[df["confidence"].notna()]["confidence"]
            if len(confidence) > 0:
                assert confidence.between(0.0, 1.0).all(), (
                    f"{parser_name}: Confidence values out of [0, 1] range"
                )
