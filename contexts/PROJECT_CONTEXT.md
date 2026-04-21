# PROJECT_CONTEXT.md — Shamanism Spatio-Temporal Analysis

> **Purpose of this file:** This is the master context document for the project. Feed it to your AI coding assistant (GitHub Copilot, Claude Code, Cursor, etc.) at the start of every session so it understands the project's goals, architecture, data, and conventions. Keep it updated as decisions evolve.

---

## 1. Research question

**Do the practices and features labeled "shamanism" across world cultures cluster into a statistically coherent category — as predicted by neurobiological universalism — or do they distribute as regionally distinct complexes better explained by cultural diffusion and Western classificatory bias?**

This is a spatio-temporal computational analysis using cross-cultural databases. The project follows the DH Circle methodology: source digitisation → processing → analysis/visualisation → insight → new questions feeding back into sources.

### Two competing hypotheses

| Hypothesis | What the data would show | Key authors |
|---|---|---|
| **Neurobiological universalism** | All "shamanic" cultures cluster together globally regardless of geography. Core features (trance, spirit contact) co-occur universally because of shared human brain architecture. | Eliade, Winkelman |
| **Regional diffusion / classificatory bias** | Cultures fragment into 3–5 regional clusters with distinct feature profiles. "Shamanism" is a Western umbrella term imposed on unrelated practices. | Kehoe, Hutton, Znamenski |

---

## 2. Data sources

### 2.1 Database of Religious History (DRH)
- **URL:** https://religiondatabase.org/
- **Unit of observation:** Religious group/tradition
- **Format:** Structured expert-survey responses (mostly binary yes/no/uncertain + free text)
- **Relevant variables:** Trance, spirit possession, soul journey, healing rituals, divination, cosmological levels, religious specialists, ritual substances, ancestor worship
- **Access method:** Web API (JSON) or CSV bulk download
- **Strengths:** Rich on belief content and ritual detail
- **Weaknesses:** Uneven geographic coverage, expert-dependent coding

### 2.2 Seshat: Global History Databank
- **URL:** https://seshatdatabank.info/
- **Unit of observation:** Polity (political entity) at a specific time period
- **Format:** CSV/TSV with coded variables, temporal ranges
- **Relevant variables:** Spirit possession, religious specialist presence, divination, supernatural beings, ritual complexity
- **Access method:** Bulk download (CSV) or API
- **Strengths:** Excellent temporal resolution (century-level), covers deep history
- **Weaknesses:** Coarser religious data (polity-level, not tradition-level)

### 2.3 D-PLACE (Database of Places, Language, Culture and Environment)
- **URL:** https://d-place.org/
- **Unit of observation:** Ethnolinguistic society
- **Format:** CSV with coded ethnographic variables, linked to Glottolog language trees
- **Relevant variables:** EA v112 (trance states), SCCS shamanism/healing codes, drug use, divination, religious practitioners (EA v34), initiation rites
- **Access method:** Bulk CSV download, GitHub repository
- **Strengths:** Linked to phylogenetic language trees, geographic coordinates included, Standard Cross-Cultural Sample (SCCS) is well-validated
- **Weaknesses:** Mostly single ethnographic snapshot per society ("ethnographic present"), colonial-era observation bias

---

## 3. Feature schema (operationalization)

Each culture-time-point becomes a row. Columns are binary (0/1) or ordinal (0/1/2) features. `NA` = not recorded (never treat as 0).

### 3.1 Altered states of consciousness
| Feature | Code | Definition | Primary source |
|---|---|---|---|
| `trance_induction` | binary | Practitioner deliberately enters non-ordinary mental state | DRH, D-PLACE v112, Seshat |
| `soul_flight` | binary | Soul/spirit travels to other realms while body remains | DRH, D-PLACE SCCS |
| `spirit_possession` | binary | Spirit enters and controls the practitioner's body | DRH, Seshat, D-PLACE |
| `entheogen_use` | binary | Psychoactive substances used ritually for altered states | D-PLACE SCCS, DRH |

### 3.2 Specialist role and initiation
| Feature | Code | Definition | Primary source |
|---|---|---|---|
| `dedicated_specialist` | ordinal (0/1/2) | Recognized social role (0=none, 1=part-time, 2=full-time) | DRH, Seshat, D-PLACE EA v34 |
| `initiatory_crisis` | binary | Illness, death-rebirth, or ordeal required before becoming specialist | DRH, D-PLACE SCCS |
| `hereditary_transmission` | binary | Role passed within family/lineage | D-PLACE EA, DRH |

### 3.3 Cosmology and spirit world
| Feature | Code | Definition | Primary source |
|---|---|---|---|
| `layered_cosmology` | binary | Belief in upper/lower/middle worlds or axis mundi | DRH, D-PLACE SCCS |
| `animal_transformation` | binary | Practitioner becomes or merges with animal spirit | DRH, D-PLACE SCCS |
| `ancestor_mediation` | binary | Communication with or channeling of deceased ancestors | DRH, Seshat, D-PLACE |
| `nature_spirits` | binary | Interaction with spirits of natural features (rivers, mountains, forests) | DRH, D-PLACE |

### 3.4 Technique and performance
| Feature | Code | Definition | Primary source |
|---|---|---|---|
| `rhythmic_percussion` | binary | Drumming, rattling, or rhythmic sound central to trance induction | DRH, D-PLACE SCCS |
| `healing_function` | binary | Primary purpose is curing illness or removing affliction | DRH, Seshat, D-PLACE |
| `divination` | binary | Foretelling future or discovering hidden knowledge | DRH, Seshat, D-PLACE |
| `public_performance` | binary | Ritual performed before community audience | DRH, D-PLACE SCCS |
| `chanting_singing` | binary | Vocal techniques (icaros, throat singing, chanting) central to practice | DRH, D-PLACE |

### 3.5 Coding rules
- **Presence threshold:** Code 1 if any source reports the feature as present in the tradition. Code 0 only if explicitly described as absent.
- **Conflict resolution:** If sources disagree, majority vote across sources. Document conflicts in a `conflicts.csv` log.
- **Missing data:** Code as `NA`. Never impute as 0. Handle via multiple imputation or complete-case analysis in the analysis phase.
- **Galton's problem:** Select one representative society per language family, or weight observations by phylogenetic distance.

---

## 4. Project architecture

```
shamanism-spatiotemporal/
├── PROJECT_CONTEXT.md          # ← This file (AI context)
├── README.md                   # Project overview for humans
├── .gitignore
├── pyproject.toml              # Python project config (dependencies)
│
├── data/
│   ├── raw/                    # Original downloads (never modify)
│   │   ├── drh/
│   │   ├── seshat/
│   │   └── dplace/
│   ├── processed/              # Cleaned, aligned data
│   │   ├── harmonised/             # ← NEW: per-source harmonised DataFrames
│   │   │   ├── drh_harmonised.parquet
│   │   │   ├── seshat_harmonised.parquet
│   │   │   ├── dplace_harmonised.parquet
│   │   │   ├── coverage_audit.csv
│   │   │   └── scale_decisions.csv
│   │   ├── feature_matrix.parquet
│   │   ├── geocoded.parquet
│   │   └── conflicts.csv
│   └── reference/              # Language trees, shapefiles, etc.
│       ├── glottolog/
│       └── natural_earth/
│
├── notebooks/                  # Jupyter notebooks (exploration, one per phase)
│   ├── 01_data_ingestion.ipynb
│   ├── 02_harmonisation.ipynb      # ← NEW: crosswalk, coverage audit, scale normalisation
│   ├── 03_feature_extraction.ipynb
│   ├── 04_geocoding.ipynb
│   ├── 05_clustering.ipynb
│   ├── 06_spatial_analysis.ipynb
│   ├── 07_diffusion_models.ipynb
│   └── 08_robustness_checks.ipynb
│
├── src/                        # Reusable Python modules
│   ├── __init__.py
│   ├── ingest/                 # Data loading and parsing
│   │   ├── __init__.py
│   │   ├── drh.py              # DRH API/CSV parser
│   │   ├── seshat.py           # Seshat CSV parser
│   │   └── dplace.py           # D-PLACE CSV parser
│   ├── harmonise/              # ← NEW: cross-database harmonisation
│   │   ├── __init__.py
│   │   ├── crosswalk.py        # Ontological mapping: source variables → feature schema
│   │   ├── units.py            # Unit-of-observation reconciliation (tradition / polity / society)
│   │   ├── temporal.py         # Temporal standardisation & mode flagging
│   │   ├── coverage.py         # Coverage audit: geographic & temporal gap report
│   │   └── scale.py            # Scale normalisation (ordinal → binary decisions)
│   ├── features/               # Feature extraction and alignment
│   │   ├── __init__.py
│   │   ├── schema.py           # Feature definitions (the schema above)
│   │   ├── align.py            # Cross-database alignment logic
│   │   └── impute.py           # Missing data handling
│   ├── geo/                    # Geocoding and temporal binning
│   │   ├── __init__.py
│   │   ├── geocode.py
│   │   └── temporal.py
│   ├── analysis/               # Statistical analysis
│   │   ├── __init__.py
│   │   ├── clustering.py       # PCA, UMAP, k-means, hierarchical
│   │   ├── spatial.py          # Moran's I, DBSCAN, spatial autocorrelation
│   │   ├── phylogenetic.py     # Mantel test, phylogenetic signal
│   │   └── validation.py       # Silhouette, bootstrap, elbow
│   └── viz/                    # Visualization helpers
│       ├── __init__.py
│       ├── globe.py            # Globe rendering helpers
│       └── plots.py            # Static matplotlib/seaborn plots
│
├── app/                        # Interactive prototype (web app)
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── Globe.jsx       # 3D globe (deck.gl or CesiumJS)
│   │   │   ├── TimeSlider.jsx  # Time range slider
│   │   │   ├── SearchBar.jsx   # Practice/feature search
│   │   │   ├── ClusterPanel.jsx # Cluster info sidebar
│   │   │   └── Legend.jsx
│   │   ├── hooks/
│   │   │   └── useData.js      # Data loading and filtering
│   │   └── utils/
│   │       ├── colors.js       # Cluster color schemes
│   │       └── filters.js      # Time/feature filtering logic
│   └── public/
│       └── data/               # Pre-processed JSON for the frontend
│           ├── cultures.json   # Geocoded cultures with features
│           └── clusters.json   # Pre-computed cluster assignments
│
├── tests/
│   ├── test_ingest.py
│   ├── test_harmonise.py       # ← NEW
│   ├── test_features.py
│   ├── test_clustering.py
│   └── test_spatial.py
│
└── scripts/
    ├── download_data.sh        # Fetch raw data from APIs
    ├── build_matrix.py         # Run full pipeline: raw → feature matrix
    └── export_for_app.py       # Convert analysis output → JSON for frontend
```

---

## 5. Technology stack

### 5.1 Backend / analysis (Python 3.11+)
| Library | Purpose |
|---|---|
| `pandas`, `polars` | Data manipulation, parquet I/O |
| `numpy` | Numerical operations |
| `scikit-learn` | PCA, k-means, silhouette score, DBSCAN |
| `umap-learn` | UMAP dimensionality reduction |
| `scipy` | Hierarchical clustering, Mantel test, spatial distance matrices |
| `libpysal` + `esda` | Moran's I, spatial autocorrelation (PySAL ecosystem) |
| `geopandas` | Geospatial data handling |
| `matplotlib` + `seaborn` | Static plots for notebooks |
| `requests` | API calls to DRH |
| `dendropy` or `ete3` | Phylogenetic tree handling (D-PLACE Glottolog trees) |
| `scikit-bio` | Mantel test, distance matrices |
| `fancyimpute` or `sklearn.impute` | Multiple imputation for missing data |

### 5.2 Frontend / prototype (TypeScript + React)
| Library | Purpose |
|---|---|
| `react` + `vite` | App framework and bundler |
| `deck.gl` | WebGL globe with scatterplot layers |
| `react-map-gl` | Map base layer (Mapbox) |
| `d3-scale`, `d3-color` | Color scales for clusters and features |
| `rc-slider` or custom | Time range slider component |
| `zustand` or `jotai` | Lightweight state management |

### 5.3 Development environment
| Tool | Purpose |
|---|---|
| VS Code | Primary editor |
| GitHub Copilot / Claude | AI coding assistants (vibe coding) |
| Git + GitHub | Version control, branching per phase |
| Jupyter | Exploration notebooks |
| pytest | Test suite |
| pre-commit | Linting (ruff), formatting (black) |

---

## 6. Pipeline: step-by-step build plan

Follow this order. Each step is one git branch. Merge to main only after tests pass.

### Phase 1: Data ingestion (`branch: feat/ingest`)
1. Write `src/ingest/dplace.py` — load D-PLACE CSV files, parse society metadata (name, lat/lon, language family, Glottolog code), extract relevant variable columns (EA v112, v34, SCCS codes)
2. Write `src/ingest/seshat.py` — load Seshat CSVs, parse polity metadata (name, region, date range), extract religion-related variables
3. Write `src/ingest/drh.py` — query DRH API or parse bulk CSV, extract religious group metadata and survey responses
4. Write `notebooks/01_data_ingestion.ipynb` — explore all three datasets, document coverage, identify relevant variables, note gaps
5. **Test:** Each parser returns a clean DataFrame with columns: `source`, `culture_id`, `culture_name`, `lat`, `lon`, `time_start`, `time_end`, `variable_name`, `value`

### Phase 2: Data harmonisation (`branch: feat/harmonise`)

> **Why this phase exists.** The three databases differ in unit of observation (tradition / polity / society), temporal granularity, coding vocabulary, and variable scale. Feeding raw parser output directly into `align.py` pushes these structural differences into the feature matrix silently. This phase resolves them explicitly, producing three clean, structurally comparable DataFrames before any cross-database alignment occurs. Nothing downstream of this phase should touch raw variable names.

1. Write `src/harmonise/crosswalk.py` — define an explicit ontological crosswalk table mapping every source variable to the shared feature schema (Section 3). Document every mapping decision (e.g., `DRH:trance_states` ↔ `DPLACE:EA_v112 (values 4–5)` ↔ `Seshat:spirit_possession`). Store the crosswalk as a versioned CSV at `data/reference/crosswalk.csv`.
2. Write `src/harmonise/units.py` — define rules for reconciling units of observation:
   - DRH: religious tradition → keep as-is; flag entries linked to multiple polities with `unit_ambiguous = True`
   - Seshat: polity at time-slice → assign to the dominant tradition in that polity/period where identifiable; otherwise flag `unit_ambiguous = True`
   - D-PLACE: ethnolinguistic society → keep as-is; add `unit_type = "society"` column
   - Output rule: each row carries a `unit_type` column (`tradition` / `polity` / `society`) and a `unit_ambiguous` boolean
3. Write `src/harmonise/temporal.py` — standardise temporal representation across all sources:
   - Assign each record `time_start` and `time_end` as integers (BCE negative, CE positive)
   - Add `temporal_mode` column: `snapshot` (D-PLACE, ethnographic present ≈ 1850–1950), `diachronic` (Seshat), or `mixed` (DRH, varies by entry)
   - Flag D-PLACE records explicitly as circa 1850–1950 rather than treating them as timeless
4. Write `src/harmonise/coverage.py` — produce a coverage audit before merging:
   - World map of record density per database by macro-region and time bin
   - Overlap matrix: how many cultures appear in 2 or 3 databases simultaneously?
   - Gap report: regions or periods with < 3 records across all sources
   - Output: `data/processed/harmonised/coverage_audit.csv`
5. Write `src/harmonise/scale.py` — normalise coding scales for cross-database comparability:
   - Identify variables that are ordinal in one source and binary in another (e.g., `dedicated_specialist`)
   - Document each binarisation decision in `data/processed/harmonised/scale_decisions.csv`
   - **Decide Galton's correction strategy here** (one-per-language-family vs. phylogenetic weights) — this affects the eligible pool of observations and must be fixed before feature extraction
6. Write `notebooks/02_harmonisation.ipynb` — inspect each harmonised DataFrame, visualise coverage gaps on a world map, review crosswalk decisions, validate that no raw variable names leak into harmonised outputs, flag any conflicts for `conflicts.csv`
7. **Test:** All three harmonised DataFrames share an identical column schema: `source`, `culture_id`, `culture_name`, `unit_type`, `unit_ambiguous`, `temporal_mode`, `lat`, `lon`, `time_start`, `time_end`, `variable_name`, `value`. No raw source variable names appear downstream. `coverage_audit.csv` and `scale_decisions.csv` are both populated. Galton's correction strategy is recorded in Section 8 before the phase is closed.

### Phase 2.5: Cross-Source Culture Linkage (`branch: feat/linkage`)

> **Why this phase exists.** Phase 2 produced harmonised DataFrames but they use incompatible culture identifiers (D-PLACE uses "CARNEIRO4_001", DRH tracks traditions not specific societies). This means Phase 3 cannot detect cross-source conflicts or validate results. Phase 2.5 creates explicit linkage tables mapping DRH traditions to D-PLACE societies using geographic proximity and temporal overlap, enabling cross-source validation in Phase 3.

1. Write `src/harmonise/linkage.py` — Implement geographic+temporal linkage:
   - `haversine_distance()` — Calculate great-circle distances between points
   - `find_geographic_matches()` — Identify D-PLACE cultures within 500 km of each DRH tradition coordinate
   - `classify_temporal_overlap()` — Classify temporal relationship (SAME_ERA / ADJACENT_ERA / DISTANT_ERA) with confidence weights
   - `compute_confidence_score()` — Combine geographic and temporal signals: confidence = (1 - normalized_distance) × temporal_weight
   - `resolve_linkages()` — Filter by confidence threshold and produce structured output tables
   - `create_linkage_tables()` — Full pipeline from parquets to reference tables
2. Generate linkage reference tables (automatic via pipeline script):
   - `data/reference/dplace_drh_linkage.csv` — Main output: (drh_id, d_place_culture_id, distance_km, temporal_overlap, confidence_score)
   - `data/reference/linkage_confidence.csv` — Per-DRH record: confidence distribution summary, needs_expert_review flags
   - `data/reference/linkage_coverage.csv` — High-level statistics: cultures linked, traditions linked, geographic threshold
   - `data/reference/linkage_needs_review.csv` — Matches below confidence threshold (0.5) requiring manual expert adjudication
3. Write `tests/test_linkage.py` — Comprehensive test suite (22 tests):
   - Distance calculations against known city pairs
   - Temporal classification edge cases
   - Confidence scoring bounds
   - Integration tests with real Phase 2 outputs
4. Document Phase 2.5 in `contexts/PHASE2_5_CONTEXT.md`
5. **Output:** 4 reference CSVs ready for Phase 3 cross-source analysis. Example linkages:
   - "Siberian Shamanism" (DRH) → Selkup, Ket (D-PLACE, confidence 0.85–0.88)
   - "Korean Shamanism" (DRH) → Koreans (D-PLACE, confidence 0.95+)
   - "Sufi Islam" (DRH) → Iranians, Bakhtiari (D-PLACE, confidence 0.25–0.35)
6. **Test:** 22/22 unit tests passing. Linkage tables have consistent structure. Confidence scores in [0, 1]. No linkages have distance > 500 km. Geographic matches exist for ≥3 DRH traditions.

### Phase 3: Feature extraction (`branch: feat/features`)

> **Input:** harmonised DataFrames from Phase 2 + linkage tables from Phase 2.5 — not raw parser output.

1. Write `src/features/schema.py` — define the feature schema (Section 3 above) as a Python dataclass or dict. Map each feature to its crosswalk-resolved variable names (not raw source variables).
2. Write `src/features/align.py` — for each culture, look up the relevant variables across all three harmonised DataFrames, apply coding rules, produce the binary/ordinal feature matrix
3. Write `src/features/impute.py` — implement missing data strategies (complete-case filter, multiple imputation via IterativeImputer)
4. Write `notebooks/03_feature_extraction.ipynb` — inspect the feature matrix, report missingness rates per feature and per culture, flag conflicts
5. Output: `data/processed/feature_matrix.parquet` — one row per culture-time-point, columns = features, plus metadata columns (`culture_id`, `source`, `unit_type`, `temporal_mode`, `lat`, `lon`, `time_start`, `time_end`)
6. **Test:** Matrix shape is (n_cultures, n_features + metadata). No silent NA→0 conversions. No raw source variable names in column headers. Conflict log is populated.

### Phase 4: Clustering & Validation (`branch: analysis/clustering`)

> **Type:** Analysis & Validation (uses Phase 3 feature matrix; no new infrastructure code)
> **Purpose:** Execute clustering and identify optimal cluster structure. Validate results via robustness testing.

1. Write `src/analysis/clustering.py`:
   - `run_pca(matrix, n_components)` — PCA with loadings output
   - `run_umap(matrix, n_neighbors, min_dist)` — UMAP embedding
   - `run_kmeans(matrix, k_range)` — k-means for k=1..10, return inertias and labels
   - `run_hierarchical(matrix, method, metric)` — agglomerative clustering, return dendrogram data
   - `run_dbscan(matrix, eps, min_samples)` — density-based clustering
2. Write `src/analysis/validation.py`:
   - `silhouette_analysis(matrix, labels)` — per-cluster and global silhouette scores
   - `elbow_plot(inertias)` — detect elbow point
   - `bootstrap_stability(matrix, algo, n_iter)` — resample 80%, re-cluster, measure agreement (Adjusted Rand Index)
3. Write `notebooks/05_clustering.ipynb`:
   - Run PCA, plot loadings → which features drive variance?
   - Run UMAP, color by region → visual cluster check
   - Run k-means for k=1..10, plot elbow + silhouette → choose optimal k
   - Run hierarchical clustering, plot dendrogram → which cultures merge first?
   - Run DBSCAN → identify outlier cultures
   - Compare: do PCA and UMAP agree on cluster structure?
   - **Critical test:** Run clustering with (a) theory-driven features only, (b) all religion variables. Compare cluster stability.
4. Write `scripts/phase4_robustness.py` — offline robustness testing:
   - Feature sensitivity: core vs. all features vs. subsets
   - Alternative k values: k=2–10 comparison
   - Imputation strategies: fill-zero vs. mean vs. KNN
   - Geographic independence: Spearman correlation (feature dist vs. geography)
   - Bootstrap stability: 100 resamples, Adjusted Rand Index agreement
   - Temporal stability: clustering within each era separately
   - Output: `robustness_analysis.json` with all test results
5. **Deliverables:** Optimal k determined, cluster assignments, validation metrics, robustness report
6. **Test:** Silhouette > 0.4, Davies-Bouldin < 2.0, Calinski-Harabasz > 20. Bootstrap ARI > 0.6. All robustness tests exceed publication thresholds.

### Phase 5: Interpretation & Publication (`branch: analysis/publication`)

> **Type:** Publication & Interpretation (post-analysis; no code infrastructure)
> **Purpose:** Transform k-means clusters into publication-ready manuscript. Evaluate competing hypotheses with quantified statistical tests. This phase is manuscript drafting and theoretical synthesis, not infrastructure development.

1. Create `notebooks/10_robustness_analysis.ipynb` — Visualize Phase 4 robustness results:
   - Load pre-computed `robustness_analysis.json`
   - Section 1: Load cluster membership & profiles
   - Section 2: Full dataset comparison (phylo-filtered vs. all 1,850 cultures)
   - Section 3: Feature sensitivity visualization
   - Section 4: k selection robustness (k=5-10 metrics)
   - Section 5: Imputation strategy performance
   - Section 6: Geographic independence test
   - Section 7: Robustness validation checklist (all tests must PASS)
   - **Output:** 4 publication figures (300 dpi PNG)

2. Create `notebooks/11_cluster_interpretation.ipynb` — Cluster interpretation & hypothesis evaluation:
   - Section 1: Setup & data loading
   - Section 2: Geographic distribution analysis (9 world regions)
   - Section 3: Cluster profile heatmap (8×19 features)
   - Section 4: Regional distribution by cluster
   - Section 5: Hypothesis 1 evaluation — Neurobiological universalism (3+ quantified tests)
   - Section 6: Hypothesis 2 evaluation — Regional diffusion (2+ quantified tests)
   - Section 7: Cluster interpretations (8 detailed narratives, 100–200 words each)
   - Section 8: Hypothesis synthesis (evidence summary for both theories)
   - Section 9–10: Manuscript Methods & Results sections (publication-ready prose)
   - **Output:** Cluster narratives, hypothesis evaluation, 2 manuscript sections

3. Deliverables:
   - ✅ 8 interpretable clusters with named feature signatures
   - ✅ Hypothesis evaluation: quantified support for universalism AND diffusion
   - ✅ Geographic analysis: cluster distribution across 9 world regions
   - ✅ 5+ publication figures (300 dpi PNG)
   - ✅ Manuscript sections: Methods (550+ words) + Results (400+ words)
   - ⏳ Pending: Discussion section, Abstract, Supplementary tables

4. Success criteria:
   - All clusters have interpretable cultural narratives
   - Hypothesis tests are quantified (p-values, effect sizes, test statistics)
   - Manuscript sections are publication-ready (clear, concise, well-cited)
   - Figures are high-quality and properly captioned
   - Publication readiness checklist complete

### Phase 6: Spatial analysis (`branch: feat/spatial`)
1. Write `src/analysis/spatial.py`:
   - `morans_i(feature_vector, coords, weight_type)` — spatial autocorrelation per feature
   - `spatial_cluster_test(feature_matrix, coords)` — test whether clusters are spatially contiguous
   - `distance_decay(feature_matrix, coords)` — plot feature similarity vs. geographic distance
2. Write `src/analysis/phylogenetic.py`:
   - `load_language_tree(glottolog_path)` — parse Newick tree from D-PLACE
   - `mantel_test(geo_dist, feature_dist, phylo_dist)` — partial Mantel: does geography predict features after controlling for language?
   - `phylogenetic_signal(tree, feature_vector)` — Pagel's lambda or Blomberg's K
3. Write `notebooks/06_spatial_analysis.ipynb` and `notebooks/07_diffusion_models.ipynb`
4. **Test:** Moran's I p-values are computed with permutation tests (n=999). Mantel test uses permutations, not parametric p-values.

### Phase 7: Interactive prototype (`branch: feat/app`)
1. Write `scripts/export_for_app.py` — convert `geocoded.parquet` + cluster labels to JSON:
   ```json
   {
     "cultures": [
       {
         "id": "tungus_001",
         "name": "Evenki",
         "lat": 62.0, "lon": 108.0,
         "time_start": -500, "time_end": 1900,
         "cluster": 0,
         "features": { "trance_induction": 1, "soul_flight": 1, ... }
       }
     ],
     "clusters": [
       { "id": 0, "label": "Siberian/Arctic complex", "color": "#1D9E75", "top_features": ["soul_flight", "rhythmic_percussion", "trance_induction"] }
     ]
   }
   ```
2. Build `app/src/components/Globe.jsx`:
   - Render a Deck.gl ScatterplotLayer on a globe projection
   - Each point = one culture, colored by cluster membership
   - Point size = number of features present (data density indicator)
   - Tooltip on hover: culture name, time period, feature list
3. Build `app/src/components/TimeSlider.jsx`:
   - Range slider with two handles (start/end year)
   - Preset buttons: "all time", "pre-1000 BCE", "ethnographic present"
   - Changing the slider filters the globe points via `useData` hook
4. Build `app/src/components/SearchBar.jsx`:
   - Autocomplete search for feature names (e.g., type "trance" → highlights all cultures with trance_induction=1)
   - Toggle: "show only matching" vs. "highlight matching"
   - When a feature is selected, globe re-colors: matching cultures in feature color, non-matching in gray
5. Build `app/src/components/ClusterPanel.jsx`:
   - Sidebar showing cluster summary: name, number of cultures, top features, geographic distribution
   - Click a cluster to zoom the globe to its geographic extent
6. **Test:** App loads with full dataset in < 3 seconds. Time slider filters correctly. Search highlights correctly. All points have valid coordinates.

### Phase 8: Robustness and interpretation (`branch: feat/robustness`)
1. `notebooks/08_robustness_checks.ipynb`:
   - Sensitivity to feature set: compare theory-driven vs. kitchen-sink clustering
   - Sensitivity to missing data: compare complete-case vs. imputed results
   - Sensitivity to Galton's problem: compare full dataset vs. one-per-language-family
   - Sensitivity to time: do clusters change across time slices?
2. Interpretation summary: for each cluster, list the defining features, geographic range, and theoretical implications

---

## 7. Conventions and rules

### 7.1 Code style
- Python: `black` formatter, `ruff` linter, type hints on all function signatures
- JavaScript/TypeScript: `prettier`, `eslint`
- All functions have docstrings explaining parameters, return types, and assumptions
- No hardcoded file paths — use `pathlib.Path` relative to project root or config file

### 7.2 Data conventions
- **Never modify raw data.** All transformations produce new files in `data/processed/`.
- Use `.parquet` for intermediate data (fast, typed, compact). Use `.csv` only for human-readable logs.
- Column naming: `snake_case`, lowercase, no spaces. Example: `trance_induction`, `time_start`, `culture_name`.
- Missing values: `pd.NA` or `np.nan`, never empty string, never 0, never -1.

### 7.3 Git workflow
- One branch per phase (see Section 6). Name: `feat/<phase-name>`
- Commit after each working sub-step. Message format: `feat(ingest): parse D-PLACE society metadata`
- Merge to `main` via pull request after notebook runs end-to-end
- Tag milestones: `v0.1-ingestion`, `v0.2-harmonisation`, `v0.3-features`, `v0.4-clustering`, `v0.5-prototype`
- **Never commit API keys or credentials.** Use `.env` file (gitignored) and `python-dotenv`.

### 7.4 Vibe coding practices (from course guidelines)
- **Manage context:** Always provide this file + the relevant `src/` module + the current notebook to the AI assistant. Don't assume it remembers previous sessions.
- **Plan 1–2 steps ahead:** Don't ask the AI to build the entire pipeline at once. Work phase by phase.
- **Iterate small:** Get one function working before moving to the next. Test in isolation before integrating.
- **Verify diffs:** Always review what the AI changed before committing. Check for silent NA→0 conversions, hardcoded paths, and dropped edge cases.
- **Parallel attempts:** If clustering gives unexpected results, try multiple approaches (PCA vs. UMAP, k-means vs. hierarchical) before concluding.
- **Know when to restart:** If a module gets tangled, start a fresh file rather than patching endlessly.
- **AI self-test:** Ask the AI to write tests for its own code. Run them before trusting the output.

---

## 8. Key analytical decisions (document as you go)

Track every methodological choice here. When you make a decision, add a row.

**RESOLVED (15 avril 2026):**

| Decision | Options considered | Choice made | Justification | Phase | Date |
|---|---|---|---|---|---|
| Unit-of-observation reconciliation | Keep all units / Collapse to finest / Polity-only | **Keep all units** (society, tradition, polity) with `unit_type` + `unit_ambiguous` flags | Preserves data richness; downstream analysis can filter by unit type for sensitivity checks | Ph. 2 | 15 Apr 2026 |
| Crosswalk validation threshold | Majority vote / Any-source / All-sources | **Any-source presence rule** — log disagreements in `conflicts.csv` | Maximizes coverage; conflicts explicitly documented for transparency | Ph. 2 | 15 Apr 2026 |
| D-PLACE temporal assumption | Fixed year / Range / Other | **Ethnographic present: 1800–1950 CE** (positive CE years for clarity) with high uncertainty (±500yr equivalent) | Represents period of anthropological observation (late 19th–early 20th century). Interpreted as approximate cultural state, not precise date. | Ph. 2 | 15 Apr 2026 |
| D-PLACE temporal encoding | Negative BCE / Positive CE / Mixed | **Positive CE years (1800, 1950)** for semantic clarity; deprecated use of negative notation | Resolves Issue #5: standard convention clearer than negated BCE | Ph. 2 | 15 Apr 2026 |
| Scale harmonisation rule | Theory-driven / Majority vote / Source-weighted | **Strictly theory-driven approach** — binarisation thresholds grounded in domain logic | Ensures interpretability; avoids arbitrary statistical thresholds | Ph. 2 | 15 Apr 2026 |
| Galton's correction strategy (primary) | None / One-per-language-family / Phylogenetic weights | **Primary analysis: One-per-language-family (via Glottolog)**; full dataset as robustness check | Manages phylogenetic pseudoreplication; implements two-pronged approach per Mace & Pagel (1994) | Ph. 4 | 15 Apr 2026 |
| Galton's correction strategy (robustness) | None / Full dataset | **Robustness check: Run clustering on full dataset (all 2,087 D-PLACE cultures)** | Compares filtered vs. unfiltered results to assess sensitivity to phylogenetic non-independence | Ph. 4 | 15 Apr 2026 |
| Source quality weighting | Quality-weighted / Majority / Any-source / Weighted | **REMOVED: No source weighting** — Use any-source rule instead | Resolves Issue #3: Eliminates hidden bias from quality assumptions; treats all sources equally | Ph. 2–3 | 15 Apr 2026 |
| Conflict resolution strategy | Quality-weighted / Majority / Any-source | **Any-source rule** (no weighting) — if ANY source reports feature → 1 | Transparent, reproducible; avoids arbitrary quality scores | Ph. 3 | 15 Apr 2026 |
| Region definition | Natural Earth / Custom / Other | **Natural Earth regions** for reproducibility | Standard, publicly available, no custom bias | Ph. 4 | 15 Apr 2026 |
| Time bin width | 200yr / 500yr / 1000yr | **500-year bins** — balance between resolution and sample size per bin | 500yr provides sufficient granularity for cultural change time scales | Ph. 4 | 15 Apr 2026 |
| Gap threshold | <3 / <5 / <10 records | **<5 records per region/time bin** = high gap severity | Conservative threshold; flags underrepresented space-times | Ph. 2 | 15 Apr 2026 |
| Data quality scoring | Single metric / Multi-factor | **Multi-factor: `data_quality_score = f(unit_ambiguous, time_uncertainty, source_count)`** | Enables filtering high-quality subsets + robustness checks across data quality levels | Ph. 2 | 15 Apr 2026 |
| Number of features | 10 / 15 / 20+ | _pending_ | | Ph. 3 | |
| Missing data strategy | Complete-case / Imputation / Both | _pending_ | | Ph. 3 | |
| Clustering algorithm | k-means / Hierarchical / DBSCAN / Multiple | _pending_ | | Ph. 5 | |
| Optimal k | 1–10 | _pending_ | Determined by elbow + silhouette | Ph. 5 | |
| Spatial weight matrix | k-nearest / Distance band / Queen contiguity | _pending_ | | Ph. 6 | |
| Globe framework | Deck.gl / CesiumJS / Mapbox Globe | _pending_ | | Ph. 7 | |

---

## 9a. Methodological Deep Dives

### Galton's Problem (Phylogenetic Independence)

**Issue resolved (15 avril 2026):**

D-PLACE contains 2,087 ethnolinguistic societies clustered into ~150–200 language families (via Glottolog). Including all 2,087 violates independence assumptions: societies from the same language family are phylogenetically related and likely to share features through descent rather than independent evolution.

**Solution: Two-pronged robustness approach**

1. **Primary analysis (Option B):** Filter to one representative culture per language family (~150–200 cultures)
   - Implemented in `src/analysis/phylogenetic.py:filter_one_per_language_family()`
   - Ensures phylogenetic independence
   - Suitable for clustering, correlation tests, statistical inference

2. **Robustness check (Option A):** Run identical analysis on full dataset (2,087 cultures)
   - Compare cluster stability, silhouette scores, ARI metrics
   - If results are similar → phylogenetic non-independence not critical
   - If results diverge → phylogenetic filtering is important for validity

**Reference:** Mace & Pagel (1994). "The comparative method in anthropology." *Current Anthropology* 35(3): 87–92.

---

### Source Weighting (Conflict Resolution)

**Issue resolved (15 avril 2026):**

Original approach used quality-weighted averaging (D-PLACE: 0.5, DRH: 0.3, Seshat: 0.2). This introduced hidden bias without explicit justification.

**Solution: Remove weighting, use any-source rule**

- If ANY source reports feature as present → value = 1
- Conflicts logged in `conflicts.csv` for transparency
- All sources treated equally; no arbitrary quality assumptions
- Requires explicit, documented disagreement handling

**Rationale:** Quality is tracked but not used for weighting. Downstream analysis can filter by data_quality_score if needed.

---

### D-PLACE Temporal Assumption

**Issue resolved (15 avril 2026):**

**What:** D-PLACE data represents the "ethnographic present" during 1800–1950 CE (period of anthropological observation).

**Semantic clarification:**
- Now encoded as **positive CE years** for standard clarity: `time_start = 1800, time_end = 1950`
- (Old negative-BCE encoding `-1950 to -1800` is deprecated but documented for legacy compatibility)

**What it means:**
- ~150-year window corresponding to late 19th and early 20th century fieldwork
- Represents an *approximate cultural state*, not a precise date
- Observed practices may reflect traditions extending centuries back

**Temporal uncertainty:**
- Uncertainty level: 3 (~±500+ years equivalent)
- This is *representativeness uncertainty*, not measurement error
- High uncertainty reflects ambiguity in how "contemporary practices" map to historical processes

**Why 1800–1950 specifically:**
- Corresponds to period of SCCS / D-PLACE ethnographic collection
- Conservative choice balancing coverage and coherence

**Usage in analysis:**
- D-PLACE separate from Seshat (diachronic) for temporal analysis
- Flag D-PLACE records explicitly as "ethnographic present" snapshot
- When combining across sources, acknowledge temporal mismatch

---

## 10. Known risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| DRH coverage gaps (few African, Pacific entries) | Clusters biased toward well-documented regions | Flag coverage density on the globe; weight analyses by coverage |
| "Ethnographic present" conflates time periods | Temporal analysis is unreliable for D-PLACE data | Separate analysis for Seshat (diachronic) vs. D-PLACE (synchronic snapshot) |
| Feature set predetermines clustering result | Circular reasoning | Run clustering with alternative feature sets; report sensitivity |
| Galton's problem inflates sample size | Spatial clusters are artifacts of shared ancestry | Phylogenetic correction via D-PLACE language trees |
| Western classification bias in source databases | "Shamanism" label applied inconsistently | Include all spirit-related practices, not just those labeled "shamanic"; let clustering decide |
| Missing data skews clustering | Cultures with few recorded features cluster by missingness, not by actual similarity | Use complete-case as primary; imputation as sensitivity check |

---

## 11. Glossary

| Term | Definition |
|---|---|
| **Operationalization** | Translating an abstract theoretical concept (shamanism) into measurable variables (binary features) |
| **Datafication** | Converting qualitative source material into structured, machine-readable data |
| **DH Circle** | The feedback loop: digitisation → processing → analysis → visualisation → insight → new digitisation |
| **Galton's problem** | The statistical non-independence of culturally or linguistically related societies |
| **Moran's I** | A measure of spatial autocorrelation: do nearby locations have similar values? |
| **Mantel test** | Tests correlation between two distance matrices (e.g., geographic distance vs. feature distance) |
| **Silhouette score** | Measures cluster quality: how similar each point is to its own cluster vs. nearest other cluster (-1 to 1) |
| **UMAP** | Uniform Manifold Approximation and Projection: nonlinear dimensionality reduction preserving local structure |
| **Ethnographic present** | The convention of describing a society in present tense at the time of first Western ethnographic contact |
| **Entheogen** | A psychoactive substance used in ritual/spiritual context (ayahuasca, peyote, psilocybin, etc.) |

---

*Last updated: 2026-04-14*
*Maintainers: [your names here]*
