"""Extended Step C Analysis using 10-bar post window.

Adds:
 1. Real multi-exit evaluation (5,6,7,8,9,10 bars) for F1 universe.
 2. Decile threshold sweep: evaluate performance for keeping top X% (30,40,50,60,70,80,90,100) of DeltaStd_1_2 among positive set.
 3. Angle contraction trailing sweep: contraction factors (0.9,0.85,0.8,0.75,0.7).

Produces:
 - step_c_multi_exit_<SYMBOL>.csv
 - step_c_decile_thresholds_<SYMBOL>.csv
 - step_c_angle_trailing_grid_<SYMBOL>.csv
 - Aggregated summaries: step_c_multi_exit_summary.csv, step_c_decile_thresholds_summary.csv, step_c_angle_trailing_grid_summary.csv

Run:
  python src/research/step_c_extended_analysis.py
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ASSETS = ["GBPUSD", "EURUSD", "USDCHF"]
INPUT_TEMPLATE = "ema_crossover_analysis_{sym}.csv"

EXIT_HORIZONS = [5,6,7,8,9,10]
DECILE_KEEP_PCTS = [30,40,50,60,70,80,90,100]
ANGLE_CONTRACTIONS = [0.9,0.85,0.8,0.75,0.7]


def load(sym: str) -> pd.DataFrame:
    df = pd.read_csv(PROJECT_ROOT / INPUT_TEMPLATE.format(sym=sym))
    def j(v):
        try:
            return json.loads(v) if isinstance(v,str) else (v if isinstance(v,list) else [])
        except Exception:
            return []
    df['Post_Pips_List'] = df['Post_Pips_Series'].apply(j)
    df['Post_AngDiff_List'] = df['Post_AngDiff_Series'].apply(j)
    # DeltaStd_1_2 recompute if absent
    if 'DeltaStd_1_2' not in df.columns:
        df['Post_Std_List'] = df['Post_Std_Series'].apply(j)
        df['DeltaStd_1_2'] = df['Post_Std_List'].apply(lambda lst: lst[1]-lst[0] if len(lst)>=2 else np.nan)
    return df


def perf(series: pd.Series) -> dict:
    if series.empty:
        return dict(Trades=0, Mean=0.0, WinRate=0.0, Sharpe=0.0)
    mean = series.mean()
    win = (series>0).mean()
    sd = series.std(ddof=0)
    sharpe = mean/sd if sd and not np.isclose(sd,0.0) else 0.0
    return dict(Trades=len(series), Mean=mean, WinRate=win, Sharpe=sharpe)


def multi_exit(df: pd.DataFrame) -> pd.DataFrame:
    base = df[df['DeltaStd_1_2']>0]
    rows = []
    for h in EXIT_HORIZONS:
        idx = h-1  # 0-based
        px = base['Post_Pips_List'].apply(lambda lst: lst[idx] if len(lst)>idx else np.nan).dropna()
        m = perf(px)
        m.update(Horizon=h)
        rows.append(m)
    return pd.DataFrame(rows)


def decile_thresholds(df: pd.DataFrame) -> pd.DataFrame:
    pos = df[df['DeltaStd_1_2']>0].copy()
    if pos.empty:
        return pd.DataFrame()
    pos = pos.replace([np.inf,-np.inf],np.nan).dropna(subset=['DeltaStd_1_2'])
    pos['Rank'] = pos['DeltaStd_1_2'].rank(method='first', ascending=True)
    total = len(pos)
    rows = []
    for pct in DECILE_KEEP_PCTS:
        keep_n = int(np.ceil(total * pct/100.0))
        subset = pos.nlargest(keep_n,'DeltaStd_1_2')
        m = perf(subset['Pips_Result'])
        m.update(KeepPercent=pct)
        rows.append(m)
    return pd.DataFrame(rows)


def angle_trailing_grid(df: pd.DataFrame) -> pd.DataFrame:
    base = df[df['DeltaStd_1_2']>0].copy()
    rows = []
    for factor in ANGLE_CONTRACTIONS:
        def apply_row(row):
            angs = row.Post_AngDiff_List
            pips = row.Post_Pips_List
            if len(angs)<=1 or len(pips)<len(angs):
                return pips[-1] if pips else row.Pips_Result
            run_max = angs[0]
            for i in range(1,len(angs)):
                if angs[i-1] > run_max:
                    run_max = angs[i-1]
                if angs[i] <= factor * run_max:
                    return pips[i] if i < len(pips) else pips[-1]
            return pips[-1]
        pnl = base.apply(apply_row, axis=1)
        m = perf(pnl)
        m.update(Contraction=factor)
        rows.append(m)
    return pd.DataFrame(rows)


def main():  # noqa: D401
    multi_all = []
    decile_all = []
    angle_all = []
    for sym in ASSETS:
        df = load(sym)
        mdf = multi_exit(df)
        mdf['Symbol'] = sym
        mdf.to_csv(PROJECT_ROOT / f'step_c_multi_exit_{sym}.csv', index=False)
        multi_all.append(mdf)

        ddf = decile_thresholds(df)
        ddf['Symbol'] = sym
        ddf.to_csv(PROJECT_ROOT / f'step_c_decile_thresholds_{sym}.csv', index=False)
        decile_all.append(ddf)

        adf = angle_trailing_grid(df)
        adf['Symbol'] = sym
        adf.to_csv(PROJECT_ROOT / f'step_c_angle_trailing_grid_{sym}.csv', index=False)
        angle_all.append(adf)

    if multi_all:
        pd.concat(multi_all).to_csv(PROJECT_ROOT / 'step_c_multi_exit_summary.csv', index=False)
    if decile_all:
        pd.concat(decile_all).to_csv(PROJECT_ROOT / 'step_c_decile_thresholds_summary.csv', index=False)
    if angle_all:
        pd.concat(angle_all).to_csv(PROJECT_ROOT / 'step_c_angle_trailing_grid_summary.csv', index=False)

    # Print high-level summaries
    if multi_all:
        print('=== Multi Exit (F1 universe) Sharpe by Horizon ===')
        print(pd.concat(multi_all).pivot(index='Horizon', columns='Symbol', values='Sharpe').round(4).to_string())
    if decile_all:
        print('\n=== Decile Threshold Keep% Sharpe ===')
        print(pd.concat(decile_all).pivot(index='KeepPercent', columns='Symbol', values='Sharpe').round(4).to_string())
    if angle_all:
        print('\n=== Angle Contraction Factor Sharpe ===')
        print(pd.concat(angle_all).pivot(index='Contraction', columns='Symbol', values='Sharpe').round(4).to_string())

if __name__ == '__main__':  # pragma: no cover
    main()
