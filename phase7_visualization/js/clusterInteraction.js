/**
 * clusterInteraction.js
 * Interactive cluster filtering and highlighting
 */

const ClusterInteraction = (() => {
    const legendContainer = document.getElementById('clusterLegend');
    let selectedCluster = null;

    /**
     * Initialize cluster legend and interactions
     */
    const init = () => {
        renderLegend();
    };

    /**
     * Render interactive cluster legend
     */
    const renderLegend = () => {
        legendContainer.innerHTML = '';

        for (let i = 0; i < 8; i++) {
            const color = ColorScheme.getClusterColor(i);
            const item = document.createElement('div');
            item.className = 'cluster-legend-item';
            item.style.display = 'flex';
            item.style.alignItems = 'center';
            item.style.padding = '8px';
            item.style.margin = '4px 0';
            item.style.borderRadius = '4px';
            item.style.cursor = 'pointer';
            item.style.userSelect = 'none';
            item.style.transition = 'background-color 0.2s';

            // Color box
            const box = document.createElement('div');
            box.style.width = '16px';
            box.style.height = '16px';
            box.style.backgroundColor = color;
            box.style.borderRadius = '2px';
            box.style.marginRight = '8px';
            box.style.border = '1px solid rgba(0,0,0,0.2)';

            // Label
            const label = document.createElement('span');
            label.textContent = `Cluster ${i}`;
            label.style.fontSize = '12px';
            label.style.color = '#333';

            item.appendChild(box);
            item.appendChild(label);

            // Click handler
            item.addEventListener('click', () => toggleCluster(i));
            item.addEventListener('mouseenter', () => {
                item.style.backgroundColor = 'rgba(0,0,0,0.05)';
            });
            item.addEventListener('mouseleave', () => {
                item.style.backgroundColor = selectedCluster === i ? 'rgba(0,0,0,0.1)' : 'transparent';
            });

            legendContainer.appendChild(item);
        }

        console.log('✓ Interactive cluster legend rendered');
    };

    /**
     * Toggle cluster highlight
     */
    const toggleCluster = (clusterId) => {
        if (selectedCluster === clusterId) {
            // Click same cluster again to deselect
            selectedCluster = null;
            resetGlobeOpacity();
        } else {
            // Select new cluster
            selectedCluster = clusterId;
            highlightCluster(clusterId);
        }

        // Update legend visual
        updateLegendVisuals();
    };

    /**
     * Highlight a specific cluster on the globe
     */
    const highlightCluster = (clusterId) => {
        // This will be called by GlobeVisualization to apply opacity
        const event = new CustomEvent('clusterHighlight', {
            detail: { cluster: clusterId }
        });
        document.dispatchEvent(event);

        console.log(`Highlighting cluster ${clusterId}`);
    };

    /**
     * Reset globe opacity to normal
     */
    const resetGlobeOpacity = () => {
        const event = new CustomEvent('clusterHighlight', {
            detail: { cluster: null }
        });
        document.dispatchEvent(event);

        console.log('Resetting cluster highlight');
    };

    /**
     * Update legend visual state
     */
    const updateLegendVisuals = () => {
        const items = legendContainer.querySelectorAll('.cluster-legend-item');
        items.forEach((item, idx) => {
            if (selectedCluster === idx) {
                item.style.backgroundColor = 'rgba(0,0,0,0.1)';
                item.style.borderLeft = '3px solid #333';
                item.style.paddingLeft = '5px';
            } else {
                item.style.backgroundColor = 'transparent';
                item.style.borderLeft = 'none';
                item.style.paddingLeft = '8px';
            }
        });
    };

    /**
     * Get currently selected cluster
     */
    const getSelectedCluster = () => selectedCluster;

    return {
        init,
        toggleCluster,
        highlightCluster,
        resetGlobeOpacity,
        getSelectedCluster
    };
})();
