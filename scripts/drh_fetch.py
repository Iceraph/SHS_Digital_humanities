#!/usr/bin/env python3
"""
Fetch DRH (Database of Religious History) entry metadata and answers via public APIs.

Two endpoints used (both publicly accessible without authentication):
  1. GraphQL at https://religiondatabase.org/graphql/ — entry metadata
     (name, year, region, poll_type) via entry_search_connection.
  2. Hasura at https://religiondatabase.org/v1/graphql — full answer data
     via polls_baseanswerset table (published answers only).

Pipeline:
  1. Query DRH GraphQL for all religious_group entries matching shamanism/trance/spirit
     keywords (~240 traditions).
  2. Decode base64 entry IDs → integer IDs for Hasura queries.
  3. Batch-fetch published answers for all target question IDs via Hasura.
  4. Build data/raw/drh/drh_sample.csv with real yes/no answers.
  5. Save entry metadata to data/raw/drh/drh_entries_metadata.csv.

Usage:
    python scripts/drh_fetch.py
"""

import base64
import csv
import json
import time
from pathlib import Path

import requests

DRH_GRAPHQL = "https://religiondatabase.org/graphql/"
DRH_HASURA  = "https://religiondatabase.org/v1/graphql"

OUT_METADATA = Path("data/raw/drh/drh_entries_metadata.csv")
OUT_SAMPLE   = Path("data/raw/drh/drh_sample.csv")

# ---------------------------------------------------------------------------
# Target question IDs (Religious Group poll, confirmed via Hasura introspection)
# Multiple IDs per concept reflect different poll versions (v5/v6/v7)
# ---------------------------------------------------------------------------
TARGET_QUESTION_IDS = [
    # Trance / spirit possession
    4861, 4892, 4944,
    # Through divination (two phrasings)
    4862, 4893, 4945,
    # Spirit-body distinction
    4776, 4777, 4778, 4779,
    # Healing
    4780,
    # Other / older poll versions
    2903, 3282, 3278, 3295, 3310,
]

# Question name → canonical column name in output CSV
QUESTION_NAME_MAP = {
    "In trance possession:":                      "In trance possession:",
    "Through divination practices:":              "Through divination practices:",
    "Through divination processes:":              "Through divination processes:",
    "Is a spirit-body distinction present:":      "Is a spirit-body distinction present:",
    "Other spirit-body relationship:":            "Other spirit-body relationship:",
    "Spirit-mind is conceived of as having qualitatively different powers or properties than other body parts:":
                                                  "Spirit distinct powers:",
    "Spirit-mind is conceived of as non-material, ontologically distinct from body:":
                                                  "Spirit non-material:",
    "Belief in afterlife:":                       "Belief in afterlife:",
    # Older poll phrasings
    "In trance possession":                       "In trance possession:",
    "Through divination practices":               "Through divination practices:",
    "Through divination processes":               "Through divination processes:",
}

QUESTION_COLS = list(dict.fromkeys(QUESTION_NAME_MAP.values()))  # ordered unique

SEARCH_QUERIES = [
    "shamanism", "trance", "spirit possession", "animism shaman",
    "healing ritual", "soul journey", "divination spirit",
]

# Answer value → yes/no/unk
def _answer_text(answers: list) -> str:
    """Convert Hasura answer list to yes/no/unk string."""
    if not answers:
        return "unk"
    val = answers[0].get("value")
    if val == 1:
        return "yes"
    if val == 0:
        return "no"
    name = (answers[0].get("name") or "").lower()
    if name.startswith("yes"):
        return "yes"
    if name.startswith("no"):
        return "no"
    return "unk"


# ---------------------------------------------------------------------------
# GraphQL helper
# ---------------------------------------------------------------------------
def gql(endpoint: str, query: str) -> dict:
    resp = requests.post(
        endpoint,
        json={"query": query},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Step 1: Fetch entry metadata from DRH GraphQL
# ---------------------------------------------------------------------------
def fetch_all_entries() -> list[dict]:
    seen_ids: set = set()
    entries: list[dict] = []

    for search_q in SEARCH_QUERIES:
        after = None
        while True:
            after_arg = f', after: "{after}"' if after else ""
            result = gql(DRH_GRAPHQL, f"""
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

                # Decode base64 ID → integer (e.g. "RW50cnk6ODg3" → "Entry:887" → 887)
                try:
                    decoded = base64.b64decode(node["id"]).decode()
                    int_id = int(decoded.split(":")[-1])
                except Exception:
                    int_id = None

                entries.append({
                    "drh_id":   node["id"],
                    "int_id":   int_id,
                    "name":     node["name"] or "",
                    "poll_type": node["poll_type"],
                    "year_from": node.get("year_from"),
                    "year_to":   node.get("year_to"),
                    "region":   (node.get("region") or {}).get("name", ""),
                })
            page = conn["pageInfo"]
            if not page["hasNextPage"]:
                break
            after = page["endCursor"]
            time.sleep(0.3)
        time.sleep(0.5)

    print(f"Fetched {len(entries)} unique religious_group entries")
    return entries


# ---------------------------------------------------------------------------
# Step 2: Fetch answers from Hasura in batches
# ---------------------------------------------------------------------------
def fetch_answers(int_ids: list[int], batch_size: int = 50) -> dict[int, dict[str, str]]:
    """
    Returns {entry_int_id: {col_name: "yes"/"no"/"unk"}} for all entries.
    Queries Hasura in batches of `batch_size` entries.
    """
    answers_by_entry: dict[int, dict[str, str]] = {eid: {} for eid in int_ids}
    q_ids_str = ", ".join(str(q) for q in TARGET_QUESTION_IDS)

    total = len(int_ids)
    fetched = 0

    for i in range(0, total, batch_size):
        batch = int_ids[i : i + batch_size]
        ids_str = ", ".join(str(e) for e in batch)

        query = f"""
        {{
          polls_baseanswerset(where: {{
            entry_id: {{_in: [{ids_str}]}},
            question_id: {{_in: [{q_ids_str}]}},
            answer_sets: {{published: {{_eq: true}}}}
          }}) {{
            entry_id
            question_id
            question {{ name }}
            answers {{ value name }}
          }}
        }}
        """
        result = gql(DRH_HASURA, query)
        rows = result["data"]["polls_baseanswerset"]

        for row in rows:
            eid = row["entry_id"]
            q_name = row["question"]["name"]
            col = QUESTION_NAME_MAP.get(q_name)
            if col is None:
                continue
            # Take first/only answer; don't overwrite an existing "yes" with something else
            existing = answers_by_entry[eid].get(col, "unk")
            new_val = _answer_text(row["answers"])
            if existing == "unk" or (existing == "no" and new_val == "yes"):
                answers_by_entry[eid][col] = new_val

        fetched += len(batch)
        print(f"  Fetched answers for {fetched}/{total} entries...", end="\r")
        time.sleep(0.3)

    print()
    coded = sum(1 for v in answers_by_entry.values() if any(x != "unk" for x in v.values()))
    print(f"  {coded} entries have at least one coded answer")
    return answers_by_entry


# ---------------------------------------------------------------------------
# Step 3: Save metadata CSV
# ---------------------------------------------------------------------------
def save_metadata(entries: list[dict]) -> None:
    OUT_METADATA.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_METADATA, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["drh_id", "int_id", "name", "poll_type", "year_from", "year_to", "region"]
        )
        writer.writeheader()
        writer.writerows(entries)
    print(f"Saved metadata → {OUT_METADATA}")


# ---------------------------------------------------------------------------
# Step 4: Build drh_sample.csv
# ---------------------------------------------------------------------------
def build_sample_csv(entries: list[dict], answers_by_entry: dict[int, dict[str, str]]) -> None:
    fieldnames = ["Entry name", "Start Date", "End Date", "Region"] + QUESTION_COLS

    rows = []
    for e in entries:
        int_id = e["int_id"]
        ans = answers_by_entry.get(int_id, {})
        row = {
            "Entry name": e["name"],
            "Start Date": e["year_from"] if e["year_from"] is not None else "",
            "End Date":   e["year_to"]   if e["year_to"]   is not None else "",
            "Region":     e["region"],
        }
        for col in QUESTION_COLS:
            row[col] = ans.get(col, "unk")
        rows.append(row)

    # Deduplicate by name
    seen_names: set = set()
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
    print(f"Saved {len(deduped)} entries → {OUT_SAMPLE}")
    print(f"  {coded} with at least one coded answer")
    print(f"  {len(deduped) - coded} with all 'unk' (no matching published answers)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("\n" + "=" * 60)
    print("DRH DATA FETCH (GraphQL + Hasura)")
    print("=" * 60 + "\n")

    entries = fetch_all_entries()
    save_metadata(entries)

    int_ids = [e["int_id"] for e in entries if e["int_id"] is not None]
    print(f"\nFetching answers for {len(int_ids)} entries via Hasura...")
    answers_by_entry = fetch_answers(int_ids)

    build_sample_csv(entries, answers_by_entry)


if __name__ == "__main__":
    main()
