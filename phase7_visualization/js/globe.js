/**
 * globe.js
 * Switchable 2D/3D globe wrapper
 */

const GlobeVisualization = (() => {
    let mode = '3d';
    let active = Globe3D;

    const setMode = (nextMode) => {
        mode = nextMode === '2d' ? '2d' : '3d';
        active = mode === '2d' ? Globe2D : Globe3D;
    };

    const init = async () => {
        await active.init();
    };

    const plotCultures = (cultures) => active.plotCultures(cultures);
    const animate = () => active.animate();
    const filterByFeature = (featureName) => active.filterByFeature(featureName);
    const filterByCluster = (clusterId) => active.filterByCluster(clusterId);
    const filterByLanguageFamily = (languageFamily) => active.filterByLanguageFamily(languageFamily);
    const resetFilters = () => active.resetFilters();
    const highlightSubset = (ids, color) => active.highlightSubset(ids, color);
    const clearSubsetHighlight = () => active.clearSubsetHighlight();
    const getSelectedCultures = () => active.getSelectedCultures();
    const getFilters = () => active.getFilters();

    return {
        init,
        setMode,
        plotCultures,
        animate,
        filterByFeature,
        filterByCluster,
        filterByLanguageFamily,
        resetFilters,
        highlightSubset,
        clearSubsetHighlight,
        getSelectedCultures,
        getFilters
    };
})();
