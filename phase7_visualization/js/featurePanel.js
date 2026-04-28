/**
 * featurePanel.js
 * Feature search, filtering, and statistics display
 */

const FeaturePanel = (() => {
    const featureList = document.getElementById('featureList');
    const featureSearch = document.getElementById('featureSearch');
    const statsPanel = document.getElementById('statsPanel');
    const phyloFilter = document.getElementById('phyloFilter');
    const clusterFilter = document.getElementById('clusterFilter');
    const viewStatsBtn = document.getElementById('viewStatsBtn');
    const exportBtn = document.getElementById('exportBtn');

    let allFeatures = [];
    let selectedFeature = null;

    /**
     * Initialize feature panel
     */
    const init = () => {
        // Load features
        allFeatures = DataLoader.getFeatureNames();

        // Populate language families
        populateLanguageFamilies();

        // Render feature list
        renderFeatureList(allFeatures);

        // Event listeners
        featureSearch.addEventListener('input', onFeatureSearch);
        phyloFilter.addEventListener('change', onPhyloFilterChange);
        clusterFilter.addEventListener('change', onClusterFilterChange);
        viewStatsBtn.addEventListener('click', onViewStats);
        exportBtn.addEventListener('click', onExport);

        console.log(`✓ Feature panel initialized with ${allFeatures.length} features`);
    };

    /**
     * Populate language family dropdown
     */
    const populateLanguageFamilies = () => {
        const families = DataLoader.getLanguageFamilies();
        
        families.forEach(family => {
            const option = document.createElement('option');
            option.value = family;
            option.textContent = family;
            phyloFilter.appendChild(option);
        });

        if (families.length === 0) {
            console.warn('No language families found in data');
        }
    };

    /**
     * Render feature list
     */
    const renderFeatureList = (features) => {
        featureList.innerHTML = '';

        if (features.length === 0) {
            featureList.innerHTML = '<p class="text-muted small">No features found</p>';
            return;
        }

        features.forEach(feature => {
            const stats = DataLoader.getFeatureStats(feature);
            const moransI = DataLoader.getModransI(feature);
            const isSignificant = moransI && moransI.p_value && moransI.p_value < 0.05;

            const div = document.createElement('div');
            div.className = 'feature-item';
            div.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div style="display: flex; align-items: center; flex: 1;">
                        <input type="checkbox" value="${feature}" class="feature-checkbox">
                        <span class="ms-2">${feature}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <small class="text-muted">${stats.percentage}%</small>
                        ${isSignificant ? '<span class="badge bg-warning feature-sig-badge">SIG</span>' : ''}
                    </div>
                </div>
            `;

            div.addEventListener('click', () => selectFeature(feature));
            featureList.appendChild(div);
        });
    };

    /**
     * Handle feature search
     */
    const onFeatureSearch = (event) => {
        const query = event.target.value.toLowerCase();
        const filtered = allFeatures.filter(f => f.toLowerCase().includes(query));
        renderFeatureList(filtered);
    };

    /**
     * Select a feature
     */
    const selectFeature = (featureName) => {
        selectedFeature = featureName;

        // Update UI
        document.querySelectorAll('.feature-item').forEach(item => {
            item.classList.remove('selected');
        });

        const selectedItem = Array.from(document.querySelectorAll('.feature-item')).find(item => {
            const checkbox = item.querySelector('.feature-checkbox');
            return checkbox && checkbox.value === featureName;
        });

        if (selectedItem) {
            selectedItem.classList.add('selected');
        }

        // Update stats panel
        updateStatsPanel(featureName);

        // Filter globe
        GlobeVisualization.filterByFeature(featureName);

        console.log(`Selected feature: ${featureName}`);
    };

    /**
     * Update statistics panel
     */
    const updateStatsPanel = (featureName) => {
        const stats = DataLoader.getFeatureStats(featureName);
        const moransI = DataLoader.getModransI(featureName);

        // Determine presence intensity for color coding
        const getIntensityColor = (pct) => {
            const num = parseFloat(pct);
            if (num >= 50) return '#d32f2f';  // High: red
            if (num >= 30) return '#f57c00';  // Medium-high: orange
            if (num >= 10) return '#fbc02d';  // Medium: yellow
            if (num >= 5)  return '#7cb342';  // Low-medium: light green
            return '#c0ca33';                  // Very low: pale green
        };

        const presenceColor = getIntensityColor(stats.percentage);
        const presenceIntensity = parseFloat(stats.percentage);

        let html = `
            <div style="margin-bottom: 0.75rem;">
                <h6 style="margin-bottom: 0.5rem; font-weight: 600; color: #1a1a1a;">${featureName}</h6>
        `;

        // Global presence with visual indicator
        html += `
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                    <div style="flex-grow: 1;">
                        <div style="font-size: 0.85rem; color: #666; margin-bottom: 0.25rem;">Global Presence</div>
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <div style="flex-grow: 1; height: 24px; background-color: #f0f0f0; border-radius: 4px; overflow: hidden; border: 1px solid #ddd;">
                                <div style="height: 100%; width: ${presenceIntensity}%; background-color: ${presenceColor}; transition: width 0.3s;"></div>
                            </div>
                            <strong style="min-width: 50px; text-align: right;">${stats.percentage}%</strong>
                        </div>
                    </div>
                </div>
        `;

        // Culture count
        html += `
                <div style="font-size: 0.85rem; color: #666; margin-bottom: 0.5rem;">
                    <span>Cultures: </span><strong>${stats.presence_count}/${stats.total_cultures}</strong>
                </div>
        `;

        // Moran's I if available - Enhanced display
        if (moransI && moransI.statistic !== undefined) {
            const isSig = moransI.p_value && moransI.p_value < 0.05;
            const isSigStrict = moransI.p_value && moransI.p_value < 0.01;
            
            // Determine border color based on significance
            let moransColor = '#999';  // Default: not significant
            let sigLevel = 'Not significant';
            let sigBadge = '';
            
            if (isSigStrict) {
                moransColor = '#d32f2f';  // Red: highly significant
                sigLevel = 'Highly significant (p < 0.01)';
                sigBadge = '<span style="background-color: #ffcdd2; color: #b71c1c; padding: 2px 6px; border-radius: 3px; font-size: 0.7rem; font-weight: 600;">★★ p<0.01</span>';
            } else if (isSig) {
                moransColor = '#f57c00';  // Orange: significant
                sigLevel = 'Significant (p < 0.05)';
                sigBadge = '<span style="background-color: #fff3e0; color: #e65100; padding: 2px 6px; border-radius: 3px; font-size: 0.7rem; font-weight: 600;">★ p<0.05</span>';
            }
            
            // Interpret Moran's I value
            const moransVal = parseFloat(moransI.statistic);
            let interpretation = '';
            if (moransVal > 0.3) {
                interpretation = 'Strong clustering - similar values cluster together';
            } else if (moransVal > 0.1) {
                interpretation = 'Moderate clustering detected';
            } else if (moransVal > -0.1) {
                interpretation = 'Random spatial distribution';
            } else {
                interpretation = 'Dispersion - different values cluster together';
            }
            
            // Z-score interpretation
            const zScore = moransI.z_score || 0;
            const zColor = Math.abs(zScore) > 1.96 ? '#d32f2f' : '#999';
            
            html += `
                <div style="background-color: #f5f5f5; padding: 0.65rem; border-radius: 4px; margin-bottom: 0.75rem; border-left: 4px solid ${moransColor};">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <div style="font-size: 0.85rem; font-weight: 600; color: #1a1a1a;">Spatial Clustering Analysis</div>
                        ${sigBadge}
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-bottom: 0.5rem;">
                        <div>
                            <div style="font-size: 0.75rem; color: #666; margin-bottom: 0.15rem;">Moran's I</div>
                            <div style="font-size: 0.9rem; font-weight: 600; color: ${moransColor};">${moransVal.toFixed(3)}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.75rem; color: #666; margin-bottom: 0.15rem;">Z-Score</div>
                            <div style="font-size: 0.9rem; font-weight: 600; color: ${zColor};">${zScore.toFixed(3)}</div>
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 0.4rem;">
                        <div style="font-size: 0.75rem; color: #666; margin-bottom: 0.15rem;">Pattern</div>
                        <div style="font-size: 0.8rem; color: #333; font-style: italic;">${interpretation}</div>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem; color: #999; border-top: 1px solid rgba(0,0,0,0.1); padding-top: 0.4rem;">
                        <span>p-value: <strong>${moransI.p_value ? moransI.p_value.toFixed(4) : 'N/A'}</strong></span>
                        <span>${sigLevel}</span>
                    </div>
                </div>
            `;
        } else {
            // Fallback when Moran's I data is not available
            html += `
                <div style="background-color: #f5f5f5; padding: 0.65rem; border-radius: 4px; margin-bottom: 0.75rem; border-left: 4px solid #ccc;">
                    <div style="font-size: 0.85rem; font-weight: 600; color: #666; margin-bottom: 0.35rem;">Spatial Clustering Analysis</div>
                    <div style="font-size: 0.8rem; color: #999; font-style: italic;">Spatial analysis data pending for this feature. Phase 6 analysis covers 19 key features.</div>
                </div>
            `;
        }

        // Cluster breakdown with visual bars
        html += `
                <div style="margin-top: 0.75rem; border-top: 1px solid #e0e0e0; padding-top: 0.5rem;">
                    <div style="font-size: 0.85rem; font-weight: 600; color: #1a1a1a; margin-bottom: 0.5rem;">Presence by Cluster</div>
        `;

        for (let i = 0; i < 8; i++) {
            const pct = parseFloat(stats.by_cluster[i]);
            const clusterColor = ColorScheme.getClusterColor(i);
            const barFill = pct > 0 ? pct : 0;
            
            html += `
                    <div style="display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.4rem; font-size: 0.8rem;">
                        <div style="width: 20px; height: 16px; background-color: ${clusterColor}; border-radius: 2px; flex-shrink: 0; border: 1px solid rgba(0,0,0,0.1);"></div>
                        <span style="color: #666; min-width: 18px;">C${i}</span>
                        <div style="flex-grow: 1; height: 16px; background-color: #f0f0f0; border-radius: 2px; overflow: hidden; border: 1px solid #e0e0e0;">
                            <div style="height: 100%; width: ${barFill}%; background-color: ${clusterColor}; opacity: 0.7; transition: width 0.3s;"></div>
                        </div>
                        <strong style="min-width: 35px; text-align: right;">${pct}%</strong>
                    </div>
            `;
        }

        html += `
                </div>
            </div>
        `;

        statsPanel.innerHTML = html;
    };

    /**
     * Handle phylogenetic filter change
     */
    const onPhyloFilterChange = (event) => {
        const familyId = event.target.value;
        GlobeVisualization.filterByLanguageFamily(familyId);
        console.log(`Filtered by language family: ${familyId}`);
    };

    /**
     * Handle cluster filter change
     */
    const onClusterFilterChange = (event) => {
        const clusterId = event.target.value;
        GlobeVisualization.filterByCluster(clusterId);
        console.log(`Filtered by cluster: ${clusterId}`);
    };

    /**
     * View detailed statistics
     */
    const onViewStats = () => {
        if (!selectedFeature) {
            alert('Please select a feature first');
            return;
        }

        const stats = DataLoader.getFeatureStats(selectedFeature);
        console.log('Feature statistics:', stats);
        
        // Could open a modal or expanded view here
        alert(`Feature: ${selectedFeature}\nPresence: ${stats.percentage}% (${stats.presence_count}/${stats.total_cultures})`);
    };

    /**
     * Export filtered data as CSV
     */
    const onExport = () => {
        try {
            // Get cultures based on current selection
            const selected = GlobeVisualization.getSelectedCultures();
            let cultures = selected.length > 0 
                ? selected.map(id => DataLoader.getCultureById(id))
                : DataLoader.getCultures();

            if(!cultures || cultures.length === 0) {
                alert('No cultures to export');
                return;
            }

            // Build CSV with all relevant data
            const headers = ['ID', 'Name', 'Cluster', 'Latitude', 'Longitude', 'Source', 'LanguageFamily', 'FeatureCount'];
            const rows = cultures.map(c => {
                const featureCount = c.features ? Object.values(c.features).filter(v => v === 1).length : 0;
                return [
                    c.id || '',
                    (c.name || '').replace(/"/g, '""'),  // Escape quotes
                    c.cluster !== null ? c.cluster : '',
                    c.lat || '',
                    c.lon || '',
                    c.source || '',
                    c.language_family || 'unknown',
                    featureCount
                ];
            });

            // Format as CSV
            const csv = [headers, ...rows]
                .map(row => row.map(cell => `"${cell}"`).join(','))
                .join('\n');

            // Create download
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            
            // Filename with timestamp and filter info
            const timestamp = new Date().toISOString().split('T')[0];
            const filterInfo = selected.length > 0 ? `_selected_${selected.length}` : '_all';
            link.download = `shamanism_cultures_${timestamp}${filterInfo}.csv`;
            
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);

            // Show success feedback
            const exportBtn = document.getElementById('exportBtn');
            const originalText = exportBtn.textContent;
            exportBtn.textContent = `✓ Exported ${cultures.length} cultures`;
            exportBtn.disabled = true;
            setTimeout(() => {
                exportBtn.textContent = originalText;
                exportBtn.disabled = false;
            }, 2000);

            console.log(`✓ Exported ${cultures.length} cultures to CSV`);
        } catch(error) {
            console.error('Export failed:', error);
            alert(`Export failed: ${error.message}`);
        }
    };

    /**
     * Clear filters and reset to default
     */
    const resetFilters = () => {
        featureSearch.value = '';
        phyloFilter.value = '';
        clusterFilter.value = '';
        selectedFeature = null;
        statsPanel.innerHTML = '<p class="text-muted mb-0">Select a feature to view details</p>';
        GlobeVisualization.resetFilters();
        renderFeatureList(allFeatures);
    };

    return {
        init,
        selectFeature,
        resetFilters,
        getSelectedFeature: () => selectedFeature
    };
})();
