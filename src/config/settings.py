from pathlib import Path
import backtrader as bt

# --- Paths ---
# Assumes the script is run from project root or src/ is configured in PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent # Adjust if needed
DATA_PATH = PROJECT_ROOT / "data"

# --- Default Data Files ---
DEFAULT_DATA0_PATH = str(DATA_PATH / "SPY_5m_1Mon.csv")
DEFAULT_DATA1_PATH = str(DATA_PATH / "GLD_5m_1Mon.csv")

# --- Default Date Filters ---
DEFAULT_FROM_DATE = None
DEFAULT_TO_DATE = None

# --- Default Broker/Sizer/Strategy Args ---
DEFAULT_BROKER_ARGS = 'cash=100000,commission=0.001'
DEFAULT_SIZER_ARGS = 'stake=5'
DEFAULT_STRAT_ARGS = ''
DEFAULT_CEREBRO_ARGS = ''

# --- CSV Data Parameters ---
CSV_PARAMS = dict(
    # dataname is set dynamically
    nullvalue=float('NaN'),
    headers=True,
    skiprows=1,
    dtformat=('%Y-%m-%d %H:%M:%S%z'),
    datetime=0,
    time=-1,
    high=2,
    low=3,
    open=1,
    close=4,
    volume=5,
    openinterest=-1,
    timeframe=bt.TimeFrame.Minutes,
    compression=5
)