"""KOI EURUSD - Phase 5 Combinations Test
==========================================
Run TOP combinations from Phases 1-4 with real backtests.
Based on koi_optimizer.py structure.

USAGE:
    python koi_eurusd_combinations.py

COMBINATIONS TO TEST (based on Phase 1-4 results):
- SL/TP variations: 3.0/6.0 (baseline), 2.5/5.0, 3.5/7.0, 3.0/9.0
- Breakout: 2-4 pips offset, 2-4 bars window
- SL Filter: various ranges
- ATR Filter: enabled/disabled with different ranges
"""

import sys
from pathlib import Path
from datetime import datetime
from itertools import product

import backtrader as bt
import numpy as np

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
from koi_template import ForexCommission, ForexCSVData

# =============================================================================
# CONFIGURATION
# =============================================================================
DATA_FILE = Path(__file__).parent.parent.parent / 'data' / 'EURUSD_5m_5Yea.csv'
FROMDATE = '2020-01-01'
TODATE = '2025-07-01'
STARTING_CASH = 100000.0
MIN_TRADES = 100  # Minimum trades for validity

# =============================================================================
# COMBINATIONS TO TEST - Final fine-tune around #11 (PF 1.26)
# =============================================================================
COMBINATIONS = [
    # ID, SL_mult, TP_mult, Breakout_pips, Breakout_bars, SL_min, SL_max, ATR_min, ATR_max, CCI_thresh, Notes
    
    # === Baseline reconfirmation ===
    (1,  2.0, 6.0,  2.0, 3, 8.0, 15.0, 0.00050, 0.00100, 100, "BEST #11"),
    
    # === Breakout fine-tune around 2 pips ===
    (2,  2.0, 6.0,  1.0, 3, 8.0, 15.0, 0.00050, 0.00100, 100, "BO 1 pip"),
    (3,  2.0, 6.0,  1.5, 3, 8.0, 15.0, 0.00050, 0.00100, 100, "BO 1.5 pips"),
    (4,  2.0, 6.0,  2.5, 3, 8.0, 15.0, 0.00050, 0.00100, 100, "BO 2.5 pips"),
    
    # === Breakout window variations ===
    (5,  2.0, 6.0,  2.0, 2, 8.0, 15.0, 0.00050, 0.00100, 100, "BO 2/2"),
    (6,  2.0, 6.0,  2.0, 4, 8.0, 15.0, 0.00050, 0.00100, 100, "BO 2/4"),
    (7,  2.0, 6.0,  2.0, 5, 8.0, 15.0, 0.00050, 0.00100, 100, "BO 2/5"),
    
    # === SL/TP fine-tune ===
    (8,  1.8, 5.4,  2.0, 3, 8.0, 15.0, 0.00050, 0.00100, 100, "SL1.8/TP5.4"),
    (9,  2.0, 7.0,  2.0, 3, 8.0, 15.0, 0.00050, 0.00100, 100, "SL2.0/TP7.0"),
    (10, 2.0, 8.0,  2.0, 3, 8.0, 15.0, 0.00050, 0.00100, 100, "SL2.0/TP8.0"),
    (11, 2.2, 6.6,  2.0, 3, 8.0, 15.0, 0.00050, 0.00100, 100, "SL2.2/TP6.6"),
    
    # === ATR range variations ===
    (12, 2.0, 6.0,  2.0, 3, 8.0, 15.0, 0.00048, 0.00100, 100, "ATR 48-100"),
    (13, 2.0, 6.0,  2.0, 3, 8.0, 15.0, 0.00052, 0.00100, 100, "ATR 52-100"),
    (14, 2.0, 6.0,  2.0, 3, 8.0, 15.0, 0.00050, 0.00095, 100, "ATR 50-95"),
    (15, 2.0, 6.0,  2.0, 3, 8.0, 15.0, 0.00055, 0.00105, 100, "ATR 55-105"),
    
    # === SL pips filter ===
    (16, 2.0, 6.0,  2.0, 3, 6.0, 14.0, 0.00050, 0.00100, 100, "SL 6-14"),
    (17, 2.0, 6.0,  2.0, 3, 7.0, 14.0, 0.00050, 0.00100, 100, "SL 7-14"),
    (18, 2.0, 6.0,  2.0, 3, 8.0, 16.0, 0.00050, 0.00100, 100, "SL 8-16"),
    (19, 2.0, 6.0,  2.0, 3, 9.0, 15.0, 0.00050, 0.00100, 100, "SL 9-15"),
    (20, 2.0, 6.0,  2.0, 3, 8.0, 14.0, 0.00050, 0.00100, 100, "SL 8-14"),
]

# =============================================================================
# STRATEGY CLASS
# =============================================================================
class KoiEURUSD(bt.Strategy):
    params = dict(
        ema_1=10, ema_2=20, ema_3=40, ema_4=80, ema_5=120,
        cci_period=20, cci_threshold=100,
        atr_length=10,
        atr_sl_mult=3.0,
        atr_tp_mult=6.0,
        use_breakout=True,
        breakout_candles=3,
        breakout_offset_pips=3.0,
        risk_percent=0.005,
        pip_value=0.0001,
        lot_size=100000,
        use_min_sl_filter=True,
        min_sl_pips=10.0,
        use_max_sl_filter=True,
        max_sl_pips=20.0,
        use_atr_filter=False,
        atr_min=0.00030,
        atr_max=0.00100,
        print_signals=False,
    )

    def __init__(self):
        self.ema1 = bt.ind.EMA(self.data.close, period=self.p.ema_1)
        self.ema2 = bt.ind.EMA(self.data.close, period=self.p.ema_2)
        self.ema3 = bt.ind.EMA(self.data.close, period=self.p.ema_3)
        self.ema4 = bt.ind.EMA(self.data.close, period=self.p.ema_4)
        self.ema5 = bt.ind.EMA(self.data.close, period=self.p.ema_5)
        self.cci = bt.ind.CCI(self.data, period=self.p.cci_period)
        self.atr = bt.ind.ATR(self.data, period=self.p.atr_length)
        
        self.order = None
        self.stop_order = None
        self.limit_order = None
        self.stop_level = None
        self.take_level = None
        
        self.state = "SCANNING"
        self.pattern_bar = None
        self.breakout_level = None
        self.pattern_atr = None
        self.pattern_cci = None
        
        self.trades = 0
        self.wins = 0
        self.gross_profit = 0.0
        self.gross_loss = 0.0
        self._portfolio_values = []

    def _check_bullish_engulfing(self):
        try:
            prev_open = float(self.data.open[-1])
            prev_close = float(self.data.close[-1])
            if prev_close >= prev_open:
                return False
            curr_open = float(self.data.open[0])
            curr_close = float(self.data.close[0])
            if curr_close <= curr_open:
                return False
            if curr_open > prev_close or curr_close < prev_open:
                return False
            return True
        except:
            return False

    def _check_emas_ascending(self):
        try:
            for ema in [self.ema1, self.ema2, self.ema3, self.ema4, self.ema5]:
                if float(ema[0]) <= float(ema[-1]):
                    return False
            return True
        except:
            return False

    def _check_entry_conditions(self):
        if self.position or self.order:
            return False
        if not self._check_bullish_engulfing():
            return False
        if not self._check_emas_ascending():
            return False
        if float(self.cci[0]) <= self.p.cci_threshold:
            return False
        return True

    def _calculate_size(self, entry, stop):
        equity = self.broker.get_value()
        risk_amount = equity * self.p.risk_percent
        price_risk = abs(entry - stop)
        if price_risk <= 0:
            return 0
        pip_risk = price_risk / self.p.pip_value
        if pip_risk > 0:
            lots = risk_amount / (pip_risk * 10.0)
            lots = max(0.01, round(lots, 2))
            lots = min(lots, 10.0)
            return int(lots * self.p.lot_size)
        return 0

    def _execute_entry(self, atr_now, cci_now):
        # ATR filter
        if self.p.use_atr_filter:
            if atr_now < self.p.atr_min or atr_now > self.p.atr_max:
                return
        
        entry = float(self.data.close[0])
        self.stop_level = entry - (atr_now * self.p.atr_sl_mult)
        self.take_level = entry + (atr_now * self.p.atr_tp_mult)
        
        sl_pips = abs(entry - self.stop_level) / self.p.pip_value
        
        # SL filters
        if self.p.use_min_sl_filter and sl_pips < self.p.min_sl_pips:
            return
        if self.p.use_max_sl_filter and sl_pips > self.p.max_sl_pips:
            return
        
        size = self._calculate_size(entry, self.stop_level)
        if size <= 0:
            return
        
        self.order = self.buy(size=size)

    def _reset_state(self):
        self.state = "SCANNING"
        self.pattern_bar = None
        self.breakout_level = None
        self.pattern_atr = None
        self.pattern_cci = None

    def next(self):
        self._portfolio_values.append(self.broker.get_value())
        
        if self.order:
            return
        
        if self.position:
            if self.state != "SCANNING":
                self._reset_state()
            return
        
        atr_now = float(self.atr[0]) if not np.isnan(float(self.atr[0])) else 0
        cci_now = float(self.cci[0])
        current_bar = len(self)
        
        if self.p.use_breakout:
            if self.state == "SCANNING":
                if self._check_entry_conditions() and atr_now > 0:
                    self.pattern_bar = current_bar
                    offset = self.p.breakout_offset_pips * self.p.pip_value
                    self.breakout_level = float(self.data.high[0]) + offset
                    self.pattern_atr = atr_now
                    self.pattern_cci = cci_now
                    self.state = "WAITING"
            
            elif self.state == "WAITING":
                bars_since = current_bar - self.pattern_bar
                if bars_since > self.p.breakout_candles:
                    self._reset_state()
                    return
                if float(self.data.high[0]) > self.breakout_level:
                    self._execute_entry(self.pattern_atr, self.pattern_cci)
                    self._reset_state()
        else:
            if self._check_entry_conditions() and atr_now > 0:
                self._execute_entry(atr_now, cci_now)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status == order.Completed:
            if order == self.order:
                if self.stop_level and self.take_level:
                    self.stop_order = self.sell(
                        size=order.executed.size,
                        exectype=bt.Order.Stop,
                        price=self.stop_level,
                    )
                    self.limit_order = self.sell(
                        size=order.executed.size,
                        exectype=bt.Order.Limit,
                        price=self.take_level,
                    )
                self.order = None
            else:
                if self.stop_order and order.ref == self.stop_order.ref:
                    if self.limit_order:
                        self.cancel(self.limit_order)
                elif self.limit_order and order.ref == self.limit_order.ref:
                    if self.stop_order:
                        self.cancel(self.stop_order)
                self.stop_order = None
                self.limit_order = None
        
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
        pnl = trade.pnlcomm
        self.trades += 1
        if pnl > 0:
            self.wins += 1
            self.gross_profit += pnl
        else:
            self.gross_loss += abs(pnl)

    def get_metrics(self):
        pf = self.gross_profit / self.gross_loss if self.gross_loss > 0 else 0
        wr = self.wins / self.trades * 100 if self.trades > 0 else 0
        net = self.gross_profit - self.gross_loss
        
        max_dd = 0.0
        if self._portfolio_values:
            values = np.array(self._portfolio_values)
            peak = np.maximum.accumulate(values)
            dd = (peak - values) / peak * 100
            max_dd = np.max(dd)
        
        return {
            'trades': self.trades,
            'wins': self.wins,
            'win_rate': wr,
            'profit_factor': pf,
            'gross_profit': self.gross_profit,
            'gross_loss': self.gross_loss,
            'net_pnl': net,
            'max_drawdown': max_dd,
        }


# =============================================================================
# RUN SINGLE BACKTEST
# =============================================================================
def run_backtest(params):
    """Run a single backtest with given parameters."""
    cerebro = bt.Cerebro(stdstats=False)
    
    data = ForexCSVData(
        dataname=str(DATA_FILE),
        fromdate=datetime.strptime(FROMDATE, '%Y-%m-%d'),
        todate=datetime.strptime(TODATE, '%Y-%m-%d'),
    )
    cerebro.adddata(data)
    
    cerebro.broker.setcash(STARTING_CASH)
    cerebro.broker.addcommissioninfo(ForexCommission(commission=2.50))
    
    cerebro.addstrategy(KoiEURUSD, **params)
    
    results = cerebro.run()
    return results[0].get_metrics()


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 80)
    print("KOI EURUSD - PHASE 5: COMBINATIONS TEST")
    print("=" * 80)
    print(f"Period: {FROMDATE} to {TODATE}")
    print(f"Data: {DATA_FILE.name}")
    print(f"Combinations to test: {len(COMBINATIONS)}")
    print(f"Min trades required: {MIN_TRADES}")
    print("=" * 80)
    print()
    
    results = []
    
    print(f"{'#':<3} {'Config':<35} {'Trades':>7} {'WR%':>6} {'PF':>6} {'PnL':>12} {'DD%':>6}")
    print("-" * 80)
    
    for combo in COMBINATIONS:
        combo_id, sl_m, tp_m, bo_pips, bo_bars, sl_min, sl_max, atr_min, atr_max, cci_th, notes = combo
        
        params = {
            'atr_sl_mult': sl_m,
            'atr_tp_mult': tp_m,
            'breakout_offset_pips': bo_pips,
            'breakout_candles': bo_bars,
            'min_sl_pips': sl_min,
            'max_sl_pips': sl_max,
            'use_atr_filter': atr_min is not None,
            'atr_min': atr_min or 0.00030,
            'atr_max': atr_max or 0.00100,
            'cci_threshold': cci_th,
        }
        
        try:
            metrics = run_backtest(params)
            
            config_str = f"SL{sl_m}/TP{tp_m} BO{bo_pips}/{bo_bars} CCI{cci_th}"
            if atr_min:
                config_str += f" ATR"
            
            status = "✓" if metrics['profit_factor'] >= 1.3 and metrics['trades'] >= MIN_TRADES else ""
            
            print(f"{combo_id:<3} {config_str:<35} {metrics['trades']:>7} {metrics['win_rate']:>5.1f}% "
                  f"{metrics['profit_factor']:>6.2f} ${metrics['net_pnl']:>10,.0f} {metrics['max_drawdown']:>5.1f}% {status}")
            
            results.append({
                'id': combo_id,
                'notes': notes,
                'params': params,
                'metrics': metrics,
            })
            
        except Exception as e:
            print(f"{combo_id:<3} ERROR: {e}")
    
    print("-" * 80)
    
    # Show TOP results
    valid = [r for r in results if r['metrics']['trades'] >= MIN_TRADES]
    valid.sort(key=lambda x: x['metrics']['profit_factor'], reverse=True)
    
    print(f"\n{'='*80}")
    print("TOP 5 BY PROFIT FACTOR (min {MIN_TRADES} trades)")
    print("=" * 80)
    
    for i, r in enumerate(valid[:5], 1):
        m = r['metrics']
        print(f"\n{i}. #{r['id']} - {r['notes']}")
        print(f"   Trades: {m['trades']} | WR: {m['win_rate']:.1f}% | PF: {m['profit_factor']:.2f}")
        print(f"   PnL: ${m['net_pnl']:,.0f} | Max DD: {m['max_drawdown']:.1f}%")
        print(f"   Params: {r['params']}")
    
    print(f"\n{'='*80}")
    print("COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
