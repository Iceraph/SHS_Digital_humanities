/**
 * colorScheme.js
 * Cluster color mapping and color scheme management
 */

const ColorScheme = (() => {
    const clusterColors = {
        0: '#e74c3c',  // Red
        1: '#3498db',  // Blue
        2: '#2ecc71',  // Green
        3: '#f39c12',  // Orange
        4: '#9b59b6',  // Purple
        5: '#1abc9c',  // Teal
        6: '#e67e22',  // Dark Orange
        7: '#34495e'   // Dark Gray
    };

    const inactiveColor = '#bdc3c7';  // Gray for inactive/filtered-out

    /**
     * Get color for a specific cluster
     * @param {number} clusterId - Cluster ID
     * @returns {string} Hex color code
     */
    const getClusterColor = (clusterId) => {
        return clusterColors[clusterId] || inactiveColor;
    };

    /**
     * Get all cluster colors
     * @returns {object} Map of cluster ID to color
     */
    const getAllColors = () => {
        return { ...clusterColors };
    };

    /**
     * Get color with opacity
     * @param {number} clusterId - Cluster ID
     * @param {number} opacity - Opacity value (0-1)
     * @returns {string} RGBA color
     */
    const getClusterColorWithOpacity = (clusterId, opacity = 0.7) => {
        const hex = clusterColors[clusterId] || inactiveColor;
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${opacity})`;
    };

    /**
     * Get inactive color
     * @returns {string} Hex color code
     */
    const getInactiveColor = () => {
        return inactiveColor;
    };

    return {
        getClusterColor,
        getAllColors,
        getClusterColorWithOpacity,
        getInactiveColor
    };
})();
