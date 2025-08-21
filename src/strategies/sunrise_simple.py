"""Simplified Sunrise Strategy
=================================

Clean, minimal implementation of the Pine Script logic you supplied.  The goal
here is clarity and easy mapping to the TradingView code – NOT feature
explosion.  Only the essential ideas remain:

ENTRY (long only)
-----------------
1. Confirmation EMA crosses ABOVE ANY of fast / medium / slow (first bullish momentum sign).
2. Previous candle bullish (close[1] > open[1]).
3. Optional ordering filter (confirmation EMA above all other EMAs).
4. Optional price filter (close > filter EMA).
5. Optional angle filte        # Use stored exit reason from notify_order
        exit_reason = getattr(self, 'last_exit_reason', "UNKNOWN")
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
        ema_filter_price_length=50, #¡¡
        ema_exit_length=25, #??
        # ATR / targets 
        atr_length=14,
        atr_sl_multiplier=2.5,
        atr_tp_multiplier=12.0,
        atr_trailing_multiplier=2.5,
        # Filters / angles 
        use_ema_order_condition=False,
        use_price_filter_ema=True,
        use_angle_filter=True,
        min_angle=65.0,
        angle_scale_factor=10000.0,
        # Security window after exit
        use_security_window=False,
        security_window_bars=15,  
        # Limited price filter 
        use_limited_price_filter=False,
        entry_price_filter_window=30,  # Back to smaller window for comparison
        # Pullback entry system
        use_pullback_entry=True,  # Restore pullback mode
        pullback_max_candles=1,  # Balanced - original 3 red candles
        entry_window_periods=10,  # Balanced - original 5 periods
        entry_pip_offset=2.0,  # Balanced - original 1.0 pips
        # EXITS 
        use_bar_count_exit=False, #¡¡ # Test different exit methods
        bar_count_exit=10,  
        use_ema_crossover_exit=False, #??
        # Trailing
        use_trailing_stop=False, #?? 
        close_on_new_entry=False, #??
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
            self.stop_has_been_trailed = False  # Track if stop has moved up from initial level
            
            # PINE SCRIPT EQUIVALENT: Track trade history for ta.barssince() logic
            self.trade_exit_bars = []  # Store bars where trades closed (ta.barssince equivalent)
            
            # PINE SCRIPT BEHAVIOR: Prevent entry and exit on same bar
            self.exit_this_bar = False  # Flag to prevent entry on exit bar
            self.last_exit_bar_current = None  # Track if we exited this specific bar #3
            
            # PULLBACK ENTRY STATE MACHINE
            self.pullback_state = "NORMAL"  # States: NORMAL, WAITING_PULLBACK, WAITING_BREAKOUT
            self.pullback_red_count = 0  # Count of consecutive red candles
            self.first_red_high = None  # High of first red candle in pullback
            self.entry_window_start = None  # Bar when entry window opened
            self.breakout_target = None  # Price target for entry breakout

            # Basic stats
            self.trades = 0
            self.wins = 0
            self.losses = 0
            self.gross_profit = 0.0
            self.gross_loss = 0.0
            
            # Track exit reason for notify_trade
            self.last_exit_reason = "UNKNOWN"

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
            
            # Reset pullback state when no position (fresh start)
            if self.p.use_pullback_entry and orders_canceled > 0:
                self._reset_pullback_state()

        # Check if we have pending ENTRY orders (but allow protective orders)
        if self.order:
            return  # Wait for entry order to complete before doing anything else

        dt = bt.num2date(self.data.datetime[0])

        # POSITION MANAGEMENT
        if self.position:
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
                            self.stop_has_been_trailed = True  # Mark that stop has been trailed up
                            
                            # UPDATE THE ACTUAL STOP ORDER WITH NEW LEVEL
                            if self.stop_order:
                                try:
                                    self.cancel(self.stop_order)
                                    self.stop_order = self.sell(
                                        size=self.position.size,
                                        exectype=bt.Order.Stop,
                                        price=self.stop_level
                                    )
                                    if self.p.print_signals:
                                        print(f"TRAIL {dt:%Y-%m-%d %H:%M} {old_stop:.5f} -> {new_stop_level:.5f}")
                                except Exception as e:
                                    print(f"ERROR updating trailing stop: {e}")
            
            # Check exit conditions
            bars_since_entry = len(self) - self.last_entry_bar if self.last_entry_bar is not None else 0
            
            # Timed exit (Pine Script logic: barsSinceEntry >= barras_salida)
            if self.p.use_bar_count_exit and bars_since_entry >= self.p.bar_count_exit and not self.exit_this_bar:
                print(f"BAR_EXIT at {dt:%Y-%m-%d %H:%M} after {bars_since_entry} bars (target: {self.p.bar_count_exit})")
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
                return

        # Entry signal evaluation
        if not self._full_entry_signal():
            return

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
        self.stop_has_been_trailed = False  # Reset trailing flag for new trade

        # Position sizing (Pine Script equivalent calculation)
        if self.p.enable_risk_sizing:
            raw_risk = entry_price - self.stop_level
            if raw_risk <= 0:
                return
            equity = self.broker.get_value()
            risk_val = equity * self.p.risk_percent
            risk_per_contract = raw_risk * self.p.contract_size
            if risk_per_contract <= 0:
                return
            contracts = max(int(risk_val / risk_per_contract), 1)
        else:
            contracts = int(self.p.size)
        
        if contracts <= 0:
            return
            
        bt_size = contracts * self.p.contract_size

        if self.p.print_signals:
            rr = (self.take_level - entry_price) / (entry_price - self.stop_level) if (entry_price - self.stop_level) > 0 else float('nan')
            print(f"ENTRY {dt:%Y-%m-%d %H:%M} price={entry_price:.5f} size={bt_size} SL={self.stop_level:.5f} TP={self.take_level:.5f} RR={rr:.2f}")
        
        # MANUAL ORDER MANAGEMENT: Replace buy_bracket with simple buy + manual stop/limit
        
        # 1. Place market buy order
        self.order = self.buy(size=bt_size)
        
        self.last_entry_price = entry_price
        self.last_entry_bar = len(self)

    def _full_entry_signal(self):
        """Return True if ALL *full* entry constraints pass.

        Mirrors the Pine Script required + optional filters.
        Includes optional pullback entry logic.
        """
        dt = bt.num2date(self.data.datetime[0])
        
        # PULLBACK ENTRY SYSTEM STATE MACHINE
        if self.p.use_pullback_entry:
            return self._handle_pullback_entry(dt)
        
        # STANDARD ENTRY LOGIC (when pullback is disabled)
        return self._standard_entry_signal(dt)
    
    def _standard_entry_signal(self, dt):
        """Standard entry logic without pullback system"""
        # 1. Previous candle bullish check
        try:
            prev_bull = self.data.close[-1] > self.data.open[-1]
        except IndexError:
            return False

        # 2. EMA crossover check (ANY of the three)
        cross_fast = self._cross_above(self.ema_confirm, self.ema_fast)
        cross_medium = self._cross_above(self.ema_confirm, self.ema_medium) 
        cross_slow = self._cross_above(self.ema_confirm, self.ema_slow)
        cross_any = cross_fast or cross_medium or cross_slow
        
        if cross_any:
            cross_type = []
            if cross_fast: cross_type.append("FAST")
            if cross_medium: cross_type.append("MEDIUM") 
            if cross_slow: cross_type.append("SLOW")
        
        if not (prev_bull and cross_any):
            return False

        # 3. EMA order condition
        if self.p.use_ema_order_condition:
            ema_order_ok = (
                self.ema_confirm[0] > self.ema_fast[0] and
                self.ema_confirm[0] > self.ema_medium[0] and
                self.ema_confirm[0] > self.ema_slow[0]
            )
            if not ema_order_ok:
                return False

        # 4. Price filter EMA
        if self.p.use_price_filter_ema:
            price_above_filter = self.data.close[0] > self.ema_filter_price[0]
            if not price_above_filter:
                return False

        # 5. Angle filter
        if self.p.use_angle_filter:
            current_angle = self._angle()
            angle_ok = current_angle > self.p.min_angle
            if not angle_ok:
                return False

        # 6. Limited price filter
        if self.p.use_limited_price_filter:
            if self.p.print_signals:
                print(f"DEBUG LIMITED_PRICE_FILTER: enabled={self.p.use_limited_price_filter}, last_entry_bar={self.last_entry_bar}")
            
            if self.last_entry_bar is not None:
                bars_since_last_entry = len(self) - self.last_entry_bar
                if self.p.print_signals:
                    print(f"DEBUG LIMITED_PRICE_FILTER: bars_since_last_entry={bars_since_last_entry}, window={self.p.entry_price_filter_window}")
                
                if bars_since_last_entry < self.p.entry_price_filter_window:
                    # Within filter window - require close > last entry price
                    if self.last_entry_price is not None:
                        price_above_last_entry = self.data.close[0] > self.last_entry_price
                        if self.p.print_signals:
                            print(f"DEBUG PRICE_FILTER: close={self.data.close[0]:.5f} vs last_entry={self.last_entry_price:.5f}, above={price_above_last_entry}")
                        
                        if not price_above_last_entry:
                            if self.p.print_signals:
                                print(f"SKIP entry: price filter - close {self.data.close[0]:.5f} <= last_entry {self.last_entry_price:.5f} (bars since: {bars_since_last_entry})")
                            return False
                    else:
                        if self.p.print_signals:
                            print(f"DEBUG LIMITED_PRICE_FILTER: last_entry_price is None")
                else:
                    if self.p.print_signals:
                        print(f"DEBUG LIMITED_PRICE_FILTER: Outside window - {bars_since_last_entry} >= {self.p.entry_price_filter_window}")
            else:
                if self.p.print_signals:
                    print(f"DEBUG LIMITED_PRICE_FILTER: No previous entry (last_entry_bar is None)")
        else:
            if self.p.print_signals:
                print(f"DEBUG LIMITED_PRICE_FILTER: DISABLED")

        # All filters passed
        return True
    
    def _handle_pullback_entry(self, dt):
        """Pullback entry state machine logic"""
        current_bar = len(self)
        current_close = float(self.data.close[0])
        current_open = float(self.data.open[0])
        current_high = float(self.data.high[0])
        
        # Check if current candle is red (bearish)
        is_red_candle = current_close < current_open
        
        # STATE MACHINE LOGIC
        if self.pullback_state == "NORMAL":
            # Check for initial entry conditions (1 & 2)
            if self._basic_entry_conditions():
                self.pullback_state = "WAITING_PULLBACK"
                self.pullback_red_count = 0
                self.first_red_high = None
                return False  # Don't enter yet, wait for pullback
            return False
            
        elif self.pullback_state == "WAITING_PULLBACK":
            if is_red_candle:
                self.pullback_red_count += 1
                
                # Store high of first red candle
                if self.pullback_red_count == 1:
                    self.first_red_high = current_high
                
                # Check if we exceeded max red candles
                if self.pullback_red_count > self.p.pullback_max_candles:
                    self._reset_pullback_state()
                    return False
                    
            else:  # Green candle - pullback ended
                if self.pullback_red_count > 0:
                    # Pullback phase complete, start entry window
                    self.pullback_state = "WAITING_BREAKOUT"
                    self.entry_window_start = current_bar
                    self.breakout_target = self.first_red_high + (self.p.entry_pip_offset * self.p.pip_value)
                else:
                    # No pullback occurred, reset
                    self._reset_pullback_state()
            return False
            
        elif self.pullback_state == "WAITING_BREAKOUT":
            # Check if entry window expired
            bars_in_window = current_bar - self.entry_window_start
            if bars_in_window >= self.p.entry_window_periods:
                self._reset_pullback_state()
                return False
            
            # Check for breakout above target
            if current_high >= self.breakout_target:
                # Breakout detected! Check all other entry conditions
                if self._validate_all_entry_filters():
                    if self.p.print_signals:
                        print(f"BREAKOUT ENTRY! High={current_high:.5f} >= target={self.breakout_target:.5f}")
                    self._reset_pullback_state()  # Reset for next setup
                    return True
            return False
        
        return False
    
    def _basic_entry_conditions(self):
        """Check basic entry conditions 1 & 2 for pullback system"""
        # 1. Previous candle bullish check
        try:
            prev_bull = self.data.close[-1] > self.data.open[-1]
        except IndexError:
            return False

        # 2. EMA crossover check (ANY of the three)
        cross_fast = self._cross_above(self.ema_confirm, self.ema_fast)
        cross_medium = self._cross_above(self.ema_confirm, self.ema_medium) 
        cross_slow = self._cross_above(self.ema_confirm, self.ema_slow)
        cross_any = cross_fast or cross_medium or cross_slow
        
        return prev_bull and cross_any
    
    def _validate_all_entry_filters(self):
        """Validate all entry filters (3-6) for pullback entry"""
        # 3. EMA order condition
        if self.p.use_ema_order_condition:
            ema_order_ok = (
                self.ema_confirm[0] > self.ema_fast[0] and
                self.ema_confirm[0] > self.ema_medium[0] and
                self.ema_confirm[0] > self.ema_slow[0]
            )
            if not ema_order_ok:
                return False

        # 4. Price filter EMA
        if self.p.use_price_filter_ema:
            price_above_filter = self.data.close[0] > self.ema_filter_price[0]
            if not price_above_filter:
                return False

        # 5. Angle filter
        if self.p.use_angle_filter:
            current_angle = self._angle()
            angle_ok = current_angle > self.p.min_angle
            if not angle_ok:
                return False

        # 6. Limited price filter (simplified for pullback)
        if self.p.use_limited_price_filter:
            if self.last_entry_bar is not None:
                bars_since_last_entry = len(self) - self.last_entry_bar
                if bars_since_last_entry < self.p.entry_price_filter_window:
                    if self.last_entry_price is not None:
                        price_above_last_entry = self.data.close[0] > self.last_entry_price
                        if not price_above_last_entry:
                            return False

        return True
    
    def _reset_pullback_state(self):
        """Reset pullback state machine to initial state"""
        self.pullback_state = "NORMAL"
        self.pullback_red_count = 0
        self.first_red_high = None
        self.entry_window_start = None
        self.breakout_target = None

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
        """Enhanced order notification with detailed exit reporting and PnL calculation"""
        dt = bt.num2date(self.data.datetime[0])
        
        if order.status in [order.Submitted, order.Accepted]:
            # Order submitted/accepted, nothing to do
            return

        if order.status == order.Completed:
            if order.isbuy():
                self.last_entry_price = order.executed.price
                self.last_entry_bar = len(self)
                if self.p.print_signals:
                    print(f"BUY EXECUTED at {order.executed.price:.5f} size={order.executed.size}")
                
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
                    
            else:  # SELL order - Just report execution, let notify_trade handle PnL
                exit_price = order.executed.price
                
                # Debug: Identify which order triggered the exit and determine reason
                order_type = "UNKNOWN"
                exit_reason = "UNKNOWN"
                if self.stop_order == order:
                    order_type = "STOP_ORDER"
                    # Distinguish between initial STOP_LOSS and TRAILING_STOP
                    if self.stop_has_been_trailed:
                        exit_reason = "TRAILING_STOP"
                    else:
                        exit_reason = "STOP_LOSS"
                elif self.limit_order == order:
                    order_type = "LIMIT_ORDER"
                    exit_reason = "TAKE_PROFIT"
                elif self.order == order:
                    order_type = "MANUAL_ORDER"
                    exit_reason = "MANUAL_CLOSE"
                
                # Store exit reason for notify_trade
                self.last_exit_reason = exit_reason
                
                if self.p.print_signals:
                    sl_text = f"{self.stop_level:.5f}" if self.stop_level else "None"
                    tp_text = f"{self.take_level:.5f}" if self.take_level else "None"
                    print(f"SELL EXECUTED at {exit_price:.5f} size={order.executed.size} type={order_type}")
                    print(f"  Exit reason stored: {exit_reason}")
                    print(f"  Current levels: SL={sl_text} TP={tp_text}")
                
                # Clean up order references
                if self.stop_order == order:
                    self.stop_order = None
                    # Cancel remaining limit order
                    if self.limit_order:
                        try:
                            self.cancel(self.limit_order)
                        except:
                            pass
                        self.limit_order = None
                        
                elif self.limit_order == order:
                    self.limit_order = None
                    # Cancel remaining stop order
                    if self.stop_order:
                        try:
                            self.cancel(self.stop_order)
                        except:
                            pass
                        self.stop_order = None
                        
                elif self.order == order:
                    self.order = None
                    # Cancel all protective orders on manual close
                    if self.stop_order:
                        try:
                            self.cancel(self.stop_order)
                        except:
                            pass
                        self.stop_order = None
                    if self.limit_order:
                        try:
                            self.cancel(self.limit_order)
                        except:
                            pass
                        self.limit_order = None
                
                # Reset levels after any exit
                self.stop_level = None
                self.take_level = None
                self.initial_stop_level = None

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
        """Use Backtrader's proper trade notification for accurate PnL tracking"""
        
        if not trade.isclosed:
            return

        dt = bt.num2date(self.data.datetime[0])
        
        # Get accurate PnL from Backtrader
        pnl = trade.pnlcomm
        
        # Calculate entry and exit prices from PnL and trade data
        # PnL = (exit_price - entry_price) * size - commission
        # For long trades: exit_price = entry_price + (pnl / size)
        
        entry_price = self.last_entry_price if self.last_entry_price else 0
        if entry_price > 0 and trade.size != 0:
            # Calculate exit price from PnL: exit = entry + (pnl / size)
            exit_price = entry_price + (pnl / trade.size)
        else:
            # Fallback to trade.price (might be average or exit price)
            exit_price = trade.price
            if exit_price == entry_price:
                # Last resort: estimate from current data
                exit_price = float(self.data.close[0])
        
        # Use stored exit reason from notify_order (more reliable than price comparison)
        exit_reason = getattr(self, 'last_exit_reason', 'UNKNOWN')
        
        # Fallback: If no stored reason, try price comparison
        if exit_reason == 'UNKNOWN':
            if self.stop_level and abs(exit_price - self.stop_level) < 0.0002:
                exit_reason = "TRAILING_STOP"
            elif self.take_level and abs(exit_price - self.take_level) < 0.0002:
                exit_reason = "TAKE_PROFIT"
            else:
                exit_reason = "MANUAL_CLOSE"
        
        # Update statistics
        self.trades += 1
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
            pips = (exit_price - entry_price) / self.p.pip_value if self.p.pip_value and entry_price > 0 else 0
            print(f"TRADE CLOSED {dt:%Y-%m-%d %H:%M} reason={exit_reason} PnL={pnl:.2f} Pips={pips:.1f}")
            print(f"  Entry: {entry_price:.5f} -> Exit: {exit_price:.5f} | Size: {trade.size}")

        # Reset levels
        self.stop_level = None
        self.take_level = None
        self.initial_stop_level = None
        self.stop_has_been_trailed = False
        
        # Reset pullback state after trade completion
        if self.p.use_pullback_entry:
            self._reset_pullback_state()

    def stop(self):
        # Close any open positions at strategy end and manually process the trade
        if self.position:
            current_price = self.data.close[0]
            entry_price = self.position.price
            position_size = self.position.size
            
            # Calculate unrealized PnL correctly (position.size is already in currency units)
            price_diff = current_price - entry_price
            unrealized_pnl = position_size * price_diff
            
            if self.p.print_signals:
                print(f"STRATEGY END: Closing open position.")
                print(f"  Size: {position_size}, Entry: {entry_price:.5f}, Current: {current_price:.5f}")
                print(f"  Unrealized PnL: {unrealized_pnl:+.2f}")
            
            # Manually update statistics for the open trade before closing
            self.trades += 1
            if unrealized_pnl > 0:
                self.wins += 1
                self.gross_profit += unrealized_pnl
            else:
                self.losses += 1
                self.gross_loss += abs(unrealized_pnl)
            
            # Close the position
            self.order = self.close()
            
            # Cancel any remaining protective orders
            if self.stop_order:
                self.cancel(self.stop_order)
                self.stop_order = None
            if self.limit_order:
                self.cancel(self.limit_order)
                self.limit_order = None
        
        # Enhanced summary calculation
        print("=== SUNRISE SIMPLE SUMMARY ===")
        
        # Calculate metrics
        wr = (self.wins / self.trades * 100.0) if self.trades else 0.0
        pf = (self.gross_profit / self.gross_loss) if self.gross_loss > 0 else float('inf')
        
        # Backtrader portfolio value
        final_value = self.broker.get_value()
        starting_cash = 100000.0  # Known starting value
        total_pnl = final_value - starting_cash
        
        print(f"Trades: {self.trades} Wins: {self.wins} Losses: {self.losses} WinRate: {wr:.2f}% PF: {pf:.2f}")
        print(f"Final Value: {final_value:,.2f} | Total PnL: {total_pnl:+,.2f}")
        
        # Validation
        calculated_pnl = self.gross_profit - self.gross_loss
        pnl_diff = abs(calculated_pnl - total_pnl)
        if pnl_diff > 10.0:  # Allow for small rounding/fee differences
            print(f"INFO: PnL difference: {pnl_diff:.2f} (calculated: {calculated_pnl:+.2f})")

        if self.p.use_pullback_entry:
            self._reset_pullback_state()


if __name__ == '__main__':
    # =============================================================
    # RUNTIME FLAGS (edit here – no CLI / argparse as requested)
    # =============================================================
    DATA_FILENAME = 'EURUSD_5m_5Yea.csv'  # CSV inside data/
    FROMDATE = '2022-07-10'               # Extended test period
    TODATE = '2025-07-25'                 # Extended test period
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
        try: cerebro.plot(style='candlestick')
        except Exception as e: print(f"Plot error: {e}")
