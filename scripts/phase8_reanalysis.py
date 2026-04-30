"""
Phase 8 Reanalysis — Eliminate source confounding.

Steps executed (in order):
  1. Diagnostics: missingness-cluster correlation + source classification test
  2. D-PLACE-only subset (>=3 features coded)
  3. Optimal k selection on D-PLACE subset
  4. Final k-means clustering
  5. Nearest-centroid assignment for DRH / Seshat / sparse D-PLACE
  6. Mantel test on D-PLACE subset
  7. Export new cultures_metadata.json and analysis_results.json

See contexts/PHASE8_CONTEXT.md for full decision rationale.
"""

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist, pdist, squareform
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed"
VIZ  = ROOT / "phase7_visualization" / "data"

FEAT_COLS = [
    "ancestor_mediation", "animal_transformation", "chanting_singing",
    "dedicated_specialist", "divination", "entheogen_use",
    "hereditary_transmission", "initiatory_crisis", "initiatory_ordeal",
    "layered_cosmology", "nature_spirits", "possession_crisis",
    "public_performance", "rhythmic_percussion", "ritual_performance",
    "soul_flight", "specialist_presence", "spirit_possession",
    "trance_induction", "unmapped_shamanic_indicators",
]
# healing_function: 0 coded — dropped
# moralizing_supernatural: Seshat-only, excluded by design


# ── helpers ──────────────────────────────────────────────────────────────────

def haversine_matrix(lats, lons):
    """Great-circle distance matrix (km)."""
    R = 6371
    lat_r = np.radians(lats)
    lon_r = np.radians(lons)
    dlat = lat_r[:, None] - lat_r[None, :]
    dlon = lon_r[:, None] - lon_r[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat_r[:, None]) * np.cos(lat_r[None, :]) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))


def mantel_test(dist_a, dist_b, n_permutations=999, random_state=42):
    """Mantel test between two square distance matrices."""
    rng = np.random.default_rng(random_state)
    a = squareform(dist_a, checks=False)
    b = squareform(dist_b, checks=False)
    r_obs, _ = spearmanr(a, b)
    count = 0
    n = dist_b.shape[0]
    for _ in range(n_permutations):
        idx = rng.permutation(n)
        b_perm = squareform(dist_b[np.ix_(idx, idx)], checks=False)
        r_perm, _ = spearmanr(a, b_perm)
        if r_perm >= r_obs:
            count += 1
    p = (count + 1) / (n_permutations + 1)
    return float(r_obs), float(p)


# ── Step 0: load ──────────────────────────────────────────────────────────────

print("Loading feature matrix...")
df = pd.read_parquet(DATA / "feature_matrix.parquet")
df["n_coded"] = df[FEAT_COLS].notna().sum(axis=1)
print(f"  Total cultures: {len(df)}")
print(f"  Sources: {df['source'].value_counts().to_dict()}")


# ── Step 1: Diagnostics ───────────────────────────────────────────────────────

print("\n=== STEP 1: DIAGNOSTICS ===")

# Load existing cluster assignments from viz metadata
with open(VIZ / "cultures_metadata.json") as f:
    existing_meta = json.load(f)

existing_clusters = {c["id"]: c["cluster"] for c in existing_meta["cultures"]}
df["existing_cluster"] = df["culture_id"].astype(str).map(existing_clusters)
df_with_cluster = df[df["existing_cluster"].notna()].copy()
df_with_cluster["existing_cluster"] = df_with_cluster["existing_cluster"].astype(int)

# 1a. Missingness-cluster correlation (Spearman)
rho, p = spearmanr(df_with_cluster["n_coded"], df_with_cluster["existing_cluster"])
print(f"\n1a. Missingness-cluster correlation (Spearman ρ):")
print(f"    ρ = {rho:.3f}, p = {p:.4f}")
if abs(rho) > 0.4:
    print("    ⚠ HIGH: clustering is partially driven by missingness")
else:
    print("    OK: low missingness-cluster correlation")

# 1b. Source classification test
X_all = df[FEAT_COLS].fillna(0).values
y_src = df["source"].values
clf = LogisticRegression(max_iter=500, random_state=42)
from sklearn.model_selection import cross_val_score
scores = cross_val_score(clf, X_all, np.array(y_src), cv=5, scoring="accuracy")
print(f"\n1b. Source classification accuracy (5-fold CV): {scores.mean():.1%} ± {scores.std():.1%}")
if scores.mean() > 0.70:
    print("    ⚠ HIGH: features encode database origin, not just cultural variation")
else:
    print("    OK: features do not strongly predict source")

diagnostics = {
    "missingness_cluster_spearman_rho": rho,
    "missingness_cluster_p": p,
    "source_classification_accuracy_mean": float(scores.mean()),
    "source_classification_accuracy_std": float(scores.std()),
}


# ── Step 2: D-PLACE subset ────────────────────────────────────────────────────

print("\n=== STEP 2: D-PLACE SUBSET ===")

dplace = df[(df["source"] == "dplace") & (df["n_coded"] >= 3)].copy()
print(f"  D-PLACE cultures with >= 3 features coded: {len(dplace)}")
print(f"  Mean features per culture: {dplace['n_coded'].mean():.1f}")

# Feature coverage in this subset
print("\n  Feature coverage in D-PLACE subset:")
for c in FEAT_COLS:
    n = dplace[c].notna().sum()
    pct = n / len(dplace) * 100
    if pct > 0:
        print(f"    {c}: {n} ({pct:.1f}%)")

X_dp = dplace[FEAT_COLS].fillna(0).values
scaler = StandardScaler()
X_dp_scaled = scaler.fit_transform(X_dp)


# ── Step 3: Optimal k ────────────────────────────────────────────────────────

print("\n=== STEP 3: OPTIMAL K SELECTION ===")

k_results = {}
for k in range(2, 11):
    km = KMeans(n_clusters=k, random_state=42, n_init=20, max_iter=500)
    labels = km.fit_predict(X_dp_scaled)
    sil = silhouette_score(X_dp_scaled, labels) if len(set(labels)) > 1 else -1
    db  = davies_bouldin_score(X_dp_scaled, labels)
    ch  = calinski_harabasz_score(X_dp_scaled, labels)
    k_results[k] = {"silhouette": sil, "davies_bouldin": db, "calinski_harabasz": ch}
    print(f"  k={k}: silhouette={sil:.3f}, DB={db:.3f}, CH={ch:.1f}")

best_k = max(k_results, key=lambda k: k_results[k]["silhouette"])
print(f"\n  Best k by silhouette: {best_k}")


# ── Step 4: Final clustering ──────────────────────────────────────────────────

print(f"\n=== STEP 4: FINAL K-MEANS (k={best_k}) ===")

km_final = KMeans(n_clusters=best_k, random_state=42, n_init=20, max_iter=500)
dplace["cluster_phase8"] = km_final.fit_predict(X_dp_scaled)
centroids = km_final.cluster_centers_

cluster_sizes = dplace["cluster_phase8"].value_counts().sort_index()
print("  Cluster sizes:")
for cid, n in cluster_sizes.items():
    print(f"    Cluster {cid}: {n} cultures")

# Cluster profiles (mean feature values)
profiles = []
for cid in sorted(dplace["cluster_phase8"].unique()):
    sub = dplace[dplace["cluster_phase8"] == cid]
    profile = {"cluster": int(cid), "n_cultures": int(len(sub))}
    for feat in FEAT_COLS:
        vals = sub[feat].dropna()
        profile[feat] = float(vals.mean()) if len(vals) else 0.0
    profiles.append(profile)

print("\n  Top features per cluster (mean presence, coded cultures only):")
for p in profiles:
    top = sorted(
        [(f, p[f]) for f in FEAT_COLS if p[f] > 0],
        key=lambda x: -x[1]
    )[:4]
    print(f"  Cluster {p['cluster']} (n={p['n_cultures']}): {[f'{f}={v:.2f}' for f,v in top]}")


# ── Step 5: Nearest-centroid assignment for all other cultures ────────────────

print("\n=== STEP 5: NEAREST-CENTROID ASSIGNMENT ===")

others = df[~df["culture_id"].isin(dplace["culture_id"])].copy()
X_others = others[FEAT_COLS].fillna(0).values
X_others_scaled = scaler.transform(X_others)
dists = cdist(X_others_scaled, centroids, metric="euclidean")
others["cluster_phase8"] = dists.argmin(axis=1)
others["cluster_phase8_assignment"] = "nearest_centroid"
dplace["cluster_phase8_assignment"] = "primary"

# Cultures with 0 features — mark as unassigned
zero_feat_mask = others["n_coded"] == 0
others.loc[zero_feat_mask, "cluster_phase8"] = None
others.loc[zero_feat_mask, "cluster_phase8_assignment"] = "unassigned_no_features"

all_assigned = pd.concat([dplace, others], ignore_index=True)
print(f"  Primary (D-PLACE >=3 feat): {len(dplace)}")
print(f"  Nearest-centroid: {(~zero_feat_mask).sum()}")
print(f"  Unassigned (0 features): {zero_feat_mask.sum()}")

assigned_mask = all_assigned["cluster_phase8"].notna()
print(f"\n  Source x Cluster (assigned only):")
print(pd.crosstab(
    all_assigned.loc[assigned_mask, "source"],
    all_assigned.loc[assigned_mask, "cluster_phase8"]
))


# ── Step 6: Mantel test on D-PLACE primary subset ────────────────────────────

print("\n=== STEP 6: MANTEL TEST (D-PLACE primary subset) ===")

dp_geo = dplace[dplace["lat"].notna() & dplace["lon"].notna()].copy()
print(f"  Cultures with coordinates: {len(dp_geo)}")

geo_dist = haversine_matrix(dp_geo["lat"].values, dp_geo["lon"].values)
feat_mat = dp_geo[FEAT_COLS].fillna(0).values
feat_dist = squareform(pdist(feat_mat, metric="jaccard"))

r_geo_feat, p_geo_feat = mantel_test(geo_dist, feat_dist, n_permutations=999)
print(f"  Geography ~ Features: r={r_geo_feat:.4f}, p={p_geo_feat:.4f} ({'sig' if p_geo_feat < 0.05 else 'n.s.'})")

mantel_results = [
    {
        "test": "Mantel: Geography ~ Features (D-PLACE primary subset)",
        "n_cultures": len(dp_geo),
        "correlation": r_geo_feat,
        "p_value": p_geo_feat,
        "significant": p_geo_feat < 0.05,
        "note": "D-PLACE cultures with >=3 features coded and coordinates"
    }
]


# ── Step 7: Export ────────────────────────────────────────────────────────────

print("\n=== STEP 7: EXPORT ===")

# Build lookup: culture_id -> new cluster
cluster_lookup = {}
for _, row in all_assigned.iterrows():
    cid = str(row["culture_id"])
    cl = row["cluster_phase8"]
    cluster_lookup[cid] = int(cl) if pd.notna(cl) else None

# Update cultures_metadata.json
for culture in existing_meta["cultures"]:
    cid = str(culture["id"])
    new_cl = cluster_lookup.get(cid)
    culture["cluster_phase8"] = new_cl
    # Preserve old cluster for comparison
    # culture["cluster"] already holds the Phase 4 value

# Save updated metadata
out_meta = VIZ / "cultures_metadata.json"
with open(out_meta, "w") as f:
    json.dump(existing_meta, f, separators=(",", ":"))
print(f"  ✓ Updated {out_meta}")

# Save cluster profiles
out_profiles = VIZ / "cluster_profiles_phase8.json"
with open(out_profiles, "w") as f:
    json.dump({"profiles": profiles, "k": best_k, "source": "dplace_primary"}, f, indent=2)
print(f"  ✓ Saved {out_profiles}")

# Save k selection results
k_out = {str(k): v for k, v in k_results.items()}

# Load existing analysis_results and update
with open(VIZ / "analysis_results.json") as f:
    analysis = json.load(f)

analysis["phase8"] = {
    "diagnostics": diagnostics,
    "dplace_subset_size": int(len(dplace)),
    "optimal_k": int(best_k),
    "k_selection": k_out,
    "mantel_dplace_primary": mantel_results,
    "note": "Phase 8 reanalysis: D-PLACE only primary clustering. See PHASE8_CONTEXT.md."
}

# Update Mantel section with Phase 8 results alongside original
analysis["mantel_phase8"] = mantel_results

out_analysis = VIZ / "analysis_results.json"
with open(out_analysis, "w") as f:
    json.dump(analysis, f, indent=2)
print(f"  ✓ Updated {out_analysis}")

# Save cluster membership parquet
out_parquet = DATA / "clusters" / "phase8" / "culture_cluster_membership_phase8.parquet"
out_parquet.parent.mkdir(parents=True, exist_ok=True)
all_assigned[["culture_id", "culture_name", "source", "lat", "lon",
              "language_family", "cluster_phase8", "cluster_phase8_assignment",
              "n_coded"]].to_parquet(out_parquet, index=False)
print(f"  ✓ Saved {out_parquet}")

print("\n✓✓✓ Phase 8 reanalysis complete ✓✓✓")
print(f"  Primary clusters: {best_k} (D-PLACE, n={len(dplace)})")
print(f"  Mantel geography~features: r={r_geo_feat:.4f}, p={p_geo_feat:.4f}")
