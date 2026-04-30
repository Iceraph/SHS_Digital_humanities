# Phase 8: Reanalysis — Eliminating Source Confounding

**Status:** In progress  
**Date Created:** 30 April 2026  
**Decision recorded by:** Claude Sonnet 4.6 (session 3, 30 Apr 2026)  
**Triggered by:** Diagnostic review of Phase 4/5/7 clustering outputs

---

## 1. Why This Phase Exists

A post-hoc review of the Phase 4 clustering revealed that the results are **not valid for cultural interpretation**. The clusters separate databases from each other, not shamanic practices.

### 1.1 The Evidence

Cross-tabulating cluster assignment against data source:

| Cluster | D-PLACE | DRH | Seshat | Interpretation |
|---|---|---|---|---|
| 0 | 271 | 106 | 0 | Mixed D-PLACE + DRH |
| 1 | 624 | 2 | 115 | Largely D-PLACE |
| 2 | 185 | 0 | 0 | **D-PLACE only** |
| 3 | 1 | 0 | 0 | Singleton — meaningless |
| 4 | 31 | 0 | 0 | D-PLACE only |
| 5 | 0 | 0 | 336 | **Seshat only** |
| 6 | 105 | 0 | 0 | D-PLACE only |
| 7 | 0 | 70 | 0 | **DRH only** |

Clusters 2, 4, 5, 6, 7 are pure single-source clusters. This is a source artifact, not a cultural pattern.

### 1.2 Root Cause: NA → 0 on a Structurally Sparse Matrix

The feature matrix has extreme missingness:

| Feature | D-PLACE | DRH | Seshat |
|---|---|---|---|
| trance_induction | 22.6% coded | 39.6% coded | 0% coded |
| spirit_possession | 12.9% coded | 69.6% coded | 0% coded |
| dedicated_specialist | 0% coded | 0% coded | 75.5% coded |
| ancestor_mediation | 9.9% coded | 0% coded | 0% coded |

The clustering pipeline (`clustering.py:load_and_prepare_features`) fills NA with 0. When Seshat has dedicated_specialist coded at 75% and everything else at 0%, and DRH has soul_flight/spirit_possession coded and everything else at 0%, k-means groups by *which features are absent*, not which are present.

**There are zero features shared across all three sources at >5% coverage.** An intersection-features approach is not viable.

### 1.3 Additional Problems

- `healing_function`: 0 cultures coded — column should be dropped
- Cluster 3: singleton (1 culture) — k=8 is over-specified
- Phylogenetic signal analysis stored placeholder names (`feature_0`…`feature_18`) — Pagel's λ was never computed on named features
- Current Mantel test used the confounded joint matrix — result not interpretable

---

## 2. Decision

### What we are NOT doing
- Cross-source joint clustering (source confound cannot be corrected by imputation given zero intersection features)
- Publishing the current 8-cluster assignment as cultural evidence

### What we ARE doing

**Primary analysis: D-PLACE only, cultures with ≥ 3 features coded**

D-PLACE contains a well-studied subsample of ~357 societies from the Standard Cross-Cultural Sample (SCCS) and related collections with 3–11 shamanic features coded (mean 8.2). These are the societies with enough coverage for meaningful clustering.

- n = 357 cultures, 17 features, mean 8.2 coded per culture
- Features with >5% coverage in D-PLACE: all SCCS-derived variables
- Missingness within this subsample filled with 0 (justified: SCCS coding convention is explicit absence when not mentioned)
- Galton's correction (one-per-language-family) applied within this subset

**DRH and Seshat: post-hoc assignment only**

After fitting the D-PLACE model, DRH and Seshat entries are assigned by nearest-centroid. Their cluster labels are used for visualization and qualitative comparison, not for statistical inference.

**Re-run statistical tests on D-PLACE subset**
- Mantel test (geography ~ features, partial Mantel controlling for phylogeny)
- Pagel's λ per named feature vs. Glottolog tree
- Source classification test (diagnostic)
- Missingness-cluster correlation test (diagnostic)

---

## 3. Analysis Plan

### Step 1 — Diagnostics (run once, document)
- **Missingness-cluster correlation**: Spearman ρ between n_features_coded and cluster_label. If ρ > 0.4, clustering is missingness-driven.
- **Source classification test**: Logistic regression predicting source from features (fillna=0). If accuracy > 70%, features encode database origin.

### Step 2 — D-PLACE subset definition
- Filter: `source == 'dplace'` AND `n_coded >= 3`
- Drop: `healing_function` (0 coded), `moralizing_supernatural` (Seshat-only by design)
- Features: 17 remaining SCCS variables
- n ≈ 357 cultures

### Step 3 — Optimal k selection
- Run k-means for k = 2…10 on D-PLACE subset
- Report silhouette, Davies-Bouldin, Calinski-Harabasz
- Apply Galton's filter (one-per-language-family) for primary; full D-PLACE as robustness check

### Step 4 — Final clustering
- Fit k-means with optimal k on D-PLACE subset
- Nearest-centroid assignment for remaining D-PLACE (1-2 features), DRH, Seshat
- Save new `culture_cluster_membership_phase8.parquet`

### Step 5 — Statistical tests on D-PLACE subset
- Mantel: geography ~ features (permutation n=999)
- Partial Mantel: features ~ geo | phylo and features ~ phylo | geo
- Pagel's λ per feature (requires Glottolog tree + per-society values)

### Step 6 — Export
- Update `phase7_visualization/data/cultures_metadata.json` with new cluster assignments
- Update `phase7_visualization/data/analysis_results.json` with new test results

---

## 4. Interpretation Logic After Fix

| Scenario | Meaning | Hypothesis supported |
|---|---|---|
| Clusters persist in D-PLACE subset | Real cultural structure | Evaluate geography/phylogeny tests |
| No clusters (silhouette < 0.2) | "Shamanism" is not a coherent category | Classificatory bias |
| Weak clusters + regional grouping | Features co-occur regionally | Diffusion |
| Clusters present + geography independent | Features arise independently | Neurobiological universalism |

---

## 5. What is NOT Changed

- The visualization (globe, phylotree, feature panel) — remains valid for exploration
- The data pipeline (harmonization, feature extraction) — outputs are correct, analysis choices were wrong
- The DRH geocoding and globally distributed sidebar — not affected
- The Mantel *direction* (geography probably not predictive) — likely survives the reanalysis, but must be verified

---

## 6. Results (30 April 2026)

### Diagnostics

| Test | Result | Flag |
|---|---|---|
| Missingness–cluster correlation (Spearman ρ) | ρ = 0.339, p < 0.001 | Moderate — partially missingness-driven |
| Source classification accuracy (5-fold CV) | 87.6% ± 3.5% | ⚠ HIGH — features strongly encode database origin |

The 87.6% source classification accuracy confirms the Phase 4 clusters were largely database artifacts. Features are not source-neutral.

### D-PLACE Primary Subset

- n = 357 cultures with ≥ 3 features coded (mean 8.2 features)
- `unmapped_shamanic_indicators`: 99.7% present in subset → effectively a constant; does not discriminate clusters
- `specialist_presence`: 89.6% coded
- All other features: 10–52% coded within subset

### Clustering (k=9, silhouette=0.417)

| Cluster | n | Top features |
|---|---|---|
| 0 | 223 | specialist_presence (0.75), ritual_performance (0.55) |
| 1 | 61 | public_performance (0.98), ritual_performance (0.64) |
| 2 | 39 | nature_spirits (0.85), layered_cosmology (0.79), specialist_presence (1.0) |
| 3 | 6 | hereditary_transmission (1.0) |
| 4–7 | 1–3 | micro-clusters (over-specified) |
| 8 | 20 | ritual_performance (0.89) |

Clusters 4–7 are micro-clusters (1–3 cultures). **k=9 is likely over-specified.** A re-run with k=3–5 and `unmapped_shamanic_indicators` removed is recommended.

### ⚠ Mantel Test Reversal — Critical Finding

| Test | r | p | Significant |
|---|---|---|---|
| Phase 4 (joint matrix) | 0.040 | 0.186 | No |
| **Phase 8 (D-PLACE primary)** | **0.444** | **0.001** | **Yes** |

On the clean D-PLACE subset, **geography significantly predicts feature similarity** (r = 0.44, p = 0.001). The previous non-significant result was an artifact of source confounding diluting the geographic signal across databases with different geographic footprints.

This **reverses the hypothesis evaluation**: the evidence now points toward geographic patterning, which supports **regional diffusion** rather than neurobiological universalism. The universalism score of 4.0/5 must be retracted until further analysis.

### Immediate Follow-Up Required

1. **Remove `unmapped_shamanic_indicators` from features** — it is constant in the SCCS subset and contributes no discriminating signal
2. **Re-run clustering with k=3–5** to eliminate micro-clusters
3. **Re-run Mantel with the refined clustering** to confirm r=0.44 persists
4. **Compute Pagel's λ** on named D-PLACE features vs. Glottolog tree (still outstanding)
5. **Revise hypothesis synthesis** — universalism score must drop given significant Mantel

### Outputs

- `data/processed/clusters/phase8/culture_cluster_membership_phase8.parquet`
- `phase7_visualization/data/cultures_metadata.json` — `cluster_phase8` field added
- `phase7_visualization/data/cluster_profiles_phase8.json`
- `phase7_visualization/data/analysis_results.json` — `phase8` section added

## 7. Open Question — Did Phase 2 Harmonization Fail?

**Status:** TODO — audit required before final write-up

**Context:** The 87.6% source classification accuracy and zero shared features across sources raises the question: did the Phase 2 crosswalk fail to map overlapping variables, or do the databases genuinely not overlap on shamanic features?

**Two possible explanations:**

| Explanation | Evidence | Implication |
|---|---|---|
| Crosswalk missed mappings | Seshat has spirit_possession_crisis, Seshat has ritual specialists — were these mapped? | Phase 2 process failure; crosswalk needs revision |
| Databases genuinely don't overlap | Seshat was built for political complexity, not shamanism; DRH covers world religions not ethnographic societies | Data gap, not process failure; joint clustering was always the wrong design |

**Audit steps (TODO):**
1. Read `data/reference/crosswalk.csv` — list every Seshat and DRH variable that was mapped to the shared schema
2. Cross-check against `data/processed/harmonised/seshat_harmonised.parquet` and `drh_harmonised.parquet` — are the mapped variables populated, or all-NA?
3. If all-NA despite a crosswalk entry: Phase 2 extraction failed (fix the ingest pipeline)
4. If variable genuinely absent from source: data gap (document as limitation, no fix needed)
5. Document findings in this section

**Why it matters for the paper:** If the crosswalk is correct, the zero-intersection result is a data limitation to acknowledge. If Phase 2 missed real mappings, fixing it could add 1–3 shared features and enable a partial cross-source validation.

**Priority:** Medium — does not block Phase 8 reanalysis (D-PLACE primary is valid regardless), but affects the Discussion section's framing of cross-source coverage.

---

## 8. Refinement Results (30 April 2026, phase8_refinement.py)

### Feature set change
Removed `unmapped_shamanic_indicators` (99.7% present in SCCS subset — constant, no discriminating power) and `dedicated_specialist` (0% in D-PLACE). Final clustering used 16 SCCS shamanic features.

### Clustering: k=3

Only k=2 and k=3 avoid micro-clusters (min size ≥ 10). Selected k=3 (silhouette=0.341, all clusters ≥ 39 cultures).

| Cluster | n | Defining features |
|---|---|---|
| 0 | 39 | specialist_presence (1.0), nature_spirits (0.85), layered_cosmology (0.79), entheogen_use (0.72) — **cosmological specialists** |
| 1 | 215 | specialist_presence (0.82), layered_cosmology (0.30) — **general religious practitioners** |
| 2 | 103 | ritual_performance (0.83), public_performance (0.75) — **performative/public ritual** |

Three interpretable clusters corresponding to: specialist cosmology, generalist practitioners, public ritual performance.

### Mantel Test (confirmed)

**r = 0.465, p = 0.001** — highly significant. Geography predicts shamanic feature similarity in the clean D-PLACE dataset. This is the opposite of the Phase 4 conclusion and directly contradicts the "Neurobiological Universalism" synthesis.

### Pagel's λ

13/16 features show **strong phylogenetic signal** (λ ≈ 0.87–1.0, p < 0.05). This means shamanic features are strongly conserved within language families — cultures that share linguistic ancestry tend to share shamanic practices.

| Interpretation | n features | Examples |
|---|---|---|
| Strong (λ > 0.7, p < 0.05) | 13 | ancestor_mediation, soul_flight, rhythmic_percussion, entheogen_use |
| Moderate (not significant) | 1 | hereditary_transmission (n=39, underpowered) |
| Insufficient data | 2 | spirit_possession, trance_induction (0 coded in SCCS subset) |

### Revised Hypothesis Evaluation

| Test | Phase 4 result | Phase 8 (clean) result | Direction |
|---|---|---|---|
| Mantel geography~features | r=0.04, p=0.19 n.s. | **r=0.47, p=0.001 sig** | Supports diffusion |
| Pagel's λ | Stubs (not computed) | **λ=0.87–1.0, p<0.05 for 13/16 features** | Supports diffusion |
| Spatial autocorrelation | 1/19 sig (from Phase 6) | Not recomputed (see Phase 6) | Ambiguous |

**The universalism score of 4.0/5 must be retracted.** The clean analysis supports regional/phylogenetic patterning — shamanic features are geographically clustered (r=0.47) and phylogenetically conserved (λ≈1.0). This is more consistent with cultural diffusion within language families than with independent neurobiological emergence.

---

## 9. Implementation Log

**Date:** 30 April 2026  
**Script:** `scripts/phase8_reanalysis.py`  
**Status:** Complete (follow-up required — see Section 6)

