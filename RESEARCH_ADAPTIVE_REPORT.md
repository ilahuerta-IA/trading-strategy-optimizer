# Adaptive EMA Crossover Research → Production Blueprint

## 1. Objective Recap
Investigate triple EMA crossover behavior (fast > medium & slow) on 5m FX pairs and derive robust, *post-entry* expansion features to filter and adaptively manage trades.

## 2. Data Engineering Evolution
1. Step A: Captured per-trade pre/post series (Std, AngleDiff) for 5 bars.
2. Step B: Derived early features (ΔStd_1_2, SpikeFlag, Cumulative_Expansion_2) and filter grid (F1–F5). Key finding: ΔStd_1_2 > 0 primary edge; naive early exit harmed performance.
3. Step C: Extended window to 10 bars, decile analysis, adaptive angle trailing, percentile concentration, multi-exit horizon study.
4. Extended Step C: Real 7–10 bar evaluation, percentile sweep, angle contraction parameter grid.
5. Adaptive Strategy: On-the-fly ΔStd_1_2 gating + rolling top percentile + angle trailing.

## 3. Core Empirical Findings
| Aspect | Finding | Action |
|--------|---------|--------|
| Early Expansion (ΔStd_1_2) | Strongly monotonic decile → top deciles show large positive expectancy | Use ΔStd_1_2 > 0 base filter; optional top X% concentration |
| SpikeFlag | Adds minimal edge once ΔStd_1_2 applied | Omit for simplicity |
| Fixed Hold Length | Sharpe peak at 5 bars, declines after | Keep 5-bar max horizon |
| Percentile Concentration | Sharpe rises as we restrict to top 30–40% | Parameterize keep_percent (40% default) |
| Angle Trailing | Angle contraction exit (0.85–0.90) improves Sharpe vs fixed | Adopt trailing with factor 0.90 |
| Longer Holds (7–10) | Deteriorate Sharpe | Avoid extension |

## 4. Parameter Grid Highlights
### Multi Exit Sharpe (ΔStd_1_2 > 0 universe)
5-bar highest across assets; longer horizons degrade risk-adjusted returns.

### Keep Percent (Top Positive ΔStd_1_2)
Top 30–40% range provides meaningful Sharpe lift; capacity vs performance tradeoff managed via keep_percent.

### Angle Contraction Factor
Sharpe increases with less aggressive contraction; 0.90 produced highest cross-asset Sharpe in sweep.

## 5. Adaptive Production Strategy Logic
1. Entry: On crossover (fast crosses above both medium & slow). Enter immediately.
2. Evaluation at Bar +2:
   - Compute ΔStd_1_2 = std(+2) - std(+1).
   - If ΔStd_1_2 ≤ 0 → exit (EarlyExitDeltaNeg).
   - If percentile filtering active (after warm-up) and ΔStd_1_2 below threshold → exit (EarlyExitBelowPercentile).
3. Angle Trailing (from bar +3): Exit when current angle_diff ≤ factor * running_max_angle_diff (factor=0.90) → AngleTrail.
4. Fallback: MaxHold at 5 bars if no earlier exit.
5. Warm-Up: Percentile filter activates after min_trades_for_threshold positive deltas collected.

## 6. Implementation Artifacts
- Research Strategy: `triemahl2_research.py` (configurable post_window & baseline exit).
- Extended Analyses: `step_b_feature_filters.py`, `step_c_advanced_analysis.py`, `step_c_extended_analysis.py`.
- Adaptive Strategy: `triemahl2_adaptive.py`.
- Batch Runners: `run_batch_triemahl2_research.py`, `run_batch_triemahl2_adaptive.py`.
- Threshold Count Augmentation: `augment_decile_thresholds_with_counts.py`.

## 7. Adaptive Batch Summary (keep_percent=40, angle_factor=0.90)
Refer to `adaptive_asset_summary.csv` for exact figures.
Key distributions show large proportion of early exits due to percentile and delta filters, validating selective concentration.

## 8. Recommended Default Configuration
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| keep_percent | 40 | Balances Sharpe and trade count |
| angle_trail_factor | 0.90 | Best Sharpe without over-trimming |
| max_hold_bars | 5 | Empirical optimum |
| min_trades_for_threshold | 300 | Stabilize percentile estimation |

## 9. Validation & Next Steps
### Suggested Further Work
- Add rolling out-of-sample validation (temporal walk-forward windows).
- Evaluate transaction cost sensitivity (slippage/spread) per filter level.
- Consider volatility regime segmentation (ATR quantiles) for dynamic keep_percent.
- Capture raw bar OHLC for post-window beyond 10 for robustness tests.
- Implement unit tests for angle trailing edge cases.

### Risk Notes
- Percentile filter relies on stationarity of ΔStd_1_2 distribution; monitor drift.
- Angle trailing may exit during temporary compression before further expansion in trending shifts; consider adaptive smoothing.

## 10. Blueprint Summary
Entry: Crossover → provisional.
Qualification (bar +2): Require ΔStd_1_2 > 0 AND (if active) ≥ percentile threshold.
Management: Angle trailing (factor 0.90) else max 5-bar exit.
Concentration Lever: keep_percent adjustable for capacity vs. Sharpe.

---
Generated automatically by research pipeline. Modify as insights evolve.
