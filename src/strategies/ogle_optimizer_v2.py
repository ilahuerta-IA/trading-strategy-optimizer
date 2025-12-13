"""OGLE Optimizer V2 - Multi-Parameter Grid Search
==================================================
Optimizes multiple OGLE parameters in phases:
- Phase 1: SL/TP Multipliers (Risk:Reward ratio)
- Phase 2: Entry Window + Pullback (timing)
- Phase 3: EMAs (trend detection sensitivity)
- Phase 4: ATR Filter (volatility filtering)

Usage:
    python ogle_optimizer_v2.py [phase]
    
    phase: 1, 2, 3, 4, or 'all' for full optimization

Based on eris_optimizer_v2.py structure.
"""

import sys
import os
import math
from pathlib import Path
from datetime import datetime
from itertools import product

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

import backtrader as bt
import numpy as np
from collections import defaultdict

# Import base components from template
from sunrise_ogle_template import (
    ForexCommission, SunriseOgle,
    STARTING_CASH, DATA_FILENAME, FROMDATE, TODATE,
    PIP_VALUE, FOREX_INSTRUMENT, SPREAD_PIPS,
    USE_FIXED_COMMISSION, COMMISSION_PER_LOT_PER_ORDER,
    MARGIN_PERCENT, _CURRENT_CONFIG, EXPORT_TRADE_REPORTS
)

# Disable trade reports for optimization (performance)
import sunrise_ogle_template
sunrise_ogle_template.EXPORT_TRADE_REPORTS = False
sunrise_ogle_template.TRADE_REPORT_ENABLED = False


# =============================================================================
# PARAMETER GRIDS FOR OPTIMIZATION
# =============================================================================

# Phase 1: SL/TP Optimization (Risk:Reward ratios)
PHASE1_GRID = {
    'long_atr_sl_multiplier': [1.5, 2.0, 2.5, 3.0, 3.5],
    'long_atr_tp_multiplier': [6.0, 8.0, 10.0, 12.0, 15.0],
}

# Phase 2: Entry Window + Pullback Optimization
PHASE2_GRID = {
    'long_entry_window_periods': [2, 3, 4, 5, 7, 10],
    'long_pullback_max_candles': [1, 2, 3],
}

# Phase 3: EMA Optimization
PHASE3_GRID = {
    'ema_fast_length': [12, 18, 24],
    'ema_medium_length': [18, 24, 30],
    'ema_slow_length': [18, 24, 30, 36],
    'ema_filter_price_length': [40, 50, 60, 70],
}

# Phase 4: ATR Filter Optimization
PHASE4_GRID = {
    'long_atr_min_threshold': [0.000200, 0.000250, 0.000300, 0.000350],
    'long_atr_max_threshold': [0.000600, 0.000700, 0.000800, 0.000900],
}

# Full grid (reduced combinations for feasibility)
FULL_GRID = {
    'long_atr_sl_multiplier': [2.0, 2.5, 3.0],
    'long_atr_tp_multiplier': [8.0, 10.0, 12.0],
    'long_entry_window_periods': [2, 3, 5],
    'ema_fast_length': [12, 18],
    'ema_filter_price_length': [50, 60],
}


# =============================================================================
# BASELINE PARAMETERS (Current USDCHF optimized values)
# =============================================================================
BASELINE_PARAMS = {
    # EMAs (USDCHF optimized)
    'ema_fast_length': 18,
    'ema_medium_length': 18,
    'ema_slow_length': 24,
    'ema_confirm_length': 1,
    'ema_filter_price_length': 50,
    'ema_exit_length': 25,
    
    # ATR Risk Management
    'atr_length': 10,
    'long_atr_sl_multiplier': 2.5,
    'long_atr_tp_multiplier': 10.0,
    
    # Trading Direction (Long-Only)
    'enable_long_trades': True,
    'enable_short_trades': False,
    
    # ATR Volatility Filter
    'long_use_atr_filter': True,
    'long_atr_min_threshold': 0.000300,
    'long_atr_max_threshold': 0.000700,
    
    # ATR Increment/Decrement (disabled)
    'long_use_atr_increment_filter': False,
    'long_atr_increment_min_threshold': 0.000011,
    'long_atr_increment_max_threshold': 0.000080,
    'long_use_atr_decrement_filter': False,
    'long_atr_decrement_min_threshold': -0.000030,
    'long_atr_decrement_max_threshold': -0.000001,
    
    # Entry Filters
    'long_use_ema_order_condition': False,
    'long_use_price_filter_ema': True,
    'long_use_candle_direction_filter': False,
    'long_use_angle_filter': False,
    'long_min_angle': 40.0,
    'long_max_angle': 80.0,
    'long_angle_scale_factor': 10000.0,
    'long_use_ema_below_price_filter': False,
    
    # Pullback Entry System
    'long_use_pullback_entry': True,
    'long_pullback_max_candles': 2,
    'long_entry_window_periods': 2,
    'window_offset_multiplier': 1.0,
    'use_window_time_offset': False,
    'window_price_offset_multiplier': 0.01,
    
    # Time Range Filter (USDCHF: 07:00-13:00 UTC)
    'use_time_range_filter': True,
    'entry_start_hour': 7,
    'entry_start_minute': 0,
    'entry_end_hour': 13,
    'entry_end_minute': 0,
    
    # Position Sizing
    'size': 1,
    'enable_risk_sizing': True,
    'risk_percent': 0.005,
    'margin_pct': MARGIN_PERCENT,
    'contract_size': 100000,
    
    # Forex Settings
    'forex_instrument': FOREX_INSTRUMENT,
    'forex_pip_value': _CURRENT_CONFIG['pip_value'],
    'forex_pip_decimal_places': _CURRENT_CONFIG['pip_decimal_places'],
    'forex_lot_size': _CURRENT_CONFIG['lot_size'],
    'forex_atr_scale': _CURRENT_CONFIG['atr_scale'],
    'spread_pips': SPREAD_PIPS,
    'use_forex_position_calc': True,
    
    # Display (disabled for optimization)
    'print_signals': False,
    'verbose_debug': False,
    'plot_result': False,
    'buy_sell_plotdist': 0.0005,
    'plot_sltp_lines': False,
}


# =============================================================================
# SILENT OGLE STRATEGY (No printing, fast execution)
# =============================================================================

class OgleSilent(bt.Strategy):
    """Silent OGLE for optimization - minimal output, maximum speed."""
    
    params = dict(**BASELINE_PARAMS)

    def __init__(self):
        # EMAs
        self.ema_fast = bt.ind.EMA(self.data.close, period=self.p.ema_fast_length)
        self.ema_medium = bt.ind.EMA(self.data.close, period=self.p.ema_medium_length)
        self.ema_slow = bt.ind.EMA(self.data.close, period=self.p.ema_slow_length)
        self.ema_confirm = bt.ind.EMA(self.data.close, period=max(1, self.p.ema_confirm_length))
        self.ema_filter = bt.ind.EMA(self.data.close, period=self.p.ema_filter_price_length)
        
        # ATR
        self.atr = bt.ind.ATR(self.data, period=self.p.atr_length)
        
        # Order management
        self.order = None
        self.stop_order = None
        self.limit_order = None
        self.stop_level = None
        self.take_level = None
        
        # State machine for pullback entry
        self.state = "SCANNING"
        self.signal_high = None
        self.signal_bar = None
        self.pullback_count = 0
        self.window_start_bar = None
        
        # Statistics
        self.trades = 0
        self.wins = 0
        self.losses = 0
        self.gross_profit = 0.0
        self.gross_loss = 0.0
        self._trade_pnls = []
        self._portfolio_values = []

    def _cross_above(self, a, b):
        """Check if line a crosses above line b."""
        try:
            return (float(a[0]) > float(b[0])) and (float(a[-1]) <= float(b[-1]))
        except (IndexError, ValueError, TypeError):
            return False

    def _is_bullish_candle(self, offset=0):
        """Check if candle at offset is bullish."""
        try:
            return self.data.close[offset] > self.data.open[offset]
        except IndexError:
            return False

    def _is_bearish_candle(self, offset=0):
        """Check if candle at offset is bearish."""
        try:
            return self.data.close[offset] < self.data.open[offset]
        except IndexError:
            return False

    def _check_time_filter(self, dt):
        """Check if current time is within trading window."""
        if not self.p.use_time_range_filter:
            return True
        
        current_minutes = dt.hour * 60 + dt.minute
        start_minutes = self.p.entry_start_hour * 60 + self.p.entry_start_minute
        end_minutes = self.p.entry_end_hour * 60 + self.p.entry_end_minute
        
        return start_minutes <= current_minutes < end_minutes

    def _check_atr_filter(self):
        """Check if ATR is within acceptable range."""
        if not self.p.long_use_atr_filter:
            return True
        
        try:
            current_atr = float(self.atr[0])
            if math.isnan(current_atr):
                return False
            return self.p.long_atr_min_threshold <= current_atr <= self.p.long_atr_max_threshold
        except (IndexError, ValueError):
            return False

    def _check_ema_crossover(self):
        """Check for bullish EMA crossover signal."""
        crossover = (
            self._cross_above(self.ema_confirm, self.ema_fast) or
            self._cross_above(self.ema_confirm, self.ema_medium) or
            self._cross_above(self.ema_confirm, self.ema_slow)
        )
        return crossover

    def _check_price_filter(self):
        """Check if price is above filter EMA."""
        if not self.p.long_use_price_filter_ema:
            return True
        try:
            return float(self.data.close[0]) > float(self.ema_filter[0])
        except (IndexError, ValueError):
            return False

    def _reset_state(self):
        """Reset state machine to scanning mode."""
        self.state = "SCANNING"
        self.signal_high = None
        self.signal_bar = None
        self.pullback_count = 0
        self.window_start_bar = None

    def prenext(self):
        self._portfolio_values.append(self.broker.get_value())

    def next(self):
        self._portfolio_values.append(self.broker.get_value())
        current_bar = len(self)
        dt = self.data.datetime.datetime(0)
        
        # Cancel pending orders if no position
        if not self.position:
            if self.order:
                self.cancel(self.order)
                self.order = None
            if self.stop_order:
                self.cancel(self.stop_order)
                self.stop_order = None
            if self.limit_order:
                self.cancel(self.limit_order)
                self.limit_order = None
        
        # Skip if orders pending or in position
        if self.order or self.position or self.stop_order or self.limit_order:
            return
        
        # Skip if not in long trading mode
        if not self.p.enable_long_trades:
            return
        
        # Time filter check
        if not self._check_time_filter(dt):
            if self.state != "SCANNING":
                self._reset_state()
            return
        
        # ATR filter check
        if not self._check_atr_filter():
            if self.state != "SCANNING":
                self._reset_state()
            return
        
        # State machine
        if self.state == "SCANNING":
            # Look for bullish signal
            if self._check_ema_crossover():
                if self._check_price_filter():
                    # Store signal candle high
                    self.signal_high = float(self.data.high[0])
                    self.signal_bar = current_bar
                    self.pullback_count = 0
                    self.state = "PULLBACK"
        
        elif self.state == "PULLBACK":
            # Count bearish candles (pullback)
            if self._is_bearish_candle(0):
                self.pullback_count += 1
                
                # Check if we have enough pullback candles
                if self.pullback_count >= self.p.long_pullback_max_candles:
                    self.window_start_bar = current_bar
                    self.state = "BREAKOUT"
            else:
                # Non-bearish candle - check if pullback was complete
                if self.pullback_count >= self.p.long_pullback_max_candles:
                    self.window_start_bar = current_bar
                    self.state = "BREAKOUT"
                elif self.pullback_count > 0:
                    # Partial pullback followed by bullish - might be entry
                    self.window_start_bar = current_bar
                    self.state = "BREAKOUT"
                else:
                    # No pullback yet, continue waiting
                    pass
        
        elif self.state == "BREAKOUT":
            # Check window expiry
            if self.window_start_bar is not None:
                bars_in_window = current_bar - self.window_start_bar
                if bars_in_window > self.p.long_entry_window_periods:
                    self._reset_state()
                    return
            
            # Check for breakout above signal high
            current_high = float(self.data.high[0])
            if current_high > self.signal_high:
                self._execute_long_entry(dt, current_bar)

    def _execute_long_entry(self, dt, current_bar):
        """Execute long entry with ATR-based SL/TP."""
        atr_value = float(self.atr[0])
        if math.isnan(atr_value) or atr_value <= 0:
            self._reset_state()
            return
        
        entry_price = float(self.data.close[0])
        entry_low = float(self.data.low[0])
        entry_high = float(self.data.high[0])
        
        # Calculate SL/TP levels
        self.stop_level = entry_low - (atr_value * self.p.long_atr_sl_multiplier)
        self.take_level = entry_high + (atr_value * self.p.long_atr_tp_multiplier)
        
        risk_distance = entry_price - self.stop_level
        if risk_distance <= 0:
            self._reset_state()
            return
        
        # Position sizing
        equity = self.broker.get_value()
        risk_amount = equity * self.p.risk_percent
        pip_risk = risk_distance / self.p.forex_pip_value
        
        # Calculate pip value
        if self.p.forex_instrument.startswith('USD'):
            pip_value_in_quote = self.p.forex_lot_size * self.p.forex_pip_value
            value_per_pip_per_lot = pip_value_in_quote / entry_price
        else:
            value_per_pip_per_lot = self.p.forex_lot_size * self.p.forex_pip_value
        
        if pip_risk > 0 and value_per_pip_per_lot > 0:
            optimal_lots = risk_amount / (pip_risk * value_per_pip_per_lot)
        else:
            self._reset_state()
            return
        
        # Margin constraint
        margin_per_lot = self.p.forex_lot_size * (self.p.margin_pct / 100.0)
        max_lots_by_margin = equity / margin_per_lot
        if optimal_lots > max_lots_by_margin:
            optimal_lots = max_lots_by_margin
        
        optimal_lots = max(0.01, round(optimal_lots, 2))
        bt_size = int(optimal_lots * self.p.forex_lot_size)
        if bt_size < 1000:
            bt_size = 1000
        
        self.order = self.buy(size=bt_size)
        self._reset_state()

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status == order.Completed:
            if order == self.order:
                # Entry filled - place SL/TP orders
                if self.stop_level and self.take_level:
                    self.stop_order = self.sell(
                        size=order.executed.size,
                        exectype=bt.Order.Stop,
                        price=self.stop_level,
                        oco=self.limit_order
                    )
                    self.limit_order = self.sell(
                        size=order.executed.size,
                        exectype=bt.Order.Limit,
                        price=self.take_level,
                        oco=self.stop_order
                    )
                self.order = None
            else:
                # Exit order completed
                self.stop_order = None
                self.limit_order = None
                self.order = None
                self.stop_level = None
                self.take_level = None
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if self.order and order.ref == self.order.ref:
                self.order = None
            if self.stop_order and order.ref == self.stop_order.ref:
                self.stop_order = None
            if self.limit_order and order.ref == self.limit_order.ref:
                self.limit_order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        
        dt = self.data.datetime.datetime(0)
        pnl = trade.pnlcomm
        
        self.trades += 1
        if pnl > 0:
            self.wins += 1
            self.gross_profit += pnl
        else:
            self.losses += 1
            self.gross_loss += abs(pnl)
        
        self._trade_pnls.append({
            'date': dt,
            'year': dt.year,
            'pnl': pnl,
            'is_winner': pnl > 0
        })
        
        self.stop_level = None
        self.take_level = None

    def stop(self):
        if self.position:
            self.close()


# =============================================================================
# OPTIMIZATION RUNNER
# =============================================================================

def run_single_backtest(params_override):
    """Run a single backtest with specified parameters."""
    cerebro = bt.Cerebro()
    
    # Load data
    data_dir = Path(__file__).parent.parent.parent / "data"
    data_path = data_dir / DATA_FILENAME
    
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    
    # CSV format: Date,Time,Open,High,Low,Close,Volume
    data = bt.feeds.GenericCSVData(
        dataname=str(data_path),
        fromdate=datetime.strptime(FROMDATE, '%Y-%m-%d'),
        todate=datetime.strptime(TODATE, '%Y-%m-%d'),
        dtformat='%Y%m%d',
        tmformat='%H:%M:%S',
        datetime=0,
        time=1,
        open=2,
        high=3,
        low=4,
        close=5,
        volume=6,
        openinterest=-1,
        timeframe=bt.TimeFrame.Minutes,
        compression=5,
    )
    
    cerebro.adddata(data)
    cerebro.broker.set_cash(STARTING_CASH)
    
    if USE_FIXED_COMMISSION:
        cerebro.broker.addcommissioninfo(ForexCommission())
    
    # Merge baseline with overrides, force silent mode
    final_params = {**BASELINE_PARAMS, **params_override}
    final_params['print_signals'] = False
    final_params['verbose_debug'] = False
    final_params['plot_result'] = False
    final_params['plot_sltp_lines'] = False
    
    # Use real SunriseOgle strategy for accurate replication
    cerebro.addstrategy(SunriseOgle, **final_params)
    
    results = cerebro.run()
    strat = results[0]
    
    # Calculate metrics
    final_value = cerebro.broker.get_value()
    total_pnl = final_value - STARTING_CASH
    
    # Get trade stats - handle both SunriseOgle and OgleSilent
    trades = getattr(strat, 'trades', 0)
    wins = getattr(strat, 'wins', 0)
    losses = getattr(strat, 'losses', 0)
    gross_profit = getattr(strat, 'gross_profit', 0.0)
    gross_loss = getattr(strat, 'gross_loss', 0.0)
    
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
    win_rate = (wins / trades * 100) if trades > 0 else 0
    
    # Max Drawdown
    max_dd = 0.0
    portfolio_values = getattr(strat, '_portfolio_values', [])
    if len(portfolio_values) > 1:
        peak = portfolio_values[0]
        for value in portfolio_values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100.0
            if dd > max_dd:
                max_dd = dd
    
    # Yearly breakdown
    yearly_pnl = defaultdict(float)
    trade_pnls = getattr(strat, '_trade_pnls', [])
    for t in trade_pnls:
        yearly_pnl[t['year']] += t['pnl']
    
    # Count negative years
    negative_years = sum(1 for pnl in yearly_pnl.values() if pnl < 0)
    
    return {
        'trades': trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_pnl': total_pnl,
        'max_drawdown': max_dd,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'yearly_pnl': dict(yearly_pnl),
        'negative_years': negative_years,
    }


def run_optimization(param_grid, phase_name=""):
    """Run optimization over parameter grid."""
    print(f"\n{'='*70}")
    print(f"OGLE OPTIMIZER V2 - {phase_name}")
    print(f"{'='*70}")
    
    # Generate all combinations
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(product(*param_values))
    
    print(f"Parameters: {param_names}")
    print(f"Total combinations: {len(combinations)}")
    print(f"{'='*70}\n")
    
    results = []
    
    for i, combo in enumerate(combinations, 1):
        params_override = dict(zip(param_names, combo))
        
        # Progress
        param_str = " | ".join([f"{k}={v}" for k, v in params_override.items()])
        print(f"[{i}/{len(combinations)}] Testing: {param_str}")
        
        try:
            result = run_single_backtest(params_override)
            result['params'] = params_override
            results.append(result)
            
            # Quick summary
            print(f"    -> Trades: {result['trades']} | PF: {result['profit_factor']:.2f} | "
                  f"WR: {result['win_rate']:.1f}% | PnL: ${result['total_pnl']:,.0f} | "
                  f"MaxDD: {result['max_drawdown']:.2f}% | NegYrs: {result['negative_years']}")
            
        except Exception as e:
            print(f"    -> ERROR: {e}")
    
    # Sort by Profit Factor (with minimum trades filter)
    min_trades = 30  # Lower threshold for OGLE (fewer trades than ERIS)
    valid_results = [r for r in results if r['trades'] >= min_trades]
    valid_results.sort(key=lambda x: x['profit_factor'], reverse=True)
    
    # Print top results
    print(f"\n{'='*70}")
    print(f"TOP 10 RESULTS (min {min_trades} trades) - Sorted by Profit Factor")
    print(f"{'='*70}")
    
    for i, r in enumerate(valid_results[:10], 1):
        param_str = " | ".join([f"{k}={v}" for k, v in r['params'].items()])
        print(f"\n{i}. {param_str}")
        print(f"   Trades: {r['trades']} | Wins: {r['wins']} | Losses: {r['losses']}")
        print(f"   Win Rate: {r['win_rate']:.1f}% | Profit Factor: {r['profit_factor']:.2f}")
        print(f"   Total PnL: ${r['total_pnl']:,.0f} | Max DD: {r['max_drawdown']:.2f}%")
        print(f"   Negative Years: {r['negative_years']} | Yearly: {r['yearly_pnl']}")
    
    # Print best by different metrics
    print(f"\n{'='*70}")
    print("BEST BY METRIC:")
    print(f"{'='*70}")
    
    if valid_results:
        best_pf = max(valid_results, key=lambda x: x['profit_factor'])
        best_pnl = max(valid_results, key=lambda x: x['total_pnl'])
        best_trades = max(valid_results, key=lambda x: x['trades'])
        lowest_dd = min(valid_results, key=lambda x: x['max_drawdown'])
        fewest_neg_years = min(valid_results, key=lambda x: x['negative_years'])
        
        print(f"\nBest Profit Factor: {best_pf['profit_factor']:.2f}")
        print(f"   Params: {best_pf['params']}")
        print(f"   PnL: ${best_pf['total_pnl']:,.0f} | Trades: {best_pf['trades']}")
        
        print(f"\nBest Total PnL: ${best_pnl['total_pnl']:,.0f}")
        print(f"   Params: {best_pnl['params']}")
        print(f"   PF: {best_pnl['profit_factor']:.2f} | Trades: {best_pnl['trades']}")
        
        print(f"\nMost Trades: {best_trades['trades']}")
        print(f"   Params: {best_trades['params']}")
        print(f"   PF: {best_trades['profit_factor']:.2f} | PnL: ${best_trades['total_pnl']:,.0f}")
        
        print(f"\nLowest Drawdown: {lowest_dd['max_drawdown']:.2f}%")
        print(f"   Params: {lowest_dd['params']}")
        print(f"   PF: {lowest_dd['profit_factor']:.2f} | PnL: ${lowest_dd['total_pnl']:,.0f}")
        
        print(f"\nFewest Negative Years: {fewest_neg_years['negative_years']}")
        print(f"   Params: {fewest_neg_years['params']}")
        print(f"   PF: {fewest_neg_years['profit_factor']:.2f} | PnL: ${fewest_neg_years['total_pnl']:,.0f}")
    
    return valid_results


def main():
    """Main entry point."""
    phase = sys.argv[1] if len(sys.argv) > 1 else "1"
    
    if phase == "1":
        results = run_optimization(PHASE1_GRID, "PHASE 1: SL/TP Multipliers")
    elif phase == "2":
        results = run_optimization(PHASE2_GRID, "PHASE 2: Entry Window + Pullback")
    elif phase == "3":
        results = run_optimization(PHASE3_GRID, "PHASE 3: EMAs")
    elif phase == "4":
        results = run_optimization(PHASE4_GRID, "PHASE 4: ATR Filter")
    elif phase == "all" or phase == "full":
        results = run_optimization(FULL_GRID, "FULL OPTIMIZATION")
    else:
        print(f"Unknown phase: {phase}")
        print("Usage: python ogle_optimizer_v2.py [1|2|3|4|all]")
        return
    
    print(f"\n{'='*70}")
    print("OPTIMIZATION COMPLETE")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
