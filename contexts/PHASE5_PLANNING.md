# Phase 5 Planning: Interpretation & Publication

**Status:** Ready to Begin  
**Date:** 16 avril 2026  
**Predecessor:** Phase 4 (Clustering) ✅ COMPLETE

---

## 1. Phase 5 Overview

**Objective:** Transform k=8 clustering results into publication-ready manuscript and figures. Evaluate competing hypotheses (neurobiological universalism vs. regional diffusion).

**Timeline:** 2–3 weeks  
**Deliverables:** 
- Interpretation notebook (10–11)
- Manuscript sections (methods, results, discussion outlines)
- Publication figures (dendrograms, maps, temporal plots)
- Hypothesis evaluation summary

---

## 2. Cluster Interpretation (Key Task)

### Understanding the 8 Clusters

Based on immediate Phase 4 results, here's what each cluster represents:

| Cluster | Size | Dominant Features | Interpretation |
|---------|------|-------------------|-----------------|
| **0** | 714 | Generic/minimal features | **Outlier/non-specialist cultures** |
| **1** | 41 | Specialist (96%), cosmology (51%), entheogens (46%) | **Sophisticated shamanism** |
| **2** | 273 | **Trance induction (100%)** | **Trance-specialist complex** |
| **3** | 43 | Public performance (65%), ritual (55%) | **Public/ritual shamanism** |
| **4** | 175 | **Spirit possession (100%)** | **Possession-mediumship complex** |
| **5** | 1 | Hereditary transmission (100%) | **Single hereditary specialist** |
| **6** | 3 | Initiatory crisis (100%) | **Crisis-based initiation** |
| **7** | 7 | Ancestor mediation (100%) | **Ancestral veneration specialists** |

### Phase 5 Cluster Profiling Tasks

Each cluster needs:

1. **Geographic coherence test:** Do clusters map to geographic regions or are they globally distributed?
2. **Feature signature:** Top 3–5 defining features per cluster
3. **Temporal patterns:** How are cultures in each cluster distributed across time?
4. **Cross-cultural examples:** Specific named cultures per cluster (5–10 per cluster)
5. **Theoretical interpretation:** Does each cluster support universalism or diffusion theory?

---

## 3. Hypothesis Evaluation Framework

### Hypothesis 1: Neurobiological Universalism 🧠
**Prediction:** 1–2 tight global clusters with core shamanic features everywhere

**Tests:**
- [ ] Do Clusters 1–2 (specialist + trance) dominate?
- [ ] Are top features (trance, soul_flight, possession) found in >70% of cultures?
- [ ] Are clusters geographically distributed (not regional)?
- [ ] Is Silhouette score > 0.7 (tight coherence)?

**Expected result: SUPPORTED if** all 4 tests pass ✓

### Hypothesis 2: Regional Diffusion / Classificatory Bias 🗺️
**Prediction:** 4–6 regional clusters with distinct feature profiles

**Tests:**
- [ ] Do clusters map cleanly to geographic regions (Siberia, Americas, SEAsia, Africa, etc.)?
- [ ] Is feature distribution skewed by region (e.g., Africa = possession, Siberia = trance)?
- [ ] Are there "gap regions" with no shamanism representation?
- [ ] Is Silhouette score 0.4–0.6 (loose, regional clustering)?

**Expected result: SUPPORTED if** 3/4 tests pass ✓

---

## 4. Phase 5 Notebook Structure

### Notebook 10: Robustness Analysis

```
Section 1: Load Phase 4 outputs
  - Load culture_cluster_membership.csv
  - Load cluster_profiles.csv
  - Load validation_metrics.json

Section 2: Full dataset comparison (1,850 cultures)
  - Re-run identical clustering on full (non-filtered) dataset
  - Compare silhouette, Davies-Bouldin, cluster membership
  - Compute ARI between phylo-filtered and full-dataset results
  - Interpretation: Is result robust to Galton's correction?

Section 3: Feature sensitivity (core vs. all features)
  - Run clustering separately for:
    - Core shamanic features only (5 features)
    - All 19 features
  - Compare via ARI and silhouette scores
  - Interpretation: Are clusters stable across feature selection?

Section 4: Bootstrap stability (80% resampling, 100 iterations)
  - Resample 80% of cultures, re-cluster, measure ARI
  - Plot stability distribution
  - Interpretation: Are clusters robust to sampling variation?

Section 5: Summary table
  - Table comparing all robustness tests
  - Pass/fail checklist
```

### Notebook 11: Cluster Interpretation & Hypothesis Evaluation

```
Section 1: Geographic mapping
  - Scatter plot: each culture as point, colored by cluster
  - Overlay regions (Siberia, Americas, SEAsia, etc.)
  - Map with cluster boundaries marked
  - Count cultures per cluster per region (heatmap)

Section 2: Feature profiles
  - Bar chart: feature presence % per cluster (19 features × 8 clusters)
  - Identify top 3 defining features per cluster
  - Heatmap with cultural examples for each cluster

Section 3: Temporal distribution
  - Histogram: cultures per cluster per era (from ERAS config)
  - Time series: do clusters change temporal distribution?
  - Interpretation: Are clusters temporally stable?

Section 4: Hypothesis evaluation
  - Test 1: Are top features universal?
  - Test 2: Do clusters map to regions?
  - Test 3: Geographic vs. feature correlation (from robustness)
  - Summary: Which hypothesis supported?

Section 5: Cross-validation with external sources
  - Sample DRH traditions per cluster
  - Sample Seshat polities per cluster
  - Do they match D-PLACE cluster assignments?
  - Document any conflicts

Section 6: Cluster narratives
  - Write 100–200 word interpretation for each cluster
  - Cite specific cross-cultural examples
  - Link to supporting hypothesis
```

---

## 5. Publication Figures Checklist

### Figure 1: Cluster Validation
- **Left:** Silhouette plot (all 1,257 cultures, colored by cluster)
- **Right:** Dendrogram (hierarchical clustering on same data)
- **Caption:** Cluster coherence and membership stability

### Figure 2: Global Distribution Map
- World map with all 1,257 cultures as dots
- Color = cluster membership
- Size = number of features present per culture
- Overlay language families (lighter outlines)

### Figure 3: Cluster Profiles
- Heatmap: 8 clusters × 19 features
- Color intensity = feature presence %
- Sorted by cluster hierarchical similarity
- Annotations for cluster names/interpretations

### Figure 4: Geographic Coherence
- 8 subplots (one per cluster)
- Each subplot = regional breakdown of cluster
- Stacked bar chart: culture count per region per cluster
- Shows whether clusters are global or regional

### Figure 5: Hypothesis Comparison
- Left column: Predictions of Universalism hypothesis
  - Expected: 1–2 tight clusters globally distributed
  - Actual: 8 clusters shown as observed
- Right column: Predictions of Diffusion hypothesis
  - Expected: 4–6 regional clusters
  - Actual: 8 clusters shown mapped to regions
- Visual comparison narrative

---

## 6. Robustness Enhancements (Recommended)

### Priority 1 (Must do before Phase 5)
- [ ] **Feature sensitivity:** Test core vs. all features (ARI comparison)
- [ ] **Full dataset comparison:** Re-cluster 1,850 cultures, compare k=8 results
- [ ] **Geographic independence:** Compute Spearman r(feature_dist, geography_dist)

### Priority 2 (Nice to have)
- [ ] **Bootstrap stability:** Resample 80%, 100 iterations, measure ARI distribution
- [ ] **Temporal stability:** Cluster within each era separately, compare membership
- [ ] **Imputation comparison:** Test filling with 0 vs. mean vs. KNN imputation

### Priority 3 (Optional, publication quality)
- [ ] **Sensitivity to outliers:** Run clustering with/without max cluster size clipping
- [ ] **Cross-validation:** Train classifier on phylo-filtered, predict full dataset
- [ ] **Posterior predictive:** Bayesian mixture model with credible intervals

**Run robustness tests:**
```bash
python scripts/phase4_robustness.py  # ~15 minutes
```

---

## 7. Manuscript Outline

### Methods Section (Draft)

**Title:** Culture and Brain: Phylogenetic Clustering of Shamanic Practices

**Methods subsections:**
1. **Data Sources:** D-PLACE (1,850 societies), DRH, Seshat
2. **Feature Schema:** 19 shamanic practice features (operationalization)
3. **Phylogenetic Correction:** Galton's problem solution via language family filtering
4. **Clustering Methodology:**
   - Feature standardisation (z-score)
   - Optimal k selection (silhouette analysis, k=2–10)
   - K-means and hierarchical clustering
   - Validation metrics (silhouette, Davies-Bouldin, Calinski-Harabasz)
5. **Robustness Testing:** Feature sensitivity, bootstrap stability, geographic independence

### Results Section (Draft)

1. **Dataset Characteristics**
   - 1,257 cultures after phylogenetic filtering
   - 19 shamanic features, 68% data completeness

2. **Optimal Clustering**
   - Optimal k=8 (silhouette score = 0.722)
   - Davies-Bouldin = 0.782 (excellent separation)
   - Clear dendrogram structure

3. **Cluster Profiles**
   - 8 interpretable clusters with distinct feature signatures
   - Cluster 1–2: Specialist shamanism (high trance, cosmology)
   - Cluster 4: Possession mediumship complex
   - Cluster 0: Non-specialist religious practitioners

4. **Geographic Distribution**
   - [Describe geographic patterns per cluster]
   - [Document regional coherence]

5. **Robustness Testing Summary**
   - Feature sensitivity: ARI = 0.XX (robust)
   - Bootstrap stability: mean ARI = 0.YY (±ZZ)
   - Geographic independence: r(feature, geography) = 0.WW (p < 0.05)

### Discussion Section (Sketch)

1. **Support for Hypothesis [X]**
   - Evidence that clusters reflect [neurobiological universalism / regional diffusion]

2. **Qualifications and Limitations**
   - Geographic bias in data collection
   - Ethnographic present bias (D-PLACE)
   - Clustering assumes Euclidean geometry

3. **Theoretical Implications**
   - Cross-cultural practice clustering
   - Role of geography vs. neurobiology

4. **Next Steps**
   - Spatial autocorrelation analysis (Phase 6)
   - Temporal trajectory modeling (Phase 8)

---

## 8. Execution Checklist

### Week 1: Robustness & Data Prep
- [ ] Execute `scripts/phase4_robustness.py`
- [ ] Review robustness_analysis.json
- [ ] Document any sensitivity concerns

### Week 2: Notebook 10 (Robustness)
- [ ] Implement full dataset clustering (1,850 cultures, k=8)
- [ ] Compute ARI between phylo-filtered and full results
- [ ] Feature sensitivity tests (3 subsets)
- [ ] Bootstrap stability analysis
- [ ] Create comparison visualizations

### Week 2–3: Notebook 11 (Interpretation)
- [ ] Geographic mapping of clusters
- [ ] Temporal distribution analysis
- [ ] Hypothesis evaluation tests (5–7 tests)
- [ ] Cluster narratives (100 words each, ×8 clusters)
- [ ] Publication figures (5–6 figures)

### Week 3: Manuscript Draft
- [ ] Methods section (methodology)
- [ ] Results section (key findings)
- [ ] Discussion sketch (implications)
- [ ] Figure captions

---

## 9. Success Criteria

✅ **Robustness Testing:**
- Feature sensitivity ARI > 0.6 (across feature subsets)
- Bootstrap ARI mean > 0.7 (across 100 resamples)
- Geographic correlation r < 0.3 (features independent of geography)

✅ **Cluster Interpretation:**
- All 8 clusters interpretable (named, characterized)
- Geographic coherence documented (>60% of each cluster in 1–2 regions, or globally distributed)
- Temporal stability >70% (cluster membership consistent across eras)

✅ **Hypothesis Evaluation:**
- Clear evidence favoring one hypothesis, or
- Nuanced interpretation explaining both patterns

✅ **Publication Readiness:**
- 5+ high-quality figures
- Methods section 2–3 pages
- Results section with tables and statistics
- Discussion linking to theory

---

## 10. Optional Extensions (After Phase 5)

If time/interest permits:

1. **Temporal trajectory:** How do clusters evolve 1800–present?
2. **Machine learning:** Train XGBoost to predict cluster from core features
3. **Diffusion network:** Map contact pathways between cluster regions
4. **Linguistic depth:** Compare language family vs. cluster membership
5. **External validation:** Validate against ethnographic monograph samples

---

**Next action:** Run `python scripts/phase4_robustness.py` → Review results → Create Notebook 10

All Phase 5 infrastructure is ready to start! 🚀
