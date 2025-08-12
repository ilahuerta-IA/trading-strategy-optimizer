"""Step C: Advanced Analysis of ΔStd_1_2 and Refined Adaptive Exit Logic.

This script builds on Step B outputs to:
 1. Perform decile analysis on ΔStd_1_2 per asset (and combined) -> decile mean pips & win rate.
 2. Evaluate refined adaptive exit strategies:
    a. Conditional Early Exit (CEE): For trades failing ΔStd_1_2 > 0 (i.e., <=0) AND Cumulative_Expansion_2 <= 0,
       exit at bar +2 pips; otherwise keep 5-bar result. Only applied inside SpikeFlag==0 universe.
    b. Angle Trailing Reduction (ATRail): For trades passing ΔStd_1_2 > 0, if angle diff contracts >=20% from
       its peak before bar 5, exit at the contraction bar's pips else keep 5-bar result.
       (Approximation: use Post_AngDiff_Series; earliest bar where ang <= 0.8 * max(previous max)).
    c. Extended Hold (EXT7): For top quantile (Q80 or top 2 deciles) ΔStd_1_2 trades, simulate 7-bar hold using
       extrapolated pips (NOTE: base dataset has only 5 bars; for demonstration we approximate by adding last delta
       between bar4->bar5 once per extra bar; flagged as estimation).

 3. Produce comparison tables versus baseline filters (F1/F3) with metrics.

Outputs:
 - step_c_deciles_<SYMBOL>.csv
 - step_c_deciles_combined.csv
 - step_c_exit_strategies_<SYMBOL>.csv
 - step_c_exit_summary.csv
 - step_c_blueprint.txt (strategy blueprint recommendations)

Limitations:
 - Extended hold simulation uses a naive extrapolation due to lack of raw bar data beyond +5 in current dataset.
   For production adoption, regenerate research captures with longer post window (e.g., 10 bars).

Run:
  python src/research/step_c_advanced_analysis.py
"""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ASSETS = ["GBPUSD", "EURUSD", "USDCHF"]
INPUT_TEMPLATE = "ema_crossover_analysis_{sym}.csv"

# ----------------------------- Helpers ----------------------------------

def _load(sym: str) -> pd.DataFrame:
    path = PROJECT_ROOT / INPUT_TEMPLATE.format(sym=sym)
    df = pd.read_csv(path)
    # Parse JSON series
    def _j(v):
        try:
            return json.loads(v) if isinstance(v, str) else (v if isinstance(v, list) else [])
        except Exception:
            return []
    df["Post_Std_List"] = df["Post_Std_Series"].apply(_j)
    df["Post_AngDiff_List"] = df["Post_AngDiff_Series"].apply(_j)
    df["Post_Pips_List"] = df.get("Post_Pips_Series", pd.Series(["[]"] * len(df))).apply(_j)
    # Derived from Step B if not present
    if "DeltaStd_1_2" not in df.columns:
        df["DeltaStd_1_2"] = df["Post_Std_List"].apply(lambda lst: lst[1]-lst[0] if len(lst) >=2 else np.nan)
    if "Cumulative_Expansion_2" not in df.columns:
        df["Cumulative_Expansion_2"] = df.apply(lambda r: (r.Post_Std_List[1] - r.Entry_Std) if len(r.Post_Std_List)>=2 else np.nan, axis=1)
    if "SpikeFlag" not in df.columns:
        df["SpikeFlag"] = df["Post_Std_List"].apply(lambda lst: 1 if (len(lst)>0 and np.argmax(lst)==0) else 0)
    return df


def _metrics(series: pd.Series) -> tuple[float,float,float]:
    mean = series.mean() if len(series) else 0.0
    win_rate = (series > 0).mean() if len(series) else 0.0
    std = series.std(ddof=0)
    sharpe = mean/std if std and not np.isclose(std,0.0) else 0.0
    return mean, win_rate, sharpe

# ---------------------- 1. Decile Analysis -------------------------------

def decile_analysis(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d = d.replace([np.inf, -np.inf], np.nan).dropna(subset=["DeltaStd_1_2"])  # require metric
    d['Decile'] = pd.qcut(d['DeltaStd_1_2'], 10, labels=False, duplicates='drop')  # 0..9
    rows = []
    for dec in sorted(d['Decile'].dropna().unique()):
        sub = d[d.Decile == dec]
        mean_p, wr, sharpe = _metrics(sub['Pips_Result'])
        rows.append(dict(Decile=int(dec), Count=len(sub), Mean_Pips=mean_p, Win_Rate=wr, Sharpe=sharpe,
                         DeltaStd_Range=f"{sub['DeltaStd_1_2'].min():.5f}..{sub['DeltaStd_1_2'].max():.5f}"))
    return pd.DataFrame(rows)

# ------------------ 2. Adaptive Exit Strategies -------------------------

def simulate_conditional_early_exit(df: pd.DataFrame) -> pd.Series:
    # Universe: SpikeFlag==0 only (consistent with F2 logic)
    # If (DeltaStd_1_2 <= 0) AND (Cumulative_Expansion_2 <= 0) exit at bar +2 pips
    # Else keep full 5-bar Pips_Result
    def _logic(row):
        if row.SpikeFlag == 0 and (not pd.isna(row.DeltaStd_1_2)) and row.DeltaStd_1_2 <= 0 and row.Cumulative_Expansion_2 <= 0:
            pl = row.Post_Pips_List[1] if len(row.Post_Pips_List) >= 2 else row.Pips_Result
            return pl
        return row.Pips_Result
    return df.apply(_logic, axis=1)


def simulate_angle_trailing(df: pd.DataFrame) -> pd.Series:
    # Apply only to trades passing DeltaStd_1_2 > 0 (winners candidates); otherwise keep Pips_Result.
    # For those, if angle diff contracts >=20% from its previous max before end, exit at first contraction bar.
    def _logic(row):
        if pd.isna(row.DeltaStd_1_2) or row.DeltaStd_1_2 <= 0:
            return row.Pips_Result
        angs = row.Post_AngDiff_List
        pips = row.Post_Pips_List
        if len(angs) <= 1 or len(pips) < len(angs):
            return row.Pips_Result
        running_max = angs[0]
        # Walk through bars +2..+5 (index 1..4). If ang <= 0.8 * running_max, exit at prior bar pips (current bar close not yet decisive) -> use current index pips value.
        for i in range(1, len(angs)):
            running_max = max(running_max, angs[i-1])
            threshold = 0.8 * running_max
            if angs[i] <= threshold:
                # Exit at this bar's pips.
                if i < len(pips):
                    return pips[i]
                return row.Pips_Result
        return row.Pips_Result
    return df.apply(_logic, axis=1)


def simulate_extended_hold(df: pd.DataFrame) -> pd.Series:
    # Approximate 7-bar hold for top 20% DeltaStd_1_2 trades using last bar momentum extrapolation.
    if df.empty:
        return pd.Series([], dtype=float)
    cutoff = df['DeltaStd_1_2'].quantile(0.80)
    def _logic(row):
        if pd.isna(row.DeltaStd_1_2) or row.DeltaStd_1_2 < cutoff:
            return row.Pips_Result  # keep 5-bar result
        # Extrapolate using last increment between bar4 and bar5
        pips_list = row.Post_Pips_List
        if len(pips_list) >= 5:
            # last increment (bar5 - bar4)
            last_inc = pips_list[4] - pips_list[3] if len(pips_list) >=5 else 0.0
            # add two increments
            return pips_list[4] + 2 * last_inc
        return row.Pips_Result
    return df.apply(_logic, axis=1)


def evaluate_exits(df: pd.DataFrame) -> pd.DataFrame:
    base_universe = df[df['DeltaStd_1_2'] > 0]  # baseline profitable filter

    strategies = []
    def _collect(name, series):
        mean_p, wr, sharpe = _metrics(series)
        strategies.append(dict(Strategy=name, Trades=len(series), Mean_Pips=mean_p, Win_Rate=wr, Sharpe=sharpe))

    # Baseline fixed 5-bar exit (F1)
    _collect('Baseline_F1_Fixed5', base_universe['Pips_Result'])
    # Conditional Early Exit (applied to whole df then subset to F2 universe for comparability)
    cee_series = simulate_conditional_early_exit(df)
    cee_filter = df[df['DeltaStd_1_2'] > 0]  # we measure only on trades we would take
    _collect('CEE_on_F1Universe', cee_series[cee_filter.index])
    # Angle trailing
    atrail_series = simulate_angle_trailing(df)
    _collect('AngleTrail_on_F1Universe', atrail_series[cee_filter.index])
    # Extended hold (approximation)
    ext_series = simulate_extended_hold(df)
    _collect('Extended7_on_F1Universe', ext_series[cee_filter.index])

    return pd.DataFrame(strategies)

# --------------------------- Main ---------------------------------------

def main():  # noqa: D401
    all_deciles = []
    all_exit_results = []
    combined_rows = []

    for sym in ASSETS:
        df = _load(sym)
        dec = decile_analysis(df)
        dec['Symbol'] = sym
        dec_out = PROJECT_ROOT / f'step_c_deciles_{sym}.csv'
        dec.to_csv(dec_out, index=False)
        all_deciles.append(dec)

        exits = evaluate_exits(df)
        exits['Symbol'] = sym
        exits_out = PROJECT_ROOT / f'step_c_exit_strategies_{sym}.csv'
        exits.to_csv(exits_out, index=False)
        all_exit_results.append(exits)

        # Append for combined deciles (pooling normalized approach later if needed)
        combined_rows.append(df)

    # Combined deciles (pooled)
    combined_df = pd.concat(combined_rows, ignore_index=True)
    combined_dec = decile_analysis(combined_df)
    combined_dec['Symbol'] = 'ALL'
    combined_dec.to_csv(PROJECT_ROOT / 'step_c_deciles_combined.csv', index=False)

    # Exit summary merged
    exit_summary = pd.concat(all_exit_results, ignore_index=True)
    exit_summary.to_csv(PROJECT_ROOT / 'step_c_exit_summary.csv', index=False)

    # Blueprint recommendation (initial heuristic based on results)
    blueprint_lines = []
    blueprint_lines.append('Strategy Blueprint (Draft)')
    blueprint_lines.append('Entry: Require DeltaStd_1_2 > 0 (optionally consider threshold at decile where mean pips markedly jumps).')
    blueprint_lines.append('Secondary: Avoid SpikeFlag trades optional (low marginal impact).')
    blueprint_lines.append('Exit: If Angle trailing contraction threshold yields higher Sharpe than fixed 5, adopt; else keep fixed 5.')
    blueprint_lines.append('Early Failure Handling: Consider CEE only if it improves Sharpe without reducing mean excessively.')
    blueprint_lines.append('Extended Hold: Defer until longer post window data is collected (current extrapolation is placeholder).')
    (PROJECT_ROOT / 'step_c_blueprint.txt').write_text('\n'.join(blueprint_lines), encoding='utf-8')

    # Console print highlights
    print('=== Step C Combined Decile Summary (ΔStd_1_2) ===')
    print(combined_dec[['Decile','Count','Mean_Pips','Win_Rate','Sharpe','DeltaStd_Range']].to_string(index=False))
    print('\n=== Step C Exit Strategy Summary ===')
    print(exit_summary.pivot(index='Strategy', columns='Symbol', values='Sharpe').round(4).to_string())


if __name__ == '__main__':  # pragma: no cover
    main()
