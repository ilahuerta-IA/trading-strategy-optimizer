/**
 * Populates the backtest report section of the page with data fetched from the server.
 * @param {object} reportData - The report data object.
 */
export function populateReportData(reportData) {
    const reportRunConfigDiv = document.getElementById('reportRunConfig');
    const reportPerformanceSummaryDiv = document.getElementById('reportPerformanceSummary');
    const reportTradeStatsDiv = document.getElementById('reportTradeStats');

    if (!reportRunConfigDiv || !reportPerformanceSummaryDiv || !reportTradeStatsDiv) {
        console.error("Report divs not found!");
        return;
    }
    
    // Clear previous report data
    reportRunConfigDiv.innerHTML = '';
    reportPerformanceSummaryDiv.innerHTML = '';
    reportTradeStatsDiv.innerHTML = '';

    // Populate Strategy Parameters
    if (reportData.run_config) {
        let configHtml = '<div class="report-section"><h3>Strategy Parameters</h3><dl>';
        for (const [key, value] of Object.entries(reportData.run_config)) {
            configHtml += `<dt>${key}</dt><dd>${typeof value === 'object' ? JSON.stringify(value, null, 2) : value}</dd>`;
        }
        configHtml += '</dl></div>';
        reportRunConfigDiv.innerHTML = configHtml;
    }

    // Populate Performance Summary
    const perfData = reportData.value_analysis || reportData.performance_summary;
    if (perfData) {
        let summaryHtml = '<div class="report-section"><h3>Performance Summary</h3><table>';
        for (const [key, value] of Object.entries(perfData)) {
            summaryHtml += `<tr><td>${key.replace(/_/g, ' ')}</td><td>${typeof value === 'number' ? value.toFixed(2) : value}</td></tr>`;
        }
        summaryHtml += '</table></div>';
        reportPerformanceSummaryDiv.innerHTML = summaryHtml;
    }

    // Populate Trade Stats
    const tradeData = reportData.metrics_report || reportData.trade_stats;
    if (tradeData) {
        let statsHtml = '<div class="report-section"><h3>Trade Statistics</h3><table>';
        for (const [key, value] of Object.entries(tradeData)) {
            statsHtml += `<tr><td>${key.replace(/_/g, ' ')}</td><td>${typeof value === 'number' ? value.toFixed(2) : value}</td></tr>`;
        }
        statsHtml += '</table></div>';
        reportTradeStatsDiv.innerHTML = statsHtml;
    }
}