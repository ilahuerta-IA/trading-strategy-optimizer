"""Advanced Sunrise OGLE Strategy - Template (Long-Only)
========================================================
MULTI-ASSET TEMPLATE - Copy and modify for different forex pairs.
Default configuration: USDCHF (values from sunrise_ogle_usdchf.py)

SUPPORTED INSTRUMENTS:
- USDCHF (default) - 0.0001 pip value, 5 decimals
- USDJPY - 0.01 pip value, 3 decimals, JPY P&L conversion
- EURUSD, GBPUSD, NZDUSD, AUDUSD - 0.0001 pip value, 5 decimals

ENTRY SYSTEM: VOLATILITY EXPANSION CHANNEL (4-PHASE STATE MACHINE)
------------------------------------------------------------------
PHASE 1 - SIGNAL SCANNING:
  - Monitor for EMA crossovers + directional candle confirmation
  - State: SCANNING -> ARMED_LONG

PHASE 2 - PULLBACK CONFIRMATION:
  - Wait for specified pullback candles (long_pullback_max_candles)
  - LONG: Wait 1-3 red candles after bullish signal
  - Global Invalidation Rule: Reset if opposing signal appears

PHASE 3 - BREAKOUT WINDOW OPENING:
  - Calculate breakout window with configurable offset
  - Set precise price levels for breakout detection

PHASE 4 - BREAKOUT MONITORING:
  - LONG: Enter when high breaks above stored breakout level
  - Window expiry: Auto-reset if no breakout within window

ENTRY CONDITIONS (LONG):
1. Confirmation EMA crosses ABOVE any of fast/medium/slow EMAs
2. Optional: Previous candle bullish (close[1] > open[1])
3. Optional: EMA ordering filter (confirm > fast & medium & slow)
4. Optional: Price filter (close > filter EMA)
5. Optional: Angle filter (EMA slope within range)
6. Optional: ATR volatility filter (ATR within range)

EXIT SYSTEM:
- ATR-based Stop Loss & Take Profit (OCA orders)
- SL = entry_bar_low - (ATR x SL_Mult)
- TP = entry_bar_high + (ATR x TP_Mult)

RISK MANAGEMENT:
- Fixed risk percentage per trade (default 0.5%)
- Automatic lot size calculation based on stop loss distance
- OCA protective orders (auto-cancel when one executes)

COMMISSION MODEL (Darwinex Zero):
- Commission: $2.50 per lot per order
- Margin: 3.33% (30:1 leverage)

DISCLAIMER:
Educational and research purposes ONLY. Not investment advice.
"""
from __future__ import annotations
import math
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import backtrader as bt
import numpy as np

# =============================================================
# CONFIGURATION PARAMETERS - EASILY EDITABLE AT TOP OF FILE
# =============================================================

# --- VOLATILITY EXPANSION CHANNEL - QUICK ACCESS ---
# USE_WINDOW_TIME_OFFSET = False        <- Enable/disable time delay (True/False)
# WINDOW_OFFSET_MULTIPLIER = 1.0        <- Time delay multiplier (0.5-2.0)
# WINDOW_PRICE_OFFSET_MULTIPLIER = 0.01 <- Channel expansion (0.3-1.0)
# LONG_PULLBACK_MAX_CANDLES = 2         <- LONG pullback depth (1-3)
# LONG_ENTRY_WINDOW_PERIODS = 2         <- LONG window duration (3-10)
# -------------------------------------------------------

# === INSTRUMENT SELECTION ===
# Default: USDCHF - change DATA_FILENAME and FOREX_INSTRUMENT together
DATA_FILENAME = 'USDCHF_5m_5Yea.csv'

# === BACKTEST SETTINGS ===
FROMDATE = '2020-07-01'               # Start date for backtesting (YYYY-MM-DD)
TODATE = '2025-07-01'                 # End date for backtesting (YYYY-MM-DD)
STARTING_CASH = 100000.0              # Initial account balance in USD
QUICK_TEST = False                    # True: Reduce to last 10 days for quick testing
LIMIT_BARS = 0                        # >0: Stop after N bars processed (0 = no limit)
ENABLE_PLOT = True                    # Show final chart with trades (requires matplotlib)

# === FOREX CONFIGURATION ===
ENABLE_FOREX_CALC = True              # Enable advanced forex position calculations
FOREX_INSTRUMENT = 'USDCHF'           # Current instrument (USDCHF, USDJPY, EURUSD, etc.)
PIP_VALUE = 0.0001                    # Standard for CHF pairs (0.01 for JPY pairs)
TEST_FOREX_MODE = False               # True: Quick 30-day test with forex calculations

# === COMMISSION SETTINGS (Darwinex Zero) ===
# From broker specs:
# - Spread: Variable per pair (already in price, not simulated separately)
# - Margin: 3.33% (30:1 leverage)
# - Commission: $2.50 per lot per order (entry + exit)
USE_FIXED_COMMISSION = True           # Enable commission simulation
COMMISSION_PER_LOT_PER_ORDER = 2.50   # USD per lot per order
SPREAD_PIPS = 0.7                     # USDCHF spread for cost calculation
MARGIN_PERCENT = 3.33                 # 3.33% margin = 30:1 leverage

# === TRADING DIRECTION ===
ENABLE_LONG_TRADES = True             # Enable long (buy) entries
# Note: This is a Long-Only template. SHORT trades are not supported.

# === DEBUG SETTINGS ===
VERBOSE_DEBUG = False                 # Print detailed debug info to console (set True only for troubleshooting)

# === TRADE REPORTING ===
EXPORT_TRADE_REPORTS = True           # Export detailed trade reports to temp_reports directory

# === VISUAL SETTINGS ===
PLOT_SLTP_LINES = True                # Show SL/TP lines on chart (red/green dashed)

# =============================================================================
# INSTRUMENT CONFIGURATION - Auto-detect JPY pairs vs Standard pairs
# =============================================================================
INSTRUMENT_CONFIGS = {
    'USDJPY': {'pip_value': 0.01, 'pip_decimal_places': 3, 'lot_size': 100000, 'atr_scale': 100.0, 'is_jpy': True, 'spread': 1.0},
    'EURJPY': {'pip_value': 0.01, 'pip_decimal_places': 3, 'lot_size': 100000, 'atr_scale': 100.0, 'is_jpy': True, 'spread': 1.2},
    'GBPJPY': {'pip_value': 0.01, 'pip_decimal_places': 3, 'lot_size': 100000, 'atr_scale': 100.0, 'is_jpy': True, 'spread': 1.5},
    'USDCHF': {'pip_value': 0.0001, 'pip_decimal_places': 5, 'lot_size': 100000, 'atr_scale': 1.0, 'is_jpy': False, 'spread': 0.7},
    'EURUSD': {'pip_value': 0.0001, 'pip_decimal_places': 5, 'lot_size': 100000, 'atr_scale': 1.0, 'is_jpy': False, 'spread': 0.6},
    'GBPUSD': {'pip_value': 0.0001, 'pip_decimal_places': 5, 'lot_size': 100000, 'atr_scale': 1.0, 'is_jpy': False, 'spread': 0.9},
    'NZDUSD': {'pip_value': 0.0001, 'pip_decimal_places': 5, 'lot_size': 100000, 'atr_scale': 1.0, 'is_jpy': False, 'spread': 1.2},
    'AUDUSD': {'pip_value': 0.0001, 'pip_decimal_places': 5, 'lot_size': 100000, 'atr_scale': 1.0, 'is_jpy': False, 'spread': 0.8},
}

# Get config for current instrument (default to USDCHF-like if not found)
_CURRENT_CONFIG = INSTRUMENT_CONFIGS.get(FOREX_INSTRUMENT, {
    'pip_value': PIP_VALUE,
    'pip_decimal_places': 5,
    'lot_size': 100000,
    'atr_scale': 1.0,
    'is_jpy': 'JPY' in FOREX_INSTRUMENT,
    'spread': 1.0
})

# === LONG ATR VOLATILITY FILTER (USDCHF OPTIMIZED) ===
LONG_USE_ATR_FILTER = True                   # Enable ATR-based volatility filtering
LONG_ATR_MIN_THRESHOLD = 0.000300            # Minimum ATR for entry
LONG_ATR_MAX_THRESHOLD = 0.000900            # Maximum ATR for entry (optimized Phase 4)

# ATR INCREMENT FILTER (DISABLED for USDCHF)
LONG_USE_ATR_INCREMENT_FILTER = False        # Disabled - inferior performance
LONG_ATR_INCREMENT_MIN_THRESHOLD = 0.000011
LONG_ATR_INCREMENT_MAX_THRESHOLD = 0.000080

# ATR DECREMENT FILTER (DISABLED for USDCHF)
LONG_USE_ATR_DECREMENT_FILTER = False        # Disabled - inferior performance
LONG_ATR_DECREMENT_MIN_THRESHOLD = -0.000030
LONG_ATR_DECREMENT_MAX_THRESHOLD = -0.000001

# === LONG ENTRY FILTERS (USDCHF OPTIMIZED) ===
LONG_USE_EMA_ORDER_CONDITION = False         # Require confirm_EMA > all other EMAs
LONG_USE_PRICE_FILTER_EMA = True             # Require close > filter_EMA (trend alignment)
LONG_USE_CANDLE_DIRECTION_FILTER = False     # Require previous candle bullish
LONG_USE_ANGLE_FILTER = False                # Require minimum EMA slope angle
LONG_MIN_ANGLE = 40.0                        # Minimum angle in degrees
LONG_MAX_ANGLE = 80.0                        # Maximum angle in degrees
LONG_ANGLE_SCALE_FACTOR = 10000.0            # Scale factor for angle calculation

# === LONG EMA POSITION FILTER ===
LONG_USE_EMA_BELOW_PRICE_FILTER = False      # Require EMAs below price

# === LONG PULLBACK ENTRY SYSTEM (USDCHF OPTIMIZED) ===
LONG_USE_PULLBACK_ENTRY = True               # Enable pullback entry system
LONG_PULLBACK_MAX_CANDLES = 2                # Max red candles in pullback
LONG_ENTRY_WINDOW_PERIODS = 2                # Bars to wait for breakout

# --- VOLATILITY EXPANSION CHANNEL - KEY TIMING PARAMETERS ---
USE_WINDOW_TIME_OFFSET = False               # DISABLED for USDCHF
WINDOW_OFFSET_MULTIPLIER = 1.0               # Window delay multiplier
WINDOW_PRICE_OFFSET_MULTIPLIER = 0.01        # Price expansion multiplier

# === TIME RANGE FILTER (USDCHF OPTIMIZED: 07:00-13:00 UTC) ===
USE_TIME_RANGE_FILTER = True                 # Enable time filter
ENTRY_START_HOUR = 7                         # Start hour (UTC)
ENTRY_START_MINUTE = 0                       # Start minute
ENTRY_END_HOUR = 13                          # End hour (UTC)
ENTRY_END_MINUTE = 0                         # End minute

# === RISK MANAGEMENT (USDCHF OPTIMIZED) ===
ATR_LENGTH = 10                              # ATR calculation period
LONG_ATR_SL_MULTIPLIER = 2.5                 # SL = ATR x 2.5
LONG_ATR_TP_MULTIPLIER = 10.0                # TP = ATR x 10.0 (R:R = 1:4)
RISK_PERCENT = 0.005                         # 0.5% risk per trade


# =============================================================================
# COMMISSION CLASS - Supports both JPY and Standard pairs
# =============================================================================
class ForexCommission(bt.CommInfoBase):
    """
    Commission scheme for Forex pairs with fixed commission per lot.
    Supports both JPY pairs (P&L conversion) and standard pairs.
    
    Darwinex Zero specs:
    - Commission: $2.50 per lot per order
    - Spread: Variable per instrument (in price)
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


class SunriseOgle(bt.Strategy):
    params = dict(
        # === TECHNICAL INDICATORS (USDCHF OPTIMIZED - Phase 3) ===
        ema_fast_length=24,              # Fast EMA period (optimized from 18)
        ema_medium_length=30,            # Medium EMA period (optimized from 18)
        ema_slow_length=36,              # Slow EMA period (optimized from 24)
        ema_confirm_length=1,            # Confirmation EMA (usually 1 for immediate response)
        ema_filter_price_length=40,      # Price filter EMA (optimized from 50)
        ema_exit_length=25,              # Exit EMA for crossover exit strategy
        
        # === ATR RISK MANAGEMENT ===
        atr_length=ATR_LENGTH,           # ATR calculation period
        
        # === TRADING DIRECTION ===
        enable_long_trades=ENABLE_LONG_TRADES,  # Enable long (buy) entries
        enable_short_trades=False,              # Forced False
        
        # === LONG ATR VOLATILITY FILTER ===
        long_use_atr_filter=LONG_USE_ATR_FILTER,
        long_atr_min_threshold=LONG_ATR_MIN_THRESHOLD,
        long_atr_max_threshold=LONG_ATR_MAX_THRESHOLD,
        # ATR INCREMENT/DECREMENT FILTERS
        long_use_atr_increment_filter=LONG_USE_ATR_INCREMENT_FILTER,
        long_atr_increment_min_threshold=LONG_ATR_INCREMENT_MIN_THRESHOLD,
        long_atr_increment_max_threshold=LONG_ATR_INCREMENT_MAX_THRESHOLD,
        long_use_atr_decrement_filter=LONG_USE_ATR_DECREMENT_FILTER,
        long_atr_decrement_min_threshold=LONG_ATR_DECREMENT_MIN_THRESHOLD,
        long_atr_decrement_max_threshold=LONG_ATR_DECREMENT_MAX_THRESHOLD,
        
        # === LONG ENTRY FILTERS ===
        long_use_ema_order_condition=LONG_USE_EMA_ORDER_CONDITION,
        long_use_price_filter_ema=LONG_USE_PRICE_FILTER_EMA,
        long_use_candle_direction_filter=LONG_USE_CANDLE_DIRECTION_FILTER,
        long_use_angle_filter=LONG_USE_ANGLE_FILTER,
        long_min_angle=LONG_MIN_ANGLE,
        long_max_angle=LONG_MAX_ANGLE,
        long_angle_scale_factor=LONG_ANGLE_SCALE_FACTOR,
        long_use_ema_below_price_filter=LONG_USE_EMA_BELOW_PRICE_FILTER,
        long_atr_sl_multiplier=LONG_ATR_SL_MULTIPLIER,    # SL multiplier (USDCHF: 2.5)
        long_atr_tp_multiplier=LONG_ATR_TP_MULTIPLIER,    # TP multiplier (USDCHF: 10.0)
        
        # === LONG PULLBACK ENTRY SYSTEM ===
        long_use_pullback_entry=LONG_USE_PULLBACK_ENTRY,
        long_pullback_max_candles=LONG_PULLBACK_MAX_CANDLES,
        long_entry_window_periods=LONG_ENTRY_WINDOW_PERIODS,
        window_offset_multiplier=WINDOW_OFFSET_MULTIPLIER,
        use_window_time_offset=USE_WINDOW_TIME_OFFSET,
        window_price_offset_multiplier=WINDOW_PRICE_OFFSET_MULTIPLIER,
        
        # === TIME RANGE FILTER ===
        use_time_range_filter=USE_TIME_RANGE_FILTER,
        entry_start_hour=ENTRY_START_HOUR,
        entry_start_minute=ENTRY_START_MINUTE,
        entry_end_hour=ENTRY_END_HOUR,
        entry_end_minute=ENTRY_END_MINUTE,
        
        # === POSITION SIZING ===
        size=1,
        enable_risk_sizing=True,
        risk_percent=RISK_PERCENT,        # Risk per trade (0.5%)
        margin_pct=MARGIN_PERCENT,        # Margin for position limit
        contract_size=100000,
        print_signals=True,
        verbose_debug=VERBOSE_DEBUG,
        
        # === FOREX SETTINGS (auto-configured from INSTRUMENT_CONFIGS) ===
        forex_instrument=FOREX_INSTRUMENT,
        forex_pip_value=_CURRENT_CONFIG['pip_value'],
        forex_pip_decimal_places=_CURRENT_CONFIG['pip_decimal_places'],
        forex_lot_size=_CURRENT_CONFIG['lot_size'],
        forex_atr_scale=_CURRENT_CONFIG['atr_scale'],
        spread_pips=SPREAD_PIPS,
        use_forex_position_calc=True,

        # === ACCOUNT SETTINGS ===
        account_currency='USD',
        account_leverage=30.0,
        
        # === PLOTTING & VISUALIZATION ===
        plot_result=True,
        buy_sell_plotdist=0.0005,
        plot_sltp_lines=PLOT_SLTP_LINES,
    )

    def _record_trade_entry(self, signal_direction, dt, entry_price, position_size, current_atr):
        """Record trade entry details for reporting (optimized format)"""
        if not (EXPORT_TRADE_REPORTS or TRADE_REPORT_ENABLED) or not self.trade_report_file:
            return
            
        try:
            # Calculate periods before entry with enhanced fallback logic
            current_bar = len(self)
            periods_before_entry = 0
            
            # 4-tier fallback logic for robust timing calculation
            if hasattr(self, 'entry_window_start') and self.entry_window_start is not None:
                # Primary: Use window start (most accurate)
                periods_before_entry = current_bar - self.entry_window_start
                print(f"[DEBUG] Used entry_window_start: {self.entry_window_start}, bars = {periods_before_entry}")
            elif hasattr(self, 'signal_detection_bar') and self.signal_detection_bar is not None:
                # Secondary: Use signal detection bar
                periods_before_entry = current_bar - self.signal_detection_bar
                print(f"[DEBUG] Used signal_detection_bar: {self.signal_detection_bar}, bars = {periods_before_entry}")
            elif hasattr(self, 'window_bar_start') and self.window_bar_start is not None:
                # Tertiary: Use window_bar_start if available
                periods_before_entry = current_bar - self.window_bar_start
                print(f"[DEBUG] Used window_bar_start: {self.window_bar_start}, bars = {periods_before_entry}")
            else:
                # Quaternary: Estimate based on pullback count + 1
                fallback_bars_to_entry = getattr(self, 'pullback_candle_count', 0) + 1
                periods_before_entry = fallback_bars_to_entry
                print(f"[DEBUG] Used fallback calculation: pullback_count={getattr(self, 'pullback_candle_count', 0)} + 1 = {periods_before_entry}")
            
            # Ensure reasonable bounds
            if periods_before_entry < 0:
                periods_before_entry = 1
            elif periods_before_entry > 50:  # Cap at reasonable maximum
                periods_before_entry = 50
            
            # Get current angle with correct scale factor based on signal direction
            current_angle = self._angle() if hasattr(self, '_angle') else 0.0
            
            # Calculate real ATR increment (current vs signal detection) - USER REQUESTED
            real_atr_increment = 0.0
            stored_signal_atr = getattr(self, 'entry_signal_detection_atr', None)
            if stored_signal_atr is not None:
                real_atr_increment = abs(current_atr - stored_signal_atr)
            
            # Store trade entry data (simplified - keep ATR Current, add back increment)
            trade_entry = {
                'entry_time': dt,
                'direction': signal_direction,
                'stop_level': self.stop_level,
                'take_level': self.take_level,
                'current_atr': current_atr,  # Keep this - very important data
                'current_angle': current_angle,
                'periods_before_entry': periods_before_entry,
                'real_atr_increment': real_atr_increment,  # Add back - user requested
                'pullback_state': getattr(self, 'pullback_state', 'NORMAL')
            }
            
            # Add to trade reports list
            self.trade_reports.append(trade_entry)
            
            # Write to file (remove Stop Loss/Take Profit, ensure ATR increment shows)
            self.trade_report_file.write(f"ENTRY #{len(self.trade_reports)}\n")
            self.trade_report_file.write(f"Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.trade_report_file.write(f"Direction: {signal_direction}\n")
            self.trade_report_file.write(f"ATR Current: {current_atr:.6f}\n")  # Keep this - very important!
            # Always show ATR increment - USER REQUESTED: Add ATR increment in each entry
            stored_increment = getattr(self, 'entry_atr_increment', None)
            print(f"[DEBUG] entry_atr_increment = {stored_increment}")  # DEBUG
            if stored_increment is not None:
                # Determine if it's increment or decrement based on sign and filter status
                if stored_increment >= 0:
                    # Positive change - always show as increment
                    if self.p.long_use_atr_increment_filter:
                        self.trade_report_file.write(f"ATR Increment: {stored_increment:+.6f} (Filtered)\n")
                    else:
                        self.trade_report_file.write(f"ATR Increment: {stored_increment:+.6f} (No Filter)\n")
                else:
                    # Negative change - show as decrement only if filter is enabled
                    decrement_filter_enabled = self.p.long_use_atr_decrement_filter
                    if decrement_filter_enabled:
                        self.trade_report_file.write(f"ATR Decrement: {abs(stored_increment):.6f} (Filtered)\n")
                    else:
                        self.trade_report_file.write(f"ATR Change: {stored_increment:+.6f} (Decrement Filter OFF)\n")
            else:
                print(f"DEBUG: ATR Change = N/A because entry_atr_increment is None")  # DEBUG
                self.trade_report_file.write(f"ATR Change: N/A\n")
            self.trade_report_file.write(f"Angle Current: {current_angle:.2f} deg\n")
            
            # Debug angle validation status
            if self.p.long_use_angle_filter:
                angle_ok = self.p.long_min_angle <= current_angle <= self.p.long_max_angle
                self.trade_report_file.write(f"Angle Filter: ENABLED | Range: {self.p.long_min_angle:.1f}-{self.p.long_max_angle:.1f} deg | Valid: {angle_ok}\n")
            else:
                self.trade_report_file.write(f"Angle Filter: DISABLED\n")

            # Always show periods/bars before entry
            self.trade_report_file.write(f"Bars to Entry: {periods_before_entry}\n")
            if getattr(self, 'pullback_state', 'NORMAL') != 'NORMAL':
                self.trade_report_file.write(f"Pullback State: {getattr(self, 'pullback_state', 'NORMAL')}\n")
            self.trade_report_file.write("-" * 50 + "\n\n")
            self.trade_report_file.flush()
            
        except Exception as e:
            print(f"Trade entry recording error: {e}")

    def _record_trade_exit(self, dt, exit_price, pnl, exit_reason):
        """Record trade exit details for reporting (optimized format)"""
        if not (EXPORT_TRADE_REPORTS or TRADE_REPORT_ENABLED) or not self.trade_report_file:
            return
            
        try:
            # Find the most recent trade entry
            if self.trade_reports:
                last_trade = self.trade_reports[-1]
                
                # Calculate trade duration
                if 'entry_time' in last_trade:
                    duration = dt - last_trade['entry_time']
                    duration_minutes = duration.total_seconds() / 60
                    duration_bars = int(duration_minutes / 5)  # 5-minute bars
                else:
                    duration_minutes = 0
                    duration_bars = 0
                
                # Calculate pips for display
                direction = last_trade.get('direction', 'UNKNOWN')
                entry_price = None
                # Get entry price from stored levels or estimate from P&L
                if 'stop_level' in last_trade and 'take_level' in last_trade:
                    # Estimate entry price from stop/take levels and direction
                    stop_level = last_trade['stop_level']
                    take_level = last_trade['take_level']
                    # For LONG: entry between stop and take
                    entry_price = (stop_level + take_level) / 2
                
                # Calculate pips based on direction and P&L
                pips = 0.0
                if entry_price and exit_price:
                    pips = (exit_price - entry_price) / 0.0001  # Forex pip calculation
                
                # Update trade record with exit info (add pips back)
                last_trade.update({
                    'exit_time': dt,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'pips': pips,
                    'exit_reason': exit_reason,
                    'duration_minutes': duration_minutes,
                    'duration_bars': duration_bars
                })
                
                # Write exit details to file (add pips back)
                self.trade_report_file.write(f"EXIT #{len(self.trade_reports)}\n")
                self.trade_report_file.write(f"Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n")
                self.trade_report_file.write(f"Exit Reason: {exit_reason}\n")
                self.trade_report_file.write(f"P&L: {pnl:.2f}\n")
                if abs(pips) > 0.1:  # Only show pips if meaningful
                    self.trade_report_file.write(f"Pips: {pips:.1f}\n")
                self.trade_report_file.write(f"Duration: {duration_bars} bars ({duration_minutes:.0f} min)\n")
                self.trade_report_file.write("=" * 80 + "\n\n")
                self.trade_report_file.flush()
                
        except Exception as e:
            print(f"Trade exit recording error: {e}")

    def _close_trade_reporting(self):
        """Close trade reporting file and generate summary"""
        if self.trade_report_file:
            try:
                # Write summary
                total_trades = len(self.trade_reports)
                winning_trades = [t for t in self.trade_reports if t.get('pnl', 0) > 0]
                losing_trades = [t for t in self.trade_reports if t.get('pnl', 0) < 0]
                
                total_pnl = sum(t.get('pnl', 0) for t in self.trade_reports)
                win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
                
                self.trade_report_file.write("\n" + "="*80 + "\n")
                self.trade_report_file.write("SUMMARY\n")
                self.trade_report_file.write("="*80 + "\n")
                self.trade_report_file.write(f"Total Trades: {total_trades}\n")
                self.trade_report_file.write(f"Winning Trades: {len(winning_trades)}\n")
                self.trade_report_file.write(f"Losing Trades: {len(losing_trades)}\n")
                self.trade_report_file.write(f"Win Rate: {win_rate:.2f}%\n")
                self.trade_report_file.write(f"Total P&L: {total_pnl:.2f}\n")
                
                if winning_trades:
                    avg_win = sum(t.get('pnl', 0) for t in winning_trades) / len(winning_trades)
                    self.trade_report_file.write(f"Average Win: {avg_win:.2f}\n")
                
                if losing_trades:
                    avg_loss = sum(t.get('pnl', 0) for t in losing_trades) / len(losing_trades)
                    self.trade_report_file.write(f"Average Loss: {avg_loss:.2f}\n")
                
                self.trade_report_file.write("="*80 + "\n")
                self.trade_report_file.close()
                print(f"Trade report completed: {total_trades} trades recorded")
                
            except Exception as e:
                print(f"Trade reporting close error: {e}")
            
            self.trade_report_file = None

    def _cross_above(self, a, b):
        try:
            current_a = float(a[0])
            current_b = float(b[0])
            previous_a = float(a[-1])
            previous_b = float(b[-1])
            crossover = (current_a > current_b) and (previous_a <= previous_b)
            return crossover
        except (IndexError, ValueError, TypeError):
            return False

    def _cross_below(self, a, b):
        try:
            current_a = float(a[0])
            current_b = float(b[0])
            previous_a = float(a[-1])
            previous_b = float(b[-1])
            crossunder = (current_a < current_b) and (previous_a >= previous_b)
            return crossunder
        except (IndexError, ValueError, TypeError):
            return False

    def _angle(self):
        try:
            current_ema = float(self.ema_confirm[0])
            previous_ema = float(self.ema_confirm[-1])
            rise = (current_ema - previous_ema) * self.p.long_angle_scale_factor
            angle_radians = math.atan(rise)  # run = 1 (1 bar)
            angle_degrees = math.degrees(angle_radians)
            return angle_degrees
        except (IndexError, ValueError, TypeError, ZeroDivisionError):
            return float('nan')
    
    def _calculate_forex_position_size(self, entry_price, stop_loss_price):
        if not self.p.use_forex_position_calc:
            return None, None, None, None, None
            
        # Calculate risk in pips
        price_difference = abs(entry_price - stop_loss_price)
        pip_risk = price_difference / self.p.forex_pip_value
        
        # Account equity and risk amount
        account_equity = self.broker.get_value()
        risk_amount = account_equity * self.p.risk_percent
        
        if self.p.forex_quote_currency == 'USD':
            pip_value_per_lot = 10.0  # Standard forex: $10 per pip for 100K lot
        else:
            pip_value_per_lot = 10.0
        
        # Calculate optimal lot size
        if pip_risk > 0:
            optimal_lots = risk_amount / (pip_risk * pip_value_per_lot)
            optimal_lots = max(self.p.forex_micro_lot_size, 
                             round(optimal_lots / self.p.forex_micro_lot_size) * self.p.forex_micro_lot_size)
        else:
            return None, None, None, None, None
        
        # Minimum position size check (very minimal)
        min_lots = 0.01  # Minimum 0.01 lots
        if optimal_lots < min_lots:
            optimal_lots = min_lots
            
        # Maximum absolute limit (very high - 500 lots)
        max_absolute_lots = 500.0
        if optimal_lots > max_absolute_lots:
            optimal_lots = max_absolute_lots
            
        # Calculate position value and margin required
        position_value = optimal_lots * self.p.forex_lot_size * entry_price
        margin_required = position_value * (self.p.forex_margin_required / 100.0)
        
        contracts = max(1, int(optimal_lots * 100000))  # Scale lots to NZD units
        print(f"DEBUG_POSITION_SIZE: optimal_lots={optimal_lots:.2f}, contracts={contracts}")
        
        return optimal_lots, contracts, margin_required, pip_risk, position_value
    
    def _format_forex_trade_info(self, entry_price, stop_loss, take_profit, lot_size, pip_risk, position_value, margin_required):
        if not self.p.use_forex_position_calc:
            return ""
            
        # Calculate potential profit in ticks
        if take_profit and entry_price:
            profit_pips = abs(take_profit - entry_price) / self.p.forex_pip_value
            risk_reward = profit_pips / pip_risk if pip_risk > 0 else 0
        else:
            profit_pips = 0
            risk_reward = 0
            
        # Calculate monetary values for NZDUSD
        # Standard forex: $10 per pip for 100K lot
        pip_value_per_lot = 10.0
            
        risk_amount = pip_risk * lot_size * pip_value_per_lot
        profit_potential = profit_pips * lot_size * pip_value_per_lot
        spread_cost = self.p.forex_spread_pips * lot_size * pip_value_per_lot
        
        # Format units for NZDUSD
        units_desc = f"{lot_size * self.p.forex_lot_size:,.0f} {self.p.forex_base_currency}"
        
        # Format prices based on decimal places
        price_format = f"{{:.{self.p.forex_pip_decimal_places}f}}"
        
        return (f"\n--- FOREX TRADE DETAILS ({self.p.forex_instrument}) ---\n"
                f"Position Size: {lot_size:.2f} lots ({units_desc})\n"
                f"Position Value: ${position_value:,.2f}\n"
                f"Margin Required: ${margin_required:,.2f} ({self.p.forex_margin_required}%)\n"
                f"Entry: {price_format.format(entry_price)} | SL: {price_format.format(stop_loss)} | TP: {price_format.format(take_profit)}\n"
                f"Risk: {pip_risk:.1f} ticks (${risk_amount:.2f}) | Profit: {profit_pips:.1f} ticks (${profit_potential:.2f})\n"
                f"Risk/Reward: 1:{risk_reward:.2f} | Spread Cost: ${spread_cost:.2f}\n"
                f"Account Leverage: {self.p.account_leverage:.0f}:1 | Account: {self.p.account_currency}")
    
    def _validate_forex_setup(self):
        if not self.p.use_forex_position_calc:
            return True
            
        data_filename = getattr(self, '_data_filename', '')
        instrument = self.p.forex_instrument
        
        # Check if data filename matches configured instrument
        if instrument.upper() not in data_filename.upper():
            print(f"WARNING: Data file '{data_filename}' may not match configured instrument {instrument}")
            
        return True
    
    def _get_forex_instrument_config(self, instrument_name=None):
        """Get forex configuration for the specified instrument from INSTRUMENT_CONFIGS."""
        if instrument_name is None:
            instrument_name = self.p.forex_instrument
        
        # Use global INSTRUMENT_CONFIGS
        return INSTRUMENT_CONFIGS.get(instrument_name, INSTRUMENT_CONFIGS.get('USDCHF'))
    
    def _apply_forex_config(self):
        if not self.p.use_forex_position_calc:
            return
            
        # Get configuration for configured instrument
        instrument = self.p.forex_instrument
        config = self._get_forex_instrument_config(instrument)
        
        data_filename = getattr(self, '_data_filename', '').upper()
        self._detected_instrument = instrument
                
        # Apply instrument configuration
        self.p.forex_pip_value = config['pip_value']
        self.p.forex_pip_decimal_places = config['pip_decimal_places']
        self.p.forex_lot_size = config['lot_size']
        self.p.spread_pips = config.get('spread', 1.0)
                
        # Log forex configuration
        print(f"CONFIGURED: {instrument} from filename: {data_filename}")
        print(f"Pip Value: {self.p.forex_pip_value} | Lot Size: {self.p.forex_lot_size:,}")

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
            self.pending_close = False  # Flag to prevent new entries while closing position
            
            # Current protective price levels (float) for plotting / decisions
            self.stop_level = None
            self.take_level = None
            
            # Portfolio tracking for combined plotting
            self._portfolio_values = []
            self._timestamps = []
            self._trade_pnls = []  # Store PnL and dates for yearly stats
            
            # Book-keeping for filters
            self.last_entry_bar = None
            self.last_exit_bar = None
            self.last_entry_price = None
            # Track initial stop level
            self.initial_stop_level = None
            
            # Track trade history for ta.barssince() logic
            self.trade_exit_bars = []  # Store bars where trades closed (ta.barssince equivalent)
            
            # Prevent entry and exit on same bar
            self.exit_this_bar = False  # Flag to prevent entry on exit bar
            self.last_exit_bar_current = None  # Track if we exited this specific bar #3
            
            # PULLBACK ENTRY STATE MACHINE
            self.pullback_state = "NORMAL"  # States: NORMAL, WAITING_PULLBACK, WAITING_BREAKOUT
            self.pullback_red_count = 0  # Count of consecutive red candles (LONG pullbacks)
            self.first_red_high = None  # High of first red candle in pullback (LONG)
            self.entry_window_start = None  # Bar when entry window opened
            self.breakout_target = None  # Price target for entry breakout
            
            # ATR VOLATILITY FILTER TRACKING
            self.signal_detection_atr = None  # ATR value when signal was first detected
            self.signal_detection_bar = None  # Bar number when signal was first detected
            self.pullback_start_atr = None    # ATR value when pullback phase started

            # NEW STATE MACHINE FOR VOLATILITY EXPANSION CHANNEL ENTRY LOGIC
            self.entry_state = "SCANNING"  # States: SCANNING, ARMED_LONG, WINDOW_OPEN
            self.armed_direction = None    # Will be 'LONG'
            self.pullback_candle_count = 0
            self.last_pullback_candle_high = None
            self.last_pullback_candle_low = None
            self.window_top_limit = None
            self.window_bottom_limit = None
            self.window_expiry_bar = None
            self.window_breakout_level = None  # Price level that must be broken for entry
            
            # CRITICAL FIX: Store original signal trigger candle for validation
            self.signal_trigger_candle = None

            # Track initial cash (will be set on first bar)
            self._initial_cash = None
            
            # Basic stats
            self.trades = 0
            self.wins = 0
            self.losses = 0
            self.gross_profit = 0.0
            self.gross_loss = 0.0
            
            # Track exit reason for notify_trade
            self.last_exit_reason = "UNKNOWN"
            
            # Track entry signals and performance metrics
            self.debug_file = None
            self.entry_signal_count = 0
            self.blocked_entry_count = 0
            self.successful_entry_count = 0
            
            # Store data filename for forex validation
            self._data_filename = getattr(self.data._dataname, 'name', 
                                        getattr(self.data, '_dataname', ''))
            if isinstance(self._data_filename, str):
                self._data_filename = Path(self._data_filename).name
            
            # Apply forex configuration based on instrument detection
            if self.p.use_forex_position_calc:
                self._apply_forex_config()
                self.p.contract_size = self.p.forex_lot_size  # Sync the contract size with the detected lot size
                self._validate_forex_setup()
                
            # Initialize trade reporting
            self._init_trade_reporting()

    def _init_trade_reporting(self):
        """Initialize trade reporting functionality"""
        self.trade_reports = []  # Store trade details for export
        self.trade_report_file = None
        
        if EXPORT_TRADE_REPORTS or TRADE_REPORT_ENABLED:
            try:
                # Create temp_reports directory if it doesn't exist
                from pathlib import Path
                report_dir = Path("temp_reports")
                report_dir.mkdir(exist_ok=True)
                
                # Extract asset name from data filename
                asset_name = "UNKNOWN"
                if hasattr(self, '_data_filename') and self._data_filename:
                    # Extract asset name from filename (e.g., "USDCHF_5m_5Yea.csv" -> "USDCHF")
                    asset_name = str(self._data_filename).split('_')[0].replace('.csv', '')
                
                # Create trade report filename with timestamp
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_filename = f"{asset_name}_trades_{timestamp}.txt"
                report_path = report_dir / report_filename
                
                # Open trade report file
                self.trade_report_file = open(report_path, 'w', encoding='utf-8')
                
                # Write header
                self.trade_report_file.write(f"=== SUNRISE STRATEGY TRADE REPORT ===\n")
                self.trade_report_file.write(f"Asset: {asset_name}\n")
                self.trade_report_file.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                self.trade_report_file.write(f"Data File: {self._data_filename}\n")
                
                # Trading configuration
                direction = []
                if self.p.enable_long_trades: direction.append("LONG")
                self.trade_report_file.write(f"Trading Direction: {' & '.join(direction) if direction else 'NONE'}\n")
                self.trade_report_file.write("\n")
                
                # Fixed Configuration Parameters (no longer repeated in each entry)
                self.trade_report_file.write("CONFIGURATION PARAMETERS:\n")
                self.trade_report_file.write("-" * 30 + "\n")
                
                # LONG parameters
                if self.p.enable_long_trades:
                    self.trade_report_file.write("LONG Configuration:\n")
                    self.trade_report_file.write(f"  ATR Range: {self.p.long_atr_min_threshold:.6f} - {self.p.long_atr_max_threshold:.6f}\n")
                    # ATR increment/decrement filter configuration
                    if self.p.long_use_atr_increment_filter:
                        self.trade_report_file.write(f"  ATR Increment Range: {self.p.long_atr_increment_min_threshold:.6f} to {self.p.long_atr_increment_max_threshold:.6f}\n")
                    if self.p.long_use_atr_decrement_filter:
                        self.trade_report_file.write(f"  ATR Decrement Range: {self.p.long_atr_decrement_min_threshold:.6f} to {self.p.long_atr_decrement_max_threshold:.6f}\n")
                    self.trade_report_file.write(f"  Angle Range: {self.p.long_min_angle:.2f} to {self.p.long_max_angle:.2f} deg\n")
                    self.trade_report_file.write(f"  Candle Direction Filter: {'ENABLED (Require bullish candle)' if self.p.long_use_candle_direction_filter else 'DISABLED'}\n")
                    self.trade_report_file.write(f"  Pullback Mode: {self.p.long_use_pullback_entry}\n\n")
                    
                # Common parameters
                self.trade_report_file.write("Common Parameters:\n")
                self.trade_report_file.write(f"  Risk Percent: {self.p.risk_percent:.1f}%\n")
                if self.p.use_time_range_filter:
                    self.trade_report_file.write(f"  Trading Hours: {self.p.entry_start_hour:02d}:{self.p.entry_start_minute:02d} - {self.p.entry_end_hour:02d}:{self.p.entry_end_minute:02d} UTC\n")
                else:
                    self.trade_report_file.write(f"  Trading Hours: 24/7 (No time filter)\n")
                
                # Window time offset configuration
                if self.p.use_window_time_offset:
                    typical_offset = int(1 * self.p.window_offset_multiplier)  # Typical case with 1 pullback candle
                    self.trade_report_file.write(f"  Window Time Offset: ENABLED (Multiplier: {self.p.window_offset_multiplier:.1f}, Typical delay: {typical_offset} bars)\n")
                else:
                    self.trade_report_file.write(f"  Window Time Offset: DISABLED (Immediate window opening)\n")
                if self.p.enable_long_trades:
                    self.trade_report_file.write(f"  LONG Stop Loss ATR Multiplier: {self.p.long_atr_sl_multiplier:.1f}\n")
                    self.trade_report_file.write(f"  LONG Take Profit ATR Multiplier: {self.p.long_atr_tp_multiplier:.1f}\n")
                
                self.trade_report_file.write("\n" + "="*80 + "\n")
                self.trade_report_file.write("TRADE DETAILS\n")
                self.trade_report_file.write("="*80 + "\n\n")
                self.trade_report_file.flush()
                
                print(f"Trade report: {report_path}")
                
            except Exception as e:
                print(f"Trade reporting initialization failed: {e}")
                self.trade_report_file = None

    def _reset_entry_state(self):
        """Reset all entry state variables to initial values for new signal detection"""
        self.entry_state = "SCANNING"
        self.armed_direction = None
        self.pullback_candle_count = 0
        self.last_pullback_candle_high = None
        self.last_pullback_candle_low = None
        self.window_top_limit = None
        self.window_bottom_limit = None
        self.window_expiry_bar = None
        self.window_breakout_level = None
        # CRITICAL FIX: Reset stored trigger candle
        self.signal_trigger_candle = None

    def _phase1_scan_for_signal(self):
        """PHASE 1: Scan for initial EMA crossover signals (LONG ONLY)"""
        # Check LONG signals
        if self.p.enable_long_trades:
            # Previous candle bullish check (optional)
            try:
                prev_bull = self.data.close[-1] > self.data.open[-1]
            except IndexError:
                prev_bull = False

            # EMA crossover check (ANY of the three) - ABOVE for LONG
            cross_fast = self._cross_above(self.ema_confirm, self.ema_fast)
            cross_medium = self._cross_above(self.ema_confirm, self.ema_medium) 
            cross_slow = self._cross_above(self.ema_confirm, self.ema_slow)
            cross_any = cross_fast or cross_medium or cross_slow
            
            # Check candle direction filter (optional)
            candle_direction_ok = True
            if self.p.long_use_candle_direction_filter:
                candle_direction_ok = prev_bull
            
            if candle_direction_ok and cross_any:
                # Apply additional filters
                signal_valid = True
                
                # EMA order condition (LONG: confirm > others)
                if self.p.long_use_ema_order_condition:
                    ema_order_ok = (
                        self.ema_confirm[0] > self.ema_fast[0] and
                        self.ema_confirm[0] > self.ema_medium[0] and
                        self.ema_confirm[0] > self.ema_slow[0]
                    )
                    if not ema_order_ok:
                        signal_valid = False

                # Price filter EMA (LONG: close > filter)
                if signal_valid and self.p.long_use_price_filter_ema:
                    price_above_filter = self.data.close[0] > self.ema_filter_price[0]
                    if not price_above_filter:
                        signal_valid = False
                
                # EMA position filter (LONG: all EMAs below price)
                if signal_valid and self.p.long_use_ema_below_price_filter:
                    emas_below_price = (
                        self.ema_fast[0] < self.data.close[0] and
                        self.ema_medium[0] < self.data.close[0] and
                        self.ema_slow[0] < self.data.close[0]
                    )
                    if not emas_below_price:
                        signal_valid = False

                # Angle filter (LONG: positive angle range)
                if signal_valid and self.p.long_use_angle_filter:
                    current_angle = self._angle()
                    angle_ok = self.p.long_min_angle <= current_angle <= self.p.long_max_angle
                    if not angle_ok:
                        signal_valid = False

                # ATR volatility filter (LONG)
                if signal_valid and self.p.long_use_atr_filter:
                    current_atr = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
                    if current_atr < self.p.long_atr_min_threshold or current_atr > self.p.long_atr_max_threshold:
                        signal_valid = False

                if signal_valid:
                    # CRITICAL FIX: Store ATR when LONG signal is detected 
                    current_atr = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
                    self.signal_detection_atr = current_atr
                    return 'LONG'

        return None

    def _phase2_confirm_pullback(self, armed_direction):
        """PHASE 2: Count pullback candles and validate pullback sequence"""
        # Check candle direction for pullback
        is_pullback_candle = False
        
        if armed_direction == 'LONG':
            # For LONG: pullback = bearish candle (close < open)
            is_pullback_candle = self.data.close[0] < self.data.open[0]
        
        if is_pullback_candle:
            self.pullback_candle_count += 1
            
            # Check if we've reached the required pullback count based on direction
            max_candles = self.p.long_pullback_max_candles
            
            if self.pullback_candle_count >= max_candles:
                # Capture the last pullback candle data for channel calculation
                self.last_pullback_candle_high = float(self.data.high[0])
                self.last_pullback_candle_low = float(self.data.low[0])
                
                if self.p.print_signals:
                    print(f"PULLBACK CONFIRMED: {armed_direction} pullback complete ({self.pullback_candle_count} candles)")
                return True
        else:
            # Non-pullback candle - apply Global Invalidation Rule
            # Reset to scanning if we get a candle that breaks the pullback pattern
            if self.p.print_signals:
                print(f"PULLBACK INVALIDATED: {armed_direction} non-pullback candle detected, resetting to SCANNING")
            self._reset_entry_state()
            
        return False

    def _phase3_open_breakout_window(self, armed_direction):
        """PHASE 3: Open the two-sided breakout window after pullback confirmation"""
        current_bar = len(self)

        # 1. Implement Optional Time Offset
        window_start_bar = current_bar
        if self.p.use_window_time_offset:
            time_offset = int(self.pullback_candle_count * self.p.window_offset_multiplier)
            window_start_bar = current_bar + time_offset
        
        self.window_bar_start = window_start_bar
        
        # 2. Set Window Duration
        window_periods = self.p.long_entry_window_periods
        self.window_expiry_bar = window_start_bar + window_periods

        # 3. Calculate the Two-Sided Price Channel EXACTLY as specified
        last_high = self.last_pullback_candle_high
        last_low = self.last_pullback_candle_low
        candle_range = last_high - last_low
        price_offset = candle_range * self.p.window_price_offset_multiplier

        self.window_top_limit = last_high + price_offset
        self.window_bottom_limit = last_low - price_offset
        
        # 4. Final State Transition
        self.entry_state = "WINDOW_OPEN"
        
        if self.p.print_signals:
            time_offset_text = f" (offset: {time_offset} bars)" if self.p.use_window_time_offset else " (immediate)"
            print(f"WINDOW OPENED ({armed_direction}): Active from bar {window_start_bar} to {self.window_expiry_bar}{time_offset_text}")
            success_level = self.window_top_limit
            failure_level = self.window_bottom_limit
            print(f"  - Success Level: {' > '}{success_level:.5f}")
            print(f"  - Failure Level: {' < '}{failure_level:.5f}")
            print(f"  - Channel Range: {last_low:.5f} to {last_high:.5f} + {price_offset:.5f} offset")

    def _phase4_monitor_window(self, armed_direction):
        """PHASE 4: Monitor for breakout or failure within the two-sided channel"""
        current_bar = len(self)

        # Check if window is active yet
        if current_bar < self.window_bar_start:
            return None  # Not yet active, do nothing

        # Check for Timeout
        if current_bar > self.window_expiry_bar:
            if self.p.print_signals:
                print(f"WINDOW TIMEOUT ({armed_direction}): No breakout occurred. Resetting to ARMED.")
            self.entry_state = f"ARMED_{armed_direction}"  # Return to pullback search
            self.pullback_candle_count = 0  # Reset count
            # Clear window variables
            self.window_top_limit, self.window_bottom_limit, self.window_expiry_bar = None, None, None
            self.window_breakout_level = None
            return None

        # Check Window Boundaries
        current_high = self.data.high[0]
        current_low = self.data.low[0]

        if armed_direction == 'LONG':
            # Check for SUCCESS condition first (break above top_limit)
            if current_high >= self.window_top_limit:
                if self.p.print_signals:
                    print(f"SUCCESS BREAKOUT (LONG): Price {current_high:.5f} broke above success level {self.window_top_limit:.5f}")
                return 'SUCCESS'
            
            # Check for FAILURE condition (break below bottom_limit - indicates instability)
            elif current_low <= self.window_bottom_limit:
                if self.p.print_signals:
                    print(f"FAILURE BREAKOUT (LONG): Price {current_low:.5f} broke below failure level {self.window_bottom_limit:.5f}. Instability detected.")
                self.entry_state = "ARMED_LONG"  # Return to pullback search
                self.pullback_candle_count = 0
                self.window_top_limit, self.window_bottom_limit, self.window_expiry_bar = None, None, None
                self.window_breakout_level = None
                return None
        
        return None  # No breakout yet, continue monitoring

    def next(self):
        """Main strategy logic using volatility expansion channel entry system with 4-phase state machine"""
        # Capture initial cash on first bar (before any trades)
        if self._initial_cash is None:
            self._initial_cash = self.broker.get_value()
        
        # Track portfolio value and timestamp for plotting
        if hasattr(self, '_portfolio_values'):
            self._portfolio_values.append(self.broker.get_value())
            self._timestamps.append(self.data.datetime.datetime(0))
        
        # RESET exit flag at start of each new bar
        self.exit_this_bar = False
        
        # CHECK for pending close operation - skip all logic if waiting for close
        if hasattr(self, 'pending_close') and self.pending_close:
            if not self.position:
                # Position closed successfully, clear flag
                self.pending_close = False
                print("DEBUG: Close operation completed, clearing pending_close flag")
            else:
                # Still waiting for close to complete
                return
        
        # Track current bar information
        dt = bt.num2date(self.data.datetime[0])
        current_bar = len(self)
        current_close = float(self.data.close[0])
        
        # Track position state changes
        if self.position:
            self._was_in_position = True
        elif hasattr(self, '_was_in_position'):
            delattr(self, '_was_in_position')
        
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
                    
            if orders_canceled > 0:
                if self.p.print_signals:
                    print(f"CLEANUP: Canceled {orders_canceled} phantom orders")
            
            # Reset pullback state when no position (fresh start)
            if orders_canceled > 0:
                self._reset_entry_state()

        # Check if we have pending ENTRY orders (but allow protective orders)
        if self.order:
            return  # Wait for entry order to complete before doing anything else

        # =====================================================================
        # POSITION MANAGEMENT SECTION
        # =====================================================================
        if self.position:
            # Check exit conditions
            bars_since_entry = len(self) - self.last_entry_bar if self.last_entry_bar is not None else 0
            
            # Track position (Long-Only strategy)
            position_direction = 'LONG'
            
            # Continue holding - no new entry logic when in position
            return

        # =====================================================================
        # ENTRY LOGIC SECTION - NEW 4-PHASE VOLATILITY EXPANSION SYSTEM
        # =====================================================================
        
        # Pine Script prevention: No entry if exit was taken on same bar
        if self.exit_this_bar:
            if self.p.print_signals:
                print(f"SKIP entry: exit action already taken this bar")
            return
        
        # =====================================================================
        # 4-PHASE STATE MACHINE ENTRY SYSTEM
        # =====================================================================
        
        # GLOBAL INVALIDATION RULE: Reset armed states if opposing EMA crossover occurs
        if self.entry_state == "ARMED_LONG":
            opposing_signal = None
            
            # Check for bearish signal that would invalidate LONG setup
            try:
                prev_bear = self.data.close[-1] < self.data.open[-1]
                cross_fast = self._cross_below(self.ema_confirm, self.ema_fast)
                cross_medium = self._cross_below(self.ema_confirm, self.ema_medium) 
                cross_slow = self._cross_below(self.ema_confirm, self.ema_slow)
                if prev_bear and (cross_fast or cross_medium or cross_slow):
                    opposing_signal = "SHORT"
            except IndexError:
                pass
            
            if opposing_signal:
                if self.p.print_signals:
                    print(f"GLOBAL INVALIDATION: {opposing_signal} signal detected, resetting {self.entry_state}")
                self._reset_entry_state()

        # STATE MACHINE ROUTER
        if self.entry_state == "SCANNING":
            # PHASE 1: Scan for initial signal
            signal_direction = self._phase1_scan_for_signal()
            if signal_direction:
                # Transition to ARMED state
                self.entry_state = f"ARMED_{signal_direction}"
                self.armed_direction = signal_direction
                self.pullback_candle_count = 0
                
                # CRITICAL FIX: Store the original signal candle for validation
                self.signal_trigger_candle = {
                    'open': float(self.data.open[-1]),
                    'close': float(self.data.close[-1]),
                    'high': float(self.data.high[-1]),
                    'low': float(self.data.low[-1]),
                    'datetime': self.data.datetime.datetime(-1),
                    'is_bullish': self.data.close[-1] > self.data.open[-1],
                    'is_bearish': self.data.close[-1] < self.data.open[-1]
                }
                
                if self.p.print_signals:
                    print(f"STATE TRANSITION: SCANNING -> ARMED_{signal_direction} at {dt:%Y-%m-%d %H:%M}")
                    print(f"   Signal detection candle: close[-1]={self.data.close[-1]:.5f} open[-1]={self.data.open[-1]:.5f}")
                    print(f"   Bearish previous candle: {self.data.close[-1] < self.data.open[-1]}")
                    print(f"   Starting pullback confirmation phase...")
                
        elif self.entry_state == "ARMED_LONG":
            # PHASE 2: Confirm pullback
            if self._phase2_confirm_pullback(self.armed_direction):
                # Transition to WINDOW_OPEN state
                self.entry_state = "WINDOW_OPEN"
                self._phase3_open_breakout_window(self.armed_direction)
                if self.p.print_signals:
                    print(f"STATE TRANSITION: ARMED_LONG -> WINDOW_OPEN at {dt:%Y-%m-%d %H:%M}")
                    print(f"   Pullback complete, window monitoring begins...")
                
        elif self.entry_state == "WINDOW_OPEN":
            # PHASE 4: Monitor window for breakout
            breakout_status = self._phase4_monitor_window(self.armed_direction)
            
            if breakout_status == 'SUCCESS':
                # BREAKOUT DETECTED - VALIDATE TIME FILTER BEFORE ENTRY
                # Check time range filter for final entry execution
                if not self._is_in_trading_time_range(dt):
                    if self.p.print_signals:
                        print(f"[X] ENTRY BLOCKED: Breakout detected but outside trading hours - {dt.hour:02d}:{dt.minute:02d} outside {self.p.entry_start_hour:02d}:{self.p.entry_start_minute:02d}-{self.p.entry_end_hour:02d}:{self.p.entry_end_minute:02d} UTC")
                    self._reset_entry_state()
                    return
                
                # EXECUTE ENTRY
                signal_direction = self.armed_direction
                
                # CRITICAL: Validate against ORIGINAL signal trigger candle, not current previous candle
                if hasattr(self, 'signal_trigger_candle') and self.signal_trigger_candle:
                    trigger_candle = self.signal_trigger_candle
                    candle_body = abs(trigger_candle['close'] - trigger_candle['open'])
                    min_body_size = 0.00001
                    
                    # Use stored trigger candle colors
                    current_prev_candle_bullish = trigger_candle['is_bullish'] and candle_body >= min_body_size
                    
                else:
                    # Fallback to current previous candle if trigger candle not stored
                    prev_close = self.data.close[-1]
                    prev_open = self.data.open[-1]
                    candle_body = abs(prev_close - prev_open)
                    min_body_size = 0.00001
                    
                    current_prev_candle_bullish = (prev_close > prev_open) and (candle_body >= min_body_size)
                    
                    if self.p.print_signals:
                        print(f"[!] FALLBACK: Using current previous candle for validation")
                
                # Validate previous candle color matches signal direction (optional)
                candle_direction_valid = True
                
                if signal_direction == 'LONG' and self.p.long_use_candle_direction_filter:
                    if not current_prev_candle_bullish:
                        candle_direction_valid = False
                        if self.p.print_signals:
                            trigger_close = trigger_candle['close']
                            trigger_open = trigger_candle['open']
                            print(f"[X] LONG ENTRY BLOCKED: Previous candle is not bullish (close[-1]={trigger_close:.5f} open[-1]={trigger_open:.5f} body={candle_body:.5f})")
                        self._reset_entry_state()
                        return
                
                # CRITICAL FIX: Calculate ATR change BEFORE validation so it can be used in filters
                # Get current ATR and compare with signal detection ATR if available
                current_atr = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
                
                if hasattr(self, 'signal_detection_atr') and self.signal_detection_atr is not None:
                    self.entry_atr_increment = current_atr - self.signal_detection_atr
                    self.entry_signal_detection_atr = self.signal_detection_atr
                else:
                    self.entry_atr_increment = None
                    self.entry_signal_detection_atr = None

                # CRITICAL FIX: Validate ALL entry filters BEFORE any entry execution
                if signal_direction == 'LONG':
                    if not self._validate_all_entry_filters():
                        if self.p.print_signals:
                            print(f"[X] ENTRY BLOCKED: LONG entry validation failed (angle/ATR filters)")
                        self._reset_entry_state()
                        return
                
                if self.p.print_signals:
                    print(f"[OK] PULLBACK ENTRY VALIDATION PASSED: {signal_direction} with prev candle bullish={current_prev_candle_bullish} body={candle_body:.5f}")
                
                # FINAL TIME FILTER CHECK: Ensure no entries outside trading hours
                dt = bt.num2date(self.data.datetime[0])
                if not self._is_in_trading_time_range(dt):
                    if self.p.print_signals:
                        print(f"[X] ENTRY BLOCKED: {signal_direction} entry rejected - {dt.hour:02d}:{dt.minute:02d} outside {self.p.entry_start_hour:02d}:{self.p.entry_start_minute:02d}-{self.p.entry_end_hour:02d}:{self.p.entry_end_minute:02d} UTC")
                    self._reset_entry_state()
                    return
                
                # Calculate position size and create order
                atr_now = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
                if atr_now <= 0:
                    self._reset_entry_state()
                    return

                entry_price = float(self.data.close[0])
                bar_low = float(self.data.low[0])
                bar_high = float(self.data.high[0])
                
                # Set stop and take levels based on signal direction
                if signal_direction == 'LONG':
                    self.stop_level = bar_low - atr_now * self.p.long_atr_sl_multiplier
                    self.take_level = bar_high + atr_now * self.p.long_atr_tp_multiplier
                
                self.initial_stop_level = self.stop_level

                # Position sizing calculation
                if self.p.enable_risk_sizing:
                    if signal_direction == 'LONG':
                        raw_risk = entry_price - self.stop_level
                        
                    if raw_risk <= 0:
                        self._reset_entry_state()
                        return
                    equity = self.broker.get_value()
                    risk_val = equity * self.p.risk_percent
                    risk_per_contract = raw_risk * self.p.contract_size
                    if risk_per_contract <= 0:
                        self._reset_entry_state()
                        return
                    contracts = max(int(risk_val / risk_per_contract), 1)
                else:
                    contracts = int(self.p.size)
                
                if contracts <= 0:
                    self._reset_entry_state()
                    return
                    
                bt_size = contracts * self.p.contract_size

                # Place market order based on signal direction
                if signal_direction == 'LONG':
                    self.order = self.buy(size=bt_size)
                    signal_type_display = " LONG BUY"

                # Print entry confirmation
                if self.p.print_signals:
                    if signal_direction == 'LONG':
                        rr = (self.take_level - entry_price) / (entry_price - self.stop_level) if (entry_price - self.stop_level) > 0 else float('nan')
                    
                    print(f">>> VOLATILITY EXPANSION ENTRY{signal_type_display} {dt:%Y-%m-%d %H:%M} price={entry_price:.5f} size={bt_size} SL={self.stop_level:.5f} TP={self.take_level:.5f} RR={rr:.2f}")

                # Record trade entry for reporting
                self._record_trade_entry(signal_direction, dt, entry_price, bt_size, atr_now)

                self.last_entry_price = entry_price
                self.last_entry_bar = current_bar
                
                # Reset state machine after entry
                self._reset_entry_state()
                
                # Reset signal tracking variables AFTER trade recording is complete
                self._reset_signal_tracking()

    def _validate_all_entry_filters(self):
        """Validate all entry filters (3-6) for pullback entry"""
        # 3. EMA order condition
        if self.p.long_use_ema_order_condition:
            ema_order_ok = (
                self.ema_confirm[0] > self.ema_fast[0] and
                self.ema_confirm[0] > self.ema_medium[0] and
                self.ema_confirm[0] > self.ema_slow[0]
            )
            if not ema_order_ok:
                return False

        # 4. Price filter EMA
        if self.p.long_use_price_filter_ema:
            price_above_filter = self.data.close[0] > self.ema_filter_price[0]
            if not price_above_filter:
                return False
        
        # 4.5. EMA position filter (LONG: all EMAs below price)
        if self.p.long_use_ema_below_price_filter:
            emas_below_price = (
                self.ema_fast[0] < self.data.close[0] and
                self.ema_medium[0] < self.data.close[0] and
                self.ema_slow[0] < self.data.close[0]
            )
            if not emas_below_price:
                return False

        # 5. Angle filter
        if self.p.long_use_angle_filter:
            current_angle = self._angle()
            angle_ok = self.p.long_min_angle <= current_angle <= self.p.long_max_angle
            if self.p.verbose_debug:
                print(f"[DEBUG] ANGLE VALIDATION DEBUG - LONG Pullback Entry:")
                print(f"   Current Angle: {current_angle:.2f} deg")
                print(f"   Required Range: {self.p.long_min_angle:.1f} to {self.p.long_max_angle:.1f} deg")
                print(f"   [OK] Angle OK: {angle_ok}")
            if not angle_ok:
                if self.p.verbose_debug:
                    print(f"[X] ANGLE FILTER REJECTED: LONG entry blocked - angle {current_angle:.2f} degrees outside range [{self.p.long_min_angle:.1f}, {self.p.long_max_angle:.1f}]")
                return False

        # 6. ATR Increment/Decrement Filter
        if hasattr(self, 'entry_atr_increment') and self.entry_atr_increment is not None:
            increment = self.entry_atr_increment
            
            # Increment Filter (Positive change)
            if increment > 0 and self.p.long_use_atr_increment_filter:
                if not (self.p.long_atr_increment_min_threshold <= increment <= self.p.long_atr_increment_max_threshold):
                    if self.p.print_signals:
                        print(f"[X] ATR INCREMENT FILTER: Blocked {increment:.6f} (Range: {self.p.long_atr_increment_min_threshold:.6f}-{self.p.long_atr_increment_max_threshold:.6f})")
                    return False
            
            # Decrement Filter (Negative change)
            if increment < 0 and self.p.long_use_atr_decrement_filter:
                if not (self.p.long_atr_decrement_min_threshold <= increment <= self.p.long_atr_decrement_max_threshold):
                    if self.p.print_signals:
                        print(f"[X] ATR DECREMENT FILTER: Blocked {increment:.6f} (Range: {self.p.long_atr_decrement_min_threshold:.6f}-{self.p.long_atr_decrement_max_threshold:.6f})")
                    return False

        return True
    
    def _reset_pullback_state(self):
        """Reset pullback state machine to initial state but preserve tracking variables"""
        self.pullback_state = "NORMAL"
        # Reset LONG pullback variables
        self.pullback_red_count = 0
        self.first_red_high = None
        # Reset common variables (but preserve tracking variables for trade recording)
        self.breakout_target = None
        # Reset ATR tracking variables
        self.pullback_start_atr = None
        # NOTE: Do NOT reset entry_window_start, signal_detection_bar, signal_detection_atr
        # These are needed for accurate "Bars to Entry" calculation in trade reports

    def _reset_signal_tracking(self):
        """Reset signal tracking variables after trade recording is complete"""
        self.entry_window_start = None
        self.signal_detection_bar = None
        self.signal_detection_atr = None

    def notify_order(self, order):
        """Enhanced order notification with robust OCA group for SL/TP supporting LONG positions."""
        dt = bt.num2date(self.data.datetime[0])

        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status == order.Completed:
            # Determine if this is an entry or exit order
            if order == self.order:  # This is our main entry order
                # Entry order completed
                self.last_entry_price = order.executed.price
                self.last_entry_bar = len(self)
                
                if order.isbuy():
                    # LONG position entry (BUY order)
                    entry_type = " LONG BUY"
                    if self.p.print_signals:
                        print(f"[OK] {entry_type} EXECUTED at {order.executed.price:.5f} size={order.executed.size}")

                    # Place protective orders (SELL SL/TP for LONG position)
                    if self.stop_level and self.take_level:
                        self.stop_order = self.sell(
                            size=order.executed.size,
                            exectype=bt.Order.Stop,
                            price=self.stop_level,
                            oco=self.limit_order  # Link to TP order
                        )
                        self.limit_order = self.sell(
                            size=order.executed.size,
                            exectype=bt.Order.Limit,
                            price=self.take_level,
                            oco=self.stop_order  # Link to SL order
                        )
                        if self.p.print_signals:
                            print(f"[SHIELD] LONG PROTECTIVE OCA ORDERS: SL={self.stop_level:.5f} TP={self.take_level:.5f}")
                
                self.order = None

            else:
                # Exit order completed (SL/TP or manual close)
                exit_price = order.executed.price
                
                # Determine exit reason
                exit_reason = "UNKNOWN"
                if order.exectype == bt.Order.Stop:
                    exit_reason = "STOP_LOSS"
                elif order.exectype == bt.Order.Limit:
                    exit_reason = "TAKE_PROFIT"
                else:
                    exit_reason = "MANUAL_CLOSE"
                
                self.last_exit_reason = exit_reason
                
                # Determine position direction that was closed
                position_type = "LONG"
                
                if self.p.print_signals:
                    print(f"[EXIT] {position_type} EXIT EXECUTED at {exit_price:.5f} size={order.executed.size} reason={exit_reason}")

                # Reset all state variables to ensure a clean slate for the next trade
                self.stop_order = None
                self.limit_order = None
                self.order = None
                self.stop_level = None
                self.take_level = None
                self.initial_stop_level = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # With OCA, one of the two protective orders will always be canceled
            # when the other one executes. This is normal and expected.
            # We only need to log if it's unexpected.
            is_expected_cancel = (self.stop_order and self.limit_order)
            if not is_expected_cancel and self.p.print_signals:
                print(f"Order {order.getstatusname()}: {order.ref}")
            
            # Clean up references
            if self.order and order.ref == self.order.ref: self.order = None
            if self.stop_order and order.ref == self.stop_order.ref: self.stop_order = None
            if self.limit_order and order.ref == self.limit_order.ref: self.limit_order = None

    def notify_trade(self, trade):
        """Use Backtrader's proper trade notification for accurate PnL tracking"""
        
        if not trade.isclosed:
            return

        dt = bt.num2date(self.data.datetime[0])
        
        # Get accurate PnL from Backtrader
        pnl = trade.pnlcomm
        
        # Calculate entry and exit prices from PnL and trade data
        entry_price = self.last_entry_price if self.last_entry_price else 0
        position_direction = 'LONG'  # Long-Only strategy
        
        if entry_price > 0 and trade.size != 0:
            # Calculate exit price from PnL
            if position_direction == 'LONG':
                # LONG: exit = entry + (pnl / size)
                exit_price = entry_price + (pnl / trade.size)
            else:
                # LONG: exit = entry + (pnl / size)
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
                exit_reason = "STOP_LOSS"
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
        
        # Store trade for yearly stats (advanced metrics)
        self._trade_pnls.append({
            'date': dt,
            'year': dt.year,
            'month': dt.month,
            'pnl': pnl,
            'is_winner': pnl > 0
        })

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
            # Calculate pips (Long-Only)
            pips = (exit_price - entry_price) / self.p.forex_pip_value if self.p.forex_pip_value and entry_price > 0 else 0
            
            print(f"LONG TRADE CLOSED {dt:%Y-%m-%d %H:%M} reason={exit_reason} PnL={pnl:.2f} Pips={pips:.1f}")
            print(f"  Entry: {entry_price:.5f} -> Exit: {exit_price:.5f} | Size: {trade.size}")

        # Record trade exit for reporting
        self._record_trade_exit(dt, exit_price, pnl, exit_reason)

        # Reset levels
        self.stop_level = None
        self.take_level = None
        self.initial_stop_level = None
        
        # Reset pullback state after trade completion
        if self.p.long_use_pullback_entry:
            self._reset_pullback_state()

    def stop(self):
        """Strategy end - print summary with advanced metrics."""
        # Close any open positions at strategy end
        if self.position:
            current_price = self.data.close[0]
            entry_price = self.position.price
            position_size = self.position.size
            
            price_diff = current_price - entry_price
            unrealized_pnl = position_size * price_diff
            
            if self.p.print_signals:
                print(f"STRATEGY END: Closing open position.")
                print(f"  Size: {position_size}, Entry: {entry_price:.5f}, Current: {current_price:.5f}")
                print(f"  Unrealized PnL: {unrealized_pnl:+.2f}")
            
            self.trades += 1
            if unrealized_pnl > 0:
                self.wins += 1
                self.gross_profit += unrealized_pnl
            else:
                self.losses += 1
                self.gross_loss += abs(unrealized_pnl)
            
            self.order = self.close()
            
            if self.stop_order:
                self.cancel(self.stop_order)
                self.stop_order = None
            if self.limit_order:
                self.cancel(self.limit_order)
                self.limit_order = None
        
        # Calculate basic metrics
        win_rate = (self.wins / self.trades * 100) if self.trades > 0 else 0
        profit_factor = (self.gross_profit / self.gross_loss) if self.gross_loss > 0 else float('inf')
        
        final_value = self.broker.get_value()
        # Use actual initial cash (supports dual-strategy mode with split capital)
        initial_cash = self._initial_cash if self._initial_cash else STARTING_CASH
        total_pnl = final_value - initial_cash
        
        # =================================================================
        # ADVANCED METRICS: Drawdown, Sharpe Ratio
        # =================================================================
        max_drawdown_pct = 0.0
        sharpe_ratio = 0.0
        
        if hasattr(self, '_portfolio_values') and len(self._portfolio_values) > 1:
            peak = self._portfolio_values[0]
            for value in self._portfolio_values:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak * 100.0
                if drawdown > max_drawdown_pct:
                    max_drawdown_pct = drawdown
        
        if hasattr(self, '_portfolio_values') and len(self._portfolio_values) > 10:
            returns = []
            for i in range(1, len(self._portfolio_values)):
                ret = (self._portfolio_values[i] - self._portfolio_values[i-1]) / self._portfolio_values[i-1]
                returns.append(ret)
            
            if len(returns) > 0:
                returns_array = np.array(returns)
                mean_return = np.mean(returns_array)
                std_return = np.std(returns_array)
                periods_per_year = 252 * 24 * 12  # 5-minute periods per year
                if std_return > 0:
                    sharpe_ratio = (mean_return * periods_per_year) / (std_return * np.sqrt(periods_per_year))
        
        # =================================================================
        # ADVANCED METRICS: CAGR, Sortino, Calmar, Monte Carlo
        # =================================================================
        cagr = 0.0
        sortino_ratio = 0.0
        calmar_ratio = 0.0
        monte_carlo_dd_95 = 0.0
        monte_carlo_dd_99 = 0.0
        
        # Calculate CAGR
        if hasattr(self, '_portfolio_values') and len(self._portfolio_values) > 1 and initial_cash > 0:
            total_return = final_value / initial_cash
            if hasattr(self, '_trade_pnls') and self._trade_pnls:
                first_date = self._trade_pnls[0]['date']
                last_date = self._trade_pnls[-1]['date']
                days = (last_date - first_date).days
                years = max(days / 365.25, 0.1)
            else:
                years = len(self._portfolio_values) / (252 * 24 * 12)
                years = max(years, 0.1)
            
            if total_return > 0:
                cagr = (pow(total_return, 1.0 / years) - 1.0) * 100.0
        
        # Calculate Sortino Ratio
        if hasattr(self, '_portfolio_values') and len(self._portfolio_values) > 10:
            returns = []
            for i in range(1, len(self._portfolio_values)):
                ret = (self._portfolio_values[i] - self._portfolio_values[i-1]) / self._portfolio_values[i-1]
                returns.append(ret)
            
            if len(returns) > 0:
                returns_array = np.array(returns)
                mean_return = np.mean(returns_array)
                negative_returns = returns_array[returns_array < 0]
                if len(negative_returns) > 0:
                    downside_dev = np.std(negative_returns)
                    periods_per_year = 252 * 24 * 12
                    if downside_dev > 0:
                        sortino_ratio = (mean_return * periods_per_year) / (downside_dev * np.sqrt(periods_per_year))
        
        # Calculate Calmar Ratio
        if max_drawdown_pct > 0:
            calmar_ratio = cagr / max_drawdown_pct
        
        # Monte Carlo Simulation
        if hasattr(self, '_trade_pnls') and len(self._trade_pnls) >= 20:
            n_simulations = 10000
            pnl_list = [t['pnl'] for t in self._trade_pnls]
            mc_max_drawdowns = []
            
            for _ in range(n_simulations):
                shuffled_pnl = np.random.permutation(pnl_list)
                equity = initial_cash
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
        # YEARLY STATISTICS WITH SHARPE/SORTINO
        # =================================================================
        yearly_stats = defaultdict(lambda: {
            'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0,
            'gross_profit': 0.0, 'gross_loss': 0.0, 'pnls': []
        })
        
        if hasattr(self, '_trade_pnls'):
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
        
        # =================================================================
        # PRINT SUMMARY
        # =================================================================
        print("\n" + "=" * 70)
        print("=== SUNRISE OGLE STRATEGY SUMMARY ===")
        print("=" * 70)
        
        # Commission info
        if USE_FIXED_COMMISSION:
            real_calls = ForexCommission.commission_calls
            real_total = ForexCommission.total_commission
            total_lots = ForexCommission.total_lots
            avg_commission_per_trade = real_total / self.trades if self.trades > 0 else 0
            print(f"Commission: ${COMMISSION_PER_LOT_PER_ORDER:.2f}/lot/order (Darwinex Zero)")
            print(f"Total commission: ${real_total:,.2f} | Avg per trade: ${avg_commission_per_trade:.2f}")
        else:
            print("Commission: DISABLED")
        
        print(f"Total Trades: {self.trades}")
        print(f"Wins: {self.wins} | Losses: {self.losses}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Profit Factor: {profit_factor:.2f}")
        print(f"Gross Profit: {self.gross_profit:,.2f}")
        print(f"Gross Loss: {self.gross_loss:,.2f}")
        print(f"Net P&L: {total_pnl:,.2f}")
        print(f"Final Value: {final_value:,.2f}")
        
        # Advanced Metrics with quality indicators
        print(f"\n{'='*70}")
        print("ADVANCED RISK METRICS")
        print(f"{'='*70}")
        
        sharpe_status = "Poor" if sharpe_ratio < 0.5 else "Marginal" if sharpe_ratio < 1.0 else "Good" if sharpe_ratio < 2.0 else "Excellent"
        print(f"Sharpe Ratio:    {sharpe_ratio:>8.2f}  [{sharpe_status}]")
        
        sortino_status = "Poor" if sortino_ratio < 0.5 else "Marginal" if sortino_ratio < 1.0 else "Good" if sortino_ratio < 2.0 else "Excellent"
        print(f"Sortino Ratio:   {sortino_ratio:>8.2f}  [{sortino_status}]")
        
        cagr_status = "Below Market" if cagr < 8 else "Market-level" if cagr < 12 else "Good" if cagr < 20 else "Exceptional"
        print(f"CAGR:            {cagr:>7.2f}%  [{cagr_status}]")
        
        dd_status = "Excellent" if max_drawdown_pct < 10 else "Acceptable" if max_drawdown_pct < 20 else "High" if max_drawdown_pct < 30 else "Dangerous"
        print(f"Max Drawdown:    {max_drawdown_pct:>7.2f}%  [{dd_status}]")
        
        calmar_status = "Poor" if calmar_ratio < 0.5 else "Acceptable" if calmar_ratio < 1.0 else "Good" if calmar_ratio < 2.0 else "Excellent"
        print(f"Calmar Ratio:    {calmar_ratio:>8.2f}  [{calmar_status}]")
        
        if monte_carlo_dd_95 > 0:
            mc_ratio = monte_carlo_dd_95 / max_drawdown_pct if max_drawdown_pct > 0 else 0
            mc_status = "Good" if mc_ratio < 1.5 else "Caution" if mc_ratio < 2.0 else "Warning"
            print(f"\nMonte Carlo Analysis (10,000 simulations):")
            print(f"  95th Percentile DD: {monte_carlo_dd_95:>6.2f}%  [{mc_status}]")
            print(f"  99th Percentile DD: {monte_carlo_dd_99:>6.2f}%")
            print(f"  Historical vs MC95: {mc_ratio:.2f}x")
        
        print(f"{'='*70}")
        
        # Yearly Statistics
        if yearly_stats:
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
        self._close_trade_reporting()
    
    def _cancel_all_pending_orders(self):
        """Cancel all pending orders to ensure clean state"""
        try:
            if self.order:
                self.broker.cancel(self.order)
                self.order = None
            if self.stop_order:
                self.broker.cancel(self.stop_order)
                self.stop_order = None
            if self.limit_order:
                self.broker.cancel(self.limit_order)
                self.limit_order = None
            print("DEBUG: All pending orders cancelled")
        except Exception as e:
            print(f"Error cancelling orders: {e}")

    def _is_in_trading_time_range(self, dt):
        """Check if current time is within allowed trading hours (UTC)"""
        if not self.p.use_time_range_filter:
            return True
            
        current_hour = dt.hour
        current_minute = dt.minute
        
        # Convert to total minutes for easier comparison
        current_time_minutes = current_hour * 60 + current_minute
        start_time_minutes = self.p.entry_start_hour * 60 + self.p.entry_start_minute
        end_time_minutes = self.p.entry_end_hour * 60 + self.p.entry_end_minute
        
        # Check if current time is within the allowed range
        if start_time_minutes <= end_time_minutes:
            # Normal case: start time is before end time (same day)
            return start_time_minutes <= current_time_minutes <= end_time_minutes
        else:
            # Edge case: range crosses midnight (e.g., 22:00 to 06:00)
            return current_time_minutes >= start_time_minutes or current_time_minutes <= end_time_minutes

if __name__ == '__main__':
    from datetime import datetime, timedelta

    if QUICK_TEST:
        try:
            td_obj = datetime.strptime(TODATE, '%Y-%m-%d')
            FROMDATE = (td_obj - timedelta(days=10)).strftime('%Y-%m-%d')
        except Exception:
            pass

    class SLTPObserver(bt.Observer):
        """Stop Loss and Take Profit Observer for plotting SL/TP levels on chart."""
        lines = ('sl','tp',)
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
    
    BASE = Path(__file__).resolve().parent.parent.parent
    DATA_FILE = BASE / 'data' / DATA_FILENAME
    STRAT_KWARGS = dict(
        plot_result=ENABLE_PLOT,
        use_forex_position_calc=ENABLE_FOREX_CALC,
        forex_instrument=FOREX_INSTRUMENT
    )
    
    if TEST_FOREX_MODE:
        try:
            td_obj = datetime.strptime(TODATE, '%Y-%m-%d')
            FROMDATE = (td_obj - timedelta(days=30)).strftime('%Y-%m-%d')
            print(f"FOREX TEST MODE: Testing period reduced to {FROMDATE} - {TODATE}")
        except Exception:
            pass

    def parse_date(s):
        if not s: return None
        try: return datetime.strptime(s, '%Y-%m-%d')
        except Exception: return None

    if not DATA_FILE.exists():
        print(f"Data file not found: {DATA_FILE}")
        raise SystemExit(1)

    # CSV format: Date,Time,Open,High,Low,Close,Volume (Darwinex format)
    feed_kwargs = dict(
        dataname=str(DATA_FILE),
        dtformat='%Y%m%d',
        tmformat='%H:%M:%S',
        datetime=0,
        time=1,
        open=2,
        high=3,
        low=4,
        close=5,
        volume=6,
        timeframe=bt.TimeFrame.Minutes,
        compression=5
    )
    fd = parse_date(FROMDATE)
    td = parse_date(TODATE)
    if fd: feed_kwargs['fromdate'] = fd
    if td: feed_kwargs['todate'] = td
    data = bt.feeds.GenericCSVData(**feed_kwargs)

    cerebro = bt.Cerebro(stdstats=False)
    cerebro.adddata(data)
    cerebro.broker.setcash(STARTING_CASH)
    
    # Apply Darwinex Zero commission structure
    if USE_FIXED_COMMISSION:
        is_jpy = 'JPY' in FOREX_INSTRUMENT
        cerebro.broker.addcommissioninfo(
            ForexCommission(
                commission=COMMISSION_PER_LOT_PER_ORDER,
                is_jpy_pair=is_jpy,
                jpy_rate=150.0 if is_jpy else 1.0
            )
        )
        print(f"Commission: ${COMMISSION_PER_LOT_PER_ORDER:.2f}/lot/order (Darwinex Zero)")
    else:
        cerebro.broker.setcommission(leverage=30.0)
    
    cerebro.addstrategy(SunriseOgle, **STRAT_KWARGS)
    
    try:
        cerebro.addobserver(bt.observers.BuySell, barplot=False, plotdist=SunriseOgle.params.buy_sell_plotdist)
    except Exception:
        pass
    
    if PLOT_SLTP_LINES:
        try:
            cerebro.addobserver(SLTPObserver)
        except Exception:
            pass
    
    try:
        cerebro.addobserver(bt.observers.Value)
    except Exception:
        pass

    if LIMIT_BARS > 0:
        orig_next = SunriseOgle.next
        def limited_next(self):
            if len(self.data) >= LIMIT_BARS:
                self.env.runstop()
                return
            orig_next(self)
        SunriseOgle.next = limited_next

    print(f"\n{'='*70}")
    print(f"=== SUNRISE OGLE TEMPLATE === ({FOREX_INSTRUMENT})")
    print(f"{'='*70}")
    print(f"Period: {FROMDATE} to {TODATE}")
    print(f"Data: {DATA_FILENAME}")
    print(f"Starting Cash: ${STARTING_CASH:,.0f}")
    print(f"Risk per trade: {RISK_PERCENT*100:.2f}%")
    print(f"SL: {LONG_ATR_SL_MULTIPLIER}x ATR | TP: {LONG_ATR_TP_MULTIPLIER}x ATR")
    print(f"Time Filter: {ENTRY_START_HOUR:02d}:00-{ENTRY_END_HOUR:02d}:00 UTC" if USE_TIME_RANGE_FILTER else "Time Filter: DISABLED")
    print(f"{'='*70}\n")

    results = cerebro.run()
    final_value = cerebro.broker.getvalue()
    
    # Enhanced plotting
    if ENABLE_PLOT:
        trading_mode = "LONG-ONLY"
        
        if getattr(results[0].p, 'plot_result', False):
            try:
                strategy_result = results[0]
                final_pnl = final_value - STARTING_CASH
                plot_title = f'SUNRISE OGLE ({FOREX_INSTRUMENT} - {trading_mode})\n'
                plot_title += f'Final Value: ${final_value:,.0f} | P&L: {final_pnl:+,.0f} | '
                plot_title += f'Trades: {strategy_result.trades} | Win Rate: {(strategy_result.wins/strategy_result.trades*100) if strategy_result.trades > 0 else 0:.1f}%'
                
                print(f"[CHART] Showing {FOREX_INSTRUMENT} strategy chart...")
                cerebro.plot(style='candlestick', subtitle=plot_title)
            except Exception as e: 
                print(f"Plot error: {e}")
        else:
            print(f"[INFO] Plotting disabled. Set ENABLE_PLOT=True to show charts.")
