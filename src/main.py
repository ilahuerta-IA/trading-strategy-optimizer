import argparse
from pathlib import Path
import sys

# Adjust path if necessary to find other modules in src/
# If running main.py directly from project root, this helps:
project_root = Path(__file__).resolve().parent.parent
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))
# print(f"Added to sys.path: {src_path}") # Optional debug

from backtesting.runner import setup_and_run_backtest
from config import settings # Import defaults from config

def parse_args(pargs=None):
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Backtrader Strategy Runner'
    )
    # Use defaults from settings
    parser.add_argument('--data0', default=settings.DEFAULT_DATA0_PATH,
                        metavar='FILEPATH', help='Path to CSV data file for data0')
    parser.add_argument('--data1', default=settings.DEFAULT_DATA1_PATH,
                        metavar='FILEPATH', help='Path to CSV data file for data1')
    parser.add_argument('--fromdate', default=settings.DEFAULT_FROM_DATE,
                        help='Start Date[time] in YYYY-MM-DD[THH:MM:SS] format')
    parser.add_argument('--todate', default=settings.DEFAULT_TO_DATE,
                        help='End Date[time] in YYYY-MM-DD[THH:MM:SS] format')
    parser.add_argument('--broker', default=settings.DEFAULT_BROKER_ARGS,
                        metavar='kwargs', help='kwargs for BackBroker')
    parser.add_argument('--sizer', default=settings.DEFAULT_SIZER_ARGS,
                        metavar='kwargs', help='kwargs for FixedSize sizer')
    parser.add_argument('--strat', default=settings.DEFAULT_STRAT_ARGS,
                        metavar='kwargs', help='kwargs for strategy')
    parser.add_argument('--cerebro', default=settings.DEFAULT_CEREBRO_ARGS,
                        metavar='kwargs', help='kwargs for cerebro.run')
    parser.add_argument('--plot', default=None, # Keep None for plotting off by default
                        nargs='?', const='{}',
                        metavar='kwargs', help='Enable plotting and pass plot kwargs')

    return parser.parse_args(pargs)

if __name__ == '__main__':
    print("Starting backtest run...")
    args = parse_args()
    setup_and_run_backtest(args) # Pass parsed args to the runner
    print("Backtest run script finished.")