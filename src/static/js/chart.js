import { populateReportData } from './ui.js';

// Ensure the DOM is fully loaded before running the script
document.addEventListener('DOMContentLoaded', () => {
    let mainChart;
    let data0CandlestickSeries;
    let data1Chart;
    let data1CandlestickSeries;

    const mainChartContainer = document.getElementById('mainChartContainer');
    const data1ChartContainer = document.getElementById('data1ChartContainer');
    const subchartsAreaDiv = document.getElementById('subchartsArea');
    const loadingDiv = document.getElementById('loading');
    
    const allChartObjectsForSync = [];
    let subchartInstances = {};

    /**
     * Assigns a specific color based on keywords in the indicator's name.
     * @param {string} seriesKey - The identifier for the indicator series (e.g., 'sma_fast_d0_sma').
     * @returns {string} A hex color code.
     */
    function getIndicatorColor(seriesKey) {
        const lowerKey = seriesKey.toLowerCase();
        if (lowerKey.includes('fast')) {
            return '#FFD700'; // Yellow/Gold for fast SMAs
        }
        if (lowerKey.includes('slow')) {
            return '#FFA500'; // Orange for slow SMAs
        }
        // Fallback for any other indicators
        return '#f4a261';
    }

    function getOrCreateSubchart(paneId, paneTitle) {
        if (!subchartInstances[paneId]) {
            const subchartDiv = document.createElement('div');
            subchartDiv.id = `subchart_pane_${paneId}`;
            subchartDiv.className = 'chart-pane';
            subchartDiv.style.height = '25vh';
            subchartDiv.style.marginBottom = '10px';
            subchartDiv.style.display = 'flex';
            subchartDiv.style.flexDirection = 'column';
            // subchartDiv.style.backgroundColor = '#131722'; // REMOVED: This will be handled by CSS

            const titleElement = document.createElement('h4');
            titleElement.textContent = paneTitle;
            titleElement.style.color = '#D9D9D9';
            titleElement.style.margin = '5px 0 5px 10px';
            titleElement.style.fontSize = '0.9em';
            titleElement.style.flexShrink = '0';
            subchartDiv.appendChild(titleElement);

            const chartContainer = document.createElement('div');
            chartContainer.style.width = '100%';
            chartContainer.style.flexGrow = '1';
            subchartDiv.appendChild(chartContainer);
            
            subchartsAreaDiv.appendChild(subchartDiv);

            const chart = LightweightCharts.createChart(chartContainer, {
                width: chartContainer.offsetWidth,
                height: chartContainer.offsetHeight,
                layout: { background: { color: '#131722' }, textColor: '#D9D9D9', fontSize: 11, fontFamily: 'Trebuchet MS' },
                grid: { vertLines: { color: '#2B2B43' }, horzLines: { color: '#2B2B43' } },
                timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#484848' },
                crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
                rightPriceScale: { borderColor: '#484848' },
            });
            allChartObjectsForSync.push(chart);
            subchartInstances[paneId] = { chart: chart, div: subchartDiv, titleElement: titleElement, chartContainer: chartContainer };
        }
        return subchartInstances[paneId];
    }

    function resizeAllCharts() {
        if (mainChart) {
            mainChart.resize(mainChartContainer.offsetWidth, mainChartContainer.offsetHeight);
        }
        if (data1Chart) {
            data1Chart.resize(data1ChartContainer.offsetWidth, data1ChartContainer.offsetHeight);
        }
        Object.values(subchartInstances).forEach(subEntry => {
            if (subEntry && subEntry.chart && subEntry.chartContainer) {
                subEntry.chart.resize(subEntry.chartContainer.offsetWidth, subEntry.chartContainer.offsetHeight);
            }
        });
    }

    window.addEventListener('resize', resizeAllCharts);

    fetch('/api/chart_data')
        .then(response => response.json())
        .then(data => {
            console.log('Raw data from /api/chart_data:', data);

            // Main chart (data0)
            if (data.data0_ohlc && data.data0_ohlc.length > 0) {
                mainChart = LightweightCharts.createChart(mainChartContainer, {
                    width: mainChartContainer.offsetWidth,
                    height: mainChartContainer.offsetHeight,
                    layout: { background: { color: '#131722' }, textColor: '#D9D9D9', fontSize: 11, fontFamily: 'Trebuchet MS' },
                    grid: { vertLines: { color: '#2B2B43' }, horzLines: { color: '#2B2B43' } },
                    timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#484848' },
                    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
                    rightPriceScale: { borderColor: '#484848' },
                });
                allChartObjectsForSync.push(mainChart);
                data0CandlestickSeries = mainChart.addCandlestickSeries({
                    upColor: '#26A69A', downColor: '#EF5350',
                    wickUpColor: '#26A69A', wickDownColor: '#EF5350',
                    borderVisible: false,
                });
                data0CandlestickSeries.setData(data.data0_ohlc);
            }

            // Data1 chart
            if (data.data1_ohlc && data.data1_ohlc.length > 0 && data1ChartContainer) {
                data1Chart = LightweightCharts.createChart(data1ChartContainer, {
                    width: data1ChartContainer.offsetWidth,
                    height: data1ChartContainer.offsetHeight,
                    layout: { background: { color: '#131722' }, textColor: '#D9D9D9', fontSize: 11, fontFamily: 'Trebuchet MS' },
                    grid: { vertLines: { color: '#2B2B43' }, horzLines: { color: '#2B2B43' } },
                    timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#484848' },
                    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
                    rightPriceScale: { borderColor: '#484848' },
                });
                allChartObjectsForSync.push(data1Chart);
                data1CandlestickSeries = data1Chart.addCandlestickSeries({
                    upColor: '#26A69A', downColor: '#EF5350',
                    wickUpColor: '#26A69A', wickDownColor: '#EF5350',
                    borderVisible: false,
                });
                data1CandlestickSeries.setData(data.data1_ohlc);
            }

            // Plot indicators
            if (data.indicator_series) {
                Object.keys(data.indicator_series).forEach(seriesKey => {
                    if (seriesKey === 'd1_close_line_close') return;
                    const seriesData = data.indicator_series[seriesKey];
                    if (!seriesData || !Array.isArray(seriesData) || seriesData.length === 0) return;

                    let targetChart;
                    if (seriesKey.includes('_d0_') || seriesKey.includes('data0')) {
                        targetChart = mainChart;
                    } else if (seriesKey.includes('_d1_') || seriesKey.includes('data1')) {
                        targetChart = data1Chart;
                    } else {
                        const displayName = seriesKey.replace(/_/g, ' ');
                        const subchartEntry = getOrCreateSubchart(seriesKey, displayName);
                        targetChart = subchartEntry.chart;
                    }

                    if (targetChart) {
                        const lineSeries = targetChart.addLineSeries({
                            color: getIndicatorColor(seriesKey),
                            lineWidth: 1, // Adjusted for better visibility
                            title: seriesKey.replace(/_/g, ' ')
                        });
                        lineSeries.setData(seriesData);
                    }
                });
            }

            // Portfolio Value
            const portfolioData = data.portfolio_value_line || data.portfolio_value;
            if (portfolioData && portfolioData.length > 0) {
                const subchartEntry = getOrCreateSubchart('portfolio_value', 'Portfolio Value');
                const portfolioSeries = subchartEntry.chart.addLineSeries({
                    color: '#E0E0E0', // Use a distinct light color for portfolio
                    lineWidth: 1, // Adjusted for better visibility
                    title: 'Portfolio Value'
                });
                portfolioSeries.setData(portfolioData);
            }

            // Trade Markers
            if (data.trade_signals) {
                if (data0CandlestickSeries) {
                    const data0Markers = data.trade_signals
                        .filter(s => !s.data_feed || s.data_feed === 'data0')
                        .map(s => ({ time: s.time, position: s.type === 'buy' ? 'belowBar' : 'aboveBar', color: s.type === 'buy' ? '#26A69A' : '#EF5350', shape: s.type === 'buy' ? 'arrowUp' : 'arrowDown', text: s.type === 'buy' ? 'B' : 'S' }));
                    data0CandlestickSeries.setMarkers(data0Markers);
                }
                if (data1CandlestickSeries) {
                    const data1Markers = data.trade_signals
                        .filter(s => s.data_feed === 'data1')
                        .map(s => ({ time: s.time, position: s.type === 'buy' ? 'belowBar' : 'aboveBar', color: s.type === 'buy' ? '#26A69A' : '#EF5350', shape: s.type === 'buy' ? 'arrowUp' : 'arrowDown', text: s.type === 'buy' ? 'B' : 'S' }));
                    data1CandlestickSeries.setMarkers(data1Markers);
                }
            }

            // Sync charts
            allChartObjectsForSync.forEach(chart => {
                chart.timeScale().subscribeVisibleLogicalRangeChange(timeRange => {
                    allChartObjectsForSync.forEach(otherChart => {
                        if (otherChart !== chart) otherChart.timeScale().setVisibleLogicalRange(timeRange);
                    });
                });
                chart.subscribeCrosshairMove(param => {
                    allChartObjectsForSync.forEach(otherChart => {
                        if (otherChart !== chart) otherChart.setCrosshairPosition(param.point ? param.point.x : -1, param.point ? param.point.y : -1, param.seriesPrices, param.time);
                    });
                });
            });

            // Fit content
            if (mainChart) mainChart.timeScale().fitContent();
            if (data1Chart) data1Chart.timeScale().fitContent();
            Object.values(subchartInstances).forEach(sub => sub.chart.timeScale().fitContent());

            loadingDiv.style.display = 'none';

            // Populate Report
            if (data.report_data) {
                populateReportData(data.report_data);
            }

            // Initial resize
            setTimeout(() => resizeAllCharts(), 100);
        })
        .catch(error => {
            loadingDiv.innerText = 'Failed to load chart data. Check console.';
            console.error('Error fetching or processing chart data:', error);
        });
});

// Add this code within a DOMContentLoaded event listener or at the end of your existing script

document.addEventListener('DOMContentLoaded', function() {
    // Get DOM elements
    const runButton = document.getElementById('runBacktestButton');
    const responseDiv = document.getElementById('responseMessage');
    const pFastD0Input = document.getElementById('p_fast_d0_input');
    const strategyNameInput = document.getElementById('strategyNameInput');

    if (runButton) {
        runButton.addEventListener('click', () => {
            console.log('--- FRONTEND: Run Backtest Button Clicked ---');
            
            // 1. Get user input
            const pFastD0Value = parseInt(pFastD0Input.value, 10);
            const strategyName = strategyNameInput.value;

            console.log(`Frontend Input - Strategy: ${strategyName}, p_fast_d0: ${pFastD0Value}`);

            // Basic validation on the frontend
            if (isNaN(pFastD0Value) || pFastD0Value <= 0) {
                responseDiv.innerText = 'Error: Please enter a valid, positive number for the MA Period.';
                responseDiv.className = 'error';
                responseDiv.style.display = 'block';
                return;
            }

            // 2. Construct the JSON payload
            const payload = {
                strategy_name: strategyName,
                strategy_parameters: {
                    p_fast_d0: pFastD0Value,
                    // Add other default parameters if your strategy needs them
                    p_slow_d0: 50,
                    p_fast_d1: 20,
                    p_slow_d1: 50
                },
                // Include other top-level keys with default values
                data_files: {
                    data_path_1: "SPY_5m_1Yea.csv", // Use a default for this test
                    data_path_2: "XAUUSD_5m_1Yea.csv"
                },
                date_range: {
                    fromdate: "2023-01-01",
                    todate: "2023-12-31"
                }
            };

            console.log('Frontend Payload to send:', payload);

            // 3. Provide UI feedback
            runButton.disabled = true;
            runButton.innerText = 'Sending Request...';
            responseDiv.style.display = 'none'; // Hide old messages

            // 4. Send the request
            fetch('/api/run_single_backtest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            })
            .then(response => {
                console.log('Frontend: Response status:', response.status);
                if (!response.ok) {
                    // Handle HTTP errors like 400 or 500
                    return response.json().then(err => { throw err; });
                }
                return response.json();
            })
            .then(data => {
                console.log('Frontend: Response from backend:', data);
                // Display success message
                responseDiv.innerText = `Success: ${data.message} | Task ID: ${data.task_id}`;
                responseDiv.className = 'success';
                responseDiv.style.display = 'block';
            })
            .catch(error => {
                console.error('Frontend: Error:', error);
                // Display error message, using the message from the backend if available
                responseDiv.innerText = `Error: ${error.message || 'A network error occurred.'}`;
                responseDiv.className = 'error';
                responseDiv.style.display = 'block';
            })
            .finally(() => {
                // This block will run whether the fetch succeeded or failed
                runButton.disabled = false;
                runButton.innerText = 'Run Backtest (Test)';
                console.log('--- FRONTEND: Request completed ---');
            });
        });
    }
});