import argparse
from pathlib import Path
import sys
import datetime
import matplotlib.pyplot as plt # Keep for potentially showing default plot

# --- Path setup ---
project_root = Path(__file__).resolve().parent.parent
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))
# print(f"Added to sys.path: {src_path}") # Optional debug

# --- Imports ---
from backtesting.runner import setup_and_run_backtest
from config import settings # Import defaults from config
from utils.parsing import parse_kwargs_str # Assuming parse_kwargs_str is moved to utils
from visualization.custom_plotter import plot_backtest_data

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
    parser.add_argument('--plot', action='store_true',
                        help='Enable plotting (generates custom plot and attempts default Backtrader plot)')
    parser.add_argument('--candlestick', action='store_true', # Defaults to False if not present
                        help='Plot data0 as candlestick instead of line in the custom plot.')
    parser.add_argument('--run-name', default=default_run_name,
                        help='Identifier name for this backtest run')

    return parser.parse_args(pargs)

if __name__ == '__main__':
    print("Starting backtest run...")
    args = parse_args()


    # --- Run the backtest and get structured results ---
    results_data = setup_and_run_backtest(args, parse_kwargs_func=parse_kwargs_str)

    # --- Generate Custom Plot ---
    if results_data:
        print("\n--- Attempting Custom Plot Generation ---")
        # Check if the crucial analysis dictionary exists
        if hasattr(results_data, 'value_analysis') and results_data.value_analysis is not None:
            # Extract data feed names (used in runner, get them here too)
            data0_name = Path(args.data_path_1).stem
            data1_name = Path(args.data_path_2).stem

            # Call the NEW plotting function
            plot_backtest_data(
                analysis_data=results_data.value_analysis,
                run_name=args.run_name,
                data0_name=data0_name,
                data1_name=data1_name,
                use_candlestick=args.candlestick
            )
        else:
            print("Custom Plot Skipped: Value analysis data not found or is None in results.")
    else:
        print("Custom Plot Skipped: Backtest runner did not return results.")

    # --- Optional: Show default plot if generated ---
    if args.plot:
        print("\nDisplaying any generated Matplotlib figures (including default Backtrader plot)...")
        # Need to check if plt has figures to show, otherwise show() might do nothing or error
        # A simple check:
        if plt.get_fignums(): # Check if any figures exist
            plt.show()
        else:
            print("No Matplotlib figures found to display.")

    print("Backtest run script finished.")