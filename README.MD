# Quant Bot Project: Backtesting & Analysis Platform

## Overview

This project provides a Python-based framework for backtesting, analyzing, and potentially executing quantitative trading strategies, with a focus on multi-asset evaluation. It uses Backtrader as the core backtesting engine, Plotly for interactive visualizations, and Streamlit for building a user-friendly analysis dashboard.

The system is designed to be modular and extensible, allowing users to add their own strategies and data. Performance is optimized by using pre-processed historical data (e.g., M15, H1 timeframes) stored in efficient formats like Parquet.

## Features

*   **Backtesting Engine:** Leverages the powerful and flexible Backtrader library.
*   **Multi-Asset/Multi-Timeframe:** Supports running strategies across multiple instruments and timeframes simultaneously (using pre-processed data).
*   **Parametric Strategies:** Easily define strategy parameters for testing and optimization.
*   **Standard Indicators:** Integrates common technical indicators via libraries like TA-Lib or Pandas TA (or custom implementations).
*   **Performance Metrics:** Calculates standard performance metrics (Sharpe Ratio, Drawdown, SQN, Trade Analysis, etc.) using Backtrader Analyzers.
*   **Interactive Dashboard:** A Streamlit application (`dashboard/app.py`) allows:
    *   Selecting strategies and assets/timeframes.
    *   Adjusting strategy parameters.
    *   Running backtests on demand.
    *   Visualizing results with interactive Plotly charts (candlesticks, indicators, trades).
    *   Viewing performance statistics and trade lists.
*   **Pre-processed Data Handling:** Uses pre-aggregated data (e.g., M15, H1) hosted on GitHub Releases for efficient loading and analysis, keeping the main repository lightweight. Includes scripts to process your own raw data.
*   **(Future) Optimization:** Planned integration with Weights & Biases Sweeps for hyperparameter optimization.
*   **(Future) Live Execution:** Planned standalone bot for MT5 execution (separate process).

## Getting Started

### Prerequisites

*   Python (3.9 or higher recommended)
*   Git
*   (Optional but Recommended) [TA-Lib](https://mrjbq7.github.io/ta-lib/install.html): Follow the installation instructions for your specific OS *before* installing the Python wrapper. This can sometimes be tricky.

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
    *(Note: You will need to create the `requirements.txt` file, see below)*

### Creating `requirements.txt`

Create a file named `requirements.txt` in the project root with the following libraries (add others as needed):

```txt
backtrader
pandas
plotly
streamlit
requests
pyarrow       # For Parquet support
numpy
# Optional: Add pandas-ta or talib if used by your strategies
# pandas-ta
# TA-Lib      # If TA-Lib C library is installed