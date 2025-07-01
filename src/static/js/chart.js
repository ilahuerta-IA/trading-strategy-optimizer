// src/static/js/chart.js - DYNAMIC PARAMETER FORM VERSION (COMPLETE)

import { populateReportData } from './ui.js';

document.addEventListener('DOMContentLoaded', () => {
    // --- State & DOM Elements ---
    let pollingInterval = null;
    let strategiesInfo = null; // To store all strategy definitions
    const runButton = document.getElementById('runBacktestButton');
    const responseDiv = document.getElementById('responseMessage');
    const strategyNameInput = document.getElementById('strategyNameInput');
    const paramsContainer = document.getElementById('strategyParamsContainer');

    /**
     * Creates HTML input fields for a strategy's parameters.
     * @param {Array<object>} paramDefinitions - List of parameter definitions from the API.
     */
    function buildParameterForm(paramDefinitions) {
        if (!paramsContainer) return;
        paramsContainer.innerHTML = ''; // Clear "Loading..." or old params

        if (!paramDefinitions || paramDefinitions.length === 0) {
            paramsContainer.innerHTML = '<p style="color: #888;">This strategy has no configurable parameters.</p>';
            return;
        }

        paramDefinitions.forEach(param => {
            const formGroup = document.createElement('div');
            formGroup.className = 'form-group';

            const label = document.createElement('label');
            label.setAttribute('for', `param-${param.name}`);
            label.textContent = `${param.ui_label || param.name}:`;
            
            const input = document.createElement('input');
            input.id = `param-${param.name}`;
            input.name = param.name;
            input.type = (param.type === 'int' || param.type === 'float') ? 'number' : 'text';
            if (input.type === 'number') {
                if (param.step) input.step = param.step;
                if (param.min_value !== null) input.min = param.min_value;
                if (param.max_value !== null) input.max = param.max_value;
            }
            input.value = param.default_value;

            formGroup.appendChild(label);
            formGroup.appendChild(input);
            paramsContainer.appendChild(formGroup);
        });
    }
    
    /**
     * Reads values from all dynamically generated parameter inputs.
     * @returns {object} An object of { parameterName: value }.
     */
    function gatherStrategyParameters() {
        const params = {};
        if (!paramsContainer) return params;

        const inputs = paramsContainer.querySelectorAll('input');
        inputs.forEach(input => {
            const paramName = input.name;
            let value = input.value;
            if (input.type === 'number') {
                value = parseFloat(value);
            }
            params[paramName] = value;
        });
        return params;
    }

    /**
     * Initializes the page by fetching strategy info and building the form.
     */
    function initializePage() {
        const strategyName = strategyNameInput.value;
        if (!strategyName) {
            paramsContainer.innerHTML = '<p style="color: red;">No default strategy is set.</p>';
            return;
        }

        fetch('/api/strategies_info')
            .then(res => res.ok ? res.json() : Promise.reject(new Error(`Server Error: ${res.statusText}`)))
            .then(data => {
                strategiesInfo = data.strategies; // Store the array of strategies
                const targetStrategy = strategiesInfo.find(s => s.name === strategyName);
                
                if (targetStrategy && targetStrategy.parameters) {
                    buildParameterForm(targetStrategy.parameters);
                } else {
                    paramsContainer.innerHTML = `<p style="color: red;">Could not find parameters for strategy: ${strategyName}</p>`;
                }
            })
            .catch(error => {
                console.error("Error fetching strategy info:", error);
                paramsContainer.innerHTML = `<p style="color: red;">Failed to load strategy parameters from the server.</p>`;
            });
    }

    /**
     * Clears the UI of previous results and status messages.
     */
    function clearUI() {
        if (pollingInterval) clearInterval(pollingInterval);
        document.getElementById('reportRunConfig').innerHTML = '';
        document.getElementById('reportPerformanceSummary').innerHTML = '';
        document.getElementById('reportTradeStats').innerHTML = '';
        if (responseDiv) responseDiv.style.display = 'none';
    }

    /**
     * Polls the backend for task status and displays the report on completion.
     * @param {string} taskId - The unique ID of the backtest task.
     */
    function startPolling(taskId) {
        if (responseDiv) {
            responseDiv.className = 'info';
            responseDiv.innerText = `Task ${taskId} queued. Polling for status...`;
            responseDiv.style.display = 'block';
        }
        
        if (runButton) runButton.disabled = true;

        pollingInterval = setInterval(() => {
            fetch(`/api/backtest_status/${taskId}`)
                .then(res => res.json())
                .then(data => {
                    if (responseDiv) responseDiv.innerText = `Task Status: ${data.status}...`;
                    
                    if (data.status === 'completed' || data.status === 'failed') {
                        clearInterval(pollingInterval);
                        pollingInterval = null;
                        
                        if (runButton) {
                            runButton.disabled = false;
                            runButton.innerText = 'Run Backtest';
                        }
                        
                        if (data.status === 'completed') {
                            if (responseDiv) {
                                responseDiv.className = 'success';
                                responseDiv.innerText = 'Backtest complete! Report generated below.';
                            }
                            const results = JSON.parse(data.result_json);
                            populateReportData(results);
                        } else {
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
        }, 3000);
    }

    // --- Main "Run Backtest" Button Listener ---
    if (runButton) {
        runButton.addEventListener('click', () => {
            clearUI();

            const strategyParameters = gatherStrategyParameters();

            const payload = {
                strategy_name: strategyNameInput.value,
                strategy_parameters: strategyParameters,
                data_files: { 
                    data_path_1: "SPY_5m_1Yea.csv", 
                    data_path_2: "XAUUSD_5m_1Yea.csv" 
                },
            };

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
                if (runButton) {
                    runButton.disabled = false;
                    runButton.innerText = 'Run Backtest';
                }
                console.error('Submission Error:', error);
            });
        });
    }
    
    // Initialize the form when the page loads
    initializePage();
});