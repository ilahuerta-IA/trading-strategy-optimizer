"""Advanced Sunrise Strategy - USDJPY Trading System
==================================================
USDJPY VERSION: This is a specialized version optimized exclusively for USDJPY trading.
Adapted from the original strategy with JPY-specific parameters and configurations.

This strategy implements a sophisticated trading system optimized for USDJPY with the following features:

ENTRY MODES
-----------
> TRADING DIRECTION:
  - LONG ONLY: Buy entries when uptrend conditions met
  - SHORT ONLY: Sell entries when downtrend conditions met  
  - BOTH: Enable long and short trading simultaneously
  
> ENTRY PRIORITY (when both LONG and SHORT conditions are met):
  - LONG signals are checked FIRST and take priority
  - If LONG conditions are met, SHORT conditions are ignored for that bar
  - Only one position allowed at a time - conflicts result in position closure

> STANDARD MODE (use_pullback_entry=False):
  Direct entry when all conditions align simultaneously

> VOLATILITY EXPANSION CHANNEL ENTRY SYSTEM (use_pullback_entry=True) - RECOMMENDED:
  ADVANCED 4-PHASE STATE MACHINE for superior entry timing:
  
  PHASE 1 - SIGNAL SCANNING:
  - Monitor for EMA crossovers + directional candle confirmation
  - State: SCANNING -> ARMED_LONG/ARMED_SHORT
  
  PHASE 2 - PULLBACK CONFIRMATION:
  - Wait for specified pullback candles (long_pullback_max_candles/short_pullback_max_candles)
  - LONG: Wait 1-3 red candles after bullish signal
  - SHORT: Wait 1-3 green candles after bearish signal
  - Global Invalidation Rule: Reset if opposing signal appears
  
  PHASE 3 - BREAKOUT WINDOW OPENING:
  - Calculate breakout window with configurable offset
  - Set precise price levels for breakout detection
  - Window duration: long_entry_window_periods/short_entry_window_periods
  - Window offset: pullback_count x window_offset_multiplier
  
  PHASE 4 - BREAKOUT MONITORING:
  - Monitor for actual price breakout above/below window levels
  - LONG: Enter when high breaks above stored breakout level
  - SHORT: Enter when low breaks below stored breakout level
  - Window expiry: Auto-reset if no breakout within window

ENTRY CONDITIONS
----------------
LONG CONDITIONS:
1. ✅ Confirmation EMA crosses ABOVE any of fast/medium/slow EMAs
2. ⚙️ Optional: Previous candle bullish (close[1] > open[1])
3. ⚙️ Optional: EMA ordering filter (confirm > fast & medium & slow)
4. ⚙️ Optional: Price filter (close > filter EMA)
5. ⚙️ Optional: Angle filter (EMA slope > minimum degrees)
6. ⚙️ Optional: ATR volatility filter (minimum ATR + volatility change)

SHORT CONDITIONS:
1. ✅ Confirmation EMA crosses BELOW any of fast/medium/slow EMAs
2. ⚙️ Optional: Previous candle bearish (close[1] < open[1])
3. ⚙️ Optional: EMA ordering filter (confirm < fast & medium & slow)
4. ⚙️ Optional: Price filter (close < filter EMA)
5. ⚙️ Optional: Angle filter (EMA slope < minimum degrees)
6. ⚙️ Optional: ATR volatility filter (minimum ATR + volatility change)

EXIT SYSTEM
-----------
🎯 PRIMARY: ATR-based Stop Loss & Take Profit (OCA orders)
   - LONG: Stop Loss = entry_bar_low - (ATR × 2.5), Take Profit = entry_bar_high + (ATR × 12.0)
   - SHORT: Stop Loss = entry_bar_high + (ATR × 2.5), Take Profit = entry_bar_low - (ATR × 6.5)
   
⚙️ OPTIONAL EXITS:
   - Time-based: Close after N bars in position
   - EMA crossover: Direction-aware exit signals (confirm vs exit EMA)

MULTI-ASSET SUPPORT
-------------------
💴 FOREX: USDJPY (US Dollar vs Japanese Yen)
   - Standard 100,000 unit contract sizes
   - 0.01 pip values (3 decimal places)
   - 30:1 leverage with 2.0% margin

RISK MANAGEMENT
---------------
💰 POSITION SIZING: Risk-based calculation
   - Fixed risk percentage per trade (default 1%)
   - Automatic lot size calculation based on stop loss distance
   - Forex-specific pip value calculations

🛡️ PROTECTIVE ORDERS: One-Cancels-All (OCA) system
   - Simultaneous stop loss and take profit orders
   - Automatic order cancellation when one executes
   - Prevents phantom positions and order conflicts

CONFIGURATION
-------------
📍 All settings moved to TOP of file for easy access:
   - Instrument selection (DATA_FILENAME)
   - Date ranges, cash, plotting options  
   - Trading hours: 7:00-17:00 UTC (configurable)
   - Direction control: LONG/SHORT/BOTH modes
   
DISCLAIMER
----------
Educational and research purposes ONLY. Not investment advice. 
Trading involves substantial risk of loss. Past performance does not 
guarantee future results. Validate all logic and data quality before 
using in any live or simulated trading environment.
"""
from __future__ import annotations
import math
from pathlib import Path
from datetime import datetime, timedelta
import backtrader as bt

# =============================================================
# CONFIGURATION PARAMETERS - EASILY EDITABLE AT TOP OF FILE
# =============================================================

# ⚡⚡⚡ VOLATILITY EXPANSION CHANNEL - QUICK ACCESS ⚡⚡⚡
# 🎯 The most important parameters for fine-tuning entry timing:
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔧 USE_WINDOW_TIME_OFFSET = True         ← Enable/disable time delay (True/False)
# 🔧 WINDOW_OFFSET_MULTIPLIER = 1.0        ← Time delay multiplier (0.5-2.0)
# 🔧 WINDOW_PRICE_OFFSET_MULTIPLIER = 0.5  ← Channel expansion (0.3-1.0)
# 🔧 LONG_PULLBACK_MAX_CANDLES = 1         ← LONG pullback depth (1-3)
# 🔧 SHORT_PULLBACK_MAX_CANDLES = 2        ← SHORT pullback depth (1-3)  
# 🔧 LONG_ENTRY_WINDOW_PERIODS = 7         ← LONG window duration (3-10)
# 🔧 SHORT_ENTRY_WINDOW_PERIODS = 7        ← SHORT window duration (3-10)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# === INSTRUMENT SELECTION ===
# USDJPY version
DATA_FILENAME = 'USDJPY_5m_5Yea.csv'     # 💴 USDJPY - US Dollar vs Japanese Yen

# === BACKTEST SETTINGS ===
FROMDATE = '2023-12-01'               # Start date for backtesting (YYYY-MM-DD)
TODATE = '2025-12-05'                 # End date for backtesting (YYYY-MM-DD)
STARTING_CASH = 100000.0              # Initial account balance in USD
QUICK_TEST = False                    # True: Reduce to last 10 days for quick testing
LIMIT_BARS = 0                        # >0: Stop after N bars processed (0 = no limit)
ENABLE_PLOT = True                    # Show final chart with trades (requires matplotlib)

# === FOREX CONFIGURATION ===
ENABLE_FOREX_CALC = True              # Enable advanced forex position calculations
FOREX_INSTRUMENT = 'USDJPY'           # Fixed to USDJPY
TEST_FOREX_MODE = False               # True: Quick 30-day test with forex calculations

# === TRADING DIRECTION ===
ENABLE_LONG_TRADES = True            # Enable long (buy) entries
ENABLE_SHORT_TRADES = False           # Enable short (sell) entries

# === DUAL CEREBRO MODE ===
RUN_DUAL_CEREBRO = False             # Run separate LONG-only and SHORT-only cerebros to avoid position interference

# === DEBUG SETTINGS ===
VERBOSE_DEBUG = False                 # Print detailed debug info to console (set True only for troubleshooting)

# === TRADE REPORTING ===
EXPORT_TRADE_REPORTS = True          # Export detailed trade reports to temp_reports directory
TRADE_REPORT_ENABLED = True          # Enable trade report generation (simple text format)

# === PLOTTING OPTIONS ===
SHOW_INDIVIDUAL_PLOTS = False         # Show individual LONG/SHORT plots when running dual cerebro
AUTO_PLOT_SINGLE_MODE = False         # Automatically plot in single mode (LONG-only or SHORT-only)

# === LONG ATR VOLATILITY FILTER ===
LONG_USE_ATR_FILTER = False                 # Enable ATR-based volatility filtering for long entries
LONG_ATR_MIN_THRESHOLD = 0.0450          
LONG_ATR_MAX_THRESHOLD = 0.1000        # Reset for USDJPY (typically 0.05-0.20)
# ATR INCREMENT FILTER
LONG_USE_ATR_INCREMENT_FILTER = False       
LONG_ATR_INCREMENT_MIN_THRESHOLD = 0.0020 
LONG_ATR_INCREMENT_MAX_THRESHOLD = 1.0 
# ATR DECREMENT FILTER
LONG_USE_ATR_DECREMENT_FILTER = False        
LONG_ATR_DECREMENT_MIN_THRESHOLD = -0.0150 
LONG_ATR_DECREMENT_MAX_THRESHOLD = -0.0050 

# === SHORT ATR VOLATILITY FILTER ===
SHORT_USE_ATR_FILTER = True                 # Enable ATR-based volatility filtering for short entries  
SHORT_ATR_MIN_THRESHOLD = 0.0         
SHORT_ATR_MAX_THRESHOLD = 1.0         
# ATR INCREMENT FILTER
SHORT_USE_ATR_INCREMENT_FILTER = False      
SHORT_ATR_INCREMENT_MIN_THRESHOLD = 0.0 
SHORT_ATR_INCREMENT_MAX_THRESHOLD = 1.0 
# ATR DECREMENT FILTER 
SHORT_USE_ATR_DECREMENT_FILTER = False       
SHORT_ATR_DECREMENT_MIN_THRESHOLD = -1.0 
SHORT_ATR_DECREMENT_MAX_THRESHOLD = 0.0 

# === LONG ENTRY FILTERS ===
LONG_USE_EMA_ORDER_CONDITION = False        # Require confirm_EMA > all other EMAs for long entries
LONG_USE_PRICE_FILTER_EMA = True            # Require close > filter_EMA (trend alignment) for long entries
LONG_USE_CANDLE_DIRECTION_FILTER = False     # Require previous candle bullish (close[1] > open[1]) for long entries
LONG_USE_ANGLE_FILTER = True                # Require minimum EMA slope angle for long entries
LONG_MIN_ANGLE = 30.0                       
LONG_MAX_ANGLE = 95.0                       
LONG_ANGLE_SCALE_FACTOR = 100.0             # 💴 USDJPY: Scale factor 100.0 (1 pip = 0.01)

# === LONG EMA POSITION FILTER ===
LONG_USE_EMA_BELOW_PRICE_FILTER = False     # NEW: Require fast, medium & slow EMAs below price for long entries

# === SHORT ENTRY FILTERS ===
SHORT_USE_EMA_ORDER_CONDITION = True      # Require confirm_EMA < all other EMAs for short entries
SHORT_USE_PRICE_FILTER_EMA = True           # Require close < filter_EMA (trend alignment) for short entries  
SHORT_USE_CANDLE_DIRECTION_FILTER = True    # Require previous candle bearish (close[1] < open[1]) for short entries
SHORT_USE_ANGLE_FILTER = True               # Require minimum EMA slope angle for short entries
SHORT_MIN_ANGLE = -90.0                     
SHORT_MAX_ANGLE = -20.0                     
SHORT_ANGLE_SCALE_FACTOR = 100.0            # 💴 USDJPY: Scale factor 100.0 (1 pip = 0.01)

# === SHORT EMA POSITION FILTER ===
SHORT_USE_EMA_ABOVE_PRICE_FILTER = False    # NEW: Require fast, medium & slow EMAs above price for short entries

# === LONG PULLBACK ENTRY SYSTEM ===
LONG_USE_PULLBACK_ENTRY = True             # Enable 3-phase pullback entry system for long entries
LONG_PULLBACK_MAX_CANDLES = 2              # Max red candles in pullback for long entries (1-3 recommended)
LONG_ENTRY_WINDOW_PERIODS = 7             # Bars to wait for breakout after pullback (long entries)

# === SHORT PULLBACK ENTRY SYSTEM ===
SHORT_USE_PULLBACK_ENTRY = True            # Enable 3-phase pullback entry system for short entries
SHORT_PULLBACK_MAX_CANDLES = 2             # Max green candles in pullback for short entries (1-3 recommended)
SHORT_ENTRY_WINDOW_PERIODS = 7            # Bars to wait for breakdown after pullback (short entries)

# ===============================================================
# ⚡ VOLATILITY EXPANSION CHANNEL - KEY TIMING PARAMETERS ⚡
# ===============================================================
# 🎯 CRITICAL: These parameters control the advanced entry timing system
# 🔧 USE_WINDOW_TIME_OFFSET: Enable/disable time delay for window opening
USE_WINDOW_TIME_OFFSET = True              # NEW: Enable/disable the time delay for window opening
# 🔧 WINDOW_OFFSET_MULTIPLIER: Controls delay between pullback and window opening (only if USE_WINDOW_TIME_OFFSET=True)
WINDOW_OFFSET_MULTIPLIER = 2.0             # Window delay multiplier (0.5=fast, 1.0=standard, 2.0=conservative)
                                          # Formula: window_start = current_bar + (pullback_count × this_value)
                                          # 🔬 EXPERIMENT: Try 0.5 for aggressive, 1.5 for conservative entries
# 🔧 WINDOW_PRICE_OFFSET_MULTIPLIER: Controls the price expansion of the two-sided channel
WINDOW_PRICE_OFFSET_MULTIPLIER = 0.01      # NEW: Price expansion multiplier (0.5 = 50% of candle range)
                                          # Formula: channel_width = candle_range × this_value
# ===============================================================

# === TIME RANGE FILTER ===
USE_TIME_RANGE_FILTER = False              # ENABLED: Time filter for complete analysis
ENTRY_START_HOUR = 0                       # Start hour for entry window (UTC)
ENTRY_START_MINUTE = 0                     # Start minute for entry window (UTC)
ENTRY_END_HOUR = 23                        # End hour for entry window (UTC)
ENTRY_END_MINUTE = 59                      # End minute for entry window (UTC)


class SunriseOgleUSDJPY(bt.Strategy):
    params = dict(
        # === TECHNICAL INDICATORS ===
        ema_fast_length=14,              # Fast EMA period for trend detection
        ema_medium_length=14,             # Medium EMA period for trend confirmation
        ema_slow_length=24,               # Slow EMA period for trend strength
        ema_confirm_length=1,             # Confirmation EMA (usually 1 for immediate response)
        ema_filter_price_length=70,       # Price filter EMA to avoid counter-trend trades
        ema_exit_length=25,               # Exit EMA for crossover exit strategy
        
        # === ATR RISK MANAGEMENT ===
        atr_length=10,                    # ATR calculation period
        
        # === TRADING DIRECTION ===
        enable_long_trades=ENABLE_LONG_TRADES,  # Enable long (buy) entries
        enable_short_trades=ENABLE_SHORT_TRADES, # Enable short (sell) entries
        
        # === DUAL CEREBRO OVERRIDES ===
        long_enabled=None,                # Override for LONG trades (None=use enable_long_trades)
        short_enabled=None,               # Override for SHORT trades (None=use enable_short_trades)
        
        # === LONG ATR VOLATILITY FILTER ===
        long_use_atr_filter=LONG_USE_ATR_FILTER,    # Enable ATR-based volatility filtering for long entries
        long_atr_min_threshold=LONG_ATR_MIN_THRESHOLD,  # Minimum ATR for long entry
        long_atr_max_threshold=LONG_ATR_MAX_THRESHOLD,  # Maximum ATR for long entry
        # ATR INCREMENT/DECREMENT FILTERS
        long_use_atr_increment_filter=LONG_USE_ATR_INCREMENT_FILTER,  # Enable ATR increment filtering
        long_atr_increment_min_threshold=LONG_ATR_INCREMENT_MIN_THRESHOLD,  # Minimum ATR increment
        long_atr_increment_max_threshold=LONG_ATR_INCREMENT_MAX_THRESHOLD,  # Maximum ATR increment
        long_use_atr_decrement_filter=LONG_USE_ATR_DECREMENT_FILTER,  # Enable ATR decrement filtering
        long_atr_decrement_min_threshold=LONG_ATR_DECREMENT_MIN_THRESHOLD,  # Minimum ATR decrement
        long_atr_decrement_max_threshold=LONG_ATR_DECREMENT_MAX_THRESHOLD,  # Maximum ATR decrement
        
        # === LONG ENTRY FILTERS ===
        long_use_ema_order_condition=LONG_USE_EMA_ORDER_CONDITION,    # Require confirm_EMA > all other EMAs for long entries
        long_use_price_filter_ema=LONG_USE_PRICE_FILTER_EMA,        # Require close > filter_EMA (trend alignment) for long entries
        long_use_candle_direction_filter=LONG_USE_CANDLE_DIRECTION_FILTER, # Require previous candle bullish for long entries
        long_use_angle_filter=LONG_USE_ANGLE_FILTER,            # Require minimum EMA slope angle for long entries
        long_min_angle=LONG_MIN_ANGLE,                   # Minimum angle in degrees for EMA slope (long entries)
        long_max_angle=LONG_MAX_ANGLE,                   # Maximum angle in degrees for EMA slope (long entries)
        long_angle_scale_factor=LONG_ANGLE_SCALE_FACTOR,       # Scaling factor for angle calculation sensitivity (long entries)
        long_use_ema_below_price_filter=LONG_USE_EMA_BELOW_PRICE_FILTER,  # NEW: Require fast, medium & slow EMAs below price for long entries
        long_atr_sl_multiplier=3.5,                          # Stop Loss multiplier for LONG trades
        long_atr_tp_multiplier=6.5,                          # Take Profit multiplier for LONG trades
        
        # === LONG PULLBACK ENTRY SYSTEM ===
        long_use_pullback_entry=LONG_USE_PULLBACK_ENTRY,          # Enable 3-phase pullback entry system for long entries
        long_pullback_max_candles=LONG_PULLBACK_MAX_CANDLES,           # Max red candles in pullback for long entries (1-3 recommended)
        long_entry_window_periods=LONG_ENTRY_WINDOW_PERIODS,          # Bars to wait for breakout after pullback (long entries)
        window_offset_multiplier=WINDOW_OFFSET_MULTIPLIER,        # ⚡ CRITICAL: Volatility expansion window timing control
        use_window_time_offset=USE_WINDOW_TIME_OFFSET,            # ⚡ NEW: Enable/disable time delay for window opening
        window_price_offset_multiplier=WINDOW_PRICE_OFFSET_MULTIPLIER,  # ⚡ NEW: Controls two-sided channel expansion
        
        # === SHORT ATR VOLATILITY FILTER ===
        short_use_atr_filter=SHORT_USE_ATR_FILTER,    # Enable ATR-based volatility filtering for short entries
        short_atr_min_threshold=SHORT_ATR_MIN_THRESHOLD,  # Minimum ATR for short entry
        short_atr_max_threshold=SHORT_ATR_MAX_THRESHOLD,  # Maximum ATR for short entry
        # ATR INCREMENT/DECREMENT FILTERS
        short_use_atr_increment_filter=SHORT_USE_ATR_INCREMENT_FILTER,  # Enable ATR increment filtering
        short_atr_increment_min_threshold=SHORT_ATR_INCREMENT_MIN_THRESHOLD,  # Minimum ATR increment
        short_atr_increment_max_threshold=SHORT_ATR_INCREMENT_MAX_THRESHOLD,  # Maximum ATR increment
        short_use_atr_decrement_filter=SHORT_USE_ATR_DECREMENT_FILTER,  # Enable ATR decrement filtering
        short_atr_decrement_min_threshold=SHORT_ATR_DECREMENT_MIN_THRESHOLD,  # Minimum ATR decrement
        short_atr_decrement_max_threshold=SHORT_ATR_DECREMENT_MAX_THRESHOLD,  # Maximum ATR decrement
        
        # === SHORT ENTRY FILTERS ===
        short_use_ema_order_condition=SHORT_USE_EMA_ORDER_CONDITION,    # Require confirm_EMA < all other EMAs for short entries
        short_use_price_filter_ema=SHORT_USE_PRICE_FILTER_EMA,        # Require close < filter_EMA (trend alignment) for short entries
        short_use_candle_direction_filter=SHORT_USE_CANDLE_DIRECTION_FILTER, # Require previous candle bearish for short entries
        short_use_angle_filter=SHORT_USE_ANGLE_FILTER,            # Require minimum EMA slope angle for short entries
        short_min_angle=SHORT_MIN_ANGLE,                   # Minimum angle in degrees for EMA slope (short entries)
        short_max_angle=SHORT_MAX_ANGLE,                   # Maximum angle in degrees for EMA slope (short entries)
        short_angle_scale_factor=SHORT_ANGLE_SCALE_FACTOR,       # Scaling factor for angle calculation sensitivity (short entries)
        short_use_ema_above_price_filter=SHORT_USE_EMA_ABOVE_PRICE_FILTER,  # NEW: Require fast, medium & slow EMAs above price for short entries
        short_atr_sl_multiplier=2.5,                             # Stop Loss multiplier for SHORT trades
        short_atr_tp_multiplier=7.0,                             # Take Profit multiplier for SHORT trades

        # === SHORT PULLBACK ENTRY SYSTEM ===
        short_use_pullback_entry=SHORT_USE_PULLBACK_ENTRY,          # Enable 3-phase pullback entry system for short entries
        short_pullback_max_candles=SHORT_PULLBACK_MAX_CANDLES,           # Max green candles in pullback for short entries (1-3 recommended)
        short_entry_window_periods=SHORT_ENTRY_WINDOW_PERIODS,          # Bars to wait for breakdown after pullback (short entries)
        
        # === TIME RANGE FILTER ===
        use_time_range_filter=USE_TIME_RANGE_FILTER,         # Enable time-based entry filtering
        entry_start_hour=ENTRY_START_HOUR,                   # Start hour for entry window (UTC)
        entry_start_minute=ENTRY_START_MINUTE,               # Start minute for entry window (UTC)
        entry_end_hour=ENTRY_END_HOUR,                       # End hour for entry window (UTC)
        entry_end_minute=ENTRY_END_MINUTE,                   # End minute for entry window (UTC)
        
        # === POSITION SIZING ===
        size=1,                           # Default position size (used if risk sizing disabled)
        enable_risk_sizing=True,          # Enable percentage-based risk sizing
        risk_percent=0.01,                # Risk 1% of account per trade
        contract_size=100000,             # Base contract size (auto-adjusted per instrument)
        print_signals=True,               # Print trade signals and debug info to console
        verbose_debug=VERBOSE_DEBUG,      # Print detailed debug info to console (for troubleshooting only)
        
        # === FOREX SETTINGS ===
        use_forex_position_calc=True,     # Enable advanced forex position calculations
        forex_instrument='USDJPY',        # Fixed to USDJPY
        forex_base_currency='USD',        # Base currency: USD
        forex_quote_currency='JPY',       # Quote currency: JPY
        forex_pip_value=0.01,             # Pip value for USDJPY (0.01)
        forex_pip_decimal_places=3,       # Price decimal places for USDJPY
        forex_lot_size=100000,            # Lot size for USDJPY (100K USD)
        forex_micro_lot_size=0.01,        # Minimum lot increment (0.01 standard lots)
        forex_spread_pips=1.0,            # Typical spread in pips for USDJPY
        forex_margin_required=2.0,        # Margin requirement % for USDJPY (30:1 leverage)

        # === ACCOUNT SETTINGS ===
        account_currency='USD',           # Account denomination currency
        account_leverage=30.0,            # Account leverage (matches broker setting)
        
        # === PLOTTING & VISUALIZATION ===
        plot_result=True,                 # Enable strategy plotting
        buy_sell_plotdist=0.0005,         # Distance for buy/sell markers on chart
        plot_sltp_lines=True,             # Show stop loss and take profit lines
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
            elif hasattr(self, 'signal_detection_bar') and self.signal_detection_bar is not None:
                # Secondary: Use signal detection bar
                periods_before_entry = current_bar - self.signal_detection_bar
            elif hasattr(self, 'window_bar_start') and self.window_bar_start is not None:
                # Tertiary: Use window_bar_start if available
                periods_before_entry = current_bar - self.window_bar_start
            else:
                # Quaternary: Estimate based on pullback count + 1
                fallback_bars_to_entry = getattr(self, 'pullback_candle_count', 0) + 1
                periods_before_entry = fallback_bars_to_entry
            
            # Ensure reasonable bounds
            if periods_before_entry < 0:
                periods_before_entry = 1
            elif periods_before_entry > 50:  # Cap at reasonable maximum
                periods_before_entry = 50
            
            # Get current angle with correct scale factor based on signal direction
            if signal_direction == 'SHORT':
                # Calculate angle with SHORT scale factor
                try:
                    current_ema = float(self.ema_confirm[0])
                    previous_ema = float(self.ema_confirm[-1])
                    rise = (current_ema - previous_ema) * self.p.short_angle_scale_factor
                    angle_radians = math.atan(rise)
                    current_angle = math.degrees(angle_radians)
                except:
                    current_angle = 0.0
            else:  # LONG
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
            if stored_increment is not None:
                # Determine if it's increment or decrement based on sign and filter status
                if stored_increment >= 0:
                    # Positive change - always show as increment
                    if self.p.long_use_atr_increment_filter if signal_direction == 'LONG' else self.p.short_use_atr_increment_filter:
                        self.trade_report_file.write(f"ATR Increment: {stored_increment:+.6f} (Filtered)\n")
                    else:
                        self.trade_report_file.write(f"ATR Increment: {stored_increment:+.6f} (No Filter)\n")
                else:
                    # Negative change - show as decrement only if filter is enabled
                    decrement_filter_enabled = self.p.long_use_atr_decrement_filter if signal_direction == 'LONG' else self.p.short_use_atr_decrement_filter
                    if decrement_filter_enabled:
                        self.trade_report_file.write(f"ATR Decrement: {abs(stored_increment):.6f} (Filtered)\n")
                    else:
                        self.trade_report_file.write(f"ATR Change: {stored_increment:+.6f} (Decrement Filter OFF)\n")
            else:
                self.trade_report_file.write(f"ATR Change: N/A\n")
            self.trade_report_file.write(f"Angle Current: {current_angle:.2f}°\n")
            
            # Debug angle validation status - FIX: Use correct parameters for LONG vs SHORT
            if signal_direction == 'LONG':
                if self.p.long_use_angle_filter:
                    angle_ok = self.p.long_min_angle <= current_angle <= self.p.long_max_angle
                    self.trade_report_file.write(f"Angle Filter: ENABLED | Range: {self.p.long_min_angle:.1f}°-{self.p.long_max_angle:.1f}° | Valid: {angle_ok}\n")
                else:
                    self.trade_report_file.write(f"Angle Filter: DISABLED\n")
            else:  # SHORT
                if self.p.short_use_angle_filter:
                    angle_ok = self.p.short_min_angle <= current_angle <= self.p.short_max_angle
                    self.trade_report_file.write(f"Angle Filter: ENABLED | Range: {self.p.short_min_angle:.1f}°-{self.p.short_max_angle:.1f}° | Valid: {angle_ok}\n")
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
                    entry_price = (stop_level + take_level) / 2
                
                # Calculate pips based on direction and P&L
                pips = 0.0
                if entry_price and exit_price:
                    if direction == 'LONG':
                        pips = (exit_price - entry_price) / self.p.forex_pip_value  # Forex pip calculation
                    else:  # SHORT
                        pips = (entry_price - exit_price) / self.p.forex_pip_value  # Forex pip calculation
                
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
                print(f"📊 Trade report completed: {total_trades} trades recorded")
                
            except Exception as e:
                print(f"Trade reporting close error: {e}")
            
            self.trade_report_file = None

    def _cross_above(self, a, b):
        """Return True if `a` crossed above `b` on the current bar."""
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

    def _cross_below(self, a, b):
        """Return True if `a` crossed below `b` on the current bar."""
        try:
            current_a = float(a[0])
            current_b = float(b[0])
            previous_a = float(a[-1])
            previous_b = float(b[-1])
            
            # Pine Script crossunder logic: current < AND previous >=
            crossunder = (current_a < current_b) and (previous_a >= previous_b)
            
            return crossunder
        except (IndexError, ValueError, TypeError):
            return False

    def _angle(self):
        """Compute instantaneous angle (degrees) of the confirm EMA slope."""
        try:
            current_ema = float(self.ema_confirm[0])
            previous_ema = float(self.ema_confirm[-1])
            
            # Pine Script: math.atan((ema_confirm - ema_confirm[1]) * angle_scale_factor) * 180 / math.pi
            rise = (current_ema - previous_ema) * self.p.long_angle_scale_factor
            angle_radians = math.atan(rise)  # run = 1 (1 bar)
            angle_degrees = math.degrees(angle_radians)
            
            return angle_degrees
        except (IndexError, ValueError, TypeError, ZeroDivisionError):
            return float('nan')
    
    def _calculate_forex_position_size(self, entry_price, stop_loss_price):
        """Calculate optimal position size for USDJPY trading with proper risk management.
        
        Args:
            entry_price: Entry price level
            stop_loss_price: Stop loss price level
            
        Returns:
            tuple: (lot_size, contracts, margin_required, pip_risk, position_value)
        """
        if not self.p.use_forex_position_calc:
            return None, None, None, None, None
            
        # Calculate risk in pips
        price_difference = abs(entry_price - stop_loss_price)
        pip_risk = price_difference / self.p.forex_pip_value
        
        # Account equity and risk amount
        account_equity = self.broker.get_value()
        risk_amount = account_equity * self.p.risk_percent
        
        # Calculate value per pip per lot for USDJPY
        # Quote currency is JPY, so value is in JPY. Need to convert to USD.
        # Value in JPY = 100,000 * 0.01 = 1000 JPY per pip per lot
        # Value in USD = 1000 JPY / Current USDJPY Price
        
        if self.p.forex_quote_currency == 'USD':
            value_per_pip_per_lot = (self.p.forex_pip_value * self.p.forex_lot_size)
        elif self.p.forex_quote_currency == 'JPY':
            # Approximate conversion using entry price
            value_per_pip_per_lot = (self.p.forex_pip_value * self.p.forex_lot_size) / entry_price
        else:
            # Fallback
            value_per_pip_per_lot = 1.0
        
        # Calculate optimal lot size
        if pip_risk > 0 and value_per_pip_per_lot > 0:
            optimal_lots = risk_amount / (pip_risk * value_per_pip_per_lot)
            optimal_lots = max(self.p.forex_micro_lot_size, 
                             round(optimal_lots / self.p.forex_micro_lot_size) * self.p.forex_micro_lot_size)
        else:
            return None, None, None, None, None
        
        # Minimum position size check
        min_lots = 0.01
        if optimal_lots < min_lots:
            optimal_lots = min_lots
            
        # Maximum absolute limit
        max_absolute_lots = 500.0
        if optimal_lots > max_absolute_lots:
            optimal_lots = max_absolute_lots
            
        # Calculate position value and margin required
        # Position Value in USD = Lots * 100,000 USD (Base currency is USD)
        position_value = optimal_lots * self.p.forex_lot_size 
        margin_required = position_value * (self.p.forex_margin_required / 100.0)
        
        # Convert to Backtrader contracts
        contracts = max(1, int(optimal_lots * self.p.forex_lot_size))
        
        return optimal_lots, contracts, margin_required, pip_risk, position_value
    
    def _format_forex_trade_info(self, entry_price, stop_loss, take_profit, lot_size, pip_risk, position_value, margin_required):
        """Format comprehensive forex trade information for logging."""
        if not self.p.use_forex_position_calc:
            return ""
            
        if take_profit and entry_price:
            profit_pips = abs(take_profit - entry_price) / self.p.forex_pip_value
            risk_reward = profit_pips / pip_risk if pip_risk > 0 else 0
        else:
            profit_pips = 0
            risk_reward = 0
            
        # Calculate monetary values for USDJPY
        # Value per pip per lot in USD approx $6.5-7.0
        pip_value_per_lot_usd = (self.p.forex_pip_value * self.p.forex_lot_size) / entry_price
            
        risk_amount = pip_risk * lot_size * pip_value_per_lot_usd
        profit_potential = profit_pips * lot_size * pip_value_per_lot_usd
        spread_cost = self.p.forex_spread_pips * lot_size * pip_value_per_lot_usd
        
        units_desc = f"{lot_size * self.p.forex_lot_size:,.0f} {self.p.forex_base_currency}"
        price_format = f"{{:.{self.p.forex_pip_decimal_places}f}}"
        
        return (f"\n--- USDJPY TRADE DETAILS ---\n"
                f"Position Size: {lot_size:.2f} lots ({units_desc})\n"
                f"Position Value: ${position_value:,.2f}\n"
                f"Margin Required: ${margin_required:,.2f} ({self.p.forex_margin_required}%)\n"
                f"Entry: {price_format.format(entry_price)} | SL: {price_format.format(stop_loss)} | TP: {price_format.format(take_profit)}\n"
                f"Risk: {pip_risk:.1f} pips (${risk_amount:.2f}) | Profit: {profit_pips:.1f} pips (${profit_potential:.2f})\n"
                f"Risk/Reward: 1:{risk_reward:.2f} | Spread Cost: ${spread_cost:.2f}\n"
                f"Account Leverage: {self.p.account_leverage:.0f}:1 | Account: {self.p.account_currency}")
    
    def _validate_forex_setup(self):
        """Validate forex configuration for USDJPY."""
        if not self.p.use_forex_position_calc:
            return True
            
        data_filename = getattr(self, '_data_filename', '')
        if 'USDJPY' not in data_filename.upper():
            print(f"WARNING: Data file is {data_filename} but strategy is configured for USDJPY")
            
        if hasattr(self.data, 'close') and len(self.data.close) > 0:
            current_price = float(self.data.close[0])
            if current_price < 70 or current_price > 200:
                print(f"WARNING: Price {current_price} seems unusual for USDJPY (expected range: 70-200)")
                
        if self.p.forex_pip_value != 0.01:
            print(f"INFO: USDJPY typically uses pip value of 0.01, current setting: {self.p.forex_pip_value}")
            
        return True
    
    def _get_forex_instrument_config(self, instrument_name=None):
        """Get configuration for USDJPY instrument."""
        if instrument_name is None or instrument_name == 'AUTO':
            data_filename = getattr(self, '_data_filename', '').upper()
            if 'USDJPY' in data_filename:
                instrument_name = 'USDJPY'
            else:
                instrument_name = 'USDJPY'
        
        config = {
            'USDJPY': {
                'base_currency': 'USD',
                'quote_currency': 'JPY',
                'pip_value': 0.01,
                'pip_decimal_places': 3,
                'lot_size': 100000,
                'margin_required': 2.0,
                'typical_spread': 1.0
            }
        }
        
        return config.get(instrument_name, config['USDJPY'])
    
    def _apply_forex_config(self):
        """Apply forex configuration for USDJPY."""
        if not self.p.use_forex_position_calc:
            return
            
        config = self._get_forex_instrument_config('USDJPY')
        
        self.p.forex_base_currency = config['base_currency']
        self.p.forex_quote_currency = config['quote_currency']
        self._detected_instrument = 'USDJPY'
        data_filename = getattr(self, '_data_filename', '').upper()
                
        self.p.forex_pip_value = config['pip_value']
        self.p.forex_pip_decimal_places = config['pip_decimal_places']
        self.p.forex_lot_size = config['lot_size']
        self.p.forex_margin_required = config['margin_required']
        self.p.forex_spread_pips = config['typical_spread']
        self.p.forex_instrument = 'USDJPY'
                
        print(f"CONFIGURED: USDJPY from filename: {data_filename}")
        print(f"Forex Config: {self.p.forex_base_currency}/{self.p.forex_quote_currency}")
        print(f"Pip Value: {self.p.forex_pip_value} | Lot Size: {self.p.forex_lot_size:,} | Margin: {self.p.forex_margin_required}%")

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
            self.pullback_green_count = 0  # Count of consecutive green candles (SHORT pullbacks)
            self.first_green_low = None  # Low of first green candle in pullback (SHORT)
            self.entry_window_start = None  # Bar when entry window opened
            self.breakout_target = None  # Price target for entry breakout
            
            # ATR VOLATILITY FILTER TRACKING
            self.signal_detection_atr = None  # ATR value when signal was first detected
            self.signal_detection_bar = None  # Bar number when signal was first detected
            self.pullback_start_atr = None    # ATR value when pullback phase started

            # NEW STATE MACHINE FOR VOLATILITY EXPANSION CHANNEL ENTRY LOGIC
            self.entry_state = "SCANNING"  # States: SCANNING, ARMED_LONG, ARMED_SHORT, WINDOW_OPEN
            self.armed_direction = None    # Will be 'LONG' or 'SHORT'
            self.pullback_candle_count = 0
            self.last_pullback_candle_high = None
            self.last_pullback_candle_low = None
            self.window_top_limit = None
            self.window_bottom_limit = None
            self.window_expiry_bar = None
            self.window_breakout_level = None  # Price level that must be broken for entry
            
            # 🔧 CRITICAL FIX: Store original signal trigger candle for validation
            self.signal_trigger_candle = None

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
                
            # Apply dual cerebro overrides for trading direction
            if self.p.long_enabled is not None:
                self.p.enable_long_trades = self.p.long_enabled
            if self.p.short_enabled is not None:
                self.p.enable_short_trades = self.p.short_enabled
                
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
                # Use script directory to ensure consistent location regardless of CWD
                script_dir = Path(__file__).parent
                report_dir = script_dir / "temp_reports"
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
                if self.p.enable_short_trades: direction.append("SHORT")
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
                    self.trade_report_file.write(f"  Angle Range: {self.p.long_min_angle:.2f}° to {self.p.long_max_angle:.2f}°\n")
                    self.trade_report_file.write(f"  Candle Direction Filter: {'ENABLED (Require bullish candle)' if self.p.long_use_candle_direction_filter else 'DISABLED'}\n")
                    self.trade_report_file.write(f"  Pullback Mode: {self.p.long_use_pullback_entry}\n\n")
                    
                # SHORT parameters  
                if self.p.enable_short_trades:
                    self.trade_report_file.write("SHORT Configuration:\n")
                    self.trade_report_file.write(f"  ATR Range: {self.p.short_atr_min_threshold:.6f} - {self.p.short_atr_max_threshold:.6f}\n")
                    # ATR increment/decrement filter configuration
                    if self.p.short_use_atr_increment_filter:
                        self.trade_report_file.write(f"  ATR Increment Range: {self.p.short_atr_increment_min_threshold:.6f} to {self.p.short_atr_increment_max_threshold:.6f}\n")
                    if self.p.short_use_atr_decrement_filter:
                        self.trade_report_file.write(f"  ATR Decrement Range: {self.p.short_atr_decrement_min_threshold:.6f} to {self.p.short_atr_decrement_max_threshold:.6f}\n")
                    self.trade_report_file.write(f"  Angle Range: {self.p.short_min_angle:.2f}° to {self.p.short_max_angle:.2f}°\n")
                    self.trade_report_file.write(f"  Candle Direction Filter: {'ENABLED (Require bearish candle)' if self.p.short_use_candle_direction_filter else 'DISABLED'}\n")
                    self.trade_report_file.write(f"  Pullback Mode: {self.p.short_use_pullback_entry}\n\n")
                    
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
                if self.p.enable_short_trades:
                    self.trade_report_file.write(f"  SHORT Stop Loss ATR Multiplier: {self.p.short_atr_sl_multiplier:.1f}\n")
                    self.trade_report_file.write(f"  SHORT Take Profit ATR Multiplier: {self.p.short_atr_tp_multiplier:.1f}\n")
                
                self.trade_report_file.write("\n" + "="*80 + "\n")
                self.trade_report_file.write("TRADE DETAILS\n")
                self.trade_report_file.write("="*80 + "\n\n")
                self.trade_report_file.flush()
                
                print(f"📊 TRADE REPORT: {report_path}")
                
            except Exception as e:
                print(f"⚠️  Trade reporting initialization failed: {e}")
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
        # 🔧 CRITICAL FIX: Reset stored trigger candle
        self.signal_trigger_candle = None

    def _phase1_scan_for_signal(self):
        """PHASE 1: Scan for initial EMA crossover signals"""
        # Check LONG signals
        if self.p.enable_long_trades:
            try:
                prev_bull = self.data.close[-1] > self.data.open[-1]
            except IndexError:
                prev_bull = False

            cross_fast = self._cross_above(self.ema_confirm, self.ema_fast)
            cross_medium = self._cross_above(self.ema_confirm, self.ema_medium) 
            cross_slow = self._cross_above(self.ema_confirm, self.ema_slow)
            cross_any = cross_fast or cross_medium or cross_slow
            
            candle_direction_ok = True
            if self.p.long_use_candle_direction_filter:
                candle_direction_ok = prev_bull
            
            if candle_direction_ok and cross_any:
                signal_valid = True
                
                if self.p.long_use_ema_order_condition:
                    ema_order_ok = (
                        self.ema_confirm[0] > self.ema_fast[0] and
                        self.ema_confirm[0] > self.ema_medium[0] and
                        self.ema_confirm[0] > self.ema_slow[0]
                    )
                    if not ema_order_ok:
                        signal_valid = False

                if signal_valid and self.p.long_use_price_filter_ema:
                    price_above_filter = self.data.close[0] > self.ema_filter_price[0]
                    if not price_above_filter:
                        signal_valid = False
                
                if signal_valid and self.p.long_use_ema_below_price_filter:
                    emas_below_price = (
                        self.ema_fast[0] < self.data.close[0] and
                        self.ema_medium[0] < self.data.close[0] and
                        self.ema_slow[0] < self.data.close[0]
                    )
                    if not emas_below_price:
                        signal_valid = False

                if signal_valid and self.p.long_use_angle_filter:
                    current_angle = self._angle()
                    angle_ok = self.p.long_min_angle <= current_angle <= self.p.long_max_angle
                    if not angle_ok:
                        signal_valid = False

                if signal_valid and self.p.long_use_atr_filter:
                    current_atr = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
                    if current_atr < self.p.long_atr_min_threshold or current_atr > self.p.long_atr_max_threshold:
                        signal_valid = False

                if signal_valid:
                    current_atr = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
                    self.signal_detection_atr = current_atr
                    return 'LONG'

        # Check SHORT signals
        if self.p.enable_short_trades:
            try:
                prev_bear = self.data.close[-1] < self.data.open[-1]
            except IndexError:
                prev_bear = False

            cross_fast = self._cross_below(self.ema_confirm, self.ema_fast)
            cross_medium = self._cross_below(self.ema_confirm, self.ema_medium) 
            cross_slow = self._cross_below(self.ema_confirm, self.ema_slow)
            cross_any = cross_fast or cross_medium or cross_slow
            
            candle_direction_ok = True
            if self.p.short_use_candle_direction_filter:
                candle_direction_ok = prev_bear
            
            if candle_direction_ok and cross_any:
                signal_valid = True
                
                if self.p.short_use_ema_order_condition:
                    ema_order_ok = (
                        self.ema_confirm[0] < self.ema_fast[0] and
                        self.ema_confirm[0] < self.ema_medium[0] and
                        self.ema_confirm[0] < self.ema_slow[0]
                    )
                    if not ema_order_ok:
                        signal_valid = False

                if signal_valid and self.p.short_use_price_filter_ema:
                    price_below_filter = self.data.close[0] < self.ema_filter_price[0]
                    if not price_below_filter:
                        signal_valid = False
                
                if signal_valid and self.p.short_use_ema_above_price_filter:
                    emas_above_price = (
                        self.ema_fast[0] > self.data.close[0] and
                        self.ema_medium[0] > self.data.close[0] and
                        self.ema_slow[0] > self.data.close[0]
                    )
                    if not emas_above_price:
                        signal_valid = False

                if signal_valid and self.p.short_use_angle_filter:
                    current_angle = self._angle()
                    angle_ok = self.p.short_min_angle <= current_angle <= self.p.short_max_angle
                    if not angle_ok:
                        signal_valid = False

                if signal_valid and self.p.short_use_atr_filter:
                    current_atr = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
                    if current_atr < self.p.short_atr_min_threshold or current_atr > self.p.short_atr_max_threshold:
                        signal_valid = False

                if signal_valid:
                    current_atr = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
                    self.signal_detection_atr = current_atr
                    # if self.p.print_signals:
                    #     print(f"SHORT SIGNAL DETECTED - {self.data.datetime.datetime(0)}:")
                    #     print(f"   Signal detection ATR: {current_atr:.6f}")
                    return 'SHORT'

        return None

    def _phase2_confirm_pullback(self, armed_direction):
        """PHASE 2: Count pullback candles and validate pullback sequence"""
        is_pullback_candle = False
        
        if armed_direction == 'LONG':
            is_pullback_candle = self.data.close[0] < self.data.open[0]
        else:  # SHORT
            is_pullback_candle = self.data.close[0] > self.data.open[0]
        
        if is_pullback_candle:
            self.pullback_candle_count += 1
            
            max_candles = (self.p.long_pullback_max_candles if armed_direction == 'LONG' 
                          else self.p.short_pullback_max_candles)
            
            if self.pullback_candle_count >= max_candles:
                self.last_pullback_candle_high = float(self.data.high[0])
                self.last_pullback_candle_low = float(self.data.low[0])
                
                # if self.p.print_signals:
                #     print(f"PULLBACK CONFIRMED: {armed_direction} pullback complete ({self.pullback_candle_count} candles)")
                return True
        else:
            # if self.p.print_signals:
            #     print(f"PULLBACK INVALIDATED: {armed_direction} non-pullback candle detected, resetting to SCANNING")
            self._reset_entry_state()
            
        return False

    def _phase3_open_breakout_window(self, armed_direction):
        """PHASE 3: Open the two-sided breakout window after pullback confirmation"""
        current_bar = len(self)

        window_start_bar = current_bar
        if self.p.use_window_time_offset:
            time_offset = int(self.pullback_candle_count * self.p.window_offset_multiplier)
            window_start_bar = current_bar + time_offset
        
        self.window_bar_start = window_start_bar
        
        window_periods = (self.p.long_entry_window_periods if armed_direction == 'LONG' 
                         else self.p.short_entry_window_periods)
        self.window_expiry_bar = window_start_bar + window_periods

        last_high = self.last_pullback_candle_high
        last_low = self.last_pullback_candle_low
        candle_range = last_high - last_low
        price_offset = candle_range * self.p.window_price_offset_multiplier

        self.window_top_limit = last_high + price_offset
        self.window_bottom_limit = last_low - price_offset
        
        self.entry_state = "WINDOW_OPEN"
        
        # if self.p.print_signals:
        #     time_offset_text = f" (offset: {time_offset} bars)" if self.p.use_window_time_offset else " (immediate)"
        #     print(f"WINDOW OPENED ({armed_direction}): Active from bar {window_start_bar} to {self.window_expiry_bar}{time_offset_text}")

    def _phase4_monitor_window(self, armed_direction):
        """PHASE 4: Monitor for breakout or failure within the two-sided channel"""
        current_bar = len(self)

        if current_bar < self.window_bar_start:
            return None

        if current_bar > self.window_expiry_bar:
            # if self.p.print_signals:
            #     print(f"WINDOW TIMEOUT ({armed_direction}): No breakout occurred. Resetting to ARMED.")
            self.entry_state = f"ARMED_{armed_direction}"
            self.pullback_candle_count = 0
            self.window_top_limit, self.window_bottom_limit, self.window_expiry_bar = None, None, None
            self.window_breakout_level = None
            return None

        current_high = self.data.high[0]
        current_low = self.data.low[0]

        if armed_direction == 'LONG':
            if current_high >= self.window_top_limit:
                # if self.p.print_signals:
                #     print(f"SUCCESS BREAKOUT (LONG): Price {current_high:.5f} broke above success level {self.window_top_limit:.5f}")
                return 'SUCCESS'
            
            elif current_low <= self.window_bottom_limit:
                # if self.p.print_signals:
                #     print(f"FAILURE BREAKOUT (LONG): Price {current_low:.5f} broke below failure level {self.window_bottom_limit:.5f}. Instability detected.")
                self.entry_state = "ARMED_LONG"
                self.pullback_candle_count = 0
                self.window_top_limit, self.window_bottom_limit, self.window_expiry_bar = None, None, None
                self.window_breakout_level = None
                return None

        elif armed_direction == 'SHORT':
            if current_low <= self.window_bottom_limit:
                # if self.p.print_signals:
                #     print(f"SUCCESS BREAKOUT (SHORT): Price {current_low:.5f} broke below success level {self.window_bottom_limit:.5f}")
                return 'SUCCESS'

            elif current_high >= self.window_top_limit:
                # if self.p.print_signals:
                #     print(f"FAILURE BREAKOUT (SHORT): Price {current_high:.5f} broke above failure level {self.window_top_limit:.5f}. Instability detected.")
                self.entry_state = "ARMED_SHORT"
                self.pullback_candle_count = 0
                self.window_top_limit, self.window_bottom_limit, self.window_expiry_bar = None, None, None
                self.window_breakout_level = None
                return None
        
        return None

    def next(self):
        """Main strategy logic using volatility expansion channel entry system with 4-phase state machine"""
        if hasattr(self, '_portfolio_values'):
            self._portfolio_values.append(self.broker.get_value())
            self._timestamps.append(self.data.datetime.datetime(0))
        
        self.exit_this_bar = False
        
        if hasattr(self, 'pending_close') and self.pending_close:
            if not self.position:
                self.pending_close = False
            else:
                return
        
        dt = bt.num2date(self.data.datetime[0])
        current_bar = len(self)
        
        if self.position:
            self._was_in_position = True
        elif hasattr(self, '_was_in_position'):
            delattr(self, '_was_in_position')
        
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
                self._reset_entry_state()

        if self.order:
            return

        if self.position:
            return

        if self.exit_this_bar:
            return
        
        if self.entry_state in ["ARMED_LONG", "ARMED_SHORT"]:
            opposing_signal = None
            
            if self.entry_state == "ARMED_LONG":
                try:
                    prev_bear = self.data.close[-1] < self.data.open[-1]
                    cross_fast = self._cross_below(self.ema_confirm, self.ema_fast)
                    cross_medium = self._cross_below(self.ema_confirm, self.ema_medium) 
                    cross_slow = self._cross_below(self.ema_confirm, self.ema_slow)
                    if prev_bear and (cross_fast or cross_medium or cross_slow):
                        opposing_signal = "SHORT"
                except IndexError:
                    pass
                    
            elif self.entry_state == "ARMED_SHORT":
                try:
                    prev_bull = self.data.close[-1] > self.data.open[-1]
                    cross_fast = self._cross_above(self.ema_confirm, self.ema_fast)
                    cross_medium = self._cross_above(self.ema_confirm, self.ema_medium) 
                    cross_slow = self._cross_above(self.ema_confirm, self.ema_slow)
                    if prev_bull and (cross_fast or cross_medium or cross_slow):
                        opposing_signal = "LONG"
                except IndexError:
                    pass
            
            if opposing_signal:
                # if self.p.print_signals:
                #     print(f"GLOBAL INVALIDATION: {opposing_signal} signal detected, resetting {self.entry_state}")
                self._reset_entry_state()

        if self.entry_state == "SCANNING":
            signal_direction = self._phase1_scan_for_signal()
            if signal_direction:
                self.entry_state = f"ARMED_{signal_direction}"
                self.armed_direction = signal_direction
                self.pullback_candle_count = 0
                
                self.signal_trigger_candle = {
                    'open': float(self.data.open[-1]),
                    'close': float(self.data.close[-1]),
                    'high': float(self.data.high[-1]),
                    'low': float(self.data.low[-1]),
                    'datetime': self.data.datetime.datetime(-1),
                    'is_bullish': self.data.close[-1] > self.data.open[-1],
                    'is_bearish': self.data.close[-1] < self.data.open[-1]
                }
                
                # if self.p.print_signals:
                #     print(f"STATE TRANSITION: SCANNING → ARMED_{signal_direction} at {dt:%Y-%m-%d %H:%M}")
                
        elif self.entry_state in ["ARMED_LONG", "ARMED_SHORT"]:
            if self._phase2_confirm_pullback(self.armed_direction):
                self.entry_state = "WINDOW_OPEN"
                self._phase3_open_breakout_window(self.armed_direction)
                # if self.p.print_signals:
                #     print(f"STATE TRANSITION: ARMED_{self.armed_direction} → WINDOW_OPEN at {dt:%Y-%m-%d %H:%M}")
                
        elif self.entry_state == "WINDOW_OPEN":
            breakout_status = self._phase4_monitor_window(self.armed_direction)
            
            if breakout_status == 'SUCCESS':
                if not self._is_in_trading_time_range(dt):
                    self._reset_entry_state()
                    return
                
                signal_direction = self.armed_direction
                
                if hasattr(self, 'signal_trigger_candle') and self.signal_trigger_candle:
                    trigger_candle = self.signal_trigger_candle
                    candle_body = abs(trigger_candle['close'] - trigger_candle['open'])
                    min_body_size = 0.00001
                    
                    current_prev_candle_bullish = trigger_candle['is_bullish'] and candle_body >= min_body_size
                    current_prev_candle_bearish = trigger_candle['is_bearish'] and candle_body >= min_body_size
                else:
                    prev_close = self.data.close[-1]
                    prev_open = self.data.open[-1]
                    candle_body = abs(prev_close - prev_open)
                    min_body_size = 0.00001
                    
                    current_prev_candle_bullish = (prev_close > prev_open) and (candle_body >= min_body_size)
                    current_prev_candle_bearish = (prev_close < prev_open) and (candle_body >= min_body_size)
                
                if signal_direction == 'LONG' and self.p.long_use_candle_direction_filter:
                    if not current_prev_candle_bullish:
                        self._reset_entry_state()
                        return
                
                elif signal_direction == 'SHORT' and self.p.short_use_candle_direction_filter:
                    if not current_prev_candle_bearish:
                        self._reset_entry_state()
                        return
                
                if signal_direction == 'LONG':
                    if not self._validate_all_entry_filters():
                        self._reset_entry_state()
                        return
                elif signal_direction == 'SHORT':
                    if not self._validate_all_short_entry_filters():
                        self._reset_entry_state()
                        return
                
                dt = bt.num2date(self.data.datetime[0])
                if not self._is_in_trading_time_range(dt):
                    self._reset_entry_state()
                    return
                
                atr_now = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
                if atr_now <= 0:
                    self._reset_entry_state()
                    return

                entry_price = float(self.data.close[0])
                bar_low = float(self.data.low[0])
                bar_high = float(self.data.high[0])
                
                if signal_direction == 'LONG':
                    self.stop_level = bar_low - atr_now * self.p.long_atr_sl_multiplier
                    self.take_level = bar_high + atr_now * self.p.long_atr_tp_multiplier
                elif signal_direction == 'SHORT':
                    self.stop_level = bar_high + atr_now * self.p.short_atr_sl_multiplier
                    self.take_level = bar_low - atr_now * self.p.short_atr_tp_multiplier
                
                self.initial_stop_level = self.stop_level

                if self.p.enable_risk_sizing:
                    if signal_direction == 'LONG':
                        raw_risk = entry_price - self.stop_level
                    else:
                        raw_risk = self.stop_level - entry_price
                        
                    if raw_risk <= 0:
                        self._reset_entry_state()
                        return
                    equity = self.broker.get_value()
                    risk_val = equity * self.p.risk_percent
                    risk_per_contract = raw_risk * self.p.contract_size
                    
                    # Convert risk to USD for USDJPY (Account is USD, Risk is JPY)
                    # Risk (USD) = Risk (JPY) / USDJPY_Price
                    if self.p.forex_instrument == 'USDJPY' and entry_price > 0:
                        risk_per_contract = risk_per_contract / entry_price

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

                if signal_direction == 'LONG':
                    self.order = self.buy(size=bt_size)
                    signal_type_display = " LONG BUY"
                elif signal_direction == 'SHORT':
                    self.order = self.sell(size=bt_size)
                    signal_type_display = " SHORT SELL"

                if self.p.print_signals:
                    print(f"🎯 VOLATILITY EXPANSION ENTRY{signal_type_display} {dt:%Y-%m-%d %H:%M} price={entry_price:.5f} size={bt_size} SL={self.stop_level:.5f} TP={self.take_level:.5f}")

                current_atr = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
                
                if hasattr(self, 'signal_detection_atr') and self.signal_detection_atr is not None:
                    self.entry_atr_increment = current_atr - self.signal_detection_atr
                    self.entry_signal_detection_atr = self.signal_detection_atr
                else:
                    self.entry_atr_increment = None
                    self.entry_signal_detection_atr = None

                self._record_trade_entry(signal_direction, dt, entry_price, bt_size, atr_now)

                self.last_entry_price = entry_price
                self.last_entry_bar = current_bar
                
                self._reset_entry_state()
                self._reset_signal_tracking()

    def _is_in_trading_time_range(self, dt):
        """Check if current time is within allowed trading hours (UTC)"""
        if not self.p.use_time_range_filter:
            return True
            
        current_hour = dt.hour
        current_minute = dt.minute
        
        current_time_minutes = current_hour * 60 + current_minute
        start_time_minutes = self.p.entry_start_hour * 60 + self.p.entry_start_minute
        end_time_minutes = self.p.entry_end_hour * 60 + self.p.entry_end_minute
        
        if start_time_minutes <= end_time_minutes:
            return start_time_minutes <= current_time_minutes <= end_time_minutes
        else:
            return current_time_minutes >= start_time_minutes or current_time_minutes <= end_time_minutes
    
    def _validate_all_entry_filters(self):
        """Validate all entry filters (3-6) for pullback entry"""
        if self.p.long_use_ema_order_condition:
            ema_order_ok = (
                self.ema_confirm[0] > self.ema_fast[0] and
                self.ema_confirm[0] > self.ema_medium[0] and
                self.ema_confirm[0] > self.ema_slow[0]
            )
            if not ema_order_ok:
                return False

        if self.p.long_use_price_filter_ema:
            price_above_filter = self.data.close[0] > self.ema_filter_price[0]
            if not price_above_filter:
                return False
        
        if self.p.long_use_ema_below_price_filter:
            emas_below_price = (
                self.ema_fast[0] < self.data.close[0] and
                self.ema_medium[0] < self.data.close[0] and
                self.ema_slow[0] < self.data.close[0]
            )
            if not emas_below_price:
                return False

        if self.p.long_use_angle_filter:
            current_angle = self._angle()
            angle_ok = self.p.long_min_angle <= current_angle <= self.p.long_max_angle
            if not angle_ok:
                return False

        return True
    
    def _validate_all_short_entry_filters(self):
        """Validate all SHORT entry filters (3-6) for pullback entry"""
        if self.p.short_use_ema_order_condition:
            ema_order_ok = (
                self.ema_confirm[0] < self.ema_fast[0] and
                self.ema_confirm[0] < self.ema_medium[0] and
                self.ema_confirm[0] < self.ema_slow[0]
            )
            if not ema_order_ok:
                return False

        if self.p.short_use_price_filter_ema:
            price_below_filter = self.data.close[0] < self.ema_filter_price[0]
            if not price_below_filter:
                return False
        
        if self.p.short_use_ema_above_price_filter:
            emas_above_price = (
                self.ema_fast[0] > self.data.close[0] and
                self.ema_medium[0] > self.data.close[0] and
                self.ema_slow[0] > self.data.close[0]
            )
            if not emas_above_price:
                return False

        if self.p.short_use_angle_filter:
            try:
                current_ema = float(self.ema_confirm[0])
                previous_ema = float(self.ema_confirm[-1])
                rise = (current_ema - previous_ema) * self.p.short_angle_scale_factor
                angle_radians = math.atan(rise)
                current_angle = math.degrees(angle_radians)
            except:
                current_angle = 0.0
                
            angle_ok = self.p.short_min_angle <= current_angle <= self.p.short_max_angle
            if not angle_ok:
                return False

        return True
    
    def _reset_pullback_state(self):
        """Reset pullback state machine to initial state but preserve tracking variables"""
        self.pullback_state = "NORMAL"
        self.pullback_red_count = 0
        self.first_red_high = None
        self.pullback_green_count = 0
        self.first_green_low = None
        self.breakout_target = None
        self.pullback_start_atr = None

    def _reset_signal_tracking(self):
        """Reset signal tracking variables after trade recording is complete"""
        self.entry_window_start = None
        self.signal_detection_bar = None
        self.signal_detection_atr = None

    def notify_order(self, order):
        """Enhanced order notification with robust OCA group for SL/TP supporting both LONG and SHORT positions."""
        dt = bt.num2date(self.data.datetime[0])

        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status == order.Completed:
            if order == self.order:
                self.last_entry_price = order.executed.price
                self.last_entry_bar = len(self)
                
                if order.isbuy():
                    entry_type = " LONG BUY"
                    if self.p.print_signals:
                        print(f"✅ {entry_type} EXECUTED at {order.executed.price:.5f} size={order.executed.size}")

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
                        if self.p.print_signals:
                            print(f"🛡️  LONG PROTECTIVE OCA ORDERS: SL={self.stop_level:.5f} TP={self.take_level:.5f}")
                
                else:
                    entry_type = " SHORT SELL"
                    if self.p.print_signals:
                        print(f"✅ {entry_type} EXECUTED at {order.executed.price:.5f} size={order.executed.size}")

                    if self.stop_level and self.take_level:
                        self.stop_order = self.buy(
                            size=order.executed.size,
                            exectype=bt.Order.Stop,
                            price=self.stop_level,
                            oco=self.limit_order
                        )
                        self.limit_order = self.buy(
                            size=order.executed.size,
                            exectype=bt.Order.Limit,
                            price=self.take_level,
                            oco=self.stop_order
                        )
                        if self.p.print_signals:
                            print(f"🛡️  SHORT PROTECTIVE OCA ORDERS: SL={self.stop_level:.5f} TP={self.take_level:.5f}")
                
                self.order = None

            else:
                exit_price = order.executed.price
                
                exit_reason = "UNKNOWN"
                if order.exectype == bt.Order.Stop:
                    exit_reason = "STOP_LOSS"
                elif order.exectype == bt.Order.Limit:
                    exit_reason = "TAKE_PROFIT"
                else:
                    exit_reason = "MANUAL_CLOSE"
                
                self.last_exit_reason = exit_reason
                
                position_type = " LONG" if order.issell() else " SHORT"
                
                if self.p.print_signals:
                    print(f"🔚 {position_type} EXIT EXECUTED at {exit_price:.5f} size={order.executed.size} reason={exit_reason}")

                self.stop_order = None
                self.limit_order = None
                self.order = None
                self.stop_level = None
                self.take_level = None
                self.initial_stop_level = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            is_expected_cancel = (self.stop_order and self.limit_order)
            # if not is_expected_cancel and self.p.print_signals:
            #     print(f"Order {order.getstatusname()}: {order.ref}")
            
            if self.order and order.ref == self.order.ref: self.order = None
            if self.stop_order and order.ref == self.stop_order.ref: self.stop_order = None
            if self.limit_order and order.ref == self.limit_order.ref: self.limit_order = None

    def notify_trade(self, trade):
        """Use Backtrader's proper trade notification for accurate PnL tracking"""
        
        if not trade.isclosed:
            return

        dt = bt.num2date(self.data.datetime[0])
        pnl = trade.pnlcomm
        
        # Debug print to verify notify_trade is called
        # print(f"DEBUG: notify_trade called. PnL: {pnl:.2f}")

        entry_price = self.last_entry_price if self.last_entry_price else 0
        position_direction = 'LONG' if trade.size > 0 else 'SHORT'
        
        if entry_price > 0 and trade.size != 0:
            if position_direction == 'LONG':
                exit_price = entry_price + (pnl / trade.size)
            else:
                exit_price = entry_price + (pnl / trade.size)
        else:
            exit_price = trade.price
            if exit_price == entry_price:
                exit_price = float(self.data.close[0])
        
        exit_reason = getattr(self, 'last_exit_reason', 'UNKNOWN')
        
        if exit_reason == 'UNKNOWN':
            if self.stop_level and abs(exit_price - self.stop_level) < 0.0002:
                exit_reason = "STOP_LOSS"
            elif self.take_level and abs(exit_price - self.take_level) < 0.0002:
                exit_reason = "TAKE_PROFIT"
            else:
                exit_reason = "MANUAL_CLOSE"
        
        self.trades += 1
        if pnl > 0:
            self.wins += 1
            self.gross_profit += pnl
        else:
            self.losses += 1
            self.gross_loss += abs(pnl)

        current_bar = len(self)
        self.trade_exit_bars.append(current_bar)
        self.exit_this_bar = True
        
        if len(self.trade_exit_bars) > 100:
            self.trade_exit_bars = self.trade_exit_bars[-100:]

        self.last_exit_bar = current_bar

        if self.p.print_signals:
            if position_direction == 'LONG':
                pips = (exit_price - entry_price) / self.p.forex_pip_value if self.p.forex_pip_value and entry_price > 0 else 0
            else:
                pips = (entry_price - exit_price) / self.p.forex_pip_value if self.p.forex_pip_value and entry_price > 0 else 0
            
            print(f"{position_direction} TRADE CLOSED {dt:%Y-%m-%d %H:%M} reason={exit_reason} PnL={pnl:.2f} Pips={pips:.1f}")
            print(f"  Entry: {entry_price:.5f} -> Exit: {exit_price:.5f} | Size: {trade.size}")

        self._record_trade_exit(dt, exit_price, pnl, exit_reason)

        self.stop_level = None
        self.take_level = None
        self.initial_stop_level = None
        
        if self.p.long_use_pullback_entry or self.p.short_use_pullback_entry:
            self._reset_pullback_state()

    def stop(self):
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
        
        print("=== SUNRISE OGLE USDJPY SUMMARY ===")
        
        wr = (self.wins / self.trades * 100.0) if self.trades else 0.0
        pf = (self.gross_profit / self.gross_loss) if self.gross_loss > 0 else float('inf')
        
        final_value = self.broker.get_value()
        starting_cash = 100000.0
        total_pnl = final_value - starting_cash
        
        print(f"Trades: {self.trades} Wins: {self.wins} Losses: {self.losses} WinRate: {wr:.2f}% PF: {pf:.2f}")
        print(f"Final Value: {final_value:,.2f} | Total PnL: {total_pnl:+,.2f}")
        
        if self.p.long_use_pullback_entry or self.p.short_use_pullback_entry:
            self._reset_pullback_state()
        
        self._close_trade_reporting()


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

class USDJPYCommission(bt.CommInfoBase):
    """
    Custom Commission Scheme for USDJPY when Account Currency is USD.
    
    Logic:
    - PnL in JPY = (Price_Exit - Price_Entry) * Size
    - PnL in USD = PnL in JPY / Price_Exit (approximate, or Price_Close)
    """
    params = (
        ('stocklike', False),
        ('commtype', bt.CommInfoBase.COMM_PERC),
        ('percabs', True),
        ('leverage', 30.0),
    )

    def profitandloss(self, size, price, newprice):
        # Standard PnL calculation (in Quote Currency JPY)
        pnl_jpy = size * (newprice - price)
        
        # Convert JPY to USD using the closing price (approximate)
        if newprice > 0:
            pnl_usd = pnl_jpy / newprice
            # print(f"DEBUG: PnL: Size={size}, Entry={price:.4f}, Exit={newprice:.4f} | PnL(JPY)={pnl_jpy:.2f} | PnL(USD)={pnl_usd:.2f}")
            return pnl_usd
        else:
            return pnl_jpy

    def cashadjust(self, size, price, newprice):
        '''Calculates cash adjustment for a given price difference'''
        if not self._stocklike:
            pnl_jpy = size * (newprice - price)
            if newprice > 0:
                pnl_usd = pnl_jpy / newprice
                # print(f"DEBUG: CashAdj: Size={size}, Price={price:.4f}, NewPrice={newprice:.4f} | Adj(JPY)={pnl_jpy:.2f} | Adj(USD)={pnl_usd:.2f}")
                return pnl_usd
        return 0.0

if __name__ == '__main__':
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
        print(f"Data file not found: {DATA_FILE}"); raise SystemExit(1)

    feed_kwargs = dict(dataname=str(DATA_FILE), dtformat='%Y%m%d', tmformat='%H:%M:%S',
                       datetime=0, time=1, open=2, high=3, low=4, close=5, volume=6,
                       timeframe=bt.TimeFrame.Minutes, compression=5)
    fd = parse_date(FROMDATE); td = parse_date(TODATE)
    if fd: feed_kwargs['fromdate'] = fd
    if td: feed_kwargs['todate'] = td
    data = bt.feeds.GenericCSVData(**feed_kwargs)

    cerebro = bt.Cerebro(stdstats=False)
    cerebro.adddata(data, name='USDJPY')
    cerebro.broker.setcash(STARTING_CASH)

    # Add custom commission for USDJPY
    cerebro.broker.addcommissioninfo(USDJPYCommission(), name='USDJPY')

    cerebro.addstrategy(SunriseOgleUSDJPY, **STRAT_KWARGS)
    try: cerebro.addobserver(bt.observers.BuySell, barplot=False, plotdist=SunriseOgleUSDJPY.params.buy_sell_plotdist)
    except Exception: pass
    if SunriseOgleUSDJPY.params.plot_sltp_lines:
        try: cerebro.addobserver(SLTPObserver)
        except Exception: pass
    try: cerebro.addobserver(bt.observers.Value)
    except Exception: pass

    if LIMIT_BARS > 0:
        orig_next = SunriseOgleUSDJPY.next
        def limited_next(self):
            if len(self.data) >= LIMIT_BARS:
                self.env.runstop(); return
            orig_next(self)
        SunriseOgleUSDJPY.next = limited_next

    print(f"=== SUNRISE OGLE USDJPY === (from {FROMDATE} to {TODATE})")
    if ENABLE_FOREX_CALC:
        print(f">> FOREX MODE ENABLED - Data: {DATA_FILENAME}")
        print(f">> Instrument: USDJPY")
    else:
        print(f" STANDARD MODE - Data: {DATA_FILENAME}")

    if RUN_DUAL_CEREBRO and ENABLE_LONG_TRADES and ENABLE_SHORT_TRADES:
        print(" DUAL CEREBRO MODE: Running separate LONG-only and SHORT-only strategies")
        
        print("\n RUNNING LONG-ONLY STRATEGY...")
        cerebro_long = bt.Cerebro(stdstats=False)
        data_long = bt.feeds.GenericCSVData(**feed_kwargs)
        cerebro_long.adddata(data_long)
        cerebro_long.broker.setcash(STARTING_CASH)
        cerebro_long.broker.setcommission(leverage=30.0)
        
        long_kwargs = STRAT_KWARGS.copy()
        long_kwargs.update({
            'long_enabled': True,
            'short_enabled': False,
            'print_signals': True
        })
        cerebro_long.addstrategy(SunriseOgleUSDJPY, **long_kwargs)
        
        try: cerebro_long.addobserver(bt.observers.BuySell, barplot=False, plotdist=SunriseOgleUSDJPY.params.buy_sell_plotdist)
        except Exception: pass
        if SunriseOgleUSDJPY.params.plot_sltp_lines:
            try: cerebro_long.addobserver(SLTPObserver)
            except Exception: pass
        try: cerebro_long.addobserver(bt.observers.Value)
        except Exception: pass
        
        results_long = cerebro_long.run()
        final_value_long = cerebro_long.broker.getvalue()
        
        print("\n RUNNING SHORT-ONLY STRATEGY...")
        cerebro_short = bt.Cerebro(stdstats=False)
        data_short = bt.feeds.GenericCSVData(**feed_kwargs)
        cerebro_short.adddata(data_short)
        cerebro_short.broker.setcash(STARTING_CASH)
        cerebro_short.broker.setcommission(leverage=30.0)
        
        short_kwargs = STRAT_KWARGS.copy()
        short_kwargs.update({
            'long_enabled': False,
            'short_enabled': True,
            'print_signals': True
        })
        cerebro_short.addstrategy(SunriseOgleUSDJPY, **short_kwargs)
        
        try: cerebro_short.addobserver(bt.observers.BuySell, barplot=False, plotdist=SunriseOgleUSDJPY.params.buy_sell_plotdist)
        except Exception: pass
        if SunriseOgleUSDJPY.params.plot_sltp_lines:
            try: cerebro_short.addobserver(SLTPObserver)
            except Exception: pass
        try: cerebro_short.addobserver(bt.observers.Value)
        except Exception: pass
        
        results_short = cerebro_short.run()
        final_value_short = cerebro_short.broker.getvalue()
        
        print("\n=== DUAL CEREBRO SUMMARY ===")
        long_pnl = final_value_long - STARTING_CASH
        short_pnl = final_value_short - STARTING_CASH
        combined_pnl = long_pnl + short_pnl
        combined_value = STARTING_CASH + combined_pnl
        
        long_strategy = results_long[0]
        short_strategy = results_short[0]
        
        combined_trades = long_strategy.trades + short_strategy.trades
        combined_wins = long_strategy.wins + short_strategy.wins
        combined_losses = long_strategy.losses + short_strategy.losses
        combined_gross_profit = long_strategy.gross_profit + short_strategy.gross_profit
        combined_gross_loss = long_strategy.gross_loss + short_strategy.gross_loss
        
        combined_win_rate = (combined_wins / combined_trades * 100) if combined_trades > 0 else 0
        combined_pf = (combined_gross_profit / abs(combined_gross_loss)) if combined_gross_loss != 0 else float('inf')
        
        print(f" LONG-ONLY  PnL: {long_pnl:+,.2f} | Final: {final_value_long:,.2f}")
        print(f" SHORT-ONLY PnL: {short_pnl:+,.2f} | Final: {final_value_short:,.2f}")
        print(f" COMBINED   PnL: {combined_pnl:+,.2f} | Final: {combined_value:,.2f}")
        print(f" COMBINED Stats: Trades: {combined_trades} | Wins: {combined_wins} | Losses: {combined_losses} | WinRate: {combined_win_rate:.2f}% | PF: {combined_pf:.2f}")
        
        final_value = combined_value
        
    else:
        results = cerebro.run()
        final_value = cerebro.broker.getvalue()
        
    print(f"Final Value: {final_value:,.2f}")
        
    if not RUN_DUAL_CEREBRO and (ENABLE_PLOT or AUTO_PLOT_SINGLE_MODE):
        trading_mode = []
        if ENABLE_LONG_TRADES:
            trading_mode.append("LONG")
        if ENABLE_SHORT_TRADES:
            trading_mode.append("SHORT")
        
        mode_description = " & ".join(trading_mode) if trading_mode else "NO TRADES"
        
        if AUTO_PLOT_SINGLE_MODE or getattr(results[0].p, 'plot_result', False):
            try:
                strategy_result = results[0]
                final_pnl = final_value - STARTING_CASH
                plot_title = f'SUNRISE STRATEGY ({mode_description} MODE)\n'
                plot_title += f'Final Value: ${final_value:,.0f} | P&L: {final_pnl:+,.0f} | '
                plot_title += f'Trades: {strategy_result.trades} | Win Rate: {(strategy_result.wins/strategy_result.trades*100) if strategy_result.trades > 0 else 0:.1f}%'
                
                print(f"📊 Showing {mode_description} strategy chart...")
                cerebro.plot(style='candlestick', subtitle=plot_title)
            except Exception as e: 
                print(f"Plot error: {e}")
        else:
            print(f"📊 Plotting disabled. Set ENABLE_PLOT=True and AUTO_PLOT_SINGLE_MODE=True to show charts.")
    
elif not RUN_DUAL_CEREBRO:
    print(f"📊 Plotting disabled. Set ENABLE_PLOT=True to show charts.")
