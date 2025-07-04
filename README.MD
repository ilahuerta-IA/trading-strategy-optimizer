# Python Asynchronous Backtesting Platform

## Overview

This project provides a comprehensive Python-based framework for backtesting and analyzing quantitative trading strategies. It is built around the powerful **Backtrader** engine and offers two distinct, powerful interfaces for running and analyzing backtests:

1.  **A Command-Line Tool (`main.py`):** For power users and automated scripting. When run with the `--plot` flag, it generates a **rich, interactive, self-contained HTML report** for deep visual analysis, which opens automatically in your browser.
2.  **An Interactive Web Application (`app_server.py`):** For easy, browser-based interaction. It features a non-blocking, asynchronous backend that allows users to dynamically configure data files, date ranges, and all strategy parameters, viewing detailed **statistical reports** upon completion.

The system is designed to be modular and extensible, allowing users to easily add and test their own trading strategies across both interfaces.

## Features

*   **Standalone Interactive HTML Reports:** The command-line tool generates a single, portable `.html` file containing all charts (OHLC, indicators, portfolio value), trade markers, and statistical tables. This report is rendered using the **Lightweight Charts™** library and can be viewed offline and shared easily.
*   **Asynchronous Web Backend:** The web app uses a robust architecture with a **background worker process** and **SQLite** database to handle long backtests without blocking the UI or causing server timeouts.
*   **Fully Dynamic Web UI:** The web interface dynamically generates input forms for data files, date ranges, and all strategy-specific parameters based on definitions in the Python code, allowing for full configuration from the browser.
*   **Dynamic Strategy System:** Easily add new strategies in Python. The system automatically discovers them and their parameters for use in both the CLI and web interface.
*   **Comprehensive Analytics:** Leverages Backtrader's analyzers to calculate a wide array of metrics (Sharpe Ratio, Max Drawdown, SQN, PnL, etc.).
*   **Extensible and Modular:** The code is structured with clear separation of concerns (web server, worker, CLI runner, visualization), making it maintainable and easy to extend.

## Project Structure (Key Components)

```
.
├── src/
│   ├── app_server.py           # Flask web server for interactive backtesting.
│   ├── worker.py               # Background worker that runs backtests for the web app.
│   ├── database.py             # SQLite database setup.
│   ├── templates/
│   │   └── index.html          # Main HTML page for the web app.
│   ├── static/                 # CSS and JS for the web app.
│   ├── visualization/
│   │   ├── web_plotter.py      # Generates the standalone HTML report for main.py.
│   │   └── report_template.html# Template for the HTML report.
│   ├── backtesting/
│   │   └── runner.py           # Core backtest setup and execution logic.
│   ├── strategies/             # Directory for strategy classes.
│   └── utils/
│       └── serialization.py    # Robust JSON serialization utility.
├── main.py                     # CLI entry point.
├── data/                       # Directory for CSV data files.
├── requirements.txt            # Python dependencies.
└── .gitignore                  # Specifies files for Git to ignore.
```

## Getting Started

### Prerequisites

*   Python (3.9 or higher recommended)
*   Git

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/ilahuerta-IA/trading-strategy-optimizer.git
    cd trading-strategy-optimizer
    ```
2.  **Set up a virtual environment (Recommended):**
    ```bash
    python -m venv venv
    # Activate: venv\Scripts\activate (Windows) or source venv/bin/activate (macOS/Linux)
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### 1. Command-Line Tool (for Deep Visualization & Scripting)

This is the best way to get a full visual report.

**Run a backtest and generate an interactive HTML report:**
```bash
python main.py --plot --fromdate 2023-01-01 --strat "p_fast_d0=15"
```
This will run the backtest and automatically open the detailed report in your web browser. Use `python main.py --help` for all options.

### 2. Web Application (for Interactive Statistical Analysis)

This is the recommended way to quickly test different parameter configurations and see the numerical results.

1.  **Start the server:** From the project root, run:
    ```bash
    python src/app_server.py
    ```
2.  **Open your web browser** and navigate to: `http://127.0.0.1:5000/`
3.  **Run a backtest:**
    *   Use the form to configure your data files, date range, and strategy parameters.
    *   Click "Run Backtest" and wait for the numerical report to appear on the page.

## Development & Customization

### Adding a New Strategy

1.  Create a new Python file in `src/strategies/`.
2.  Define your strategy class, inheriting from `BaseStrategy`.
3.  Implement a static method `get_parameter_definitions()` to define parameters for the web UI.
4.  Implement `_plottable_indicators` and `self.signals` to ensure indicators and trades appear in the HTML report.
5.  In `src/strategies/__init__.py`, import and register your new strategy in the `AVAILABLE_STRATEGIES` dictionary.

## Future Enhancements

*   **UI Strategy Selector:** Add a dropdown to the web UI to select from all available strategies.
*   **On-Demand Charting for Web App:** Add a "Visualize" button to the web app's results that generates and opens the standalone HTML report for that specific run.
*   **Batch Backtesting:** Add a feature to run a strategy across a range of parameters and display a summary table.

## License

Distributed under the MIT License.

## Acknowledgements

*   [Backtrader](https://www.backtrader.com/)
*   [Flask](https://flask.palletsprojects.com/)
*   [Lightweight Charts™ by TradingView](https://www.tradingview.com/lightweight-charts/)
