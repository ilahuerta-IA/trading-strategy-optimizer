
# Python Asynchronous Backtesting Platform

## Overview

This project provides a comprehensive Python-based framework for backtesting and analyzing quantitative trading strategies. It uses **Backtrader** as its core backtesting engine and features a powerful, non-blocking web interface built with **Flask**.

The key feature of this platform is its **asynchronous architecture**. Backtests, which can be computationally intensive and take several minutes, are executed in a separate background worker process. This ensures the web UI remains fast and responsive at all times. Users can submit backtests, modify strategy parameters, and view detailed statistical reports without freezing their browser or hitting server timeouts.

## Features

*   **Asynchronous Backtesting:** A robust backend using Python's `multiprocessing` and a task queue to handle long-running backtests without blocking the web server.
*   **Persistent Job & Result Storage:** Utilizes a lightweight **SQLite** database to track the status of every backtest (`queued`, `running`, `completed`, `failed`) and to store the final, comprehensive results.
*   **Interactive Web Interface (`Flask` + `JavaScript`):**
    *   Dynamically generates input forms for strategy parameters based on definitions in the Python strategy code.
    *   Allows users to run new backtests with custom parameters directly from the browser.
    *   Real-time status polling provides feedback to the user while the backtest is running.
    *   Displays a professional and detailed numerical report of backtest results upon completion.
*   **Command-Line Interface (`main.py`):** A fully-featured CLI is also available for power users to run backtests, generate reports, and (optionally) visualize charts locally.
*   **Dynamic Strategy System:** The backend is designed to dynamically discover and load strategies, making it easy to add new ones. Strategies can define their own parameters in a structured way for the UI to consume.
*   **Comprehensive Analytics:** Leverages Backtrader's built-in analyzers to produce a wide array of metrics, including Sharpe Ratio, Max Drawdown, SQN, PnL, and detailed trade statistics.
*   **Extensible and Modular:** The code is structured with clear separation of concerns (web server, worker, runner, strategies), making it maintainable and easy to extend.

## Project Structure (Key Components)

```
.
├── src/
│   ├── app_server.py           # Flask web server, handles API requests.
│   ├── worker.py               # Background worker process for running backtests.
│   ├── database.py             # SQLite database initialization.
│   ├── templates/
│   │   └── index.html          # Main HTML page for the web interface.
│   ├── static/
│   │   ├── js/
│   │   │   ├── chart.js        # Main JS logic for the web UI (event handling, polling).
│   │   │   └── ui.js           # JS for populating the report tables.
│   │   └── css/style.css       # Styles for the web interface.
│   ├── backtesting/
│   │   └── runner.py           # Core backtest setup and execution logic.
│   ├── strategies/             # Directory for strategy classes.
│   │   ├── __init__.py         # Strategy registration.
│   │   ├── base_strategy.py    # Base class for defining parameters.
│   │   └── ...                 # Strategy implementation files.
│   └── ...                     # Other modules (config, utils, etc.)
├── main.py                     # CLI entry point.
├── data/                       # Directory for CSV data files.
├── backtests.db                # SQLite database (generated, not in Git).
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

### Data Setup

1.  Place your historical data as `.csv` files inside the `data/` directory.
2.  The default parser expects columns like `Date,Time,Open,High,Low,Close,Volume`. This can be configured in `src/config/settings.py`.
3.  Update the default data paths in `src/config/settings.py` if desired.

## Usage

### 1. Web Application (Recommended)

This is the primary way to interact with the backtesting system.

1.  **Start the server:** From the project root, run:
    ```bash
    python src/app_server.py
    ```
    This will initialize the database, start the background worker, and launch the Flask web server.

2.  **Open your web browser** and navigate to: `http://127.0.0.1:5000/`

3.  **Run a backtest:**
    *   The web page will display a form with the parameters for the default strategy.
    *   Change any parameters you wish to test.
    *   Click "Run Backtest".
    *   The UI will show the status of your task (`queued`, `running`).
    *   Once complete, a full statistical report will be displayed on the page.

### 2. Command-Line Interface (for advanced use)

The CLI is perfect for scripting or quick runs without a browser.

**Run a backtest with default parameters:**
```bash
python main.py
```

**Run a highly customized backtest:**
```bash
python main.py --strategy-name CorrelatedSMACross --strat "p_fast_d0=15,p_slow_d0=40"
```
Use `python main.py --help` to see all available options.

## Development & Customization

### Adding a New Strategy

1.  **Create Strategy File:** Create a new `.py` file in `src/strategies/`.
2.  **Define Strategy Class:** Your class should inherit from `BaseStrategy` (or `bt.Strategy`).
3.  **Define Parameters:** Implement a static method `get_parameter_definitions()` that returns a list of `ParameterDefinition` objects. This allows the web UI to automatically generate the form for your new strategy.
    ```python
    # In your new strategy file
    from .base_strategy import BaseStrategy, ParameterDefinition

    class MyNewStrategy(BaseStrategy):
        # ...
        @staticmethod
        def get_parameter_definitions():
            return [
                ParameterDefinition(name='my_param', default_value=10, ui_label='My Custom Parameter'),
                # ... other params
            ]
    ```
4.  **Register Strategy:** Open `src/strategies/__init__.py` and add your new strategy to the `AVAILABLE_STRATEGIES` dictionary.

The web application will now be able to find and display your new strategy and its parameters (once a strategy selector is added to the UI).

## Future Enhancements (Roadmap)

*   **Web UI Strategy & Data Selection:** Add dropdowns to the UI to select from all available strategies and data files.
*   **Chart Visualization:** Re-introduce charting in a stable, on-demand way (e.g., opening charts for a completed backtest in a new window).
*   **Batch Backtesting:** Add a feature to run a strategy across a range of parameters and display a summary table of the results.
*   **Results History:** Create a UI to view the results of all past backtests stored in the database.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Acknowledgements

*   [Backtrader](https://www.backtrader.com/)
*   [Flask](https://flask.palletsprojects.com/)

