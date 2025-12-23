"""OGLE-KOI Dual Strategy - Combined Backtest for USDCAD
=======================================================
ASSET: USDCAD 5M
TIMEFRAME: 5 minutes
DIRECTION: Long-only (both strategies)

DUAL CEREBRO IMPLEMENTATION:
- Each strategy runs in its own cerebro instance
- Portfolio allocation: 50% KOI, 50% OGLE
- Results aggregated for combined performance
- Interactive portfolio charts

STRATEGY 1 - KOI (from koi_usdcad_pro.py):
- Bullish Engulfing + 5 EMAs ascending + CCI 100-130 + Breakout Window
- SL: 3.0x ATR, TP: 12.0x ATR
- SL Filter: 10-18 pips
- Session Filter: H03-17
- Results: 147 trades, PF 1.46, WR 28.6%, Net +$21,905

STRATEGY 2 - OGLE (from sunrise_ogle_usdcad_pro.py):
- EMA Crossover + Pullback + Volatility Expansion Channel
- Results: 127 trades, PF 1.73, WR 32.3%, Net +$24,031

EXPECTED COMBINED: ~274 trades, PF ~1.60, Net ~$46K

COMMISSION MODEL: Darwinex Zero ($2.50/lot/order)
"""
from __future__ import annotations

import backtrader as bt
import numpy as np
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sys

# =============================================================================
# CONFIGURATION - USDCAD
# =============================================================================

DATA_FILENAME = 'USDCAD_5m_5Yea.csv'
FROMDATE = '2020-01-01'
TODATE = '2025-12-01'
STARTING_CASH = 100000.0
ENABLE_PLOT = True

FOREX_INSTRUMENT = 'USDCAD'
PIP_VALUE = 0.0001

USE_FIXED_COMMISSION = True
COMMISSION_PER_LOT_PER_ORDER = 2.50

# Portfolio allocation
KOI_ALLOCATION = 0.50
OGLE_ALLOCATION = 0.50

# Risk per trade
RISK_PERCENT = 0.005


# =============================================================================
# COMMISSION CLASS
# =============================================================================
class ForexCommission(bt.CommInfoBase):
    """Forex commission for Darwinex Zero."""
    params = (
        ('stocklike', False),
        ('commtype', bt.CommInfoBase.COMM_FIXED),
        ('percabs', True),
        ('leverage', 500.0),
        ('automargin', True),
        ('commission', 2.50),
    )

    def _getcommission(self, size, price, pseudoexec):
        if USE_FIXED_COMMISSION:
            lots = abs(size) / 100000.0
            return lots * COMMISSION_PER_LOT_PER_ORDER
        return 0.0

    def profitandloss(self, size, price, newprice):
        pnl_quote = size * (newprice - price)
        if newprice > 0:
            return pnl_quote / newprice
        return pnl_quote

    def cashadjust(self, size, price, newprice):
        if not self._stocklike:
            return self.profitandloss(size, price, newprice)
        return 0.0


# =============================================================================
# KOI STRATEGY (from koi_usdcad_pro.py - OPTIMIZED PARAMS)
# =============================================================================
class KOIStrategy(bt.Strategy):
    """KOI: Bullish Engulfing + 5 EMAs + CCI 100-130 + Breakout Window
    
    USDCAD Optimized Parameters:
    - CCI: 25 period, 100-130 range (sweet spot from trade log)
    - SL: 10-18 pips (from trade log analysis)
    - Session: H03-17
    - Breakout: 5 candles, 5 pips offset
    """
    
    params = dict(
        # EMAs
        ema_periods=[10, 20, 40, 80, 120],
        # CCI - USDCAD optimized
        cci_period=25,
        cci_threshold=100,
        cci_max_threshold=130,  # CCI 100-130 is winning zone
        # ATR SL/TP
        atr_length=10,
        atr_sl_mult=3.0,
        atr_tp_mult=12.0,
        # Breakout window
        breakout_window=5,
        breakout_offset_pips=5.0,
        # SL filters - USDCAD optimized
        min_sl_pips=10.0,
        max_sl_pips=18.0,
        # Session filter - USDCAD optimized
        use_session_filter=True,
        session_start=3,
        session_end=17,
        # Risk
        risk_percent=RISK_PERCENT,
        pip_value=PIP_VALUE,
        contract_size=100000,
        strategy_name='KOI',
    )

    def __init__(self):
        d = self.data
        self.emas = [bt.ind.EMA(d.close, period=p) for p in self.p.ema_periods]
        self.cci = bt.ind.CCI(d, period=self.p.cci_period)
        self.atr = bt.ind.ATR(d, period=self.p.atr_length)
        
        self.order = None
        self.stop_order = None
        self.limit_order = None
        self.stop_level = None
        self.take_level = None
        
        self.state = "SCANNING"
        self.pattern_bar = None
        self.breakout_level = None
        self.pattern_atr = None
        
        self.trades = 0
        self.wins = 0
        self.losses = 0
        self.gross_profit = 0.0
        self.gross_loss = 0.0
        self._trade_pnls = []
        self._portfolio_values = []
        self._timestamps = []

    def _check_session(self):
        """Check if current hour is within trading session."""
        if not self.p.use_session_filter:
            return True
        hour = self.data.datetime.datetime(0).hour
        return self.p.session_start <= hour < self.p.session_end

    def _check_bullish_engulfing(self):
        try:
            prev_open, prev_close = float(self.data.open[-1]), float(self.data.close[-1])
            if prev_close >= prev_open:
                return False
            curr_open, curr_close = float(self.data.open[0]), float(self.data.close[0])
            if curr_close <= curr_open:
                return False
            if curr_open > prev_close or curr_close < prev_open:
                return False
            return True
        except:
            return False

    def _check_emas_ascending(self):
        try:
            for ema in self.emas:
                if float(ema[0]) <= float(ema[-1]):
                    return False
            return True
        except:
            return False

    def _check_cci(self):
        """Check CCI is in winning zone: 100-130"""
        try:
            cci_val = float(self.cci[0])
            return self.p.cci_threshold < cci_val < self.p.cci_max_threshold
        except:
            return False

    def _check_entry_conditions(self):
        if self.position or self.order:
            return False
        if not self._check_session():
            return False
        if not self._check_bullish_engulfing():
            return False
        if not self._check_emas_ascending():
            return False
        if not self._check_cci():
            return False
        return True

    def _calculate_size(self, entry_price, stop_loss):
        equity = self.broker.get_value()
        risk_amount = equity * self.p.risk_percent
        price_risk = abs(entry_price - stop_loss)
        if price_risk <= 0:
            return 0
        pip_risk = price_risk / self.p.pip_value
        pip_value_per_lot = 10.0
        if pip_risk > 0:
            lots = risk_amount / (pip_risk * pip_value_per_lot)
            lots = max(0.01, min(round(lots, 2), 10.0))
            return int(lots * self.p.contract_size)
        return 0

    def _reset_state(self):
        self.state = "SCANNING"
        self.pattern_bar = None
        self.breakout_level = None
        self.pattern_atr = None

    def _execute_entry(self, atr_now):
        entry_price = float(self.data.close[0])
        self.stop_level = entry_price - (atr_now * self.p.atr_sl_mult)
        self.take_level = entry_price + (atr_now * self.p.atr_tp_mult)
        
        sl_pips = abs(entry_price - self.stop_level) / self.p.pip_value
        if sl_pips < self.p.min_sl_pips or sl_pips > self.p.max_sl_pips:
            return
        
        bt_size = self._calculate_size(entry_price, self.stop_level)
        if bt_size <= 0:
            return
        
        self.order = self.buy(size=bt_size)

    def next(self):
        self._portfolio_values.append(self.broker.get_value())
        self._timestamps.append(bt.num2date(self.data.datetime[0]))
        
        if self.order:
            return
        
        if self.position:
            if self.state != "SCANNING":
                self._reset_state()
            return
        
        current_bar = len(self)
        
        if self.state == "SCANNING":
            if self._check_entry_conditions():
                atr_now = float(self.atr[0])
                self.breakout_level = float(self.data.high[0]) + (self.p.breakout_offset_pips * self.p.pip_value)
                self.pattern_bar = current_bar
                self.pattern_atr = atr_now
                self.state = "WAITING_BREAKOUT"
        
        elif self.state == "WAITING_BREAKOUT":
            bars_since = current_bar - self.pattern_bar
            if bars_since > self.p.breakout_window:
                self._reset_state()
                return
            
            if float(self.data.high[0]) > self.breakout_level:
                self._execute_entry(self.pattern_atr)
                self._reset_state()

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status == order.Completed:
            if order == self.order:
                self.order = None
                if order.isbuy():
                    self.stop_order = self.sell(size=order.executed.size, exectype=bt.Order.Stop, price=self.stop_level)
                    self.limit_order = self.sell(size=order.executed.size, exectype=bt.Order.Limit, price=self.take_level, oco=self.stop_order)
            else:
                if self.stop_order and order.ref == self.stop_order.ref:
                    if self.limit_order:
                        self.cancel(self.limit_order)
                    self.stop_order = None
                    self.limit_order = None
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
        
        dt = bt.num2date(self.data.datetime[0])
        pnl = trade.pnlcomm
        
        self.trades += 1
        if pnl > 0:
            self.wins += 1
            self.gross_profit += pnl
        else:
            self.losses += 1
            self.gross_loss += abs(pnl)
        
        self._trade_pnls.append({'date': dt, 'year': dt.year, 'pnl': pnl, 'is_winner': pnl > 0})


# =============================================================================
# OGLE STRATEGY WRAPPER - Imports actual strategy
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

try:
    from sunrise_ogle_usdcad_pro import SunriseOgle as OGLEStrategyBase
    OGLE_AVAILABLE = True
    print("[OK] OGLE strategy imported successfully")
except ImportError as e:
    print(f"[WARN] Could not import OGLE strategy: {e}")
    OGLE_AVAILABLE = False
    OGLEStrategyBase = bt.Strategy


# =============================================================================
# DATA FEED CREATION
# =============================================================================
def create_data_feed(fromdate, todate):
    """Create Backtrader data feed from CSV file."""
    data_path = Path(__file__).parent.parent.parent / 'data' / DATA_FILENAME
    if not data_path.exists():
        data_path = Path(__file__).parent / DATA_FILENAME
    
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    
    return bt.feeds.GenericCSVData(
        dataname=str(data_path),
        fromdate=datetime.strptime(fromdate, '%Y-%m-%d'),
        todate=datetime.strptime(todate, '%Y-%m-%d'),
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
        compression=5
    )


# =============================================================================
# RUN SINGLE STRATEGY BACKTEST
# =============================================================================
def run_single_strategy_backtest(strategy_class, strategy_name, allocation, fromdate, todate, starting_cash, **extra_kwargs):
    """Run backtest for a single strategy."""
    print(f"\n[RUN] Running {strategy_name} backtest...")
    
    cerebro = bt.Cerebro(stdstats=False)
    
    data = create_data_feed(fromdate, todate)
    cerebro.adddata(data)
    
    asset_cash = starting_cash * allocation
    cerebro.broker.setcash(asset_cash)
    
    if USE_FIXED_COMMISSION:
        cerebro.broker.addcommissioninfo(ForexCommission(commission=COMMISSION_PER_LOT_PER_ORDER))
    
    cerebro.addstrategy(strategy_class, **extra_kwargs)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    
    initial_value = cerebro.broker.getvalue()
    print(f"  Initial Value: ${initial_value:,.2f}")
    
    results = cerebro.run()
    strategy_result = results[0]
    
    final_value = cerebro.broker.getvalue()
    total_return = final_value - initial_value
    return_pct = (total_return / initial_value) * 100
    
    print(f"  Final Value: ${final_value:,.2f}")
    print(f"  P&L: ${total_return:,.2f} ({return_pct:+.2f}%)")
    
    trade_analyzer = strategy_result.analyzers.trades.get_analysis()
    drawdown_analyzer = strategy_result.analyzers.drawdown.get_analysis()
    
    return {
        'strategy_name': strategy_name,
        'cerebro': cerebro,
        'strategy': strategy_result,
        'initial_value': initial_value,
        'final_value': final_value,
        'total_return': total_return,
        'return_pct': return_pct,
        'trade_analysis': trade_analyzer,
        'drawdown_analysis': drawdown_analyzer,
    }


# =============================================================================
# AGGREGATE RESULTS
# =============================================================================
def aggregate_results(results_list, starting_cash):
    """Aggregate results from both strategies."""
    print(f"\n" + "=" * 70)
    print(f"=== OGLE-KOI DUAL STRATEGY SUMMARY (USDCAD) ===")
    print(f"=" * 70)
    
    total_initial = sum(r['initial_value'] for r in results_list)
    total_final = sum(r['final_value'] for r in results_list)
    total_pnl = total_final - total_initial
    total_return_pct = (total_pnl / total_initial) * 100
    
    all_trade_pnls = []
    total_trades = 0
    total_wins = 0
    total_losses = 0
    total_gross_profit = 0.0
    total_gross_loss = 0.0
    
    print(f"\n{'=' * 70}")
    print("INDIVIDUAL STRATEGY PERFORMANCE")
    print(f"{'=' * 70}")
    print(f"{'Strategy':<10} {'Trades':>8} {'WR%':>8} {'PF':>8} {'Net P&L':>12}")
    print(f"{'-' * 70}")
    
    for result in results_list:
        name = result['strategy_name']
        strat = result['strategy']
        
        trades = getattr(strat, 'trades', 0)
        wins = getattr(strat, 'wins', 0)
        losses = getattr(strat, 'losses', 0)
        gross_profit = getattr(strat, 'gross_profit', 0.0)
        gross_loss = getattr(strat, 'gross_loss', 0.0)
        trade_pnls = getattr(strat, '_trade_pnls', [])
        
        wr = (wins / trades * 100) if trades > 0 else 0
        pf = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
        net_pnl = gross_profit - gross_loss
        
        pf_str = f"{pf:.2f}" if pf != float('inf') else "∞"
        print(f"{name:<10} {trades:>8} {wr:>7.1f}% {pf_str:>8} ${net_pnl:>10,.0f}")
        
        total_trades += trades
        total_wins += wins
        total_losses += losses
        total_gross_profit += gross_profit
        total_gross_loss += gross_loss
        all_trade_pnls.extend(trade_pnls)
    
    combined_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0
    combined_pf = (total_gross_profit / total_gross_loss) if total_gross_loss > 0 else float('inf')
    combined_pf_str = f"{combined_pf:.2f}" if combined_pf != float('inf') else "∞"
    
    print(f"{'-' * 70}")
    print(f"{'COMBINED':<10} {total_trades:>8} {combined_wr:>7.1f}% {combined_pf_str:>8} ${total_pnl:>10,.0f}")
    
    print(f"\n{'=' * 70}")
    print("COMBINED METRICS")
    print(f"{'=' * 70}")
    print(f"Total Trades: {total_trades}")
    print(f"Wins: {total_wins} | Losses: {total_losses}")
    print(f"Win Rate: {combined_wr:.1f}%")
    print(f"Profit Factor: {combined_pf_str}")
    print(f"Gross Profit: ${total_gross_profit:,.2f}")
    print(f"Gross Loss: ${total_gross_loss:,.2f}")
    print(f"Net P&L: ${total_pnl:,.0f}")
    print(f"Final Value: ${total_final:,.0f}")
    
    # Trade-based returns (more realistic for low-frequency strategies)
    trade_returns = []
    trades_per_year = 0
    if all_trade_pnls:
        equity = starting_cash
        for trade in sorted(all_trade_pnls, key=lambda x: x['date']):
            ret = trade['pnl'] / equity
            trade_returns.append(ret)
            equity += trade['pnl']
        
        # Calculate trades per year for annualization
        first_date = min(t['date'] for t in all_trade_pnls)
        last_date = max(t['date'] for t in all_trade_pnls)
        years = max((last_date - first_date).days / 365.25, 0.1)
        trades_per_year = len(trade_returns) / years
    
    # Sharpe Ratio (Trade-based, annualized by trades/year)
    sharpe_ratio = 0.0
    if len(trade_returns) > 10:
        returns_array = np.array(trade_returns)
        mean_return = np.mean(returns_array)
        std_return = np.std(returns_array)
        if std_return > 0:
            sharpe_ratio = (mean_return / std_return) * np.sqrt(trades_per_year)
    
    # Sortino Ratio (Trade-based, annualized by trades/year)
    sortino_ratio = 0.0
    if len(trade_returns) > 10:
        returns_array = np.array(trade_returns)
        mean_return = np.mean(returns_array)
        negative_returns = returns_array[returns_array < 0]
        if len(negative_returns) > 0:
            downside_std = np.std(negative_returns)
            if downside_std > 0:
                sortino_ratio = (mean_return / downside_std) * np.sqrt(trades_per_year)
    
    # CAGR
    cagr = 0.0
    if starting_cash > 0 and all_trade_pnls:
        total_return_ratio = total_final / starting_cash
        first_date = min(t['date'] for t in all_trade_pnls)
        last_date = max(t['date'] for t in all_trade_pnls)
        years = (last_date - first_date).days / 365.25
        if years > 0 and total_return_ratio > 0:
            cagr = (total_return_ratio ** (1 / years) - 1) * 100
    
    # Max Drawdown
    max_dd_pct = 0.0
    if all_trade_pnls:
        sorted_trades = sorted(all_trade_pnls, key=lambda x: x['date'])
        equity_curve = [starting_cash]
        for t in sorted_trades:
            equity_curve.append(equity_curve[-1] + t['pnl'])
        values = np.array(equity_curve)
        peak = np.maximum.accumulate(values)
        dd = (peak - values) / peak * 100
        max_dd_pct = np.max(dd)
    
    # Calmar Ratio
    calmar_ratio = cagr / max_dd_pct if max_dd_pct > 0 else 0.0
    
    # Monte Carlo
    mc_dd_95, mc_dd_99 = 0.0, 0.0
    if len(all_trade_pnls) >= 20:
        pnl_list = [t['pnl'] for t in all_trade_pnls]
        mc_drawdowns = []
        for _ in range(10000):
            shuffled = np.random.permutation(pnl_list)
            equity = starting_cash
            peak = equity
            max_dd = 0.0
            for pnl in shuffled:
                equity += pnl
                if equity > peak:
                    peak = equity
                dd = (peak - equity) / peak * 100
                if dd > max_dd:
                    max_dd = dd
            mc_drawdowns.append(max_dd)
        mc_drawdowns = np.array(mc_drawdowns)
        mc_dd_95 = np.percentile(mc_drawdowns, 95)
        mc_dd_99 = np.percentile(mc_drawdowns, 99)
    
    # Print advanced metrics
    print(f"\n{'=' * 70}")
    print("ADVANCED RISK METRICS")
    print(f"{'=' * 70}")
    
    if trades_per_year > 0:
        print(f"Trades/Year: {trades_per_year:.1f} (annualization: √{trades_per_year:.0f})")
    
    sharpe_status = "Poor" if sharpe_ratio < 0.5 else "Marginal" if sharpe_ratio < 1.0 else "Good" if sharpe_ratio < 2.0 else "Excellent"
    print(f"Sharpe Ratio:          {sharpe_ratio:>8.2f}  [{sharpe_status}]")
    
    sortino_status = "Poor" if sortino_ratio < 0.5 else "Marginal" if sortino_ratio < 1.0 else "Good" if sortino_ratio < 2.0 else "Excellent"
    print(f"Sortino Ratio:         {sortino_ratio:>8.2f}  [{sortino_status}]")
    
    cagr_status = "Below Market" if cagr < 8 else "Market-level" if cagr < 12 else "Good" if cagr < 20 else "Exceptional"
    print(f"CAGR:                  {cagr:>7.2f}%  [{cagr_status}]")
    
    dd_status = "Excellent" if max_dd_pct < 10 else "Acceptable" if max_dd_pct < 20 else "High" if max_dd_pct < 30 else "Dangerous"
    print(f"Max Drawdown:          {max_dd_pct:>7.2f}%  [{dd_status}]")
    
    calmar_status = "Poor" if calmar_ratio < 0.5 else "Acceptable" if calmar_ratio < 1.0 else "Good" if calmar_ratio < 2.0 else "Excellent"
    print(f"Calmar Ratio:          {calmar_ratio:>8.2f}  [{calmar_status}]")
    
    if mc_dd_95 > 0:
        mc_ratio = mc_dd_95 / max_dd_pct if max_dd_pct > 0 else 0
        mc_status = "Good" if mc_ratio < 1.5 else "Caution" if mc_ratio < 2.0 else "Warning"
        print(f"\nMonte Carlo Analysis (10,000 simulations):")
        print(f"  95th Percentile DD: {mc_dd_95:>6.2f}%  [{mc_status}]")
        print(f"  99th Percentile DD: {mc_dd_99:>6.2f}%")
        print(f"  Historical vs MC95: {mc_ratio:.2f}x")
    
    # Yearly stats
    yearly_stats = defaultdict(lambda: {'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0, 'gross_profit': 0.0, 'gross_loss': 0.0})
    for trade in all_trade_pnls:
        year = trade['year']
        yearly_stats[year]['trades'] += 1
        yearly_stats[year]['pnl'] += trade['pnl']
        if trade['is_winner']:
            yearly_stats[year]['wins'] += 1
            yearly_stats[year]['gross_profit'] += trade['pnl']
        else:
            yearly_stats[year]['losses'] += 1
            yearly_stats[year]['gross_loss'] += abs(trade['pnl'])
    
    print(f"\n{'=' * 70}")
    print("YEARLY STATISTICS (COMBINED)")
    print(f"{'=' * 70}")
    print(f"{'Year':<6} {'Trades':>7} {'WR%':>7} {'PF':>7} {'PnL':>12}")
    print(f"{'-' * 70}")
    
    for year in sorted(yearly_stats.keys()):
        stats = yearly_stats[year]
        wr = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
        pf = (stats['gross_profit'] / stats['gross_loss']) if stats['gross_loss'] > 0 else float('inf')
        pf_str = f"{pf:.2f}" if pf != float('inf') else "∞"
        print(f"{year:<6} {stats['trades']:>7} {wr:>6.1f}% {pf_str:>7} ${stats['pnl']:>10,.0f}")
    
    print(f"{'=' * 70}")
    
    return {
        'total_pnl': total_pnl,
        'total_return_pct': total_return_pct,
        'sharpe': sharpe_ratio,
        'sortino': sortino_ratio,
        'max_dd': max_dd_pct,
        'combined_pf': combined_pf,
        'total_trades': total_trades,
        'all_trade_pnls': all_trade_pnls,
    }


# =============================================================================
# INTERACTIVE PORTFOLIO CHARTS
# =============================================================================
def create_portfolio_charts(results_list, starting_cash):
    """Create interactive portfolio charts."""
    if not ENABLE_PLOT:
        return
    
    print(f"\n[CHART] Creating interactive portfolio charts...")
    
    portfolio_data = {}
    
    for result in results_list:
        name = result['strategy_name']
        strat = result['strategy']
        
        if hasattr(strat, '_portfolio_values') and hasattr(strat, '_timestamps'):
            timestamps = strat._timestamps
            values = strat._portfolio_values
            
            if len(timestamps) > 0 and len(values) > 0:
                portfolio_data[name] = {
                    'timestamps': timestamps,
                    'values': values,
                    'initial_value': result['initial_value']
                }
                print(f"  {name}: {len(timestamps)} data points")
    
    if not portfolio_data:
        print("  No portfolio data available")
        return
    
    # Calculate combined portfolio
    combined_total = []
    combined_timestamps = []
    
    if len(portfolio_data) >= 2:
        strategies = list(portfolio_data.keys())
        min_length = min(len(portfolio_data[s]['values']) for s in strategies)
        combined_timestamps = portfolio_data[strategies[0]]['timestamps'][:min_length]
        
        for i in range(min_length):
            total_val = sum(portfolio_data[s]['values'][i] for s in strategies)
            combined_total.append(total_val)
    elif len(portfolio_data) == 1:
        name = list(portfolio_data.keys())[0]
        combined_timestamps = portfolio_data[name]['timestamps']
        combined_total = list(portfolio_data[name]['values'])
    
    colors = {'KOI': '#2E86AB', 'OGLE': '#F18F01', 'Combined': '#2ca02c'}
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 12), sharex=True)
    fig.suptitle(f'OGLE-KOI Multi-Strategy Backtest ({FOREX_INSTRUMENT} 5M)', 
                 fontsize=20, fontweight='bold', y=0.98)
    
    # SUBPLOT 1: Individual Strategies
    for name, data in portfolio_data.items():
        timestamps = data['timestamps']
        values = data['values']
        
        if values:
            initial = data['initial_value']
            final = values[-1]
            pnl_pct = ((final - initial) / initial) * 100
            legend_label = f'{name}: ${final:,.0f} ({pnl_pct:+.1f}%)'
        else:
            legend_label = f'{name} Portfolio'
        
        ax1.plot(timestamps, values,
                 label=legend_label,
                 color=colors.get(name, '#333333'),
                 linewidth=2.5,
                 alpha=0.85)
    
    title_parts = []
    for name, data in portfolio_data.items():
        if data['values']:
            initial = data['initial_value']
            final = data['values'][-1]
            pnl_pct = ((final - initial) / initial) * 100
            title_parts.append(f"{name}: {pnl_pct:+.1f}%")
    ax1.set_title("Individual Strategy Performance | " + " | ".join(title_parts), 
                  fontsize=14, fontweight='bold', pad=10)
    
    ax1.set_ylabel('Portfolio Value ($)', fontsize=12, fontweight='bold')
    ax1.legend(loc='upper left', fontsize=11, framealpha=0.95, fancybox=True, shadow=True)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    # SUBPLOT 2: Combined Portfolio
    if combined_total and combined_timestamps:
        combined_initial = sum(data['initial_value'] for data in portfolio_data.values())
        combined_final = combined_total[-1] if combined_total else combined_initial
        combined_pnl = combined_final - combined_initial
        combined_pnl_pct = (combined_pnl / combined_initial) * 100
        
        ax2.plot(combined_timestamps, combined_total,
                 label=f'Combined Portfolio: ${combined_final:,.0f} ({combined_pnl_pct:+.1f}%)',
                 color=colors['Combined'],
                 linewidth=3,
                 alpha=0.9)
        
        ax2.fill_between(combined_timestamps, combined_initial, combined_total, 
                         alpha=0.2, color=colors['Combined'])
        
        ax2.set_title(f"Combined Portfolio | Initial: ${combined_initial:,.0f} | Final: ${combined_final:,.0f} | P&L: ${combined_pnl:,.0f} ({combined_pnl_pct:+.2f}%)", 
                      fontsize=14, fontweight='bold', pad=10)
    
    ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Portfolio Value ($)', fontsize=12, fontweight='bold')
    ax2.legend(loc='upper left', fontsize=11, framealpha=0.95, fancybox=True, shadow=True)
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show()
    print(f"  [OK] Interactive chart displayed!")


# =============================================================================
# MAIN
# =============================================================================
def run_dual_strategy_backtest():
    """Main function to run dual strategy backtest."""
    print(f"=== OGLE-KOI DUAL STRATEGY BACKTEST ({FOREX_INSTRUMENT}) ===")
    print(f"Period: {FROMDATE} to {TODATE}")
    print(f"Starting Cash: ${STARTING_CASH:,.2f}")
    print(f"Strategies: KOI ({KOI_ALLOCATION*100:.0f}%), OGLE ({OGLE_ALLOCATION*100:.0f}%)")
    
    all_results = []
    
    # Run KOI
    try:
        koi_result = run_single_strategy_backtest(
            KOIStrategy, 'KOI', KOI_ALLOCATION,
            FROMDATE, TODATE, STARTING_CASH
        )
        all_results.append(koi_result)
    except Exception as e:
        print(f"[ERROR] Error running KOI: {e}")
        import traceback
        traceback.print_exc()
    
    # Run OGLE
    if OGLE_AVAILABLE:
        try:
            ogle_result = run_single_strategy_backtest(
                OGLEStrategyBase, 'OGLE', OGLE_ALLOCATION,
                FROMDATE, TODATE, STARTING_CASH,
                plot_result=False,
                print_signals=False,
                verbose_debug=False,
                use_forex_position_calc=True,
                forex_instrument=FOREX_INSTRUMENT,
            )
            all_results.append(ogle_result)
        except Exception as e:
            print(f"[ERROR] Error running OGLE: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[WARN] OGLE strategy not available - running KOI only")
    
    if not all_results:
        print("[ERROR] No strategies completed!")
        return None, None
    
    summary = aggregate_results(all_results, STARTING_CASH)
    create_portfolio_charts(all_results, STARTING_CASH)
    
    return summary, all_results


if __name__ == '__main__':
    try:
        summary, results = run_dual_strategy_backtest()
        if summary:
            print(f"\n[DONE] Dual strategy backtest completed!")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
