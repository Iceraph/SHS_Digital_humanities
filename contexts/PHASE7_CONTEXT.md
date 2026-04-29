# Phase 7: Interactive Visualization & Prototype Development

**Status:** Planning  
**Date Created:** 21 April 2026  
**Phase Duration:** 2-3 weeks  
**Target Completion:** Early May 2026

---

## 1. Executive Summary

Phase 7 transforms Phase 6 statistical outputs into interactive web-based visualizations for manuscript publication and community exploration. This phase develops three key visualization components:

1. **3D Geographic Globe** - Interactive spatial clustering map with rotate/zoom/pan
2. **Feature Search & Filtering Interface** - Dynamic attribute exploration with phylogenetic filtering
3. **Phylogenetic Tree Visualization** - Language family tree with cluster annotations

### Phase Transition
- **Input (from Phase 6):** Statistical analysis outputs (CSV results, PNG figures)
- **Output (Phase 7):** Interactive HTML/web prototype with embedded D3.js and Three.js visualizations
- **Downstream (Phase 8):** Publication-ready figures + supplementary interactive materials

---

## 2. Phase 6 Completion Summary

### ✅ Deliverables Completed

**Analysis Results:**
- `morans_i_per_feature.csv` - Spatial autocorrelation for 19 features (1 significant)
- `distance_decay_analysis.csv` - Feature similarity across 4 distance bins
- `phylogenetic_signal.csv` - Pagel's λ and Blomberg's K for 19 features
- `mantel_results.csv` - Geography-Features correlation (r=0.040, p=0.186, n.s.)

**Publication Figures:**
- `01_distance_decay_curve.png` - Distance decay with error bars (300 dpi)
- `02_phylogenetic_signal.png` - Pagel's λ and K distributions (300 dpi)

**Synthesis Results:**
- `hypothesis_synthesis.json` - Final conclusion: **Neurobiological Universalism Supported** (Score 4.0/5)

**Data Infrastructure:**
- Validated 11/11 data integrity checks
- Geographic distance matrices (373-19,799 km range)
- Phylogenetic distance matrices (5 language families)
- Feature distance/similarity matrices (Jaccard distances)

### Key Findings
1. **Spatial Clustering:** Only 5.3% of features show significant geographic clustering → supports universalism
2. **Phylogenetic Signal:** Mean λ=0.474, only 1/19 strong signal → weak language family effects
3. **Geographic-Feature Correlation:** r=0.040 (n.s.) → geography independent of shamanic features
4. **Interpretation:** Features reflect neurobiological universality, not cultural diffusion

### Data Availability for Phase 7
- **Synthetic test data:** 50 cultures (used for validation)
- **Production data:** 1,257 cultures (loaded in Phase 4, ready for Phase 7)
- **Coordinates:** Geographic metadata for 228/240 DRH + all D-PLACE + all Seshat entries. 12 DRH entries have no coordinates by design (globally distributed traditions — see Section 4.4).
- **Cluster assignments:** 8 clusters from Phase 4 analysis
- **Language families:** 5-7 language families (from D-PLACE/phylogenetic tree)
- **Feature attributes:** 19 shamanic binary features with metadata

---

## 3. Phase 7 Architecture

### 3.1 Technology Stack

**Frontend Framework:**
```
JavaScript/TypeScript + Webpack
├── D3.js 7.x (phylogenetic tree, data visualization)
├── Three.js (3D globe rendering)
├── Leaflet (geographic tile layers)
├── Bootstrap 5 (UI components, responsive grid)
└── Chart.js (supplementary statistical charts)
```

**Backend Services:**
```
Python (FastAPI or Flask) [Optional - only if real-time filtering needed]
├── Load preprocessed data (CSVs, distance matrices)
├── Serve via REST API if interactive filtering required
└── Cache distance/correlation matrices for fast queries
```

**Build & Deployment:**
```
├── Webpack (bundling + minification)
├── GitHub Pages (hosting static site)
├── Jupyter HTML export (alternative: embed in notebook)
└── Docker (optional: containerize for reproducibility)
```

### 3.2 Component Architecture

```
phase7_visualization/
├── index.html                          # Main entry point
├── css/
│   ├── style.css                       # Custom styling
│   └── bootstrap-overrides.css
├── js/
│   ├── main.js                         # Entry point, event coordination
│   ├── globe.js                        # Three.js 3D globe + cluster coloring
│   ├── phylotree.js                    # D3 phylogenetic tree rendering
│   ├── featurePanel.js                 # Feature search/filter UI
│   ├── dataLoader.js                   # Load CSVs, compute matrices
│   └── colorScheme.js                  # Cluster colors, legends
├── data/
│   ├── cultures_metadata.json          # {id, lat, lon, cluster, language_family, features[]}
│   ├── phylo_tree.json                 # Newick format tree structure
│   ├── distance_matrices.json          # {geo_dist, phylo_dist, feature_dist}
│   └── analysis_results.json           # {morans_i, mantel_results, phylo_signal}
└── lib/
    ├── d3.min.js
    ├── three.min.js
    └── leaflet.min.js
```

### 3.3 Data Flow

```
Phase 6 Outputs (CSVs)
    ↓
Python Script: Convert to JSON
    ├── cultures_metadata.json (cultures + coordinates + clusters)
    ├── distance_matrices.json (precompute distances for filtering)
    ├── phylo_tree.json (language family tree structure)
    └── analysis_results.json (Moran's I, Mantel test results)
    ↓
JavaScript Data Loader
    ├── Parse JSON → in-memory objects
    ├── Index by cluster, feature, language family
    └── Cache distance matrices
    ↓
Interactive Components
    ├── 3D Globe (rotate/zoom, hover info)
    ├── Feature Filter Panel (search, phylogenetic filter)
    └── Phylogenetic Tree (interactive legend)
```

---

## 4. Phase 7 Deliverables

### 4.1 Component 1: 3D Geographic Globe

**Purpose:** Visualize 1,257 cultures on interactive globe with cluster color-coding

**Features:**
- ✅ Render globe using Three.js with texture mapping
- ✅ Plot each culture as 3D point (lat/lon projected to sphere)
- ✅ Color-code by cluster (8 distinct colors)
- ✅ Interactive controls: rotate, zoom, pan
- ✅ Hover tooltip: culture name, cluster, language family, feature count
- ✅ Click to highlight culture + show details panel
- ✅ Feature-based filtering: highlight only cultures with specific feature
- ✅ Distance decay visualization: overlay distance bins as concentric circles

**Technical Implementation:**
```javascript
// Pseudocode
const globe = new ThreeGlobe()
  .globeImageUrl('img/earth-texture.jpg')
  .pointsData(culturesData)
  .pointColor(d => clusterColorMap[d.cluster])
  .pointSize(8)
  .pointAltitude(0)
  .onPointHover(showTooltip)
  .onPointClick(showDetailPanel)
```

**Success Criteria:**
- [ ] All 1,257 cultures rendered and visible
- [ ] Smooth rotation/zoom with < 60ms latency
- [ ] Cluster colors consistent with Phase 6 figures
- [ ] Hover information (culture name, cluster, features) displayed
- [ ] Feature filter highlights subset of cultures
- [ ] Globally distributed traditions listed in sidebar (see Section 4.4)

### 4.2 Component 2: Feature Search & Filter Interface

**Purpose:** Enable users to explore individual shamanic features and their spatial/phylogenetic patterns

**Features:**
- ✅ Dropdown/search for 19 shamanic features
- ✅ Show cultures where feature is present (1) vs absent (0)
- ✅ Display statistical summary: % present globally, by cluster, by language family
- ✅ Phylogenetic filter: highlight only cultures from selected language family
- ✅ Distance decay overlay: show correlation of feature with distance
- ✅ Moran's I indicator: badge showing significance level (p<0.05, p<0.01, n.s.)
- ✅ Feature metadata: description, presence rate, association with clusters
- ✅ Multi-select: compare 2-3 features simultaneously

**UI Layout:**
```
┌─────────────────────────────────────────────┐
│  Feature Search Panel                       │
├─────────────────────────────────────────────┤
│  [Search: ________]                         │
│  ☐ Feature_1 (45% of cultures)              │
│  ☐ Feature_2 (38% of cultures) ⭐ sig       │
│  ☐ Feature_3 (12% of cultures)              │
│  ...                                        │
│                                             │
│  [Advanced Filters]                         │
│  Phylogenetic filter: [All ▼] LF_A LF_B   │
│  Cluster filter: [All ▼]                    │
│  Geographic range: 0-5000 km ▬▬▬▬▬         │
│                                             │
│  [View Statistics] [Export Data]            │
└─────────────────────────────────────────────┘
```

**Statistics Display:**
```
Feature: Ecstatic Trance
├── Global presence: 45% (565/1257)
├── By cluster:
│   ├── Cluster 0: 82%
│   ├── Cluster 1: 23%
│   └── Cluster 2: 61%
├── By language family:
│   ├── LF_A: 72%
│   ├── LF_B: 31%
│   └── LF_C: 18%
├── Geographic clustering (Moran's I): I=0.200, p<0.001 ⭐
└── Phylogenetic signal (λ): 0.790 (STRONG)
```

**Technical Implementation:**
```javascript
// Feature panel state management
featurePanel.onSelect(featureName, () => {
  globe.highlightCultures(culturesWithFeature)
  statsPanel.update(featureStats)
  phyloTree.highlightFamilies(familiesWithFeature)
})

featurePanel.onPhyloFilter(familyName, () => {
  globe.filterByFamily(familyName)
  statsPanel.updateSubset()
})
```

**Success Criteria:**
- [ ] All 19 features searchable in < 100ms
- [ ] Statistics calculated dynamically for filters
- [ ] Phylogenetic filtering works correctly
- [ ] Globe and tree update synchronously
- [ ] Export CSV of filtered data working

### 4.4 Globally Distributed Traditions (no-coordinate entries)

**Background:** 12 DRH traditions have no geographic coordinates because they are inherently non-localizable — they are global diffusion networks or organisations with no meaningful single point (Gardnerian Wicca, Wesleyanism, Digital Shinto Communities, etc.). Assigning a fake centroid would introduce spurious signal into Moran's I and Mantel tests, so `lat/lon = NaN` is the correct encoding.

**Consequences by use:**
- **Clustering:** No effect — k-means uses features only, not coordinates. All 12 will receive cluster assignments.
- **Spatial analysis:** Correctly excluded from Moran's I and Mantel test (requires coordinates).
- **Globe:** These 12 entries do not appear as dots — they must be surfaced elsewhere to avoid silently misleading the reader.

**Required UI treatment — Globally Distributed Traditions sidebar:**
- A collapsible panel (or footer note) on the globe view listing these 12 entries by name, with their cluster assignment and feature count
- Label: *"12 traditions are globally distributed and cannot be plotted geographically. They are included in the clustering analysis."*
- Each entry links to its detail card (same as clicking a globe dot)
- The count (12) should appear in the data coverage legend so readers know the globe does not show 100% of the DRH data

**Implementation note:** Filter `cultures_metadata.json` entries where `lat === null` and `source === "drh"` to populate this list dynamically.

---

### 4.3 Component 3: Phylogenetic Tree Visualization

**Purpose:** Display language family relationships with cluster annotations and shamanic feature patterns

**Features:**
- ✅ Render phylogenetic tree using D3 tree layout (Newick format)
- ✅ Color-code tree branches by dominant cluster
- ✅ Label leaves with language family names
- ✅ Annotate branches with feature patterns (icons or badges)
- ✅ Interactive tooltips: cluster composition, mean feature presence, geographic range
- ✅ Click on node to filter globe to that language family
- ✅ Highlight path from root to selected family

**Tree Structure:**
```
D-PLACE Phylogenetic Tree (simplified example):
├── LF_A (50 cultures)
│   ├── LF_A.1 (25 cultures) [Cluster 2, 3] 🎭 ⚡
│   └── LF_A.2 (25 cultures) [Cluster 1, 4] 🎭
├── LF_B (200 cultures)
│   ├── LF_B.1 (100) [Cluster 0] ⚡ 🔮
│   └── LF_B.2 (100) [Cluster 5, 6]
└── LF_C (1007 cultures)
    ├── LF_C.1 (500) [Cluster 7] 🎭
    └── LF_C.2 (507) [Cluster 0, 1, 2]
```

**Technical Implementation:**
```javascript
// D3 phylogenetic tree
const tree = d3.tree()
  .size([width, height])

const root = d3.hierarchy(phyloData)
const links = tree(root).links()
const nodes = root.descendants()

svg.selectAll('.link')
  .data(links)
  .enter()
  .append('path')
  .attr('d', d3.linkVertical())
  .attr('stroke', d => clusterColorMap[d.target.data.dominantCluster])
```

**Success Criteria:**
- [ ] Tree renders without overlapping labels
- [ ] All language families correctly positioned
- [ ] Click-to-filter works synchronously with globe
- [ ] Feature icons visible on branches
- [ ] Zoom/pan functionality for large trees

---

## 5. Implementation Plan

### Sprint 1: Foundation & Data Preparation (Days 1-3)
- [ ] Convert Phase 6 CSV outputs to JSON format
- [ ] Create cultures_metadata.json with all culture attributes
- [ ] Compute and cache distance matrices
- [ ] Extract phylogenetic tree structure from D-PLACE
- [ ] Set up project structure and build tools (Webpack)
- [ ] Initialize HTML skeleton and Bootstrap grid

### Sprint 2: 3D Globe Implementation (Days 4-7)
- [ ] Integrate Three.js and configure globe rendering
- [ ] Project lat/lon coordinates to 3D sphere
- [ ] Implement cluster color-coding
- [ ] Add interactive controls (rotate, zoom, pan)
- [ ] Implement hover tooltips and click handlers
- [ ] Performance optimization (frustum culling, LOD)

### Sprint 3: Feature Panel & Filtering (Days 8-11)
- [ ] Build feature search dropdown with autocomplete
- [ ] Implement statistics calculation engine
- [ ] Add phylogenetic family filter
- [ ] Create statistics display layout
- [ ] Synchronize globe highlighting with filters
- [ ] Add multi-select feature comparison

### Sprint 4: Phylogenetic Tree & Integration (Days 12-15)
- [ ] Parse phylogenetic tree (Newick format)
- [ ] Implement D3 tree visualization
- [ ] Add cluster annotations and feature badges
- [ ] Implement click-to-filter interaction
- [ ] Synchronize tree with globe and feature panel
- [ ] Add zoom/pan controls for tree

### Sprint 5: Polish & Testing (Days 16-18)
- [ ] Cross-browser testing (Chrome, Firefox, Safari)
- [ ] Mobile responsiveness testing
- [ ] Performance profiling and optimization
- [ ] Accessibility audit (WCAG 2.1 AA)
- [ ] Documentation and README
- [ ] Package for deployment
- [ ] Implement Globally Distributed Traditions sidebar (Section 4.4) — list 12 no-coordinate DRH entries with cluster assignments and link to detail cards

---

## 6. Technical Dependencies

### From Earlier Phases
```
Phase 4: Cluster assignments (1,257 × 8)
         Geographic coordinates (1,257 × 2)
         Feature matrix (1,257 × 19)

Phase 3: D-PLACE linkage data
         Language family mapping
         Geographic validation

Phase 6: Statistical outputs (CSVs)
         Figure templates (styling, colors)
         Analysis conclusions

External: D-PLACE phylogenetic tree (JSON/Newick)
          SESHAT language family data
          Geographic tile data (mapbox, OSM)
```

### JavaScript Libraries
```json
{
  "dependencies": {
    "d3": "^7.0.0",
    "three": "^r150",
    "leaflet": "^1.9.0",
    "bootstrap": "^5.3.0",
    "chart.js": "^4.0.0",
    "papaparse": "^5.4.0"
  },
  "devDependencies": {
    "webpack": "^5.0.0",
    "webpack-cli": "^5.0.0",
    "babel-loader": "^9.0.0"
  }
}
```

---

## 7. Success Criteria & Validation

### Code Quality
- [ ] All interactive features respond in < 200ms
- [ ] No JavaScript console errors
- [ ] Code documented with JSDoc comments
- [ ] >80% browser support (Chrome, Firefox, Safari, Edge)

### Functionality
- [ ] All 1,257 cultures render on globe
- [ ] Feature search returns results in < 100ms
- [ ] Filters update visualizations synchronously
- [ ] Tree rendering supports 5-10 language families
- [ ] Export/download functionality working

### User Experience
- [ ] Responsive on desktop, tablet, mobile
- [ ] Clear legends and color schemes
- [ ] Tooltips provide useful information
- [ ] No visual artifacts or lag
- [ ] Accessibility: keyboard navigation, screen reader support

### Publication Quality
- [ ] High-resolution figure exports (PNG, SVG, PDF)
- [ ] Consistent styling with Phase 6 figures
- [ ] Color-blind friendly palettes
- [ ] Clear captions and annotations

---

## 8. Deliverables & Outputs

### HTML Outputs
- `index.html` - Main interactive visualization page
- `styles.css` - Custom styling
- `bundle.js` - Webpack-compiled JavaScript

### Documentation
- `README_PHASE7.md` - Setup and usage instructions
- `API_DOCUMENTATION.md` - JSON data formats
- `USER_GUIDE.md` - Interactive feature guide

### Data Files
- `data/cultures_metadata.json` - All culture attributes
- `data/phylo_tree.json` - Phylogenetic structure
- `data/distance_matrices.json` - Precomputed matrices
- `data/analysis_results.json` - Phase 6 statistics

### Manuscript Assets
- `figures/` - High-resolution exports of visualizations
- `supplementary_materials/` - Interactive HTML for SI

---

## 9. Timeline & Milestones

| Milestone | Target Date | Completion |
|-----------|-------------|-----------|
| Data preparation complete | April 22 | ⬜ |
| Globe prototype functional | April 24 | ⬜ |
| Feature panel UI complete | April 27 | ⬜ |
| Phylogenetic tree rendering | April 29 | ⬜ |
| Full integration & testing | May 2 | ⬜ |
| Publication-ready release | May 5 | ⬜ |

---

## 10. Risk Assessment & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Three.js performance on large datasets | High | Use WebGL shaders, instancing, LOD |
| D3 tree layout complexity | Medium | Pre-compute layout offline, cache |
| Mobile performance degradation | Medium | Separate mobile build, reduce LOD |
| Browser compatibility issues | Medium | Use polyfills, test early on all browsers |
| Phylogenetic data format inconsistency | Low | Validate Newick parsing, error handling |

---

## 11. Related Documentation

- [PHASE6_CONTEXT.md](PHASE6_CONTEXT.md) - Phase 6 completion details
- [PHASE4_CONTEXT.md](PHASE4_CONTEXT.md) - Cluster assignments and geographic data
- [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) - Overall project architecture

---

## 12. Next Steps

1. **Review & Approval:** Validate Phase 7 context against project requirements
2. **Data Preparation:** Convert Phase 6 CSVs to JSON format
3. **Project Setup:** Initialize Webpack and npm packages
4. **Development:** Begin Sprint 1 (Foundation & Data)

---

**Phase 7 Context Status:** ✅ READY FOR IMPLEMENTATION

