# Phase 3: Analysis & Synthesis
**Date:** 15 avril 2026  
**Status:** Planning  
**Deliverables:** Multi-source analysis, conflict resolution, synthesis narratives

---

## 1. Phase 3 Overview

Phase 3 transforms harmonised data into actionable insights through:
- **Cross-source comparison** - Identify agreements, conflicts, complementarities
- **Temporal analysis** - Detect patterns across -2000 to present timeline
- **Geographic coverage** - Map regional bias, identify data gaps
- **Feature synthesis** - Create composite indicators across sources
- **Conflict resolution** - Document and adjudicate source disagreements
- **Theory validation** - Test harmonised features against ethnographic/historical narratives

**Phase 2 → Phase 3:** 
- Input: 3 harmonised parquets (11,820 D-PLACE + 11 DRH records) + coverage audit
- Output: Analysis notebooks, conflict registry, synthesis methodology, visualizations

---

## 2. Phase 3 Architecture

### 2.1 Module Structure
```
src/analysis/
├── __init__.py
├── config.py              # Analysis configuration
├── comparison.py          # Cross-source comparison logic
├── temporal.py            # Temporal trend analysis
├── geography.py           # Geographic analysis & mapping
├── synthesis.py           # Feature synthesis & composite indicators
├── conflicts.py           # Conflict detection & resolution
└── validation.py          # Theory validation against ethnographic narratives

notebooks/
├── 03_cross_source_analysis.ipynb      # Comparison, conflicts, agreements
├── 04_temporal_patterns.ipynb          # -2000 to present timeline analysis
├── 05_geographic_analysis.ipynb        # Regional coverage, bias detection
├── 06_synthesis_indicators.ipynb       # Feature aggregation, composites
└── 07_conflict_resolution.ipynb        # Documented disagreements
```

### 2.2 Data Flow
```
Phase 2 Outputs (Harmonised Parquets)
    ↓
3 harmonised DataFrames (identical schema)
    ↓
┌─────────────────────────────────────────┐
│   CROSS-SOURCE COMPARISON               │
│   - Feature presence by source          │
│   - Agreement/conflict detection        │
│   - Confidence weighting                │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│   TEMPORAL ANALYSIS                     │
│   - Timeline extraction (-2000 to 2026) │
│   - Diachronic feature evolution        │
│   - Era-based stratification            │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│   GEOGRAPHIC ANALYSIS                   │
│   - Regional density heatmaps           │
│   - Latitude/longitude clustering       │
│   - Coverage bias quantification        │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│   SYNTHESIS & VALIDATION                │
│   - Composite indicators                │
│   - Ethnographic narrative matching     │
│   - Methodological documentation        │
└─────────────────────────────────────────┘
```

---

## 3. Phase 3 Methodological Decisions (Proposed)

### 3.1 Cross-Source Conflict Resolution
**Decision 1: Agreement Threshold**
- When sources disagree on presence (e.g., D-PLACE says trance_induction=1, DRH says 0):
  - **Option A (Any-source):** If ANY source reports feature → 1 (current Phase 2 approach)
  - **Option B (Majority):** If >50% of active sources agree → use majority value
  - **Option C (Weighted):** Use data_quality_score to weight vote
  - **PROPOSED:** Option C (weighted by quality score), with conflict flagged

**Decision 2: Conflict Logging**
- Create conflicts.csv with columns:
  - `culture_id`, `source1`, `source2`, `feature_name`, `value1`, `value2`, `quality1`, `quality2`, `resolved_value`, `resolution_method`
- Methods: "quality_weighted", "majority", "manual_inspection", "excluded"

### 3.2 Temporal Analysis Strategy
**Decision 3: Era Stratification**
- Define eras for diachronic analysis:
  - Prehistoric: -2000 to -1000
  - Ancient: -1000 to 500 CE
  - Medieval: 500 to 1500 CE
  - Early Modern: 1500 to 1800 CE
  - Industrial: 1800 to 1900 CE
  - Modern: 1900 to 2026 CE
- Allow overlap for cultures with date uncertainty (temporal_mode="mixed")

**Decision 4: Temporal Binning for Trends**
- Use 500-year windows (Phase 2 config) for trend detection
- Flag if culture's time_uncertainty > 1 (±100yr) when computing era-level statistics
- Document temporal coverage%

### 3.3 Geographic Analysis Strategy
**Decision 5: Regional Comparison**
- Quantify D-PLACE oversampling:
  - Calculate record density per region (records/1000 km²)
  - Calculate feature coverage%: (non-null values / total records) per region
  - Flag regions with <5 records per feature as "sparse"

**Decision 6: Coordinate Validation**
- Check lat/lon coordinate validity:
  - Outside ±90/±180 bounds → flag as invalid
  - Clusters at (0, 0) → investigate potential null substitution
  - Identify likely data-entry errors (e.g., lat=50.5, lon=10.5 in Pacific)

### 3.4 Synthesis & Validation Strategy
**Decision 7: Composite Indicators**
- Create higher-level features by aggregating base features:
  - `shamanic_complex` = (trance_induction OR spirit_possession) AND (dedicated_specialist OR initiatory_crisis)
  - `ritual_specialisation` = dedicated_specialist with high data_quality_score
  - Document uncertainty propagation (if all components have uncertainty 3, composite has +1)

**Decision 8: Theory Validation Against Narratives**
- Load ethnographic narratives from PROJECT_CONTEXT.md Section 2 (Theoretical Foundations)
- For major cultures (e.g., Siberian shamanism, Amazonian ayahuasca), cross-reference:
  - D-PLACE variables against published ethnographies
  - Feature values against field notes in DPLACE_REPO README.md
  - Document: {"culture_id": "X", "source": "ethnography_Y", "feature": "Z", "narrative_value": ..., "data_value": ..., "agreement": true/false}

---

## 4. Phase 3 Deliverables

### 4.1 Core Outputs
1. **conflicts.csv** - 3-way comparison (D-PLACE vs DRH vs Seshat)
2. **era_analysis.csv** - Feature presence by era + temporal uncertainty
3. **region_analysis.csv** - Record density, coverage%, sparse flags by region
4. **composite_indicators.csv** - Aggregated features with uncertainty propagation
5. **ethnographic_validation.csv** - Cross-check against published narratives

### 4.2 Notebooks
- **03_cross_source_analysis.ipynb** - Conflict matrix visualisation, agreement%
- **04_temporal_patterns.ipynb** - Timeline charts, era stratification
- **05_geographic_analysis.ipynb** - Regional heatmaps, density plots
- **06_synthesis_indicators.ipynb** - Composite indicator distributions
- **07_conflict_resolution.ipynb** - Documented disagreements + resolution log

### 4.3 Test Suite (test_analysis.py)
- Unit tests: comparison, temporal binning, geographic clustering
- Integration tests: conflict detection, synthesis pipeline
- Validation tests: schema conformance, uncertainty propagation
- Target: >90% coverage

---

## 5. Phase 3 Scope & Sequencing

### 5.1 Estimated Timeline
| Module | Tasks | Hours |
|--------|-------|-------|
| comparison.py | Implement cross-source logic, conflict detection | 3-4 |
| temporal.py | Era stratification, binning, uncertainty propagation | 3-4 |
| geography.py | Coordinate validation, density calc, clustering | 2-3 |
| synthesis.py | Composite indicators, uncertainty rollup | 2-3 |
| conflicts.py | Conflict resolution, logging, adjudication | 2-3 |
| validation.py | Ethnographic cross-check, narrative matching | 2-3 |
| Notebooks (5) | Analysis + visualisation for each module | 5-7 |
| test_analysis.py | Comprehensive test suite | 2-3 |
| **Total** | | **22-30 hrs** |

### 5.2 Proposed Sequence
1. **Week 1:** comparison.py → conflicts detection
2. **Week 2:** temporal.py → era-based analysis
3. **Week 3:** geography.py + synthesis.py → regional + composite indicators
4. **Week 4:** validation.py → ethnographic narratives + notebooks + tests

---

## 6. Phase 3 Research Questions

Phase 3 analysis will address:

1. **Cross-source concordance:** How often do D-PLACE and DRH agree on shamanic features?
2. **Temporal stability:** Do shamanic practices persist across eras, or show transition patterns?
3. **Geographic bias:** Is D-PLACE over-represented in specific regions? (e.g., Siberia)
4. **Feature complementarity:** Which D-PLACE features best co-occur with DRH tradition markers?
5. **Composite validity:** Do synthetic "shamanic_complex" indicators align with ethnographic definitions?
6. **Theory validation:** Do harmonised data confirm or challenge existing shamanism theories?

---

## 7. Assumptions & Constraints

### 7.1 Assumptions
- Phase 2 harmonised outputs are complete, valid, and semantically consistent
- D-PLACE variable definitions (SCCS codes, EA codes) remain consistent across all records
- DRH tradition classifications and cultural mapping are authoritative
- Seshat data (when activated) will follow Phase 2 forward-compatible patterns

### 7.2 Constraints
- **No new data ingestion** - Phase 3 uses only Phase 2 harmonised outputs + config metadata
- **No algorithm changes** - Phase 3 validates Phase 2 decisions, doesn't revise
- **Manual inspection required** - Difficult conflicts flagged for human adjudication
- **Narrative sources limited** - Ethnographic validation depends on available published literature

---

## 8. Success Criteria for Phase 3

✅ **Completion Criteria**
1. conflicts.csv with all 3-way agreements/disagreements documented
2. All 5 analysis notebooks executable with >95% test pass rate
3. Composite indicators calculated for 10+ secondary features
4. Ethnographic validation cross-checked against ≥5 published narratives per major culture
5. Geographic coverage bias quantified (% records by region)
6. Temporal era stratification applied to ≥80% of harmonised records
7. Zero missing values in derived outputs (NAs tracked explicitly)
8. Documentation complete: methodology, decisions, validation evidence

**Quality Gates**
- test_analysis.py: ≥90% pass rate
- Conflict resolution: ≥95% adjudicated
- Narrative validation: ≥80% harmonised features cross-validated
- Schema conformance: 100% (no data loss during synthesis)

---

## 9. Phase 3 Integration Points

### 9.1 Dependencies
- Phase 1 complete: ✅ (11,820 D-PLACE + 11 DRH + 4 Seshat raw records)
- Phase 2 complete: ✅ (harmonised schema, 5 modules, assembly script, full test suite)
- Methodological decisions: Proposed above (3.1-3.4), await user confirmation

### 9.2 Future Extensions (Phase 4+)
- **Phase 4:** Model building - temporal regression, cross-cultural correlations
- **Phase 5:** Publication & synthesis - coherent narrative integrating all sources

---

## 10. Next Steps

**Immediate Actions:**
1. ✅ Review Phase 3 context & methodological decisions (Sections 3)
2. ⏳ Confirm or modify proposed decisions for each module
3. ⏳ Prioritize modules (e.g., conflicts first vs. temporal analysis first)
4. ⏳ Provide ethnographic narratives for validation (Section 3.4, Decision 8)

**Then proceed with Phase 3 execution** following confirmed decisions.

---

## Appendix: Phase 2 → Phase 3 Data Handoff

**Phase 2 Outputs (Confirmed):**
```
data/processed/harmonised/
├── dplace_harmonised.parquet     (11,820 rows × 22 columns)
├── drh_harmonised.parquet        (11 rows × 22 columns)
├── coverage_audit.csv            (9 region×time_bin cells)
└── schema: 22 columns, identical across sources
```

**Phase 3 Inputs (Ready):**
- ✅ All harmonised parquets verified
- ✅ Schema consistency confirmed
- ✅ Data quality scores computed
- ✅ Coverage gaps documented

**Phase 3 Will Generate:**
- Comparison matrices (agreement %, conflict flags)
- Temporal stratification (6 eras × features)
- Regional density & coverage statistics
- Composite indicator definitions & distributions
- Validation reports (narrative cross-check)

---

**Last Updated:** 15 avril 2026  
**Phase Status:** Ready for execution upon approval of methodological decisions
