"""Batch runner for Triemahl2AdaptiveStrategy across multiple assets.

Outputs per asset:
 - adaptive_trades_<SYMBOL>.csv (raw trade log from strategy)
Aggregated:
 - adaptive_asset_summary.csv (performance + reason counts)

Configuration focuses on chosen high-performance parameters from research:
 - keep_percent = 40 (top 40% of positive ΔStd_1_2 retained once calibrated)
 - angle_trail_factor = 0.90
 - max_hold_bars = 5

Adjust constants below to experiment further.
"""
from __future__ import annotations

import backtrader as bt
import pandas as pd
from pathlib import Path
import sys
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_STRATEGY_PATH = PROJECT_ROOT / 'src' / 'strategies'
sys.path.insert(0, str(SRC_STRATEGY_PATH))

from triemahl2_adaptive import Triemahl2AdaptiveStrategy  # type: ignore  # noqa: E402

ASSET_FILES = [
    'GBPUSD_5m_8Yea.csv',
    'EURUSD_5m_8Yea.csv',
    'USDCHF_5m_8Yea.csv',
]
DATA_DIR = PROJECT_ROOT / 'data'

# Strategy parameter selection
KEEP_PERCENT = 40
ANGLE_TRAIL_FACTOR = 0.90
MAX_HOLD_BARS = 5
MIN_TRADES_FOR_THRESHOLD = 300

SUMMARY_ROWS = []


def _sharpe(pips_series: pd.Series) -> float:
    if pips_series.empty:
        return 0.0
    m = pips_series.mean()
    s = pips_series.std(ddof=0)
    return float(m / s) if s and not np.isclose(s, 0.0) else 0.0


def run_asset(csv_name: str):
    symbol = csv_name.split('_')[0]
    data_path = DATA_DIR / csv_name
    if not data_path.exists():
        print(f"WARN: Missing data file {data_path}, skipping {symbol}.")
        return
    out_file = f"adaptive_trades_{symbol}.csv"

    cerebro = bt.Cerebro()
    cerebro.addstrategy(
        Triemahl2AdaptiveStrategy,
        max_hold_bars=MAX_HOLD_BARS,
        angle_trail_factor=ANGLE_TRAIL_FACTOR,
        keep_percent=KEEP_PERCENT,
        min_trades_for_threshold=MIN_TRADES_FOR_THRESHOLD,
        output_csv=out_file,
        verbose=False,
    )
    data = bt.feeds.GenericCSVData(
        dataname=str(data_path),
        dtformat=('%Y%m%d'),
        tmformat=('%H:%M:%S'),
        datetime=0, time=1, open=2, high=3, low=4, close=5, volume=6,
        timeframe=bt.TimeFrame.Minutes,
        compression=5,
    )
    cerebro.adddata(data)
    cerebro.broker.setcash(100000.0)
    cerebro.run()

    trades_path = PROJECT_ROOT / out_file
    if not trades_path.exists():
        print(f"WARN: No output for {symbol}.")
        return
    df = pd.read_csv(trades_path)
    if df.empty:
        print(f"INFO: No trades for {symbol}.")
        return
    # Performance metrics
    pips = df['Pips']
    summary = {
        'Symbol': symbol,
        'Trades': len(df),
        'WinRate': (pips > 0).mean(),
        'AvgPips': pips.mean(),
        'MedianPips': pips.median(),
        'MeanWin': pips[pips > 0].mean() if (pips > 0).any() else 0.0,
        'MeanLoss': pips[pips <= 0].mean() if (pips <= 0).any() else 0.0,
        'Sharpe': _sharpe(pips),
        'KeepPercentParam': KEEP_PERCENT,
        'AngleTrailFactor': ANGLE_TRAIL_FACTOR,
    }
    # Reason counts
    reason_counts = df['Reason'].value_counts().to_dict()
    for r in ['EarlyExitDeltaNeg', 'EarlyExitBelowPercentile', 'AngleTrail', 'MaxHold']:
        summary[f'Reason_{r}'] = reason_counts.get(r, 0)
    # Delta stats
    if 'DeltaStd_1_2' in df.columns:
        pos_delta = df['DeltaStd_1_2'].dropna()
        summary['AvgDelta'] = pos_delta.mean() if not pos_delta.empty else 0.0
        summary['MedianDelta'] = pos_delta.median() if not pos_delta.empty else 0.0
    SUMMARY_ROWS.append(summary)


def main():  # noqa: D401
    for f in ASSET_FILES:
        run_asset(f)
    if SUMMARY_ROWS:
        summary_df = pd.DataFrame(SUMMARY_ROWS)
        out = PROJECT_ROOT / 'adaptive_asset_summary.csv'
        summary_df.to_csv(out, index=False)
        print('=== Adaptive Strategy Summary ===')
        print(summary_df.to_string(index=False))
    else:
        print('No summaries generated.')


if __name__ == '__main__':  # pragma: no cover
    main()
