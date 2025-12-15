"""KOI Strategy - Bullish Engulfing + 5 EMA + CCI + Breakout Window
================================================================
ASSET: USDCHF 5M
TIMEFRAME: 5 minutes
DIRECTION: Long-only

ENTRY SYSTEM (4 PHASES):
1. PATTERN: Bullish engulfing candle detected
2. TREND: All 5 EMAs ascending (EMA[0] > EMA[-1])
3. MOMENTUM: CCI > threshold (100)
4. BREAKOUT: Price breaks pattern HIGH + offset within N candles

EXIT SYSTEM:
- Stop Loss: Entry - (ATR x 3.0)
- Take Profit: Entry + (ATR x 12.0)
- Risk:Reward = 1:4

FILTERS:
- SL Range: 10.5-14.5 pips (balanced volatility filter)

PERFORMANCE (2020-2025, 5 years):
- Trades: 148
- Win Rate: 43.2%
- Profit Factor: 1.86
- Max Drawdown: 7.0%
- Net P&L: +$29,364 (+29.4%)

ADVANCED METRICS:
- Sharpe Ratio (Daily): 3.12 [Excellent]
- Sortino Ratio (Daily): 6.26 [Excellent]
- Calmar Ratio: 0.64 [Acceptable]
- Monte Carlo 95% DD: 7.82%

YEARLY BREAKDOWN:
- 2020: -$2,666 (27 trades, WR=25.9%)
- 2021: +$2,262 (31 trades, WR=58.1%)
- 2022: +$11,184 (31 trades, WR=41.9%)
- 2023: +$4,378 (26 trades, WR=38.5%)
- 2024: +$8,617 (16 trades, WR=50.0%)
- 2025: +$5,599 (17 trades, WR=47.1%)

ROBUSTNESS TEST (10 date ranges):
- PF Range: 1.54 - 2.38 (Avg: 1.99)
- Sharpe Range: 2.18 - 4.75 (Avg: 3.52)
- MaxDD Range: 5.0% - 7.0% (Avg: 6.6%)
- Tests passing (PF>=1.5): 10/10 (100%)

COMMISSION MODEL: Darwinex Zero ($2.50/lot/order)
"""
from __future__ import annotations
import math
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import backtrader as bt
import numpy as np

# =============================================================================
# CONFIGURATION
# =============================================================================

DATA_FILENAME = 'USDCHF_5m_5Yea.csv'
FROMDATE = '2020-01-01'
TODATE = '2025-12-01'
STARTING_CASH = 100000.0
ENABLE_PLOT = True  # Set to False for batch testing

FOREX_INSTRUMENT = 'USDCHF'
PIP_VALUE = 0.0001

USE_FIXED_COMMISSION = True
COMMISSION_PER_LOT_PER_ORDER = 2.50
SPREAD_PIPS = 0.7
MARGIN_PERCENT = 3.33

EXPORT_TRADE_REPORTS = True

# =============================================================================
# KOI PARAMETERS - OPTIMIZED
# =============================================================================

# EMAs
EMA_1_PERIOD = 10
EMA_2_PERIOD = 20
EMA_3_PERIOD = 40
EMA_4_PERIOD = 80
EMA_5_PERIOD = 120

# CCI
CCI_PERIOD = 20
CCI_THRESHOLD = 100

# ATR SL/TP
ATR_LENGTH = 10
ATR_SL_MULTIPLIER = 3.0
ATR_TP_MULTIPLIER = 12.0

# Breakout Window
USE_BREAKOUT_WINDOW = True
BREAKOUT_WINDOW_CANDLES = 3
BREAKOUT_LEVEL_OFFSET_PIPS = 5.0

# Risk
RISK_PERCENT = 0.005

# =============================================================================
# FILTERS
# =============================================================================

# Session Filter
USE_SESSION_FILTER = False
ENTRY_START_HOUR = 0
ENTRY_END_HOUR = 23

# Min SL Filter
USE_MIN_SL_FILTER = True
MIN_SL_PIPS = 10.5

# Max SL Filter
USE_MAX_SL_FILTER = True
MAX_SL_PIPS = 14.5

# ATR Filter
USE_ATR_FILTER = False
ATR_MIN_THRESHOLD = 0.00030
ATR_MAX_THRESHOLD = 0.00100

# =============================================================================
# COMMISSION CLASS - Copied from OGLE (works!)
# =============================================================================
class ForexCommission(bt.CommInfoBase):
    """
    Commission scheme for Forex pairs with fixed commission per lot.
    Darwinex Zero specs:
    - Commission: $2.50 per lot per order
    - Margin: 3.33% (30:1 leverage)
    """
    params = (
        ('stocklike', False),
        ('commtype', bt.CommInfoBase.COMM_FIXED),
        ('percabs', True),
        ('leverage', 500.0),
        ('automargin', True),
        ('commission', 2.50),
        ('is_jpy_pair', False),
        ('jpy_rate', 150.0),
    )
    
    # Debug counters (class-level)
    commission_calls = 0
    total_commission = 0.0
    total_lots = 0.0

    def _getcommission(self, size, price, pseudoexec):
        """Return commission based on lot size."""
        if USE_FIXED_COMMISSION:
            lots = abs(size) / 100000.0
            comm = lots * COMMISSION_PER_LOT_PER_ORDER
            
            if not pseudoexec:
                ForexCommission.commission_calls += 1
                ForexCommission.total_commission += comm
                ForexCommission.total_lots += lots
            
            return comm
        return 0.0

    def profitandloss(self, size, price, newprice):
        """Calculate P&L with quote currency conversion."""
        pnl_quote = size * (newprice - price)
        if self.p.is_jpy_pair:
            pnl_quote = pnl_quote * self.p.jpy_rate
        if newprice > 0:
            return pnl_quote / newprice
        return pnl_quote

    def cashadjust(self, size, price, newprice):
        """Adjust cash for non-stocklike instruments."""
        if not self._stocklike:
            return self.profitandloss(size, price, newprice)
        return 0.0


# =============================================================================
# KOI STRATEGY
# =============================================================================
class KOIStrategy(bt.Strategy):
    params = dict(
        ema_1_period=EMA_1_PERIOD,
        ema_2_period=EMA_2_PERIOD,
        ema_3_period=EMA_3_PERIOD,
        ema_4_period=EMA_4_PERIOD,
        ema_5_period=EMA_5_PERIOD,
        cci_period=CCI_PERIOD,
        cci_threshold=CCI_THRESHOLD,
        atr_length=ATR_LENGTH,
        atr_sl_multiplier=ATR_SL_MULTIPLIER,
        atr_tp_multiplier=ATR_TP_MULTIPLIER,
        use_breakout_window=USE_BREAKOUT_WINDOW,
        breakout_window_candles=BREAKOUT_WINDOW_CANDLES,
        breakout_level_offset_pips=BREAKOUT_LEVEL_OFFSET_PIPS,
        risk_percent=RISK_PERCENT,
        use_session_filter=USE_SESSION_FILTER,
        entry_start_hour=ENTRY_START_HOUR,
        entry_end_hour=ENTRY_END_HOUR,
        use_min_sl_filter=USE_MIN_SL_FILTER,
        min_sl_pips=MIN_SL_PIPS,
        use_max_sl_filter=USE_MAX_SL_FILTER,
        max_sl_pips=MAX_SL_PIPS,
        use_atr_filter=USE_ATR_FILTER,
        atr_min_threshold=ATR_MIN_THRESHOLD,
        atr_max_threshold=ATR_MAX_THRESHOLD,
        pip_value=PIP_VALUE,
        contract_size=100000,
        print_signals=False,
    )

    def __init__(self):
        d = self.data
        
        # Indicators
        self.ema_1 = bt.ind.EMA(d.close, period=self.p.ema_1_period)
        self.ema_2 = bt.ind.EMA(d.close, period=self.p.ema_2_period)
        self.ema_3 = bt.ind.EMA(d.close, period=self.p.ema_3_period)
        self.ema_4 = bt.ind.EMA(d.close, period=self.p.ema_4_period)
        self.ema_5 = bt.ind.EMA(d.close, period=self.p.ema_5_period)
        self.cci = bt.ind.CCI(d, period=self.p.cci_period)
        self.atr = bt.ind.ATR(d, period=self.p.atr_length)
        
        # Orders
        self.order = None
        self.stop_order = None
        self.limit_order = None
        
        # Levels
        self.stop_level = None
        self.take_level = None
        self.last_entry_price = None
        self.last_entry_bar = None
        self.last_exit_reason = None
        
        # Breakout state
        self.state = "SCANNING"
        self.pattern_detected_bar = None
        self.breakout_level = None
        self.pattern_atr = None
        self.pattern_cci = None
        
        # Stats
        self.trades = 0
        self.wins = 0
        self.losses = 0
        self.gross_profit = 0.0
        self.gross_loss = 0.0
        self._portfolio_values = []
        self._trade_pnls = []
        
        # Trade reporting
        self.trade_reports = []
        self.trade_report_file = None
        self._init_trade_reporting()

    def _init_trade_reporting(self):
        if EXPORT_TRADE_REPORTS:
            try:
                report_dir = Path("temp_reports")
                report_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_path = report_dir / f"KOI_USDCHF_trades_{timestamp}.txt"
                self.trade_report_file = open(report_path, 'w', encoding='utf-8')
                self.trade_report_file.write("=== KOI STRATEGY TRADE REPORT ===\n")
                self.trade_report_file.write(f"Generated: {datetime.now()}\n")
                self.trade_report_file.write(f"EMAs: {self.p.ema_1_period}, {self.p.ema_2_period}, "
                                            f"{self.p.ema_3_period}, {self.p.ema_4_period}, {self.p.ema_5_period}\n")
                self.trade_report_file.write(f"CCI: {self.p.cci_period}/{self.p.cci_threshold}\n")
                self.trade_report_file.write(f"Breakout: {self.p.breakout_level_offset_pips}pips, {self.p.breakout_window_candles}bars\n\n")
                print(f"Trade report: {report_path}")
            except Exception as e:
                print(f"Trade reporting init failed: {e}")

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
            emas = [self.ema_1, self.ema_2, self.ema_3, self.ema_4, self.ema_5]
            for ema in emas:
                if float(ema[0]) <= float(ema[-1]):
                    return False
            return True
        except:
            return False

    def _check_cci_condition(self):
        try:
            return float(self.cci[0]) > self.p.cci_threshold
        except:
            return False

    def _check_session(self, dt):
        if not self.p.use_session_filter:
            return True
        hour = dt.hour
        if self.p.entry_start_hour <= self.p.entry_end_hour:
            return self.p.entry_start_hour <= hour < self.p.entry_end_hour
        else:
            return hour >= self.p.entry_start_hour or hour < self.p.entry_end_hour

    def _check_entry_conditions(self):
        if self.position or self.order:
            return False
        
        dt = bt.num2date(self.data.datetime[0])
        if not self._check_session(dt):
            return False
        
        if not self._check_bullish_engulfing():
            return False
        
        if not self._check_emas_ascending():
            return False
        
        if not self._check_cci_condition():
            return False
        
        return True

    def _calculate_position_size(self, entry_price, stop_loss):
        equity = self.broker.get_value()
        risk_amount = equity * self.p.risk_percent
        price_risk = abs(entry_price - stop_loss)
        if price_risk <= 0:
            return 0
        pip_risk = price_risk / self.p.pip_value
        pip_value_per_lot = 10.0
        if pip_risk > 0:
            lots = risk_amount / (pip_risk * pip_value_per_lot)
            lots = max(0.01, round(lots, 2))
            lots = min(lots, 10.0)
            return int(lots * self.p.contract_size)
        return 0

    def _reset_breakout_state(self):
        self.state = "SCANNING"
        self.pattern_detected_bar = None
        self.breakout_level = None
        self.pattern_atr = None
        self.pattern_cci = None

    def _record_trade_entry(self, dt, entry_price, size, atr, cci, sl_pips):
        if not self.trade_report_file:
            return
        try:
            entry = {
                'entry_time': dt,
                'entry_price': entry_price,
                'size': size,
                'atr': atr,
                'cci': cci,
                'sl_pips': sl_pips,
                'stop_level': self.stop_level,
                'take_level': self.take_level,
            }
            self.trade_reports.append(entry)
            self.trade_report_file.write(f"ENTRY #{len(self.trade_reports)}\n")
            self.trade_report_file.write(f"Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.trade_report_file.write(f"Entry Price: {entry_price:.5f}\n")
            self.trade_report_file.write(f"Stop Loss: {self.stop_level:.5f}\n")
            self.trade_report_file.write(f"Take Profit: {self.take_level:.5f}\n")
            self.trade_report_file.write(f"SL Pips: {sl_pips:.1f}\n")
            self.trade_report_file.write(f"ATR: {atr:.6f}\n")
            self.trade_report_file.write(f"CCI: {cci:.2f}\n")
            self.trade_report_file.write("-" * 50 + "\n\n")
            self.trade_report_file.flush()
        except Exception as e:
            pass

    def _record_trade_exit(self, dt, pnl, reason):
        if not self.trade_report_file or not self.trade_reports:
            return
        try:
            self.trade_reports[-1]['pnl'] = pnl
            self.trade_reports[-1]['exit_reason'] = reason
            self.trade_report_file.write(f"EXIT #{len(self.trade_reports)}\n")
            self.trade_report_file.write(f"Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.trade_report_file.write(f"Exit Reason: {reason}\n")
            self.trade_report_file.write(f"P&L: ${pnl:.2f}\n")
            self.trade_report_file.write("=" * 80 + "\n\n")
            self.trade_report_file.flush()
        except:
            pass

    def _execute_entry(self, dt, atr_now, cci_now):
        if self.p.use_atr_filter:
            if atr_now < self.p.atr_min_threshold or atr_now > self.p.atr_max_threshold:
                return
        
        entry_price = float(self.data.close[0])
        self.stop_level = entry_price - (atr_now * self.p.atr_sl_multiplier)
        self.take_level = entry_price + (atr_now * self.p.atr_tp_multiplier)
        
        sl_pips = abs(entry_price - self.stop_level) / self.p.pip_value
        
        if self.p.use_min_sl_filter:
            if sl_pips < self.p.min_sl_pips:
                return
        
        if self.p.use_max_sl_filter:
            if sl_pips > self.p.max_sl_pips:
                return
        
        bt_size = self._calculate_position_size(entry_price, self.stop_level)
        if bt_size <= 0:
            return
        
        self.order = self.buy(size=bt_size)
        
        if self.p.print_signals:
            print(f">>> KOI BUY {dt:%Y-%m-%d %H:%M} price={entry_price:.5f} "
                  f"SL={self.stop_level:.5f} TP={self.take_level:.5f} CCI={cci_now:.0f} SL_pips={sl_pips:.1f}")
        
        self._record_trade_entry(dt, entry_price, bt_size, atr_now, cci_now, sl_pips)

    def next(self):
        self._portfolio_values.append(self.broker.get_value())
        
        dt = bt.num2date(self.data.datetime[0])
        current_bar = len(self)
        
        if self.order:
            return
        
        if self.position:
            if self.state != "SCANNING":
                self._reset_breakout_state()
            return
        
        # State machine for breakout window
        if self.p.use_breakout_window:
            if self.state == "SCANNING":
                if self._check_entry_conditions():
                    atr_now = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0
                    cci_now = float(self.cci[0])
                    if atr_now <= 0:
                        return
                    
                    self.pattern_detected_bar = current_bar
                    offset = self.p.breakout_level_offset_pips * self.p.pip_value
                    self.breakout_level = float(self.data.high[0]) + offset
                    self.pattern_atr = atr_now
                    self.pattern_cci = cci_now
                    self.state = "WAITING_BREAKOUT"
                    return
            
            elif self.state == "WAITING_BREAKOUT":
                bars_since = current_bar - self.pattern_detected_bar
                
                if bars_since > self.p.breakout_window_candles:
                    self._reset_breakout_state()
                    return
                
                if float(self.data.high[0]) > self.breakout_level:
                    self._execute_entry(dt, self.pattern_atr, self.pattern_cci)
                    self._reset_breakout_state()
                    return
        else:
            if self._check_entry_conditions():
                atr_now = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0
                cci_now = float(self.cci[0])
                if atr_now > 0:
                    self._execute_entry(dt, atr_now, cci_now)

    def notify_order(self, order):
        """Order notification with OCA for SL/TP - copied from OGLE."""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status == order.Completed:
            if order == self.order:  # Entry order
                self.last_entry_price = order.executed.price
                self.last_entry_bar = len(self)
                
                if self.p.print_signals:
                    print(f"[OK] LONG BUY EXECUTED at {order.executed.price:.5f} size={order.executed.size}")

                # Place protective OCA orders
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

            else:  # Exit order (SL/TP)
                exit_reason = "UNKNOWN"
                if order.exectype == bt.Order.Stop:
                    exit_reason = "STOP_LOSS"
                elif order.exectype == bt.Order.Limit:
                    exit_reason = "TAKE_PROFIT"
                
                self.last_exit_reason = exit_reason
                
                if self.p.print_signals:
                    print(f"[EXIT] at {order.executed.price:.5f} reason={exit_reason}")

                # Reset state
                self.stop_order = None
                self.limit_order = None
                self.order = None
                self.stop_level = None
                self.take_level = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # OCA cancellation is expected
            is_expected_cancel = (self.stop_order and self.limit_order)
            if not is_expected_cancel and self.p.print_signals:
                print(f"Order {order.getstatusname()}: {order.ref}")
            
            if self.order and order.ref == self.order.ref: self.order = None
            if self.stop_order and order.ref == self.stop_order.ref: self.stop_order = None
            if self.limit_order and order.ref == self.limit_order.ref: self.limit_order = None

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
        
        self._trade_pnls.append({
            'date': dt,
            'year': dt.year,
            'pnl': pnl,
            'is_winner': pnl > 0
        })
        
        reason = getattr(self, 'last_exit_reason', 'UNKNOWN')
        self._record_trade_exit(dt, pnl, reason)

    def stop(self):
        """Strategy end - print summary with advanced metrics (Sharpe, Sortino, Calmar, Monte Carlo)."""
        final_value = self.broker.get_value()
        total_pnl = final_value - STARTING_CASH
        win_rate = (self.wins / self.trades * 100) if self.trades > 0 else 0
        profit_factor = (self.gross_profit / self.gross_loss) if self.gross_loss > 0 else float('inf')
        
        # =================================================================
        # MAX DRAWDOWN (from equity curve)
        # =================================================================
        max_drawdown_pct = 0.0
        if self._portfolio_values:
            values = np.array(self._portfolio_values)
            peak = np.maximum.accumulate(values)
            dd = (peak - values) / peak * 100
            max_drawdown_pct = np.max(dd)
        
        # =================================================================
        # CALCULATE DAILY RETURNS FOR RATIOS
        # =================================================================
        daily_returns = []
        if self._trade_pnls:
            # Group trades by date and calculate daily P&L
            daily_pnl = defaultdict(float)
            for trade in self._trade_pnls:
                date_key = trade['date'].date()
                daily_pnl[date_key] += trade['pnl']
            
            # Calculate returns based on cumulative equity
            equity = STARTING_CASH
            sorted_dates = sorted(daily_pnl.keys())
            for date in sorted_dates:
                pnl = daily_pnl[date]
                if equity > 0:
                    daily_ret = pnl / equity
                    daily_returns.append(daily_ret)
                    equity += pnl
        
        # =================================================================
        # SHARPE RATIO (annualized from daily returns)
        # =================================================================
        sharpe_ratio = 0.0
        if len(daily_returns) > 10:
            returns_array = np.array(daily_returns)
            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array)
            if std_return > 0:
                # Annualize: multiply mean by 252, divide by sqrt(252) for std
                sharpe_ratio = (mean_return / std_return) * np.sqrt(252)
        
        # =================================================================
        # CAGR (Compound Annual Growth Rate)
        # =================================================================
        cagr = 0.0
        if len(self._portfolio_values) > 1 and STARTING_CASH > 0:
            total_return = final_value / STARTING_CASH
            if self._trade_pnls:
                first_date = self._trade_pnls[0]['date']
                last_date = self._trade_pnls[-1]['date']
                days = (last_date - first_date).days
                years = max(days / 365.25, 0.1)
            else:
                years = 5.0  # Default assumption
            
            if total_return > 0:
                cagr = (pow(total_return, 1.0 / years) - 1.0) * 100.0
        
        # =================================================================
        # SORTINO RATIO (downside deviation from daily returns)
        # =================================================================
        sortino_ratio = 0.0
        if len(daily_returns) > 10:
            returns_array = np.array(daily_returns)
            mean_return = np.mean(returns_array)
            negative_returns = returns_array[returns_array < 0]
            if len(negative_returns) > 0:
                downside_dev = np.std(negative_returns)
                if downside_dev > 0:
                    sortino_ratio = (mean_return / downside_dev) * np.sqrt(252)
        
        # =================================================================
        # TRADE-BASED SHARPE (alternative metric)
        # =================================================================
        trade_sharpe = 0.0
        if len(self._trade_pnls) > 10:
            pnl_list = [t['pnl'] for t in self._trade_pnls]
            pnl_array = np.array(pnl_list)
            mean_pnl = np.mean(pnl_array)
            std_pnl = np.std(pnl_array)
            if std_pnl > 0:
                # Trades per year estimate
                if self._trade_pnls:
                    first_date = self._trade_pnls[0]['date']
                    last_date = self._trade_pnls[-1]['date']
                    days = max((last_date - first_date).days, 1)
                    trades_per_year = len(self._trade_pnls) * 365.25 / days
                else:
                    trades_per_year = 30  # Default
                trade_sharpe = (mean_pnl / std_pnl) * np.sqrt(trades_per_year)
        
        # =================================================================
        # CALMAR RATIO (CAGR / Max Drawdown)
        # =================================================================
        calmar_ratio = 0.0
        if max_drawdown_pct > 0:
            calmar_ratio = cagr / max_drawdown_pct
        
        # =================================================================
        # MONTE CARLO SIMULATION (10,000 simulations)
        # =================================================================
        monte_carlo_dd_95 = 0.0
        monte_carlo_dd_99 = 0.0
        if len(self._trade_pnls) >= 20:
            n_simulations = 10000
            pnl_list = [t['pnl'] for t in self._trade_pnls]
            mc_max_drawdowns = []
            
            for _ in range(n_simulations):
                shuffled_pnl = np.random.permutation(pnl_list)
                equity = STARTING_CASH
                peak = equity
                max_dd = 0.0
                
                for pnl in shuffled_pnl:
                    equity += pnl
                    if equity > peak:
                        peak = equity
                    dd = (peak - equity) / peak * 100.0 if peak > 0 else 0.0
                    if dd > max_dd:
                        max_dd = dd
                
                mc_max_drawdowns.append(max_dd)
            
            mc_max_drawdowns = np.array(mc_max_drawdowns)
            monte_carlo_dd_95 = np.percentile(mc_max_drawdowns, 95)
            monte_carlo_dd_99 = np.percentile(mc_max_drawdowns, 99)
        
        # =================================================================
        # PRINT SUMMARY
        # =================================================================
        print("\n" + "=" * 70)
        print("=== KOI STRATEGY SUMMARY ===")
        print("=" * 70)
        
        # Commission info
        if USE_FIXED_COMMISSION:
            real_total = ForexCommission.total_commission
            total_lots = ForexCommission.total_lots
            avg_commission_per_trade = real_total / self.trades if self.trades > 0 else 0
            print(f"Commission: ${COMMISSION_PER_LOT_PER_ORDER:.2f}/lot/order (Darwinex Zero)")
            print(f"Total commission: ${real_total:,.2f} | Avg per trade: ${avg_commission_per_trade:.2f}")
        
        print(f"Total Trades: {self.trades}")
        print(f"Wins: {self.wins} | Losses: {self.losses}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Profit Factor: {profit_factor:.2f}")
        print(f"Gross Profit: ${self.gross_profit:,.2f}")
        print(f"Gross Loss: ${self.gross_loss:,.2f}")
        print(f"Net P&L: ${total_pnl:,.0f}")
        print(f"Final Value: ${final_value:,.0f}")
        
        # =================================================================
        # ADVANCED RISK METRICS
        # =================================================================
        print(f"\n{'='*70}")
        print("ADVANCED RISK METRICS")
        print(f"{'='*70}")
        
        sharpe_status = "Poor" if sharpe_ratio < 0.5 else "Marginal" if sharpe_ratio < 1.0 else "Good" if sharpe_ratio < 2.0 else "Excellent"
        print(f"Sharpe Ratio (Daily):  {sharpe_ratio:>8.2f}  [{sharpe_status}]")
        
        sortino_status = "Poor" if sortino_ratio < 0.5 else "Marginal" if sortino_ratio < 1.0 else "Good" if sortino_ratio < 2.0 else "Excellent"
        print(f"Sortino Ratio (Daily): {sortino_ratio:>8.2f}  [{sortino_status}]")
        
        trade_sharpe_status = "Poor" if trade_sharpe < 0.5 else "Marginal" if trade_sharpe < 1.0 else "Good" if trade_sharpe < 2.0 else "Excellent"
        print(f"Sharpe Ratio (Trades): {trade_sharpe:>8.2f}  [{trade_sharpe_status}]")
        
        cagr_status = "Below Market" if cagr < 8 else "Market-level" if cagr < 12 else "Good" if cagr < 20 else "Exceptional"
        print(f"CAGR:                  {cagr:>7.2f}%  [{cagr_status}]")
        
        dd_status = "Excellent" if max_drawdown_pct < 10 else "Acceptable" if max_drawdown_pct < 20 else "High" if max_drawdown_pct < 30 else "Dangerous"
        print(f"Max Drawdown:          {max_drawdown_pct:>7.2f}%  [{dd_status}]")
        
        calmar_status = "Poor" if calmar_ratio < 0.5 else "Acceptable" if calmar_ratio < 1.0 else "Good" if calmar_ratio < 2.0 else "Excellent"
        print(f"Calmar Ratio:          {calmar_ratio:>8.2f}  [{calmar_status}]")
        
        if monte_carlo_dd_95 > 0:
            mc_ratio = monte_carlo_dd_95 / max_drawdown_pct if max_drawdown_pct > 0 else 0
            mc_status = "Good" if mc_ratio < 1.5 else "Caution" if mc_ratio < 2.0 else "Warning"
            print(f"\nMonte Carlo Analysis (10,000 simulations):")
            print(f"  95th Percentile DD: {monte_carlo_dd_95:>6.2f}%  [{mc_status}]")
            print(f"  99th Percentile DD: {monte_carlo_dd_99:>6.2f}%")
            print(f"  Historical vs MC95: {mc_ratio:.2f}x")
        
        # =================================================================
        # YEARLY STATISTICS WITH SHARPE/SORTINO
        # =================================================================
        yearly_stats = defaultdict(lambda: {
            'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0,
            'gross_profit': 0.0, 'gross_loss': 0.0, 'pnls': []
        })
        
        for trade in self._trade_pnls:
            year = trade['year']
            yearly_stats[year]['trades'] += 1
            yearly_stats[year]['pnl'] += trade['pnl']
            yearly_stats[year]['pnls'].append(trade['pnl'])
            if trade['is_winner']:
                yearly_stats[year]['wins'] += 1
                yearly_stats[year]['gross_profit'] += trade['pnl']
            else:
                yearly_stats[year]['losses'] += 1
                yearly_stats[year]['gross_loss'] += abs(trade['pnl'])
        
        # Calculate yearly Sharpe and Sortino
        for year in yearly_stats:
            pnls = yearly_stats[year]['pnls']
            if len(pnls) > 1:
                pnl_array = np.array(pnls)
                mean_pnl = np.mean(pnl_array)
                std_pnl = np.std(pnl_array)
                
                if std_pnl > 0:
                    yearly_stats[year]['sharpe'] = (mean_pnl / std_pnl) * np.sqrt(len(pnls))
                else:
                    yearly_stats[year]['sharpe'] = 0.0
                
                neg_pnls = pnl_array[pnl_array < 0]
                if len(neg_pnls) > 0:
                    downside_std = np.std(neg_pnls)
                    if downside_std > 0:
                        yearly_stats[year]['sortino'] = (mean_pnl / downside_std) * np.sqrt(len(pnls))
                    else:
                        yearly_stats[year]['sortino'] = 0.0
                else:
                    yearly_stats[year]['sortino'] = float('inf') if mean_pnl > 0 else 0.0
            else:
                yearly_stats[year]['sharpe'] = 0.0
                yearly_stats[year]['sortino'] = 0.0
        
        print(f"\n{'='*70}")
        print("YEARLY STATISTICS")
        print(f"{'='*70}")
        print(f"{'Year':<6} {'Trades':>7} {'WR%':>7} {'PF':>7} {'PnL':>12} {'Sharpe':>8} {'Sortino':>8}")
        print(f"{'-'*70}")
        
        for year in sorted(yearly_stats.keys()):
            stats = yearly_stats[year]
            wr = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            year_pf = (stats['gross_profit'] / stats['gross_loss']) if stats['gross_loss'] > 0 else float('inf')
            year_sharpe = stats.get('sharpe', 0.0)
            year_sortino = stats.get('sortino', 0.0)
            
            sortino_str = f"{year_sortino:>7.2f}" if year_sortino != float('inf') else "    inf"
            
            print(f"{year:<6} {stats['trades']:>7} {wr:>6.1f}% {year_pf:>7.2f} ${stats['pnl']:>10,.0f} {year_sharpe:>8.2f} {sortino_str}")
        
        print(f"{'='*70}")
        
        # Close trade reporting
        if self.trade_report_file:
            self.trade_report_file.close()
            print(f"\nTrade report saved.")


# =============================================================================
# SL/TP OBSERVER FOR PLOTTING
# =============================================================================
class SLTPObserver(bt.Observer):
    """Stop Loss and Take Profit Observer for plotting SL/TP levels on chart."""
    lines = ('sl', 'tp',)
    plotinfo = dict(plot=True, subplot=False)
    plotlines = dict(
        sl=dict(color='red', ls='--', linewidth=1.0),
        tp=dict(color='green', ls='--', linewidth=1.0)
    )
    
    def next(self):
        strat = self._owner
        if strat.position:
            self.lines.sl[0] = strat.stop_level if strat.stop_level else float('nan')
            self.lines.tp[0] = strat.take_level if strat.take_level else float('nan')
        else:
            self.lines.sl[0] = float('nan')
            self.lines.tp[0] = float('nan')


# =============================================================================
# MAIN
# =============================================================================
if __name__ == '__main__':
    cerebro = bt.Cerebro(stdstats=False)
    
    # Data
    data_path = Path(__file__).parent.parent.parent / 'data' / DATA_FILENAME
    if not data_path.exists():
        data_path = Path(__file__).parent / DATA_FILENAME
    
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
        openinterest=-1
    )
    cerebro.adddata(data)
    
    # Broker - SAME AS OGLE
    cerebro.broker.setcash(STARTING_CASH)
    if USE_FIXED_COMMISSION:
        cerebro.broker.addcommissioninfo(
            ForexCommission(
                commission=COMMISSION_PER_LOT_PER_ORDER,
                is_jpy_pair=False,
                jpy_rate=1.0
            )
        )
    
    cerebro.addstrategy(KOIStrategy)
    
    # Add observers
    try:
        cerebro.addobserver(bt.observers.BuySell, barplot=False)
    except Exception:
        pass
    
    try:
        cerebro.addobserver(SLTPObserver)
    except Exception:
        pass
    
    try:
        cerebro.addobserver(bt.observers.Value)
    except Exception:
        pass
    
    # Run
    print(f"\n{'='*70}")
    print(f"=== KOI STRATEGY === ({FOREX_INSTRUMENT})")
    print(f"{'='*70}")
    print(f"Period: {FROMDATE} to {TODATE}")
    print(f"Data: {DATA_FILENAME}")
    print(f"Starting Cash: ${STARTING_CASH:,.0f}")
    print(f"Risk per trade: {RISK_PERCENT*100:.2f}%")
    print(f"SL: {ATR_SL_MULTIPLIER}x ATR | TP: {ATR_TP_MULTIPLIER}x ATR")
    print(f"SL Filter: {MIN_SL_PIPS}-{MAX_SL_PIPS} pips")
    print(f"{'='*70}\n")
    
    results = cerebro.run()
    final_value = cerebro.broker.getvalue()
    
    # Enhanced plotting
    if ENABLE_PLOT:
        try:
            strategy_result = results[0]
            final_pnl = final_value - STARTING_CASH
            plot_title = f'KOI Strategy ({FOREX_INSTRUMENT} - LONG-ONLY)\n'
            plot_title += f'Final Value: ${final_value:,.0f} | P&L: ${final_pnl:+,.0f} | '
            plot_title += f'Trades: {strategy_result.trades} | Win Rate: {(strategy_result.wins/strategy_result.trades*100) if strategy_result.trades > 0 else 0:.1f}%'
            
            print(f"[CHART] Showing {FOREX_INSTRUMENT} strategy chart...")
            cerebro.plot(style='candlestick', subtitle=plot_title)
        except Exception as e:
            print(f"Plot error: {e}")
