// src/static/js/chart.js - WITH DYNAMIC DATE PICKERS

import { populateReportData } from './ui.js';

document.addEventListener('DOMContentLoaded', () => {
    // --- State & DOM Elements ---
    let pollingInterval = null;
    let strategiesInfo = null;
    const runButton = document.getElementById('runBacktestButton');
    const responseDiv = document.getElementById('responseMessage');
    const strategyNameInput = document.getElementById('strategyNameInput');
    const paramsContainer = document.getElementById('strategyParamsContainer');
    const dataFile1Select = document.getElementById('dataFile1Select');
    const dataFile2Select = document.getElementById('dataFile2Select');
    const fromDateInput = document.getElementById('fromDateInput');
    const toDateInput = document.getElementById('toDateInput');

    /**
     * Populates a <select> dropdown with a list of filenames.
     * @param {HTMLSelectElement} selectElement The dropdown element.
     * @param {Array<string>} fileList The list of filenames.
     */
    function populateDataFileDropdown(selectElement, fileList) {
        if (!selectElement) return;
        selectElement.innerHTML = ''; // Clear "Loading..."

        if (!fileList || fileList.length === 0) {
            selectElement.innerHTML = '<option value="">No data files found</option>';
            return;
        }

        fileList.forEach(fileName => {
            const option = document.createElement('option');
            option.value = fileName;
            option.textContent = fileName;
            selectElement.appendChild(option);
        });
    }

    /**
     * Fetches the date range for a given file and updates the date pickers.
     * @param {string} filename The selected data file name.
     */
    function updateDatePickersForFile(filename) {
        if (!filename || !fromDateInput || !toDateInput) return;

        fetch(`/api/data_file_info/${filename}`)
            .then(res => res.ok ? res.json() : Promise.reject('File info not found'))
            .then(data => {
                if (data.start_date && data.end_date) {
                    // Set the min, max, and current values of the date pickers
                    fromDateInput.min = data.start_date;
                    fromDateInput.max = data.end_date;
                    fromDateInput.value = data.start_date; // Default to start of data

                    toDateInput.min = data.start_date;
                    toDateInput.max = data.end_date;
                    toDateInput.value = data.end_date;   // Default to end of data
                }
            })
            .catch(error => {
                console.error(`Error fetching date range for ${filename}:`, error);
                // Clear the date pickers on error
                fromDateInput.value = '';
                toDateInput.value = '';
            });
    }

    /**
     * Creates HTML input fields for a strategy's parameters.
     * @param {Array<object>} paramDefinitions - List of parameter definitions from the API.
     */
    function buildParameterForm(paramDefinitions) {
        if (!paramsContainer) return;
        paramsContainer.innerHTML = '';

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
            let value = input.value;
            if (input.type === 'number') {
                value = parseFloat(value);
            }
            params[input.name] = value;
        });
        return params;
    }

    /**
     * The `initializePage` function now needs to trigger the date fetch.
     */
    function initializePage() {
        // Fetch and populate Strategy Parameters
        const strategyName = strategyNameInput.value;
        if (strategyName) {
            fetch('/api/strategies_info')
                .then(res => res.ok ? res.json() : Promise.reject(new Error(`Server Error: ${res.statusText}`)))
                .then(data => {
                    strategiesInfo = data.strategies;
                    const targetStrategy = strategiesInfo.find(s => s.name === strategyName);
                    if (targetStrategy && targetStrategy.parameters) {
                        buildParameterForm(targetStrategy.parameters);
                    } else {
                        paramsContainer.innerHTML = `<p style="color: red;">Could not find parameters for strategy: ${strategyName}</p>`;
                    }
                })
                .catch(error => {
                    console.error("Error fetching strategy info:", error);
                    paramsContainer.innerHTML = `<p style="color: red;">Failed to load strategy parameters.</p>`;
                });
        } else {
             paramsContainer.innerHTML = '<p style="color: red;">No default strategy is set.</p>';
        }

        // Fetch Data Files and set up the listener
        fetch('/api/data_files')
            .then(res => res.ok ? res.json() : Promise.reject(new Error('Failed to load data files')))
            .then(fileList => {
                populateDataFileDropdown(dataFile1Select, fileList);
                populateDataFileDropdown(dataFile2Select, fileList);
                
                if (fileList.includes("SPY_5m_1Yea.csv")) {
                    dataFile1Select.value = "SPY_5m_1Yea.csv";
                }
                if (fileList.includes("XAUUSD_5m_1Yea.csv")) {
                    dataFile2Select.value = "XAUUSD_5m_1Yea.csv";
                }

                // --- After populating, fetch dates for the initially selected file ---
                if (dataFile1Select.value) {
                    updateDatePickersForFile(dataFile1Select.value);
                }

                // --- Add an event listener to update dates when the user changes the primary file ---
                dataFile1Select.addEventListener('change', (event) => {
                    updateDatePickersForFile(event.target.value);
                });
            })
            .catch(error => {
                console.error("Error fetching data files:", error);
                const errorMsg = '<option value="">Error loading files</option>';
                if (dataFile1Select) dataFile1Select.innerHTML = errorMsg;
                if (dataFile2Select) dataFile2Select.innerHTML = errorMsg;
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
            
            // --- Get ALL form values ---
            const strategyParameters = gatherStrategyParameters();
            const selectedDataFile1 = dataFile1Select.value;
            const selectedDataFile2 = dataFile2Select.value;
            const fromDate = fromDateInput.value;
            const toDate = toDateInput.value;

            if (!selectedDataFile1 || !selectedDataFile2) {
                if (responseDiv) {
                    responseDiv.innerText = "Please select data files for both Data Path 1 and Data Path 2.";
                    responseDiv.className = 'error';
                    responseDiv.style.display = 'block';
                }
                return;
            }

            // --- Construct the payload ---
            const payload = {
                strategy_name: strategyNameInput.value,
                strategy_parameters: strategyParameters,
                data_files: { 
                    data_path_1: selectedDataFile1, 
                    data_path_2: selectedDataFile2 
                },
                date_range: {
                    fromdate: fromDate,
                    todate: toDate
                }
            };
            
            console.log("Submitting complete payload:", payload);

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