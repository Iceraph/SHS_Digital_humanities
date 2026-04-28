#!/usr/bin/env python3
"""Phase 4 multi-source clustering (experimental).

Sibling of ``phase4_clustering.py`` that merges D-PLACE, DRH, and Seshat
harmonised data into a single wide feature matrix before clustering.

Design choices:

* **Phylogenetic filtering applies only to D-PLACE rows.** D-PLACE has
  Glottocodes; DRH traditions and Seshat polities don't, and the rest of the
  pipeline already treats them as distinct units of observation. DRH and
  Seshat rows pass through the filter untouched.
* **Each row carries a ``source`` column** so the cluster composition can be
  audited downstream.
* **Sparse-row filter**: drop cultures with fewer than ``MIN_FEATURES_PRESENT``
  non-NA features before clustering, to dampen the missing-data clustering
  artefact (Seshat polities only have 1 mapped feature, so without this
  filter they dominate a single "all-zero except one" cluster).

Outputs are written to ``data/processed/clusters/multisource/`` so the
D-PLACE-only baseline files are preserved for comparison.

Usage::

    PYTHONPATH=. python scripts/phase4_clustering_multisource.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from analysis.clustering import (  # noqa: E402
    extract_cluster_profiles,
    hierarchical_clustering,
    kmeans_clustering,
    load_and_prepare_features,
    optimal_k_selection,
    validate_clusters,
)
from analysis.config import CLUSTERING_FEATURES  # noqa: E402
from analysis.phylogenetic import filter_one_per_language_family  # noqa: E402


MIN_FEATURES_PRESENT = 1  # rows with fewer non-NA mapped features are dropped


def pivot_source(harmonised_path: Path, source_name: str) -> pd.DataFrame:
    """Pivot a long-format harmonised parquet to wide (one row per culture)."""
    df = pd.read_parquet(harmonised_path)
    df = df.dropna(subset=["feature_name"])
    if len(df) == 0:
        return pd.DataFrame()

    pivoted = (
        df.groupby(["culture_id", "feature_name"])["feature_value_binarised"]
        .mean()
        .reset_index()
        .pivot(index="culture_id", columns="feature_name", values="feature_value_binarised")
        .reset_index()
    )

    meta = (
        df.groupby("culture_id")
        .agg(culture_name=("culture_name", "first"), lat=("lat", "first"), lon=("lon", "first"))
        .reset_index()
    )
    pivoted = pivoted.merge(meta, on="culture_id", how="left")
    pivoted["source"] = source_name
    return pivoted


def attach_dplace_language_families(df: pd.DataFrame, societies_path: Path) -> pd.DataFrame:
    """Add a ``language_family`` column derived from D-PLACE Glottocodes."""
    societies = pd.read_csv(societies_path)
    societies["language_family"] = (
        societies["Glottocode"].fillna("unknown").str.split("-").str[0]
    )
    meta = societies[["ID", "Glottocode", "language_family"]].rename(
        columns={"ID": "culture_id", "Glottocode": "glottocode"}
    )
    return df.merge(meta, on="culture_id", how="left")


def build_combined_matrix(project_root: Path) -> pd.DataFrame:
    """Load all three sources and stack them into one wide DataFrame."""
    harmonised_dir = project_root / "data" / "processed" / "harmonised"
    societies_path = project_root / "data" / "raw" / "dplace" / "societies.csv"

    print("Pivoting harmonised parquets ...")
    dplace = pivot_source(harmonised_dir / "dplace_harmonised.parquet", "dplace")
    drh = pivot_source(harmonised_dir / "drh_harmonised.parquet", "drh")
    seshat = pivot_source(harmonised_dir / "seshat_harmonised.parquet", "seshat")
    print(f"  dplace: {len(dplace)} cultures, {dplace.shape[1]} cols")
    print(f"  drh:    {len(drh)} cultures, {drh.shape[1]} cols")
    print(f"  seshat: {len(seshat)} cultures, {seshat.shape[1]} cols")

    print("Attaching language_family for D-PLACE ...")
    dplace = attach_dplace_language_families(dplace, societies_path)

    # DRH and Seshat: each row is its own language family (no over-representation
    # of related cultures within these sources, so phylogenetic filtering is a no-op).
    drh["language_family"] = "drh:" + drh["culture_id"].astype(str)
    drh["glottocode"] = pd.NA
    seshat["language_family"] = "seshat:" + seshat["culture_id"].astype(str)
    seshat["glottocode"] = pd.NA

    combined = pd.concat([dplace, drh, seshat], ignore_index=True, sort=False)
    print(f"Combined: {len(combined)} cultures")
    return combined


def filter_dplace_only(combined: pd.DataFrame) -> pd.DataFrame:
    """Phylogenetically filter the D-PLACE rows; pass DRH/Seshat through."""
    dplace_rows = combined[combined["source"] == "dplace"]
    other_rows = combined[combined["source"] != "dplace"]
    print(f"Phylogenetic filter on D-PLACE: {len(dplace_rows)} rows ...")
    dplace_filtered = filter_one_per_language_family(dplace_rows)
    print(
        f"  D-PLACE filtered: {len(dplace_filtered)} cultures "
        f"({dplace_rows['language_family'].nunique()} language families)"
    )
    out = pd.concat([dplace_filtered, other_rows], ignore_index=True, sort=False)
    print(f"  Multi-source filtered total: {len(out)} cultures")
    return out


def main() -> int:
    print("=" * 80)
    print("PHASE 4 MULTI-SOURCE CLUSTERING (D-PLACE + DRH + Seshat)")
    print("=" * 80)

    project_root = Path(__file__).parent.parent
    out_dir = project_root / "data" / "processed" / "clusters" / "multisource"
    out_dir.mkdir(parents=True, exist_ok=True)

    combined = build_combined_matrix(project_root)
    filtered = filter_dplace_only(combined)

    available = [f for f in CLUSTERING_FEATURES if f in filtered.columns]
    print(f"\nClustering features available: {len(available)}")
    print(f"  -> {available}")

    n_present = filtered[available].notna().sum(axis=1)
    print(
        f"\nNon-NA feature counts: min={n_present.min()}, "
        f"median={n_present.median()}, max={n_present.max()}"
    )
    keep = n_present >= MIN_FEATURES_PRESENT
    dropped = (~keep).sum()
    by_source = (
        filtered.assign(_kept=keep).groupby("source")["_kept"].agg(["sum", "size"])
    )
    print(f"\nDropping rows with < {MIN_FEATURES_PRESENT} non-NA features ({dropped} dropped):")
    print(by_source.rename(columns={"sum": "kept", "size": "total"}).to_string())
    filtered = filtered[keep].reset_index(drop=True)

    X, df_clean = load_and_prepare_features(filtered, available, standardize=True)
    df_clean = df_clean.merge(
        filtered[["culture_id", "source"]].drop_duplicates("culture_id"),
        on="culture_id",
        how="left",
    )
    print(f"\nFeature matrix: {X.shape}")

    print("\nOptimal-k search (k=2..9) ...")
    selection = optimal_k_selection(X, k_range=range(2, 10))
    # Best silhouette favours k=2 mega-clusters; also report k=8 for parity with the
    # D-PLACE-only baseline and to surface finer structure.
    optimal_k = selection["recommended_k"]
    print(
        "  silhouette per k: "
        + ", ".join(f"k={k}:{s:.3f}" for k, s in zip(range(2, 10), selection["silhouette_scores"]))
    )
    print(f"  -> optimal k = {optimal_k} (silhouette {selection['best_silhouette']:.3f})")

    print(f"\nK-means with k={optimal_k} ...")
    km = kmeans_clustering(X, k=optimal_k, random_state=42)
    labels = km["labels"]
    val = validate_clusters(X, labels)
    print(f"  silhouette: {val['silhouette_score_global']:.3f}")
    print(f"  davies-bouldin: {val['davies_bouldin_index']:.3f}")
    print(f"  calinski-harabasz: {val['calinski_harabasz_index']:.1f}")
    print(f"  cluster sizes: {val['cluster_sizes']}")

    print(f"\nHierarchical (Ward) with k={optimal_k} ...")
    hi = hierarchical_clustering(X, k=optimal_k, linkage_method="ward")
    val_hi = validate_clusters(X, hi["labels"])
    print(f"  silhouette: {val_hi['silhouette_score_global']:.3f}")

    # Parity run at k=8 to compare with the D-PLACE-only baseline (which also chose k=8).
    print("\nK-means parity run at k=8 ...")
    km8 = kmeans_clustering(X, k=8, random_state=42)
    val8 = validate_clusters(X, km8["labels"])
    print(f"  silhouette: {val8['silhouette_score_global']:.3f}")
    print(f"  davies-bouldin: {val8['davies_bouldin_index']:.3f}")
    print(f"  cluster sizes: {val8['cluster_sizes']}")
    df_clean_k8 = df_clean.copy()
    df_clean_k8["cluster"] = km8["labels"]
    composition_k8 = (
        df_clean_k8.groupby(["cluster", "source"])
        .size()
        .unstack(fill_value=0)
        .add_prefix("n_")
    )
    print("Cluster composition by source (k=8):")
    print(composition_k8.to_string())
    composition_k8.to_csv(out_dir / "cluster_composition_by_source_k8.csv")
    pd.DataFrame(
        {
            "culture_id": df_clean_k8["culture_id"].values,
            "source": df_clean_k8["source"].values,
            "cluster_id": km8["labels"],
        }
    ).to_csv(out_dir / "culture_cluster_membership_k8.csv", index=False)

    df_with = df_clean.copy()
    df_with["cluster"] = labels
    profiles = extract_cluster_profiles(df_with, labels, available)

    print("\nTop features per cluster (k-means):")
    for cid in sorted(set(labels)):
        if cid in profiles.index:
            top = profiles.loc[cid, available].nlargest(3)
            print(
                f"  cluster {cid} (n={int((labels==cid).sum())}): "
                + ", ".join(f"{f}({v:.2f})" for f, v in top.items())
            )

    composition = (
        df_with.groupby(["cluster", "source"])
        .size()
        .unstack(fill_value=0)
        .add_prefix("n_")
    )
    print("\nCluster composition by source:")
    print(composition.to_string())

    membership = pd.DataFrame(
        {
            "culture_id": df_with["culture_id"].values,
            "source": df_with["source"].values,
            "cluster_id": labels,
            "method": "kmeans",
        }
    )
    membership.to_csv(out_dir / "culture_cluster_membership.csv", index=False)
    profiles.to_csv(out_dir / "cluster_profiles.csv")
    composition.to_csv(out_dir / "cluster_composition_by_source.csv")
    metrics = {
        "n_cultures": int(len(df_with)),
        "n_features": int(X.shape[1]),
        "min_features_present": MIN_FEATURES_PRESENT,
        "kmeans": {
            "k": int(optimal_k),
            "silhouette": float(val["silhouette_score_global"]),
            "davies_bouldin": float(val["davies_bouldin_index"]),
            "calinski_harabasz": float(val["calinski_harabasz_index"]),
            "cluster_sizes": {str(k): int(v) for k, v in val["cluster_sizes"].items()},
        },
        "hierarchical": {
            "silhouette": float(val_hi["silhouette_score_global"]),
        },
        "k_selection": {
            "k_range": list(range(2, 10)),
            "silhouette_scores": [float(s) for s in selection["silhouette_scores"]],
            "recommended_k": int(optimal_k),
        },
        "cluster_composition_by_source": composition.to_dict(),
    }
    (out_dir / "validation_metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"\n✓ Outputs written to {out_dir.relative_to(project_root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
