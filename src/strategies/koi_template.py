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

FILTERS (OPTIMIZED):
- SL Range: 10-15 pips (filters out low/high volatility entries)

PERFORMANCE (2020-2025, 5 years):
- Trades: 168
- Win Rate: 43.5%
- Profit Factor: 1.77
- Max Drawdown: 8.1%
- Net P&L: +$31,508 (+31.5%)

YEARLY BREAKDOWN:
- 2020: -$4,197 (30 trades)
- 2021: +$4,780 (42 trades)
- 2022: +$13,281 (34 trades)
- 2023: +$3,772 (30 trades)
- 2024: +$8,474 (19 trades)
- 2025: +$5,394 (13 trades, partial year)

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
TODATE = '2025-07-01'
STARTING_CASH = 100000.0
ENABLE_PLOT = False

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
MIN_SL_PIPS = 10.0

# Max SL Filter (NEW)
USE_MAX_SL_FILTER = True
MAX_SL_PIPS = 15.0

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
        final_value = self.broker.get_value()
        total_pnl = final_value - STARTING_CASH
        win_rate = (self.wins / self.trades * 100) if self.trades > 0 else 0
        profit_factor = (self.gross_profit / self.gross_loss) if self.gross_loss > 0 else float('inf')
        
        # Max DD
        if self._portfolio_values:
            values = np.array(self._portfolio_values)
            peak = np.maximum.accumulate(values)
            dd = (peak - values) / peak * 100
            max_dd = np.max(dd)
        else:
            max_dd = 0
        
        print("\n" + "=" * 70)
        print("=== KOI STRATEGY SUMMARY ===")
        print("=" * 70)
        print(f"Total Trades: {self.trades}")
        print(f"Wins: {self.wins} | Losses: {self.losses}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Profit Factor: {profit_factor:.2f}")
        print(f"Max Drawdown: {max_dd:.1f}%")
        print(f"Net P&L: ${total_pnl:,.0f}")
        print(f"Final Value: ${final_value:,.0f}")
        
        # Yearly stats
        yearly = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0.0})
        for t in self._trade_pnls:
            y = t['year']
            yearly[y]['trades'] += 1
            yearly[y]['pnl'] += t['pnl']
            if t['is_winner']:
                yearly[y]['wins'] += 1
        
        print("\n" + "=" * 70)
        print("YEARLY STATISTICS")
        print("=" * 70)
        for year in sorted(yearly.keys()):
            y = yearly[year]
            wr = (y['wins'] / y['trades'] * 100) if y['trades'] > 0 else 0
            print(f"{year}: {y['trades']:3d} trades | WR={wr:.1f}% | PnL=${y['pnl']:,.0f}")
        
        if self.trade_report_file:
            self.trade_report_file.close()
            print(f"\nTrade report saved.")


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
    
    # Run
    print(f"Starting Portfolio: ${STARTING_CASH:,.0f}")
    cerebro.run()
    
    if ENABLE_PLOT:
        cerebro.plot(style='candlestick')
