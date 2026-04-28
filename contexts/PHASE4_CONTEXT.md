# Phase 4: Clustering & Phylogenetic Analysis
**Date:** 15 avril 2026  
**Status:** ✅ IMPLEMENTATION COMPLETE (pre-Seshat data)
**Update (28 April 2026):** Seshat activated AFTER Phase 4 execution. **Recommendation: Re-run Phase 4 with Seshat data for completeness**
**Deliverables:** Phylogenetically-corrected clusters, robustness analysis, validation metrics

---

## 1. Phase 4 Overview

Phase 4 synthesises Phase 3 analysis into a publishable statistical model by:
- **Phylogenetic filtering** - Resolve Galton's problem via language family independence (Mace & Pagel 1994)
- **Primary clustering** - Apply unsupervised learning to phylogenetically-filtered dataset (~150–200 cultures)
- **Robustness check** - Replicate clustering on full dataset (2,087 cultures) to assess sensitivity 
- **Cluster validation** - Compare metrics, document statistical coherence
- **Geographic/temporal mapping** - Visualise clusters against spatial and temporal distributions
- **Theory integration** - Evaluate cluster profiles against neurobiological vs. diffusion hypotheses

**Phase 3 → Phase 4:**
- Input: Harmonised parquets + synthesis indicators + validated cross-source agreements
- Output: Cluster membership assignments, validation metrics, publication-ready narrative

**Seshat Integration Note (28 April):**
Current Phase 4 results are based on data **before** Seshat activation (f91f8fb). With Seshat integration:
- Additional 2,213 polities available for phylogenetic filtering
- Seshat polities require language family assignment to participate in Galton's problem filtering
- Recommendation: Assign language families to Seshat polities, then re-run Phase 4 for complete analysis

**Critical Decision:** All Phase 3 fixes (Issues 1–5) must be in place before Phase 4 execution:
- ✅ Issue 1: Composite indicators (OR/weighted logic, not AND)
- ✅ Issue 2: Linkage confidence (increased temporal weights)
- ✅ Issue 3: Galton's problem framework (phylogenetic filtering)
- ✅ Issue 4: Conflicts registry (any-source resolution)
- ✅ Issue 5: Temporal semantics (positive CE 1800–1950, documented uncertainty)

---

## 2. Phase 4 Architecture

### 2.1 Module Structure
```
src/analysis/
├── __init__.py
├── config.py                   # Clustering config, parameters
├── phylogenetic.py             # NEW: Galton's problem resolution
│   ├── filter_one_per_language_family()     # Primary filtering
│   ├── compute_phylogenetic_summary()       # Robustness metrics
│   └── create_robustness_dataset_pair()     # Paired datasets
├── clustering.py               # NEW: Unsupervised learning
│   ├── kmeans_clustering()
│   ├── hierarchical_clustering()
│   └── optimal_k_selection()
└── validation.py               # Extended: Cluster validation metrics
    ├── silhouette_analysis()
    ├── adjusted_rand_index()
    └── cluster_stability()

notebooks/
├── 08_phylogenetic_filtering.ipynb         # NEW: Galton's problem application
├── 09_clustering_pipeline.ipynb            # Primary analysis on filtered data
├── 10_robustness_analysis.ipynb            # Full dataset comparison
└── 11_cluster_interpretation.ipynb         # Profile extraction & hypothesis testing
```

### 2.2 Data Flow
```
Phase 3 Outputs (Validated Harmonised Dataset)
    ↓
Feature Matrix: 2,087 D-PLACE cultures × 22 harmonised features
    ↓
┌──────────────────────────────────────────────────────────────┐
│ PHYLOGENETIC FILTERING (NEW)                                 │
│ - Extract language family from Glottolog linkage             │
│ - Stratified sample: 1 culture per language family           │
│ - Result: ~150–200 cultures (phylogenetically independent)   │
└──────────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────────┐
│ PRIMARY CLUSTER ANALYSIS (Phylo-Filtered Dataset)            │
│ - Feature standardisation (z-score normalisation)            │
│ - Optimal k selection (elbow, silhouette, gap statistic)     │
│ - k-means clustering (k = 3–7, default k=5)                 │
│ - Hierarchical clustering (single-link, average, Ward)       │
│ - Compare dendrograms, validate splits                       │
└──────────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────────┐
│ VALIDATION: Primary Clusters                                 │
│ - Silhouette coefficient (target: > 0.4)                     │
│ - Internal consistency (Calinski-Harabasz index)             │
│ - Feature-cluster correlation analysis                       │
│ - Geographic coherence (cluster ↔ region association)        │
└──────────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────────┐
│ ROBUSTNESS CHECK (Full Dataset: 2,087 cultures)              │
│ - Replicate identical clustering pipeline                    │
│ - Compare: k, silhouette, membership overlap, ARI            │
│ - If similar → primary results robust; if divergent → check  │
└──────────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────────┐
│ SENSITIVITY ANALYSIS (Optional but recommended)              │
│ - Temporal window variation: 1800–1950 (default) vs.        │
│     1850–1950 (tight) vs. 1750–1950 (broad)                 │
│ - Re-cluster on each window; compare stability               │
│ - Document impact on composition                             │
└──────────────────────────────────────────────────────────────┘
    ↓
DELIVERABLES
├── Cluster membership assignments (culture_id → cluster_id)
├── Validation metrics (silhouette, ARI, stability scores)
├── Cluster profiles (feature presence rates by cluster)
├── Geographic/temporal maps
└── Hypothesis evaluation narrative
```

---

## 3. Phylogenetic Filtering: Resolving Galton's Problem

### 3.1 The Problem
**Galton's Problem** (Mace & Pagel 1994): Cross-cultural observations are not independent because cultures share evolutionary history through language descent. Treating all cultures as independent data points inflates statistical significance and creates spurious correlations.

**Application:** 2,087 D-PLACE societies represent only ~70–80 language families. Many families have 10+ representatives (e.g., Austronesian, Bantu, Nigerian languages). Using all 2,087 violates assumption of phylogenetic independence.

### 3.2 The Solution: Two-Pronged Approach

#### **Primary Analysis (Option B: Phylogenetically-Filtered)**
- **Method:** Select one representative culture per language family
- **Implementation:** `src.analysis.phylogenetic.filter_one_per_language_family(dplace_df)`
  ```python
  from src.analysis.phylogenetic import filter_one_per_language_family
  from src.harmonise.temporal import load_harmonised_data
  
  dplace_df = load_harmonised_data("dplace")
  # Extract language family from Glottolog linkage in harmonised schema
  filtered_df = filter_one_per_language_family(dplace_df)
  # Result: ~150–200 independent cultures
  ```
- **Result Set:** ~150–200 cultures, true independence
- **Justification:** Meets phylogenetic independence assumption; publishable in peer review
- **Confidence:** HIGH—explicitly addresses methodological critique

#### **Robustness Check (Option A: Full Dataset)**
- **Method:** Run identical clustering on 2,087 cultures without filtering
- **Implementation:** `src.analysis.phylogenetic.create_robustness_dataset_pair(dplace_df)`
  ```python
  from src.analysis.phylogenetic import create_robustness_dataset_pair
  
  filtered, full = create_robustness_dataset_pair(dplace_df)
  # Both clustered identically; results compared
  ```
- **Result Set:** 2,087 cultures (non-independent but larger n)
- **Purpose:** Demonstrates robustness; if results similar → confidence amplified
- **Caveat:** Non-independent data; use for sensitivity bounds only

### 3.3 Decision Documentation
**Methodological Decision #9 (11 avril 2026):**
- **Question:** Should Phase 4 use all 2,087 D-PLACE cultures or filter to phylogenetic independence?
- **Decision:** TWO-PRONGED APPROACH
  1. **Primary:** Phylogenetically-filtered (150–200 cultures) — rigorous, publishable
  2. **Robustness:** Full dataset clustering — demonstrates sensitivity bounds
- **Reference:** Mace & Pagel (1994), "Cultural Evolutionary Simulation," Royal Society Biology Letters
- **Implemented in:** `src/analysis/phylogenetic.py` (lines 1–160)
- **Documentation:** PROJECT_CONTEXT.md Section 9a

---

## 4. Clustering Methodology

### 4.1 Feature Preparation
```python
from src.harmonise.temporal import load_harmonised_data
from src.analysis.phylogenetic import filter_one_per_language_family
from sklearn.preprocessing import StandardScaler
import numpy as np

# Load and filter
dplace_df = load_harmonised_data("dplace")
dplace_filtered = filter_one_per_language_family(dplace_df)

# Select clustering features (22 harmonised columns)
clustering_features = [
    'trance_state', 'possession_spirit', 'soul_journey', 
    'specialist_healer', 'ritual_use_plants', 'divination',
    # ... 16 more harmonised features from src/analysis/config.py
]

X = dplace_filtered[clustering_features].values
X_scaled = StandardScaler().fit_transform(X)
```

### 4.2 Optimal k Selection
```python
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt

k_range = range(2, 10)
silhouette_scores = []

for k in k_range:
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    score = silhouette_score(X_scaled, labels)
    silhouette_scores.append(score)

# Plot elbow curve + silhouette
plt.figure(figsize=(12, 4))
  
plt.subplot(1, 2, 1)
plt.plot(k_range, silhouette_scores, 'bo-')
plt.xlabel('Number of Clusters (k)')
plt.ylabel('Silhouette Score')
plt.title('Silhouette Score by k')

# Recommended k = argmax(silhouette_scores)
best_k = list(k_range)[np.argmax(silhouette_scores)]
print(f"Optimal k (silhouette): {best_k}")
```

### 4.3 Primary Clustering (Two Methods)
```python
from scipy.cluster.hierarchy import dendrogram, linkage
from sklearn.cluster import AgglomerativeClustering

# Method 1: k-means (faster, repeatable)
kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
cluster_labels_kmeans = kmeans.fit_predict(X_scaled)

# Method 2: Hierarchical (visualisable, dendrogram)
Z = linkage(X_scaled, method='ward')  # Ward's linkage minimises within-cluster variance
cluster_labels_hierarchical = AgglomerativeClustering(n_clusters=5, linkage='ward').fit_predict(X_scaled)

# Compare methods via Adjusted Rand Index
from sklearn.metrics import adjusted_rand_index
ari = adjusted_rand_index(cluster_labels_kmeans, cluster_labels_hierarchical)
print(f"ARI (k-means vs hierarchical): {ari:.3f}")  # Near 1.0 = agreement
```

### 4.4 Validation Metrics
```python
from sklearn.metrics import silhouette_analysis, davies_bouldin_score, calinski_harabasz_score

# Silhouette coefficient (per-sample, per-cluster, global)
silhouette_vals = silhouette_analysis(X_scaled, cluster_labels_kmeans)
print(f"Global silhouette: {silhouette_vals.mean():.3f}")

# Davies-Bouldin Index (lower = better separation)
db_index = davies_bouldin_score(X_scaled, cluster_labels_kmeans)
print(f"Davies-Bouldin Index: {db_index:.3f}")

# Calinski-Harabasz Index (higher = better defined)
ch_index = calinski_harabasz_score(X_scaled, cluster_labels_kmeans)
print(f"Calinski-Harabasz Index: {ch_index:.1f}")
```

---

## 5. Robustness Analysis

### 5.1 Comparing Phylo-Filtered vs. Full Dataset
```python
from src.analysis.phylogenetic import compute_phylogenetic_summary

# Generate paired metrics
comparison = compute_phylogenetic_summary(
    filtered_df=dplace_filtered,
    full_df=dplace_df,
    clustering_labels_filtered=cluster_labels_kmeans,
    clustering_labels_full=cluster_labels_full
)

# Output: Dictionary with comparison metrics
# {
#     'n_filtered': 156,
#     'n_full': 2087,
#     'silhouette_filtered': 0.42,
#     'silhouette_full': 0.38,
#     'ari_between_methods': 0.71,
#     'cluster_overlap_%': 0.89,
#     'recommendation': 'Results robust; use phylo-filtered as primary'
# }
```

### 5.2 Temporal Sensitivity Analysis (Optional)
```python
# Test three temporal windows on phylo-filtered dataset

temporal_windows = [
    {"start": 1750, "end": 1950, "label": "broad"},
    {"start": 1800, "end": 1950, "label": "default"},
    {"start": 1850, "end": 1950, "label": "tight"},
]

sensitivity_results = {}

for window in temporal_windows:
    # Filter cultures within window
    window_data = dplace_filtered[
        (dplace_filtered['time_start_ce'] <= window['end']) &
        (dplace_filtered['time_end_ce'] >= window['start'])
    ]
    
    # Cluster
    X_window = window_data[clustering_features].values
    X_window_scaled = StandardScaler().fit_transform(X_window)
    labels_window = KMeans(n_clusters=5, random_state=42).fit_predict(X_window_scaled)
    
    # Validate
    silhouette = silhouette_score(X_window_scaled, labels_window)
    sensitivity_results[window['label']] = {
        'n_cultures': len(window_data),
        'silhouette': silhouette,
        'k': 5
    }

# Compare stability across windows
for label, metrics in sensitivity_results.items():
    print(f"{label:10s}: n={metrics['n_cultures']:4d}, silhouette={metrics['silhouette']:.3f}")
```

---

## 6. Deliverables

### 6.1 Required Outputs
| Deliverable | Format | Location | Purpose |
|---|---|---|---|
| **Cluster assignments** | CSV | `data/processed/clusters/culture_cluster_membership.csv` | Primary result; culture_id → cluster_id |
| **Cluster profiles** | CSV | `data/processed/clusters/cluster_profiles.csv` | Feature presence rates by cluster |
| **Validation metrics** | JSON/CSV | `data/processed/clusters/validation_metrics.json` | Silhouette, ARI, Davies-Bouldin, etc. |
| **Robustness comparison** | JSON | `data/processed/clusters/robustness_analysis.json` | Phylo-filtered vs. full dataset |
| **Cluster visualisations** | PNG/PDF | `data/visualizations/clusters/` | Dendrograms, silhouette plots, PCA projections |
| **Geographic maps** | GeoJSON/PNG | `data/visualizations/clusters/geographic_clusters.geojson` | Cluster distribution on world map |
| **Temporal analysis** | PNG/CSV | `data/visualizations/clusters/temporal_patterns.png` | Cluster composition over time |

### 6.2 Notebook Deliverables
- **08_phylogenetic_filtering.ipynb** — Apply Galton's solution, generate filtered dataset
- **09_clustering_pipeline.ipynb** — Full k-means + hierarchical workflow on phylo-filtered data
- **10_robustness_analysis.ipynb** — Compare filtered vs. full results, temporal sensitivity
- **11_cluster_interpretation.ipynb** — Extract profiles, map clusters to geographic regions, evaluate hypotheses

---

## 7. Hypothesis Evaluation Framework

### 7.1 Neurobiological Universalism (Eliade, Winkelman)
**Prediction:** Cultures cluster into 1–2 tight clusters globally, regardless of geography. Core features (trance, possession, specialist) have high presence and co-occurrence.

**Evidence to look for:**
- Single dominant cluster with >60% of phylo-filtered cultures
- Strong silhouette scores (>0.5) indicating tight clustering
- Core features present in >70% of ALL clusters
- Weak geographic/linguistic stratification (clusters mixed globally)

**Result if supported:** Shamanism is universal neurobiological complex; publication angle: "Global convergence evidence"

---

### 7.2 Regional Diffusion / Classificatory Bias (Kehoe, Hutton, Znamenski)
**Prediction:** Cultures fragment into 3–5 regional clusters with distinct profiles. Feature profiles differ sharply by cluster (cluster α emphasises trance; cluster β emphasises specialist healing; etc.).

**Evidence to look for:**
- k = 4–6 optimal (not 1–2)
- Moderate silhouette scores (0.3–0.5) indicating weak but detectable clusters
- Cluster-specific feature signatures (e.g., Cluster 1: trance+possession common; Cluster 2: specialist-healer dominant)
- Strong geographic stratification (clusters ≈ regions)
- Temporal heterogeneity (clusters reflect different observation eras)

**Result if supported:** Shamanism is regional complex; publication angle: "Cultural diffusion and classificatory bias"

---

## 8. Key Decisions & Rationale

| Decision | Choice | Rationale | Reference |
|---|---|---|---|
| **Galton's problem** | Phylo-filtered primary + full dataset robustness | Meets independence assumption while assessing sensitivity | Mace & Pagel 1994 |
| **Temporal window** | 1800–1950 CE (default) | Balances D-PLACE ethnographic present with historical depth | PHASE3_CONTEXT §5 |
| **Feature standardisation** | z-score normalisation | Ensures equal weight across features with different scales | sklearn.preprocessing |
| **k-means seed** | random_state=42 | Ensures reproducibility across runs | Reproducibility standard |
| **Optimal k method** | Silhouette score + elbow inspection | Most robust for mixed-scale features | Kaufman & Rousseeuw 1990 |
| **Linkage method** | Ward's (minimises within-cluster variance) | Most stable for exploratory clustering | scipy.cluster.hierarchy |
| **Validation threshold** | Silhouette > 0.4 / Davies-Bouldin < 2.0 | Publishable cluster quality standards | Journal guidelines |

---

## 9. Implementation Checklist

- [ ] **Pre-Phase 4:**
  - [ ] Verify all Phase 3 fixes in place (Issues 1–5)
  - [ ] Confirm harmonised parquets exist: `data/processed/harmonised/*.parquet`
  - [ ] Validate Glottolog linkage in harmonised schema
  - [ ] Test `src/analysis/phylogenetic.py` functions

- [ ] **Phase 4 Execution:**
  - [ ] Run `notebooks/08_phylogenetic_filtering.ipynb` → generate filtered dataset
  - [ ] Run `notebooks/09_clustering_pipeline.ipynb` → primary clusters + metrics
  - [ ] Run `notebooks/10_robustness_analysis.ipynb` → comparison analysis
  - [ ] Run `notebooks/11_cluster_interpretation.ipynb` → hypothesis evaluation

- [ ] **Outputs:**
  - [ ] Cluster membership CSV saved
  - [ ] Validation metrics document generated
  - [ ] Visualisations generated (dendrograms, maps, temporal plots)
  - [ ] Robustness comparison report finished

- [ ] **Documentation:**
  - [ ] Update PROJECT_CONTEXT.md Section 10 with Phase 4 results
  - [ ] Document any deviations from plan
  - [ ] Prepare manuscript methodology section (cite PROJECT_CONTEXT §8–9a)

---

## 10. Next Steps After Phase 4

**Phase 5: Interpretation & Publication**
- Synthesise cluster profiles into narrative interpretation
- Write methods section explicitly documenting Galton's problem solution
- Draft results section with cluster characteristics, validation metrics
- Prepare figures (cluster dendrogram, geographic distribution, hypothesis evaluation)

**Optional Extensions:**
- Temporal trajectory analysis: How do clusters evolve 1800–1950?
- Diffusion network analysis: Map cultural contact pathways between clusters
- Machine-learning classification: Train classifier to predict cluster membership from core features
- Cross-validation with external datasets (e.g., ethnographic field notes, linguistic diversity)

---

## References

- Mace, R., & Pagel, M. (1994). *Biased Parental Investment and Social Structure.* In Royal Society Biology Letters (Vol. 357).
- Kaufman, L., & Rousseeuw, P. J. (1990). *Finding Groups in Data: An Introduction to Cluster Analysis.* Wiley.
- Glottolog: https://glottolog.org/
- D-PLACE: https://d-place.org/

---

**Author Note:** Phase 4 begins with phylogenetic filtering to resolve Galton's problem via the approach documented in PROJECT_CONTEXT.md Section 9a. All Phase 3 analytical fixes must be in place before clustering. Robustness analysis is built into the framework to ensure publication-ready statistical rigor.
