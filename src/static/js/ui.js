/**
 * Safely formats a value for the report table.
 * @param {*} value - The value to format.
 * @param {number} precision - The number of decimal places for numbers.
 * @param {string} suffix - A suffix to add (e.g., '%', ' bars').
 * @returns {string} The formatted string.
 */
function formatValue(value, precision = 2, suffix = '') {
    // Handle null, undefined, or empty string
    if (value === null || value === undefined || value === '') {
        return 'N/A';
    }
    
    // Convert string numbers to actual numbers
    if (typeof value === 'string') {
        const parsed = parseFloat(value);
        if (!isNaN(parsed)) {
            return `${parsed.toFixed(precision)}${suffix}`;
        } else {
            return 'N/A';
        }
    }
    
    // Handle actual numbers
    if (typeof value === 'number' && !isNaN(value) && isFinite(value)) {
        return `${value.toFixed(precision)}${suffix}`;
    }
    
    // For anything else, return N/A
    return 'N/A';
}

/**
 * Safely formats a count/integer value.
 * @param {*} value - The value to format.
 * @returns {string|number} The formatted value or 'N/A'.
 */
function formatCount(value) {
    if (value === null || value === undefined) {
        return 'N/A';
    }
    
    // Convert string numbers to integers
    if (typeof value === 'string') {
        const parsed = parseInt(value, 10);
        return !isNaN(parsed) ? parsed : 'N/A';
    }
    
    // Handle actual numbers
    if (typeof value === 'number' && !isNaN(value) && isFinite(value)) {
        return Math.round(value);
    }
    
    return 'N/A';
}

/**
 * Safely formats a percentage value.
 * @param {*} value - The value to format (should be in decimal, e.g., 0.05 = 5%).
 * @param {number} precision - Decimal places.
 * @returns {string} The formatted percentage.
 */
function formatPercentage(value, precision = 2) {
    const formatted = formatValue(value, precision);
    return formatted === 'N/A' ? 'N/A' : `${formatted}%`;
}

/**
 * Populates the backtest report with data from the results.
 * @param {Object} resultsData - The backtest results object.
 */
export function populateReportData(resultsData) {
    console.log("UI: Starting report population with data:", resultsData);
    
    const reportRunConfigDiv = document.getElementById('reportRunConfig');
    const reportPerfDiv = document.getElementById('reportPerformanceSummary');
    const reportTradeStatsDiv = document.getElementById('reportTradeStats');
    
    // Clear existing content
    if (reportRunConfigDiv) reportRunConfigDiv.innerHTML = '';
    if (reportPerfDiv) reportPerfDiv.innerHTML = '';
    if (reportTradeStatsDiv) reportTradeStatsDiv.innerHTML = '';
    
    // Extract data safely with fallbacks
    const runConfig = resultsData.run_config_summary || {};
    const metrics = resultsData.metrics || {};
    const tradeAnalyzer = metrics.tradeanalyzer || {};
    const drawdown = metrics.drawdown || {};
    const sharpe = metrics.sharpe || {};
    const sqn = metrics.sqn || {};
    
    console.log("UI: Extracted metrics:", { tradeAnalyzer, drawdown, sharpe, sqn });

    // --- Run Configuration Section ---
    if (reportRunConfigDiv && runConfig && Object.keys(runConfig).length > 0) {
        let configHtml = '<h3>Run Configuration</h3><table class="report-table">'; // Use a table for better alignment
        
        configHtml += `<tr><td>Strategy</td><td>${runConfig.strategy_name || 'N/A'}</td></tr>`;
        configHtml += `<tr><td>Start Date</td><td>${runConfig.fromdate || 'N/A'}</td></tr>`;
        configHtml += `<tr><td>End Date</td><td>${runConfig.todate || 'N/A'}</td></tr>`;
        configHtml += `<tr><td>Initial Cash</td><td>$${formatValue(runConfig.initial_cash)}</td></tr>`; // Using your formatValue function
        
        // Show parameters if available
        if (runConfig.parameters && Object.keys(runConfig.parameters).length > 0) {
            // Use <pre> for nice JSON formatting
            configHtml += `<tr><td>Parameters</td><td><pre>${JSON.stringify(runConfig.parameters, null, 2)}</pre></td></tr>`;
        }
        
        configHtml += '</table>';
        reportRunConfigDiv.innerHTML = configHtml;
        console.log("UI: ✅ Run configuration populated");
    }

    // --- Performance Summary Section ---
    if (reportPerfDiv && Object.keys(metrics).length > 0) {
        let summaryHtml = '<h3>Performance Summary</h3><table class="report-table">';
        
        // Use safe navigation and formatting
        const totalPnL = tradeAnalyzer.pnl?.net?.total;
        const maxDD = drawdown.max?.drawdown;
        const sharpeRatio = sharpe?.sharperatio;
        const sqnValue = sqn?.sqn;
        
        summaryHtml += `<tr><td><strong>Total Net PnL</strong></td><td>$${formatValue(totalPnL)}</td></tr>`;
        summaryHtml += `<tr><td><strong>Max Drawdown</strong></td><td>${formatPercentage(maxDD)}</td></tr>`;
        summaryHtml += `<tr><td><strong>Sharpe Ratio</strong></td><td>${formatValue(sharpeRatio, 3)}</td></tr>`;
        summaryHtml += `<tr><td><strong>SQN</strong></td><td>${formatValue(sqnValue, 3)}</td></tr>`;
        
        // Additional metrics if available
        const totalReturn = tradeAnalyzer.pnl?.net?.total;
        const winRate = tradeAnalyzer.won?.total && tradeAnalyzer.total?.closed 
            ? (tradeAnalyzer.won.total / tradeAnalyzer.total.closed) * 100 
            : null;
        
        if (winRate !== null) {
            summaryHtml += `<tr><td><strong>Win Rate</strong></td><td>${formatPercentage(winRate / 100)}</td></tr>`;
        }
        
        summaryHtml += '</table>';
        reportPerfDiv.innerHTML = summaryHtml;
        console.log("UI: ✅ Performance summary populated");
    }

    // --- Trade Statistics Section ---
    if (reportTradeStatsDiv && Object.keys(tradeAnalyzer).length > 0) {
        let statsHtml = '<h3>Trade Statistics</h3><table class="report-table">';
        
        // Basic trade counts
        statsHtml += `<tr><td><strong>Total Closed Trades</strong></td><td>${formatCount(tradeAnalyzer.total?.closed)}</td></tr>`;
        statsHtml += `<tr><td><strong>Winning Trades</strong></td><td>${formatCount(tradeAnalyzer.won?.total)}</td></tr>`;
        statsHtml += `<tr><td><strong>Losing Trades</strong></td><td>${formatCount(tradeAnalyzer.lost?.total)}</td></tr>`;
        
        // PnL statistics
        const avgWin = tradeAnalyzer.won?.pnl?.average;
        const avgLoss = tradeAnalyzer.lost?.pnl?.average;
        const maxWin = tradeAnalyzer.won?.pnl?.max;
        const maxLoss = tradeAnalyzer.lost?.pnl?.max;
        
        statsHtml += `<tr><td><strong>Average Win</strong></td><td>$${formatValue(avgWin)}</td></tr>`;
        statsHtml += `<tr><td><strong>Average Loss</strong></td><td>$${formatValue(avgLoss)}</td></tr>`;
        statsHtml += `<tr><td><strong>Largest Win</strong></td><td>$${formatValue(maxWin)}</td></tr>`;
        statsHtml += `<tr><td><strong>Largest Loss</strong></td><td>$${formatValue(maxLoss)}</td></tr>`;
        
        // Streak statistics
        const longestWinStreak = tradeAnalyzer.streak?.won?.longest;
        const longestLossStreak = tradeAnalyzer.streak?.lost?.longest;
        
        statsHtml += `<tr><td><strong>Longest Winning Streak</strong></td><td>${formatCount(longestWinStreak)}</td></tr>`;
        statsHtml += `<tr><td><strong>Longest Losing Streak</strong></td><td>${formatCount(longestLossStreak)}</td></tr>`;
        
        // Trade length statistics
        const avgLength = tradeAnalyzer.len?.average;
        const maxLength = tradeAnalyzer.len?.max;
        
        statsHtml += `<tr><td><strong>Average Trade Length</strong></td><td>${formatValue(avgLength, 1, ' bars')}</td></tr>`;
        statsHtml += `<tr><td><strong>Longest Trade</strong></td><td>${formatValue(maxLength, 0, ' bars')}</td></tr>`;
        
        statsHtml += '</table>';
        reportTradeStatsDiv.innerHTML = statsHtml;
        console.log("UI: ✅ Trade statistics populated");
    }

    console.log("UI: ✅ Report population completed successfully");
}

/**
 * Clears all report sections.
 */
export function clearReportData() {
    const reportSections = ['reportRunConfig', 'reportPerformanceSummary', 'reportTradeStats'];
    reportSections.forEach(sectionId => {
        const element = document.getElementById(sectionId);
        if (element) element.innerHTML = '';
    });
    console.log("UI: Cleared all report sections");
}