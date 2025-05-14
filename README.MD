
```markdown
# Python Backtesting & Analysis Platform

## Overview

This project provides a comprehensive Python-based framework for backtesting and analyzing quantitative trading strategies. It utilizes **Backtrader** as its core backtesting engine, offering robust simulation capabilities. The platform features two main interfaces for visualization and interaction:

1.  A **Command-Line Interface (CLI)** for running backtests with detailed console output, capable of generating static Matplotlib plots and interactive HTML charts using `lightweight-charts-python`.
2.  A **Web Application** built with **Flask** that serves an interactive dashboard powered by the **Lightweight Charts™ (JavaScript library)**, allowing for dynamic exploration of backtest results, including price action, portfolio value, custom indicators, and trade signals.

The system is designed to be modular, allowing users to easily integrate their own custom trading strategies and data sources.

## Features

*   **Core Backtesting Engine:** Leverages the powerful and flexible **Backtrader** library.
*   **Multi-Data Feed Support:** Capable of backtesting strategies that utilize two distinct data feeds simultaneously (e.g., for pairs trading, correlation analysis).
*   **Customizable Strategies:** Easily define and integrate new trading strategies. Includes examples like `CorrelatedSMACrossStrategy`, `MACrossOver`, and `BBandPearsonDivergence`.
*   **Parametric Strategies:** Strategy parameters can be easily configured via command-line arguments or (in future enhancements) a web interface.
*   **Standard & Custom Indicators:** Integrates common Backtrader indicators and supports custom-built indicators (e.g., `PearsonR`).
*   **Comprehensive Performance Metrics:** Calculates a wide array of performance metrics (Sharpe Ratio, Max Drawdown, SQN, Win Rate, Profit Factor, Trade Analysis, Monthly Returns, Transaction Details, etc.) using built-in Backtrader Analyzers.
*   **Detailed Value & Indicator Capture:** A custom `ValueCaptureAnalyzer` records time-series data for portfolio value, OHLC data for primary feeds, and values for user-defined plottable indicators within strategies.
*   **CLI Operations (`main.py`):**
    *   Run backtests with configurable parameters (data paths, strategy, dates, broker/sizer/strategy arguments).
    *   View detailed performance reports directly in the terminal.
    *   Optionally generate default Backtrader Matplotlib plots.
    *   Optionally generate interactive HTML charts using `lightweight-charts-python` via `custom_plotter.py`.
*   **Interactive Web Dashboard (`app_server.py` & `index.html`):**
    *   On startup, runs a default backtest simulation and caches the results.
    *   Serves an `index.html` page that fetches and displays backtest data using the Lightweight Charts™ JS library.
    *   Visualizes:
        *   Primary data feed (Data0) as OHLC candlesticks.
        *   Portfolio value over time.
        *   Custom indicators (from strategies) on the main chart or dedicated sub-panes.
        *   (Planned) Trade entry/exit markers on the main chart.
    *   (Future) Allows users to configure and run new backtests directly from the web interface.
*   **Centralized Configuration:** `config/settings.py` for default paths, strategy parameters, and CSV parsing rules.


## Getting Started

### Prerequisites

*   Python (3.8 or higher recommended)
*   Git

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git
    cd YOUR_REPOSITORY_NAME
    ```

2.  **Set up a virtual environment (Recommended):**
    ```bash
    python -m venv venv
    # Activate the environment
    # Windows:
    # venv\Scripts\activate
    # macOS/Linux:
    # source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Creating `requirements.txt`

Create a file named `requirements.txt` in the project root with the following content (add or adjust versions as needed):

```
backtrader
matplotlib
pandas
numpy
Flask
Flask-CORS
lightweight-charts-python  # For the CLI custom plotter
scipy                      # For PearsonR indicator
# Add other libraries if your custom strategies require them
```

### Data Setup

1.  Place your CSV data files in the `data/` directory.
2.  Ensure your CSV files have a header row and columns for Date, Time, Open, High, Low, Close, Volume.
3.  The default CSV parsing settings are in `src/config/settings.py` (under `CSV_PARAMS`). Adjust these if your CSV format differs.
4.  Update `DEFAULT_DATA_PATH_1` and `DEFAULT_DATA_PATH_2` in `src/config/settings.py` to point to your desired default data files.

## Usage

### 1. Command-Line Interface (CLI)

Navigate to the project root directory.

**Run a backtest with default settings:**

```bash
python main.py
```

**Run with specific parameters:**

```bash
python main.py \
    --data-path-1 data/YOUR_DATA_1.csv \
    --data-path-2 data/YOUR_DATA_2.csv \
    --strategy-name CorrelatedSMACross \
    --fromdate 2023-01-01 \
    --todate 2023-12-31 \
    --strat "p_fast_d0=15,p_slow_d0=40,p_fast_d1=10,p_slow_d1=30" \
    --broker "cash=50000,commission=0.0005" \
    --sizer "stake=5" \
    --plot \
    --run-name "MyTestRun_Jan2023"
```

*   Use `python main.py --help` to see all available options and their defaults.
*   The `--plot` flag will attempt to generate both the `lightweight-charts-python` HTML plot and the default Backtrader Matplotlib plot.

### 2. Web Application Dashboard

1.  **Start the Flask server:**
    Navigate to the `src/` directory:
    ```bash
    cd src
    python app_server.py
    ```
    (Alternatively, from the project root: `python src/app_server.py`)

2.  **Open your web browser** and go to: `http://127.0.0.1:5000/`

    The server will run a default backtest upon startup (configured in `app_server.py` via `ArgsMock` and `settings.py`), and the dashboard will display its results.

## Development & Customization

### Adding a New Strategy

1.  Create a new Python file in the `src/strategies/` directory (e.g., `my_new_strategy.py`).
2.  Define your strategy class, inheriting from `bt.Strategy`.
    *   Implement `__init__`, `next`, `notify_order`, `log`, etc.
    *   **For Web Visualization:**
        *   Add a class attribute `_plottable_indicators_template` (list of tuples) to specify which internal indicators should be captured by `ValueCaptureAnalyzer`. Each tuple should be: `(attribute_name, line_name, display_name_format_or_direct, target_pane, options_dict, optional_param_key_for_display_name)`.
        *   Initialize `self.signals = []` in `__init__`.
        *   In `notify_order`, append to `self.signals` upon trade execution: `{'type': 'buy'/'sell', 'datetime': dt_object, 'price': exec_price}`.
3.  Update the strategy mapping in `src/backtesting/runner.py` (in the `setup_and_run_backtest` function) to include your new strategy, or implement a more dynamic strategy loading mechanism.
4.  You can now select your strategy using the `--strategy-name` argument in the CLI or (eventually) through the web UI.

## Future Enhancements (Roadmap)

*   **Web UI Backtest Execution:** Allow users to configure and launch backtests directly from the Flask web application.
*   **Trade Signal Visualization:** Display buy/sell markers on the Lightweight Charts in the web dashboard.
*   **Results Persistence:** Save backtest results (metrics and chart data) to files or a database for later review and comparison.
*   **Dynamic Strategy Loading:** Improve `runner.py` to load strategies without manual if-elif mapping.
*   **Parameter Optimization UI:** Integrate tools for running strategy parameter optimizations via the web interface.
*   **Enhanced Legend & Interactivity:** Improve the web chart legend and add more interactive elements.
*   **(Potential) Live Execution Module:** A separate component for connecting strategies to a live trading broker.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs, feature requests, or improvements.

1.  Fork the Project.
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the Branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

## License

Distributed under the MIT License. See `LICENSE` for more information. (You'll need to add a LICENSE file if you choose one).

## Acknowledgements

*   [Backtrader](https://www.backtrader.com/)
*   [Flask](https://flask.palletsprojects.com/)
*   [Lightweight Charts™ by TradingView](https://www.tradingview.com/lightweight-charts/)
*   [lightweight-charts-python](https://github.com/louisnw01/lightweight-charts-python/)

---
```



