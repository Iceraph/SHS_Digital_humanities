/**
 * globe3d.js
 * Three.js-based 3D globe for shamanic cultures clustering
 */

const Globe3D = (() => {
    const container = document.getElementById('globeContainer');
    const tooltip = document.getElementById('globeTooltip');

    const globeRadius = 100;
    const basePointSize = 2.6;
    const selectedPointSize = 5.0;

    let scene, camera, renderer, controls, raycaster;
    let globeMesh = null;
    let pointsMesh = null;
    let selectedMesh = null;
    let currentCultures = [];
    let highlightedCluster = null;
    let subsetHighlight = null; // { ids: Set, color: string }
    let listenersBound = false;
    let landTexture = null;
    let landTexturePromise = null;

    let selectedCultures = new Set();
    let currentFilters = {
        cluster: null,
        feature: null,
        languageFamily: null
    };

    const waitForThree = async () => {
        if (window.__threeReady || (window.THREE && window.THREE.OrbitControls)) {
            return;
        }

        if (window.__threeLoaderPromise) {
            await Promise.race([
                window.__threeLoaderPromise,
                new Promise((_, reject) => setTimeout(() => reject(new Error('Three.js not loaded. Ensure module loader runs.')), 12000))
            ]);
        }

        if (!(window.__threeReady || (window.THREE && window.THREE.OrbitControls))) {
            throw new Error('Three.js not loaded. Ensure module loader runs.');
        }
    };

    const init = async () => {
        await waitForThree();
        cleanupRenderer();
        removeStaleCanvas();

        scene = new THREE.Scene();
        scene.background = new THREE.Color(0x10233b);

        const { width, height } = getSize();
        camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
        camera.position.set(0, 0, 260);

        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setSize(width, height);
        renderer.setPixelRatio(window.devicePixelRatio || 1);
        renderer.domElement.style.display = 'block';
        renderer.domElement.style.width = '100%';
        renderer.domElement.style.height = '100%';
        renderer.domElement.style.cursor = 'grab';

        container.insertBefore(renderer.domElement, container.firstChild);

        raycaster = new THREE.Raycaster();
        raycaster.params.Points.threshold = 1.5;

        setupLights();
        createGlobe();
        applyLandTexture();
        setupControls();
        bindEvents();

        if (currentCultures.length > 0) {
            plotCultures(currentCultures);
        }

        console.log('✓ 3D globe initialized');
    };

    const cleanupRenderer = () => {
        if (renderer && renderer.domElement && renderer.domElement.parentNode) {
            renderer.domElement.parentNode.removeChild(renderer.domElement);
        }
        scene = null;
        camera = null;
        renderer = null;
        controls = null;
        globeMesh = null;
        pointsMesh = null;
        selectedMesh = null;
    };

    const removeStaleCanvas = () => {
        const canvases = container.querySelectorAll('canvas');
        canvases.forEach((canvas) => {
            if (canvas !== renderer?.domElement) {
                canvas.remove();
            }
        });
    };

    const getSize = () => {
        return {
            width: container.clientWidth || 800,
            height: container.clientHeight || 600
        };
    };

    const setupLights = () => {
        const ambient = new THREE.AmbientLight(0xffffff, 0.65);
        scene.add(ambient);

        const directional = new THREE.DirectionalLight(0xffffff, 0.85);
        directional.position.set(5, 3, 5);
        scene.add(directional);
    };

    const createGlobe = () => {
        const geometry = new THREE.SphereGeometry(globeRadius, 64, 64);
        const material = new THREE.MeshPhongMaterial({
            color: 0xffffff,
            shininess: 10,
            emissive: 0x081522,
            specular: 0x0f2033
        });
        globeMesh = new THREE.Mesh(geometry, material);
        scene.add(globeMesh);
    };

    const applyLandTexture = () => {
        if (!globeMesh) return;
        loadLandTexture()
            .then((texture) => {
                if (!globeMesh || !texture) return;
                globeMesh.material.map = texture;
                globeMesh.material.needsUpdate = true;
            })
            .catch((error) => {
                console.warn('Land texture unavailable:', error);
            });
    };

    const loadLandTexture = () => {
        if (landTexturePromise) return landTexturePromise;
        landTexturePromise = fetch('data/land-110m.json')
            .then((response) => response.json())
            .then((topo) => {
                if (!window.d3 || !window.topojson) {
                    throw new Error('Missing d3/topojson for land texture');
                }
                const worldLand = topojson.feature(topo, topo.objects.land);

                const width = 1024;
                const height = 512;
                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;

                const ctx = canvas.getContext('2d');
                ctx.fillStyle = '#162a41';
                ctx.fillRect(0, 0, width, height);

                const projection = d3.geoEquirectangular()
                    .translate([width / 2, height / 2])
                    .scale(width / (2 * Math.PI));
                const path = d3.geoPath(projection, ctx);

                ctx.beginPath();
                path(worldLand);
                ctx.fillStyle = '#2f7a55';
                ctx.fill();
                ctx.strokeStyle = 'rgba(170, 220, 170, 0.45)';
                ctx.lineWidth = 0.6;
                ctx.stroke();

                const texture = new THREE.CanvasTexture(canvas);
                if (texture.colorSpace !== undefined) {
                    texture.colorSpace = THREE.SRGBColorSpace;
                }
                texture.needsUpdate = true;
                landTexture = texture;
                return texture;
            });
        return landTexturePromise;
    };

    const setupControls = () => {
        if (!THREE.OrbitControls) {
            console.warn('OrbitControls not available; using static camera');
            return;
        }
        controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.08;
        controls.enablePan = true;
        controls.minDistance = 140;
        controls.maxDistance = 420;
        controls.enableZoom = true;
    };

    const bindEvents = () => {
        if (listenersBound) return;
        listenersBound = true;

        window.addEventListener('resize', onWindowResize);
        renderer.domElement.addEventListener('mousemove', onPointerMove);
        renderer.domElement.addEventListener('click', onPointerClick);
        document.addEventListener('clusterHighlight', onClusterHighlight);
    };

    const plotCultures = (cultures) => {
        currentCultures = cultures || [];

        if (!scene) return;

        if (pointsMesh) {
            scene.remove(pointsMesh);
            pointsMesh.geometry.dispose();
            pointsMesh.material.dispose();
            pointsMesh = null;
        }

        const { positions, colors, cultureIndex } = buildPointGeometry(currentCultures);
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
        geometry.userData = { cultureIndex };

        const material = new THREE.PointsMaterial({
            size: basePointSize,
            vertexColors: true,
            transparent: true,
            opacity: 0.9
        });

        pointsMesh = new THREE.Points(geometry, material);
        scene.add(pointsMesh);

        updateSelectedMesh();
    };

    const buildPointGeometry = (cultures) => {
        const positions = [];
        const colors = [];
        const cultureIndex = [];

        cultures.forEach((culture) => {
            if (culture.lat === null || culture.lon === null) return;
            const { x, y, z } = latLonToVector3(culture.lat, culture.lon, globeRadius + 1.2);
            positions.push(x, y, z);

            const color = getCultureColor(culture);
            colors.push(color.r, color.g, color.b);
            cultureIndex.push(culture);
        });

        return { positions, colors, cultureIndex };
    };

    const latLonToVector3 = (lat, lon, radius) => {
        const phi = (90 - lat) * (Math.PI / 180);
        const theta = (lon + 180) * (Math.PI / 180);
        const x = -radius * Math.sin(phi) * Math.cos(theta);
        const z = radius * Math.sin(phi) * Math.sin(theta);
        const y = radius * Math.cos(phi);
        return { x, y, z };
    };

    const getCultureColor = (culture) => {
        if (subsetHighlight) {
            if (subsetHighlight.ids.has(culture.id)) {
                return new THREE.Color(subsetHighlight.color);
            }
            return new THREE.Color('#4c566a');
        }

        if (highlightedCluster !== null && culture.cluster !== highlightedCluster) {
            return new THREE.Color('#4c566a');
        }

        if (culture.cluster === null || culture.cluster === undefined) {
            return new THREE.Color('#a0a0a0');
        }
        return new THREE.Color(ColorScheme.getClusterColor(culture.cluster));
    };

    const updateSelectedMesh = () => {
        if (!scene) return;

        if (selectedMesh) {
            scene.remove(selectedMesh);
            selectedMesh.geometry.dispose();
            selectedMesh.material.dispose();
            selectedMesh = null;
        }

        const selected = currentCultures.filter(c => selectedCultures.has(c.id));
        if (selected.length === 0) return;

        const positions = [];
        selected.forEach(culture => {
            if (culture.lat === null || culture.lon === null) return;
            const { x, y, z } = latLonToVector3(culture.lat, culture.lon, globeRadius + 2.2);
            positions.push(x, y, z);
        });

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));

        const material = new THREE.PointsMaterial({
            size: selectedPointSize,
            color: 0xffffff,
            transparent: true,
            opacity: 0.9
        });

        selectedMesh = new THREE.Points(geometry, material);
        scene.add(selectedMesh);
    };

    const onWindowResize = () => {
        if (!renderer || !camera) return;
        const { width, height } = getSize();
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height);
    };

    const onPointerMove = (event) => {
        if (!pointsMesh) return;
        const rect = renderer.domElement.getBoundingClientRect();
        const mouse = new THREE.Vector2(
            ((event.clientX - rect.left) / rect.width) * 2 - 1,
            -((event.clientY - rect.top) / rect.height) * 2 + 1
        );

        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObject(pointsMesh);
        if (intersects.length > 0) {
            const hit = intersects[0];
            const culture = pointsMesh.geometry.userData.cultureIndex[hit.index];
            if (culture) {
                showTooltip(event.clientX, event.clientY, culture);
                renderer.domElement.style.cursor = 'pointer';
                return;
            }
        }

        tooltip.style.display = 'none';
        renderer.domElement.style.cursor = 'grab';
    };

    const onPointerClick = (event) => {
        if (!pointsMesh) return;
        const rect = renderer.domElement.getBoundingClientRect();
        const mouse = new THREE.Vector2(
            ((event.clientX - rect.left) / rect.width) * 2 - 1,
            -((event.clientY - rect.top) / rect.height) * 2 + 1
        );

        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObject(pointsMesh);
        if (intersects.length > 0) {
            const hit = intersects[0];
            const culture = pointsMesh.geometry.userData.cultureIndex[hit.index];
            if (culture) {
                selectCulture(culture);
            }
        }
    };

    const onClusterHighlight = (event) => {
        highlightedCluster = event.detail.cluster;
        plotCultures(currentCultures);
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

        updateSelectedMesh();

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
        plotCultures(DataLoader.getCultures());
    };

    const highlightSubset = (ids, color = '#f39c12') => {
        subsetHighlight = ids && ids.length > 0
            ? { ids: new Set(ids), color }
            : null;
        plotCultures(currentCultures);
    };

    const clearSubsetHighlight = () => highlightSubset(null);

    const animate = () => {
        requestAnimationFrame(animate);
        if (controls) controls.update();
        if (renderer && scene && camera) {
            renderer.render(scene, camera);
        }
    };

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
        getSelectedCultures: () => Array.from(selectedCultures),
        getFilters: () => ({ ...currentFilters })
    };
})();
