/**
 * globe2d.js
 * 2D Canvas-based geographic projection for shamanic cultures clustering
 */

const Globe2D = (() => {
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
    let worldLand = null;         // GeoJSON FeatureCollection for land polygons

    const init = () => {
        canvas = document.createElement('canvas');
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
        canvas.style.display = 'block';
        canvas.style.cursor = 'grab';
        const existingCanvas = container.querySelector('canvas');
        if (existingCanvas) existingCanvas.remove();
        container.insertBefore(canvas, container.firstChild);

        ctx = canvas.getContext('2d');

        window.addEventListener('resize', onWindowResize);
        canvas.addEventListener('mousemove', onMouseMove);
        canvas.addEventListener('click', onMouseClick);
        canvas.addEventListener('wheel', onMouseWheel, { passive: false });
        document.addEventListener('clusterHighlight', onClusterHighlight);

        loadWorldMap();
        console.log('✓ 2D Canvas globe initialized');
    };

    const loadWorldMap = async () => {
        if (worldLand) return;
        try {
            const topo = await fetch('data/land-110m.json').then(r => r.json());
            worldLand = topojson.feature(topo, topo.objects.land);
            console.log('✓ World map loaded');
            if (canvas.userData && canvas.userData.cultures) {
                render(canvas.userData.cultures);
            }
        } catch (e) {
            console.warn('World map unavailable:', e);
        }
    };

    const projectCoordinates = (lon, lat) => {
        const x = (lon + 180) / 360 * (canvas.width / scale) + offsetX;
        const y = (90 - lat) / 180 * (canvas.height / scale) + offsetY;
        return { x, y };
    };

    const plotCultures = (cultures) => {
        canvas.userData = { cultures, scale, offsetX, offsetY };
        render(cultures);
    };

    const render = (cultures) => {
        if (!cultures || cultures.length === 0) {
            console.warn('No cultures to plot');
            return;
        }

        ctx.fillStyle = '#1a3a5c';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        drawWorldMap();
        drawGraticule();

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
    };

    const drawWorldMap = () => {
        if (!worldLand) return;

        const W = canvas.width;
        const H = canvas.height;
        const baseScale = W / (2 * Math.PI * scale);
        const centerX   = W / (2 * scale) + offsetX;
        const centerY   = H / (2 * scale) + offsetY;
        const yscaleFactor = 2 * H / W;

        const baseProj = d3.geoEquirectangular()
            .scale(baseScale)
            .translate([centerX, centerY])
            .precision(0.1);

        const compositeProj = {
            stream: function(outputStream) {
                return baseProj.stream({
                    point:        (x, y) => outputStream.point(x, (y - centerY) * yscaleFactor + centerY),
                    lineStart:    ()     => outputStream.lineStart(),
                    lineEnd:      ()     => outputStream.lineEnd(),
                    polygonStart: ()     => outputStream.polygonStart(),
                    polygonEnd:   ()     => outputStream.polygonEnd(),
                    sphere:       ()     => outputStream.sphere()
                });
            }
        };

        const path = d3.geoPath().projection(compositeProj).context(ctx);

        ctx.save();
        ctx.beginPath();
        ctx.rect(0, 0, W, H);
        ctx.clip();

        ctx.beginPath();
        path(worldLand);
        ctx.fillStyle = '#2d4a38';
        ctx.fill();
        ctx.strokeStyle = 'rgba(160, 200, 160, 0.3)';
        ctx.lineWidth = 0.4;
        ctx.stroke();

        ctx.restore();
    };

    const drawGraticule = () => {
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        ctx.lineWidth = 0.5;

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

    const onWindowResize = () => {
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;

        if (canvas.userData && canvas.userData.cultures) {
            render(canvas.userData.cultures);
        }
    };

    const onMouseMove = (event) => {
        if (!canvas.userData || !canvas.userData.cultures) return;

        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;

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

    const onMouseClick = (event) => {
        if (!canvas.userData || !canvas.userData.cultures) return;

        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;

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

    const onMouseWheel = (event) => {
        event.preventDefault();

        const zoom = event.deltaY > 0 ? 0.9 : 1.1;
        scale *= zoom;
        scale = Math.max(0.5, Math.min(scale, 5));

        if (canvas.userData && canvas.userData.cultures) {
            render(canvas.userData.cultures);
        }
    };

    const onClusterHighlight = (event) => {
        const cluster = event.detail.cluster;
        highlightedCluster = cluster;

        if (canvas.userData && canvas.userData.cultures) {
            render(canvas.userData.cultures);
        }
    };

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

    const selectCulture = (culture) => {
        if (selectedCultures.has(culture.id)) {
            selectedCultures.delete(culture.id);
        } else {
            selectedCultures.add(culture.id);
        }

        if (canvas.userData && canvas.userData.cultures) {
            render(canvas.userData.cultures);
        }

        document.dispatchEvent(new CustomEvent('cultureSelected', {
            detail: { culture, selectedCount: selectedCultures.size }
        }));
    };

    const filterByFeature = (featureName) => {
        currentFilters.feature = featureName;

        const cultures = DataLoader.getCultures();
        const culturesWithFeature = featureName
            ? DataLoader.getCulturesByFeature(featureName, 1)
            : cultures;

        plotCultures(culturesWithFeature);
    };

    const filterByCluster = (clusterId) => {
        currentFilters.cluster = clusterId;

        const cultures = clusterId !== null && clusterId !== ''
            ? DataLoader.getCulturesByCluster(parseInt(clusterId))
            : DataLoader.getCultures();

        plotCultures(cultures);
    };

    const filterByLanguageFamily = (languageFamily) => {
        currentFilters.languageFamily = languageFamily;

        const cultures = DataLoader.getCulturesByLanguageFamily(languageFamily);
        plotCultures(cultures);
    };

    const resetFilters = () => {
        currentFilters = { cluster: null, feature: null, languageFamily: null };
        selectedCultures.clear();
        scale = 1;
        offsetX = 0;
        offsetY = 0;
        plotCultures(DataLoader.getCultures());
    };

    const animate = () => {
        requestAnimationFrame(animate);
    };

    const highlightSubset = (ids, color = '#f39c12') => {
        subsetHighlight = ids && ids.length > 0
            ? { ids: new Set(ids), color }
            : null;
        if (canvas.userData && canvas.userData.cultures) {
            render(canvas.userData.cultures);
        }
    };

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
