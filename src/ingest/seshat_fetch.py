"""Seshat API fetcher.

Pulls polity metadata and shamanism-relevant variables from the public
Seshat REST API at https://seshat-db.com/api (no authentication required).

Outputs three CSVs to ``data/raw/seshat/`` matching the input contract of
``parse_seshat`` in :mod:`src.ingest.seshat`:

- polities.csv : id, name, latitude, longitude, start_year, end_year, region
- variables.csv : id, name, endpoint, value_field
- data.csv     : polity_id, var_id, value, uncertainty, year_from, year_to

Variables fetched are those that map (per ``data/reference/crosswalk.csv``)
to the shamanism feature schema:

==============================  =====================  =====================
Endpoint                        Value field            Maps to feature
==============================  =====================  =====================
sc/professional-priesthoods     professional_priest..  dedicated_specialist
sc/religious-levels             religious_level_from   dedicated_specialist
rt/human-sacrifices             human_sacrifice        ritual_practice
rt/moralizing-supernatural-...  (boolean fields)       supernatural beliefs
==============================  =====================  =====================

Reference: https://github.com/Seshat-Global-History-Databank/seshat_api
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
import requests

API_BASE = "https://seshat-db.com/api"

SHAMANISM_VARIABLES: list[dict[str, str]] = [
    {
        "endpoint": "sc/professional-priesthoods",
        "value_field": "professional_priesthood",
        "var_id": "professional_priesthood",
        "var_name": "Professional priesthood",
    },
    {
        "endpoint": "sc/religious-levels",
        "value_field": "religious_level_from",
        "var_id": "religious_level",
        "var_name": "Religious organisational levels",
    },
    {
        "endpoint": "rt/human-sacrifices",
        "value_field": "human_sacrifice",
        "var_id": "human_sacrifice",
        "var_name": "Human sacrifice",
    },
    {
        "endpoint": "rt/moralizing-supernatural-punishment-and-reward",
        "value_field": "coded_value",
        "var_id": "moralizing_supernatural",
        "var_name": "Moralizing supernatural punishment and reward",
    },
    {
        "endpoint": "rt/moralizing-enforcement-is-agentic",
        "value_field": "coded_value",
        "var_id": "moralizing_agentic",
        "var_name": "Moralizing supernatural agent",
    },
]

# Categorical → numeric encoding for present/absent fields.
# "U" / "DIS" / "Unknown" are treated as NA (not 0).
PRESENT_ABSENT_MAP: dict[str, float] = {
    "present": 1.0,
    "P": 1.0,
    "absent": 0.0,
    "A": 0.0,
    "inferred present": 1.0,
    "IP": 1.0,
    "inferred absent": 0.0,
    "IA": 0.0,
    "true": 1.0,
    "false": 0.0,
}


def _paginate(endpoint: str, page_size: int = 100) -> Iterable[dict]:
    """Yield every record from a paginated Seshat endpoint."""
    url = f"{API_BASE}/{endpoint}/"
    params: dict[str, int] | None = {"page_size": page_size}
    while url:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        payload = response.json()
        yield from payload.get("results", [])
        url = payload.get("next")
        params = None  # `next` already contains the page parameter


def fetch_polities(output_path: Path) -> pd.DataFrame:
    """Fetch all polities and write polities.csv with parser-compatible columns."""
    rows: list[dict] = []
    for polity in _paginate("core/polities", page_size=100):
        nga = polity.get("home_nga") or {}
        region = (polity.get("home_seshat_region") or {}).get("name")
        rows.append(
            {
                "id": polity["id"],
                "name": polity.get("long_name") or polity.get("name"),
                "polity_code": polity.get("name"),
                "latitude": float(nga["latitude"]) if nga.get("latitude") else None,
                "longitude": float(nga["longitude"]) if nga.get("longitude") else None,
                "start_year": polity.get("start_year"),
                "end_year": polity.get("end_year"),
                "region": region,
            }
        )
    df = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return df


def _encode_value(raw: object) -> float | None:
    """Encode a Seshat variable value as float, or None for unknown/missing."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return 1.0 if raw else 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip()
    if not text:
        return None
    return PRESENT_ABSENT_MAP.get(text.lower(), PRESENT_ABSENT_MAP.get(text))


def fetch_variable_records(spec: dict[str, str]) -> list[dict]:
    """Fetch all observations for a single variable spec."""
    rows: list[dict] = []
    for record in _paginate(spec["endpoint"], page_size=100):
        polity = record.get("polity") or {}
        polity_id = polity.get("id")
        if polity_id is None:
            continue
        raw_value = record.get(spec["value_field"])
        rows.append(
            {
                "polity_id": polity_id,
                "var_id": spec["var_id"],
                "raw_value": raw_value,
                "value": _encode_value(raw_value),
                "uncertainty": "uncertain" if record.get("is_uncertain") else "certain",
                "is_disputed": record.get("is_disputed", False),
                "year_from": record.get("year_from"),
                "year_to": record.get("year_to"),
            }
        )
    return rows


def fetch_seshat_all(output_dir: Path = Path("data/raw/seshat")) -> dict[str, Path]:
    """Fetch polities + shamanism-relevant variables.

    Returns
    -------
    dict[str, Path]
        Paths to the three CSVs written: polities, variables, data.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    polities_path = output_dir / "polities.csv"
    variables_path = output_dir / "variables.csv"
    data_path = output_dir / "data.csv"

    print(f"[seshat] fetching polities → {polities_path}")
    polities_df = fetch_polities(polities_path)
    print(f"[seshat]   {len(polities_df)} polities")

    all_data_rows: list[dict] = []
    for spec in SHAMANISM_VARIABLES:
        print(f"[seshat] fetching {spec['endpoint']}")
        rows = fetch_variable_records(spec)
        print(f"[seshat]   {len(rows)} observations")
        all_data_rows.extend(rows)

    pd.DataFrame(SHAMANISM_VARIABLES).rename(
        columns={"var_id": "id", "var_name": "name"}
    ).to_csv(variables_path, index=False)
    pd.DataFrame(all_data_rows).to_csv(data_path, index=False)

    print(f"[seshat] wrote {len(all_data_rows)} rows → {data_path}")
    return {"polities": polities_path, "variables": variables_path, "data": data_path}


def fetch_seshat_equinox2020(
    output_dir: Path = Path("data/raw/seshat"),
) -> bool:
    """Backwards-compat wrapper preserved for parse_seshat's auto_fetch hook."""
    try:
        fetch_seshat_all(output_dir)
        return True
    except requests.exceptions.RequestException as exc:
        print(f"[seshat] fetch failed: {exc}")
        return False


if __name__ == "__main__":
    fetch_seshat_all()
