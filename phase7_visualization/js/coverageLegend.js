/**
 * coverageLegend.js
 * Overlay panel on the globe showing data-coverage breakdown.
 * Clicking a source row highlights that subset on the globe.
 */

const CoverageLegend = (() => {
    const SOURCE_COLORS = {
        dplace: '#e67e22',
        drh:    '#8e44ad',
        seshat: '#2980b9',
    };

    let activeSource = null;
    let el = null;

    const init = () => {
        const container = document.getElementById('globeContainer');
        if (!container) return;

        const stats = DataLoader.getCoverageStats();

        el = document.createElement('div');
        el.id = 'coverageLegend';
        el.className = 'coverage-legend';
        el.innerHTML = buildHTML(stats);

        container.appendChild(el);

        // Toggle collapse
        el.querySelector('#coverageLegendToggle').addEventListener('click', () => {
            const body = el.querySelector('#coverageLegendBody');
            const btn  = el.querySelector('#coverageLegendToggle');
            const collapsed = body.style.display === 'none';
            body.style.display = collapsed ? '' : 'none';
            btn.textContent = collapsed ? '▾' : '▸';
        });

        // Source row clicks → highlight subset on globe
        el.querySelectorAll('.coverage-source-row').forEach(row => {
            row.addEventListener('click', () => {
                const source = row.dataset.source;
                if (activeSource === source) {
                    clearHighlight();
                } else {
                    setHighlight(source, stats);
                    row.classList.add('active');
                }
            });
        });
    };

    const buildHTML = (stats) => {
        const fmt = n => n.toLocaleString();
        return `
            <div class="coverage-legend-header">
                <span class="coverage-legend-title">Data Coverage</span>
                <button id="coverageLegendToggle" class="coverage-legend-toggle">▾</button>
            </div>
            <div id="coverageLegendBody">
                <div class="coverage-row coverage-clustered">
                    <span class="coverage-count">${fmt(stats.clustered)}</span>
                    <span class="coverage-desc">cultures clustered</span>
                </div>
                <div class="coverage-row coverage-unclustered-header">
                    <span class="coverage-count">${fmt(stats.unclustered)}</span>
                    <span class="coverage-desc">insufficient data</span>
                </div>
                <div class="coverage-source-row" data-source="dplace" title="Click to highlight on globe">
                    <span class="coverage-indent">${fmt(stats.counts.dplace)}</span>
                    <span class="coverage-source-label" style="border-left-color:${SOURCE_COLORS.dplace}">D-PLACE — not recorded</span>
                </div>
                <div class="coverage-source-row" data-source="drh" title="Click to highlight on globe">
                    <span class="coverage-indent">${fmt(stats.counts.drh)}</span>
                    <span class="coverage-source-label" style="border-left-color:${SOURCE_COLORS.drh}">DRH — expert unknown</span>
                </div>
                <div class="coverage-source-row" data-source="seshat" title="Click to highlight on globe">
                    <span class="coverage-indent">${fmt(stats.counts.seshat)}</span>
                    <span class="coverage-source-label" style="border-left-color:${SOURCE_COLORS.seshat}">Seshat — outside schema</span>
                </div>
                <div class="coverage-row coverage-global">
                    <span class="coverage-indent">+ 12</span>
                    <span class="coverage-desc">DRH globally distributed</span>
                </div>
            </div>`;
    };

    const setHighlight = (source, stats) => {
        clearHighlight(/* keepActive = */ false);
        activeSource = source;

        el.querySelectorAll('.coverage-source-row').forEach(r => r.classList.remove('active'));
        el.querySelector(`.coverage-source-row[data-source="${source}"]`).classList.add('active');

        const ids = stats.ids[`${source === 'dplace' ? 'dplace_unrecorded' : source === 'drh' ? 'drh_unknown' : 'seshat_schema'}`];
        GlobeVisualization.highlightSubset(ids, SOURCE_COLORS[source]);
    };

    const clearHighlight = () => {
        activeSource = null;
        if (el) el.querySelectorAll('.coverage-source-row').forEach(r => r.classList.remove('active'));
        GlobeVisualization.clearSubsetHighlight();
    };

    return { init, clearHighlight };
})();
