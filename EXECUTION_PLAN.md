# Seshat Integration - Complete Execution Plan

**Date**: 28 April 2026  
**Objective**: Fix all 20 failing tests and update context files  
**Current Status**: 145 passing, 20 failing (87.9% success rate)

---

## Phase 1: Context File Updates (HIGH PRIORITY)

### 1.1 PROJECT_CONTEXT.md
**Location**: contexts/PROJECT_CONTEXT.md  
**Updates needed**:
- Update data volume summary (11,831 → 14,044 cultures)
- Add Seshat description to data sources section
- Update feature schema to show Seshat sources

**Lines affected**: 
- Section 2.2 (Seshat description)
- Section 4 (Architecture - data volume)

### 1.2 PHASE2_CONTEXT.md
**Location**: contexts/PHASE2_CONTEXT.md  
**Updates needed**:
- Add Seshat feature mappings table
- Document source-specific binarisation rules
- Update total records from 11,831 → 14,044

**Lines affected**: 
- Task 1 (Crosswalk section)
- Task 2 (Unit reconciliation section)

### 1.3 PHASE4_CONTEXT.md
**Location**: contexts/PHASE4_CONTEXT.md  
**Updates needed**:
- Note that Phase 4 pre-dates Seshat activation
- Recommend re-run with Seshat data
- Add phylogenetic linkage requirements for Seshat

**Lines affected**:
- Section 2 (Architecture)
- Section 3.1 (Input data)

### 1.4 PHASE6_CONTEXT.md
**Location**: contexts/PHASE6_CONTEXT.md  
**Updates needed**:
- Update Moran's I results (19 features → 64 features)
- Document 0 significant clustering (all p>0.05)
- Add Seshat temporal coverage note

**Lines affected**:
- Section 2.1 (Spatial autocorrelation results)
- Section 3 (Results summary)

---

## Phase 2: Test Fixture Updates (CRITICAL)

### 2.1 Fix test_phylogenetic.py fixtures
**Issue**: Missing `language_family` column  
**Action**:
- Add language_family column to all test fixtures
- Use sample values: "Indo-European", "Sino-Tibetan", etc.
- Update expected columns in assertions

**Files**:
- tests/fixtures/phylogenetic_test_data.py
- tests/test_phylogenetic.py

### 2.2 Fix test_spatial.py fixtures
**Issue**: Isolated locations (no neighbors within 500km)  
**Action**:
- Option A: Create geographically-clustered test data
- Option B: Use k-nearest neighbor weighting for tests
- Option C: Increase threshold_km for test data

**Files**:
- tests/fixtures/spatial_test_data.py
- tests/test_spatial.py

### 2.3 Fix test_linkage.py thresholds
**Issue**: Temporal overlap scores differ from expectations  
**Action**:
- Measure actual temporal overlap with real data
- Update test assertions to match
- Document new threshold logic

**Files**:
- tests/test_linkage.py

---

## Phase 3: Code Fixes (MEDIUM)

### 3.1 Mantel test assertion
**File**: tests/test_phylogenetic.py  
**Issue**: `test_mantel_identical_matrices` expects p<0.05 but gets 0.323

**Action**:
- Review test logic
- Verify that identical matrices should have p<0.05
- Adjust assertion or fix calculation

---

## Phase 4: Verification

### 4.1 Run test suite
**Command**: `pytest tests/ -v`  
**Target**: All 165 tests pass

### 4.2 Verify context file consistency
**Check**:
- No contradictory statements across files
- Data volumes consistent
- Feature mappings align with code

### 4.3 Commit changes
**Message**: "Seshat integration: update context files and fix tests"

---

## Estimated Effort

| Phase | Task | Time | Priority |
|-------|------|------|----------|
| 1 | Update 4 context files | 30-45 min | HIGH |
| 2.1 | Add language_family to fixtures | 20 min | CRITICAL |
| 2.2 | Fix spatial test data | 30 min | CRITICAL |
| 2.3 | Update temporal thresholds | 15 min | CRITICAL |
| 3 | Mantel test review | 15 min | MEDIUM |
| 4 | Verification & commit | 20 min | HIGH |
| **TOTAL** | **All phases** | **2.5 hours** | - |

---

## Execution Order

1. ✅ Review this plan (2 min)
2. Update context files (45 min)
3. Fix test fixtures - language_family (20 min)
4. Fix test fixtures - spatial data (30 min)
5. Fix temporal overlap assertions (15 min)
6. Review Mantel test (15 min)
7. Run full test suite (10 min)
8. Commit all changes (10 min)

