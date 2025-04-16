<!DOCTYPE html>
<html lang="en"> <!-- Changed lang to en -->
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Plan: Quantitative Trading Bot ("IntoTheMirror" Optimized) & Analysis Platform</title> <!-- Changed title to English -->
    <style>
        body { font-family: sans-serif; line-height: 1.6; padding: 20px; max-width: 900px; margin: auto; }
        h1, h2, h3 { color: #2c3e50; border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; }
        h1 { text-align: center; }
        h2 { margin-top: 30px; color: #16a085; }
        h3 { margin-top: 20px; color: #2980b9; border-bottom: none; }
        ul { list-style-type: disc; margin-left: 20px; }
        li { margin-bottom: 10px; }
        strong { color: #c0392b; }
        code { background-color: #ecf0f1; padding: 2px 5px; border-radius: 3px; font-family: monospace; }
        .tool { font-weight: bold; color: #8e44ad; }
        .objective { font-style: italic; color: #7f8c8d; margin-bottom: 15px; }
        nav { background-color: #f8f9f9; padding: 15px; border-radius: 5px; margin-bottom: 30px; border: 1px solid #ecf0f1; }
        nav ul { list-style-type: none; padding: 0; margin: 0; }
        nav li { display: inline-block; margin-right: 15px; }
        nav a { text-decoration: none; color: #2980b9; font-weight: bold; }
        nav a:hover { color: #16a085; }
        .phase-box { border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; border-radius: 5px; background-color: #fff; }
        .task-done { text-decoration: line-through; color: grey; }
        .tool-link { text-decoration: none; color: #8e44ad; }
        .tool-link:hover { text-decoration: underline; }
        .rationale { background-color: #fdf2e9; border-left: 3px solid #e67e22; padding: 10px; margin-top: 5px; font-size: 0.9em; }
        .research-link { font-size: 0.8em; margin-left: 10px; }
        .data-handling-note { font-weight: bold; color: #d35400; } /* Highlight data handling change */
    </style>
</head>
<body>

    <h1>Project Plan: Quantitative Trading Bot ("IntoTheMirror" Optimized) & Analysis Platform</h1> <!-- English -->

    <p><strong>Overview:</strong> Develop a robust system for quantitative trading strategy backtesting, optimization, and eventual execution. Focus on multi-asset/multi-timeframe analysis and robustness. Structured for open-source contribution (GitHub) and potential deployment of an analysis tool on Streamlit Community Cloud.</p> <!-- English -->

    <nav>
        <h3>Quick Navigation:</h3> <!-- English -->
        <ul>
            <li><a href="#hito-1">Milestone -1: Data Preprocessing & Release</a></li> <!-- Renamed & English -->
            <li><a href="#hito0">Milestone 0: Foundation (Backtrader + Plotly)</a></li> <!-- English -->
            <li><a href="#hito1">Milestone 1: Optimization (W&B Sweeps)</a></li> <!-- English -->
            <li><a href="#hito2">Milestone 2: Interface (Streamlit)</a></li> <!-- English -->
            <li><a href="#hito3">Milestone 3: Execution (MT5 Bot)</a></li> <!-- English -->
            <li><a href="#hito4">Milestone 4 (Optional): ML Refinement (PyTorch)</a></li> <!-- English -->
            <li><a href="#opensource">Open Source Aspects</a></li> <!-- English -->
            <li><a href="#priorart">Similar Projects & Alternatives</a></li> <!-- English -->
        </ul>
    </nav>

    <!-- NEW Milestone for Data Preprocessing -->
    <div id="hito-1" class="phase-box">
        <h2>Milestone -1: Data Preprocessing & Release</h2>
        <p class="objective">Prepare and aggregate historical data (from M1 source) into common timeframes and make them available via GitHub Releases.</p>
        <h3>Key Tools:</h3>
        <p><span class="tool">Python</span>, <span class="tool">Pandas</span>, <span class="tool">QuantDataManager</span> (or other data source), <span class="tool">GitHub</span>.</p>
        <p class="rationale"><strong>Rationale:</strong> Pre-calculating timeframes drastically improves backtesting and Streamlit app performance. Using GitHub Releases keeps the main repository lean and provides a standard way to distribute data artifacts.</p>
        <h3>Main Tasks:</h3>
        <ul>
            <li><strong>-1.1. Obtain M1 Data:</strong> Download high-quality M1 (or lowest available TF) data for the initial set of ~5 assets using QuantDataManager.</li>
            <li><strong>-1.2. Develop Preprocessing Script:</strong> Create a script (`scripts/preprocess_data.py`) that:
                <ul>
                    <li>Loads an M1 CSV/Parquet file using Pandas.</li>
                    <li>Performs necessary cleaning (if any).</li>
                    <li>Uses `pandas.resample()` to aggregate M1 data into target timeframes (e.g., M5, M15, H1). Ensure correct aggregation logic (Open=first, High=max, Low=min, Close=last, Volume=sum).</li>
                    <li>Saves the aggregated data into separate files (e.g., `XAUUSD_H1.parquet`, `SPX500_M15.parquet`). **Parquet or Feather format is highly recommended for performance.**</li>
                </ul>
            </li>
            <li><strong>-1.3. Generate Processed Files:</strong> Run the script for all initial assets and desired timeframes.</li>
            <li><strong>-1.4. Create GitHub Release:</strong>
                <ul>
                    <li>Go to your GitHub repository page -> Releases -> "Draft a new release".</li>
                    <li>Create a tag (e.g., `v0.1.0-data` or `initial-data`).</li>
                    <li>Give it a title (e.g., "Initial Preprocessed Data Files").</li>
                    <li>Upload the generated `.parquet` (or `.csv`/`.zip`) files as release assets.</li>
                    <li>Publish the release.</li>
                    <li>**Note down the base URL for downloading these assets.**</li>
                </ul>
            </li>
            <li><strong>-1.5. Document Data Acquisition:</strong> Update `README.md` to explain where the demo data comes from (the Release) and how users can preprocess their *own* data using the provided script or guidelines.</li>
        </ul>
    </div>
    <!-- END NEW Milestone -->

    <div id="hito0" class="phase-box">
        <!-- Title and Objective remain similar -->
        <h2>Milestone 0: Foundation - Backtesting Engine & Visualization</h2>
        <p class="objective">Establish a solid Python foundation using Backtrader to run parametric multi-asset/multi-timeframe strategies (using preprocessed data) and Plotly for interactive dual visualization.</p>
        <!-- Tools remain similar -->
        <h3>Key Tools:</h3>
         <p>
            <span class="tool">Python</span>, <span class="tool">Pandas</span>, <span class="tool">NumPy</span>,
            <a href="https://github.com/twopirllc/pandas-ta" target="_blank" class="tool-link tool">Pandas TA</a> / <a href="https://mrjbq7.github.io/ta-lib/" target="_blank" class="tool-link tool">TA-Lib</a>,
            <a href="https://www.backtrader.com/" target="_blank" class="tool-link tool">Backtrader</a>,
            <a href="https://plotly.com/python/" target="_blank" class="tool-link tool">Plotly</a>,
            <a href="https://git-scm.com/" target="_blank" class="tool-link tool">Git</a>,
            <span class="tool">Requests</span> (for data download).
        </p>
        <p class="rationale"><strong>Rationale:</strong> Backtrader for flexibility, Plotly for custom visualization, preprocessed data (from Release) for performance.</p>
        <h3>Main Tasks:</h3>
        <ul>
            <li><strong>0.1. Environment Setup:</strong> (Assumed done) Install dependencies, setup project structure, init Git.</li>
            <li><strong class="data-handling-note">0.2. Data Loading Module (`src/data_handling/data_loader.py`):</strong>
                <ul>
                    <li>Implement function `load_or_download_data(asset_tf_filename, release_url_base, cache_dir="cached_data")` (similar to previous example using `requests` and caching) to get data files from the GitHub Release URL.</li>
                    <li>Adapt `add_data_feeds` function:
                        <ul>
                           <li>It now takes target `asset`, `tf`, `name` as input.</li>
                           <li>Calls `load_or_download_data` to get the file path.</li>
                           <li>Loads the data using `pd.read_parquet` (or csv).</li>
                           <li>Feeds the resulting Pandas DataFrame to Backtrader using `bt.feeds.PandasData(dataname=dataframe, ...)`.</li>
                        </ul>
                    </li>
                    <li>Modify the main backtesting script to call `add_data_feeds` for the specific assets/TFs needed for *that particular backtest run*.</li>
                </ul>
            </li>
            <li><strong>0.3. Indicators in Backtrader:</strong> (Remains the same) Implement indicators.</li>
            <li><strong>0.4. Strategy Multi-Asset Parametric (`bt.Strategy`):</strong> (Remains the same) Implement strategy logic accessing `self.datas[0]`, `self.datas[1]`, etc.</li>
            <li><strong>0.5. Backtesting and Metrics:</strong> (Remains the same) Configure Cerebro, add analyzers, run, extract metrics.</li>
            <li><strong>0.6. Dual Visualization with Plotly:</strong> (Remains the same) Create function `plot_dual_backtest` using Plotly.</li>
            <li><strong>0.7. Manual Validation:</strong> (Remains the same) Run manually, verify logic and plots.</li>
        </ul>
    </div>

     <div id="hito1" class="phase-box">
        <h2>Milestone 1: Systematic Optimization with W&B Sweeps</h2>
        <p class="objective">Automate the search for optimal parameters of the multi-asset strategy using HPO and OOS validation.</p>
        <!-- Tools remain similar -->
        <h3>Key Tools:</h3>
        <p> <a href="https://wandb.ai/site" target="_blank" class="tool-link tool">Weights & Biases (W&B) Sweeps</a>, <span class="tool">Python</span>, <span class="tool">Backtrader</span>, <a href="https://colab.research.google.com/" target="_blank" class="tool-link tool">Google Colab</a> / <a href="https://www.kaggle.com/" target="_blank" class="tool-link tool">Kaggle</a>.</p>
        <p class="rationale"><strong>Rationale:</strong> W&B Sweeps for powerful Bayesian optimization and result tracking.</p>
         <h3>Main Tasks:</h3>
         <ul>
            <li><strong>1.1. Prepare Script for HPO (`sweep_runner.py`):</strong>
                <ul>
                    <li>Import necessary modules (`wandb`, backtrader, data loader).</li>
                    <li>Define function `run_backtest_for_sweep(config)`:
                        <ul>
                            <li>Takes `config` dict from W&B.</li>
                            <li>Determines which assets/TFs are needed based on `config`.</li>
                            <li>Calls `load_or_download_data` for required IS data files (from GitHub Release).</li>
                            <li>Configures and runs Backtrader Cerebro **ONLY on IS data** with parameters from `config`.</li>
                            <li>Returns IS metrics dict.</li>
                        </ul>
                    </li>
                     <li>Define `train_wandb()`:
                        <ul>
                            <li>`wandb.init()`.</li>
                            <li>Calls `run_backtest_for_sweep(wandb.config)`.</li>
                            <li>`wandb.log(metrics_is)`.</li>
                        </ul>
                    </li>
                </ul>
            </li>
            <!-- Tasks 1.2, 1.3, 1.4 remain conceptually the same, focusing on defining the YAML, running agents, and critical OOS validation -->
             <li><strong>1.2. Define Sweep Configuration (YAML):</strong> Create `sweep_config.yaml` (method, metric IS, parameters).</li>
             <li><strong>1.3. Execute HPO Agents:</strong> Launch `wandb agent`s.</li>
             <li><strong>1.4. Analyze Results & OOS Validation:</strong> Use W&B UI, run top N configs on OOS data (downloading OOS data if needed, maybe from a separate release or file naming convention), select robust configurations, save params.</li>
        </ul>
    </div>

    <div id="hito2" class="phase-box">
        <h2>Milestone 2: Streamlit Analysis Interface</h2>
        <p class="objective">Create an interactive web application for in-depth analysis and simulation of optimized strategies.</p>
         <!-- Tools remain similar -->
         <h3>Key Tools:</h3>
         <p><a href="https://streamlit.io/" target="_blank" class="tool-link tool">Streamlit</a>, <span class="tool">Plotly</span>, <span class="tool">Pandas</span>, <span class="tool">Backtrader</span>, <span class="tool">Requests</span>.</p>
        <p class="rationale"><strong>Rationale:</strong> Streamlit for easy UI creation, leveraging previous components for fast analysis.</p>
        <h3>Main Tasks:</h3>
        <ul>
            <li><strong>2.1. Configuration & Data Loading:</strong>
                <ul>
                    <li>Function to load saved optimal parameter configurations (JSON/YAML).</li>
                    <li>Integrate the `load_or_download_data` function to fetch necessary data files (IS and OOS) from the GitHub Release based on user selection (asset/TF).</li>
                </ul>
            </li>
            <li><strong>2.2. Develop Streamlit App (`app.py`):</strong>
                <ul>
                    <li>UI for selecting asset(s), timeframe(s), and a saved optimal configuration.</li>
                    <li>Widgets to potentially tweak parameters slightly for sensitivity analysis.</li>
                    <li>Button to trigger the backtest run (using the loaded data and Backtrader engine).</li>
                    <li>Display key IS and OOS metrics clearly.</li>
                    <li>Embed the interactive Plotly dual chart using `st.plotly_chart`.</li>
                </ul>
            </li>
            <li><strong>2.3. Deployment (Optional):</strong> Deploy to Streamlit Community Cloud.</li>
        </ul>
    </div>

    <!-- Hito 3, 4, Open Source, Prior Art sections remain conceptually the same -->
    <div id="hito3" class="phase-box">
        <h2>Milestone 3: MT5 Bot (Execution)</h2>
        <p class="objective">Implement the execution of the optimized and validated strategy on the MetaTrader 5 platform.</p>
         <h3>Key Tools:</h3>
        <p><span class="tool">Python</span>, Library <a href="https://pypi.org/project/MetaTrader5/" target="_blank" class="tool-link tool">MetaTrader5</a>.</p>
         <p class="rationale"><strong>Rationale:</strong> Use the official MT5 library for direct Python integration.</p>
       <h3>Main Tasks:</h3>
       <ul>
            <li><strong>3.1. MT5 Connection Module</strong></li>
            <li><strong>3.2. MT5 Data Module</strong></li>
            <li><strong>3.3. MT5 Order Execution Module</strong> (implementing risk rules)</li>
            <li><strong>3.4. Main Bot Script</strong> (loading optimal params, applying strategy logic)</li>
            <li><strong>3.5. Demo Testing & Deployment</strong></li>
       </ul>
    </div>

    <div id="hito4" class="phase-box">
        <h2>Milestone 4 (Optional Advanced): ML Refinement (PyTorch)</h2>
       <p class="objective"><strong>(Consider AFTER completing Milestones 0-2/3)</strong> Explore if an ML model can enhance the signals from the optimized strategy.</p>
       <h3>Key Tools:</h3>
        <p><span class="tool">PyTorch</span>, <span class="tool">PyTorch Lightning</span>, <span class="tool">W&B</span>.</p>
        <p class="rationale"><strong>Rationale:</strong> Introduce ML for potential improvements, building upon a robust, optimized foundation.</p>
        <h3>Possible Approach (Signal Filtering):</h3>
         <ul>
             <li>Generate ML dataset (X=features pre-signal, y=signal outcome).</li>
             <li>Train classifier model using PyTorch Lightning.</li>
             <li>Integrate model to filter signals in Milestone 2 or 3.</li>
         </ul>
    </div>

    <div id="opensource" class="phase-box">
        <h2>Open Source & Community Aspects</h2>
         <ul>
            <li>Maintain public GitHub repo with clear documentation (`README.md`, MIT License).</li>
            <li>Add contribution guidelines (`CONTRIBUTING.md`) and use Issues.</li>
            <li>Sharing the Streamlit App (Milestone 2) is key for community engagement.</li>
            <li>**Update README to clearly explain data requirements and point to GitHub Releases for demo data.**</li>
        </ul>
    </div>

     <div id="priorart" class="phase-box">
        <h2>Similar Projects & Alternatives</h2>
        <!-- Links remain the same -->
        <p>Based on DeepResearch:</p>
         <ul>
            <li><a href="https://github.com/mementum/backtrader" target="_blank" class="research-link">Backtrader</a>: Chosen base framework.</li>
            <li><a href="https://github.com/aloyszius/btester" target="_blank" class="research-link">btester</a> / <a href="https://github.com/alpha-observer/TradePruf" target="_blank" class="research-link">TradePruf</a>: Alternatives reviewed.</li>
            <li><a href="https://github.com/topics/metatrader5-python" target="_blank" class="research-link">Python-MT5 Integrations</a>: Options to explore for Hito 3.</li>
            <!-- ... other links ... -->
        </ul>
        <p><strong>Action:</strong> Continue using Backtrader as planned, leveraging external tools (Plotly, W&B, Streamlit, MT5 lib) for specific functionalities.</p>
    </div>

    <!-- Explanation of GitHub Releases vs Codespaces -->
    <div id="github-features" class="phase-box">
        <h2>Understanding GitHub Releases vs. Codespaces</h2>
        <p class="objective">Clarifying the purpose of these two distinct GitHub features.</p>
        <h3>GitHub Releases</h3>
        <ul>
            <li><strong>Purpose:</strong> Primarily used for **distributing specific versions (releases) of your software and associated artifacts**. This includes compiled binaries, documentation packages, source code archives, and importantly for us, **data files** needed to run a specific version.</li>
            <li><strong>Mechanism:</strong> You manually create a "Release" linked to a Git tag (e.g., `v1.0`). You then upload files (like your `.parquet` data) directly to that release page. GitHub hosts these files and provides stable download URLs.</li>
            <li><strong>Use Case Here:</strong> **Ideal for hosting your pre-processed data files (`.parquet`, `.csv`).** Users (or your Streamlit app) can download the data corresponding to a specific project version directly from the release assets URL. It has generous free storage limits suitable for this purpose.</li>
        </ul>
         <h3>GitHub Codespaces</h3>
        <ul>
            <li><strong>Purpose:</strong> Provides a complete, cloud-based **development environment**. It's essentially a virtual machine (container) in the cloud with VS Code (web or desktop), your repository cloned, and dependencies set up, allowing you to **code, run, test, and debug your project** directly in the cloud without complex local setup.</li>
            <li><strong>Mechanism:</strong> Configured typically via a `.devcontainer/devcontainer.json` file in your repository. When you launch a codespace, GitHub provisions the container, installs specified tools/extensions, and gives you access via a browser or VS Code remote connection.</li>
            <li><strong>Use Case Here:</strong> Useful for **you or contributors** to quickly get a working development environment for coding on the project itself (writing Python code for Backtrader, Streamlit, etc.). It is **NOT** primarily intended for distributing final data artifacts to end-users of your application. A Codespace would still need to *download* the data from GitHub Releases (or clone it if small) to run the backtests.</li>
             <li><strong>Cost:</strong> Has a monthly free quota (core-hours), after which it becomes a paid service.</li>
        </ul>
        <p class="rationale"><strong>Conclusion for Data:</strong> For making your pre-processed data files available for your Streamlit app and other users, **GitHub Releases** is the correct and recommended tool.</p>

    </div>


</body>
</html>