"""
ERIS Strategy Optimizer - Automated Parameter Optimization
===========================================================

This script uses Backtrader's built-in optimization framework to find
optimal parameters for the ERIS mean reversion strategy.

USAGE
-----
1. Configure optimization parameters in OPTIMIZATION_CONFIG section
2. Run: python -m src.strategies.eris_optimizer
3. Results are saved to temp_reports/optimization_results.csv

PARAMETERS TO OPTIMIZE
----------------------
These parameters CANNOT be analyzed from trade logs and require re-backtesting:

1. MEAN_REVERSION_EMA_PERIOD: Defines the "mean" for mean reversion
   - Shorter = more responsive, more signals
   - Longer = smoother, fewer but higher quality signals

2. OVERSOLD_ZSCORE_THRESHOLD: Threshold for counting "oversold" candles
   - Less negative (e.g., -0.5) = enters oversold zone sooner
   - More negative (e.g., -2.0) = only counts deeply oversold

3. MEAN_REVERSION_DEVIATION_MULT: Band width multiplier
   - Smaller = tighter bands, more "extreme" signals
   - Larger = wider bands, fewer signals

EDUCATIONAL NOTES
-----------------
- cerebro.optstrategy() runs multiple backtests in parallel
- Each combination of parameters is tested independently
- Results are collected via analyzers (SharpeRatio, DrawDown, TradeAnalyzer)
- Use maxcpus parameter to control parallel execution

DISCLAIMER
----------
Educational and research purposes ONLY. Not investment advice.
Past performance does not guarantee future results.
"""

from __future__ import annotations

import sys
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

import backtrader as bt

# Import the base strategy and configuration
from src.strategies.eris_template import (
    Eris,
    ForexCommission,
    DATA_FILENAME,
    FROMDATE,
    TODATE,
    STARTING_CASH,
    FOREX_INSTRUMENT,
    RESAMPLE_MINUTES,
    _CURRENT_CONFIG,
    USE_FIXED_COMMISSION,
)


# =============================================================================
# OPTIMIZATION CONFIGURATION
# =============================================================================

OPTIMIZATION_CONFIG = {
    # Parameters to optimize (lists of values to test)
    'mean_reversion_ema_period': [50, 70, 100, 150],
    'oversold_zscore_threshold': [-0.5, -1.0, -1.5, -2.0],
    
    # Optional: Additional parameters to optimize
    # Uncomment to include in optimization (increases combinations exponentially)
    # 'mean_reversion_deviation_mult': [1.5, 2.0, 2.5],
    # 'oversold_min_candles': [3, 6, 10],
    # 'oversold_max_candles': [8, 11, 15],
}

# Optimization settings
MAX_CPUS = 1  # Set to 1 for debugging, higher for speed (0 = all cores)
DISABLE_PRINT_SIGNALS = True  # Disable strategy prints during optimization


# =============================================================================
# OPTIMIZATION RESULTS ANALYZER
# =============================================================================

class OptimizationAnalyzer:
    """Collects and analyzes optimization results."""
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
    
    def add_result(self, params: Dict, metrics: Dict):
        """Add a single optimization result."""
        result = {**params, **metrics}
        self.results.append(result)
    
    def get_best_by_metric(self, metric: str, ascending: bool = False) -> Dict:
        """Get the best result by a specific metric."""
        if not self.results:
            return {}
        
        sorted_results = sorted(
            self.results,
            key=lambda x: x.get(metric, float('-inf') if not ascending else float('inf')),
            reverse=not ascending
        )
        return sorted_results[0]
    
    def save_to_csv(self, filepath: Path):
        """Save all results to CSV file."""
        if not self.results:
            print("No results to save")
            return
        
        fieldnames = list(self.results[0].keys())
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.results)
        
        print(f"Results saved to: {filepath}")
    
    def print_summary(self):
        """Print optimization summary."""
        if not self.results:
            print("No results to summarize")
            return
        
        print("\n" + "=" * 80)
        print("OPTIMIZATION RESULTS SUMMARY")
        print("=" * 80)
        print(f"Total combinations tested: {len(self.results)}")
        print()
        
        # Best by Profit Factor
        best_pf = self.get_best_by_metric('profit_factor')
        print("BEST BY PROFIT FACTOR:")
        print(f"  EMA Period: {best_pf.get('ema_period')}")
        print(f"  Oversold Threshold: {best_pf.get('oversold_threshold')}")
        print(f"  PF: {best_pf.get('profit_factor', 0):.2f}")
        print(f"  Trades: {best_pf.get('total_trades', 0)}")
        print(f"  Net P&L: ${best_pf.get('net_pnl', 0):,.0f}")
        print()
        
        # Best by Sharpe Ratio
        best_sharpe = self.get_best_by_metric('sharpe_ratio')
        print("BEST BY SHARPE RATIO:")
        print(f"  EMA Period: {best_sharpe.get('ema_period')}")
        print(f"  Oversold Threshold: {best_sharpe.get('oversold_threshold')}")
        print(f"  Sharpe: {best_sharpe.get('sharpe_ratio', 0):.2f}")
        print(f"  Trades: {best_sharpe.get('total_trades', 0)}")
        print(f"  Net P&L: ${best_sharpe.get('net_pnl', 0):,.0f}")
        print()
        
        # Best by Net P&L (with minimum trades filter)
        valid_results = [r for r in self.results if r.get('total_trades', 0) >= 50]
        if valid_results:
            best_pnl = max(valid_results, key=lambda x: x.get('net_pnl', float('-inf')))
            print("BEST BY NET P&L (min 50 trades):")
            print(f"  EMA Period: {best_pnl.get('ema_period')}")
            print(f"  Oversold Threshold: {best_pnl.get('oversold_threshold')}")
            print(f"  PF: {best_pnl.get('profit_factor', 0):.2f}")
            print(f"  Trades: {best_pnl.get('total_trades', 0)}")
            print(f"  Net P&L: ${best_pnl.get('net_pnl', 0):,.0f}")
        
        print("=" * 80)


# =============================================================================
# OPTIMIZATION STRATEGY WRAPPER
# =============================================================================

class ErisOptimizable(Eris):
    """
    Wrapper around Eris strategy for optimization.
    
    Adds analyzers and disables verbose output during optimization runs.
    """
    
    params = dict(
        # Inherit all Eris params, override for optimization
        print_signals=False,  # Always disable during optimization
        EXPORT_TRADE_REPORTS=False,  # Disable file exports during optimization
    )
    
    def stop(self):
        """Called at end of backtest - store results for optimization."""
        # Calculate metrics
        win_rate = (self.wins / self.trades * 100) if self.trades > 0 else 0
        profit_factor = (self.gross_profit / self.gross_loss) if self.gross_loss > 0 else 0
        net_pnl = self.broker.get_value() - STARTING_CASH
        
        # Store for optimization framework
        self.optimization_results = {
            'total_trades': self.trades,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'gross_profit': self.gross_profit,
            'gross_loss': self.gross_loss,
            'net_pnl': net_pnl,
            'final_value': self.broker.get_value(),
        }


# =============================================================================
# MAIN OPTIMIZATION FUNCTION
# =============================================================================

def run_optimization():
    """
    Run parameter optimization for ERIS strategy.
    
    Uses Backtrader's optstrategy to test multiple parameter combinations
    and find the optimal settings.
    """
    print("=" * 80)
    print("ERIS STRATEGY OPTIMIZER")
    print("=" * 80)
    print(f"Asset: {FOREX_INSTRUMENT}")
    print(f"Period: {FROMDATE} to {TODATE}")
    print(f"Timeframe: {RESAMPLE_MINUTES}M")
    print()
    
    # Calculate total combinations
    total_combinations = 1
    for param, values in OPTIMIZATION_CONFIG.items():
        total_combinations *= len(values)
        print(f"  {param}: {values}")
    print()
    print(f"Total combinations to test: {total_combinations}")
    print("=" * 80)
    print()
    
    # =========================================================================
    # LOAD DATA
    # =========================================================================
    data_path = Path(__file__).parent.parent.parent / "data" / DATA_FILENAME
    
    if not data_path.exists():
        print(f"ERROR: Data file not found: {data_path}")
        sys.exit(1)
    
    print(f"Loading data from: {data_path}")
    
    # Parse dates
    fromdate = datetime.strptime(FROMDATE, '%Y-%m-%d')
    todate = datetime.strptime(TODATE, '%Y-%m-%d')
    
    # Create data feed (same format as eris_template)
    data = bt.feeds.GenericCSVData(
        dataname=str(data_path),
        dtformat='%Y%m%d',
        tmformat='%H:%M:%S',
        datetime=0,
        time=1,
        open=2,
        high=3,
        low=4,
        close=5,
        volume=6,
        timeframe=bt.TimeFrame.Minutes,
        compression=5,
        fromdate=fromdate,
        todate=todate,
    )
    
    # =========================================================================
    # CREATE CEREBRO WITH OPTIMIZATION
    # =========================================================================
    cerebro = bt.Cerebro(
        optreturn=False,  # Return full strategy objects (not just params)
        stdstats=False,   # Disable standard stats for speed
    )
    
    # Add data with resampling if needed
    if RESAMPLE_MINUTES > 5:
        cerebro.resampledata(
            data,
            timeframe=bt.TimeFrame.Minutes,
            compression=RESAMPLE_MINUTES,
            name=FOREX_INSTRUMENT
        )
    else:
        cerebro.adddata(data, name=FOREX_INSTRUMENT)
    
    # Configure broker
    cerebro.broker.setcash(STARTING_CASH)
    
    is_jpy = _CURRENT_CONFIG.get('is_jpy', 'JPY' in FOREX_INSTRUMENT)
    commission_info = ForexCommission(is_jpy_pair=is_jpy, jpy_rate=150.0)
    cerebro.broker.addcommissioninfo(commission_info, name=FOREX_INSTRUMENT)
    
    # =========================================================================
    # ADD STRATEGY WITH OPTIMIZATION PARAMETERS
    # =========================================================================
    cerebro.optstrategy(
        ErisOptimizable,
        # Parameters to optimize
        mean_reversion_ema_period=OPTIMIZATION_CONFIG.get('mean_reversion_ema_period', [70]),
        oversold_zscore_threshold=OPTIMIZATION_CONFIG.get('oversold_zscore_threshold', [-1.0]),
        mean_reversion_deviation_mult=OPTIMIZATION_CONFIG.get('mean_reversion_deviation_mult', [2.0]),
        oversold_min_candles=OPTIMIZATION_CONFIG.get('oversold_min_candles', [6]),
        oversold_max_candles=OPTIMIZATION_CONFIG.get('oversold_max_candles', [11]),
        # Enable filters to see optimization effect
        print_signals=False,
        use_mean_reversion_entry_filter=True,   # ENABLED for optimization
        use_oversold_duration_filter=True,      # ENABLED for optimization
        # Fixed Z-Score range for entry filter (oversold zone)
        mr_entry_zscore_min=[-3.0],
        mr_entry_zscore_max=[-1.0],
    )
    
    # =========================================================================
    # RUN OPTIMIZATION
    # =========================================================================
    print("Starting optimization...")
    print(f"Using {MAX_CPUS if MAX_CPUS > 0 else 'all'} CPU cores")
    print()
    
    start_time = datetime.now()
    
    # Run with specified CPU count
    results = cerebro.run(maxcpus=MAX_CPUS)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\nOptimization completed in {duration:.1f} seconds")
    print(f"Speed: {total_combinations / duration:.1f} combinations/second")
    
    # =========================================================================
    # COLLECT AND ANALYZE RESULTS
    # =========================================================================
    analyzer = OptimizationAnalyzer()
    
    for strategy_list in results:
        for strategy in strategy_list:
            # Extract parameters
            params = {
                'ema_period': strategy.p.mean_reversion_ema_period,
                'oversold_threshold': strategy.p.oversold_zscore_threshold,
                'deviation_mult': strategy.p.mean_reversion_deviation_mult,
                'min_candles': strategy.p.oversold_min_candles,
                'max_candles': strategy.p.oversold_max_candles,
            }
            
            # Extract metrics from strategy
            metrics = getattr(strategy, 'optimization_results', {})
            
            # Calculate Sharpe Ratio from portfolio values if available
            sharpe = 0.0
            if hasattr(strategy, '_portfolio_values') and len(strategy._portfolio_values) > 10:
                import numpy as np
                values = strategy._portfolio_values
                returns = [(values[i] - values[i-1]) / values[i-1] 
                          for i in range(1, len(values)) if values[i-1] > 0]
                if returns:
                    mean_ret = np.mean(returns)
                    std_ret = np.std(returns)
                    if std_ret > 0:
                        periods_per_year = 252 * 24 * (60 // RESAMPLE_MINUTES)
                        sharpe = (mean_ret / std_ret) * np.sqrt(periods_per_year)
            
            metrics['sharpe_ratio'] = sharpe
            
            analyzer.add_result(params, metrics)
    
    # =========================================================================
    # SAVE AND DISPLAY RESULTS
    # =========================================================================
    # Save to CSV
    report_dir = Path(__file__).parent / "temp_reports"
    report_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = report_dir / f"optimization_{FOREX_INSTRUMENT}_{timestamp}.csv"
    analyzer.save_to_csv(csv_path)
    
    # Print summary
    analyzer.print_summary()
    
    # Print all results sorted by PF
    print("\nALL RESULTS (sorted by Profit Factor):")
    print("-" * 80)
    print(f"{'EMA':>6} {'Thresh':>8} {'Trades':>8} {'WR%':>8} {'PF':>8} {'Net P&L':>12} {'Sharpe':>8}")
    print("-" * 80)
    
    sorted_results = sorted(
        analyzer.results,
        key=lambda x: x.get('profit_factor', 0),
        reverse=True
    )
    
    for r in sorted_results[:20]:  # Top 20
        print(f"{r.get('ema_period', 0):>6} "
              f"{r.get('oversold_threshold', 0):>8.1f} "
              f"{r.get('total_trades', 0):>8} "
              f"{r.get('win_rate', 0):>7.1f}% "
              f"{r.get('profit_factor', 0):>8.2f} "
              f"${r.get('net_pnl', 0):>11,.0f} "
              f"{r.get('sharpe_ratio', 0):>8.2f}")
    
    print("-" * 80)
    
    return analyzer


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    run_optimization()
