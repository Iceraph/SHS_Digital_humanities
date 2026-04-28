# Phase 7 Sprint 2 - Implementation Plan
**Start Date**: 21 April 2026  
**Duration**: 2-3 development days  
**Focus**: Feature enhancements and data export capabilities

## Sprint 2 Overview
Build on Sprint 1 foundation by adding data export, statistics visualization, and enhanced filtering. These features will make the tool useful for research and analysis workflows.

---

## Priority 1: Quick Wins (Day 1)
### 1.1 CSV Export Functionality ⭐ HIGH PRIORITY
**Effort**: 2-3 hours | **Impact**: 🔴 Critical  
**User Story**: "As a researcher, I want to export filtered cultures to CSV for further analysis"

**Tasks**:
- [ ] Implement CSV generation from filtered cultures
- [ ] Add export button functionality in feature panel
- [ ] Include: ID, Name, Cluster, Lat, Lon, Source, Features
- [ ] Test with various filter combinations

**Files to modify**:
- `js/featurePanel.js` - Add export handler
- `js/main.js` - Register export event

**Acceptance Criteria**:
- ✅ Export button downloads CSV file
- ✅ CSV contains all selected/filtered cultures
- ✅ File named with timestamp (cultures_YYYYMMDD_HHMMSS.csv)
- ✅ Works with all filter combinations

---

### 1.2 Interactive Legend (Cluster Highlighting) ⭐ HIGH PRIORITY
**Effort**: 1-2 hours | **Impact**: 🟡 High  
**User Story**: "As a researcher, I want to click cluster colors to isolate viewing"

**Tasks**:
- [ ] Make legend clickable in phylo panel
- [ ] Highlight selected cluster on globe
- [ ] Dim other clusters (70% opacity)
- [ ] Click again to reset

**Files to modify**:
- `js/phylotree.js` - Add legend click handlers
- `js/globe.js` - Add filter visual feedback

**Acceptance Criteria**:
- ✅ Click legend → cluster highlights
- ✅ Other clusters dim to 30% opacity
- ✅ Click again → reset to all visible

---

## Priority 2: Medium Priority (Day 2)
### 2.1 Statistics Panel Enhancement ⭐ MEDIUM PRIORITY
**Effort**: 3-4 hours | **Impact**: 🟡 High  
**User Story**: "As a researcher, I want to see statistics about selected features"

**Tasks**:
- [ ] Display feature presence statistics
- [ ] Show by-cluster breakdown (8 rows)
- [ ] Calculate Moran's I spatial autocorrelation
- [ ] Show significance badges (p<0.05, p<0.01)
- [ ] Update panel when feature selected

**Data to compute**:
```javascript
{
  "feature": "CARNEIRO4_182",
  "totalPresence": 22,
  "percentGlobal": 1.2,
  "byCluster": {
    "0": {"count": 15, "percent": 68.2},
    "1": {"count": 2, "percent": 9.1},
    ...
  },
  "moransI": {
    "value": 0.342,
    "pValue": 0.0234,
    "significant": true
  }
}
```

**Files to create**:
- `js/statistics.js` - New stats calculation module

**Files to modify**:
- `js/featurePanel.js` - Display stats panel
- `js/main.js` - Wire up stats

---

### 2.2 Language Family Population ⭐ MEDIUM PRIORITY
**Effort**: 2-3 hours | **Impact**: 🟡 Medium  
**User Story**: "Populate actual language family data from D-PLACE for phylogenetic analysis"

**Tasks**:
- [ ] Extract language family mapping from D-PLACE
- [ ] Create language_families.json reference
- [ ] Update cultures_metadata.json with families
- [ ] Export with new data
- [ ] Test phylo tree with real families

**Output**: New data file with language family assignments

---

## Priority 3: Nice-to-Have (Day 3)
### 3.1 Feature Search Enhancement
**Effort**: 1 hour | **Impact**: 🟢 Medium

**Tasks**:
- [ ] Live search filtering in feature list
- [ ] Highlight matching features
- [ ] Show match count

---

### 3.2 Culture Tooltip Enhancement
**Effort**: 1-2 hours | **Impact**: 🟢 Low

**Tasks**:
- [ ] Show features on hover
- [ ] Display cluster name
- [ ] Show source database

---

## Implementation Order

### Day 1 (Today)
1. ✅ CSV Export (Quick win - high ROI)
2. ✅ Interactive Legend (UX improvement)
3. ⏳ Baseline Statistics Display (without Moran's I initially)

### Day 2
1. ⏳ Moran's I Calculation (requires spatial analysis)
2. ⏳ Language Family Data Population
3. ⏳ Statistics Panel Complete

### Day 3
1. ⏳ Enhancements & Polish
2. ⏳ Testing & Bug Fixes
3. ⏳ Performance Optimization

---

## Technical Considerations

### CSV Export
- Use PapaParse (already installed) for formatting
- Trigger browser download
- Handle special characters in names
- Performance: Should be instant for <10k rows

### Statistics
- Pre-compute Moran's I during data load
- Cache results in DataLoader
- Update panel reactively on feature selection

### Language Families
- Option A: Extract from D-PLACE CSV
- Option B: Use Ethnologue mappings
- Option C: Manual curation for key families

---

## Testing Checklist

### CSV Export
- [ ] Export all cultures (1,850 rows)
- [ ] Export filtered by cluster
- [ ] Export filtered by feature
- [ ] File opens correctly in Excel/CSV editor
- [ ] Column headers present and correct
- [ ] No data truncation

### Interactive Legend
- [ ] Click cluster 0 → highlights
- [ ] Other clusters dim
- [ ] Click again → resets
- [ ] Works on all 8 clusters
- [ ] Visual feedback clear

### Statistics
- [ ] Displays on feature selection
- [ ] Numbers match data
- [ ] By-cluster breakdown accurate
- [ ] Updates on filter change
- [ ] No performance issues

---

## Success Metrics

| Feature | Target | Status |
|---------|--------|--------|
| CSV Export Working | 100% | 🔴 Pending |
| Interactive Legend | 8/8 clusters | 🔴 Pending |
| Statistics Accurate | 100% | 🔴 Pending |
| Performance (export <1s) | <1s | 🔴 Pending |
| User Testing Feedback | Positive | 🔴 Pending |

---

## Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Moran's I calculation slow | Medium | Medium | Pre-compute at load time |
| Language family data unavailable | Low | Low | Use placeholder "unknown" |
| CSV too large (memory) | Low | Low | Stream generation if needed |

---

## Definition of Done (Sprint 2)
- ✅ CSV export working and tested
- ✅ Interactive legend working
- ✅ Statistics panel displaying
- ✅ All code documented
- ✅ No console errors
- ✅ Responsive on all screen sizes
- ✅ Completion report written

---

## Notes
- Keep Sprint 1 stability - no breaking changes
- Maintain backward compatibility with existing data
- Focus on user-facing features
- Prepare foundation for Sprint 3 (3D globe, temporal analysis)

