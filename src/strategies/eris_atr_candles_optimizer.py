"""
ERIS ATR + Candles Optimizer
============================
Grid search para encontrar el balance óptimo entre:
- ATR_MAX_THRESHOLD: Filtrar alta volatilidad
- OVERSOLD_MIN_CANDLES: Mínimo de velas en zona oversold

Métricas evaluadas: PF, Sharpe, Sortino, MaxDD, Calmar, Win Rate
"""

import sys
from pathlib import Path
from datetime import datetime
from itertools import product
import numpy as np

import backtrader as bt

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.strategies.eris_template import (
    Eris, ForexCommission, 
    STARTING_CASH, FOREX_INSTRUMENT, RESAMPLE_MINUTES,
    _CURRENT_CONFIG
)

# =============================================================================
# OPTIMIZATION GRID
# =============================================================================
# ATR max thresholds to test (filters out high volatility)
ATR_MAX_VALUES = [0.00025, 0.00030, 0.00035, 0.00040, 0.00045, 0.00050, 0.00060, 0.00070, 0.00080, 0.00100]

# Minimum oversold candles to test
CANDLES_MIN_VALUES = [6, 7, 8, 9, 10, 11, 12]

# Date range
FROMDATE = '2020-01-01'
TODATE = '2025-06-01'

# Data file
DATA_FILE = PROJECT_ROOT / 'data' / 'USDCHF_5m_5Yea.csv'


# =============================================================================
# STRATEGY WRAPPER
# =============================================================================
class ErisTest(Eris):
    """Wrapper that captures detailed metrics."""
    
    params = dict(
        print_signals=False,
        EXPORT_TRADE_REPORTS=False,
    )
    
    def __init__(self):
        super().__init__()
        self._daily_values = []
        self._last_date = None
        
    def next(self):
        super().next()
        # Track daily portfolio values for Sharpe/Sortino
        current_date = self.data.datetime.date(0)
        if current_date != self._last_date:
            self._daily_values.append(self.broker.get_value())
            self._last_date = current_date


def calculate_metrics(strategy, initial_cash):
    """Calculate comprehensive metrics from strategy results."""
    
    trades = strategy.trades
    wins = strategy.wins
    losses = strategy.losses
    gross_profit = strategy.gross_profit
    gross_loss = strategy.gross_loss
    final_value = strategy.broker.get_value()
    net_pnl = final_value - initial_cash
    
    # Basic metrics
    win_rate = (wins / trades * 100) if trades > 0 else 0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
    
    # Daily returns for risk metrics
    daily_values = strategy._daily_values
    if len(daily_values) < 10:
        return {
            'trades': trades,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'pf': profit_factor,
            'net_pnl': net_pnl,
            'sharpe': 0,
            'sortino': 0,
            'max_dd_pct': 0,
            'calmar': 0,
        }
    
    # Calculate daily returns
    values = np.array(daily_values)
    returns = np.diff(values) / values[:-1]
    
    # Sharpe Ratio (annualized)
    mean_ret = np.mean(returns)
    std_ret = np.std(returns)
    sharpe = (mean_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0
    
    # Sortino Ratio (only downside deviation)
    downside_returns = returns[returns < 0]
    downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 0
    sortino = (mean_ret / downside_std * np.sqrt(252)) if downside_std > 0 else 0
    
    # Maximum Drawdown
    peak = values[0]
    max_dd = 0
    for val in values:
        if val > peak:
            peak = val
        dd = (peak - val) / peak
        if dd > max_dd:
            max_dd = dd
    max_dd_pct = max_dd * 100
    
    # Calmar Ratio (annualized return / max drawdown)
    total_return = (final_value - initial_cash) / initial_cash
    years = len(daily_values) / 252
    annual_return = total_return / years if years > 0 else 0
    calmar = (annual_return / max_dd) if max_dd > 0 else 0
    
    return {
        'trades': trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'pf': profit_factor,
        'net_pnl': net_pnl,
        'sharpe': sharpe,
        'sortino': sortino,
        'max_dd_pct': max_dd_pct,
        'calmar': calmar,
    }


def run_single_backtest(atr_max, candles_min):
    """Run a single backtest with given parameters."""
    
    cerebro = bt.Cerebro(stdstats=False)
    
    # Load data
    fromdate = datetime.strptime(FROMDATE, '%Y-%m-%d')
    todate = datetime.strptime(TODATE, '%Y-%m-%d')
    
    data = bt.feeds.GenericCSVData(
        dataname=str(DATA_FILE),
        dtformat='%Y%m%d',
        tmformat='%H:%M:%S',
        datetime=0, time=1, open=2, high=3, low=4, close=5, volume=6,
        timeframe=bt.TimeFrame.Minutes,
        compression=5,
        fromdate=fromdate,
        todate=todate,
    )
    
    cerebro.resampledata(
        data,
        timeframe=bt.TimeFrame.Minutes,
        compression=RESAMPLE_MINUTES,
        name=FOREX_INSTRUMENT
    )
    
    # Broker setup
    cerebro.broker.setcash(STARTING_CASH)
    is_jpy = _CURRENT_CONFIG.get('is_jpy', False)
    commission = ForexCommission(is_jpy_pair=is_jpy, jpy_rate=150.0)
    cerebro.broker.addcommissioninfo(commission, name=FOREX_INSTRUMENT)
    
    # Add strategy with test parameters
    cerebro.addstrategy(
        ErisTest,
        # Override ATR filter
        use_atr_filter=True,
        atr_min_threshold=0.0,  # No minimum
        atr_max_threshold=atr_max,
        # Override oversold candles
        use_oversold_duration_filter=True,
        oversold_min_candles=candles_min,
        oversold_max_candles=50,  # High to not limit
    )
    
    # Run
    results = cerebro.run()
    strategy = results[0]
    
    return calculate_metrics(strategy, STARTING_CASH)


def main():
    """Run grid optimization."""
    
    print("=" * 100)
    print("ERIS ATR + CANDLES OPTIMIZER")
    print("=" * 100)
    print(f"Asset: {FOREX_INSTRUMENT}")
    print(f"Period: {FROMDATE} to {TODATE}")
    print(f"Data: {DATA_FILE}")
    print()
    print(f"ATR Max values: {ATR_MAX_VALUES}")
    print(f"Candles Min values: {CANDLES_MIN_VALUES}")
    print(f"Total combinations: {len(ATR_MAX_VALUES) * len(CANDLES_MIN_VALUES)}")
    print("=" * 100)
    print()
    
    # Results storage
    results = []
    
    # Grid search
    total = len(ATR_MAX_VALUES) * len(CANDLES_MIN_VALUES)
    count = 0
    
    for atr_max, candles_min in product(ATR_MAX_VALUES, CANDLES_MIN_VALUES):
        count += 1
        print(f"[{count}/{total}] ATR<={atr_max:.5f}, Candles>={candles_min}...", end=" ", flush=True)
        
        try:
            metrics = run_single_backtest(atr_max, candles_min)
            metrics['atr_max'] = atr_max
            metrics['candles_min'] = candles_min
            results.append(metrics)
            
            print(f"Trades={metrics['trades']:>3}, PF={metrics['pf']:.2f}, "
                  f"Sharpe={metrics['sharpe']:.2f}, MaxDD={metrics['max_dd_pct']:.1f}%")
        except Exception as e:
            print(f"ERROR: {e}")
    
    # =============================================================================
    # RESULTS ANALYSIS
    # =============================================================================
    print("\n" + "=" * 100)
    print("OPTIMIZATION RESULTS")
    print("=" * 100)
    
    # Filter results with minimum trades
    MIN_TRADES = 50  # At least 50 trades for statistical significance
    valid_results = [r for r in results if r['trades'] >= MIN_TRADES]
    
    print(f"\nTotal combinations: {len(results)}")
    print(f"Valid combinations (>={MIN_TRADES} trades): {len(valid_results)}")
    
    if not valid_results:
        print("\n⚠️ No combinations with enough trades!")
        print("\nAll results sorted by trades:")
        for r in sorted(results, key=lambda x: x['trades'], reverse=True)[:20]:
            print(f"  ATR<={r['atr_max']:.5f}, Candles>={r['candles_min']:>2}: "
                  f"Trades={r['trades']:>3}, PF={r['pf']:.2f}")
        return
    
    # Print header
    print(f"\n{'ATR Max':>10} {'Candles':>8} {'Trades':>7} {'WR%':>7} {'PF':>7} "
          f"{'Net P&L':>12} {'Sharpe':>8} {'Sortino':>8} {'MaxDD%':>8} {'Calmar':>8}")
    print("-" * 100)
    
    # Sort by composite score (PF * Sharpe * (1 - MaxDD/100))
    for r in valid_results:
        dd_factor = 1 - (r['max_dd_pct'] / 100) if r['max_dd_pct'] < 100 else 0.01
        r['score'] = r['pf'] * max(0, r['sharpe']) * dd_factor
    
    sorted_results = sorted(valid_results, key=lambda x: x['score'], reverse=True)
    
    for r in sorted_results[:30]:
        print(f"{r['atr_max']:>10.5f} {r['candles_min']:>8} {r['trades']:>7} "
              f"{r['win_rate']:>6.1f}% {r['pf']:>7.2f} ${r['net_pnl']:>11,.0f} "
              f"{r['sharpe']:>8.2f} {r['sortino']:>8.2f} {r['max_dd_pct']:>7.1f}% "
              f"{r['calmar']:>8.2f}")
    
    # Best by each metric
    print("\n" + "=" * 100)
    print("BEST BY EACH METRIC (min 50 trades)")
    print("=" * 100)
    
    metrics_to_show = [
        ('pf', 'Profit Factor', False),
        ('sharpe', 'Sharpe Ratio', False),
        ('sortino', 'Sortino Ratio', False),
        ('max_dd_pct', 'Max Drawdown', True),  # Lower is better
        ('calmar', 'Calmar Ratio', False),
        ('net_pnl', 'Net P&L', False),
        ('score', 'Composite Score', False),
    ]
    
    for metric, name, ascending in metrics_to_show:
        best = sorted(valid_results, key=lambda x: x[metric], reverse=not ascending)[0]
        print(f"\n{name}:")
        print(f"  ATR Max: {best['atr_max']:.5f}")
        print(f"  Candles Min: {best['candles_min']}")
        print(f"  Trades: {best['trades']}")
        print(f"  PF: {best['pf']:.2f}, Sharpe: {best['sharpe']:.2f}, "
              f"MaxDD: {best['max_dd_pct']:.1f}%, Net P&L: ${best['net_pnl']:,.0f}")
    
    # Save to CSV
    import csv
    csv_path = PROJECT_ROOT / 'temp_reports' / f'eris_atr_candles_optimization_{datetime.now():%Y%m%d_%H%M%S}.csv'
    csv_path.parent.mkdir(exist_ok=True)
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n✅ Results saved to: {csv_path}")


if __name__ == '__main__':
    main()
