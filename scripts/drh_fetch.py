#!/usr/bin/env python3
"""
Fetch DRH (Database of Religious History) entry metadata via the public GraphQL API.

The DRH GraphQL endpoint (https://religiondatabase.org/graphql/) exposes entry
metadata (name, year, region, poll_type) but NOT question answers — those require
authenticated access.  This script:

  1. Queries the DRH for all religious_group entries matching shamanism/trance/spirit
     keywords (yielding ~125 traditions).
  2. Saves their metadata to data/raw/drh/drh_entries_metadata.csv.
  3. Rebuilds data/raw/drh/drh_sample.csv in the correct DRH question-column format,
     using the real entry names from the API and leaving answer columns as "unk" for
     entries without verified coding.  Five well-known traditions retain literature-
     derived coding (documented below).

IMPORTANT: Full DRH answer integration requires either:
  - Authenticated API access (register at religiondatabase.org)
  - Manual CSV export from the DRH web interface (Browse → Export)
    with question IDs: 4944, 4861, 4892, 4862, 4893, 4945, 4776, 4779, 2903, 3282

Usage:
    python scripts/drh_fetch.py
"""

import csv
import json
import time
from pathlib import Path

import requests

DRH_GRAPHQL = "https://religiondatabase.org/graphql/"
OUT_METADATA = Path("data/raw/drh/drh_entries_metadata.csv")
OUT_SAMPLE = Path("data/raw/drh/drh_sample.csv")

# ---------------------------------------------------------------------------
# Real DRH question column names (from question_search API, Religious Group v6)
# These match the actual text shown in CSV exports from religiondatabase.org
# ---------------------------------------------------------------------------
QUESTION_COLS = [
    "In trance possession:",          # Q4944 / Q4861 — trance / spirit possession
    "Through divination practices:",  # Q4862 / Q4945 — divination
    "Is a spirit-body distinction present:",  # Q4776 — soul concept
    "Physical healing",               # healing function (Religious Group v6)
    "Through divination processes:",  # Q4893 — divination (v5/v6 alt phrasing)
    "Other spirit-body relationship:",  # Q4779 — spirit possession variant
]

# ---------------------------------------------------------------------------
# Literature-derived coding for 5 well-known traditions (clearly documented)
# Sources: Eliade 1964, Winkelman 2010, Harvey 2003, Kim 2003
# "yes" / "no" / "unk" maps to 1 / 0 / NA in the feature matrix
# ---------------------------------------------------------------------------
KNOWN_ANSWERS = {
    "Postsocialist Mongolian Shamanism": {
        "In trance possession:": "yes",
        "Through divination practices:": "yes",
        "Is a spirit-body distinction present:": "yes",
        "Physical healing": "yes",
        "Through divination processes:": "yes",
        "Other spirit-body relationship:": "yes",
    },
    "Korean shamanism": {
        "In trance possession:": "yes",
        "Through divination practices:": "yes",
        "Is a spirit-body distinction present:": "yes",
        "Physical healing": "yes",
        "Through divination processes:": "yes",
        "Other spirit-body relationship:": "yes",
    },
    "Tyva Republic (Animism-Totemism-Shamanism)": {
        "In trance possession:": "yes",
        "Through divination practices:": "yes",
        "Is a spirit-body distinction present:": "yes",
        "Physical healing": "yes",
        "Through divination processes:": "yes",
        "Other spirit-body relationship:": "yes",
    },
    "Sufi Islam": {
        "In trance possession:": "yes",
        "Through divination practices:": "no",
        "Is a spirit-body distinction present:": "yes",
        "Physical healing": "no",
        "Through divination processes:": "no",
        "Other spirit-body relationship:": "yes",
    },
    "Tibetan Buddhism": {
        "In trance possession:": "yes",
        "Through divination practices:": "yes",
        "Is a spirit-body distinction present:": "yes",
        "Physical healing": "yes",
        "Through divination processes:": "yes",
        "Other spirit-body relationship:": "yes",
    },
}

SEARCH_QUERIES = [
    "shamanism", "trance", "spirit possession", "animism shaman",
    "healing ritual", "soul journey", "divination spirit",
]


def gql(query: str) -> dict:
    resp = requests.post(
        DRH_GRAPHQL,
        json={"query": query},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_all_entries() -> list[dict]:
    """Fetch all religious_group entries matching shamanism-related searches."""
    seen_ids = set()
    entries = []

    for search_q in SEARCH_QUERIES:
        after = None
        while True:
            after_arg = f', after: "{after}"' if after else ""
            result = gql(f"""
            {{
              entry_search_connection(query: "{search_q}", first: 50{after_arg}) {{
                count
                pageInfo {{ hasNextPage endCursor }}
                edges {{
                  node {{
                    id name poll_type year_from year_to
                    region {{ name }}
                  }}
                }}
              }}
            }}
            """)
            conn = result["data"]["entry_search_connection"]
            for edge in conn["edges"]:
                node = edge["node"]
                if node["poll_type"] != "religious_group":
                    continue
                if node["id"] in seen_ids:
                    continue
                seen_ids.add(node["id"])
                entries.append({
                    "drh_id": node["id"],
                    "name": node["name"] or "",
                    "poll_type": node["poll_type"],
                    "year_from": node.get("year_from"),
                    "year_to": node.get("year_to"),
                    "region": (node.get("region") or {}).get("name", ""),
                })
            page = conn["pageInfo"]
            if not page["hasNextPage"]:
                break
            after = page["endCursor"]
            time.sleep(0.3)

        time.sleep(0.5)

    print(f"Fetched {len(entries)} unique religious_group entries")
    return entries


def save_metadata(entries: list[dict]) -> None:
    OUT_METADATA.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_METADATA, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["drh_id", "name", "poll_type",
                                               "year_from", "year_to", "region"])
        writer.writeheader()
        writer.writerows(entries)
    print(f"Saved metadata → {OUT_METADATA}")


def build_sample_csv(entries: list[dict]) -> None:
    """
    Build drh_sample.csv with correct DRH question columns.
    Answers sourced from:
      - KNOWN_ANSWERS dict (literature-derived, 5 traditions)
      - "unk" for all others (pending authenticated DRH export)
    """
    fieldnames = ["Entry name", "Start Date", "End Date", "Region"] + QUESTION_COLS

    rows = []
    for e in entries:
        answers = KNOWN_ANSWERS.get(e["name"], {})
        row = {
            "Entry name": e["name"],
            "Start Date": e["year_from"] if e["year_from"] is not None else "",
            "End Date": e["year_to"] if e["year_to"] is not None else "",
            "Region": e["region"],
        }
        for col in QUESTION_COLS:
            row[col] = answers.get(col, "unk")
        rows.append(row)

    # Deduplicate by name (keep first occurrence)
    seen_names = set()
    deduped = []
    for r in rows:
        if r["Entry name"] not in seen_names:
            seen_names.add(r["Entry name"])
            deduped.append(r)

    OUT_SAMPLE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_SAMPLE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(deduped)

    coded = sum(1 for r in deduped if any(r[c] != "unk" for c in QUESTION_COLS))
    print(f"Saved {len(deduped)} entries to {OUT_SAMPLE}")
    print(f"  - {coded} with literature-coded answers")
    print(f"  - {len(deduped) - coded} with 'unk' (pending DRH authenticated export)")


def main():
    print("\n" + "=" * 60)
    print("DRH DATA FETCH (GraphQL API)")
    print("=" * 60 + "\n")

    entries = fetch_all_entries()
    save_metadata(entries)
    build_sample_csv(entries)

    print("\nNOTE: Full answer integration requires authenticated DRH access.")
    print("      Download CSV from religiondatabase.org/browse/ with question IDs:")
    print("      4944, 4861, 4892, 4862, 4893, 4945, 4776, 4779, 2903, 3282")
    print("      Then replace data/raw/drh/drh_sample.csv with the export.\n")


if __name__ == "__main__":
    main()
