import yfinance as yf
import pandas as pd
from pathlib import Path
import datetime

# --- Configuration ---
TICKERS = ["SPY", "GLD"]
INTERVAL = "5m"
# Note: Yahoo typically limits 5m data history (often to ~60 days).
PERIOD = "1mo"
FILENAME_SUFFIX = f"{INTERVAL}_{PERIOD.replace('m','M')}n"

# --- IMPORTANT: Update this path to your specific directory ---
# Using raw string (r"...") or forward slashes for Windows paths
# RAW_DATA_DIR = Path(r"C:\Iván\Yosoybuendesarrollador\Python\Portafolio\quant_bot_project\data")
RAW_DATA_DIR = Path("C:/Iván/Yosoybuendesarrollador/Python/Portafolio/quant_bot_project/data") # Forward slashes often work too

# --- Script Logic ---

print(f"Data download script started.")
print(f"Target directory: {RAW_DATA_DIR}")
print(f"Tickers: {', '.join(TICKERS)}")
print(f"Interval: {INTERVAL}")
print(f"Requested Period: {PERIOD}")
print("-" * 30)

# Create the target directory if it doesn't exist
try:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Directory '{RAW_DATA_DIR}' ensured.")
except OSError as e:
    print(f"Error creating directory '{RAW_DATA_DIR}': {e}")
    print("Please check permissions or create the directory manually.")
    exit() # Exit if directory creation fails

# Loop through tickers and download data
for ticker_symbol in TICKERS:
    filename = f"{ticker_symbol}_{FILENAME_SUFFIX}.csv"
    full_file_path = RAW_DATA_DIR / filename # Use pathlib to join paths

    print(f"\nProcessing: {ticker_symbol}")
    print(f"Attempting to download data (Interval: {INTERVAL}, Period: {PERIOD})...")

    try:
        # Create ticker object
        ticker = yf.Ticker(ticker_symbol)

        # Download historical data
        hist_data = ticker.history(period=PERIOD, interval=INTERVAL)

        if hist_data.empty:
            print(f"Warning: Downloaded data for {ticker_symbol} is empty.")
            print(f"         Check ticker validity and requested period/interval limits.")
        else:
            print(f"Download successful for {ticker_symbol}.")
            print(f"Data points downloaded: {len(hist_data)}")
            if not hist_data.index.tz:
                 print(f"Warning: Index timezone is missing. Consider localizing.")
            else:
                 print(f"Data timezone: {hist_data.index.tz}") # Show timezone

            # Save to CSV
            try:
                hist_data.to_csv(full_file_path)
                print(f"Successfully saved data to: {full_file_path}")
            except Exception as e_save:
                print(f"Error saving {ticker_symbol} data to CSV: {e_save}")

    except Exception as e_download:
        print(f"An error occurred downloading data for {ticker_symbol}: {e_download}")
        print(f"         Skipping save for {ticker_symbol}.")

print("-" * 30)
print("Data download script finished.")