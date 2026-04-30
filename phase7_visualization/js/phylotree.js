/**
 * phylotree.js
 * D3.js phylogenetic tree visualization
 * Renders top-level language families (depth ≤ 2) to stay usable in the sidebar.
 */

const PhylogenicTreeVisualization = (() => {
    const container = document.getElementById('phyloTree');
    let svg;

    const MAX_DEPTH = 2;   // Only render root → family → subfamily
    const ROW_HEIGHT = 18; // px per leaf node

    /**
     * Prune the tree to a maximum depth so the sidebar stays readable.
     */
    const pruneTree = (node, depth = 0) => {
        if (depth >= MAX_DEPTH || !node.children || node.children.length === 0) {
            return { ...node, children: undefined };
        }
        return {
            ...node,
            children: node.children.map(c => pruneTree(c, depth + 1))
        };
    };

    /**
     * Count leaf nodes in a (possibly pruned) tree.
     */
    const countLeaves = (node) => {
        if (!node.children || node.children.length === 0) return 1;
        return node.children.reduce((sum, c) => sum + countLeaves(c), 0);
    };

    /**
     * Initialize phylogenetic tree visualization.
     */
    const init = () => {
        if (!container) return;

        // Clear spinner / any previous render
        container.innerHTML = '';

        const phyloData = DataLoader.getPhyloTree();
        if (phyloData && phyloData.name) {
            displayTree(phyloData);
        } else {
            container.innerHTML =
                '<p class="text-muted text-center p-3" style="font-size:0.85rem">No phylogenetic data available.</p>';
        }
    };

    /**
     * Render the (pruned) phylogenetic tree.
     */
    const displayTree = (data) => {
        const pruned = pruneTree(data);
        const leafCount = countLeaves(pruned);

        const margin = { top: 10, right: 120, bottom: 10, left: 10 };
        const containerW = container.clientWidth || 360;
        const width  = containerW - margin.left - margin.right;
        const height = Math.max(300, leafCount * ROW_HEIGHT);

        svg = d3.select(container)
            .append('svg')
            .attr('width',  containerW)
            .attr('height', height + margin.top + margin.bottom);

        const g = svg.append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        const tree = d3.tree().size([height, width]);
        const root = d3.hierarchy(pruned);
        tree(root);

        // Links
        g.selectAll('.tree-link')
            .data(root.links())
            .enter()
            .append('path')
            .attr('class', 'tree-link')
            .attr('fill', 'none')
            .attr('stroke', '#ccc')
            .attr('stroke-width', 1.5)
            .attr('d', d3.linkHorizontal()
                .x(d => d.y)
                .y(d => d.x));

        // Nodes
        const nodes = g.selectAll('.tree-node')
            .data(root.descendants())
            .enter()
            .append('g')
            .attr('class', 'tree-node')
            .attr('transform', d => `translate(${d.y},${d.x})`)
            .style('cursor', d => d.data.id ? 'pointer' : 'default')
            .on('click', (event, d) => {
                if (d.data.id) selectLanguageFamily(d.data.id);
            });

        // Circles coloured by dominant cluster
        nodes.append('circle')
            .attr('r', d => d.children ? 4 : 5)
            .attr('fill', d => {
                const comp = d.data.cluster_composition;
                if (comp && Object.keys(comp).length > 0) {
                    const dominant = Object.keys(comp).reduce((a, b) =>
                        comp[a] > comp[b] ? a : b);
                    return ColorScheme.getClusterColor(parseInt(dominant));
                }
                return '#bbb';
            })
            .attr('stroke', '#fff')
            .attr('stroke-width', 1);

        // Labels for leaf nodes (right side)
        nodes.filter(d => !d.children)
            .append('text')
            .attr('class', 'tree-label')
            .attr('x', 8)
            .attr('dy', '0.32em')
            .attr('text-anchor', 'start')
            .style('font-size', '10px')
            .style('fill', '#555')
            .text(d => d.data.name || d.data.id || '');

        // Hover highlight
        nodes
            .on('mouseenter', function () {
                d3.select(this).select('circle').attr('r', 7);
            })
            .on('mouseleave', function (event, d) {
                d3.select(this).select('circle').attr('r', d.children ? 4 : 5);
            });

        // Zoom / pan on the SVG
        const zoom = d3.zoom()
            .scaleExtent([0.3, 4])
            .on('zoom', (event) => g.attr('transform', event.transform));
        svg.call(zoom);
    };

    /**
     * Dispatch a language-family-selected event.
     */
    const selectLanguageFamily = (familyId) => {
        document.dispatchEvent(new CustomEvent('languageFamilySelected', {
            detail: { familyId }
        }));
    };

    const highlightCluster = (clusterId) => {
        // TODO: highlight matching nodes
        console.log(`Highlight cluster ${clusterId} on phylo tree`);
    };

    const onResize = () => {
        // Re-render on resize
        init();
    };

    return { init, selectLanguageFamily, highlightCluster, onResize };
})();
