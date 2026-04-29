/**
 * dataLoader.js
 * Load and cache JSON data from Phase 6 analysis outputs
 */

const DataLoader = (() => {
    let culturesData = null;
    let analysisResults = null;
    let clusterProfiles = null;
    let phyloTree = null;
    let distanceMatrices = null;

    const isLoaded = () => {
        return culturesData !== null;
    };

    /**
     * Load all data files
     * @returns {Promise<void>}
     */
    const loadAll = async () => {
        try {
            console.log('Loading Phase 7 data files...');

            const [cultures, analysis, clusters, phylo, matrices] = await Promise.all([
                fetch('data/cultures_metadata.json').then(r => r.json()),
                fetch('data/analysis_results.json').then(r => r.json()),
                fetch('data/cluster_profiles.json').then(r => r.json()),
                fetch('data/phylo_tree.json').then(r => r.json()),
                fetch('data/distance_matrices.json').then(r => r.json())
            ]);

            culturesData = cultures;
            analysisResults = analysis;
            clusterProfiles = clusters;
            phyloTree = phylo;
            distanceMatrices = matrices;

            console.log(`✓ Loaded ${cultures.metadata.total_cultures} cultures`);
            console.log(`✓ Loaded analysis results for ${cultures.metadata.total_clusters} clusters`);
            
            return true;
        } catch (error) {
            console.error('Error loading data:', error);
            throw error;
        }
    };

    /**
     * Get all cultures
     * @returns {Array} Array of culture objects
     */
    const getCultures = () => {
        return culturesData?.cultures || [];
    };

    /**
     * Get specific culture by ID
     * @param {string} cultureId - Culture ID
     * @returns {Object} Culture object
     */
    const getCultureById = (cultureId) => {
        return culturesData?.cultures.find(c => c.id === cultureId);
    };

    /**
     * Get cultures by cluster
     * @param {number} clusterId - Cluster ID
     * @returns {Array} Array of cultures in the cluster
     */
    const getCulturesByCluster = (clusterId) => {
        return culturesData?.cultures.filter(c => c.cluster === clusterId) || [];
    };

    /**
     * Get cultures by feature
     * @param {string} featureName - Feature name
     * @param {number} value - Feature value (1 for presence, 0 for absence)
     * @returns {Array} Array of cultures with the feature
     */
    const getCulturesByFeature = (featureName, value = 1) => {
        return culturesData?.cultures.filter(c => c.features[featureName] === value) || [];
    };

    /**
     * Get cultures by language family
     * @param {string} languageFamily - Language family name
     * @returns {Array} Array of cultures in the family
     */
    const getCulturesByLanguageFamily = (languageFamily) => {
        if (languageFamily === '' || languageFamily === undefined) return culturesData?.cultures || [];
        return culturesData?.cultures.filter(c => c.language_family === languageFamily) || [];
    };

    /**
     * Get metadata about the dataset
     * @returns {Object} Metadata object
     */
    const getMetadata = () => {
        return culturesData?.metadata || {};
    };

    /**
     * Get all unique features
     * @returns {Array} Array of feature names
     */
    const getFeatureNames = () => {
        if (!culturesData?.cultures || culturesData.cultures.length === 0) return [];
        const featureSet = new Set();
        culturesData.cultures.forEach(culture => {
            Object.keys(culture.features).forEach(feature => featureSet.add(feature));
        });
        return Array.from(featureSet).sort();
    };

    /**
     * Get statistics for a feature
     * @param {string} featureName - Feature name
     * @returns {Object} Statistics object
     */
    const getFeatureStats = (featureName) => {
        const cultures = getCultures();
        const withFeature = cultures.filter(c => c.features[featureName] === 1).length;
        const totalCultures = cultures.length;
        const percentage = ((withFeature / totalCultures) * 100).toFixed(1);

        // By cluster
        const byCluster = {};
        for (let clusterId = 0; clusterId < 8; clusterId++) {
            const clusterCultures = getCulturesByCluster(clusterId);
            const withFeatureInCluster = clusterCultures.filter(c => c.features[featureName] === 1).length;
            byCluster[clusterId] = clusterCultures.length > 0
                ? ((withFeatureInCluster / clusterCultures.length) * 100).toFixed(1)
                : 0;
        }

        return {
            feature: featureName,
            presence_count: withFeature,
            total_cultures: totalCultures,
            percentage,
            by_cluster: byCluster
        };
    };

    /**
     * Get analysis results
     * @returns {Object} Analysis results object
     */
    const getAnalysisResults = () => {
        return analysisResults || {};
    };

    /**
     * Get Moran's I for a feature
     * @param {string} featureName - Feature name
     * @returns {Object} Moran's I result
     */
    const getModransI = (featureName) => {
        const morans = analysisResults?.morans_i || [];
        return morans.find(m => m.feature === featureName);
    };

    /**
     * Get cluster profiles
     * @returns {Array} Array of cluster profile objects
     */
    const getClusterProfiles = () => {
        return clusterProfiles?.profiles || [];
    };

    /**
     * Get phylogenetic tree
     * @returns {Object} Phylogenetic tree structure
     */
    const getPhyloTree = () => {
        return phyloTree || {};
    };

    /**
     * Get all unique language families
     * @returns {Array} Array of language family names
     */
    const getLanguageFamilies = () => {
        const families = new Set();
        culturesData?.cultures.forEach(c => {
            if (c.language_family && c.language_family !== 'unknown') {
                families.add(c.language_family);
            }
        });
        return Array.from(families).sort();
    };

    /**
     * Get cultures with no geographic coordinates (globally distributed).
     * @returns {Array}
     */
    const getGloballyDistributed = () => {
        return culturesData?.cultures.filter(c => c.lat === null || c.lon === null) || [];
    };

    /**
     * Compute coverage breakdown for the Coverage Legend.
     * Returns counts for each category of unclusterable culture.
     * @returns {Object}
     */
    const getCoverageStats = () => {
        const cultures = culturesData?.cultures || [];
        const clustered   = cultures.filter(c => c.cluster !== null && c.cluster !== undefined);
        const unclustered = cultures.filter(c => c.cluster === null || c.cluster === undefined);

        // Globally distributed = no coordinates (regardless of cluster status)
        const noCoords = cultures.filter(c => c.lat === null || c.lon === null);

        // Unclustered WITH coordinates, by source
        const unclusteredWithCoords = unclustered.filter(c => c.lat !== null && c.lon !== null);
        const bySource = {};
        unclusteredWithCoords.forEach(c => {
            bySource[c.source] = (bySource[c.source] || []);
            bySource[c.source].push(c.id);
        });

        // Count total unclustered by source (for display in legend)
        const unclusteredCount = {};
        unclustered.forEach(c => {
            unclusteredCount[c.source] = (unclusteredCount[c.source] || 0) + 1;
        });

        return {
            total: cultures.length,
            clustered: clustered.length,
            unclustered: unclustered.length,
            noCoords: noCoords.length,
            counts: {
                dplace: unclusteredCount['dplace'] || 0,
                drh:    unclusteredCount['drh']    || 0,
                seshat: unclusteredCount['seshat'] || 0,
            },
            // IDs for globe highlighting (only cultures with coordinates)
            ids: {
                dplace_unrecorded: (bySource['dplace'] || []),
                drh_unknown:       (bySource['drh']    || []),
                seshat_schema:     (bySource['seshat'] || []),
            }
        };
    };

    return {
        loadAll,
        isLoaded,
        getCultures,
        getCultureById,
        getCulturesByCluster,
        getCulturesByFeature,
        getCulturesByLanguageFamily,
        getMetadata,
        getFeatureNames,
        getFeatureStats,
        getAnalysisResults,
        getModransI,
        getClusterProfiles,
        getPhyloTree,
        getLanguageFamilies,
        getGloballyDistributed,
        getCoverageStats
    };
})();
