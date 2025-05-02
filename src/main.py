import argparse
from pathlib import Path
import sys
import datetime

# Adjust path if necessary to find other modules in src/
# If running main.py directly from project root, this helps:
project_root = Path(__file__).resolve().parent.parent
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))
# print(f"Added to sys.path: {src_path}") # Optional debug

from backtesting.runner import setup_and_run_backtest
from config import settings # Import defaults from config
from utils.parsing import parse_kwargs_str # Assuming parse_kwargs_str is moved to utils

def parse_args(pargs=None):
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Backtrader Strategy Runner'
    )
    default_run_name = f"backtest_{datetime.datetime.now():%Y%m%d_%H%M%S}"

    # --- Data Paths (Keep Generic) ---
    parser.add_argument('--data-path-1', default=settings.DEFAULT_DATA_PATH_1,
                        metavar='FILEPATH', help='Path to CSV data file for the first asset')
    parser.add_argument('--data-path-2', default=settings.DEFAULT_DATA_PATH_2,
                        metavar='FILEPATH', help='Path to CSV data file for the second asset (can be same as first)')
    
    # --- NEW: Strategy Selection ---
    parser.add_argument('--strategy-name', default=settings.DEFAULT_STRATEGY_NAME,
                        help='Name of the strategy class to run (e.g., SMACrossOver, MACrossOver)')
    # --- Standard Arguments ---
    parser.add_argument('--fromdate', default=settings.DEFAULT_FROM_DATE,
                        help='Start Date[time] in YYYY-MM-DD[THH:MM:SS] format')
    parser.add_argument('--todate', default=settings.DEFAULT_TO_DATE,
                        help='End Date[time] in YYYY-MM-DD[THH:MM:SS] format')
    parser.add_argument('--broker', default=settings.DEFAULT_BROKER_ARGS,
                        metavar='kwargs', help='kwargs for BackBroker')
    parser.add_argument('--sizer', default=settings.DEFAULT_SIZER_ARGS,
                        metavar='kwargs', help='kwargs for FixedSize sizer')
    # --- Strategy Params (applied to selected strategy) ---
    parser.add_argument('--strat', default=settings.DEFAULT_STRAT_ARGS,
                        metavar='kwargs', help='kwargs to override selected strategy params (e.g., p_fast=15,p_slow=40)')
    parser.add_argument('--cerebro', default=settings.DEFAULT_CEREBRO_ARGS,
                        metavar='kwargs', help='kwargs for cerebro.run (e.g., stdstats=False)')
    parser.add_argument('--plot', default=None,
                        nargs='?', const='{}',
                        metavar='kwargs', help='Enable plotting and pass plot kwargs (e.g., style=candlestick)')
    parser.add_argument('--run-name', default=default_run_name,
                        help='Identifier name for this backtest run')

    return parser.parse_args(pargs)

if __name__ == '__main__':
    print("Starting backtest run...")
    args = parse_args()
    # Pass the parsing function (ensure it's imported correctly)
    setup_and_run_backtest(args, parse_kwargs_func=parse_kwargs_str)
    print("Backtest run script finished.")