# PHASE2_5_CONTEXT.md — Cross-Source Culture Linkage

> **Status:** Phase 2 (harmonisation) complete. Phase 2.5 addresses missing culture-level linking.
> **Goal:** Create explicit mappings between D-PLACE societies, DRH religious traditions, and geographic/temporal relationships.
> **Output:** Culture linkage reference table + confidence scoring + overlap analysis
> **Reason:** Phase 2 produced feature-level crosswalk but missed culture-level harmonisation, preventing Phase 3 from performing cross-source validation.

---

## Problem Statement

Phase 2 successfully produced:
✅ Feature crosswalk (`data/reference/crosswalk.csv`) — Maps EA112 → trance_induction, etc.
✅ Harmonised parquets — 11,831 records in unified schema

But Phase 2 **missed a critical deliverable:**
❌ Culture linkage — No mapping between D-PLACE cultures and DRH traditions

### Why This Matters

| Dataset | Unit of Analysis | Records | Problem |
|---------|-----------------|---------|---------|
| **D-PLACE** | Specific archaeological cultures (Egyptians, Koreans, Siberians) | 11,820 records, 1,383 cultures | Pinpoint geographic/cultural units |
| **DRH** | Religious traditions (Shamanism, Buddhism, Islam) | 11 records, 5 traditions | Applied across multiple cultures/regions |
| **Issue** | These are **orthogonal dimensions** | - | 1 DRH tradition ≠ 1 D-PLACE culture; instead 1 tradition can apply to MANY cultures |

**Example:**
- DRH record: "Siberian Shamanism" (Lat 60°, Lon 100°)
- D-PLACE contains: Selkup, Ket, Evenk, Tungusic, Mongolic—all shamanic societies within ~500km of that coordinate
- **Which D-PLACE culture should link to "Siberian Shamanism"?** → ANSWER: All of them, with geographic proximity weighting

### Consequences of Missing Phase 2.5

**Phase 3 Impact:**
- ✅ Feature analysis proceeds (works on D-PLACE–dominant data)
- ❌ Cross-source comparison finds 0 overlaps (cannot validate D-PLACE against DRH)
- ❌ Ethnographic validation uses mock profiles, not real linkage
- ❌ Cannot compute conflict registry with actual cross-source disagreements

**Phase 4 Impact:**
- ⚠️ Cannot test hypothesis: "Do D-PLACE clusters match DRH traditions?"
- ⚠️ Lost opportunity for independent validation

---

## Phase 2.5 Objectives

### Objective 1: Geographic+Temporal Proximity Matching

Create automatic linkage between D-PLACE and DRH records based on:

**1. Geographic Distance**
- Haversine distance between D-PLACE society centroid and DRH tradition coordinate
- Threshold: ≤500 km (adjustable, documented)
- Weight by inverse distance (closer = higher confidence)

**2. Temporal Overlap**
- D-PLACE time_start/time_end vs DRH tradition time ranges
- Check if periods overlap (accounting for uncertainty)
- Classify as: SAME_ERA, ADJACENT_ERA, DISTANT_ERA

**3. Combined Confidence Score**
```
confidence = (1 - normalized_distance) × temporal_overlap_weight
  where:
    normalized_distance = actual_distance / max_distance (500 km)
    temporal_overlap_weight = {
        1.0: SAME_ERA (periods overlap directly)
        0.5: ADJACENT_ERA (periods within ±200 years)
        0.2: DISTANT_ERA (periods >200 years apart)
    }
```

### Objective 2: Manual Expert Mapping

For borderline or ambiguous cases, provide interface for manual linkage:

**Example Cases Needing Expert Review:**
- DRH: "Aboriginal Australian Spirituality" vs D-PLACE: Okinawans (537 km away—borderline distance)
- DRH: "Sufi Islam" vs D-PLACE: Iranians, Bakhtiari, Kurds (multiple valid options)
- DRH: "Tibetan Buddhism" vs D-PLACE: Central_Tibetans, Lepcha, Sherpa (tradition spans multiple ethnic groups)

### Objective 3: Output Tables

**3a. Primary Linkage Table: `data/reference/dplace_drh_linkage.csv`**
```
drh_id,drh_tradition,drh_lat,drh_lon,d_place_culture_id,d_place_culture_name,distance_km,temporal_overlap,confidence_score,linkage_method,notes
DRH_001,Siberian Shamanism,60.00,100.00,EVENK_001,Evenk,905,SAME_ERA,0.78,geographic_proximity,"Tungusic shamanic people; 905 km from DRH coordinate"
DRH_001,Siberian Shamanism,60.00,100.00,SELKUP_001,Selkup,575,SAME_ERA,0.88,geographic_proximity,"Shamanic hunter-gatherer; closest match 575 km"
DRH_001,Siberian Shamanism,60.00,100.00,KET_001,Ket,582,SAME_ERA,0.87,geographic_proximity,"Small Siberian shamanic group; 582 km away"
DRH_004,Korean Shamanism,37.00,127.00,KOREAN_001,Koreans,84,SAME_ERA,0.97,geographic_proximity,"Geographic overlap 84 km; excellent match"
DRH_004,Korean Shamanism,37.00,127.00,KOREAN_002,Koreans (modern period),126,SAME_ERA,0.95,geographic_proximity,"Same culture, later time period; 126 km"
...
```

**3b. Confidence Summary: `data/reference/linkage_confidence.csv`**
```
drh_id,drh_tradition,num_d_place_matches,confidence_distribution,recommendation,needs_expert_review
DRH_001,Siberian Shamanism,3,"HIGH(3)",Accept automatic linkage,FALSE
DRH_002,Sufi Islam,3,"MEDIUM(2),LOW(1)",Review manually; ambiguous,TRUE
DRH_003,Tibetan Buddhism,2,"HIGH(2)",Accept automatic linkage,FALSE
DRH_004,Korean Shamanism,2,"VERY_HIGH(2)",Accept automatic linkage,FALSE
DRH_005,Aboriginal Australian Spirituality,0,"NONE","Geographic distance >500km; requires expert judgment",TRUE
```

**3c. Coverage Analysis: `data/reference/linkage_coverage.csv`**
```
metric,value,notes
drh_traditions_total,5,
drh_traditions_linked,4,"DRH_005 requires expert mapping; Aboriginal traditions outside D-PLACE geographic range"
d_place_cultures_involved,8,"Subset of 1383 D-PLACE cultures with DRH tradition links"
average_matches_per_tradition,2.0,"E.g., Siberian Shamanism links to 3 D-PLACE cultures; Korean Shamanism to 2"
geographic_range_d_place,500km,"Threshold distance between D-PLACE centroid and DRH coordinate"
temporal_coverage,1000BCE-2000CE,"DRH time ranges span Prehistoric to Modern; D-PLACE mostly 'ethnographic present' (-1750 to -1950)"
conflicts_recoverable,4/5 traditions,"Can recover conflicts between linked D-PLACE and DRH records in Phase 3"
```

---

## Implementation Tasks

### Task 1: Haversine Distance Function (`src/harmonise/linkage.py`)

```python
def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Compute great-circle distance between two (lat, lon) points.
    
    Args:
        lat1, lon1: D-PLACE culture coordinates
        lat2, lon2: DRH tradition coordinates
        
    Returns:
        Distance in kilometers
    """
    # Standard Haversine formula; return km
```

### Task 2: Geographic Proximity Matching (`src/harmonise/linkage.py`)

```python
def find_geographic_matches(
    df_dplace: pd.DataFrame,
    df_drh: pd.DataFrame,
    max_distance_km: float = 500.0,
) -> pd.DataFrame:
    """
    Find D-PLACE cultures within max_distance of each DRH tradition.
    
    For each DRH record:
      1. Extract (lat, lon) coordinate
      2. Compute distance to all D-PLACE cultures
      3. Filter to distance ≤ max_distance_km
      4. Sort by distance (closer = higher confidence)
    
    Returns:
        DataFrame:
        drh_id | d_place_culture_id | distance_km | confidence (1-distance/max_distance)
    """
```

### Task 3: Temporal Overlap Classification (`src/harmonise/linkage.py`)

```python
def classify_temporal_overlap(
    d_place_time_start: int,
    d_place_time_end: int,
    drh_time_start: int,
    drh_time_end: int,
) -> Tuple[str, float]:
    """
    Classify temporal relationship and return overlap weight.
    
    Returns:
        (classification, weight):
        - ("SAME_ERA", 1.0): Periods directly overlap
        - ("ADJACENT_ERA", 0.5): Start/end within ±200 years
        - ("DISTANT_ERA", 0.2): Periods >200 years apart
        - ("NO_OVERLAP", 0.0): Disjoint periods (rare for shamanism)
    """
```

### Task 4: Combined Confidence Scoring (`src/harmonise/linkage.py`)

```python
def compute_confidence_score(
    distance_km: float,
    temporal_classification: str,
    max_distance_km: float = 500.0,
) -> float:
    """
    Combine geographic and temporal signals into single confidence score (0-1).
    
    Confidence = (1 - distance/max_distance) × temporal_weight
    
    Returns:
        Score in [0, 1], where:
        - 0.9+: Excellent match (accept)
        - 0.7-0.9: Good match (accept)
        - 0.5-0.7: Possible match (review)
        - <0.5: Unlikely match (reject or expert review)
    """
```

### Task 5: Linkage Resolution Strategy (`src/harmonise/linkage.py`)

```python
def resolve_linkages(
    matches_df: pd.DataFrame,
    confidence_threshold: float = 0.5,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Resolve all matches into three tables:
    
    Returns:
      1. linkage_table: Clean (drh_id, d_place_culture_id, confidence) pairs
      2. confidence_summary: Per-DRH record, distribution of match qualities
      3. needs_expert_review: Ambiguous records requiring manual adjudication
    """
```

### Task 6: Manual Expert Mapping Interface (Optional for Phase 2.5)

Support for expert input:

**File: `data/reference/linkage_manual_overrides.csv`**
```
drh_id,d_place_culture_id,action,expert_justification
DRH_005,ABORIGINAL_001,LINK,"Aboriginal Australian traditions; closest D-PLACE cultures are 500+ km, but linguistic/cultural affinity documented"
DRH_002,SUFI_002,EXCLUDE,"Sufi Islam only applied in Middle East; exclude Papua New Guinea candidate"
```

## Deliverables

### Files to Create

1. **`src/harmonise/linkage.py`** (300+ lines)
   - `haversine_distance()`
   - `find_geographic_matches()`
   - `classify_temporal_overlap()`
   - `compute_confidence_score()`
   - `resolve_linkages()`
   - `create_linkage_tables()`

2. **`tests/test_linkage.py`** (200+ lines)
   - Test distance calculations (e.g., known city pairs)
   - Test temporal classification (overlap, adjacent, distant)
   - Test confidence scoring (edge cases)
   - Integration test: Full linkage pipeline

3. **`data/reference/dplace_drh_linkage.csv`** (AUTO-GENERATED)
   - Primary linkage output with confidence scores

4. **`data/reference/linkage_coverage.csv`** (AUTO-GENERATED)
   - Summary statistics on linkage success

5. **`data/reference/linkage_confidence.csv`** (AUTO-GENERATED)
   - Per-DRH record confidence distribution

### Files to Update

1. **`contexts/PROJECT_CONTEXT.md`**
   - Add Phase 2.5 to phase sequence
   - Reference new linkage module

2. **`IMPLEMENTATION_SUMMARY.md`** (if exists)
   - Add Phase 2.5 to completion checklist

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Geographic Threshold** | 500 km | Balances specificity; captures regional shamanic variation without excessive false positives |
| **Temporal Weighting** | 1.0/0.5/0.2 for SAME/ADJACENT/DISTANT | SAME_ERA strongly preferred (high confidence); adjacent acceptable; distant questionable |
| **Confidence Formula** | `(1 - dist/max_dist) × temporal_wt` | Multiplicative: both factors must be strong for high confidence |
| **Manual Overrides** | Supported via CSV | Expert judgment can override automatic scoring for edge cases |
| **One-to-Many Mapping** | Allowed (1 DRH → 3+ D-PLACE) | Necessary because traditions are trans-cultural; multiple societies share same tradition |

---

## Expected Outcomes

### Success Metrics

- ✅ 4/5 DRH traditions linked to 1+ D-PLACE cultures (100% coverage for confident candidates)
- ✅ Average confidence score ≥ 0.80 for accepted linkages
- ✅ 0 false positives (geographic distance ≤500 km for all accepted matches)
- ✅ Temporal classification accurate (via manual spot-check)

### Phase 3 Impact (After Phase 2.5)

- **Phase 3 notebook 03** (`cross_source_analysis.py`) will:
  1. Load linkage table
  2. Join D-PLACE records to DRH records via linkage ID
  3. Generate non-empty conflict registry with actual disagreements
  4. Quantify cross-source agreement strength

- **Ethnographic validation** will link to real DRH traditions (not mock profiles)

### Phase 4 Integration

Phase 4 clustering can now:
- Compare D-PLACE clusters against DRH tradition profiles
- Test if clusters recover DRH taxonomies
- Evaluate universalism vs. diffusion hypotheses with independent data

---

## Timeline & Dependencies

**Sequence:**
1. Create `src/harmonise/linkage.py` (1h)
2. Create `tests/test_linkage.py` (1h)
3. Run linkage generation script to create CSVs (15 min)
4. Update Phase 3 `comparison.py` to use linkage table (30 min)
5. Re-run Phase 3 notebook 03 with real conflicts (15 min)

**Dependencies:**
- Requires: Phase 2 harmonised parquets ✅
- Used by: Phase 3 analysis modules (after update)

---

## Notes

- Phase 2.5 is **optional but strongly recommended** for cross-source validation
- Can be deferred to Phase 4 if timeline is critical (Phase 4 can use output directly)
- Geographic threshold (500 km) is **adjustable**; if too restrictive, increase to 750 km
- No new data sources required; uses Phase 2 outputs exclusively

---

**Context Version:** 1.0  
**Date Created:** 15 avril 2026  
**Status:** Ready for implementation
