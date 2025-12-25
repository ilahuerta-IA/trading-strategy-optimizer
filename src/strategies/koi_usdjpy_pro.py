"""KOI Strategy - Bullish Engulfing + 5 EMA + CCI + Breakout Window
================================================================
ASSET: USDJPY 5M
TIMEFRAME: 5 minutes
DIRECTION: Long-only

OPTIMIZED PARAMETERS (Dec 2025):
- Phase 1 SL/TP: SL=3.5x ATR, TP=10.0x ATR
- Phase 2 CCI: Period=14, Threshold=120
- Phase 4 Breakout: Offset=7 pips, Window=7 bars
- Session Filter: Hours [0,1,3,4,5,11,13,16,17,20,22,23] (PnL > 0)
- SL Filter: DISABLED (reduces performance)

PERFORMANCE (5 years, 2020-2025, with commissions):
- Profit Factor: 1.60 (target >1.5 ✓)
- Trades: 282 (target >120 ✓)
- Win Rate: 37.2%
- Sharpe Ratio: 3.44 (Excellent)
- Max Drawdown: 6.84% (Excellent)
- Net PnL: +$53,355
- All years profitable ✓

ENTRY SYSTEM (4 PHASES):
1. PATTERN: Bullish engulfing candle detected
2. TREND: All 5 EMAs ascending (EMA[0] > EMA[-1])
3. MOMENTUM: CCI > 120
4. BREAKOUT: Price breaks pattern HIGH + 7 pips within 7 candles

EXIT SYSTEM:
- Stop Loss: Entry - (ATR x 3.5)
- Take Profit: Entry + (ATR x 10.0)
- Risk:Reward = 1:2.86

JPY PAIR IMPLEMENTATION (from JPY_PNL_GUIDE.md):
- PIP_VALUE = 0.01 (not 0.0001)
- Position size divided by forex_jpy_rate (~150)
- P&L compensated by JPY_RATE_COMPENSATION (150.0)
- Commission restored to actual lot size

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

DATA_FILENAME = 'USDJPY_5m_5Yea.csv'
FROMDATE = '2020-01-01'
TODATE = '2025-12-01'
STARTING_CASH = 100000.0
ENABLE_PLOT = True  # Set to False for batch testing

FOREX_INSTRUMENT = 'USDJPY'
PIP_VALUE = 0.01  # JPY pairs use 0.01
FOREX_JPY_RATE = 150.0  # For position sizing and P&L compensation

USE_FIXED_COMMISSION = True
COMMISSION_PER_LOT_PER_ORDER = 2.50
SPREAD_PIPS = 1.0  # USDJPY typical spread
MARGIN_PERCENT = 3.33

EXPORT_TRADE_REPORTS = True

# =============================================================================
# KOI PARAMETERS - TO OPTIMIZE FOR USDJPY
# =============================================================================

# EMAs
EMA_1_PERIOD = 10
EMA_2_PERIOD = 20
EMA_3_PERIOD = 40
EMA_4_PERIOD = 80
EMA_5_PERIOD = 120

# CCI - OPTIMIZED Phase 2
CCI_PERIOD = 14
CCI_THRESHOLD = 120

# ATR SL/TP - OPTIMIZED Phase 1
ATR_LENGTH = 10
ATR_SL_MULTIPLIER = 3.5
ATR_TP_MULTIPLIER = 10.0

# Breakout Window - OPTIMIZED Phase 4
USE_BREAKOUT_WINDOW = True
BREAKOUT_WINDOW_CANDLES = 7
BREAKOUT_LEVEL_OFFSET_PIPS = 7.0

# Risk
RISK_PERCENT = 0.005

# =============================================================================
# FILTERS - TO OPTIMIZE FOR USDJPY
# =============================================================================

# Session Filter - Trade only during profitable hours (UTC server time)
# From log analysis: Best hours = 4 (+$8,936), 23 (+$6,975), 1 (+$5,658), 0 (+$4,504)
USE_SESSION_FILTER = True
PROFITABLE_HOURS = [0, 1, 3, 4, 5, 11, 13, 16, 17, 20, 22, 23]  # All PnL > 0 hours

# Min SL Filter (JPY: values in pips where 1 pip = 0.01)
USE_MIN_SL_FILTER = False
MIN_SL_PIPS = 5.0  # JPY pairs have different SL ranges

# Max SL Filter
USE_MAX_SL_FILTER = False
MAX_SL_PIPS = 15.0

# ATR Filter (JPY: ATR values are ~100x larger than standard pairs)
USE_ATR_FILTER = False
ATR_MIN_THRESHOLD = 0.030  # e.g., 3 pips
ATR_MAX_THRESHOLD = 0.100  # e.g., 10 pips

# =============================================================================
# COMMISSION CLASS - JPY Pair Support (from JPY_PNL_GUIDE.md)
# =============================================================================
class ForexCommission(bt.CommInfoBase):
    """
    Commission scheme for Forex pairs with fixed commission per lot.
    JPY pair support with position size/P&L compensation.
    
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
        ('is_jpy_pair', True),  # USDJPY = True
        ('jpy_rate', 150.0),
    )
    
    # Debug counters (class-level)
    commission_calls = 0
    total_commission = 0.0
    total_lots = 0.0

    def _getcommission(self, size, price, pseudoexec):
        """
        Return commission based on lot size.
        
        JPY PAIRS: size was divided by jpy_rate (~150) for P&L calculation,
        but commission must be based on ACTUAL lot size, so we restore it.
        """
        if USE_FIXED_COMMISSION:
            # For JPY pairs: restore actual size before calculating lots
            actual_size = abs(size)
            if self.p.is_jpy_pair:
                actual_size = actual_size * self.p.jpy_rate  # Restore real size
            
            lots = actual_size / 100000.0
            comm = lots * COMMISSION_PER_LOT_PER_ORDER
            
            if not pseudoexec:
                ForexCommission.commission_calls += 1
                ForexCommission.total_commission += comm
                ForexCommission.total_lots += lots
            
            return comm
        return 0.0

    def profitandloss(self, size, price, newprice):
        """Calculate P&L in USD from JPY-denominated gains/losses.
        
        Since bt_size is divided by ~150 for margin management,
        we multiply P&L by 150 to compensate and get correct USD P&L.
        """
        if self.p.is_jpy_pair:
            # Size was divided by forex_jpy_rate (~150), so we multiply back
            JPY_RATE_COMPENSATION = 150.0
            pnl_jpy = size * JPY_RATE_COMPENSATION * (newprice - price)
            if newprice > 0:
                return pnl_jpy / newprice
            return pnl_jpy
        else:
            # Standard forex P&L
            pnl_quote = size * (newprice - price)
            if newprice > 0:
                return pnl_quote / newprice
            return pnl_quote

    def cashadjust(self, size, price, newprice):
        """Adjust cash for non-stocklike instruments."""
        if not self._stocklike:
            return self.profitandloss(size, price, newprice)
        return 0.0


# =============================================================================
# CUSTOM CSV DATA FEED - Fixes Date/Time separate columns issue
# =============================================================================
class ForexCSVData(bt.feeds.GenericCSVData):
    """
    Custom CSV Data Feed that correctly handles separate Date and Time columns.
    """
    
    def _loadline(self, linetokens):
        # Parse Date (column 0) and Time (column 1) 
        dt_str = linetokens[0]  # '20200101'
        tm_str = linetokens[1]  # '22:00:00'
        
        # Combine into datetime
        try:
            dt = datetime.strptime(f"{dt_str} {tm_str}", '%Y%m%d %H:%M:%S')
        except ValueError:
            return False
        
        # Check date filters
        if self.p.fromdate and dt < self.p.fromdate:
            return False
        if self.p.todate and dt > self.p.todate:
            return False
        
        # Set datetime as float (matplotlib date number)
        self.lines.datetime[0] = bt.date2num(dt)
        
        # Set OHLCV
        self.lines.open[0] = float(linetokens[2])
        self.lines.high[0] = float(linetokens[3])
        self.lines.low[0] = float(linetokens[4])
        self.lines.close[0] = float(linetokens[5])
        self.lines.volume[0] = float(linetokens[6])
        self.lines.openinterest[0] = 0.0
        
        return True


# =============================================================================
# KOI STRATEGY - USDJPY
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
        profitable_hours=PROFITABLE_HOURS,
        use_min_sl_filter=USE_MIN_SL_FILTER,
        min_sl_pips=MIN_SL_PIPS,
        use_max_sl_filter=USE_MAX_SL_FILTER,
        max_sl_pips=MAX_SL_PIPS,
        use_atr_filter=USE_ATR_FILTER,
        atr_min_threshold=ATR_MIN_THRESHOLD,
        atr_max_threshold=ATR_MAX_THRESHOLD,
        pip_value=PIP_VALUE,
        contract_size=100000,
        forex_jpy_rate=FOREX_JPY_RATE,  # CRITICAL: JPY rate for position sizing
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
                report_path = report_dir / f"KOI_USDJPY_trades_{timestamp}.txt"
                self.trade_report_file = open(report_path, 'w', encoding='utf-8')
                self.trade_report_file.write("=== KOI STRATEGY TRADE REPORT (USDJPY) ===\n")
                self.trade_report_file.write(f"Generated: {datetime.now()}\n")
                self.trade_report_file.write(f"EMAs: {self.p.ema_1_period}, {self.p.ema_2_period}, "
                                            f"{self.p.ema_3_period}, {self.p.ema_4_period}, {self.p.ema_5_period}\n")
                self.trade_report_file.write(f"CCI: {self.p.cci_period}/{self.p.cci_threshold}\n")
                self.trade_report_file.write(f"Breakout: {self.p.breakout_level_offset_pips}pips, {self.p.breakout_window_candles}bars\n\n")
                print(f"Trade report: {report_path}")
            except Exception as e:
                print(f"Trade reporting init failed: {e}")

    def _get_datetime(self, offset=0):
        """Get correct datetime combining date and time from CSV."""
        try:
            dt_date = self.data.datetime.date(offset)
            dt_time = self.data.datetime.time(offset)
            return datetime.combine(dt_date, dt_time)
        except Exception:
            return self.data.datetime.datetime(offset)

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
        # Use list of profitable hours instead of range
        return hour in self.p.profitable_hours

    def _check_entry_conditions(self):
        if self.position or self.order:
            return False
        
        dt = self._get_datetime()
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
        """Calculate position size with JPY adjustment.
        
        From JPY_PNL_GUIDE.md:
        - Calculate normal position size
        - Divide bt_size by forex_jpy_rate (~150) for backtrader
        - Commission class will restore actual size for fees
        - P&L class will compensate with JPY_RATE_COMPENSATION
        """
        equity = self.broker.get_value()
        risk_amount = equity * self.p.risk_percent
        price_risk = abs(entry_price - stop_loss)
        if price_risk <= 0:
            return 0
        
        # For JPY pairs: 1 pip = 0.01, pip value per lot = $1000/rate ≈ $6.67
        # Simplified: use standard pip value calculation
        pip_risk = price_risk / self.p.pip_value
        pip_value_per_lot = 10.0  # Approximate for most pairs
        
        if pip_risk > 0:
            lots = risk_amount / (pip_risk * pip_value_per_lot)
            lots = max(0.01, round(lots, 2))
            lots = min(lots, 10.0)
            
            # Calculate real contracts
            real_contracts = int(lots * self.p.contract_size)
            
            # CRITICAL: Divide by forex_jpy_rate for JPY pairs (from JPY_PNL_GUIDE.md)
            bt_size = int(real_contracts / self.p.forex_jpy_rate)
            
            return bt_size
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
            self.trade_report_file.write(f"Entry Price: {entry_price:.3f}\n")
            self.trade_report_file.write(f"Stop Loss: {self.stop_level:.3f}\n")
            self.trade_report_file.write(f"Take Profit: {self.take_level:.3f}\n")
            self.trade_report_file.write(f"SL Pips: {sl_pips:.1f}\n")
            self.trade_report_file.write(f"ATR: {atr:.4f}\n")
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
            print(f">>> KOI BUY {dt:%Y-%m-%d %H:%M} price={entry_price:.3f} "
                  f"SL={self.stop_level:.3f} TP={self.take_level:.3f} CCI={cci_now:.0f} SL_pips={sl_pips:.1f}")
        
        self._record_trade_entry(dt, entry_price, bt_size, atr_now, cci_now, sl_pips)

    def next(self):
        self._portfolio_values.append(self.broker.get_value())
        
        dt = self._get_datetime()
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
        """Order notification with OCA for SL/TP."""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status == order.Completed:
            if order == self.order:  # Entry order
                self.last_entry_price = order.executed.price
                self.last_entry_bar = len(self)
                
                if self.p.print_signals:
                    print(f"[OK] LONG BUY EXECUTED at {order.executed.price:.3f} size={order.executed.size}")

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
                    print(f"[EXIT] at {order.executed.price:.3f} reason={exit_reason}")

                # Reset state
                self.stop_order = None
                self.limit_order = None
                self.order = None
                self.stop_level = None
                self.take_level = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            is_expected_cancel = (self.stop_order and self.limit_order)
            if not is_expected_cancel and self.p.print_signals:
                print(f"Order {order.getstatusname()}: {order.ref}")
            
            if self.order and order.ref == self.order.ref: self.order = None
            if self.stop_order and order.ref == self.stop_order.ref: self.stop_order = None
            if self.limit_order and order.ref == self.limit_order.ref: self.limit_order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        
        dt = self._get_datetime()
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
        """Strategy end - print summary with advanced metrics."""
        final_value = self.broker.get_value()
        total_pnl = final_value - STARTING_CASH
        win_rate = (self.wins / self.trades * 100) if self.trades > 0 else 0
        profit_factor = (self.gross_profit / self.gross_loss) if self.gross_loss > 0 else float('inf')
        
        # Max Drawdown
        max_drawdown_pct = 0.0
        if self._portfolio_values:
            values = np.array(self._portfolio_values)
            peak = np.maximum.accumulate(values)
            dd = (peak - values) / peak * 100
            max_drawdown_pct = np.max(dd)
        
        # Daily returns for Sharpe
        daily_returns = []
        if self._trade_pnls:
            daily_pnl = defaultdict(float)
            for trade in self._trade_pnls:
                date_key = trade['date'].date()
                daily_pnl[date_key] += trade['pnl']
            
            equity = STARTING_CASH
            sorted_dates = sorted(daily_pnl.keys())
            for date in sorted_dates:
                pnl = daily_pnl[date]
                if equity > 0:
                    daily_ret = pnl / equity
                    daily_returns.append(daily_ret)
                    equity += pnl
        
        # Sharpe Ratio
        sharpe_ratio = 0.0
        if len(daily_returns) > 10:
            returns_array = np.array(daily_returns)
            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array)
            if std_return > 0:
                sharpe_ratio = (mean_return / std_return) * np.sqrt(252)
        
        # Print Summary
        print("\n" + "=" * 70)
        print("=== KOI STRATEGY SUMMARY (USDJPY) ===")
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
        
        # Risk Metrics
        print(f"\n{'='*70}")
        print("RISK METRICS")
        print(f"{'='*70}")
        
        sharpe_status = "Poor" if sharpe_ratio < 0.5 else "Marginal" if sharpe_ratio < 1.0 else "Good" if sharpe_ratio < 2.0 else "Excellent"
        print(f"Sharpe Ratio: {sharpe_ratio:>8.2f}  [{sharpe_status}]")
        
        dd_status = "Excellent" if max_drawdown_pct < 10 else "Acceptable" if max_drawdown_pct < 20 else "High"
        print(f"Max Drawdown: {max_drawdown_pct:>7.2f}%  [{dd_status}]")
        
        # Yearly Statistics
        yearly_stats = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0.0, 'gross_profit': 0.0, 'gross_loss': 0.0})
        
        for trade in self._trade_pnls:
            year = trade['year']
            yearly_stats[year]['trades'] += 1
            yearly_stats[year]['pnl'] += trade['pnl']
            if trade['is_winner']:
                yearly_stats[year]['wins'] += 1
                yearly_stats[year]['gross_profit'] += trade['pnl']
            else:
                yearly_stats[year]['gross_loss'] += abs(trade['pnl'])
        
        print(f"\n{'='*70}")
        print("YEARLY STATISTICS")
        print(f"{'='*70}")
        print(f"{'Year':<6} {'Trades':>7} {'WR%':>7} {'PF':>7} {'PnL':>12}")
        print(f"{'-'*70}")
        
        for year in sorted(yearly_stats.keys()):
            stats = yearly_stats[year]
            wr = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            year_pf = (stats['gross_profit'] / stats['gross_loss']) if stats['gross_loss'] > 0 else float('inf')
            print(f"{year:<6} {stats['trades']:>7} {wr:>6.1f}% {year_pf:>7.2f} ${stats['pnl']:>10,.0f}")
        
        print(f"{'='*70}")
        
        # Close trade reporting
        if self.trade_report_file:
            self.trade_report_file.close()
            print(f"\nTrade report saved.")


# =============================================================================
# MAIN
# =============================================================================
if __name__ == '__main__':
    cerebro = bt.Cerebro(stdstats=False)
    
    # Data - Use custom ForexCSVData
    data_path = Path(__file__).parent.parent.parent / 'data' / DATA_FILENAME
    if not data_path.exists():
        data_path = Path(__file__).parent / DATA_FILENAME
    
    data = ForexCSVData(
        dataname=str(data_path),
        fromdate=datetime.strptime(FROMDATE, '%Y-%m-%d'),
        todate=datetime.strptime(TODATE, '%Y-%m-%d'),
    )
    cerebro.adddata(data)
    
    # Broker with JPY commission
    cerebro.broker.setcash(STARTING_CASH)
    if USE_FIXED_COMMISSION:
        cerebro.broker.addcommissioninfo(
            ForexCommission(
                commission=COMMISSION_PER_LOT_PER_ORDER,
                is_jpy_pair=True,
                jpy_rate=FOREX_JPY_RATE
            )
        )
    
    cerebro.addstrategy(KOIStrategy)
    
    # Add observers
    try:
        cerebro.addobserver(bt.observers.BuySell, barplot=False)
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
    print(f"JPY Rate: {FOREX_JPY_RATE} (position/P&L adjustment)")
    print(f"{'='*70}\n")
    
    results = cerebro.run()
    final_value = cerebro.broker.getvalue()
    
    # Plot
    if ENABLE_PLOT:
        try:
            strategy_result = results[0]
            final_pnl = final_value - STARTING_CASH
            plot_title = f'KOI Strategy ({FOREX_INSTRUMENT} - LONG-ONLY)\n'
            plot_title += f'Final Value: ${final_value:,.0f} | P&L: ${final_pnl:+,.0f} | '
            plot_title += f'Trades: {strategy_result.trades}'
            
            print(f"[CHART] Showing {FOREX_INSTRUMENT} strategy chart...")
            cerebro.plot(style='candlestick', subtitle=plot_title)
        except Exception as e:
            print(f"Plot error: {e}")
