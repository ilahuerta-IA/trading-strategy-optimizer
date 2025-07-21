# main.py
import argparse
from pathlib import Path
import sys
import datetime
import traceback

# --- Path setup ---
project_root = Path(__file__).resolve().parent
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))

# --- Imports ---
from backtesting.runner import setup_and_run_backtest
from config import settings
from utils.parsing import parse_kwargs_str
# --- Import the new plotter ---
from visualization.web_plotter import create_standalone_report

def parse_args(pargs=None):
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Backtrader Strategy Runner'
    )
    default_run_name = f"backtest_{datetime.datetime.now():%Y%m%d_%H%M%S}"

    # ... (all argparse arguments are unchanged) ...
    parser.add_argument('--data-path-1', default=settings.DEFAULT_DATA_PATH_1, help='Path to CSV data file for the first asset')
    parser.add_argument('--data-path-2', default=settings.DEFAULT_DATA_PATH_2, help='Path to CSV data file for the second asset')
    parser.add_argument('--strategy-name', default=settings.DEFAULT_STRATEGY_NAME, help='Name of the strategy class to run')
    parser.add_argument('--fromdate', default=settings.DEFAULT_FROM_DATE, help='Start Date in YYYY-MM-DD format')
    parser.add_argument('--todate', default=settings.DEFAULT_TO_DATE, help='End Date in YYYY-MM-DD format')
    parser.add_argument('--broker', default=settings.DEFAULT_BROKER_ARGS, help='kwargs for BackBroker')
    parser.add_argument('--sizer', default=settings.DEFAULT_SIZER_ARGS, help='kwargs for FixedSize sizer')
    parser.add_argument('--strat', default=settings.DEFAULT_STRAT_ARGS, help='kwargs for selected strategy')
    parser.add_argument('--cerebro', default=settings.DEFAULT_CEREBRO_ARGS, help='kwargs for cerebro.run')
    parser.add_argument('--plot', action='store_true', help='Generate and open an interactive HTML report.')
    parser.add_argument('--run-name', default=default_run_name, help='Identifier name for this backtest run')
    return parser.parse_args(pargs)

if __name__ == '__main__':
    print("Starting backtest run...")
    args = parse_args()

    # This part is unchanged
    results_data = setup_and_run_backtest(args, parse_kwargs_func=parse_kwargs_str)

    # --- PLOTTING LOGIC ---
    if args.plot:
        if results_data:
            # Call our function that creates and opens the HTML file
            create_standalone_report(results_data)
        else:
            print("Plotting skipped: Backtest runner did not return valid results.")
    
    print("\nBacktest run script finished.")