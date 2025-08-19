"""Simplified Sunrise Strategy
=================================

Clean, minimal Backtrader port of the Pine Script logic you supplied.  The goal
here is clarity and easy mapping to the TradingView code – NOT feature
explosion.  Only the essential ideas remain:

ENTRY (long only)
-----------------
1. Confirmation EMA crosses ABOVE ANY of fast / medium / slow (first bullish momentum sign).
2. Previous candle bullish (close[1] > open[1]).
3. Optional ordering filter (confirmation EMA above all other EMAs).
4. Optional price filter (close > filter EMA).
5. Optional angle filter (arctangent of EMA slope * scale > min_angle).
6. Optional SECURITY WINDOW: forbid a *new* entry for N bars AFTER THE LAST EXIT (matches Pine: ventana de seguridad tras la última salida; NOT after the last entry).
7. Optional entry price filter: during next `entry_price_filter_window` bars after an entry require close > last_entry_price.

EXIT
----
1. Initial ATR based stop & take profit (anchored to ENTRY BAR low/high like the Pine script):
         stop  = entry_bar_low  - ATR * atr_sl_multiplier
         take  = entry_bar_high + ATR * atr_tp_multiplier
2. Trailing stop (if enabled): On EACH bullish candle only, propose
         candidate = low - ATR * atr_sl_multiplier
     If candidate > current stop_level (only move upwards) => replace stop.
3. Optional bar-count exit (close after N bars in position).
4. Optional EMA crossover exit (exit EMA crossing above confirm EMA).
5. Optional close-on-new-entry: if a *fresh* entry signal appears while in a
     trade, we close the current position; a new trade may start NEXT bar.

IMPLEMENTATION NOTES
--------------------
* Manual independent stop & limit orders (no bracket) so that replacing the
    stop does NOT auto-cancel the TP (Backtrader bracket would do that).
* No re-entry / ROLL logic – explicitly removed per request (the original simplified
    version accidentally mixed entry-based cooldown semantics, now corrected to exit-based).
    "NEW_ENTRY" here simply means we closed because a fresh signal appeared while holding.
* Minimal state: only what's strictly needed for the logic.
* Extensive inline comments explaining every critical step.

CONFIGURATION
-------------
Parameters live in the Strategy (so you can still pass overrides when adding
the strategy).  The __main__ block below uses SIMPLE FLAGS (no argparse) so
you said: "don't add CLI options, only flags" – just edit constants there.

DISCLAIMER
----------
Educational example ONLY. Not investment advice. Markets involve risk; past
performance does not guarantee future results. Validate logic & data quality
before using in any live or simulated trading environment.
"""
from __future__ import annotations
import math
from pathlib import Path
import backtrader as bt


class SunriseSimple(bt.Strategy):
    params = dict(
        # Indicator lengths (from Pine Script code - EXACT VALUES)
        ema_fast_length=14,
        ema_medium_length=18,
        ema_slow_length=24,
        ema_confirm_length=1,
        ema_filter_price_length=100,
        ema_exit_length=25,
        # ATR / targets (from Pine Script code - EXACT VALUES)
        atr_length=20,
        atr_sl_multiplier=2.5,
        atr_tp_multiplier=12.0,
        atr_trailing_multiplier=2.5,
        # Filters / angles (from Pine Script code - EXACT VALUES)
        use_ema_order_condition=True,
        use_price_filter_ema=True,
        use_angle_filter=True,
        min_angle=65.0,  # RESTORE ORIGINAL PINE SCRIPT VALUE
        angle_scale_factor=10000.0,
        # Security window after exit (Pine Script logic: ventana_seguridad - EXACT VALUE)
        use_security_window=True,
        security_window_bars=17,  # RESTORE ORIGINAL PINE SCRIPT VALUE
        # Limited price filter (Pine Script logic: filtro_precio_entrada - EXACT VALUE)
        use_limited_price_filter=False,  # DISABLE AS IN ORIGINAL PINE SCRIPT
        entry_price_filter_window=60,
        # Exits (from Pine Script code - EXACT VALUES FROM PDF)
        use_bar_count_exit=False,  # CORRECTED: Unchecked in original Pine Script settings
        bar_count_exit=8,
        use_ema_crossover_exit=False,  # CORRECTED: Also unchecked in original
        # Trailing
        use_trailing_stop=True,
        close_on_new_entry=True,
        # Sizing / logging
        size=1,
        enable_risk_sizing=True,
        risk_percent=0.01,
        contract_size=100000,
        print_signals=True,
        # Plotting
        plot_result=True,
        buy_sell_plotdist=0.0005,
        plot_sltp_lines=True,
        pip_value=0.0001,
    )

    @staticmethod
    def _cross_above(a, b):
        """Return True if `a` crossed above `b` on the current bar.
        
        Pine Script ta.crossover() equivalent:
        - Current bar: a[0] > b[0] 
        - Previous bar: a[-1] <= b[-1]
        - Must be EXACT crossover (not just above)
        """
        try:
            current_a = float(a[0])
            current_b = float(b[0])
            previous_a = float(a[-1])
            previous_b = float(b[-1])
            
            # Pine Script crossover logic: current > AND previous <=
            crossover = (current_a > current_b) and (previous_a <= previous_b)
            
            if crossover:
                print(f"DEBUG CROSSOVER: {current_a:.6f} > {current_b:.6f} (prev: {previous_a:.6f} <= {previous_b:.6f})")
            
            return crossover
        except (IndexError, ValueError, TypeError):
            return False

    def _angle(self):
        """Compute instantaneous angle (degrees) of the confirm EMA slope.

        Equivalent to Pine's math.atan(rise/run) * 180 / pi with run=1.
        The rise gets magnified by `angle_scale_factor` for sensitivity.
        """
        try:
            current_ema = float(self.ema_confirm[0])
            previous_ema = float(self.ema_confirm[-1])
            
            # Pine Script: math.atan((ema_confirm - ema_confirm[1]) * factor_escala_angulo) * 180 / math.pi
            rise = (current_ema - previous_ema) * self.p.angle_scale_factor
            angle_radians = math.atan(rise)  # run = 1 (1 bar)
            angle_degrees = math.degrees(angle_radians)
            
            # Debug angle calculation occasionally
            if len(self) % 100 == 0:  # Every 100 bars
                print(f"DEBUG ANGLE: rise={rise:.8f} angle={angle_degrees:.2f}° (threshold={self.p.min_angle}°)")
            
            return angle_degrees
        except (IndexError, ValueError, TypeError, ZeroDivisionError):
            return float('nan')

    def __init__(self):
            d = self.data
            # Indicators
            self.ema_fast = bt.ind.EMA(d.close, period=self.p.ema_fast_length)
            self.ema_medium = bt.ind.EMA(d.close, period=self.p.ema_medium_length)
            self.ema_slow = bt.ind.EMA(d.close, period=self.p.ema_slow_length)
            self.ema_confirm = bt.ind.EMA(d.close, period=self.p.ema_confirm_length)
            self.ema_filter_price = bt.ind.EMA(d.close, period=self.p.ema_filter_price_length)
            self.ema_exit = bt.ind.EMA(d.close, period=self.p.ema_exit_length)
            self.atr = bt.ind.ATR(d, period=self.p.atr_length)

            # MANUAL ORDER MANAGEMENT - Replace buy_bracket with simple orders
            self.order = None  # Track current pending order
            self.stop_order = None  # Track stop loss order
            self.limit_order = None  # Track take profit order
            
            # Current protective price levels (float) for plotting / decisions
            self.stop_level = None
            self.take_level = None
            # Book-keeping for filters
            self.last_entry_bar = None
            self.last_exit_bar = None
            self.last_entry_price = None
            # Track initial stop level to distinguish STOP vs TRAIL_STOP on execution
            self.initial_stop_level = None
            
            # PINE SCRIPT EQUIVALENT: Track trade history for ta.barssince() logic
            self.trade_exit_bars = []  # Store bars where trades closed (ta.barssince equivalent)
            
            # PINE SCRIPT BEHAVIOR: Prevent entry and exit on same bar
            self.exit_this_bar = False  # Flag to prevent entry on exit bar
            self.last_exit_bar_current = None  # Track if we exited this specific bar
            
            # CROSSOVER NOISE FILTER: Prevent multiple signals in short timeframes
            self.last_crossover_bar = None  # Track last crossover to filter noise
            self.min_bars_between_signals = 3  # Minimum bars between crossover signals #3

            # Basic stats
            self.trades = 0
            self.wins = 0
            self.losses = 0
            self.gross_profit = 0.0
            self.gross_loss = 0.0

    def next(self):
        # RESET exit flag at start of each new bar (Pine Script behavior)
        self.exit_this_bar = False
        
        # CANCEL ALL PENDING ORDERS when we have no position (cleanup phantom orders)
        if not self.position:
            orders_canceled = 0
            if self.order:
                try:
                    self.cancel(self.order)
                    orders_canceled += 1
                except:
                    pass
                self.order = None
                    
            if self.stop_order:
                try:
                    self.cancel(self.stop_order)
                    orders_canceled += 1
                except:
                    pass
                self.stop_order = None
                    
            if self.limit_order:
                try:
                    self.cancel(self.limit_order)
                    orders_canceled += 1
                except:
                    pass
                self.limit_order = None
                    
            if orders_canceled > 0 and self.p.print_signals:
                print(f"CLEANUP: Canceled {orders_canceled} phantom orders")

        # Check if we have pending orders first
        if self.order or self.stop_order or self.limit_order:
            return  # Wait for orders to complete before doing anything else

        dt = bt.num2date(self.data.datetime[0])

        # POSITION MANAGEMENT
        if self.position:
            # PINE SCRIPT TRAILING STOP LOGIC - Update on EVERY bar when in position
            # Pine Script: if usar_trailing_stop and strategy.position_size > 0
            #              if close > open  // Solo en velas alcistas
            #                  new_stop_level = low - (atr_value * atr_multiplier_sl)
            #                  stop_level := math.max(stop_level, new_stop_level)
            if self.p.use_trailing_stop:
                current_close = float(self.data.close[0])
                current_open = float(self.data.open[0])
                current_low = float(self.data.low[0])
                
                # Pine Script: Solo actualizar trailing en velas alcistas (close > open)
                if current_close > current_open:
                    atr_now = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
                    if atr_now > 0:
                        # Pine Script: new_stop_level = low - (atr_value * atr_multiplier_sl)
                        new_stop_level = current_low - (atr_now * self.p.atr_sl_multiplier)
                        
                        # Pine Script: stop_level := math.max(stop_level, new_stop_level)
                        if self.stop_level is None:
                            self.stop_level = new_stop_level
                        elif new_stop_level > self.stop_level:
                            old_stop = self.stop_level
                            self.stop_level = new_stop_level
                            if self.p.print_signals:
                                print(f"TRAIL {dt:%Y-%m-%d %H:%M} {old_stop:.5f} -> {new_stop_level:.5f}")
            
            # Check exit conditions
            bars_since_entry = len(self) - self.last_entry_bar if self.last_entry_bar is not None else 0
            
            # Timed exit (Pine Script logic: barsSinceEntry >= barras_salida)
            if self.p.use_bar_count_exit and bars_since_entry >= self.p.bar_count_exit and not self.exit_this_bar:
                print(f"BAR_EXIT at {dt:%Y-%m-%d %H:%M} after {bars_since_entry} bars")
                self.order = self.close()
                self.exit_this_bar = True  # Mark exit action taken
                return

            # EMA crossover exit
            if self.p.use_ema_crossover_exit and self._cross_above(self.ema_exit, self.ema_confirm) and not self.exit_this_bar:
                print(f"EMA_EXIT at {dt:%Y-%m-%d %H:%M}")
                self.order = self.close()
                self.exit_this_bar = True  # Mark exit action taken
                return

            # Close-on-new-entry
            if self.p.close_on_new_entry and self._temp_new_entry_signal() and not self.exit_this_bar:
                print(f"NEW_ENTRY_EXIT at {dt:%Y-%m-%d %H:%M}")
                self.order = self.close()
                self.exit_this_bar = True  # Mark exit action taken
                return

            # Continue holding - no new entry logic when in position
            return

        # ENTRY LOGIC (only when no position and no pending orders)
        
        # Pine Script prevention: No entry if exit was taken on same bar
        if self.exit_this_bar:
            if self.p.print_signals:
                print(f"SKIP entry: exit action already taken this bar")
            return
        
        # Security window check (Pine Script ta.barssince equivalent)
        # Pine Script: ta.barssince(strategy.closedtrades.exit_time changed)
        if self.p.use_security_window and self.trade_exit_bars:
            bars_since_last_exit = len(self) - self.trade_exit_bars[-1]
            if bars_since_last_exit < int(self.p.security_window_bars):
                if self.p.print_signals:
                    print(f"SKIP entry: security window {bars_since_last_exit}/{self.p.security_window_bars} bars since last exit")
                return

        # Entry signal evaluation
        if not self._full_entry_signal():
            return

        print(f"DEBUG: ATTEMPTING ENTRY at {dt:%Y-%m-%d %H:%M} position={self.position.size if self.position else 0}")

        # Calculate position size and create buy order
        atr_now = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
        if atr_now <= 0:
            return

        entry_price = float(self.data.close[0])
        bar_low = float(self.data.low[0])
        bar_high = float(self.data.high[0])
        self.stop_level = bar_low - atr_now * self.p.atr_sl_multiplier
        self.take_level = bar_high + atr_now * self.p.atr_tp_multiplier
        self.initial_stop_level = self.stop_level

        # Position sizing (Pine Script equivalent calculation)
        if self.p.enable_risk_sizing:
            raw_risk = entry_price - self.stop_level
            if raw_risk <= 0:
                print(f"DEBUG SIZE: Invalid risk {raw_risk:.5f}, skipping entry")
                return
            equity = self.broker.get_value()
            risk_val = equity * self.p.risk_percent
            risk_per_contract = raw_risk * self.p.contract_size
            if risk_per_contract <= 0:
                print(f"DEBUG SIZE: Invalid risk_per_contract {risk_per_contract:.2f}, skipping entry") 
                return
            contracts = max(int(risk_val / risk_per_contract), 1)
            
            print(f"DEBUG SIZE: equity={equity:.2f} risk_val={risk_val:.2f} raw_risk={raw_risk:.5f} contracts={contracts}")
        else:
            contracts = int(self.p.size)
            print(f"DEBUG SIZE: Fixed sizing contracts={contracts}")
        
        if contracts <= 0:
            return
            
        bt_size = contracts * self.p.contract_size

        if self.p.print_signals:
            rr = (self.take_level - entry_price) / (entry_price - self.stop_level) if (entry_price - self.stop_level) > 0 else float('nan')
            print(f"ENTRY {dt:%Y-%m-%d %H:%M} price={entry_price:.5f} size={bt_size} SL={self.stop_level:.5f} TP={self.take_level:.5f} RR={rr:.2f}")
        
        # MANUAL ORDER MANAGEMENT: Replace buy_bracket with simple buy + manual stop/limit
        print(f"DEBUG ORDER PLACEMENT: Creating manual orders size={bt_size} stop={self.stop_level:.5f} limit={self.take_level:.5f}")
        
        # 1. Place market buy order
        self.order = self.buy(size=bt_size)
        
        self.last_entry_price = entry_price
        self.last_entry_bar = len(self)

    def _full_entry_signal(self):
        """Return True if ALL *full* entry constraints pass.

        Mirrors the Pine Script required + optional filters.
        """
        dt = bt.num2date(self.data.datetime[0])
        
        # 1. Previous candle bullish check
        try:
            prev_bull = self.data.close[-1] > self.data.open[-1]
        except IndexError:
            return False

        # 2. EMA crossover check (ANY of the three) - WITH NOISE FILTER
        cross_fast = self._cross_above(self.ema_confirm, self.ema_fast)
        cross_medium = self._cross_above(self.ema_confirm, self.ema_medium) 
        cross_slow = self._cross_above(self.ema_confirm, self.ema_slow)
        cross_any = cross_fast or cross_medium or cross_slow
        
        # CROSSOVER NOISE FILTER: Prevent multiple signals in short timeframes
        current_bar = len(self)
        if cross_any:
            if self.last_crossover_bar is not None:
                bars_since_last_cross = current_bar - self.last_crossover_bar
                if bars_since_last_cross < self.min_bars_between_signals:
                    if self.p.print_signals:
                        print(f"SKIP entry: crossover noise filter {bars_since_last_cross}/{self.min_bars_between_signals} bars")
                    return False
            
            # Record this crossover
            self.last_crossover_bar = current_bar
            
            cross_type = []
            if cross_fast: cross_type.append("FAST")
            if cross_medium: cross_type.append("MEDIUM") 
            if cross_slow: cross_type.append("SLOW")
            print(f"DEBUG ENTRY {dt:%Y-%m-%d %H:%M}: EMA crossover detected ({','.join(cross_type)})")
        
        if not (prev_bull and cross_any):
            if self.p.print_signals:
                print(f"SKIP entry: prev_bull={prev_bull} cross_any={cross_any}")
            return False

        # 3. EMA order condition
        if self.p.use_ema_order_condition:
            ema_order_ok = (
                self.ema_confirm[0] > self.ema_fast[0] and
                self.ema_confirm[0] > self.ema_medium[0] and
                self.ema_confirm[0] > self.ema_slow[0]
            )
            if not ema_order_ok:
                if self.p.print_signals:
                    print(f"SKIP entry: EMA order condition failed (confirm={self.ema_confirm[0]:.5f} vs fast={self.ema_fast[0]:.5f})")
                return False

        # 4. Price filter EMA
        if self.p.use_price_filter_ema:
            price_above_filter = self.data.close[0] > self.ema_filter_price[0]
            if not price_above_filter:
                if self.p.print_signals:
                    print(f"SKIP entry: price below filter EMA ({self.data.close[0]:.5f} <= {self.ema_filter_price[0]:.5f})")
                return False

        # 5. Angle filter
        if self.p.use_angle_filter:
            current_angle = self._angle()
            angle_ok = current_angle > self.p.min_angle
            if not angle_ok:
                if self.p.print_signals:
                    print(f"SKIP entry: angle below threshold ({current_angle:.2f}° <= {self.p.min_angle}°)")
                return False

        # All filters passed
        print(f"DEBUG ENTRY {dt:%Y-%m-%d %H:%M}: ALL FILTERS PASSED!")
        return True

    def _temp_new_entry_signal(self):
        """Light version of entry check used ONLY to decide close-on-new-entry.

        IMPORTANT: This intentionally *ignores* security window & entry price
        filter just like the Pine logic's temporary re-check.
        """
        try: 
            prev_bull = self.data.close[-1] > self.data.open[-1]
        except IndexError: 
            return False
        
        cross_any = (
            self._cross_above(self.ema_confirm, self.ema_fast) or 
            self._cross_above(self.ema_confirm, self.ema_medium) or 
            self._cross_above(self.ema_confirm, self.ema_slow)
        )
        if not (prev_bull and cross_any): 
            return False
            
        if self.p.use_ema_order_condition and not (
            self.ema_confirm[0] > self.ema_fast[0] and 
            self.ema_confirm[0] > self.ema_medium[0] and 
            self.ema_confirm[0] > self.ema_slow[0]
        ): 
            return False
            
        if self.p.use_price_filter_ema and not (self.data.close[0] > self.ema_filter_price[0]): 
            return False
            
        if self.p.use_angle_filter and not (self._angle() > self.p.min_angle): 
            return False
            
        return True

    def notify_order(self, order):
        """Enhanced order notification with manual stop/limit management"""
        dt = bt.num2date(self.data.datetime[0])
        
        if order.status in [order.Submitted, order.Accepted]:
            # Order submitted/accepted, nothing to do
            return

        if order.status == order.Completed:
            if order.isbuy():
                if self.p.print_signals:
                    print(f"BUY EXECUTED at {order.executed.price:.5f} size={order.executed.size}")
                self.last_entry_bar = len(self)
                
                # MANUAL STOP/LIMIT: Place protective orders after buy execution
                if self.stop_level and self.take_level:
                    try:
                        # Place stop loss order
                        self.stop_order = self.sell(
                            size=order.executed.size,
                            exectype=bt.Order.Stop,
                            price=self.stop_level
                        )
                        
                        # Place take profit order  
                        self.limit_order = self.sell(
                            size=order.executed.size,
                            exectype=bt.Order.Limit,
                            price=self.take_level
                        )
                        
                        if self.p.print_signals:
                            print(f"PROTECTIVE ORDERS: SL={self.stop_level:.5f} TP={self.take_level:.5f}")
                    except Exception as e:
                        print(f"ERROR placing protective orders: {e}")
                        
                # Clear main order reference
                if self.order == order:
                    self.order = None
                    
            else:  # SELL order
                if self.p.print_signals:
                    print(f"SELL EXECUTED at {order.executed.price:.5f} size={order.executed.size}")
                
                # Clean up order references
                if self.stop_order == order:
                    self.stop_order = None
                    # Cancel remaining limit order
                    if self.limit_order:
                        try:
                            self.cancel(self.limit_order)
                            self.limit_order = None
                        except:
                            pass
                elif self.limit_order == order:
                    self.limit_order = None
                    # Cancel remaining stop order
                    if self.stop_order:
                        try:
                            self.cancel(self.stop_order)
                            self.stop_order = None
                        except:
                            pass

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if self.p.print_signals:
                print(f"Order {order.getstatusname()}: {order.ref}")
                
            # Clean up order references
            if self.order == order:
                self.order = None
            elif self.stop_order == order:
                self.stop_order = None
            elif self.limit_order == order:
                self.limit_order = None

    def notify_trade(self, trade):
        """Standard Backtrader trade notification"""
        if not trade.isclosed:
            return

        dt = bt.num2date(self.data.datetime[0])
        self.trades += 1
        
        pnl = trade.pnlcomm
        if pnl > 0:
            self.wins += 1
            self.gross_profit += pnl
        else:
            self.losses += 1
            self.gross_loss += abs(pnl)

        # PINE SCRIPT EQUIVALENT: Record exit bar for ta.barssince() logic
        current_bar = len(self)
        self.trade_exit_bars.append(current_bar)
        
        # Mark that exit action occurred on this bar (Pine Script sequential processing)
        self.exit_this_bar = True
        
        # Keep only recent exit bars (last 100 to avoid memory bloat)
        if len(self.trade_exit_bars) > 100:
            self.trade_exit_bars = self.trade_exit_bars[-100:]

        # Mark last exit bar for legacy compatibility
        self.last_exit_bar = current_bar

        if self.p.print_signals:
            if self.p.pip_value:
                pips = (trade.price - trade.history[0].event.price) / self.p.pip_value if trade.history else 0
            else:
                pips = 0
            print(f"TRADE CLOSED {dt:%Y-%m-%d %H:%M} PnL={pnl:.2f} Pips={pips:.1f}")

        # Reset levels
        self.stop_level = None
        self.take_level = None

    def stop(self):
        wr = (self.wins / self.trades * 100.0) if self.trades else 0.0
        pf = (self.gross_profit / self.gross_loss) if self.gross_loss > 0 else float('inf')
        print("=== SUNRISE SIMPLE SUMMARY ===")
        print(f"Trades: {self.trades} Wins: {self.wins} Losses: {self.losses} WinRate: {wr:.2f}% PF: {pf:.2f}")


if __name__ == '__main__':
    # =============================================================
    # RUNTIME FLAGS (edit here – no CLI / argparse as requested)
    # =============================================================
    DATA_FILENAME = 'EURUSD_5m_5Yea.csv'  # CSV inside data/
    FROMDATE = '2025-07-21'               # Inclusive start date (YYYY-MM-DD)
    TODATE = '2025-08-17'                 # Inclusive end date
    STARTING_CASH = 100000.0
    QUICK_TEST = False                    # If True: auto-reduce to last 10 days
    LIMIT_BARS = 0                        # >0 = stop after N bars processed
    ENABLE_PLOT = True                    # Plot final result (if matplotlib available)

    from datetime import datetime, timedelta

    if QUICK_TEST:
        try:
            td_obj = datetime.strptime(TODATE, '%Y-%m-%d')
            FROMDATE = (td_obj - timedelta(days=10)).strftime('%Y-%m-%d')
        except Exception:
            pass

    class SLTPObserver(bt.Observer):
        lines = ('sl','tp',); plotinfo = dict(plot=True, subplot=False)
        plotlines = dict(sl=dict(color='red', ls='--'), tp=dict(color='green', ls='--'))
        def next(self):
            strat = self._owner
            if strat.position:
                self.lines.sl[0] = strat.stop_level if strat.stop_level else float('nan')
                self.lines.tp[0] = strat.take_level if strat.take_level else float('nan')
            else:
                self.lines.sl[0] = float('nan'); self.lines.tp[0] = float('nan')
    BASE = Path(__file__).resolve().parent.parent.parent
    DATA_FILE = BASE / 'data' / DATA_FILENAME
    STRAT_KWARGS = dict(plot_result=ENABLE_PLOT)

    def parse_date(s):
        if not s: return None
        try: return datetime.strptime(s, '%Y-%m-%d')
        except Exception: return None

    if not DATA_FILE.exists():
        print(f"Data file not found: {DATA_FILE}"); raise SystemExit(1)

    feed_kwargs = dict(dataname=str(DATA_FILE), dtformat='%Y%m%d', tmformat='%H:%M:%S',
                       datetime=0, time=1, open=2, high=3, low=4, close=5, volume=6,
                       timeframe=bt.TimeFrame.Minutes, compression=5)
    fd = parse_date(FROMDATE); td = parse_date(TODATE)
    if fd: feed_kwargs['fromdate'] = fd
    if td: feed_kwargs['todate'] = td
    data = bt.feeds.GenericCSVData(**feed_kwargs)

    cerebro = bt.Cerebro(stdstats=False)
    cerebro.adddata(data)
    cerebro.broker.setcash(STARTING_CASH)
    cerebro.broker.setcommission(leverage=30.0)
    cerebro.addstrategy(SunriseSimple, **STRAT_KWARGS)
    try: cerebro.addobserver(bt.observers.BuySell, barplot=False, plotdist=SunriseSimple.params.buy_sell_plotdist)
    except Exception: pass
    if SunriseSimple.params.plot_sltp_lines:
        try: cerebro.addobserver(SLTPObserver)
        except Exception: pass
    try: cerebro.addobserver(bt.observers.Value)
    except Exception: pass

    if LIMIT_BARS > 0:
        # Monkey-patch next() to stop early after LIMIT_BARS bars for quick experimentation.
        orig_next = SunriseSimple.next
        def limited_next(self):
            if len(self.data) >= LIMIT_BARS:
                self.env.runstop(); return
            orig_next(self)
        SunriseSimple.next = limited_next

    print(f"=== RUNNING SUNRISE SIMPLE === (from {FROMDATE} to {TODATE})")
    results = cerebro.run()
    print(f"Final Value: {cerebro.broker.getvalue():,.2f}")
    if results and getattr(results[0].p, 'plot_result', False) and ENABLE_PLOT:
        try: cerebro.plot(style='lines')
        except Exception as e: print(f"Plot error: {e}")
