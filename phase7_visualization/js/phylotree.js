/**
 * phylotree.js
 * D3.js phylogenetic tree visualization
 * - Depth-2 pruning keeps the sidebar readable (76 top families + children)
 * - Listens to the clusterHighlight event to dim non-matching families
 * - Hover tooltip shows cluster composition breakdown
 */

const PhylogenicTreeVisualization = (() => {
    const container = document.getElementById('phyloTree');
    let svg, nodeSelection;

    // Tooltip div shared across all phylotree hovers
    const tooltip = (() => {
        const el = document.createElement('div');
        el.id = 'phyloTooltip';
        Object.assign(el.style, {
            position: 'fixed', background: 'rgba(0,0,0,0.8)', color: '#fff',
            padding: '6px 10px', borderRadius: '4px', fontSize: '11px',
            pointerEvents: 'none', display: 'none', zIndex: '9999',
            maxWidth: '200px', lineHeight: '1.5'
        });
        document.body.appendChild(el);
        return el;
    })();

    const MAX_DEPTH = 2;
    const ROW_HEIGHT = 18;

    const pruneTree = (node, depth = 0) => {
        if (depth >= MAX_DEPTH || !node.children || node.children.length === 0) {
            return { ...node, children: undefined };
        }
        return { ...node, children: node.children.map(c => pruneTree(c, depth + 1)) };
    };

    const countLeaves = (node) => {
        if (!node.children || node.children.length === 0) return 1;
        return node.children.reduce((s, c) => s + countLeaves(c), 0);
    };

    /** Dominant cluster id (string) for a node, or null. */
    const dominantCluster = (comp) => {
        if (!comp || Object.keys(comp).length === 0) return null;
        return Object.keys(comp).reduce((a, b) => comp[a] > comp[b] ? a : b);
    };

    const init = () => {
        if (!container) return;
        container.innerHTML = '';

        const phyloData = DataLoader.getPhyloTree();
        if (phyloData && phyloData.name) {
            displayTree(phyloData);
            document.addEventListener('clusterHighlight', (e) => {
                highlightCluster(e.detail.cluster);
            });
            window.addEventListener('resize', onResize);
        } else {
            container.innerHTML =
                '<p class="text-muted text-center p-3" style="font-size:0.85rem">No phylogenetic data available.</p>';
        }
    };

    const displayTree = (data) => {
        const pruned = pruneTree(data);
        const leafCount = countLeaves(pruned);

        const margin = { top: 10, right: 130, bottom: 10, left: 10 };
        const containerW = container.clientWidth || 360;
        const width  = containerW - margin.left - margin.right;
        const height = Math.max(300, leafCount * ROW_HEIGHT);

        svg = d3.select(container)
            .append('svg')
            .attr('width', containerW)
            .attr('height', height + margin.top + margin.bottom);

        const g = svg.append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        const treeLayout = d3.tree().size([height, width]);
        const root = d3.hierarchy(pruned);
        treeLayout(root);

        // Links
        g.selectAll('.tree-link')
            .data(root.links())
            .enter()
            .append('path')
            .attr('class', 'tree-link')
            .attr('fill', 'none')
            .attr('stroke', '#ccc')
            .attr('stroke-width', 1.5)
            .attr('d', d3.linkHorizontal().x(d => d.y).y(d => d.x));

        // Nodes
        nodeSelection = g.selectAll('.tree-node')
            .data(root.descendants())
            .enter()
            .append('g')
            .attr('class', 'tree-node')
            .attr('data-dominant', d => dominantCluster(d.data.cluster_composition) || '')
            .attr('transform', d => `translate(${d.y},${d.x})`)
            .style('cursor', d => d.data.id ? 'pointer' : 'default')
            .on('click', (event, d) => {
                if (d.data.id) selectLanguageFamily(d.data.id);
            })
            .on('mouseenter', onNodeEnter)
            .on('mousemove', onNodeMove)
            .on('mouseleave', onNodeLeave);

        // Circles coloured by dominant cluster
        nodeSelection.append('circle')
            .attr('r', d => d.children ? 4 : 5)
            .attr('fill', d => {
                const dom = dominantCluster(d.data.cluster_composition);
                return dom !== null ? ColorScheme.getClusterColor(parseInt(dom)) : '#bbb';
            })
            .attr('stroke', '#fff')
            .attr('stroke-width', 1);

        // Labels for leaf nodes
        nodeSelection.filter(d => !d.children)
            .append('text')
            .attr('class', 'tree-label')
            .attr('x', 8)
            .attr('dy', '0.32em')
            .attr('text-anchor', 'start')
            .style('font-size', '10px')
            .style('fill', '#555')
            .text(d => d.data.name || d.data.id || '');

        // Zoom / pan
        const zoom = d3.zoom()
            .scaleExtent([0.2, 5])
            .on('zoom', (event) => g.attr('transform', event.transform));
        svg.call(zoom);
    };

    // ── Tooltip handlers ──────────────────────────────────────────────────

    const buildTooltipHTML = (d) => {
        const comp = d.data.cluster_composition;
        const name = d.data.name || d.data.id || '(unnamed)';
        const total = comp ? Object.values(comp).reduce((s, v) => s + v, 0) : 0;

        let html = `<strong>${name}</strong>`;
        if (total > 0) {
            html += `<br><span style="opacity:0.8">${total} cultures</span>`;
            const sorted = Object.entries(comp).sort((a, b) => b[1] - a[1]).slice(0, 4);
            html += '<br>' + sorted.map(([cid, n]) => {
                const pct = Math.round(n / total * 100);
                const col = ColorScheme.getClusterColor(parseInt(cid));
                return `<span style="color:${col}">■</span> C${cid}: ${pct}%`;
            }).join('  ');
        }
        if (d.data.id && d.data.id !== name) {
            html += `<br><span style="opacity:0.6;font-size:10px">${d.data.id}</span>`;
        }
        return html;
    };

    const onNodeEnter = function (event, d) {
        d3.select(this).select('circle').attr('r', 8);
        tooltip.innerHTML = buildTooltipHTML(d);
        tooltip.style.display = 'block';
        positionTooltip(event);
    };

    const onNodeMove = (event) => positionTooltip(event);

    const onNodeLeave = function (event, d) {
        d3.select(this).select('circle').attr('r', d.children ? 4 : 5);
        tooltip.style.display = 'none';
    };

    const positionTooltip = (event) => {
        const x = event.clientX + 12;
        const y = event.clientY - 10;
        tooltip.style.left = x + 'px';
        tooltip.style.top  = y + 'px';
    };

    // ── Cluster highlighting ───────────────────────────────────────────────

    const highlightCluster = (clusterId) => {
        if (!nodeSelection) return;
        if (clusterId === null || clusterId === undefined) {
            nodeSelection.style('opacity', 1);
        } else {
            nodeSelection.style('opacity', function () {
                const dom = d3.select(this).attr('data-dominant');
                return dom === String(clusterId) ? 1 : 0.15;
            });
        }
    };

    // ── Language family selection ──────────────────────────────────────────

    const selectLanguageFamily = (familyId) => {
        document.dispatchEvent(new CustomEvent('languageFamilySelected', {
            detail: { familyId }
        }));
    };

    // ── Resize ────────────────────────────────────────────────────────────

    let resizeTimer;
    const onResize = () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(init, 200);
    };

    return { init, selectLanguageFamily, highlightCluster, onResize };
})();
