#!/usr/bin/env python3
"""
Assign cluster labels to the 462 D-PLACE cultures that were excluded from
the multi-source k-means fit by the phylogenetic filter.

These cultures have ≥1 feature coded but were deliberately left out of the
training set (one-per-language-family rule). We assign them to the nearest
cluster centroid in standardised feature space — a predict step, not a refit.

Cultures with 0 coded features (841 total: 633 D-PLACE + 146 Seshat + 62 DRH)
remain unassigned (cluster_id = NaN) — there is no feature information to
place them.

Outputs
-------
data/processed/clusters/multisource/culture_cluster_membership_k8.csv
    Updated in-place: 1,384 original rows + up to 462 new rows.
    New rows carry method = "nearest_centroid".

phase7_visualization/data/cultures_metadata.json
    Updated in-place: cluster field filled for newly assigned cultures.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

CLUSTERING_FEATURES = [
    "ancestor_mediation", "animal_transformation", "chanting_singing",
    "dedicated_specialist", "divination", "entheogen_use", "healing_function",
    "hereditary_transmission", "initiatory_crisis", "initiatory_ordeal",
    "layered_cosmology", "nature_spirits", "possession_crisis",
    "public_performance", "rhythmic_percussion", "ritual_performance",
    "soul_flight", "specialist_presence", "spirit_possession",
    "trance_induction", "unmapped_shamanic_indicators",
]

MULTISOURCE_DIR  = ROOT / "data/processed/clusters/multisource"
MEMBERSHIP_FILE  = MULTISOURCE_DIR / "culture_cluster_membership_k8.csv"  # k=8 is what the viz uses
FEATURE_MATRIX  = ROOT / "data/processed/feature_matrix.parquet"
CULTURES_JSON   = ROOT / "phase7_visualization/data/cultures_metadata.json"


def build_centroids(
    fm: pd.DataFrame,
    membership: pd.DataFrame,
    features: list[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """
    Derive cluster centroids in standardised feature space from the
    already-fitted training set.

    Only uses features that have at least one non-NaN value in the training
    set — the original multisource clustering was built from harmonised
    parquets and only included features actually coded there.

    Returns
    -------
    centroids    : (k, n_active) array in standardised space
    train_mean   : (n_active,) column means of training set
    train_std    : (n_active,) column stds  of training set (0-var cols → 1)
    cluster_ids  : (k,) sorted cluster label array
    active_feats : list of feature names actually used
    """
    training = fm[fm["culture_id"].isin(membership["culture_id"])].copy()
    training = training.merge(membership[["culture_id", "cluster_id"]], on="culture_id", how="left")

    X_all = training[features].astype(float).values

    # Drop columns that are entirely NaN in the training set
    col_has_data = ~np.all(np.isnan(X_all), axis=0)
    active_feats = [f for f, ok in zip(features, col_has_data) if ok]
    X_train = X_all[:, col_has_data]

    print(f"  Active features ({len(active_feats)}/{len(features)}): {active_feats}")

    train_mean = np.nanmean(X_train, axis=0)
    train_std  = np.nanstd(X_train, axis=0)
    train_std[train_std == 0] = 1.0

    X_filled = np.where(np.isnan(X_train), train_mean, X_train)
    X_scaled  = (X_filled - train_mean) / train_std

    cluster_ids = sorted(training["cluster_id"].dropna().unique().astype(int))
    centroids = np.array([
        X_scaled[training["cluster_id"].values == c].mean(axis=0)
        for c in cluster_ids
    ])

    return centroids, train_mean, train_std, np.array(cluster_ids), active_feats


def assign_by_nearest_centroid(
    X_scaled: np.ndarray,
    centroids: np.ndarray,
    cluster_ids: np.ndarray,
) -> np.ndarray:
    """Return the nearest centroid label for each row of X_scaled."""
    # Squared Euclidean distance: (n_cultures, k)
    diffs = X_scaled[:, np.newaxis, :] - centroids[np.newaxis, :, :]   # (n, k, d)
    sq_dists = (diffs ** 2).sum(axis=2)                                  # (n, k)
    nearest  = sq_dists.argmin(axis=1)
    return cluster_ids[nearest]


def main() -> None:
    # ------------------------------------------------------------------ load
    fm         = pd.read_parquet(FEATURE_MATRIX)
    membership = pd.read_csv(MEMBERSHIP_FILE)
    clustered_ids = set(membership["culture_id"])

    print(f"Feature matrix:        {len(fm)} cultures")
    print(f"Already clustered:     {len(membership)}")

    # ------------------------------------------------------------------ candidates
    fm["n_features"] = fm[CLUSTERING_FEATURES].notna().sum(axis=1)
    candidates = fm[
        ~fm["culture_id"].isin(clustered_ids) & (fm["n_features"] >= 1)
    ].copy()

    no_data = fm[
        ~fm["culture_id"].isin(clustered_ids) & (fm["n_features"] == 0)
    ]

    print(f"Assignable (≥1 feat):  {len(candidates)}")
    print(f"  by source: {candidates['source'].value_counts().to_dict()}")
    print(f"No-data (0 feat):      {len(no_data)} → remain unassigned")
    print(f"  by source: {no_data['source'].value_counts().to_dict()}")

    if len(candidates) == 0:
        print("Nothing to assign.")
        return

    # ------------------------------------------------------------------ centroids
    centroids, train_mean, train_std, cluster_ids, active_feats = build_centroids(
        fm, membership, CLUSTERING_FEATURES
    )
    print(f"\nClusters: {len(cluster_ids)} | Active features: {len(active_feats)}")

    # ------------------------------------------------------------------ assign
    X_cand   = candidates[active_feats].astype(float).values
    X_filled = np.where(np.isnan(X_cand), train_mean, X_cand)
    X_scaled = (X_filled - train_mean) / train_std

    labels = assign_by_nearest_centroid(X_scaled, centroids, cluster_ids)

    candidates["cluster_id"] = labels.astype(int)
    candidates["method"]     = "nearest_centroid"

    # ------------------------------------------------------------------ diagnostics
    print("\nAssigned cluster distribution:")
    dist = candidates.groupby(["cluster_id", "source"]).size().unstack(fill_value=0)
    print(dist.to_string())

    # Distance stats (sanity check — same arrays already computed above)
    diffs   = X_scaled[:, np.newaxis, :] - centroids[np.newaxis, :, :]
    sq_dist = (diffs ** 2).sum(axis=2)
    min_dist = sq_dist.min(axis=1)
    print(f"\nNearest-centroid distance stats:")
    print(f"  mean:   {min_dist.mean():.3f}")
    print(f"  median: {np.median(min_dist):.3f}")
    print(f"  p95:    {np.percentile(min_dist, 95):.3f}")

    # ------------------------------------------------------------------ save membership
    new_rows = candidates[["culture_id", "source", "cluster_id", "method"]].copy()
    updated  = pd.concat([membership, new_rows], ignore_index=True)
    updated.to_csv(MEMBERSHIP_FILE, index=False)
    print(f"\nMembership CSV (k=8): {len(membership)} → {len(updated)} cultures")

    # ------------------------------------------------------------------ update viz JSON
    new_cluster_map = dict(zip(candidates["culture_id"], candidates["cluster_id"].astype(int)))

    with open(CULTURES_JSON) as f:
        viz = json.load(f)

    patched = 0
    for c in viz["cultures"]:
        cid = c.get("id")
        if cid in new_cluster_map:
            c["cluster"] = new_cluster_map[cid]
            patched += 1

    with open(CULTURES_JSON, "w") as f:
        json.dump(viz, f, separators=(",", ":"))

    print(f"cultures_metadata.json: {patched} entries updated")

    # ------------------------------------------------------------------ final coverage
    total   = len(fm)
    now_cls = len(updated)
    print(f"\n=== Final cluster coverage ===")
    print(f"Clustered:   {now_cls}/{total} ({100*now_cls/total:.1f}%)")
    print(f"Unassigned:  {total - now_cls}/{total} ({100*(total-now_cls)/total:.1f}%) — all 0-feature cultures")


if __name__ == "__main__":
    main()
