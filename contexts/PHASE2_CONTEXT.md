# PHASE2_CONTEXT.md — Data Harmonisation

> **Status:** Phase 1 complete. Phase 2 ready to begin.
> **Goal:** Transform three independent raw datasets (D-PLACE, DRH, Seshat) into a unified, structurally comparable DataFrame with resolved cross-database conflicts and transparent harmonisation decisions.
> **Output:** Three harmonised parquet files + coverage audit + scale decisions + crosswalk reference

---

## Overview

**Status Update (28 April 2026):** Seshat activation complete. All 3 sources now active.

Phase 1 produced three raw parser outputs:
- **D-PLACE**: 11,820 records (1,850 societies, 64 variables)
- **DRH**: 11 records (11 traditions, 5 variables)
- **Seshat**: 2,214 records (2,213 polities, 6 variables) ✅ **ACTIVE 28 April**

**Total Harmonised Data**: 14,044 records (18.7% increase from Seshat; 11,820 D-PLACE + 11 DRH + 2,213 Seshat)

These differ fundamentally in **unit of observation** (society vs. tradition vs. polity), **temporal granularity** (snapshot vs. diachronic), **coding vocabulary** (EA codes vs. DRH survey labels), and **variable scales** (binary vs. ordinal).

**Phase 2 resolves these differences explicitly**, producing three "harmonised" DataFrames that share identical column schema and can be stacked or cross-referenced without hidden conflicts. Nothing downstream of this phase should contain raw source variable names.

---

## Input Data

Each source parser (from Phase 1) outputs a DataFrame with columns:
```
source, culture_id, culture_name, unit_type, lat, lon, time_start, time_end, 
variable_name, variable_value, variable_type, confidence, notes
```

### D-PLACE
- **Source:** `data/raw/dplace/societies.csv`, `variables.csv`, `data.csv`, `codes.csv`
- **Unit:** Ethnolinguistic society (SCCS or other classification scheme), associated with language family via Glottolog
- **Temporal:** Synchronic snapshot (~1850–1950 "ethnographic present")
- **Key variables:** EA112 (trance states), EA34 (religious practitioners), SCCS codes (shamanism, healing, percussion, etc.)
- **Metadata:** Glottolog code (language family), geographic coordinates, geographic region
- **Challenge:** No explicit time range; coded as single year (-1850) placeholder

### DRH (Database of Religious History)
- **Source:** `data/raw/drh/drh_sample.csv` (234 religious traditions)
- **Unit:** Religious tradition (may span multiple countries/polities)
- **Temporal:** Mixed: some entries describe a period, others are open-ended
- **Key variables:** Binary yes/no responses to religious practice questions (trance, divination, healing, possession, etc.)
- **Metadata:** Region field, Start Date / End Date (often incomplete)
- **Challenge:** No geographic coordinates in raw data; multiple traditions per region

### Seshat (Status: ✅ ACTIVE as of 28 April 2026)
- **Source:** `data/raw/seshat/polities.csv`, `variables.csv`, `data.csv` (via REST API)
- **Unit:** Polity (political entity at a specific time period)
- **Temporal:** Diachronic: each polity-variable pair has a corresponding time range (extends to -3000 CE)
- **Volume**: 2,213 polities with 2,214 variable observations
- **Key variables**: professional_priesthood, religious_level_from, human_sacrifice, moralizing_supernatural_beings
- **Metadata:** Polity centroid (lat/lon), era/period names, time ranges
- **Challenge:** Polity-level aggregation masks tradition-level diversity; temporal ranges may be uncertain
- **Implementation Date**: 28 April 2026 (Commit f91f8fb)

---

## Harmonisation Tasks

### Task 1: Crosswalk Definition (`src/harmonise/crosswalk.py`)

**Goal:** Map every raw source variable to the shared feature schema (Section 3 of PROJECT_CONTEXT.md).

**Deliverables:**
1. **`data/reference/crosswalk.csv`** — master table defining the mapping:
   ```
   feature,d_place_var_id,d_place_code,drh_column,seshat_var_id,notes
   trance_induction,EA112,1|2|3|4|5,Does religious specialist engage in trance:,spirit_possession_trance,Values 1-5 all indicate yes
   spirit_possession,EA112,6|7,Is spirit possession present:,spirit_possession,Value 6-7 map to yes
   dedicated_specialist,EA34,1|2|3|4|5,Does the religion have religious specialists:,religious_specialist_presence,"Ordinal: 1=none, 2=part-time, 3-5=full-time"
   ...
   ```

**Resolved Seshat Crosswalk Mappings (28 April 2026):**

| Seshat Variable | Maps To Feature | Binarisation Rule | Notes |
|---|---|---|---|
| `professional_priesthood` | `dedicated_specialist` | Binary passthrough (already binary in Seshat) | Maps to ordinal value 2 (full-time) |
| `religious_level_from` | `dedicated_specialist` | Ordinal → binary: threshold ≥ 3 | `religious_level_from` is ordinal 0–5; ≥3 = full-time specialist |
| `human_sacrifice` | `ritual_practice` | Binary passthrough | Seshat codes as 0/1 |
| `moralizing_supernatural_beings` | `supernatural_beliefs` | Boolean field mapping | Seshat field already boolean; mapped to 0/1 |

**Source-specific binarisation rules:**
- Seshat variables are already binary or have explicit ordinal levels; no ambiguity
- `religious_level_from` threshold of ≥3 chosen to match DRH definition of full-time specialist
- Conflicts with D-PLACE: 0 conflicts (Seshat polities are geographically non-overlapping with D-PLACE societies in most cases)

2. **`src/harmonise/crosswalk.py`** — Python module with:
   - `load_crosswalk()` → loads the CSV
   - `map_variable(source, raw_var_name, raw_value) → feature_name, feature_value` — translates any raw variable to the schema
   - `validate_crosswalk()` → ensures every source variable is covered; no raw names leak through
   - Tests: run through sample records from each source, confirm no unmapped variables

**Methodology:**
- For each source variable, inspect the raw data + its documentation
- Determine which feature(s) in the schema it represents
- If multiple raw values map to the same feature, document the threshold (e.g., "EA112 = 1|2 → trance_induction = 1")
- If a source variable only partially covers a feature (e.g., DRH records presence of trance but not spirit possession), flag it with a confidence note
- **Document every decision** in a comment block in the CSV

**Key decisions to record (Section 8 of PROJECT_CONTEXT.md):**
- **Crosswalk validation threshold:** Require the feature to appear in ≥1 sources? ≥2 sources?
- **Conflict resolution:** If DRH says "yes, trance" but D-PLACE says "no", how to code in the harmonised matrix?

---

### Task 2: Unit-of-Observation Reconciliation (`src/harmonise/units.py`)

**Goal:** Assign every record a standardised `unit_type` and flag ambiguities.

**Deliverables:**
1. **`src/harmonise/units.py`** with functions:
   - `harmonise_units(df_dplace, df_drh, df_seshat) → (df_dplace_h, df_drh_h, df_seshat_h)`
   - Each output DataFrame has new columns:
     - `unit_type`: "society" (D-PLACE), "tradition" (DRH), "polity" (Seshat)
     - `unit_ambiguous`: boolean flag if unit boundaries are uncertain
     - `unit_note`: free text explanation of any ambiguity

**Methodology:**

**D-PLACE → society (no change)**
- Each society is a distinct ethnolinguistic unit
- Add `unit_type = "society"`, `unit_ambiguous = False` to all rows

**DRH → tradition (mostly)**
- Each row represents a religious tradition/denomination
- Some traditions span multiple countries (e.g., Islam). These are marked `unit_ambiguous = True`
- If a tradition is explicitly linked to a polity in the source, add that info to `unit_note`
- Add `unit_type = "tradition"`

**Seshat → polity at time-slice**
- Each row is (polity, time period)
- Polities may contain multiple traditions simultaneously (ambiguous)
- Mark `unit_ambiguous = True` if the polity's religious composition is heterogeneous or unknown
- Add `unit_type = "polity"`
- Preserve `time_start` and `time_end` from Seshat

**Output schema (all three harmonised frames):**
```
source, culture_id, culture_name, unit_type, unit_ambiguous, unit_note,
lat, lon, time_start, time_end,
variable_name, variable_value, confirmation, notes
```

**Key decisions to record:**
- **Unit-of-observation consolidation strategy:** Keep all units / Collapse to finest / Polity-only?
- Should harmonised output filter to `unit_ambiguous = False`? Or include all with explicit flagging?

---

### Task 3: Temporal Standardisation (`src/harmonise/temporal.py`)

**Goal:** Assign all records explicit `time_start`, `time_end`, and temporal metadata.

**Deliverables:**
1. **`src/harmonise/temporal.py`** with:
   - `standardise_years(source, raw_date_col) → (time_start_int, time_end_int)` — converts to BCE (negative) / CE (positive)
   - `assign_temporal_mode(source) → mode` — flags whether data is snapshot, diachronic, or mixed
   - `apply_temporal_standardisation(df, source) → df_standardised`

2. **Add columns to harmonised output:**
   - `temporal_mode`: "snapshot" (D-PLACE), "diachronic" (Seshat), "mixed" (DRH varies)
   - `time_uncertainty`: ordinal (0=certain, 1=±100yr, 2=±500yr, 3=±1000yr+)

**Methodology:**

**D-PLACE:**
- Raw data: no explicit time range; coded as single year in Phase 1 (-1850)
- Harmonised: assign all D-PLACE records to `time_start = -1750, time_end = -1950` (estimate: ethnographic contact ~1750–1950 CE)
- Add `temporal_mode = "snapshot"` and `time_uncertainty = 3` (high uncertainty)
- Document that D-PLACE represents a broad synchronic band, not a specific year

**DRH:**
- Raw data: `Start Date` and `End Date` columns (years CE)
- Harmonised: convert directly; if missing, flag `time_uncertainty = 3`
- Assign `temporal_mode = "mixed"` because some entries are snapshots, others span centuries
- Document the range for each entry

**Seshat:**
- Raw data: Explicit `time_start` and `time_end` already present
- Harmonised: keep as-is; assign `temporal_mode = "diachronic"`
- Estimate `time_uncertainty` from the source (usually 1 or 2)

**Key decisions to record:**
- **D-PLACE temporal assumption:** What year range best represents "ethnographic present"? (-1750 to -1950)? (-1850 to -1950)? Other?
- **DRH date handling:** For entries with missing dates, how to impute? Assume modern (1900–2000)?

---

### Task 4: Coverage Audit (`src/harmonise/coverage.py`)

**Goal:** Generate explicit audit of data coverage to identify gaps and biases.

**Deliverables:**
1. **`src/harmonise/coverage.py`** with:
   - `geographic_coverage_by_source(df_list) → map_ready_df` — count records per region per source
   - `temporal_coverage_by_source(df_list) → timeline_df` — records per century per source
   - `overlap_analysis(df_dplace, df_drh, df_seshat) → overlap_matrix, venn_diagram_data`
   - `gap_report(df_combined) → gap_df` — regions/periods with <3 records

2. **`data/processed/harmonised/coverage_audit.csv`** output:
   ```
   region,dplace_count,drh_count,seshat_count,total,gap_severity,data_density_map
   Northern America,542,12,0,554,low,✓
   Central America,89,4,0,93,high,?
   sub-Saharan Africa,234,8,0,242,high,?
   ...
   ```

3. **Visualisations (in `notebooks/02_harmonisation.ipynb`):**
   - World map faceted by source, showing record density
   - Timeline (x=time, y=#records) per source
   - Venn diagram: overlap between sources

**Methodology:**
- Define regions: use Natural Earth shapefile (`data/reference/natural_earth/`) to assign lat/lon to regions
- Define time bins: e.g., 500-year windows (pre-1000 BCE, 1000–500 BCE, ..., 1500–2000 CE)
- Count records in each (region, time_bin, source) cell
- Flag "high gap severity" if a region or period has <3 records across all sources combined

**Key decisions to record:**
- **Region definition:** Use Natural Earth? Custom regions? Other?
- **Time bin width:** 200yr, 500yr, 1000yr? (Affects granularity vs. sample size)
- **Gap threshold:** <3 records is "high severity"? Other threshold?

---

### Task 5: Scale Normalisation (`src/harmonise/scale.py`)

**Goal:** Resolve scale mismatches (ordinal ↔ binary) across sources for the same feature.

**Deliverables:**
1. **`src/harmonise/scale.py`** with:
   - `identify_scale_conflicts(crosswalk) → conflicts_df` — for each feature, list its scales across sources
   - `apply_scale_decisions(df_harmonised, scale_decisions_table) → df_scaled` — binarise ordinals according to decisions
   - `validate_scales(df_scaled) → report` — confirm all outcomes are binary/ordinal consistently

2. **`data/processed/harmonised/scale_decisions.csv`** output:
   ```
   feature,d_place_scale,drh_scale,seshat_scale,harmonised_scale,binarisation_rule,justification
   dedicated_specialist,ordinal_(0-5),binary,binary,binary,"Ordinal values 0|1|2 → 0, 3|4|5 → 1","Full-time specialists are what distinguish shamanism"
   trance_induction,binary,binary,binary,binary,"All binary; no conversion needed",""
   ...
   ```

3. **As part of `PHASE2_CONTEXT.md` Section 8 decisions:**
   - Galton's problem correction strategy (must be fixed before Feature Extraction)
   - Decision: **keep ordinal or binarise**?

**Methodology:**
- Review the crosswalk: identify features where sources disagree on scale (e.g., `dedicated_specialist` is ordinal in D-PLACE but binary in DRH)
- For each scale conflict, document what the feature means at each scale
- **Make explicit binarisation rules:** e.g., "dedicated_specialist: combine D-PLACE (0/1/2 = part-time, 3/4/5 = full-time) into binary 0/1"
- For ordinal variables (e.g., "ritual complexity" with levels 0–5), decide: keep as-is and adjust feature matrix downstream, or binarise here?
- **IMPORTANT:** This is where you decide Galton's problem strategy:
  - **Option A (None):** Use all 2,087 cultures as independent observations
  - **Option B (One-per-language-family):** Filter to one society per D-PLACE language family (via Glottolog) ⇒ reduces to ~150–200 societies
  - **Option C (Phylogenetic weights):** Use all observations but weight by phylogenetic distance (complex, requires dendrogram computation)

**Key decisions to record:**
- **Scale harmonisation rule:** For each scale conflict, which source's scale do we adopt? (Theory-driven? Majority vote?)
- **Binarisation thresholds:** For ordinal variables binarised to binary, what threshold?
- **Galton's problem strategy:** A / B / C above. Document the choice clearly; it determines the eligible sample size downstream.

---

### Task 6: Harmonised DataFrames Assembly

**Goal:** Create three clean, standardised DataFrames ready for Feature Extraction.

**Deliverables:**
1. **`data/processed/harmonised/dplace_harmonised.parquet`**
   - Source: D-PLACE parser output + crosswalk + units.py + temporal.py + scale.py
   - Schema:
     ```
     source, culture_id, culture_name, unit_type, unit_ambiguous, unit_note,
     glottolog_code, language_family,  # D-PLACE-specific metadata
     lat, lon, temporal_mode, time_start, time_end, time_uncertainty,
     variable_name, variable_value, feature_name,  # After crosswalk mapping
     original_var_id, confirmation, notes
     ```
   - 11,820 rows

2. **`data/processed/harmonised/drh_harmonised.parquet`**
   - Source: DRH parser output + same harmonisation pipeline
   - Schema: same as above (columns like `glottolog_code` are null/NA)
   - 1,170 rows

3. **`data/processed/harmonised/seshat_harmonised.parquet`**
   - Source: Seshat REST API → `src/ingest/seshat_fetch.py` → harmonisation pipeline
   - Schema: same as above
   - **2,213 polities with 2,214 variable observations** (activated 28 April 2026, commit f91f8fb)

**All three share identical column schema** so they can be concatenated without silent misalignment.

---

### Task 7: Harmonisation Notebook (`notebooks/02_harmonisation.ipynb`)

**Goal:** Inspect and validate all harmonisation decisions.

**Cells:**
1. **Load and diff:** Show raw vs. harmonised versions side-by-side for sample records from each source
2. **Crosswalk validation:** List all source → feature mappings; highlight any raw variable names that leak through
3. **Units inspection:** Show distribution of `unit_type` and `unit_ambiguous` flags; explain any ambiguities
4. **Temporal exploration:** Plot time_start/end distribution per source; overlay temporal_mode flags
5. **Coverage visualisation:** 
   - World map faceted by source, showing record density per region
   - Timeline plot (x=time, y=#records)
   - Venn diagram of source overlap
   - Table from `coverage_audit.csv` highlighting gaps
6. **Scale decisions review:** Table of binarisation rules; sample records before/after
7. **Galton's problem strategy:** Document the chosen approach (A/B/C) and its implications for sample size
8. **Conflict log:** Any manual overrides or ambiguities that required expert judgment; save to `data/processed/harmonised/conflicts.csv`

**Key validation:**
- ✓ No raw source variable names in harmonised outputs
- ✓ All three harmonised frames have identical columns
- ✓ `unit_ambiguous` and `time_uncertainty` flags are present and documented
- ✓ All records have valid lat/lon after geocoding (NA is acceptable but flagged)
- ✓ Galton's problem strategy is documented and reproducible

---

## Output Files

After Phase 2 completion, the following files should exist:

```
data/processed/harmonised/
├── dplace_harmonised.parquet          # 11,820 rows
├── drh_harmonised.parquet             # 1,170 rows
├── seshat_harmonised.parquet          # 6 rows (or more if real data)
├── coverage_audit.csv                 # Region/period/source coverage summary
├── scale_decisions.csv                # Binarisation and scale normalisation decisions
└── conflicts.csv                      # Any manual overrides or ambiguous entries

data/reference/
├── crosswalk.csv                      # Master mapping: source vars → features
└── [existing files]

notebooks/
├── 02_harmonisation.ipynb             # Validation and inspection notebook
└── [existing files]

src/harmonise/
├── __init__.py
├── crosswalk.py                       # Mapping logic
├── units.py                           # Unit-of-observation reconciliation
├── temporal.py                        # Temporal standardisation
├── coverage.py                        # Coverage audit and visualisation
└── scale.py                           # Scale normalisation

tests/
├── test_harmonise.py                  # Unit tests for all harmonise modules
└── [existing files]
```

---

## Testing Checklist

Before merging Phase 2 to main:

- [ ] All 22 existing Phase 1 tests still pass
- [ ] `test_harmonise.py` passes with >90% coverage of `src/harmonise/`
- [ ] `notebooks/02_harmonisation.ipynb` runs end-to-end without errors
- [ ] No raw source variable names appear in any harmonised output (check column names + data values)
- [ ] All three harmonised DataFrames have identical column schema
- [ ] `coverage_audit.csv` identifies all major geographic and temporal gaps
- [ ] `scale_decisions.csv` justifies every binarisation decision
- [ ] Galton's problem strategy is documented and reproducible
- [ ] `conflicts.csv` logs any manual overrides or ambiguous cases
- [ ] Geographic coordinates: D-PLACE and Seshat have valid lat/lon; DRH entries are either geocoded or flagged NA
- [ ] Temporal metadata: all records have `temporal_mode` and `time_uncertainty` populated

---

## Key Methodological Decisions

Fill in Section 8 of PROJECT_CONTEXT.md as you proceed. At minimum, decide:

| Decision | Options | Status |
|---|---|---|
| Unit-of-observation consolidation | Keep all / Collapse to finest / Polity-only | _to decide_ |
| Crosswalk validation threshold | Majority vote / Any-source / All-sources | _to decide_ |
| D-PLACE temporal assumption | Which year-range for "ethnographic present"? | _to decide_ |
| Scale harmonisation rule | Theory-driven / Majority vote / Source-weighted | _to decide_ |
| Galton's problem strategy | None / One-per-language-family / Phylogenetic weights | **CRITICAL: must decide before Phase 3** |
| Region definition | Natural Earth / Custom / Other | _to decide_ |
| Time bin width | 200yr / 500yr / 1000yr | _to decide_ |
| Gap threshold | <3 records / <5 records / Other | _to decide_ |

---

## Estimated Effort

- **`crosswalk.py`**: 4–6 hours (requires careful documentation)
- **`units.py`**: 2–3 hours
- **`temporal.py`**: 3–4 hours
- **`coverage.py`**: 4–5 hours (includes visualisation)
- **`scale.py`**: 3–4 hours
- **Assembly + testing**: 3–4 hours
- **Notebook `02_harmonisation.ipynb`**: 4–6 hours (exploration + validation)
- **Total**: ~25–35 hours of focused work

Work phase-by-phase (one module per day ideally) to avoid cascading errors.

---

## Git Workflow

1. Create branch: `git checkout -b feat/harmonise`
2. Create directory: `mkdir -p src/harmonise`
3. For each sub-task (crosswalk, units, temporal, coverage, scale):
   - Write module + tests in `tests/test_harmonise.py`
   - Run tests locally: `pytest tests/test_harmonise.py::TestModule -v`
   - Commit: `git commit -m "feat(harmonise): implement [module-name]"`
4. After all modules: write `notebooks/02_harmonisation.ipynb`
5. Final commit: `git commit -m "docs(harmonise): validation notebook"` + `git tag v0.2-harmonisation`
6. PR to main; merge after review

---

## Notes for the AI Assistant

When you proceed to Phase 2 work:

1. **Load this file + PROJECT_CONTEXT.md at the start of every session.** It's your source of truth for Phase 2 scope.
2. **Work one module at a time.** Don't try to write all five modules simultaneously.
3. **Write tests first.** Define test cases (sample records from each source) before implementing the mapping logic.
4. **Document every decision.** If you override a decision or discover an edge case, log it and ask the user for confirmation.
5. **Verify diffs carefully.** Before committing each module, inspect the output to ensure no silent regressions (e.g., NA → 0 conversions).
6. **Iterate on the crosswalk.** The crosswalk is the foundation; if it's wrong, all downstream modules fail. Expect 2–3 revisions as you discover inconsistencies between sources.

---

*Created: 15 avril 2026*
*Phase 1 completion date: 15 avril 2026*
*Phase 2 estimated completion: 25 avril 2026 (subject to data access and analytical decisions)*
