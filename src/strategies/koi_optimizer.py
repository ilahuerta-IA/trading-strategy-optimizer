"""KOI Strategy - Universal Optimizer
=====================================
SINGLE OPTIMIZER for all KOI instruments.
Configure via command-line arguments or edit CONFIGS below.

USAGE:
    python koi_optimizer.py USDCHF           # Optimize USDCHF with default phases
    python koi_optimizer.py USDCHF --phase 1 # Only Phase 1 (SL/TP)
    python koi_optimizer.py USDCHF --phase 2 # Only Phase 2 (CCI)
    python koi_optimizer.py USDCHF --phase 3 # Only Phase 3 (EMAs)
    python koi_optimizer.py USDCHF --phase 4 # Only Phase 4 (Breakout)
    python koi_optimizer.py USDCHF --all     # All phases sequentially
    python koi_optimizer.py USDCHF --quick   # Quick test (1 year data)

OPTIMIZATION PHASES:
    Phase 1: SL/TP Multipliers (Risk:Reward ratio)
    Phase 2: CCI (period and threshold)
    Phase 3: EMAs (5 EMA periods)
    Phase 4: Breakout Window (offset pips + candles)
    Phase 5: SL Range Filter (min/max pips)

OUTPUT:
    - Console: Progress and TOP 10 results
    - JSON: koi_optimization_results_{INSTRUMENT}.json

KNOWN ISSUES & SOLUTIONS (DO NOT REPEAT):
    1. Use GenericCSVData, NOT PandasData
    2. Disable filters first, then add one by one
    3. Always disable print_signals for speed

Author: Iván López
Date: December 2025
"""

import sys
import math
import json
import argparse
from pathlib import Path
from datetime import datetime
from itertools import product
from collections import defaultdict

import backtrader as bt

# Add project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).parent))

# Import commission class and ForexCSVData from template
from koi_template import ForexCommission, ForexCSVData


# =============================================================================
# INSTRUMENT CONFIGURATIONS
# =============================================================================
INSTRUMENT_DATA = {
    'USDCHF': {
        'data_file': 'USDCHF_5m_5Yea.csv',
        'pip_value': 0.0001,
        'pip_decimal_places': 5,
        'spread': 0.7,
    },
    'EURUSD': {
        'data_file': 'EURUSD_5m_5Yea.csv',
        'pip_value': 0.0001,
        'pip_decimal_places': 5,
        'spread': 0.6,
    },
    'USDJPY': {
        'data_file': 'USDJPY_5m_5Yea.csv',
        'pip_value': 0.01,
        'pip_decimal_places': 3,
        'spread': 1.0,
    },
    'GBPUSD': {
        'data_file': 'GBPUSD_5m_5Yea.csv',
        'pip_value': 0.0001,
        'pip_decimal_places': 5,
        'spread': 0.9,
    },
    'USDCAD': {
        'data_file': 'USDCAD_5m_5Yea.csv',
        'pip_value': 0.0001,
        'pip_decimal_places': 5,
        'spread': 0.8,
    },
}


# =============================================================================
# OPTIMIZATION GRIDS (Modify these for different searches)
# =============================================================================

# Phase 1: SL/TP Optimization
PHASE1_GRID = {
    'atr_sl_mult': [2.0, 2.5, 3.0, 3.5],
    'atr_tp_mult': [8.0, 10.0, 12.0, 15.0],
}

# Phase 2: CCI Optimization
PHASE2_GRID = {
    'cci_period': [14, 20, 25],
    'cci_threshold': [50, 70, 100, 120],
}

# Phase 3: EMA Optimization
PHASE3_GRID = {
    'ema_1': [8, 10, 12],
    'ema_2': [16, 20, 24],
    'ema_3': [32, 40, 48],
    'ema_4': [64, 80, 96],
    'ema_5': [100, 120, 144],
}

# Phase 4: Breakout Window Optimization
PHASE4_GRID = {
    'breakout_offset_pips': [0, 3, 5, 7, 10],
    'breakout_candles': [3, 5, 7],
}

# Phase 5: SL Range Filter Optimization
PHASE5_GRID = {
    'min_sl_pips': [8.0, 10.0, 10.5, 12.0],
    'max_sl_pips': [14.0, 14.5, 16.0, 20.0],
}


# =============================================================================
# KOI STRATEGY (Simplified for Optimization)
# =============================================================================
class KoiOptimized(bt.Strategy):
    """KOI Strategy - Bullish Engulfing + 5 EMA + CCI + Breakout Window"""
    
    params = dict(
        # EMAs
        ema_1=10,
        ema_2=20,
        ema_3=40,
        ema_4=80,
        ema_5=120,
        
        # CCI
        cci_period=20,
        cci_threshold=100,
        
        # ATR SL/TP
        atr_length=10,
        atr_sl_mult=3.0,
        atr_tp_mult=12.0,
        
        # Breakout Window
        use_breakout=True,
        breakout_candles=3,
        breakout_offset_pips=5.0,
        
        # Risk
        risk_percent=0.005,
        margin_pct=3.33,
        
        # Forex
        pip_value=0.0001,
        lot_size=100000,
        
        # Filters
        use_session_filter=False,
        session_start=0,
        session_end=23,
        
        use_min_sl_filter=True,
        min_sl_pips=10.5,
        
        use_max_sl_filter=True,
        max_sl_pips=14.5,
        
        use_atr_filter=False,
        atr_min=0.00030,
        atr_max=0.00100,
        
        # Display
        print_signals=False,
    )

    def __init__(self):
        # EMAs
        self.ema1 = bt.ind.EMA(self.data.close, period=self.p.ema_1)
        self.ema2 = bt.ind.EMA(self.data.close, period=self.p.ema_2)
        self.ema3 = bt.ind.EMA(self.data.close, period=self.p.ema_3)
        self.ema4 = bt.ind.EMA(self.data.close, period=self.p.ema_4)
        self.ema5 = bt.ind.EMA(self.data.close, period=self.p.ema_5)
        
        # CCI
        self.cci = bt.ind.CCI(self.data, period=self.p.cci_period)
        
        # ATR
        self.atr = bt.ind.ATR(self.data, period=self.p.atr_length)
        
        # Orders
        self.order = None
        self.stop_order = None
        self.limit_order = None
        self.stop_level = None
        self.take_level = None
        
        # State machine
        self.state = "SCANNING"
        self.pattern_high = None
        self.pattern_bar = None
        self.breakout_countdown = 0
        
        # Stats
        self.trades = 0
        self.wins = 0
        self.losses = 0
        self.gross_profit = 0.0
        self.gross_loss = 0.0
        self._portfolio_values = []
        self._trade_pnls = []

    def _is_bullish_engulfing(self):
        """Check for bullish engulfing pattern."""
        try:
            # Previous candle bearish
            prev_bearish = self.data.close[-1] < self.data.open[-1]
            # Current candle bullish
            curr_bullish = self.data.close[0] > self.data.open[0]
            # Current body engulfs previous
            engulfs = (self.data.close[0] > self.data.open[-1] and 
                      self.data.open[0] < self.data.close[-1])
            return prev_bearish and curr_bullish and engulfs
        except IndexError:
            return False

    def _all_emas_ascending(self):
        """Check if all EMAs are ascending (EMA[0] > EMA[-1])."""
        try:
            return (self.ema1[0] > self.ema1[-1] and
                    self.ema2[0] > self.ema2[-1] and
                    self.ema3[0] > self.ema3[-1] and
                    self.ema4[0] > self.ema4[-1] and
                    self.ema5[0] > self.ema5[-1])
        except IndexError:
            return False

    def _cci_above_threshold(self):
        """Check if CCI is above threshold."""
        try:
            return self.cci[0] > self.p.cci_threshold
        except IndexError:
            return False

    def _reset_state(self):
        """Reset state machine."""
        self.state = "SCANNING"
        self.pattern_high = None
        self.pattern_bar = None
        self.breakout_countdown = 0

    def prenext(self):
        self._portfolio_values.append(self.broker.get_value())

    def next(self):
        self._portfolio_values.append(self.broker.get_value())
        current_bar = len(self)
        dt = self.data.datetime.datetime(0)
        
        # Cancel orders if no position
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
        
        # Session filter
        if self.p.use_session_filter:
            hour = dt.hour
            if hour < self.p.session_start or hour >= self.p.session_end:
                if self.state != "SCANNING":
                    self._reset_state()
                return
        
        # ATR filter
        if self.p.use_atr_filter:
            atr_val = float(self.atr[0])
            if math.isnan(atr_val):
                return
            if atr_val < self.p.atr_min or atr_val > self.p.atr_max:
                if self.state != "SCANNING":
                    self._reset_state()
                return
        
        # State machine
        if self.state == "SCANNING":
            if self._is_bullish_engulfing() and self._all_emas_ascending() and self._cci_above_threshold():
                self.pattern_high = float(self.data.high[0])
                self.pattern_bar = current_bar
                
                if self.p.use_breakout:
                    self.state = "BREAKOUT"
                    self.breakout_countdown = self.p.breakout_candles
                else:
                    self._execute_entry(dt, current_bar)
        
        elif self.state == "BREAKOUT":
            self.breakout_countdown -= 1
            
            if self.breakout_countdown <= 0:
                self._reset_state()
                return
            
            # Check breakout
            breakout_level = self.pattern_high + (self.p.breakout_offset_pips * self.p.pip_value)
            if float(self.data.high[0]) > breakout_level:
                self._execute_entry(dt, current_bar)

    def _execute_entry(self, dt, current_bar):
        """Execute entry with ATR-based SL/TP."""
        atr_value = float(self.atr[0])
        if math.isnan(atr_value) or atr_value <= 0:
            self._reset_state()
            return
        
        entry_price = float(self.data.close[0])
        
        # Calculate SL/TP
        self.stop_level = entry_price - (atr_value * self.p.atr_sl_mult)
        self.take_level = entry_price + (atr_value * self.p.atr_tp_mult)
        
        risk_distance = entry_price - self.stop_level
        if risk_distance <= 0:
            self._reset_state()
            return
        
        # SL range filter
        sl_pips = risk_distance / self.p.pip_value
        
        if self.p.use_min_sl_filter and sl_pips < self.p.min_sl_pips:
            self._reset_state()
            return
        
        if self.p.use_max_sl_filter and sl_pips > self.p.max_sl_pips:
            self._reset_state()
            return
        
        # Position sizing
        equity = self.broker.get_value()
        risk_amount = equity * self.p.risk_percent
        pip_risk = sl_pips
        value_per_pip_per_lot = self.p.lot_size * self.p.pip_value
        
        if pip_risk > 0 and value_per_pip_per_lot > 0:
            optimal_lots = risk_amount / (pip_risk * value_per_pip_per_lot)
        else:
            self._reset_state()
            return
        
        # Margin limit
        margin_per_lot = self.p.lot_size * (self.p.margin_pct / 100.0)
        max_lots = equity / margin_per_lot
        if optimal_lots > max_lots:
            optimal_lots = max_lots
        
        optimal_lots = max(0.01, round(optimal_lots, 2))
        bt_size = int(optimal_lots * self.p.lot_size)
        if bt_size < 1000:
            bt_size = 1000
        
        self.order = self.buy(size=bt_size)
        self._reset_state()

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status == order.Completed:
            if order == self.order:
                self.order = None
                
                if self.stop_level and self.take_level:
                    self.stop_order = self.sell(
                        exectype=bt.Order.Stop,
                        price=self.stop_level,
                        size=order.executed.size,
                        oco=None
                    )
                    self.limit_order = self.sell(
                        exectype=bt.Order.Limit,
                        price=self.take_level,
                        size=order.executed.size,
                        oco=self.stop_order
                    )
            else:
                # Exit order filled
                if order == self.stop_order:
                    if self.limit_order:
                        self.cancel(self.limit_order)
                        self.limit_order = None
                    self.stop_order = None
                elif order == self.limit_order:
                    if self.stop_order:
                        self.cancel(self.stop_order)
                        self.stop_order = None
                    self.limit_order = None
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if self.order and order.ref == self.order.ref:
                self.order = None

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
        })
        
        self.stop_level = None
        self.take_level = None

    def stop(self):
        if self.position:
            self.close()


# =============================================================================
# BACKTEST RUNNER
# =============================================================================
def run_single_backtest(
    instrument: str,
    params_override: dict,
    fromdate: str = '2020-01-01',
    todate: str = '2025-12-01',
    starting_cash: float = 100000.0,
) -> dict:
    """Run a single backtest with specified parameters."""
    cerebro = bt.Cerebro()
    
    # Get instrument config
    config = INSTRUMENT_DATA.get(instrument)
    if not config:
        raise ValueError(f"Unknown instrument: {instrument}")
    
    # Load data
    data_dir = PROJECT_ROOT / "data"
    data_path = data_dir / config['data_file']
    
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    
    # Use ForexCSVData to correctly handle Date/Time columns
    data = ForexCSVData(
        dataname=str(data_path),
        fromdate=datetime.strptime(fromdate, '%Y-%m-%d'),
        todate=datetime.strptime(todate, '%Y-%m-%d'),
        timeframe=bt.TimeFrame.Minutes,
        compression=5,
    )
    
    cerebro.adddata(data)
    cerebro.broker.set_cash(starting_cash)
    cerebro.broker.addcommissioninfo(ForexCommission())
    
    # Base params
    base_params = {
        'pip_value': config['pip_value'],
        'lot_size': 100000,
        'print_signals': False,
    }
    
    # Merge with overrides
    final_params = {**base_params, **params_override}
    
    cerebro.addstrategy(KoiOptimized, **final_params)
    
    results = cerebro.run()
    strat = results[0]
    
    # Calculate metrics
    final_value = cerebro.broker.get_value()
    total_pnl = final_value - starting_cash
    
    trades = strat.trades
    wins = strat.wins
    losses = strat.losses
    gross_profit = strat.gross_profit
    gross_loss = strat.gross_loss
    
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
    win_rate = (wins / trades * 100) if trades > 0 else 0
    
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
    
    # Yearly breakdown
    yearly_pnl = defaultdict(float)
    for t in strat._trade_pnls:
        yearly_pnl[t['year']] += t['pnl']
    
    negative_years = sum(1 for pnl in yearly_pnl.values() if pnl < 0)
    
    return {
        'trades': trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_pnl': total_pnl,
        'max_drawdown': max_dd,
        'yearly_pnl': dict(yearly_pnl),
        'negative_years': negative_years,
    }


# =============================================================================
# OPTIMIZATION RUNNER
# =============================================================================
def run_optimization(
    instrument: str,
    param_grid: dict,
    phase_name: str = "",
    fromdate: str = '2020-01-01',
    todate: str = '2025-12-01',
    min_trades: int = 50,
) -> list:
    """Run optimization over parameter grid."""
    print(f"\n{'='*70}", flush=True)
    print(f"KOI OPTIMIZER - {instrument} - {phase_name}", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"Data range: {fromdate} to {todate}", flush=True)
    
    # Generate combinations
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(product(*param_values))
    
    print(f"Parameters: {param_names}", flush=True)
    print(f"Total combinations: {len(combinations)}", flush=True)
    print(f"{'='*70}\n", flush=True)
    
    results = []
    
    for i, combo in enumerate(combinations, 1):
        params_override = dict(zip(param_names, combo))
        
        param_str = " | ".join([f"{k}={v}" for k, v in params_override.items()])
        print(f"[{i}/{len(combinations)}] {param_str}", end=" ", flush=True)
        
        try:
            result = run_single_backtest(
                instrument=instrument,
                params_override=params_override,
                fromdate=fromdate,
                todate=todate,
            )
            result['params'] = params_override
            results.append(result)
            
            print(f"-> T:{result['trades']} PF:{result['profit_factor']:.2f} "
                  f"WR:{result['win_rate']:.1f}% DD:{result['max_drawdown']:.1f}%", flush=True)
            
        except Exception as e:
            print(f"-> ERROR: {e}", flush=True)
    
    # Filter and sort
    valid_results = [r for r in results if r['trades'] >= min_trades]
    valid_results.sort(key=lambda x: x['profit_factor'], reverse=True)
    
    # Print top results
    print(f"\n{'='*70}")
    print(f"TOP 10 RESULTS (min {min_trades} trades)")
    print(f"{'='*70}")
    
    for i, r in enumerate(valid_results[:10], 1):
        param_str = " | ".join([f"{k}={v}" for k, v in r['params'].items()])
        print(f"\n{i}. {param_str}")
        print(f"   Trades: {r['trades']} | WR: {r['win_rate']:.1f}% | PF: {r['profit_factor']:.2f}")
        print(f"   PnL: ${r['total_pnl']:,.0f} | Max DD: {r['max_drawdown']:.1f}%")
    
    return valid_results


# =============================================================================
# MAIN
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description='KOI Strategy Optimizer')
    
    parser.add_argument('instrument', nargs='?', default='USDCHF',
                       choices=list(INSTRUMENT_DATA.keys()),
                       help='Instrument to optimize')
    parser.add_argument('--phase', type=int, default=1, choices=[1, 2, 3, 4, 5],
                       help='Optimization phase')
    parser.add_argument('--all', action='store_true',
                       help='Run all phases')
    parser.add_argument('--quick', action='store_true',
                       help='Quick test (1 year)')
    parser.add_argument('--fromdate', type=str, default='2020-01-01')
    parser.add_argument('--todate', type=str, default='2025-12-01')
    parser.add_argument('--min-trades', type=int, default=50)
    
    args = parser.parse_args()
    
    if args.quick:
        args.fromdate = '2024-01-01'
        args.todate = '2025-01-01'
        args.min_trades = 10
    
    print("=" * 70)
    print(f"KOI UNIVERSAL OPTIMIZER - {args.instrument}")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = {}
    
    phases = {
        1: ('Phase 1: SL/TP', PHASE1_GRID),
        2: ('Phase 2: CCI', PHASE2_GRID),
        3: ('Phase 3: EMAs', PHASE3_GRID),
        4: ('Phase 4: Breakout', PHASE4_GRID),
        5: ('Phase 5: SL Range Filter', PHASE5_GRID),
    }
    
    phases_to_run = list(phases.keys()) if args.all else [args.phase]
    
    for phase_num in phases_to_run:
        phase_name, param_grid = phases[phase_num]
        results = run_optimization(
            instrument=args.instrument,
            param_grid=param_grid,
            phase_name=phase_name,
            fromdate=args.fromdate,
            todate=args.todate,
            min_trades=args.min_trades,
        )
        all_results[f'phase_{phase_num}'] = {
            'name': phase_name,
            'results': results[:20],
        }
    
    # Save results
    output_file = Path(__file__).parent / f'koi_optimization_{args.instrument}.json'
    
    json_results = {
        'instrument': args.instrument,
        'timestamp': datetime.now().isoformat(),
        'phases': {}
    }
    
    for phase_key, phase_data in all_results.items():
        json_results['phases'][phase_key] = {
            'name': phase_data['name'],
            'top_results': [
                {
                    'params': r['params'],
                    'trades': r['trades'],
                    'profit_factor': round(r['profit_factor'], 3),
                    'win_rate': round(r['win_rate'], 2),
                    'total_pnl': round(r['total_pnl'], 2),
                    'max_drawdown': round(r['max_drawdown'], 2),
                }
                for r in phase_data['results'][:10]
            ]
        }
    
    with open(output_file, 'w') as f:
        json.dump(json_results, f, indent=2)
    
    print(f"\n{'='*70}")
    print("OPTIMIZATION COMPLETE")
    print(f"Results saved to: {output_file}")


if __name__ == "__main__":
    main()
