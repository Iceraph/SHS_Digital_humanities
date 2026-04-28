/**
 * main.js
 * Main application entry point and event orchestration
 */

document.addEventListener('DOMContentLoaded', async () => {
    console.log('Starting Phase 7 Visualization Application...');

    try {
        // Step 1: Load all data
        console.log('Step 1: Loading data...');
        await DataLoader.loadAll();
        console.log('✓ Data loaded');

        // Step 2: Initialize visualization components
        console.log('Step 2: Initializing visualizations...');
        
        // Initialize globe
        GlobeVisualization.init();
        console.log('✓ Globe initialized');

        // Initialize phylogenetic tree
        PhylogenicTreeVisualization.init();
        console.log('✓ Phylogenetic tree initialized');

        // Initialize feature panel
        FeaturePanel.init();
        console.log('✓ Feature panel initialized');

        // Initialize cluster interaction
        ClusterInteraction.init();
        console.log('✓ Cluster interaction initialized');

        // Step 3: Plot initial data
        console.log('Step 3: Plotting data...');
        const cultures = DataLoader.getCultures();
        GlobeVisualization.plotCultures(cultures);
        console.log(`✓ Plotted ${cultures.length} cultures`);

        // Step 4: Start animation loop
        GlobeVisualization.animate();

        // Step 5: Setup cross-component event handling
        setupEventHandling();

        console.log('\n✓✓✓ Application ready ✓✓✓\n');
        console.log('Current interactions:');
        console.log('  - Search and select features in left panel');
        console.log('  - Click cultures on globe for details');
        console.log('  - Click cluster colors in legend to highlight/isolate');
        console.log('  - Use filters to explore specific clusters or language families');
        console.log('  - Click phylogenetic tree nodes to filter');

    } catch (error) {
        console.error('✗ Application initialization failed:', error);
        displayError(error);
    }
});

/**
 * Setup event listeners for cross-component communication
 */
function setupEventHandling() {
    // Culture selection event
    document.addEventListener('cultureSelected', (event) => {
        const { culture, selectedCount } = event.detail;
        console.log(`Culture selected: ${culture.name} (${selectedCount} total)`);
    });

    // Language family selection event
    document.addEventListener('languageFamilySelected', (event) => {
        const { familyId } = event.detail;
        console.log(`Language family selected: ${familyId}`);
        
        // Could update globe filter here
        GlobeVisualization.filterByLanguageFamily(familyId);
    });

    // Handle window resize
    window.addEventListener('resize', () => {
        GlobeVisualization.init();
    });
}

/**
 * Display error message to user
 */
function displayError(error) {
    const container = document.getElementById('globeContainer');
    container.innerHTML = `
        <div style="
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            flex-direction: column;
            color: #d32f2f;
            text-align: center;
            padding: 20px;
        ">
            <h3>Application Error</h3>
            <p>${error.message}</p>
            <details style="margin-top: 20px; text-align: left;">
                <summary>Stack trace</summary>
                <pre style="
                    background-color: #f5f5f5;
                    padding: 10px;
                    border-radius: 4px;
                    overflow-x: auto;
                    font-size: 12px;
                ">${error.stack}</pre>
            </details>
        </div>
    `;
}

/**
 * Utility: Parse URL query parameters
 */
function getQueryParam(param) {
    const params = new URLSearchParams(window.location.search);
    return params.get(param);
}

/**
 * Utility: Log application state
 */
function logApplicationState() {
    console.log('=== APPLICATION STATE ===');
    console.log('Data loaded:', DataLoader.isLoaded());
    console.log('Total cultures:', DataLoader.getCultures().length);
    console.log('Total features:', DataLoader.getFeatureNames().length);
    console.log('Cluster filters:', GlobeVisualization.getFilters());
    console.log('Selected feature:', FeaturePanel.getSelectedFeature());
    console.log('========================');
}

// Make utilities globally available for debugging
window.AppDebug = {
    logState: logApplicationState,
    DataLoader,
    GlobeVisualization,
    FeaturePanel,
    PhylogenicTreeVisualization
};
