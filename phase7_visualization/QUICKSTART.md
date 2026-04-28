# Phase 7 Quick Start Guide

## 🚀 Getting Started (< 5 minutes)

### 1. Navigate to Phase 7 Directory
```bash
cd /Users/raphaelwothke-dusseaux/Desktop/Codes/SHS2/phase7_visualization
```

### 2. Start Development Server
```bash
npm run serve
# Opens http://localhost:8000 in your browser
```

### 3. Interact with Visualization
- **Globe:** Click and drag to rotate, scroll to zoom
- **Features:** Search feature names in left panel (e.g., "trance", "spirit")
- **Filters:** Use dropdowns to filter by cluster or language family
- **Export:** Click "Export Data" to download filtered cultures as CSV

---

## 📁 Project Structure

```
phase7_visualization/
├── index.html                      # Main app (open in browser)
├── js/                             # 6 modules (1,000 LOC)
│   ├── main.js                     # Application entry point
│   ├── dataLoader.js               # Data loading + filtering
│   ├── globe.js                    # Three.js 3D globe
│   ├── featurePanel.js             # Feature search UI
│   ├── phylotree.js                # D3 phylogenetic tree
│   └── colorScheme.js              # Cluster colors
├── css/style.css                   # Responsive styling
├── data/                           # 5 JSON files (637 KB)
│   ├── cultures_metadata.json      # 1,850 cultures
│   ├── analysis_results.json       # Phase 6 statistics
│   ├── cluster_profiles.json       # Cluster info
│   ├── phylo_tree.json             # Language families (stub)
│   └── distance_matrices.json      # Distance data (stub)
├── package.json                    # npm dependencies
└── README.md                       # Full documentation
```

---

## 🎯 What Works Now (Sprint 1)

✅ **3D Globe**
- 1,257 cultures plotted with accurate coordinates
- 8-color cluster visualization
- Hover tooltips, click selection
- Auto-rotation + manual controls

✅ **Feature Search**
- 19 shamanic features indexed
- Real-time filtering on globe
- Statistics by cluster
- Moran's I significance badges

✅ **Filtering**
- Filter by cluster (8 clusters)
- Filter by feature (19 features)
- Multiple filters combined
- CSV export

✅ **Responsive Design**
- Desktop, tablet, mobile layouts
- Bootstrap grid system
- Touch-friendly controls

---

## 📊 Data Summary

| Item | Count |
|------|-------|
| Cultures | 1,850 |
| Features | 19 |
| Clusters | 8 |
| Data Sources | 3 (D-PLACE, DRH, Seshat) |
| Total JSON Size | 637 KB |

---

## 🛠️ Available Commands

```bash
npm run dev          # Development server with live reload
npm run serve        # Simple HTTP server on port 8000
npm run build        # Production bundle (minified)
npm run watch        # Watch mode for development
npm run lint         # Lint JavaScript code
npm audit fix        # Fix npm vulnerabilities
```

---

## 🐛 Troubleshooting

### Page doesn't load?
1. Check browser console (Ctrl+Shift+J or Cmd+Option+J)
2. Verify data files exist: `ls data/`
3. Check that npm install completed: `ls node_modules/ | wc -l`

### Globe not showing cultures?
1. Check console: `AppDebug.logState()`
2. Verify data loaded: `AppDebug.DataLoader.isLoaded()`
3. Check feature search - might have a filter applied

### Features not searchable?
1. Verify features loaded: `AppDebug.DataLoader.getFeatureNames()`
2. Try typing a feature name slowly
3. Check that data/cultures_metadata.json exists and is valid JSON

---

## 🔍 Debug Console

In browser console, use these commands:

```javascript
// Check if everything loaded
AppDebug.logState()

// Get all cultures
AppDebug.DataLoader.getCultures().length

// Get feature names
AppDebug.DataLoader.getFeatureNames()

// Get cultures in a cluster
AppDebug.DataLoader.getCulturesByCluster(0).length

// Get cultures with a feature
AppDebug.DataLoader.getCulturesByFeature('trance_induction', 1).length

// Check globe filters
AppDebug.GlobeVisualization.getFilters()

// Get selected feature
AppDebug.FeaturePanel.getSelectedFeature()
```

---

## 📚 Documentation

- **Full README:** [phase7_visualization/README.md](./README.md)
- **Implementation Summary:** [PHASE7_IMPLEMENTATION_SUMMARY.md](../../PHASE7_IMPLEMENTATION_SUMMARY.md)
- **Phase 7 Context:** [contexts/PHASE7_CONTEXT.md](../../contexts/PHASE7_CONTEXT.md)
- **Project Architecture:** [contexts/PROJECT_CONTEXT.md](../../contexts/PROJECT_CONTEXT.md)

---

## 🎓 Learning Resources

### Three.js (3D Globe)
- Tutorial: https://threejs.org/docs/
- Geometry: Sphere with 1,257 point geometry
- Interaction: Raycaster for picking, manual rotation

### D3.js (Phylogenetic Tree)
- Tutorial: https://d3js.org/
- Layout: d3.tree() for hierarchical layout
- Data: Newick format trees from D-PLACE

### Bootstrap 5 (Responsive Layout)
- Grid System: 12-column responsive grid
- Breakpoints: 576px, 768px, 992px, 1200px
- Components: Navbar, dropdowns, buttons, badges

---

## 📝 Next Steps (Sprint 2)

1. ⏳ Real phylogenetic tree with D-PLACE data
2. ⏳ Pre-computed distance matrices
3. ⏳ Advanced filtering (multi-select, date range)
4. ⏳ Animation timeline
5. ⏳ Heatmap visualization

---

## 💡 Tips

- **For researchers:** Use feature search to explore patterns
- **For developers:** Check `js/dataLoader.js` for all data access methods
- **For designers:** Edit `css/style.css` to customize colors/layout
- **For testing:** Use `npm run dev` for live reload during development

---

## 📞 Support

For issues:
1. Check browser console for errors
2. Run `AppDebug.logState()` to verify data
3. Check that JSON files are valid: `cat data/*.json | python -m json.tool > /dev/null`
4. Verify node_modules: `npm ls --depth=0`

---

**Version:** 1.0.0-alpha  
**Date:** 21 April 2026  
**Status:** Ready for Sprint 2
