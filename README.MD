# Python Asynchronous Backtesting Platform

## Overview

This project provides a comprehensive Python-based framework for backtesting and analyzing quantitative trading strategies. It is built around the powerful **Backtrader** engine and offers two distinct, powerful interfaces for running and analyzing backtests:

1.  **A Command-Line Tool (`main.py`):** For power users and automated scripting. When run with the `--plot` flag, it generates a **rich, interactive, self-contained HTML report** for deep visual analysis, which opens automatically in your browser.
2.  **An Interactive Web Application (`app_server.py`):** For easy, browser-based interaction. It features a non-blocking, asynchronous backend that allows users to dynamically configure data files, date ranges, and all strategy parameters, viewing detailed **statistical reports** upon completion.

The system is designed to be modular and extensible, allowing users to easily add and test their own trading strategies across both interfaces.

## Features

*   **Machine Learning Strategy Integration:** Includes a ready-to-use **Time Series Transformer** strategy for predictive analysis. The framework supports a two-step workflow: training the model and then running the backtest using the generated artifacts.
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
│   ├── train_transformer.py    # Script to train the Time Series Transformer model.
│   ├── ml_models/              # Stores trained model artifacts (e.g., .pth, .pkl).
│   ├── templates/
│   │   └── index.html          # Main HTML page for the web app.
│   ├── static/                 # CSS and JS for the web app.
│   ├── visualization/
│   │   ├── web_plotter.py      # Generates the standalone HTML report for main.py.
│   │   └── report_template.html# Template for the HTML report.
│   ├── backtesting/
│   │   └── runner.py           # Core backtest setup and execution logic.
│   ├── strategies/             # Directory for strategy classes (including transformer_signal_strategy.py).
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

### 3. Machine Learning Strategy: Time Series Transformer

This project includes a sophisticated predictive strategy based on a Time Series Transformer model. The repository comes with a **pre-trained model** specifically for **EUR/USD on a 5-minute timeframe**.

The complete research, data preparation, and training methodology for this model are detailed in a dedicated repository:
**[Applied ML Trading Transformer for EUR/USD](https://github.com/ilahuerta-IA/applied-ml-trading-transformer-eurusd.git)**

You can immediately see this pre-trained model in action within this project.

#### Using the Pre-Trained Model

The model artifacts (`best_transformer_model.pth`, `target_scaler.pkl`, `model_config.json`) are already included in the `src/ml_models/` directory. To run a backtest and visualize the model's predictions against EUR/USD 5-minute price data, simply execute the strategy script directly.

From the project root, run:
```bash
python src/strategies/transformer_signal_strategy.py
```
This will launch a `backtrader` instance and generate a plot showing the price, the model's raw prediction, and a smoothed prediction line.

#### (Optional) Re-training Your Own Model

If you wish to train the model on different data or with different parameters, you can use the provided training script.

1.  **Prepare your data:** Place your historical data CSV file in the `/data` directory.
2.  **(Optional) Modify configuration:** Adjust the model configuration and hyperparameters at the top of the `src/train_transformer.py` script.
3.  **Run the training script:** This will overwrite the existing model artifacts in `src/ml_models/`.
    ```bash
    python src/train_transformer.py
    ```
4.  **Run the backtest:** Execute the strategy as described above to see your newly trained model in action.

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
