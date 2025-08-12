"""Step B: Feature Extraction & Filter Evaluation for Triemahl2 Research Data.

Loads per-asset research CSVs with JSON series columns, derives early post-entry
features, evaluates filters F1-F5, and produces comparative summary outputs.

Outputs:
 - step_b_filters_<SYMBOL>.csv (per-asset filter performance table)
 - step_b_filters_summary.csv (merged across assets)
 - step_b_feature_sample_<SYMBOL>.csv (optional sampled enriched trades for inspection)

Filters:
 F1: ΔStd_1_2 > 0
 F2: SpikeFlag == 0  (i.e., Periodo_Max_Diverg_PostCruce != 1)
 F3: F1 & F2
 F4: F3 & Max_Diferencia_EMAs_PreCruce < p90 (asset-specific 90th percentile)
 F5: Adaptive exit variant of F3: if ΔStd_1_2 <= 0 then override Pips_Result with
     Pips at bar 2 (Post_Pips_Series[1]) simulating an early exit; evaluate on
     modified Pips column (Risk-adjusted improvement test).

Computed Derived Columns:
 - Post_Std_List (list)
 - Post_Pips_List (list)
 - DeltaStd_1_2 (Std@+2 - Std@+1)
 - SpikeFlag (1 if max std occurs on +1 bar else 0)
 - Cumulative_Expansion_2 (Std@+2 - Entry_Std)
 - Adaptive_Pips_F5 (Pips with adaptive early exit logic applied)

Sharpe_Proxy = mean(Pips) / std(Pips) (population std, fallbacks handled)

Usage (run from project root virtualenv):
  python src/research/step_b_feature_filters.py
"""

from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ASSETS = ["GBPUSD", "EURUSD", "USDCHF"]
INPUT_TEMPLATE = "ema_crossover_analysis_{sym}.csv"

PER_ASSET_RESULTS = []


def _safe_json_list(val):
    if pd.isna(val):
        return []
    if isinstance(val, (list, tuple)):
        return list(val)
    try:
        return json.loads(val)
    except Exception:
        return []


def enrich_asset(sym: str) -> pd.DataFrame:
    path = PROJECT_ROOT / INPUT_TEMPLATE.format(sym=sym)
    if not path.exists():
        raise FileNotFoundError(f"Missing input {path}")
    df = pd.read_csv(path)

    # Parse JSON series
    df["Post_Std_List"] = df["Post_Std_Series"].apply(_safe_json_list)
    df["Post_Pips_List"] = df.get("Post_Pips_Series", pd.Series(["[]"] * len(df))).apply(_safe_json_list)

    # Derived features (guard for length >=2)
    def delta_std(row):
        lst = row.Post_Std_List
        return lst[1] - lst[0] if len(lst) >= 2 else np.nan

    def spike_flag(row):
        lst = row.Post_Std_List
        if not lst:
            return 0
        max_idx = int(np.argmax(lst))  # 0-based where 0 => +1 bar
        return 1 if max_idx == 0 else 0

    def cum_expansion(row):
        lst = row.Post_Std_List
        if len(lst) >= 2:
            return lst[1] - row.Entry_Std if not pd.isna(row.Entry_Std) else np.nan
        return np.nan

    df["DeltaStd_1_2"] = df.apply(delta_std, axis=1)
    df["SpikeFlag"] = df.apply(spike_flag, axis=1)
    df["Cumulative_Expansion_2"] = df.apply(cum_expansion, axis=1)

    # Prepare adaptive pips for F5
    def adaptive_pips(row):
        base = row.Pips_Result
        if np.isnan(row.DeltaStd_1_2):
            return base
        if row.DeltaStd_1_2 <= 0:
            # Use pips at bar +2 if available
            lst = row.Post_Pips_List
            if len(lst) >= 2:
                return lst[1]
            return base
        return base

    df["Adaptive_Pips_F5"] = df.apply(adaptive_pips, axis=1)
    return df


def compute_metrics(df: pd.DataFrame, pips_col: str) -> dict:
    if df.empty:
        return dict(Trades=0, Trades_Kept_Percent=0.0, New_Avg_Pips=0.0, New_Win_Rate=0.0, Sharpe_Proxy=0.0)
    mean_pips = df[pips_col].mean()
    std_pips = df[pips_col].std(ddof=0)
    sharpe = (mean_pips / std_pips) if std_pips and not np.isclose(std_pips, 0.0) else 0.0
    return dict(
        Trades=len(df),
        Trades_Kept_Percent=100.0 * len(df) / TOTAL_TRADES_CONTEXT if TOTAL_TRADES_CONTEXT else 0.0,
        New_Avg_Pips=mean_pips,
        New_Win_Rate=(df[pips_col] > 0).mean(),
        Sharpe_Proxy=sharpe,
    )


def evaluate_filters(df: pd.DataFrame, sym: str) -> pd.DataFrame:
    global TOTAL_TRADES_CONTEXT
    TOTAL_TRADES_CONTEXT = len(df)

    # Percentile for F4
    p90 = df["Max_Diferencia_EMAs_PreCruce"].quantile(0.90) if not df.empty else np.nan

    # Filter definitions return (name, subset, pips_col)
    filters = []
    # F1
    filters.append(("F1_DeltaStdPos", df[df["DeltaStd_1_2"] > 0], "Pips_Result"))
    # F2
    filters.append(("F2_NoSpike", df[df["SpikeFlag"] == 0], "Pips_Result"))
    # F3
    f3_df = df[(df["DeltaStd_1_2"] > 0) & (df["SpikeFlag"] == 0)]
    filters.append(("F3_F1andF2", f3_df, "Pips_Result"))
    # F4 (soft exclusion pre diff < p90) applied to F3 subset
    f4_df = f3_df[f3_df["Max_Diferencia_EMAs_PreCruce"] < p90] if not np.isnan(p90) else f3_df
    filters.append(("F4_F3_PreDiff_lt_p90", f4_df, "Pips_Result"))
    # F5 adaptive pips (use full set but with adaptive pips applied only to those failing F1 within F3 logic?)
    # Definition per prompt: Apply F3, but if DeltaStd_1_2 <= 0 at Bar2 use bar2 pips. That means we start from trades passing F2 (no spike) and then adapt F1 condition by substituting pips early when F1 fails.
    # Simpler interpretation: Take subset with SpikeFlag==0 (F2) and apply adaptive pips override for all, then require DeltaStd_1_2 >? The prompt says "apply F3, but if ΔStd_1_2 <= 0 ... pips at Bar2" so we keep only SpikeFlag==0 trades (F2) and use Adaptive_Pips_F5 where DeltaStd <=0 else final pips.
    f5_base = df[df["SpikeFlag"] == 0].copy()
    f5_base["Pips_F5"] = np.where(f5_base["DeltaStd_1_2"] <= 0, f5_base["Adaptive_Pips_F5"], f5_base["Pips_Result"])
    filters.append(("F5_Adaptive_F3", f5_base, "Pips_F5"))

    rows = []
    for name, subset, pips_col in filters:
        met = compute_metrics(subset, pips_col)
        met.update(Filter=name, Symbol=sym)
        rows.append(met)
    return pd.DataFrame(rows)


def main():  # noqa: D401
    all_results = []
    for sym in ASSETS:
        df = enrich_asset(sym)
        res_df = evaluate_filters(df, sym)
        all_results.append(res_df)
        # Per-asset outputs
        res_out = PROJECT_ROOT / f"step_b_filters_{sym}.csv"
        res_df.to_csv(res_out, index=False)
        # Optional sample enriched trades
        sample_out = PROJECT_ROOT / f"step_b_feature_sample_{sym}.csv"
        df.head(500).to_csv(sample_out, index=False)

    if all_results:
        merged = pd.concat(all_results, ignore_index=True)
        summary_path = PROJECT_ROOT / "step_b_filters_summary.csv"
        merged.to_csv(summary_path, index=False)
        # Pivot summary wide format
        pivot_cols = ["Trades_Kept_Percent", "New_Avg_Pips", "New_Win_Rate", "Sharpe_Proxy"]
        wide_tables = []
        for metric in pivot_cols:
            wide = merged.pivot(index="Filter", columns="Symbol", values=metric)
            wide_tables.append((metric, wide))
        # Print concise console report
        print("=== Step B Filter Evaluation Summary ===")
        for metric, wide in wide_tables:
            print(f"\n-- {metric} --")
            print(wide.round(4).to_string())


if __name__ == "__main__":  # pragma: no cover
    main()
