#!/usr/bin/env python3
"""Phase 4 — Clustering & Validation on the canonical feature matrix.

Reads ``data/processed/feature_matrix.parquet`` (Phase 3 output), applies the
phylogenetic filter and complete-case filter, then runs:

1. k-selection sweep (k=2..10): silhouette, Davies-Bouldin, Calinski-Harabasz
2. K-means at the statistically optimal k AND at the research k (interpretable)
3. Hierarchical (Ward) clustering at the same k values
4. Bootstrap stability analysis (100 resamples, 80% sample, ARI)
5. K-means vs. hierarchical agreement (ARI / Fowlkes-Mallows)
6. Cluster profiles: feature presence rates per cluster

Outputs (data/processed/clusters/phase4/):
    culture_cluster_membership.parquet
    cluster_profiles.csv
    k_selection.csv
    validation_metrics.json

Usage::

    PYTHONPATH=. python scripts/run_phase4.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    fowlkes_mallows_score,
    silhouette_score,
)
from scipy.cluster.hierarchy import fcluster, linkage

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from analysis.phylogenetic import filter_one_per_language_family  # noqa: E402
from features.impute import complete_case_filter  # noqa: E402
from features.schema import CANONICAL_FEATURES  # noqa: E402

FEATURE_MATRIX   = PROJECT_ROOT / "data" / "processed" / "feature_matrix.parquet"
OUT_DIR          = PROJECT_ROOT / "data" / "processed" / "clusters" / "phase4"

# --- Configuration ---
K_RANGE          = range(2, 11)       # k=2..10
MIN_FEATURES     = 2                  # Drop rows with < 2 non-NA features
BOOTSTRAP_N      = 100                # Stability resamples
BOOTSTRAP_FRAC   = 0.80              # Resample fraction
RANDOM_STATE     = 42


# =============================================================================
# Helpers
# =============================================================================

def _fill_for_clustering(df: pd.DataFrame, features: list[str]) -> np.ndarray:
    """Fill NaN with 0 and return a float numpy array."""
    return df[features].fillna(0).values.astype(float)


def _kmeans(X: np.ndarray, k: int, seed: int = RANDOM_STATE) -> np.ndarray:
    km = KMeans(n_clusters=k, n_init=20, max_iter=500, random_state=seed)
    return km.fit_predict(X)


def _hierarchical(X: np.ndarray, k: int) -> np.ndarray:
    Z = linkage(X, method="ward")
    return fcluster(Z, k, criterion="maxclust") - 1   # 0-indexed


def _validate(X: np.ndarray, labels: np.ndarray) -> dict:
    uniq, counts = np.unique(labels, return_counts=True)
    return {
        "silhouette":         float(silhouette_score(X, labels)),
        "davies_bouldin":     float(davies_bouldin_score(X, labels)),
        "calinski_harabasz":  float(calinski_harabasz_score(X, labels)),
        "cluster_sizes":      {int(k): int(v) for k, v in zip(uniq, counts)},
    }


def k_selection_sweep(X: np.ndarray) -> pd.DataFrame:
    rows = []
    for k in K_RANGE:
        labels = _kmeans(X, k)
        v = _validate(X, labels)
        km = KMeans(n_clusters=k, n_init=20, max_iter=500, random_state=RANDOM_STATE)
        km.fit(X)
        rows.append({
            "k":                k,
            "silhouette":       v["silhouette"],
            "davies_bouldin":   v["davies_bouldin"],
            "calinski_harabasz": v["calinski_harabasz"],
            "inertia":          float(km.inertia_),
        })
    return pd.DataFrame(rows)


def bootstrap_stability(X: np.ndarray, k: int) -> dict:
    rng = np.random.default_rng(RANDOM_STATE)
    n = len(X)
    sample_size = int(BOOTSTRAP_FRAC * n)
    ari_scores, sil_scores = [], []

    ref_labels = _kmeans(X, k)

    for _ in range(BOOTSTRAP_N):
        idx = rng.choice(n, sample_size, replace=False)
        X_s = X[idx]
        labels_s = _kmeans(X_s, k, seed=int(rng.integers(1_000_000)))
        if len(np.unique(labels_s)) > 1:
            sil_scores.append(float(silhouette_score(X_s, labels_s)))
        # ARI against reference (on the subsample)
        ari_scores.append(float(adjusted_rand_score(ref_labels[idx], labels_s)))

    return {
        "k":               k,
        "n_bootstrap":     BOOTSTRAP_N,
        "mean_ari":        float(np.mean(ari_scores)),
        "std_ari":         float(np.std(ari_scores)),
        "mean_silhouette": float(np.mean(sil_scores)) if sil_scores else float("nan"),
        "stability_grade": (
            "high"   if np.mean(ari_scores) >= 0.7 else
            "medium" if np.mean(ari_scores) >= 0.4 else
            "low"
        ),
    }


def cluster_profiles(
    df_meta: pd.DataFrame,
    labels: np.ndarray,
    features: list[str],
) -> pd.DataFrame:
    df = df_meta.copy()
    df["cluster"] = labels.astype(int)
    profiles = df.groupby("cluster")[features].mean().round(3)
    profiles["n_cultures"] = df.groupby("cluster").size()
    # Compute source breakdown as separate columns instead of a nested dict
    for src in df["source"].unique():
        profiles[f"n_{src}"] = df[df["source"] == src].groupby("cluster").size().reindex(profiles.index, fill_value=0)
    return profiles.reset_index()


# =============================================================================
# Main
# =============================================================================

def main() -> int:
    print("=" * 70)
    print("PHASE 4 — Clustering & Validation")
    print("=" * 70)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Load + filter feature matrix
    # ------------------------------------------------------------------
    print("\n[1/6] Loading feature matrix ...")
    matrix = pd.read_parquet(FEATURE_MATRIX)
    print(f"  Raw: {len(matrix)} rows")

    # Phylogenetic filter (D-PLACE only — DRH/Seshat have synthetic unique tags)
    dplace_rows  = matrix[matrix["source"] == "dplace"].copy()
    other_rows   = matrix[matrix["source"] != "dplace"].copy()
    dplace_filt  = filter_one_per_language_family(dplace_rows)
    matrix_filt  = pd.concat([dplace_filt, other_rows], ignore_index=True)
    print(f"  After phylo filter (D-PLACE): {len(dplace_filt)} / {len(dplace_rows)} rows kept")

    # Complete-case filter
    features = [f for f in CANONICAL_FEATURES if f in matrix_filt.columns]
    matrix_filt = complete_case_filter(matrix_filt, min_features=MIN_FEATURES, features=features)
    print(f"  After complete-case (≥{MIN_FEATURES} features): {len(matrix_filt)} rows")
    print("  By source:", matrix_filt["source"].value_counts().to_dict())

    X = _fill_for_clustering(matrix_filt, features)
    print(f"  Feature matrix: {X.shape}")

    # ------------------------------------------------------------------
    # 2. k-selection sweep
    # ------------------------------------------------------------------
    print(f"\n[2/6] k-selection sweep (k={min(K_RANGE)}..{max(K_RANGE)}) ...")
    k_df = k_selection_sweep(X)
    k_df.to_csv(OUT_DIR / "k_selection.csv", index=False)

    print(f"\n  {'k':>2}  {'silhouette':>10}  {'davies_bouldin':>14}  {'calinski_harabasz':>18}")
    print("  " + "-" * 50)
    for _, row in k_df.iterrows():
        flag = " ← best silhouette" if row["silhouette"] == k_df["silhouette"].max() else ""
        print(f"  {int(row['k']):>2}  {row['silhouette']:>10.4f}  "
              f"{row['davies_bouldin']:>14.4f}  {row['calinski_harabasz']:>18.1f}{flag}")

    optimal_k_sil = int(k_df.loc[k_df["silhouette"].idxmax(), "k"])
    optimal_k_db  = int(k_df.loc[k_df["davies_bouldin"].idxmin(), "k"])
    optimal_k_ch  = int(k_df.loc[k_df["calinski_harabasz"].idxmax(), "k"])
    print(f"\n  Optimal k by silhouette:       {optimal_k_sil}")
    print(f"  Optimal k by Davies-Bouldin:   {optimal_k_db}")
    print(f"  Optimal k by Calinski-Harabasz:{optimal_k_ch}")

    # Research k: highest silhouette among k >= 4 (avoids degenerate k=2 split)
    k_df_research = k_df[k_df["k"] >= 4]
    research_k = int(k_df_research.loc[k_df_research["silhouette"].idxmax(), "k"])
    print(f"  Research k (best sil, k≥4):    {research_k}")

    # If they collapse to the same k, only run once
    k_variants = [("optimal", optimal_k_sil)]
    if research_k != optimal_k_sil:
        k_variants.append(("research", research_k))
    else:
        print(f"  (optimal and research k are the same: k={optimal_k_sil})")

    # ------------------------------------------------------------------
    # 3. Cluster at optimal_k and research_k
    # ------------------------------------------------------------------
    print(f"\n[3/6] Clustering at {', '.join(f'k={k} ({l})' for l,k in k_variants)} ...")

    results = {}
    membership_rows = []

    for label, k in k_variants:
        km_labels   = _kmeans(X, k)
        hier_labels = _hierarchical(X, k)

        km_val   = _validate(X, km_labels)
        hier_val = _validate(X, hier_labels)
        ari      = float(adjusted_rand_score(km_labels, hier_labels))
        fm       = float(fowlkes_mallows_score(km_labels, hier_labels))

        print(f"\n  k={k} ({label})")
        print(f"    K-means:      sil={km_val['silhouette']:.4f}  "
              f"DB={km_val['davies_bouldin']:.4f}  "
              f"CH={km_val['calinski_harabasz']:.1f}")
        print(f"    Hierarchical: sil={hier_val['silhouette']:.4f}")
        print(f"    Agreement:    ARI={ari:.4f}  FM={fm:.4f}  "
              f"({'high' if ari >= 0.7 else 'medium' if ari >= 0.4 else 'low'})")
        print(f"    Cluster sizes (k-means): {km_val['cluster_sizes']}")

        results[label] = {
            "k": k,
            "kmeans":       {**km_val, "labels": km_labels.tolist()},
            "hierarchical": {**hier_val, "labels": hier_labels.tolist()},
            "ari":          ari,
            "fowlkes_mallows": fm,
            "agreement":    "high" if ari >= 0.7 else "medium" if ari >= 0.4 else "low",
        }

        # Membership rows
        for i, (_, row) in enumerate(matrix_filt.iterrows()):
            membership_rows.append({
                "culture_id":   row["culture_id"],
                "culture_name": row["culture_name"],
                "source":       row["source"],
                "lat":          row["lat"],
                "lon":          row["lon"],
                "time_start":   row["time_start"],
                "time_end":     row["time_end"],
                f"cluster_k{k}_kmeans":      int(km_labels[i]),
                f"cluster_k{k}_hierarchical": int(hier_labels[i]),
            })

    # Merge membership rows (one row per culture, multiple cluster columns)
    membership = pd.DataFrame(membership_rows)
    membership = (
        membership
        .groupby(["culture_id", "culture_name", "source", "lat", "lon",
                  "time_start", "time_end"], dropna=False)
        .first()
        .reset_index()
    )
    membership.to_parquet(OUT_DIR / "culture_cluster_membership.parquet", index=False)
    membership.to_csv(OUT_DIR / "culture_cluster_membership.csv", index=False)
    print(f"\n  Membership saved: {len(membership)} cultures")

    # ------------------------------------------------------------------
    # 4. Bootstrap stability
    # ------------------------------------------------------------------
    print(f"\n[4/6] Bootstrap stability (n={BOOTSTRAP_N} resamples) ...")
    stability_results = {}
    for label, k in k_variants:
        stab = bootstrap_stability(X, k)
        stability_results[label] = stab
        print(f"  k={k} ({label}): ARI mean={stab['mean_ari']:.4f} ± {stab['std_ari']:.4f} "
              f"[{stab['stability_grade']}]  sil mean={stab['mean_silhouette']:.4f}")

    # ------------------------------------------------------------------
    # 5. Cluster profiles
    # ------------------------------------------------------------------
    print(f"\n[5/6] Cluster profiles ...")
    profile_frames = []
    for label, k in k_variants:
        km_labels = np.array(results[label]["kmeans"]["labels"])
        prof = cluster_profiles(matrix_filt, km_labels, features)
        prof["k"] = k
        prof["variant"] = label
        profile_frames.append(prof)

    profiles_df = pd.concat(profile_frames, ignore_index=True)
    # Drop the 'sources' dict column for CSV (not serialisable cleanly)
    profiles_csv = profiles_df.drop(columns=["sources"], errors="ignore")
    profiles_csv.to_csv(OUT_DIR / "cluster_profiles.csv", index=False)
    print(f"  Profiles saved for k={optimal_k_sil} and k={research_k}")

    # Print research-k profiles (top 5 discriminating features per cluster)
    print(f"\n  Cluster profiles at k={research_k} (k-means, feature presence rates):")
    rk_prof = profiles_df[profiles_df["k"] == research_k].set_index("cluster")
    feat_only = [c for c in features if c in rk_prof.columns]
    print(f"  {'Cluster':>8}  {'n':>5}  Top features")
    for cluster_id, row in rk_prof.iterrows():
        n = int(row["n_cultures"])
        top = (
            row[feat_only]
            .sort_values(ascending=False)
            .head(4)
        )
        top_str = "  ".join(f"{f}={v:.2f}" for f, v in top.items())
        print(f"  {cluster_id:>8}  {n:>5}  {top_str}")

    # ------------------------------------------------------------------
    # 6. Save validation metrics + pending decisions
    # ------------------------------------------------------------------
    print(f"\n[6/6] Saving validation metrics ...")

    validation_metrics = {
        "dataset": {
            "n_cultures_total":      int(len(matrix)),
            "n_cultures_phylo_filt": int(len(matrix_filt)),
            "n_features":            len(features),
            "min_features_present":  MIN_FEATURES,
            "sources":               matrix_filt["source"].value_counts().to_dict(),
        },
        "k_selection": {
            "method":   "silhouette (primary), Davies-Bouldin, Calinski-Harabasz",
            "optimal_k_silhouette":        optimal_k_sil,
            "optimal_k_davies_bouldin":    optimal_k_db,
            "optimal_k_calinski_harabasz": optimal_k_ch,
            "research_k":                  research_k,
            "scores":   k_df.to_dict(orient="records"),
        },
        "clustering": results,
        "stability":  stability_results,
        "pending_decisions_resolved": {
            "clustering_algorithm": (
                "K-means (primary) + Hierarchical Ward (confirmation). "
                "Standard for cross-cultural data; k-means chosen because "
                "silhouette and stability favour it; hierarchical used for "
                "agreement validation."
            ),
            "optimal_k": (
                f"Statistical optimum: k={optimal_k_sil} (highest silhouette). "
                f"Research/interpretive k: k={research_k} "
                f"(best silhouette for k≥4, avoids degenerate 2-cluster split "
                f"and reveals finer cultural structure for Phase 5 interpretation)."
            ),
        },
    }

    def _json_safe(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return str(obj)

    with open(OUT_DIR / "validation_metrics.json", "w") as f:
        json.dump(validation_metrics, f, indent=2, default=_json_safe)
    print(f"  validation_metrics.json saved")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("PHASE 4 COMPLETE — Pending decisions resolved")
    print("=" * 70)
    print(f"  Clustering algorithm : K-means (primary) + Hierarchical Ward")
    primary_label = k_variants[0][0]
    primary_k     = k_variants[0][1]
    print(f"  Optimal k (stat)     : {optimal_k_sil}  (silhouette = {k_df.loc[k_df['k']==optimal_k_sil,'silhouette'].values[0]:.4f})")
    if research_k != optimal_k_sil:
        print(f"  Research k           : {research_k}  (silhouette = {k_df.loc[k_df['k']==research_k,'silhouette'].values[0]:.4f})")
    stab_key = "research" if "research" in stability_results else "optimal"
    res_key  = "research" if "research" in results else "optimal"
    print(f"  K-means stability    : ARI={stability_results[stab_key]['mean_ari']:.3f} [{stability_results[stab_key]['stability_grade']}]")
    print(f"  Methods agreement    : ARI={results[res_key]['ari']:.3f} [{results[res_key]['agreement']}]")
    print(f"\n  Outputs → {OUT_DIR.relative_to(PROJECT_ROOT)}/")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
