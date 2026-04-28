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
    let highlightedCluster = null;  // For interactive cluster highlighting

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
        container.innerHTML = '';
        container.appendChild(canvas);
        
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

        // Draw cultures
        cultures.forEach(culture => {
            if (culture.lat === null || culture.lon === null || culture.cluster === null) {
                return;
            }

            const proj = projectCoordinates(culture.lon, culture.lat);
            const size = selectedCultures.has(culture.id) ? 8 : 4;
            const color = ColorScheme.getClusterColor(culture.cluster);

            // Apply opacity based on cluster highlight
            let opacity = 0.8;
            if (highlightedCluster !== null && culture.cluster !== highlightedCluster) {
                opacity = 0.2;  // Dim non-highlighted clusters
            }

            // Draw point
            ctx.fillStyle = color;
            ctx.globalAlpha = opacity;
            ctx.beginPath();
            ctx.arc(proj.x, proj.y, size, 0, Math.PI * 2);
            ctx.fill();
            ctx.globalAlpha = 1.0;

            // Store culture reference
            if (!culture.screenX) {
                culture.screenX = proj.x;
                culture.screenY = proj.y;
                culture.screenRadius = size;
            }
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

        ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        ctx.fillRect(legendX, legendY, 150, 160);

        ctx.fillStyle = '#fff';
        ctx.font = 'bold 12px sans-serif';
        ctx.fillText('Clusters', legendX + 5, legendY + 18);

        ctx.font = '11px sans-serif';
        for (let i = 0; i < 8; i++) {
            const y = legendY + 20 + (i * itemHeight);
            const color = ColorScheme.getClusterColor(i);

            // Color box
            ctx.fillStyle = color;
            ctx.fillRect(legendX + 5, y, 12, 12);

            // Label
            ctx.fillStyle = '#fff';
            ctx.fillText(`Cluster ${i}`, legendX + 20, y + 10);
        }
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
        tooltip.innerHTML = `
            <div class="globe-tooltip-title">${culture.name}</div>
            <div class="globe-tooltip-content">
                <div>Cluster: ${culture.cluster}</div>
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

    return {
        init,
        plotCultures,
        animate,
        filterByFeature,
        filterByCluster,
        filterByLanguageFamily,
        resetFilters,
        getFilters: () => ({ ...currentFilters }),
        getSelectedCultures: () => Array.from(selectedCultures)
    };
})();
