# Trading Strategy Optimizer

A robust system for quantitative trading strategy backtesting, optimization, and eventual execution. Focus on multi-asset/multi-timeframe analysis and robustness. Structured for open-source contribution (GitHub) and potential deployment of an analysis tool on Streamlit Community Cloud.

## Project Vision

The primary goal of this project is to develop a flexible and powerful framework in Python to:
1.  **Backtest** trading strategies involving multiple assets and potentially different timeframes simultaneously (e.g., analyzing XAUUSD on 15m chart influenced by SP500 on 1h chart).
2.  **Optimize** strategy parameters (indicator periods, thresholds, risk management rules, cross-asset logic) using Hyperparameter Optimization (HPO) techniques (initially targeting W&B Sweeps with Bayesian optimization).
3.  **Analyze** backtesting results thoroughly using interactive visualizations (initially via Plotly and later integrated into a Streamlit dashboard).
4.  **(Future Goal)** Connect optimized strategies to the MetaTrader 5 platform for paper or live trading.
5.  **(Future Goal)** Provide a user-friendly Streamlit application for strategy analysis and simulation, potentially deployable via Streamlit Community Cloud.

This project aims to provide robust tools for quantitative traders looking to systematically test and refine their strategies, with a particular focus on cross-asset analysis and risk management.

## Current Status (Hito 0 - In Progress)

*   **[In Progress]** Setting up the foundational backtesting engine using `backtrader`.
*   **[To Do]** Implementing multi-asset/multi-timeframe data loading and alignment.
*   **[To Do]** Implementing core strategy logic (based on "IntoTheMirror" concept) with parameterization.
*   **[To Do]** Developing dual interactive visualization using `plotly`.
*   **[To Do]** Implementing core backtesting metrics and analyzers.

## Tech Stack (Initial)

*   Python 3.12+
*   Backtrader
*   Pandas
*   NumPy
*   Plotly
*   Pandas TA (or TA-Lib)
*   Weights & Biases (for HPO in Hito 1)
*   Streamlit (for UI in Hito 2)
*   MetaTrader5 (for execution in Hito 3)
*   Git & GitHub

## Project Structure

quant-trading-optimizer/
├── data/ # Placeholder for historical data files (.csv) - NOT versioned via Git
├── scripts/ # Executable scripts (runners for backtest, sweeps, etc.)
├── src/ # Main source code
│ ├── data_handling/ # Data loading, cleaning, alignment
│ ├── indicators/ # Indicator calculation logic
│ ├── strategy/ # Backtrader strategy classes
│ ├── backtesting/ # Backtesting engine setup and execution logic
│ ├── plotting/ # Plotly visualization functions
│ └── utils/ # Utility functions (optional)
├── notebooks/ # Optional: Jupyter notebooks for exploration
├── venv/ # Python virtual environment (ignored by Git)
├── .gitignore # Specifies intentionally untracked files
├── LICENSE # MIT License file
└── README.md # This file



## Getting Started

*(Instructions will be added here once Hito 0 is more complete - e.g., how to install dependencies, get data, run a basic backtest)*

## Contributing

*(Contribution guidelines will be added later. For now, feel free to open issues for suggestions or bug reports.)*

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.