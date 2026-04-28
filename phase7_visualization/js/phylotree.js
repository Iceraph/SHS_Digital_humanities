/**
 * phylotree.js
 * D3.js phylogenetic tree visualization
 */

const PhylogenicTreeVisualization = (() => {
    const container = document.getElementById('phyloTree');
    let svg, tree, root;

    const width = container.clientWidth || 400;
    const height = container.clientHeight || 400;
    const margin = { top: 10, right: 10, bottom: 10, left: 10 };

    /**
     * Initialize phylogenetic tree visualization
     */
    const init = () => {
        // Create SVG
        svg = d3.select('#phyloTree')
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        // Create tree layout
        tree = d3.tree().size([height - margin.top - margin.bottom, width - margin.left - margin.right]);

        // Load and display tree
        const phyloData = DataLoader.getPhyloTree();
        if (phyloData && phyloData.name) {
            displayTree(phyloData);
        } else {
            displayPlaceholder();
        }
    };

    /**
     * Display the phylogenetic tree
     */
    const displayTree = (data) => {
        // Convert to hierarchy
        root = d3.hierarchy(data);

        // Calculate tree layout
        const treeData = tree(root);

        // Create group for translations
        const g = svg.append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        // Draw links
        const links = g.selectAll('.tree-link')
            .data(treeData.links())
            .enter()
            .append('path')
            .attr('class', 'tree-link')
            .attr('d', d3.linkVertical()
                .x(d => d.y)
                .y(d => d.x));

        // Draw nodes
        const nodes = g.selectAll('.tree-node')
            .data(treeData.descendants())
            .enter()
            .append('g')
            .attr('class', 'tree-node')
            .attr('transform', d => `translate(${d.y},${d.x})`);

        // Add circles for nodes
        nodes.append('circle')
            .attr('r', d => d.children ? 4 : 6)
            .attr('fill', d => {
                if (d.data.cluster_composition && Object.keys(d.data.cluster_composition).length > 0) {
                    // Color by dominant cluster
                    const clusters = d.data.cluster_composition;
                    const dominant = Object.keys(clusters).reduce((a, b) => 
                        clusters[a] > clusters[b] ? a : b
                    );
                    return ColorScheme.getClusterColor(parseInt(dominant));
                }
                return '#999';
            })
            .on('click', (event, d) => {
                if (d.data.id) {
                    selectLanguageFamily(d.data.id);
                }
            });

        // Add labels for leaf nodes
        nodes.filter(d => !d.children)
            .append('text')
            .attr('class', 'tree-label')
            .attr('x', 10)
            .attr('text-anchor', 'start')
            .text(d => d.data.name)
            .style('font-size', '10px');

        // Add interaction
        addTreeInteraction(g, nodes);
    };

    /**
     * Add interactive features to tree
     */
    const addTreeInteraction = (g, nodes) => {
        // Hover effect
        nodes.on('mouseenter', function() {
            d3.select(this).select('circle').attr('r', 7);
        })
        .on('mouseleave', function() {
            d3.select(this).select('circle').attr('r', d => d.children ? 4 : 6);
        });

        // Optional: Add zoom/pan behavior
        const zoom = d3.zoom()
            .on('zoom', (event) => {
                g.attr('transform', event.transform);
            });
        
        svg.call(zoom);
    };

    /**
     * Display placeholder tree (for stub data)
     */
    const displayPlaceholder = () => {
        const g = svg.append('g')
            .attr('transform', `translate(${width / 2},${height / 2})`);

        g.append('text')
            .attr('text-anchor', 'middle')
            .attr('dy', '0.3em')
            .style('font-size', '14px')
            .style('fill', '#999')
            .text('Phylogenetic tree data loading...');
    };

    /**
     * Select a language family
     */
    const selectLanguageFamily = (familyId) => {
        console.log(`Selected language family: ${familyId}`);
        
        document.dispatchEvent(new CustomEvent('languageFamilySelected', {
            detail: { familyId }
        }));
    };

    /**
     * Highlight languages in a cluster
     */
    const highlightCluster = (clusterId) => {
        // TODO: Implement cluster highlighting on tree
        console.log(`Highlighting cluster ${clusterId} on tree`);
    };

    /**
     * Update tree layout on resize
     */
    const onResize = () => {
        // TODO: Implement responsive resizing
    };

    return {
        init,
        selectLanguageFamily,
        highlightCluster,
        onResize
    };
})();
