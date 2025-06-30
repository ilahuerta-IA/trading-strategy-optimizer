// In src/static/js/chart.js

import { populateReportData } from './ui.js';

document.addEventListener('DOMContentLoaded', () => {

    // --- State & DOM Elements ---
    let pollingInterval = null;
    const runButton = document.getElementById('runBacktestButton');
    const responseDiv = document.getElementById('responseMessage');
    const pFastD0Input = document.getElementById('p_fast_d0_input');
    const strategyNameInput = document.getElementById('strategyNameInput');

    /**
     * Clears the report area and status messages.
     */
    function clearUI() {
        if (pollingInterval) clearInterval(pollingInterval);
        document.getElementById('reportRunConfig').innerHTML = '';
        document.getElementById('reportPerformanceSummary').innerHTML = '';
        document.getElementById('reportTradeStats').innerHTML = '';
        if (responseDiv) responseDiv.style.display = 'none';
    }

    /**
     * Polls for task status and updates the UI accordingly.
     * @param {string} taskId
     */
    function startPolling(taskId) {
        if (responseDiv) {
            responseDiv.className = 'info'; // Use a neutral style for status messages
            responseDiv.innerText = `Task ${taskId} is queued. Waiting for worker...`;
            responseDiv.style.display = 'block';
        }
        
        // Disable the button while polling is active
        if (runButton) runButton.disabled = true;

        pollingInterval = setInterval(() => {
            fetch(`/api/backtest_status/${taskId}`)
                .then(res => res.json())
                .then(data => {
                    if (responseDiv) {
                        responseDiv.innerText = `Task Status: ${data.status}... (Last checked: ${new Date().toLocaleTimeString()})`;
                    }

                    if (data.status === 'completed' || data.status === 'failed') {
                        // --- Polling is finished ---
                        clearInterval(pollingInterval);
                        pollingInterval = null;
                        
                        // Re-enable the button now that the task is done
                        if (runButton) {
                            runButton.disabled = false;
                            runButton.innerText = 'Run Backtest';
                        }
                        
                        if (data.status === 'completed') {
                            if (responseDiv) {
                                responseDiv.className = 'success';
                                responseDiv.innerText = 'Backtest complete! Report generated below.';
                            }
                            // The result is a string, so we must parse it
                            const results = JSON.parse(data.result_json);
                            populateReportData(results); // Call the UI update function
                        } else { // status === 'failed'
                            if (responseDiv) {
                                responseDiv.className = 'error';
                                responseDiv.innerText = `Error: Backtest failed. Reason: ${data.error_message}`;
                            }
                        }
                    }
                })
                .catch(err => {
                    clearInterval(pollingInterval);
                    if (runButton) {
                        runButton.disabled = false;
                        runButton.innerText = 'Run Backtest';
                    }
                    if (responseDiv) {
                        responseDiv.className = 'error';
                        responseDiv.innerText = 'Polling failed due to a network or server error.';
                    }
                    console.error('Polling error:', err);
                });
        }, 3000); // Poll every 3 seconds
    }

    // --- Main "Run Backtest" Button Listener ---
    if (runButton) {
        runButton.addEventListener('click', () => {
            clearUI();

            const payload = {
                strategy_name: strategyNameInput.value,
                strategy_parameters: { 
                    p_fast_d0: parseInt(pFastD0Input.value, 10), 
                    p_slow_d0: 50, p_fast_d1: 20, p_slow_d1: 50 
                },
                data_files: { 
                    data_path_1: "SPY_5m_1Yea.csv", 
                    data_path_2: "XAUUSD_5m_1Yea.csv" 
                },
            };

            // Provide immediate feedback, but DON'T re-enable the button here
            runButton.disabled = true;
            runButton.innerText = 'Queuing Task...';

            fetch('/api/run_single_backtest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            })
            .then(res => res.ok ? res.json() : Promise.reject(new Error(`Server error: ${res.statusText}`)))
            .then(data => {
                if (data.task_id) {
                    console.log(`Backtest task queued with ID: ${data.task_id}`);
                    startPolling(data.task_id);
                } else {
                    throw new Error(data.message || 'Backend did not return a valid task_id.');
                }
            })
            .catch(error => {
                if (responseDiv) {
                    responseDiv.innerText = `Error: ${error.message}`;
                    responseDiv.className = 'error';
                    responseDiv.style.display = 'block';
                }
                // If submission fails, re-enable the button immediately
                if (runButton) {
                    runButton.disabled = false;
                    runButton.innerText = 'Run Backtest';
                }
                console.error('Submission Error:', error);
            });
        });
    }
});