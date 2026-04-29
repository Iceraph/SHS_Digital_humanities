/**
 * globe.js
 * 2D Canvas-based geographic projection for shamanic cultures clustering
 * (3D Three.js implementation planned for Phase 7 Sprint 2)
 */

const GlobeVisualization = (() => {
    let canvas, ctx;
    const container = document.getElementById('globeContainer');
    const tooltip = document.getElementById('globeTooltip');
    
    let selectedCultures = new Set();
    let currentFilters = {
        cluster: null,
        feature: null,
        languageFamily: null
    };
    let scale = 1;
    let offsetX = 0;
    let offsetY = 0;
    let highlightedCluster = null;
    let subsetHighlight = null;   // { ids: Set, color: string } — coverage legend filter

    /**
     * Initialize canvas and set up rendering
     */
    const init = () => {
        // Create canvas
        canvas = document.createElement('canvas');
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
        canvas.style.display = 'block';
        canvas.style.cursor = 'grab';
        const existingCanvas = container.querySelector('canvas');
        if (existingCanvas) existingCanvas.remove();
        container.insertBefore(canvas, container.firstChild);
        
        ctx = canvas.getContext('2d');

        // Event listeners
        window.addEventListener('resize', onWindowResize);
        canvas.addEventListener('mousemove', onMouseMove);
        canvas.addEventListener('click', onMouseClick);
        canvas.addEventListener('wheel', onMouseWheel, { passive: false });
        document.addEventListener('clusterHighlight', onClusterHighlight);

        console.log('✓ 2D Canvas globe initialized');
    };

    /**
     * Project lon/lat to canvas coordinates
     */
    const projectCoordinates = (lon, lat) => {
        // Simple mercator-like projection
        const x = (lon + 180) / 360 * (canvas.width / scale) + offsetX;
        const y = (90 - lat) / 180 * (canvas.height / scale) + offsetY;
        return { x, y };
    };

    /**
     * Reverse projection: canvas to lon/lat
     */
    const unprojectCoordinates = (x, y) => {
        const lon = ((x - offsetX) / (canvas.width / scale)) * 360 - 180;
        const lat = 90 - ((y - offsetY) / (canvas.height / scale)) * 180;
        return { lon, lat };
    };

    /**
     * Plot cultures on the canvas
     */
    const plotCultures = (cultures) => {
        // Store for interaction
        canvas.userData = { cultures, scale, offsetX, offsetY };

        // Clear and render
        render(cultures);
    };

    /**
     * Render cultures on canvas
     */
    const render = (cultures) => {
        if (!cultures || cultures.length === 0) {
            console.warn('No cultures to plot');
            return;
        }

        // Clear canvas
        ctx.fillStyle = 'rgba(102, 126, 234, 0.4)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Draw graticule (optional)
        drawGraticule();

        // Pass 1: draw unclustered cultures as small gray dots (background layer)
        if (highlightedCluster === null) {
            cultures.forEach(culture => {
                if (culture.lat === null || culture.lon === null) return;
                if (culture.cluster !== null && culture.cluster !== undefined) return;

                const proj = projectCoordinates(culture.lon, culture.lat);
                const isSelected = selectedCultures.has(culture.id);
                const inSubset   = subsetHighlight && subsetHighlight.ids.has(culture.id);

                ctx.fillStyle = inSubset ? subsetHighlight.color : '#aaaaaa';
                ctx.globalAlpha = inSubset ? 0.85 : (subsetHighlight ? 0.1 : 0.35);
                ctx.beginPath();
                ctx.arc(proj.x, proj.y, inSubset ? 5 : (isSelected ? 5 : 2.5), 0, Math.PI * 2);
                ctx.fill();
                ctx.globalAlpha = 1.0;

                culture.screenX = proj.x;
                culture.screenY = proj.y;
                culture.screenRadius = inSubset ? 5 : (isSelected ? 5 : 2.5);
            });
        }

        // Pass 2: draw clustered cultures on top
        cultures.forEach(culture => {
            if (culture.lat === null || culture.lon === null) return;
            if (culture.cluster === null || culture.cluster === undefined) return;

            const proj = projectCoordinates(culture.lon, culture.lat);
            const isSelected = selectedCultures.has(culture.id);
            const size = isSelected ? 8 : 4;
            const color = ColorScheme.getClusterColor(culture.cluster);

            let opacity = 0.8;
            if (highlightedCluster !== null && culture.cluster !== highlightedCluster) {
                opacity = 0.2;
            }
            // Dim clustered dots when a subset (unclustered) is highlighted
            if (subsetHighlight) opacity = Math.min(opacity, 0.15);

            ctx.fillStyle = color;
            ctx.globalAlpha = opacity;
            ctx.beginPath();
            ctx.arc(proj.x, proj.y, size, 0, Math.PI * 2);
            ctx.fill();
            ctx.globalAlpha = 1.0;

            culture.screenX = proj.x;
            culture.screenY = proj.y;
            culture.screenRadius = size;
        });

        // Draw legend
        drawLegend();
    };

    /**
     * Draw graticule (lat/lon grid)
     */
    const drawGraticule = () => {
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        ctx.lineWidth = 0.5;

        // Latitude lines
        for (let lat = -90; lat <= 90; lat += 30) {
            ctx.beginPath();
            for (let lon = -180; lon <= 180; lon += 10) {
                const proj = projectCoordinates(lon, lat);
                if (lon === -180) {
                    ctx.moveTo(proj.x, proj.y);
                } else {
                    ctx.lineTo(proj.x, proj.y);
                }
            }
            ctx.stroke();
        }

        // Longitude lines
        for (let lon = -180; lon <= 180; lon += 30) {
            ctx.beginPath();
            for (let lat = -90; lat <= 90; lat += 10) {
                const proj = projectCoordinates(lon, lat);
                if (lat === -90) {
                    ctx.moveTo(proj.x, proj.y);
                } else {
                    ctx.lineTo(proj.x, proj.y);
                }
            }
            ctx.stroke();
        }
    };

    /**
     * Draw legend
     */
    const drawLegend = () => {
        const legendX = 10;
        const legendY = 10;
        const itemHeight = 18;
        const totalItems = 9; // 8 clusters + 1 unclustered row

        ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        ctx.fillRect(legendX, legendY, 160, 22 + totalItems * itemHeight);

        ctx.fillStyle = '#fff';
        ctx.font = 'bold 12px sans-serif';
        ctx.fillText('Clusters', legendX + 5, legendY + 18);

        ctx.font = '11px sans-serif';
        for (let i = 0; i < 8; i++) {
            const y = legendY + 20 + (i * itemHeight);
            const color = ColorScheme.getClusterColor(i);
            ctx.fillStyle = color;
            ctx.fillRect(legendX + 5, y, 12, 12);
            ctx.fillStyle = '#fff';
            ctx.fillText(`Cluster ${i}`, legendX + 20, y + 10);
        }

        // Unclustered row
        const uy = legendY + 20 + (8 * itemHeight);
        ctx.fillStyle = '#aaaaaa';
        ctx.globalAlpha = 0.5;
        ctx.beginPath();
        ctx.arc(legendX + 11, uy + 6, 3, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1.0;
        ctx.fillStyle = '#ccc';
        ctx.fillText('Not clustered', legendX + 20, uy + 10);
    };

    /**
     * Handle window resize
     */
    const onWindowResize = () => {
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
        
        if (canvas.userData && canvas.userData.cultures) {
            render(canvas.userData.cultures);
        }
    };

    /**
     * Handle mouse move for hover tooltips
     */
    const onMouseMove = (event) => {
        if (!canvas.userData || !canvas.userData.cultures) return;

        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;

        // Find hovered culture
        for (const culture of canvas.userData.cultures) {
            if (culture.screenX && culture.screenY && culture.screenRadius) {
                const dist = Math.sqrt(
                    Math.pow(x - culture.screenX, 2) +
                    Math.pow(y - culture.screenY, 2)
                );
                if (dist < culture.screenRadius + 5) {
                    showTooltip(event.clientX, event.clientY, culture);
                    canvas.style.cursor = 'pointer';
                    return;
                }
            }
        }

        tooltip.style.display = 'none';
        canvas.style.cursor = 'grab';
    };

    /**
     * Handle mouse click for selection
     */
    const onMouseClick = (event) => {
        if (!canvas.userData || !canvas.userData.cultures) return;

        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;

        // Find clicked culture
        for (const culture of canvas.userData.cultures) {
            if (culture.screenX && culture.screenY && culture.screenRadius) {
                const dist = Math.sqrt(
                    Math.pow(x - culture.screenX, 2) +
                    Math.pow(y - culture.screenY, 2)
                );
                if (dist < culture.screenRadius + 5) {
                    selectCulture(culture);
                    return;
                }
            }
        }
    };

    /**
     * Handle mouse wheel for zoom
     */
    const onMouseWheel = (event) => {
        event.preventDefault();
        
        const zoom = event.deltaY > 0 ? 0.9 : 1.1;
        scale *= zoom;
        scale = Math.max(0.5, Math.min(scale, 5)); // Limit zoom range
        
        if (canvas.userData && canvas.userData.cultures) {
            render(canvas.userData.cultures);
        }
    };

    /**
     * Handle cluster highlight event from legend
     */
    const onClusterHighlight = (event) => {
        const cluster = event.detail.cluster;
        highlightedCluster = cluster;
        
        if (canvas.userData && canvas.userData.cultures) {
            render(canvas.userData.cultures);
        }
    };

    /**
     * Show tooltip for a culture
     */
    const showTooltip = (x, y, culture) => {
        const clusterLabel = (culture.cluster !== null && culture.cluster !== undefined)
            ? `Cluster ${culture.cluster}`
            : '<em>Not clustered (phylogenetic filter)</em>';
        tooltip.innerHTML = `
            <div class="globe-tooltip-title">${culture.name}</div>
            <div class="globe-tooltip-content">
                <div>Cluster: ${clusterLabel}</div>
                <div>Source: ${culture.source}</div>
                <div>Lat: ${culture.lat.toFixed(2)}, Lon: ${culture.lon.toFixed(2)}</div>
                <div>Features: ${Object.values(culture.features).filter(v => v === 1).length}</div>
            </div>
        `;
        tooltip.style.display = 'block';
        tooltip.style.left = (x + 10) + 'px';
        tooltip.style.top = (y + 10) + 'px';
    };

    /**
     * Select a culture
     */
    const selectCulture = (culture) => {
        if (selectedCultures.has(culture.id)) {
            selectedCultures.delete(culture.id);
        } else {
            selectedCultures.add(culture.id);
        }

        console.log(`Selected ${selectedCultures.size} culture(s)`);
        
        if (canvas.userData && canvas.userData.cultures) {
            render(canvas.userData.cultures);
        }

        document.dispatchEvent(new CustomEvent('cultureSelected', {
            detail: { culture, selectedCount: selectedCultures.size }
        }));
    };

    /**
     * Apply feature filter
     */
    const filterByFeature = (featureName) => {
        currentFilters.feature = featureName;
        
        const cultures = DataLoader.getCultures();
        const culturesWithFeature = featureName 
            ? DataLoader.getCulturesByFeature(featureName, 1)
            : cultures;

        plotCultures(culturesWithFeature);
    };

    /**
     * Apply cluster filter
     */
    const filterByCluster = (clusterId) => {
        currentFilters.cluster = clusterId;
        
        const cultures = clusterId !== null && clusterId !== ''
            ? DataLoader.getCulturesByCluster(parseInt(clusterId))
            : DataLoader.getCultures();

        plotCultures(cultures);
    };

    /**
     * Apply language family filter
     */
    const filterByLanguageFamily = (languageFamily) => {
        currentFilters.languageFamily = languageFamily;
        
        const cultures = DataLoader.getCulturesByLanguageFamily(languageFamily);
        plotCultures(cultures);
    };

    /**
     * Reset all filters
     */
    const resetFilters = () => {
        currentFilters = { cluster: null, feature: null, languageFamily: null };
        selectedCultures.clear();
        scale = 1;
        offsetX = 0;
        offsetY = 0;
        plotCultures(DataLoader.getCultures());
    };

    /**
     * Animate function (for future 3D implementation)
     */
    const animate = () => {
        requestAnimationFrame(animate);
    };

    /**
     * Highlight a specific subset of cultures (by ID array) in a given colour.
     * All other cultures are dimmed. Call with null to clear.
     */
    const highlightSubset = (ids, color = '#f39c12') => {
        subsetHighlight = ids && ids.length > 0
            ? { ids: new Set(ids), color }
            : null;
        if (canvas.userData && canvas.userData.cultures) {
            render(canvas.userData.cultures);
        }
    };

    /**
     * Clear subset highlight and return to normal rendering.
     */
    const clearSubsetHighlight = () => highlightSubset(null);

    return {
        init,
        plotCultures,
        animate,
        filterByFeature,
        filterByCluster,
        filterByLanguageFamily,
        resetFilters,
        highlightSubset,
        clearSubsetHighlight,
        getFilters: () => ({ ...currentFilters }),
        getSelectedCultures: () => Array.from(selectedCultures)
    };
})();
