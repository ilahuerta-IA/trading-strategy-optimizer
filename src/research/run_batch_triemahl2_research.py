"""Batch runner for Triemahl2ResearchStrategy across multiple assets.

Generates per-asset crossover research CSVs plus an aggregated summary.

Outputs:
 - ema_crossover_analysis_<SYMBOL>.csv for each asset
 - ema_crossover_asset_summary.csv (aggregate performance & key correlations)
"""

from __future__ import annotations

import backtrader as bt
import pandas as pd
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_STRATEGY_PATH = PROJECT_ROOT / 'src' / 'strategies'
sys.path.insert(0, str(SRC_STRATEGY_PATH))  # ensure import path

from triemahl2_research import Triemahl2ResearchStrategy  # type: ignore  # noqa: E402


ASSET_FILES = [
    'GBPUSD_5m_8Yea.csv',
    'EURUSD_5m_8Yea.csv',
    'USDCHF_5m_8Yea.csv',
]

DATA_DIR = PROJECT_ROOT / 'data'

SUMMARY_ROWS = []


def run_for_asset(csv_name: str):
    symbol = csv_name.split('_')[0]  # e.g. GBPUSD
    data_path = DATA_DIR / csv_name
    if not data_path.exists():
        print(f"WARN: Missing data file {data_path}, skipping.")
        return
    output_file = f"ema_crossover_analysis_{symbol}.csv"

    cerebro = bt.Cerebro()
    cerebro.addstrategy(
        Triemahl2ResearchStrategy,
        output_csv=output_file,
        verbose=False,
        post_window=10,       # extended capture window
        baseline_exit=5,       # keep baseline comparability
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

    # Load produced CSV and compute summary metrics
    out_path = PROJECT_ROOT / output_file
    if not out_path.exists():
        print(f"WARN: Output not found for {symbol}: {out_path}")
        return
    df = pd.read_csv(out_path)
    # Basic metrics
    total = len(df)
    win_rate = (df['Result_Binary'] == 1).mean() if total else 0
    avg_pips = df['Pips_Result'].mean() if total else 0
    median_pips = df['Pips_Result'].median() if total else 0
    pos_mean = df.loc[df.Pips_Result > 0, 'Pips_Result'].mean() if (df.Pips_Result > 0).any() else 0
    neg_mean = df.loc[df.Pips_Result <= 0, 'Pips_Result'].mean() if (df.Pips_Result <= 0).any() else 0
    corr_diver_post = df['Pips_Result'].corr(df['Tasa_Diver_PostCruce']) if 'Tasa_Diver_PostCruce' in df else 0
    corr_prediff = df['Pips_Result'].corr(df['Max_Diferencia_EMAs_PreCruce']) if 'Max_Diferencia_EMAs_PreCruce' in df else 0
    SUMMARY_ROWS.append({
        'Symbol': symbol,
        'Trades': total,
        'WinRate': win_rate,
        'AvgPips': avg_pips,
        'MedianPips': median_pips,
        'MeanWin': pos_mean,
        'MeanLoss': neg_mean,
        'Corr_Pips_Tasa_Diver_Post': corr_diver_post,
        'Corr_Pips_Max_PreDiff': corr_prediff,
    })


def main():  # noqa: D401
    for csv_name in ASSET_FILES:
        run_for_asset(csv_name)
    if SUMMARY_ROWS:
        summary_df = pd.DataFrame(SUMMARY_ROWS)
        summary_path = PROJECT_ROOT / 'ema_crossover_asset_summary.csv'
        summary_df.to_csv(summary_path, index=False)
        print("=== Asset Summary ===")
        print(summary_df.to_string(index=False))
    else:
        print("No summaries generated.")


if __name__ == '__main__':  # pragma: no cover
    main()
