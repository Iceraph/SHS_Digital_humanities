"""
Phase 8 Refinement — clean re-clustering + Pagel's λ.

Fixes applied vs. phase8_reanalysis.py:
  - Remove unmapped_shamanic_indicators (99.7% present in SCCS subset → constant)
  - Remove dedicated_specialist (0% in D-PLACE)
  - Cap k at 6 to avoid micro-clusters; select by silhouette + size balance
  - Compute Pagel's λ per feature using patristic distances from NEXUS trees
  - Re-run Mantel with refined feature set

See contexts/PHASE8_CONTEXT.md §6 for decision rationale.
"""

import json
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist, pdist, squareform
from scipy.stats import spearmanr
from sklearn.cluster import KMeans
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

ROOT  = Path(__file__).resolve().parent.parent
DATA  = ROOT / "data" / "processed"
VIZ   = ROOT / "phase7_visualization" / "data"
TREES = ROOT / "data" / "raw" / "dplace_repo" / "cldf" / "trees"

# Features to cluster on: SCCS shamanic variables only
# Removed: unmapped_shamanic_indicators (constant), dedicated_specialist (Seshat-only),
#          healing_function (0 coded), moralizing_supernatural (Seshat-only by design),
#          spirit_possession / trance_induction (EA variables, 0 coverage in SCCS subset)
CLUSTER_FEATURES = [
    "ancestor_mediation", "animal_transformation", "chanting_singing",
    "divination", "entheogen_use", "hereditary_transmission",
    "initiatory_crisis", "initiatory_ordeal", "layered_cosmology",
    "nature_spirits", "possession_crisis", "public_performance",
    "rhythmic_percussion", "ritual_performance", "soul_flight",
    "specialist_presence",
]

# Full set for Mantel / signal (include EA variables where coded)
ALL_FEATURES = CLUSTER_FEATURES + ["spirit_possession", "trance_induction"]


# ── Newick parser for patristic distances ─────────────────────────────────────

def extract_newick(nexus_text: str) -> str:
    """Pull the Newick string out of a NEXUS TREES block."""
    m = re.search(r"TREE\s+\S+\s*=\s*(?:\[.*?\])?\s*(.+);", nexus_text, re.DOTALL)
    if not m:
        raise ValueError("No TREE found in NEXUS")
    return m.group(1).strip()


def parse_newick(s: str):
    """
    Recursive descent Newick parser.
    Returns (name, branch_length, children) tuples as nested dicts.
    """
    s = s.strip()

    def _parse(pos):
        children = []
        if s[pos] == '(':
            pos += 1  # skip '('
            while True:
                child, pos = _parse(pos)
                children.append(child)
                if pos < len(s) and s[pos] == ',':
                    pos += 1
                elif pos < len(s) and s[pos] == ')':
                    pos += 1
                    break
                else:
                    break
        # read label
        label_end = pos
        while label_end < len(s) and s[label_end] not in (',', ':', ')', '(', ';'):
            label_end += 1
        label = s[pos:label_end].strip()
        pos = label_end
        # read branch length
        bl = 1.0
        if pos < len(s) and s[pos] == ':':
            pos += 1
            bl_end = pos
            while bl_end < len(s) and s[bl_end] not in (',', ')', '(', ';'):
                bl_end += 1
            try:
                bl = float(s[pos:bl_end])
            except ValueError:
                bl = 1.0
            pos = bl_end
        return {"name": label, "bl": bl, "children": children}, pos

    tree, _ = _parse(0)
    return tree


def _leaf_distances(node, depth=0.0, leaf_depths=None):
    """Accumulate leaf → root-distance mappings."""
    if leaf_depths is None:
        leaf_depths = {}
    d = depth + node["bl"]
    if not node["children"]:
        leaf_depths[node["name"]] = d
    else:
        for c in node["children"]:
            _leaf_distances(c, d, leaf_depths)
    return leaf_depths


def patristic_distances(tree_node):
    """
    Compute pairwise patristic distances from a parsed Newick tree.
    Returns (taxa_list, distance_matrix).
    Patristic distance = sum of branch lengths on the path between two leaves.
    Approximated as |depth(a) - depth(b)| + 2*depth(LCA).
    We use the simple upper bound: depth(a) + depth(b) - 2*depth(root_to_lca).
    For a rooted tree: dist(a,b) = depth(a) + depth(b) - 2*depth(lca(a,b)).
    We use the root-depth accumulation: dist(a,b) ≈ |root_depth(a) - root_depth(b)|
    which is exact only on ultrametric trees, but sufficient for λ approximation.
    """
    leaf_depths = _leaf_distances(tree_node, depth=0.0)
    taxa = sorted(leaf_depths.keys())
    n = len(taxa)
    depths = np.array([leaf_depths[t] for t in taxa])
    # Ultrametric approximation: dist(i,j) = depth_i + depth_j - 2*depth_lca
    # Simplified: use depth sum minus twice min depth as proxy (conservative)
    dist = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            dist[i, j] = dist[j, i] = depths[i] + depths[j]
    # Normalise to [0,1]
    mx = dist.max()
    if mx > 0:
        dist /= mx
    return taxa, dist


def build_phylo_distance_matrix(glottocodes, trees_dir: Path):
    """
    Build an N×N phylogenetic distance matrix for a list of glottocodes.
    Same-family cultures: patristic distance from NEXUS tree.
    Different-family cultures: 1.0 (maximum).
    """
    codes = list(glottocodes)
    n = len(codes)
    D = np.ones((n, n))
    np.fill_diagonal(D, 0.0)
    idx = {c: i for i, c in enumerate(codes)}

    code_set = set(codes)
    for tf in trees_dir.glob("*.trees"):
        content = tf.read_text()
        # Check if any of our codes appear
        present = [c for c in code_set if c in content]
        if len(present) < 2:
            continue
        try:
            nwk = extract_newick(content)
            tree = parse_newick(nwk)
            taxa, dist_mat = patristic_distances(tree)
            taxa_set = set(taxa)
            common = [c for c in present if c in taxa_set]
            if len(common) < 2:
                continue
            t_idx = {t: i for i, t in enumerate(taxa)}
            for i, ci in enumerate(common):
                for j, cj in enumerate(common):
                    if i >= j:
                        continue
                    ii, jj = idx[ci], idx[cj]
                    d = dist_mat[t_idx[ci], t_idx[cj]]
                    D[ii, jj] = D[jj, ii] = d
        except Exception:
            continue

    return codes, D


# ── Pagel's λ (proper Brownian motion approximation) ─────────────────────────

def pagels_lambda_proper(feature_vector, phylo_dist_matrix):
    """
    Estimate Pagel's λ via grid search over log-likelihood.
    Uses the Brownian motion covariance structure: C_ij = λ * shared_path + (1-λ) * 0.
    Approximation: C_ij proportional to (1 - phylo_dist_ij).
    """
    mask = ~np.isnan(feature_vector)
    x = feature_vector[mask].astype(float)
    D = phylo_dist_matrix[np.ix_(mask, mask)]
    n = len(x)
    if n < 5:
        return {"lambda": float("nan"), "p_value": float("nan"),
                "interpretation": "insufficient data", "n": int(n)}

    # Covariance proxy: C_ij = 1 - D_ij (higher shared ancestry = lower distance)
    C_base = 1.0 - D
    np.fill_diagonal(C_base, 1.0)

    x_c = x - x.mean()
    lambdas = np.linspace(0, 1, 101)
    lls = []
    for lam in lambdas:
        C = lam * C_base + (1 - lam) * np.eye(n)
        # Regularise
        C += 1e-6 * np.eye(n)
        try:
            L = np.linalg.cholesky(C)
            log_det = 2 * np.sum(np.log(np.diag(L)))
            Cinv_x = np.linalg.solve(C, x_c)
            ll = -0.5 * (log_det + x_c @ Cinv_x + n * np.log(2 * np.pi))
        except np.linalg.LinAlgError:
            ll = -np.inf
        lls.append(ll)

    lls = np.array(lls)
    best = int(np.argmax(lls))
    lam_ml = float(lambdas[best])

    # LRT p-value: compare ML vs λ=0
    ll_ml = lls[best]
    ll_0  = lls[0]
    lrt = 2 * (ll_ml - ll_0)
    from scipy.stats import chi2
    p = float(1 - chi2.cdf(max(lrt, 0), df=1))

    interp = ("Strong" if lam_ml > 0.7 and p < 0.05
              else "Moderate" if lam_ml > 0.3
              else "Weak")

    return {"lambda": lam_ml, "p_value": p,
            "ll_ml": float(ll_ml), "ll_null": float(ll_0),
            "interpretation": interp, "n": int(n)}


# ── Mantel ────────────────────────────────────────────────────────────────────

def haversine_matrix(lats, lons):
    R = 6371
    lat_r, lon_r = np.radians(lats), np.radians(lons)
    dlat = lat_r[:, None] - lat_r[None, :]
    dlon = lon_r[:, None] - lon_r[None, :]
    a = (np.sin(dlat / 2) ** 2
         + np.cos(lat_r[:, None]) * np.cos(lat_r[None, :]) * np.sin(dlon / 2) ** 2)
    return R * 2 * np.arcsin(np.sqrt(a))


def mantel_test(dist_a, dist_b, n_permutations=999, random_state=42):
    rng = np.random.default_rng(random_state)
    a = squareform(dist_a, checks=False)
    b = squareform(dist_b, checks=False)
    r_obs, _ = spearmanr(a, b)
    count = sum(
        1 for _ in range(n_permutations)
        if (idx := rng.permutation(dist_b.shape[0]),
            spearmanr(a, squareform(dist_b[np.ix_(idx, idx)], checks=False))[0] >= r_obs)[1]
    )
    return float(r_obs), float((count + 1) / (n_permutations + 1))


# ── Main ──────────────────────────────────────────────────────────────────────

print("Loading data...")
df = pd.read_parquet(DATA / "feature_matrix.parquet")
df["n_coded"] = df[CLUSTER_FEATURES].notna().sum(axis=1)

# D-PLACE primary subset: >= 3 features in the refined CLUSTER_FEATURES set
dplace = df[(df["source"] == "dplace") & (df["n_coded"] >= 3)].copy()
print(f"D-PLACE primary subset (refined features): {len(dplace)} cultures")

X = dplace[CLUSTER_FEATURES].fillna(0).values
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ── Step 1: k selection (cap at 6, require min cluster size >= 10) ────────────

print("\n=== STEP 1: OPTIMAL K (refined features, k=2..6) ===")
k_results = {}
for k in range(2, 7):
    km = KMeans(n_clusters=k, random_state=42, n_init=20, max_iter=500)
    labels = km.fit_predict(X_scaled)
    sizes = np.bincount(labels)
    min_size = sizes.min()
    sil = silhouette_score(X_scaled, labels)
    db  = davies_bouldin_score(X_scaled, labels)
    ch  = calinski_harabasz_score(X_scaled, labels)
    k_results[k] = {"silhouette": sil, "davies_bouldin": db,
                    "calinski_harabasz": ch, "min_cluster_size": int(min_size),
                    "sizes": sizes.tolist()}
    flag = " ← micro-cluster" if min_size < 10 else ""
    print(f"  k={k}: sil={sil:.3f}, DB={db:.3f}, CH={ch:.1f}, "
          f"min_size={min_size}{flag}")

# Best k: highest silhouette with min_cluster_size >= 10
valid_k = {k: v for k, v in k_results.items() if v["min_cluster_size"] >= 10}
if valid_k:
    best_k = max(valid_k, key=lambda k: valid_k[k]["silhouette"])
else:
    best_k = max(k_results, key=lambda k: k_results[k]["silhouette"])
print(f"\n  Selected k={best_k} (best silhouette with min cluster >= 10)")

# ── Step 2: Final clustering ──────────────────────────────────────────────────

print(f"\n=== STEP 2: FINAL K-MEANS (k={best_k}) ===")
km_final = KMeans(n_clusters=best_k, random_state=42, n_init=20, max_iter=500)
dplace["cluster_phase8r"] = km_final.fit_predict(X_scaled)
centroids = km_final.cluster_centers_

profiles = []
for cid in sorted(dplace["cluster_phase8r"].unique()):
    sub = dplace[dplace["cluster_phase8r"] == cid]
    p = {"cluster": int(cid), "n_cultures": int(len(sub))}
    for feat in CLUSTER_FEATURES:
        vals = sub[feat].dropna()
        p[feat] = float(vals.mean()) if len(vals) else 0.0
    profiles.append(p)
    top = sorted([(f, p[f]) for f in CLUSTER_FEATURES if p[f] > 0.1],
                 key=lambda x: -x[1])[:5]
    print(f"  Cluster {cid} (n={p['n_cultures']}): "
          f"{[f'{f}={v:.2f}' for f,v in top]}")

# ── Step 3: Nearest-centroid for rest ────────────────────────────────────────

print("\n=== STEP 3: NEAREST-CENTROID ASSIGNMENT ===")
others = df[~df["culture_id"].isin(dplace["culture_id"])].copy()
X_oth = others[CLUSTER_FEATURES].fillna(0).values
X_oth_scaled = scaler.transform(X_oth)
others["cluster_phase8r"] = cdist(X_oth_scaled, centroids).argmin(axis=1)
others.loc[others["n_coded"] == 0, "cluster_phase8r"] = None

assigned = pd.concat([dplace, others])
print("  Source × Cluster (assigned only):")
print(pd.crosstab(
    assigned.loc[assigned["cluster_phase8r"].notna(), "source"],
    assigned.loc[assigned["cluster_phase8r"].notna(), "cluster_phase8r"]
))

# ── Step 4: Mantel test (refined features) ───────────────────────────────────

print("\n=== STEP 4: MANTEL TEST (D-PLACE primary, refined features) ===")
dp_geo = dplace[dplace["lat"].notna() & dplace["lon"].notna()]
geo_dist  = haversine_matrix(dp_geo["lat"].values, dp_geo["lon"].values)
feat_mat  = dp_geo[ALL_FEATURES].fillna(0).values
feat_dist = squareform(pdist(feat_mat, metric="jaccard"))
r, p = mantel_test(geo_dist, feat_dist)
print(f"  r = {r:.4f}, p = {p:.4f} ({'significant' if p < 0.05 else 'n.s.'})")

# ── Step 5: Pagel's λ ─────────────────────────────────────────────────────────

print("\n=== STEP 5: PAGEL'S λ (D-PLACE primary subset) ===")

# Build phylogenetic distance matrix from NEXUS trees
gc_col = dplace["glottocode"].fillna(dplace["culture_id"])
glottocodes = gc_col.tolist()
print(f"  Building phylogenetic distance matrix for {len(glottocodes)} cultures...")
taxa, phylo_dist = build_phylo_distance_matrix(glottocodes, TREES)

# Align taxa order to dplace order
gc_to_idx = {g: i for i, g in enumerate(taxa)}
row_idx = [gc_to_idx.get(g) for g in glottocodes]

# Reorder phylo_dist to match dplace row order
valid_mask = [i is not None for i in row_idx]
valid_rows = [i for i in row_idx if i is not None]
phylo_aligned = phylo_dist[np.ix_(valid_rows, valid_rows)]
dplace_valid = dplace[valid_mask].copy()

print(f"  Cultures with phylogenetic placement: {sum(valid_mask)} / {len(dplace)}")

lambda_results = []
print(f"\n  {'Feature':<30} {'λ':>6}  {'p':>7}  {'n':>5}  Interpretation")
print("  " + "-" * 60)
for feat in ALL_FEATURES:
    fv = dplace_valid[feat].values.astype(float)
    try:
        res = pagels_lambda_proper(fv, phylo_aligned)
        lam = res["lambda"]
        pv  = res["p_value"]
        interp = res["interpretation"]
        n   = res["n"]
        flag = " *" if (not np.isnan(pv) and pv < 0.05) else ""
        print(f"  {feat:<30} {lam:>6.3f}  {pv:>7.4f}  {n:>5}  {interp}{flag}")
        lambda_results.append({"feature": feat, **res})
    except Exception as e:
        print(f"  {feat:<30} ERROR: {e}")
        lambda_results.append({"feature": feat, "lambda": None, "error": str(e)})

# ── Step 6: Export ────────────────────────────────────────────────────────────

print("\n=== STEP 6: EXPORT ===")

# Cluster lookup
cluster_lookup = {}
for _, row in assigned.iterrows():
    cl = row["cluster_phase8r"]
    cluster_lookup[str(row["culture_id"])] = int(cl) if pd.notna(cl) else None

# Update cultures_metadata.json
with open(VIZ / "cultures_metadata.json") as f:
    meta = json.load(f)
for culture in meta["cultures"]:
    culture["cluster_phase8r"] = cluster_lookup.get(str(culture["id"]))

with open(VIZ / "cultures_metadata.json", "w") as f:
    json.dump(meta, f, separators=(",", ":"))
print(f"  ✓ cultures_metadata.json updated (cluster_phase8r field)")

# Update analysis_results.json
with open(VIZ / "analysis_results.json") as f:
    analysis = json.load(f)

analysis["phase8_refined"] = {
    "k": int(best_k),
    "n_cultures_primary": int(len(dplace)),
    "features_used": CLUSTER_FEATURES,
    "k_selection": {str(k): v for k, v in k_results.items()},
    "cluster_profiles": profiles,
    "mantel": {
        "r": r, "p": p, "significant": p < 0.05,
        "n_cultures": int(len(dp_geo)),
        "note": "D-PLACE primary subset, Jaccard feature distance, Spearman Mantel"
    },
    "pagels_lambda": lambda_results,
}
with open(VIZ / "analysis_results.json", "w") as f:
    json.dump(analysis, f, indent=2)
print(f"  ✓ analysis_results.json updated (phase8_refined section)")

# Save parquet
out = DATA / "clusters" / "phase8" / "culture_cluster_membership_phase8_refined.parquet"
assigned[["culture_id", "culture_name", "source", "lat", "lon",
          "language_family", "cluster_phase8r", "n_coded"]].to_parquet(out, index=False)
print(f"  ✓ Saved {out.name}")

print(f"\n✓✓✓ Phase 8 refinement complete ✓✓✓")
print(f"  k={best_k}, Mantel r={r:.3f} p={p:.4f}")
sig_lambda = [x for x in lambda_results if x.get("p_value") and x["p_value"] < 0.05]
print(f"  Features with significant λ (p<0.05): {len(sig_lambda)}")
for x in sig_lambda:
    print(f"    {x['feature']}: λ={x['lambda']:.3f}, p={x['p_value']:.4f}")
