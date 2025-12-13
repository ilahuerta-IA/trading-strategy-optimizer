"""ERIS Optimizer V2 - Multi-Parameter Grid Search
==================================================
Optimiza múltiples parámetros de ERIS en fases:
- Phase 1: SL/TP Multipliers (Risk:Reward ratio)
- Phase 2: Entry Window (MAX_CANDLES)
- Phase 3: Mean Reversion (EMA Period, Z-Score range)

Uso:
    python eris_optimizer_v2.py [phase]
    
    phase: 1, 2, 3, o 'all' para todas las fases
"""

import sys
import os
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
from eris_template import (
    ForexCommission, MeanReversionBands, ZScoreIndicator,
    STARTING_CASH, DATA_FILENAME, FROMDATE, TODATE,
    PIP_VALUE, FOREX_INSTRUMENT, SPREAD_PIPS,
    USE_FIXED_COMMISSION, COMMISSION_PER_LOT_PER_ORDER,
    RESAMPLE_MINUTES
)


# =============================================================================
# PARAMETER GRIDS FOR OPTIMIZATION
# =============================================================================

# Phase 1: SL/TP Optimization (Risk:Reward ratios)
PHASE1_GRID = {
    'long_atr_sl_multiplier': [0.75, 1.0, 1.25, 1.5],
    'long_atr_tp_multiplier': [3.0, 4.0, 5.0, 6.0, 7.0],
}

# Phase 2: Entry Window Optimization
PHASE2_GRID = {
    'long_entry_max_candles': [3, 5, 7, 10, 12],
}

# Phase 3: Mean Reversion Optimization (EMA + Z-Score)
PHASE3_GRID = {
    'mean_reversion_ema_period': [30, 45, 60, 70, 90],
    'mr_entry_zscore_min': [-4.0, -3.0, -2.5],
    'mr_entry_zscore_max': [-1.5, -1.0, -0.5, 0.0],
}

# Full grid (for complete optimization - many combinations!)
FULL_GRID = {
    'long_atr_sl_multiplier': [0.75, 1.0, 1.5],
    'long_atr_tp_multiplier': [4.0, 5.0, 6.0],
    'long_entry_max_candles': [5, 7, 10],
    'mean_reversion_ema_period': [45, 60, 70],
    'mr_entry_zscore_min': [-3.0, -2.5],
    'mr_entry_zscore_max': [-1.0, -0.5],
}

# =============================================================================
# BASELINE PARAMETERS (Current best from previous optimization)
# =============================================================================
BASELINE_PARAMS = {
    # Pattern
    'long_pullback_num_candles': 1,
    'long_breakout_delay': False,
    'long_breakout_delay_candles': 1,
    'long_entry_max_candles': 5,
    'long_before_candles': True,
    'long_before_num_candles': 1,
    
    # Time/ATR filters (disabled)
    'use_time_filter': False,
    'trading_start_hour': 14,
    'trading_end_hour': 22,
    'use_atr_filter': False,
    'atr_min_threshold': 0.00025,
    'atr_max_threshold': 0.00040,
    'use_hours_to_avoid_filter': False,
    'hours_to_avoid': [3, 6, 7, 10, 13, 20],
    
    # ATR SL/TP
    'atr_length': 10,
    'long_atr_sl_multiplier': 1.0,
    'long_atr_tp_multiplier': 5.0,
    
    # SL Range filter (disabled)
    'use_min_sl_filter': False,
    'min_sl_pips': 3.0,
    'max_sl_pips': 250.0,
    'spread_pips': SPREAD_PIPS,
    
    # Position sizing
    'risk_percent': 0.005,
    'margin_pct': 3.33,
    'contract_size': 100000,
    
    # Forex
    'forex_instrument': FOREX_INSTRUMENT,
    'forex_pip_value': PIP_VALUE,
    'forex_pip_decimal_places': 5,
    'forex_lot_size': 100000,
    'forex_atr_scale': 1.0,
    
    # Mean Reversion
    'use_mean_reversion_indicator': True,
    'mean_reversion_ema_period': 70,
    'mean_reversion_atr_period': 10,
    'mean_reversion_deviation_mult': 2.0,
    'mean_reversion_zscore_upper': 2.0,
    'mean_reversion_zscore_lower': -2.0,
    
    # Entry filter (ENABLED)
    'use_mean_reversion_entry_filter': True,
    'mr_entry_zscore_min': -3.0,
    'mr_entry_zscore_max': -1.0,
    
    # Oversold duration (ENABLED)
    'use_oversold_duration_filter': True,
    'oversold_min_candles': 6,
    'oversold_max_candles': 11,
    'oversold_zscore_threshold': -1.0,
    
    # Display
    'print_signals': False,
    'plot_sltp_lines': False,
    'buy_sell_plotdist': 0.0001,
}


# =============================================================================
# SILENT ERIS STRATEGY (No printing, fast execution)
# =============================================================================

class ErisSilent(bt.Strategy):
    """Silent ERIS for optimization - minimal output."""
    
    params = dict(**BASELINE_PARAMS)

    def __init__(self):
        self.atr = bt.ind.ATR(self.data, period=self.p.atr_length)
        
        if self.p.use_mean_reversion_indicator:
            self.mr_bands = MeanReversionBands(
                self.data,
                ema_period=self.p.mean_reversion_ema_period,
                atr_period=self.p.mean_reversion_atr_period,
                deviation_mult=self.p.mean_reversion_deviation_mult,
            )
            self.mr_zscore = ZScoreIndicator(
                self.data,
                ema_period=self.p.mean_reversion_ema_period,
                atr_period=self.p.mean_reversion_atr_period,
                upper_threshold=self.p.mean_reversion_zscore_upper,
                lower_threshold=self.p.mean_reversion_zscore_lower,
            )
        
        self.order = None
        self.stop_order = None
        self.limit_order = None
        self.stop_level = None
        self.take_level = None
        
        self.state = "SCANNING"
        self.trigger_candle_high = None
        self.trigger_candle_bar = None
        self.candles_in_oversold = 0
        self.pullback_count = 0
        self.pullback_complete_bar = None
        self.delay_count = 0
        self.breakout_start_bar = None
        
        self.trades = 0
        self.wins = 0
        self.losses = 0
        self.gross_profit = 0.0
        self.gross_loss = 0.0
        self._trade_pnls = []
        self._portfolio_values = []

    def _is_bullish_candle(self, offset=0):
        try:
            return self.data.close[offset] > self.data.open[offset]
        except IndexError:
            return False

    def _is_bearish_candle(self, offset=0):
        try:
            return self.data.close[offset] < self.data.open[offset]
        except IndexError:
            return False

    def _check_before_candles(self):
        if not self.p.long_before_candles:
            return True
        required = self.p.long_before_num_candles
        for i in range(1, required + 1):
            offset = -i - 1
            if not self._is_bullish_candle(offset):
                return False
        return True

    def _reset_state(self):
        self.state = "SCANNING"
        self.trigger_candle_high = None
        self.trigger_candle_bar = None
        self.pullback_count = 0
        self.pullback_complete_bar = None
        self.delay_count = 0
        self.breakout_start_bar = None

    def prenext(self):
        self._portfolio_values.append(self.broker.get_value())

    def next(self):
        import math
        self._portfolio_values.append(self.broker.get_value())
        current_bar = len(self)
        dt = self.data.datetime.datetime(0)
        
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
        
        if self.order or self.position or self.stop_order or self.limit_order:
            return
        
        self._update_oversold_duration()
        
        if self.p.use_time_filter:
            current_hour = dt.hour
            if current_hour < self.p.trading_start_hour or current_hour >= self.p.trading_end_hour:
                if self.state != "SCANNING":
                    self._reset_state()
                return
        
        if self.p.use_atr_filter:
            current_atr = float(self.atr[0])
            if math.isnan(current_atr):
                return
            if current_atr < self.p.atr_min_threshold or current_atr > self.p.atr_max_threshold:
                if self.state != "SCANNING":
                    self._reset_state()
                return
        
        if self.p.use_hours_to_avoid_filter:
            current_hour = dt.hour
            if current_hour in self.p.hours_to_avoid:
                if self.state != "SCANNING":
                    self._reset_state()
                return
        
        # State machine
        if self.state == "SCANNING":
            if self._is_bullish_candle(-1):
                if self._check_before_candles():
                    self.trigger_candle_high = float(self.data.high[-1])
                    self.trigger_candle_bar = current_bar - 1
                    self.pullback_count = 0
                    self.state = "PULLBACK"
        
        elif self.state == "PULLBACK":
            if self._is_bearish_candle(0):
                self.pullback_count += 1
                if self.pullback_count >= self.p.long_pullback_num_candles:
                    self.pullback_complete_bar = current_bar
                    if self.p.long_breakout_delay:
                        self.state = "WAITING"
                        self.delay_count = 0
                        return
                    else:
                        self.state = "BREAKOUT"
                        self.breakout_start_bar = current_bar
                        return
            else:
                if self.pullback_count >= self.p.long_pullback_num_candles:
                    if self.pullback_complete_bar is None:
                        self.pullback_complete_bar = current_bar - 1
                    self.state = "BREAKOUT"
                    self.breakout_start_bar = current_bar
                else:
                    self._reset_state()
                    return
        
        elif self.state == "WAITING":
            self.delay_count += 1
            if self.delay_count >= self.p.long_breakout_delay_candles:
                self.state = "BREAKOUT"
                self.breakout_start_bar = current_bar
                return
        
        if self.state == "BREAKOUT":
            candles_since_pullback = current_bar - self.pullback_complete_bar
            if candles_since_pullback > self.p.long_entry_max_candles:
                self._reset_state()
                return
            
            current_high = float(self.data.high[0])
            if current_high > self.trigger_candle_high:
                mr_filter_ok = self._check_mean_reversion_entry_filter()
                duration_filter_ok = self._check_oversold_duration_filter()
                
                if mr_filter_ok and duration_filter_ok:
                    self._execute_entry(dt, current_bar)
                else:
                    self._reset_state()

    def _update_oversold_duration(self):
        import math
        if not self.p.use_oversold_duration_filter or not self.p.use_mean_reversion_indicator:
            return
        try:
            current_zscore = float(self.mr_zscore.zscore[0])
            if math.isnan(current_zscore):
                return
        except (AttributeError, IndexError):
            return
        
        if current_zscore < self.p.oversold_zscore_threshold:
            self.candles_in_oversold += 1
        else:
            self.candles_in_oversold = 0

    def _check_oversold_duration_filter(self):
        if not self.p.use_oversold_duration_filter:
            return True
        duration = self.candles_in_oversold
        return self.p.oversold_min_candles <= duration <= self.p.oversold_max_candles

    def _check_mean_reversion_entry_filter(self):
        import math
        if not self.p.use_mean_reversion_entry_filter or not self.p.use_mean_reversion_indicator:
            return True
        try:
            current_zscore = float(self.mr_zscore.zscore[0])
            if math.isnan(current_zscore):
                return True
        except (AttributeError, IndexError):
            return True
        return self.p.mr_entry_zscore_min <= current_zscore <= self.p.mr_entry_zscore_max

    def _execute_entry(self, dt, current_bar):
        import math
        atr_value = float(self.atr[0])
        if math.isnan(atr_value) or atr_value <= 0:
            self._reset_state()
            return
        
        entry_price = float(self.data.close[0])
        self.stop_level = entry_price - (atr_value * self.p.long_atr_sl_multiplier)
        self.take_level = entry_price + (atr_value * self.p.long_atr_tp_multiplier)
        
        risk_distance = entry_price - self.stop_level
        if risk_distance <= 0:
            self._reset_state()
            return
        
        equity = self.broker.get_value()
        risk_amount = equity * self.p.risk_percent
        pip_risk = risk_distance / self.p.forex_pip_value
        
        if self.p.use_min_sl_filter:
            if pip_risk < self.p.min_sl_pips or pip_risk > self.p.max_sl_pips:
                self._reset_state()
                return
        
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
        
        margin_per_lot = self.p.forex_lot_size * (self.p.margin_pct / 100.0)
        max_lots_by_margin = equity / margin_per_lot
        if optimal_lots > max_lots_by_margin:
            optimal_lots = max_lots_by_margin
        
        optimal_lots = max(0.01, round(optimal_lots, 2))
        bt_size = int(optimal_lots * self.p.forex_lot_size)
        if bt_size < 1000:
            bt_size = 1000
        
        self.order = self.buy(size=bt_size)
        self.last_entry_price = entry_price
        self.last_entry_bar = current_bar

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status == order.Completed:
            if order == self.order:
                self.last_entry_price = order.executed.price
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
                self._reset_state()
            else:
                self.stop_order = None
                self.limit_order = None
                self.order = None
                self.stop_level = None
                self.take_level = None
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if self.order and order.ref == self.order.ref:
                self.order = None
                self._reset_state()
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
    # Date: 20200101, Time: 22:00:00
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
    
    # Merge baseline with overrides
    final_params = {**BASELINE_PARAMS, **params_override}
    cerebro.addstrategy(ErisSilent, **final_params)
    
    results = cerebro.run()
    strat = results[0]
    
    # Calculate metrics
    final_value = cerebro.broker.get_value()
    total_pnl = final_value - STARTING_CASH
    
    profit_factor = (strat.gross_profit / strat.gross_loss) if strat.gross_loss > 0 else 0
    win_rate = (strat.wins / strat.trades * 100) if strat.trades > 0 else 0
    
    # Max Drawdown
    max_dd = 0.0
    if len(strat._portfolio_values) > 1:
        peak = strat._portfolio_values[0]
        for value in strat._portfolio_values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100.0
            if dd > max_dd:
                max_dd = dd
    
    return {
        'trades': strat.trades,
        'wins': strat.wins,
        'losses': strat.losses,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_pnl': total_pnl,
        'max_drawdown': max_dd,
        'gross_profit': strat.gross_profit,
        'gross_loss': strat.gross_loss,
    }


def run_optimization(param_grid, phase_name=""):
    """Run optimization over parameter grid."""
    print(f"\n{'='*70}")
    print(f"ERIS OPTIMIZER V2 - {phase_name}")
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
                  f"MaxDD: {result['max_drawdown']:.2f}%")
            
        except Exception as e:
            print(f"    -> ERROR: {e}")
    
    # Sort by Profit Factor (with minimum trades filter)
    valid_results = [r for r in results if r['trades'] >= 50]
    valid_results.sort(key=lambda x: x['profit_factor'], reverse=True)
    
    # Print top results
    print(f"\n{'='*70}")
    print(f"TOP 10 RESULTS (min 50 trades) - Sorted by Profit Factor")
    print(f"{'='*70}")
    
    for i, r in enumerate(valid_results[:10], 1):
        param_str = " | ".join([f"{k}={v}" for k, v in r['params'].items()])
        print(f"\n{i}. {param_str}")
        print(f"   Trades: {r['trades']} | Wins: {r['wins']} | Losses: {r['losses']}")
        print(f"   Win Rate: {r['win_rate']:.1f}% | Profit Factor: {r['profit_factor']:.2f}")
        print(f"   Total PnL: ${r['total_pnl']:,.0f} | Max DD: {r['max_drawdown']:.2f}%")
    
    # Print best by different metrics
    print(f"\n{'='*70}")
    print("BEST BY METRIC:")
    print(f"{'='*70}")
    
    if valid_results:
        best_pf = max(valid_results, key=lambda x: x['profit_factor'])
        best_pnl = max(valid_results, key=lambda x: x['total_pnl'])
        best_trades = max(valid_results, key=lambda x: x['trades'])
        lowest_dd = min(valid_results, key=lambda x: x['max_drawdown'])
        
        print(f"\nBest Profit Factor: {best_pf['profit_factor']:.2f}")
        print(f"   Params: {best_pf['params']}")
        
        print(f"\nBest Total PnL: ${best_pnl['total_pnl']:,.0f}")
        print(f"   Params: {best_pnl['params']}")
        
        print(f"\nMost Trades: {best_trades['trades']}")
        print(f"   Params: {best_trades['params']}")
        
        print(f"\nLowest Drawdown: {lowest_dd['max_drawdown']:.2f}%")
        print(f"   Params: {lowest_dd['params']}")
    
    return valid_results


def main():
    """Main entry point."""
    phase = sys.argv[1] if len(sys.argv) > 1 else "1"
    
    if phase == "1":
        results = run_optimization(PHASE1_GRID, "PHASE 1: SL/TP Multipliers")
    elif phase == "2":
        results = run_optimization(PHASE2_GRID, "PHASE 2: Entry Window")
    elif phase == "3":
        results = run_optimization(PHASE3_GRID, "PHASE 3: Mean Reversion")
    elif phase == "all" or phase == "full":
        results = run_optimization(FULL_GRID, "FULL OPTIMIZATION")
    else:
        print(f"Unknown phase: {phase}")
        print("Usage: python eris_optimizer_v2.py [1|2|3|all]")
        return
    
    print(f"\n{'='*70}")
    print("OPTIMIZATION COMPLETE")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
