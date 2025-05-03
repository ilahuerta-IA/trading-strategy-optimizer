from pathlib import Path
import backtrader as bt

# --- Paths ---
# Get the directory where this settings.py file is located (src/config)
CONFIG_DIR = Path(__file__).resolve().parent
# Get the 'src' directory (parent of config)
SRC_DIR = CONFIG_DIR.parent
# Get the project root directory (parent of src)
PROJECT_ROOT = SRC_DIR.parent

# Construct the data path relative to the project root
DATA_PATH = PROJECT_ROOT / "data"

# --- Verify Data Path ---
# Add a check to ensure the path exists, helps debugging
if not DATA_PATH.exists():
    print(f"WARNING: Data directory not found at expected location: {DATA_PATH}")
    print(f"         Calculated from PROJECT_ROOT: {PROJECT_ROOT}")

# --- Default Data Files ---
#DEFAULT_DATA0_PATH = str(DATA_PATH / "SPY_5m_1Mon.csv")
#DEFAULT_DATA1_PATH = str(DATA_PATH / "GLD_5m_1Mon.csv")
DEFAULT_DATA_PATH_1 = str(DATA_PATH / "SPY_5m_1Yea.csv")
DEFAULT_DATA_PATH_2 = str(DATA_PATH / "XAUUSD_5m_1Yea.csv")

# --- Default Date Filters ---
DEFAULT_FROM_DATE = None
DEFAULT_TO_DATE = None

# --- Default Strategy ---
#DEFAULT_STRATEGY_NAME = 'MACrossOver'
DEFAULT_STRATEGY_NAME = 'SMACrossOver' # Default to the new simple strategy
#DEFAULT_STRATEGY_NAME = 'BBandPearsonDivergence'


# Defaults for MACrossOver (strategies/ma_cci_crossover.py)
# Note: Ensure MACrossOver strategy handles 'ma=SMA' string correctly if needed, or use specific params.
#DEFAULT_STRAT_ARGS = 'ma=SMA,pd1=50,pd2=50,corr_period=20,cci_period=20,atr_period=14,atr_multiplier=1.5,cci_exit_level=20'

# --- Default STRATEGY Args (Matching SMACrossOverStrategy) ---
DEFAULT_STRAT_ARGS = 'p_fast_d0=20,p_slow_d0=50,p_fast_d1=20,p_slow_d1=50'

# Defaults for BBandPearsonDivergence <-- ADD THESE
# DEFAULT_STRAT_ARGS = 'bb_period_d0=20,' \
#                     'bb_dev_d0=2.0,' \
#                     'bb_period_d1=20,' \
#                     'bb_dev_d1=2.0,' \
#                     'pearson_period=20,' \
#                     'pearson_decrease_lookback=2,' \
#                     'pearson_decrease_pct=0.6,' \
#                     'exit_on_bbmid=True'


# --- Default Broker/Sizer/Strategy Args ---
DEFAULT_BROKER_ARGS = 'cash=100000,commission=0.001'
DEFAULT_SIZER_ARGS = 'stake=10'
DEFAULT_STRAT_ARGS = ''
DEFAULT_CEREBRO_ARGS = ''

# --- CSV Data Parameters ---
CSV_PARAMS = dict(
    # dataname is set dynamically in runner.py
    nullvalue=float('NaN'),
    headers=True,    # Assume new files also have headers
    skiprows=1,      # Skip the header row

    # --- Specify Formats for SEPARATE Date and Time columns ---
    dtformat='%Y-%m-%d',       # Format for the Date column ONLY
    tmformat='%H:%M:%S',       # Format for the Time column ONLY
    # --- End Formats ---

    # Using column names based on "Date,Time,Open,High,Low,Close,Volume"
    # Ensure these exactly match the headers in your new CSV files
    # Using column indices (0='Date', 1='Time', 2='Open', ...)
    datetime=0,
    time=1,
    open=2,
    high=3,
    low=4,
    close=5,
    volume=6,

    openinterest=-1, # No Open Interest column

    timeframe=bt.TimeFrame.Minutes, # Still 5-minute data
    compression=5,                  # Still 5 minutes

    tz='UTC', # set if data is known to be UTC
)

# Ensure a strategy name and args are actually defined
if 'DEFAULT_STRATEGY_NAME' not in locals():
    raise ValueError("DEFAULT_STRATEGY_NAME is not defined in settings.py. Please uncomment one strategy.")
if 'DEFAULT_STRAT_ARGS' not in locals():
    raise ValueError("DEFAULT_STRAT_ARGS is not defined in settings.py. Please uncomment the corresponding arguments.")

print(f"[Settings] Default Strategy: {DEFAULT_STRATEGY_NAME}")
print(f"[Settings] Default Strat Args: {DEFAULT_STRAT_ARGS}")