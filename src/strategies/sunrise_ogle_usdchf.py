"""Advanced Sunrise Strategy - USDCHF Trading System
===================================================
CLEAN VERSION: This is a cleaned and optimized version focused exclusively on USDCHF trading.
All other assets (Gold, Silver, EURUSD, GBPUSD, AUDUSD) have been removed for simplicity.

This strategy implements a sophisticated trading system optimized for USDCHF with the following features:

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
  
  KEY PARAMETERS for Volatility Expansion:
  - window_offset_multiplier: Delay window opening (0.5-2.0 recommended)
  - long_entry_window_periods: Breakout monitoring duration LONG (3-10 bars)
  • short_entry_window_periods: Breakout monitoring duration SHORT (3-10 bars)
  • long_pullback_max_candles: Required pullback depth LONG (1-3 candles)
  • short_pullback_max_candles: Required pullback depth SHORT (1-3 candles)

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

ATR VOLATILITY FILTER
----------------------
🌊 PURPOSE: Ensures trades occur during sufficient market volatility
   - LONG: ATR range 0.000200-0.000600 with decrement filtering (-0.000050 to -0.000001)
   - SHORT: ATR range 0.000400-0.000750 with increment filtering (0.000010 to 0.000150)
   - ATR change requirement measures market momentum direction
   - Pullback mode: Compares ATR from signal detection to breakout phase
   - Standard mode: Checks current ATR against minimum threshold

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
💱 FOREX PAIR: USDCHF (USD vs Swiss Franc)
   - Standard 100K lot sizes
   - 0.0001 pip values (4 decimal places)
   - 30:1 leverage with 3.33% margin

🤖 CONFIGURATION: Instrument settings optimized for USDCHF
   - Pip values: 0.0001
   - Lot sizes: 100,000 USD
   - Margin requirements: 3.33%

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

VOLATILITY EXPANSION PARAMETERS
-------------------------------
🎯 WINDOW OFFSET CONTROL (Critical for Entry Timing):
   • window_offset_multiplier (Default: 1.0)
     - Controls delay between pullback confirmation and window opening
     - Formula: window_start = current_bar + (pullback_count × multiplier)
     - Values: 0.5 = immediate, 1.0 = standard, 2.0 = delayed
     - Higher values = more confirmation, potentially missed opportunities
     - Lower values = faster entries, potentially premature

🔄 PULLBACK REQUIREMENTS:
   • long_pullback_max_candles (Default: 1)
     - Number of red candles required before LONG breakout window opens
     - Range: 1-3 candles (1=aggressive, 3=conservative)
   
   • short_pullback_max_candles (Default: 2) 
     - Number of green candles required before SHORT breakout window opens
     - Range: 1-3 candles (1=aggressive, 3=conservative)

⏱️ WINDOW DURATION:
   • long_entry_window_periods (Default: 7)
     - Bars to monitor for LONG breakout after window opens
     - Range: 3-10 bars (shorter=stricter timing, longer=more opportunities)
   
   • short_entry_window_periods (Default: 7)
     - Bars to monitor for SHORT breakout after window opens
     - Range: 3-10 bars (shorter=stricter timing, longer=more opportunities)

💡 OPTIMIZATION TIPS:
   - Conservative: pullback_candles=3, window_periods=5, offset=1.5
   - Balanced: pullback_candles=2, window_periods=7, offset=1.0
   - Aggressive: pullback_candles=1, window_periods=10, offset=0.5

CONFIGURATION
-------------
📍 All settings moved to TOP of file for easy access:
   - Instrument selection (DATA_FILENAME)
   - Date ranges, cash, plotting options  
   - Trading hours: 7:00-17:00 UTC (configurable)
   - Direction control: LONG/SHORT/BOTH modes
   
🔧 Strategy parameters in params dict for runtime overrides
📊 Visual plotting with buy/sell signals and SL/TP lines

PERFORMANCE FEATURES
-------------------
⚡ Optimized entry filtering to reduce false signals
🎯 Pullback system improves risk/reward ratios
🎯 Multiple exit strategies for different market conditions
📊 Real-time performance statistics and trade tracking

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
# 💡 Find detailed explanations below in their respective sections
# ⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡

# === INSTRUMENT SELECTION ===
# Cleaned version - USDCHF only
DATA_FILENAME = 'USDCHF_5m_5Yea.csv'     # 🇭 USD vs Swiss Franc - Major Forex Pair

# === BACKTEST SETTINGS ===
FROMDATE = '2025-12-01'               # Start date for backtesting (YYYY-MM-DD)
TODATE = '2025-12-05'                 # End date for backtesting (YYYY-MM-DD)
STARTING_CASH = 100000.0              # Initial account balance in USD
QUICK_TEST = False                    # True: Reduce to last 10 days for quick testing
LIMIT_BARS = 0                        # >0: Stop after N bars processed (0 = no limit)
ENABLE_PLOT = True                    # Show final chart with trades (requires matplotlib)

# === FOREX CONFIGURATION ===
ENABLE_FOREX_CALC = True              # Enable advanced forex position calculations
FOREX_INSTRUMENT = 'USDCHF'           # Fixed to USDCHF (no auto-detection needed)
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
LONG_USE_ATR_FILTER = True                 # Enable ATR-based volatility filtering for long entries
LONG_ATR_MIN_THRESHOLD = 0.000300          
LONG_ATR_MAX_THRESHOLD = 0.000700          
# ATR INCREMENT FILTER (DISABLED - Inferior Performance)
LONG_USE_ATR_INCREMENT_FILTER = False       # 🎯 OPTIMIZED: Increments showed inferior performance
LONG_ATR_INCREMENT_MIN_THRESHOLD = 0.000011 # EXPANDED: Much wider range for more entries
LONG_ATR_INCREMENT_MAX_THRESHOLD = 0.000080 # EXPANDED: Much wider range for more entries
# ATR DECREMENT FILTER (OPTIMIZED - Only very low changes)
LONG_USE_ATR_DECREMENT_FILTER = False        # 🎯 OPTIMIZED: Decrements with better performance
LONG_ATR_DECREMENT_MIN_THRESHOLD = -0.000030 # 🎯 EXPANDED: Much wider range for more entries
LONG_ATR_DECREMENT_MAX_THRESHOLD = -0.000001 # 🎯 EXPANDED: Much wider range for more entries

# === SHORT ATR VOLATILITY FILTER ===
SHORT_USE_ATR_FILTER = True                 # Enable ATR-based volatility filtering for short entries  
SHORT_ATR_MIN_THRESHOLD = 0.000400         # 🎯 OPTIMIZED: Same optimal range as LONG
SHORT_ATR_MAX_THRESHOLD = 0.000750         # 🎯 OPTIMIZED: Consistent with LONG analysis
# ATR INCREMENT FILTER
SHORT_USE_ATR_INCREMENT_FILTER = True      # 🎯 OPTIMIZED: Increments showed inferior performance
SHORT_ATR_INCREMENT_MIN_THRESHOLD = 0.000001 # EXPANDED: Much wider range for more entries
SHORT_ATR_INCREMENT_MAX_THRESHOLD = 0.001000 # EXPANDED: Much wider range for more entries
# ATR DECREMENT FILTER 
SHORT_USE_ATR_DECREMENT_FILTER = True       # 🎯 OPTIMIZED: Decrements with better performance
SHORT_ATR_DECREMENT_MIN_THRESHOLD = -0.000080 # 🎯 EXPANDED: Much wider range for more entries
SHORT_ATR_DECREMENT_MAX_THRESHOLD = -0.000020 # 🎯 EXPANDED: Much wider range for more entries

# === LONG ENTRY FILTERS ===
LONG_USE_EMA_ORDER_CONDITION = False        # Require confirm_EMA > all other EMAs for long entries
LONG_USE_PRICE_FILTER_EMA = True            # Require close > filter_EMA (trend alignment) for long entries
LONG_USE_CANDLE_DIRECTION_FILTER = False     # Require previous candle bullish (close[1] > open[1]) for long entries
LONG_USE_ANGLE_FILTER = False                # Require minimum EMA slope angle for long entries
LONG_MIN_ANGLE = 40.0                       # EXPANDED: Much wider angle range for more entries
LONG_MAX_ANGLE = 80.0                       # EXPANDED: Much wider angle range for more entries
LONG_ANGLE_SCALE_FACTOR = 10000.0           # Scaling factor for angle calculation sensitivity (long entries)

# === SHORT ENTRY FILTERS ===
SHORT_USE_EMA_ORDER_CONDITION = False      # Require confirm_EMA < all other EMAs for short entries
SHORT_USE_PRICE_FILTER_EMA = True           # Require close < filter_EMA (trend alignment) for short entries  
SHORT_USE_CANDLE_DIRECTION_FILTER = True    # Require previous candle bearish (close[1] < open[1]) for short entries
SHORT_USE_ANGLE_FILTER = True               # Require minimum EMA slope angle for short entries
SHORT_MIN_ANGLE = -90.0                     # EXPANDED: Much wider angle range for more entries
SHORT_MAX_ANGLE = -20.0                     # EXPANDED: Much wider angle range for more entries
SHORT_ANGLE_SCALE_FACTOR = 10000.0          # Scaling factor for angle calculation sensitivity (short entries)

# === LONG PULLBACK ENTRY SYSTEM ===
LONG_USE_PULLBACK_ENTRY = True             # Enable 3-phase pullback entry system for long entries
LONG_PULLBACK_MAX_CANDLES = 2              # Max red candles in pullback for long entries (1-3 recommended)
LONG_ENTRY_WINDOW_PERIODS = 2 #10 #7             # Bars to wait for breakout after pullback (long entries)

# === SHORT PULLBACK ENTRY SYSTEM ===
SHORT_USE_PULLBACK_ENTRY = True            # Enable 3-phase pullback entry system for short entries
SHORT_PULLBACK_MAX_CANDLES = 2             # Max green candles in pullback for short entries (1-3 recommended)
SHORT_ENTRY_WINDOW_PERIODS = 7            # Bars to wait for breakdown after pullback (short entries)

# ===============================================================
# ⚡ VOLATILITY EXPANSION CHANNEL - KEY TIMING PARAMETERS ⚡
# ===============================================================
# 🎯 CRITICAL: These parameters control the advanced entry timing system
# 🔧 USE_WINDOW_TIME_OFFSET: Enable/disable time delay for window opening
USE_WINDOW_TIME_OFFSET = False              # NEW: Enable/disable the time delay for window opening
# 🔧 WINDOW_OFFSET_MULTIPLIER: Controls delay between pullback and window opening (only if USE_WINDOW_TIME_OFFSET=True)
WINDOW_OFFSET_MULTIPLIER = 1.0             # Window delay multiplier (0.5=fast, 1.0=standard, 2.0=conservative)
                                          # Formula: window_start = current_bar + (pullback_count × this_value)
                                          # 🔬 EXPERIMENT: Try 0.5 for aggressive, 1.5 for conservative entries
# 🔧 WINDOW_PRICE_OFFSET_MULTIPLIER: Controls the price expansion of the two-sided channel
WINDOW_PRICE_OFFSET_MULTIPLIER = 0.01 #0.05      # NEW: Price expansion multiplier (0.5 = 50% of candle range)
                                          # Formula: channel_width = candle_range × this_value
# ===============================================================

# === TIME RANGE FILTER ===
USE_TIME_RANGE_FILTER = True              # ENABLED: Time filter for complete analysis
ENTRY_START_HOUR = 7#6                      # Start hour for entry window (UTC)
ENTRY_START_MINUTE = 0                     # Start minute for entry window (UTC)
ENTRY_END_HOUR = 13#18 #15                        # End hour for entry window (UTC)
ENTRY_END_MINUTE = 0#59                      # End minute for entry window (UTC)


class SunriseOgle(bt.Strategy):
    params = dict(
        # === TECHNICAL INDICATORS ===
        ema_fast_length=18, #14              # Fast EMA period for trend detection #14
        ema_medium_length=18,             # Medium EMA period for trend confirmation #18
        ema_slow_length=24, #24,               # Slow EMA period for trend strength # 24
        ema_confirm_length=1,             # Confirmation EMA (usually 1 for immediate response)
        ema_filter_price_length=50,#70       # Price filter EMA to avoid counter-trend trades #50
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
        long_atr_sl_multiplier=2.5,  #1.5                          # Stop Loss multiplier for LONG trades
        long_atr_tp_multiplier=10, #10                           # Take Profit multiplier for LONG trades
        
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
        short_atr_sl_multiplier=2.5,                             # Stop Loss multiplier for SHORT trades
        short_atr_tp_multiplier=6.5,#3.5,                             # Take Profit multiplier for SHORT trades

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
        forex_instrument='USDCHF',        # Fixed to USDCHF
        forex_base_currency='USD',        # Base currency: USD
        forex_quote_currency='CHF',       # Quote currency: CHF
        forex_pip_value=0.0001,           # Pip value for USDCHF
        forex_pip_decimal_places=4,       # Price decimal places for USDCHF
        forex_lot_size=100000,            # Lot size for USDCHF (100K USD)
        forex_micro_lot_size=0.01,        # Minimum lot increment (0.01 standard lots)
        forex_spread_pips=2.2,            # Typical spread in pips for USDCHF
        forex_margin_required=3.33,       # Margin requirement % for USDCHF (30:1 leverage)
        
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
                print(f"🎯 DEBUG: Used entry_window_start: {self.entry_window_start}, bars = {periods_before_entry}")
            elif hasattr(self, 'signal_detection_bar') and self.signal_detection_bar is not None:
                # Secondary: Use signal detection bar
                periods_before_entry = current_bar - self.signal_detection_bar
                print(f"🎯 DEBUG: Used signal_detection_bar: {self.signal_detection_bar}, bars = {periods_before_entry}")
            elif hasattr(self, 'window_bar_start') and self.window_bar_start is not None:
                # Tertiary: Use window_bar_start if available
                periods_before_entry = current_bar - self.window_bar_start
                print(f"🎯 DEBUG: Used window_bar_start: {self.window_bar_start}, bars = {periods_before_entry}")
            else:
                # Quaternary: Estimate based on pullback count + 1
                fallback_bars_to_entry = getattr(self, 'pullback_candle_count', 0) + 1
                periods_before_entry = fallback_bars_to_entry
                print(f"🎯 DEBUG: Used fallback calculation: pullback_count={getattr(self, 'pullback_candle_count', 0)} + 1 = {periods_before_entry}")
            
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
            print(f"🔍 DEBUG: entry_atr_increment = {stored_increment}")  # DEBUG
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
                print(f"🚨 DEBUG: ATR Change = N/A because entry_atr_increment is None")  # DEBUG
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
                    if direction == 'LONG':
                        # For LONG: entry between stop and take
                        entry_price = (stop_level + take_level) / 2
                    else:  # SHORT
                        # For SHORT: entry between stop and take
                        entry_price = (stop_level + take_level) / 2
                
                # Calculate pips based on direction and P&L
                pips = 0.0
                if entry_price and exit_price:
                    if direction == 'LONG':
                        pips = (exit_price - entry_price) / 0.0001  # Forex pip calculation
                    else:  # SHORT
                        pips = (entry_price - exit_price) / 0.0001  # Forex pip calculation
                
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

    def _cross_below(self, a, b):
        """Return True if `a` crossed below `b` on the current bar.
        
        Pine Script ta.crossunder() equivalent:
        - Current bar: a[0] < b[0] 
        - Previous bar: a[-1] >= b[-1]
        - Must be EXACT crossover (not just below)
        """
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
        """Compute instantaneous angle (degrees) of the confirm EMA slope.

        Equivalent to Pine's math.atan(rise/run) * 180 / pi with run=1.
        The rise gets magnified by `angle_scale_factor` for sensitivity.
        """
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
        """Calculate optimal position size for forex trading with proper risk management.
        
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
        
        # Calculate value per pip for USDCHF
        # For USDCHF: 1 standard lot (100,000 units) = $10 per pip (0.0001 price move)
        
        if self.p.forex_quote_currency == 'USD':
            value_per_pip_per_lot = (self.p.forex_pip_value * self.p.forex_lot_size)
        else:
            # For USDCHF, we need to convert CHF to USD using current exchange rate
            # Simplified: use approximate $10 per pip for standard lot
            value_per_pip_per_lot = 10.0
        
        # Calculate optimal lot size
        if pip_risk > 0:
            optimal_lots = risk_amount / (pip_risk * value_per_pip_per_lot)
            optimal_lots = max(self.p.forex_micro_lot_size, 
                             round(optimal_lots / self.p.forex_micro_lot_size) * self.p.forex_micro_lot_size)
        else:
            return None, None, None, None, None
        
        # REMOVE RESTRICTIVE LIMITS: Let user control their own risk
        # Only apply absolute minimum safety to prevent system errors
        
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
        
        # Convert to Backtrader contracts for USDCHF
        # For USDCHF: Use lot size directly 
        contracts = max(1, int(optimal_lots * 100))  # Scale lots to reasonable contract size
        print(f"DEBUG_POSITION_SIZE: optimal_lots={optimal_lots:.2f}, contracts={contracts}")
        
        return optimal_lots, contracts, margin_required, pip_risk, position_value
    
    def _format_forex_trade_info(self, entry_price, stop_loss, take_profit, lot_size, pip_risk, position_value, margin_required):
        """Format comprehensive forex trade information for logging.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            lot_size: Position size in lots
            pip_risk: Risk in pips
            position_value: Total position value
            margin_required: Margin requirement
            
        Returns:
            str: Formatted trade information
        """
        if not self.p.use_forex_position_calc:
            return ""
            
        # Calculate potential profit in pips
        if take_profit and entry_price:
            profit_pips = abs(take_profit - entry_price) / self.p.forex_pip_value
            risk_reward = profit_pips / pip_risk if pip_risk > 0 else 0
        else:
            profit_pips = 0
            risk_reward = 0
            
        # Calculate monetary values for USDCHF
        # Standard USD pairs: $10 per pip for standard lot
        pip_value_per_lot = 10.0
            
        risk_amount = pip_risk * lot_size * pip_value_per_lot
        profit_potential = profit_pips * lot_size * pip_value_per_lot
        spread_cost = self.p.forex_spread_pips * lot_size * pip_value_per_lot
        
        # Format units for USDCHF
        units_desc = f"{lot_size * self.p.forex_lot_size:,.0f} {self.p.forex_base_currency}"
        
        # Format prices based on decimal places
        price_format = f"{{:.{self.p.forex_pip_decimal_places}f}}"
        
        return (f"\n--- FOREX TRADE DETAILS ({self.p.forex_instrument}) ---\n"
                f"Position Size: {lot_size:.2f} lots ({units_desc})\n"
                f"Position Value: ${position_value:,.2f}\n"
                f"Margin Required: ${margin_required:,.2f} ({self.p.forex_margin_required}%)\n"
                f"Entry: {price_format.format(entry_price)} | SL: {price_format.format(stop_loss)} | TP: {price_format.format(take_profit)}\n"
                f"Risk: {pip_risk:.1f} pips (${risk_amount:.2f}) | Profit: {profit_pips:.1f} pips (${profit_potential:.2f})\n"
                f"Risk/Reward: 1:{risk_reward:.2f} | Spread Cost: ${spread_cost:.2f}\n"
                f"Account Leverage: {self.p.account_leverage:.0f}:1 | Account: {self.p.account_currency}")
    
    def _validate_forex_setup(self):
        """Validate forex configuration for USDCHF.
        
        Returns:
            bool: True if configuration is valid for USDCHF data
        """
        if not self.p.use_forex_position_calc:
            return True
            
        # Check if data filename matches USDCHF
        data_filename = getattr(self, '_data_filename', '')
        if 'USDCHF' not in data_filename.upper():
            print(f"WARNING: Data file is {data_filename} but strategy is configured for USDCHF")
            
        # Validate price ranges for USDCHF
        if hasattr(self.data, 'close') and len(self.data.close) > 0:
            current_price = float(self.data.close[0])
            if current_price < 0.7 or current_price > 1.3:
                print(f"WARNING: Price {current_price} seems unusual for USDCHF (expected range: 0.7-1.3)")
                
        # Check pip value consistency for USDCHF
        if self.p.forex_pip_value != 0.0001:
            print(f"INFO: USDCHF typically uses pip value of 0.0001, current setting: {self.p.forex_pip_value}")
            
        return True
    
    def _get_forex_instrument_config(self, instrument_name=None):
        """Get forex configuration for USDCHF instrument.
        
        Args:
            instrument_name: Override instrument name (defaults to USDCHF)
            
        Returns:
            dict: Configuration dictionary for USDCHF
        """
        # Auto-detect instrument from data filename if not specified
        if instrument_name is None or instrument_name == 'AUTO':
            data_filename = getattr(self, '_data_filename', '').upper()
            
            # Try to detect instrument from filename
            if 'USDCHF' in data_filename:
                instrument_name = 'USDCHF'
            else:
                instrument_name = 'USDCHF'  # Default to USDCHF for this cleaned version
        
        # USDCHF configuration only
        config = {
            'USDCHF': {  # USD vs Swiss Franc
                'base_currency': 'USD',
                'quote_currency': 'CHF',
                'pip_value': 0.0001,         # 1 pip = $0.0001
                'pip_decimal_places': 4,
                'lot_size': 100000,          # 100,000 USD
                'margin_required': 3.33,     # 3.33% (30:1 leverage)
                'typical_spread': 2.2
            }
        }
        
        return config.get(instrument_name, config['USDCHF'])
    
    def _apply_forex_config(self):
        """Apply forex configuration for USDCHF."""
        if not self.p.use_forex_position_calc:
            return
            
        # Get configuration for USDCHF
        config = self._get_forex_instrument_config('USDCHF')
        
        # Update parameters with USDCHF configuration
        self.p.forex_base_currency = config['base_currency']
        self.p.forex_quote_currency = config['quote_currency']
        
        # Store detected instrument for logging
        self._detected_instrument = 'USDCHF'
        data_filename = getattr(self, '_data_filename', '').upper()
                
        # Apply USDCHF configuration
        self.p.forex_pip_value = config['pip_value']
        self.p.forex_pip_decimal_places = config['pip_decimal_places']
        self.p.forex_lot_size = config['lot_size']
        self.p.forex_margin_required = config['margin_required']
        self.p.forex_spread_pips = config['typical_spread']
        # Update the instrument parameter with USDCHF
        self.p.forex_instrument = 'USDCHF'
                
        # Log forex configuration
        print(f"CONFIGURED: USDCHF from filename: {data_filename}")
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
        """PHASE 1: Scan for initial EMA crossover signals
        
        Returns:
            str or None: 'LONG' or 'SHORT' if signal detected, None otherwise
        """
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
                    # ✅ CRITICAL FIX: Store ATR when LONG signal is detected 
                    current_atr = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
                    self.signal_detection_atr = current_atr
                    return 'LONG'

        # Check SHORT signals
        if self.p.enable_short_trades:
            # Previous candle bearish check (optional)
            try:
                prev_bear = self.data.close[-1] < self.data.open[-1]
            except IndexError:
                prev_bear = False

            # EMA crossover check (ANY of the three) - BELOW for SHORT
            cross_fast = self._cross_below(self.ema_confirm, self.ema_fast)
            cross_medium = self._cross_below(self.ema_confirm, self.ema_medium) 
            cross_slow = self._cross_below(self.ema_confirm, self.ema_slow)
            cross_any = cross_fast or cross_medium or cross_slow
            
            # Check candle direction filter (optional)
            candle_direction_ok = True
            if self.p.short_use_candle_direction_filter:
                candle_direction_ok = prev_bear
            
            if candle_direction_ok and cross_any:
                # Apply additional filters
                signal_valid = True
                
                # EMA order condition (SHORT: confirm < others)
                if self.p.short_use_ema_order_condition:
                    ema_order_ok = (
                        self.ema_confirm[0] < self.ema_fast[0] and
                        self.ema_confirm[0] < self.ema_medium[0] and
                        self.ema_confirm[0] < self.ema_slow[0]
                    )
                    if not ema_order_ok:
                        signal_valid = False

                # Price filter EMA (SHORT: close < filter)
                if signal_valid and self.p.short_use_price_filter_ema:
                    price_below_filter = self.data.close[0] < self.ema_filter_price[0]
                    if not price_below_filter:
                        signal_valid = False

                # Angle filter (SHORT: negative angle range)
                if signal_valid and self.p.short_use_angle_filter:
                    current_angle = self._angle()
                    angle_ok = self.p.short_min_angle <= current_angle <= self.p.short_max_angle
                    if not angle_ok:
                        signal_valid = False

                # ATR volatility filter (SHORT)
                if signal_valid and self.p.short_use_atr_filter:
                    current_atr = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
                    if current_atr < self.p.short_atr_min_threshold or current_atr > self.p.short_atr_max_threshold:
                        signal_valid = False

                if signal_valid:
                    # ✅ CRITICAL FIX: Store ATR when SHORT signal is detected
                    current_atr = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
                    self.signal_detection_atr = current_atr
                    if self.p.print_signals:
                        print(f"SHORT SIGNAL DETECTED - {self.data.datetime.datetime(0)}:")
                        print(f"   Previous bearish candle: close[-1]={self.data.close[-1]:.5f} < open[-1]={self.data.open[-1]:.5f}")
                        print(f"   All filters passed, proceeding to ARMED_SHORT state")
                        print(f"   Signal detection ATR: {current_atr:.6f}")
                    return 'SHORT'

        return None

    def _phase2_confirm_pullback(self, armed_direction):
        """PHASE 2: Count pullback candles and validate pullback sequence
        
        Args:
            armed_direction: 'LONG' or 'SHORT'
            
        Returns:
            bool: True if pullback conditions are satisfied
        """
        # Check candle direction for pullback
        is_pullback_candle = False
        
        if armed_direction == 'LONG':
            # For LONG: pullback = bearish candle (close < open)
            is_pullback_candle = self.data.close[0] < self.data.open[0]
        else:  # SHORT
            # For SHORT: pullback = bullish candle (close > open)
            is_pullback_candle = self.data.close[0] > self.data.open[0]
        
        if is_pullback_candle:
            self.pullback_candle_count += 1
            
            # Check if we've reached the required pullback count based on direction
            max_candles = (self.p.long_pullback_max_candles if armed_direction == 'LONG' 
                          else self.p.short_pullback_max_candles)
            
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
        """PHASE 3: Open the two-sided breakout window after pullback confirmation
        
        Implements true volatility expansion channel with:
        - Optional time offset controlled by use_window_time_offset parameter
        - Two-sided channel with success and failure boundaries
        - Breaking failure boundary resets to ARMED state (instability detection)
        
        Args:
            armed_direction: 'LONG' or 'SHORT'
        """
        current_bar = len(self)

        # 1. Implement Optional Time Offset
        window_start_bar = current_bar
        if self.p.use_window_time_offset:
            time_offset = int(self.pullback_candle_count * self.p.window_offset_multiplier)
            window_start_bar = current_bar + time_offset
        
        self.window_bar_start = window_start_bar
        
        # 2. Set Window Duration
        window_periods = (self.p.long_entry_window_periods if armed_direction == 'LONG' 
                         else self.p.short_entry_window_periods)
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
            success_level = self.window_top_limit if armed_direction == 'LONG' else self.window_bottom_limit
            failure_level = self.window_bottom_limit if armed_direction == 'LONG' else self.window_top_limit
            print(f"  - Success Level: {' > ' if armed_direction == 'LONG' else ' < '}{success_level:.5f}")
            print(f"  - Failure Level: {' < ' if armed_direction == 'LONG' else ' > '}{failure_level:.5f}")
            print(f"  - Channel Range: {last_low:.5f} to {last_high:.5f} + {price_offset:.5f} offset")

    def _phase4_monitor_window(self, armed_direction):
        """PHASE 4: Monitor for breakout or failure within the two-sided channel
        
        Implements true volatility expansion channel with:
        - Success boundaries for entry signals
        - Failure boundaries that indicate instability and reset to ARMED state
        - Window timeout handling
        
        Args:
            armed_direction: 'LONG' or 'SHORT'
            
        Returns:
            str: 'SUCCESS' if breakout detected, None if no action needed
        """
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

        elif armed_direction == 'SHORT':
            # Check for SUCCESS condition first (break below bottom_limit)
            if current_low <= self.window_bottom_limit:
                if self.p.print_signals:
                    print(f"SUCCESS BREAKOUT (SHORT): Price {current_low:.5f} broke below success level {self.window_bottom_limit:.5f}")
                return 'SUCCESS'

            # Check for FAILURE condition (break above top_limit - indicates instability)
            elif current_high >= self.window_top_limit:
                if self.p.print_signals:
                    print(f"FAILURE BREAKOUT (SHORT): Price {current_high:.5f} broke above failure level {self.window_top_limit:.5f}. Instability detected.")
                self.entry_state = "ARMED_SHORT"  # Return to pullback search
                self.pullback_candle_count = 0
                self.window_top_limit, self.window_bottom_limit, self.window_expiry_bar = None, None, None
                self.window_breakout_level = None
                return None
        
        return None  # No breakout yet, continue monitoring

    def next(self):
        """Main strategy logic using volatility expansion channel entry system with 4-phase state machine"""
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
            
            # Determine position direction (LONG = positive size, SHORT = negative size)
            position_direction = 'LONG' if self.position.size > 0 else 'SHORT'
            
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
        if self.entry_state in ["ARMED_LONG", "ARMED_SHORT"]:
            opposing_signal = None
            
            if self.entry_state == "ARMED_LONG":
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
                    
            elif self.entry_state == "ARMED_SHORT":
                # Check for bullish signal that would invalidate SHORT setup
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
                
                # 🔧 CRITICAL FIX: Store the original signal candle for validation
                self.signal_trigger_candle = {
                    'open': float(self.data.open[-1]),
                    'close': float(self.data.close[-1]),
                    'high': float(self.data.high[-1]),
                    'low': float(self.data.low[-1]),
                    'datetime': self.data.datetime.datetime(-1),
                    'is_bullish': self.data.close[-1] > self.data.open[-1],
                    'is_bearish': self.data.close[-1] < self.data.open[-1]
                }
                
                # 🔍 DEBUG: Show trigger candle storage for SHORT signals
                if signal_direction == 'SHORT':
                    prev_close = self.data.close[-1]
                    prev_open = self.data.open[-1]
                    print(f"\n🔍 SHORT SIGNAL TRIGGER STORAGE - {dt:%Y-%m-%d %H:%M}:")
                    print(f"   📦 STORING Trigger Candle: O:{prev_open:.5f} C:{prev_close:.5f}")
                    print(f"   📦 Candle Type: {'BEARISH' if prev_close < prev_open else 'BULLISH' if prev_close > prev_open else 'DOJI'}")
                    print(f"   📦 Raw Flags: is_bullish={prev_close > prev_open} | is_bearish={prev_close < prev_open}")
                    print(f"   🎯 This candle will be used for validation when entry executes")
                
                if self.p.print_signals:
                    print(f"STATE TRANSITION: SCANNING → ARMED_{signal_direction} at {dt:%Y-%m-%d %H:%M}")
                    print(f"   Signal detection candle: close[-1]={self.data.close[-1]:.5f} open[-1]={self.data.open[-1]:.5f}")
                    print(f"   Bearish previous candle: {self.data.close[-1] < self.data.open[-1]}")
                    print(f"   Starting pullback confirmation phase...")
                
        elif self.entry_state in ["ARMED_LONG", "ARMED_SHORT"]:
            # PHASE 2: Confirm pullback
            if self._phase2_confirm_pullback(self.armed_direction):
                # Transition to WINDOW_OPEN state
                self.entry_state = "WINDOW_OPEN"
                self._phase3_open_breakout_window(self.armed_direction)
                if self.p.print_signals:
                    print(f"STATE TRANSITION: ARMED_{self.armed_direction} → WINDOW_OPEN at {dt:%Y-%m-%d %H:%M}")
                    print(f"   Previous candle at window open: close[-1]={self.data.close[-1]:.5f} open[-1]={self.data.open[-1]:.5f}")
                    print(f"   Bearish previous candle: {self.data.close[-1] < self.data.open[-1]} (required for SHORT)")
                    print(f"   Pullback complete, window monitoring begins...")
                
        elif self.entry_state == "WINDOW_OPEN":
            # PHASE 4: Monitor window for breakout
            breakout_status = self._phase4_monitor_window(self.armed_direction)
            
            if breakout_status == 'SUCCESS':
                # BREAKOUT DETECTED - VALIDATE TIME FILTER BEFORE ENTRY
                # Check time range filter for final entry execution
                if not self._is_in_trading_time_range(dt):
                    if self.p.print_signals:
                        print(f"❌ ENTRY BLOCKED: Breakout detected but outside trading hours - {dt.hour:02d}:{dt.minute:02d} outside {self.p.entry_start_hour:02d}:{self.p.entry_start_minute:02d}-{self.p.entry_end_hour:02d}:{self.p.entry_end_minute:02d} UTC")
                    self._reset_entry_state()
                    return
                
                # EXECUTE ENTRY
                signal_direction = self.armed_direction
                
                # ✅ CRITICAL: Validate against ORIGINAL signal trigger candle, not current previous candle
                if hasattr(self, 'signal_trigger_candle') and self.signal_trigger_candle:
                    trigger_candle = self.signal_trigger_candle
                    candle_body = abs(trigger_candle['close'] - trigger_candle['open'])
                    min_body_size = 0.00001
                    
                    # Use stored trigger candle colors
                    current_prev_candle_bullish = trigger_candle['is_bullish'] and candle_body >= min_body_size
                    current_prev_candle_bearish = trigger_candle['is_bearish'] and candle_body >= min_body_size
                    
                    # 🔍 CRITICAL DEBUG: Track every SHORT entry validation
                    if signal_direction == 'SHORT':
                        print(f"\n🔍 SHORT ENTRY VALIDATION DEBUG - {self.data.datetime.datetime(0)}:")
                        print(f"   📊 STORED Trigger Candle: {trigger_candle['datetime']}")
                        print(f"   📊 STORED O:{trigger_candle['open']:.5f} H:{trigger_candle['high']:.5f} L:{trigger_candle['low']:.5f} C:{trigger_candle['close']:.5f}")
                        print(f"   📊 STORED Body: {candle_body:.5f} | Bullish: {trigger_candle['is_bullish']} | Bearish: {trigger_candle['is_bearish']}")
                        print(f"   ⚖️  Final Validation: Bullish={current_prev_candle_bullish} | Bearish={current_prev_candle_bearish}")
                        print(f"   🎯 Current Price: {self.data.close[0]:.5f} | Bar: {len(self)}")
                        
                        # 🚨 CRITICAL: Show exactly what candle we're validating against vs current candle
                        current_candle = f"O:{self.data.open[-1]:.5f} C:{self.data.close[-1]:.5f}"
                        stored_candle = f"O:{trigger_candle['open']:.5f} C:{trigger_candle['close']:.5f}"
                        print(f"   🔄 COMPARISON: Current Previous [{current_candle}] vs Stored Trigger [{stored_candle}]")
                        
                        if not current_prev_candle_bearish:
                            print(f"   🚨 CRITICAL ERROR: SHORT entry with NON-BEARISH trigger candle!")
                            print(f"       Trigger candle is {'BULLISH' if trigger_candle['is_bullish'] else 'DOJI/NEUTRAL'}!")
                            print(f"       This violates the core strategy rule: SHORT entries require bearish previous candles!")
                    
                else:
                    # Fallback to current previous candle if trigger candle not stored
                    prev_close = self.data.close[-1]
                    prev_open = self.data.open[-1]
                    candle_body = abs(prev_close - prev_open)
                    min_body_size = 0.00001
                    
                    current_prev_candle_bullish = (prev_close > prev_open) and (candle_body >= min_body_size)
                    current_prev_candle_bearish = (prev_close < prev_open) and (candle_body >= min_body_size)
                    
                    if self.p.print_signals:
                        print(f"⚠️ FALLBACK: Using current previous candle for validation")
                
                # Validate previous candle color matches signal direction (optional)
                candle_direction_valid = True
                
                if signal_direction == 'LONG' and self.p.long_use_candle_direction_filter:
                    if not current_prev_candle_bullish:
                        candle_direction_valid = False
                        if self.p.print_signals:
                            trigger_close = trigger_candle['close']
                            trigger_open = trigger_candle['open']
                            print(f"❌ LONG ENTRY BLOCKED: Previous candle is not bullish (close[-1]={trigger_close:.5f} open[-1]={trigger_open:.5f} body={candle_body:.5f})")
                        self._reset_entry_state()
                        return
                
                elif signal_direction == 'SHORT' and self.p.short_use_candle_direction_filter:
                    if not current_prev_candle_bearish:
                        candle_direction_valid = False
                        if self.p.print_signals:
                            trigger_close = trigger_candle['close']
                            trigger_open = trigger_candle['open']
                            print(f"❌ SHORT ENTRY BLOCKED: Previous candle is not bearish (close[-1]={trigger_close:.5f} open[-1]={trigger_open:.5f} body={candle_body:.5f})")
                            print(f"   🚨 ERROR: SHORT entry attempted after BULLISH candle! This violates strategy rules!")
                        self._reset_entry_state()
                        return
                
                # 🔧 CRITICAL FIX: Validate ALL entry filters BEFORE any entry execution
                if signal_direction == 'LONG':
                    if not self._validate_all_entry_filters():
                        if self.p.print_signals:
                            print(f"❌ ENTRY BLOCKED: LONG entry validation failed (angle/ATR filters)")
                        self._reset_entry_state()
                        return
                elif signal_direction == 'SHORT':
                    if not self._validate_all_short_entry_filters():
                        if self.p.print_signals:
                            print(f"❌ ENTRY BLOCKED: SHORT entry validation failed (angle/ATR filters)")
                        self._reset_entry_state()
                        return
                
                if self.p.print_signals:
                    print(f"✅ PULLBACK ENTRY VALIDATION PASSED: {signal_direction} with prev candle bullish={current_prev_candle_bullish} bearish={current_prev_candle_bearish} body={candle_body:.5f}")
                
                # 🔧 FINAL TIME FILTER CHECK: Ensure no entries outside trading hours
                dt = bt.num2date(self.data.datetime[0])
                if not self._is_in_trading_time_range(dt):
                    if self.p.print_signals:
                        print(f"❌ ENTRY BLOCKED: {signal_direction} entry rejected - {dt.hour:02d}:{dt.minute:02d} outside {self.p.entry_start_hour:02d}:{self.p.entry_start_minute:02d}-{self.p.entry_end_hour:02d}:{self.p.entry_end_minute:02d} UTC")
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
                elif signal_direction == 'SHORT':
                    self.stop_level = bar_high + atr_now * self.p.short_atr_sl_multiplier  # Stop above for shorts
                    self.take_level = bar_low - atr_now * self.p.short_atr_tp_multiplier   # Take below for shorts
                
                self.initial_stop_level = self.stop_level

                # Position sizing calculation
                if self.p.enable_risk_sizing:
                    if signal_direction == 'LONG':
                        raw_risk = entry_price - self.stop_level
                    else:  # SHORT
                        raw_risk = self.stop_level - entry_price
                        
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
                elif signal_direction == 'SHORT':
                    self.order = self.sell(size=bt_size)
                    signal_type_display = " SHORT SELL"

                # Print entry confirmation
                if self.p.print_signals:
                    if signal_direction == 'LONG':
                        rr = (self.take_level - entry_price) / (entry_price - self.stop_level) if (entry_price - self.stop_level) > 0 else float('nan')
                    else:  # SHORT
                        rr = (entry_price - self.take_level) / (self.stop_level - entry_price) if (self.stop_level - entry_price) > 0 else float('nan')
                    
                    print(f"🎯 VOLATILITY EXPANSION ENTRY{signal_type_display} {dt:%Y-%m-%d %H:%M} price={entry_price:.5f} size={bt_size} SL={self.stop_level:.5f} TP={self.take_level:.5f} RR={rr:.2f}")

                # ✅ CRITICAL FIX: Calculate ATR change for trade recording
                # Get current ATR and compare with signal detection ATR if available
                current_atr = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
                
                if hasattr(self, 'signal_detection_atr') and self.signal_detection_atr is not None:
                    self.entry_atr_increment = current_atr - self.signal_detection_atr
                    self.entry_signal_detection_atr = self.signal_detection_atr
                else:
                    self.entry_atr_increment = None
                    self.entry_signal_detection_atr = None

                # Record trade entry for reporting
                self._record_trade_entry(signal_direction, dt, entry_price, bt_size, atr_now)

                self.last_entry_price = entry_price
                self.last_entry_bar = current_bar
                
                # Reset state machine after entry
                self._reset_entry_state()
                
                # Reset signal tracking variables AFTER trade recording is complete
                self._reset_signal_tracking()

    def _full_entry_signal(self):
        """Return tuple (signal_type, has_signal) for entry constraints.

        Returns:
            ('LONG', True) if LONG entry conditions met
            ('SHORT', True) if SHORT entry conditions met  
            (None, False) if no entry conditions met
        """
        dt = bt.num2date(self.data.datetime[0])
        
        # Check LONG signals if enabled
        if self.p.enable_long_trades:
            if self.p.long_use_pullback_entry:
                long_signal = self._handle_pullback_entry(dt, 'LONG')
            else:
                long_signal = self._standard_entry_signal(dt, 'LONG')
            
            if long_signal:
                return ('LONG', True)
        
        # Check SHORT signals if enabled  
        if self.p.enable_short_trades:
            if self.p.short_use_pullback_entry:
                short_signal = self._handle_pullback_entry(dt, 'SHORT')
            else:
                short_signal = self._standard_entry_signal(dt, 'SHORT')
            
            if short_signal:
                return ('SHORT', True)
        
        return (None, False)
    
    def _standard_entry_signal(self, dt, direction):
        """Standard entry logic without pullback system
        
        Args:
            dt: Current datetime
            direction: 'LONG' or 'SHORT'
        """
        if direction == 'LONG':
            return self._standard_long_entry_signal(dt)
        elif direction == 'SHORT':
            return self._standard_short_entry_signal(dt)
        else:
            return False
    
    def _standard_long_entry_signal(self, dt):
        """Standard LONG entry logic without pullback system"""        
        # 1. Previous candle bullish check (optional)
        try:
            prev_bull = self.data.close[-1] > self.data.open[-1]
        except IndexError:
            prev_bull = False

        # Check candle direction filter (optional)
        candle_direction_ok = True
        if self.p.long_use_candle_direction_filter:
            candle_direction_ok = prev_bull
            if not candle_direction_ok:
                return False

        # 2. EMA crossover check (ANY of the three) - ABOVE for LONG
        cross_fast = self._cross_above(self.ema_confirm, self.ema_fast)
        cross_medium = self._cross_above(self.ema_confirm, self.ema_medium) 
        cross_slow = self._cross_above(self.ema_confirm, self.ema_slow)
        cross_any = cross_fast or cross_medium or cross_slow
        
        if not (prev_bull and cross_any):
            return False

        # 3. EMA order condition (LONG: confirm > others)
        if self.p.long_use_ema_order_condition:
            ema_order_ok = (
                self.ema_confirm[0] > self.ema_fast[0] and
                self.ema_confirm[0] > self.ema_medium[0] and
                self.ema_confirm[0] > self.ema_slow[0]
            )
            if not ema_order_ok:
                return False

        # 4. Price filter EMA (LONG: close > filter)
        if self.p.long_use_price_filter_ema:
            price_above_filter = self.data.close[0] > self.ema_filter_price[0]
            if not price_above_filter:
                return False

        # 5. Angle filter (LONG: positive angle range)
        if self.p.long_use_angle_filter:
            current_angle = self._angle()
            angle_ok = self.p.long_min_angle <= current_angle <= self.p.long_max_angle
            if not angle_ok:
                if self.p.verbose_debug:
                    print(f"Angle Filter: LONG entry rejected - angle {current_angle:.1f}° outside range [{self.p.long_min_angle:.1f}°, {self.p.long_max_angle:.1f}°]")
                return False

        # 6. ATR volatility filter (LONG)
        if self.p.long_use_atr_filter:
            current_atr = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
            if current_atr < self.p.long_atr_min_threshold:
                if self.p.verbose_debug:
                    print(f"ATR Filter: LONG entry rejected - ATR {current_atr:.6f} < min threshold {self.p.long_atr_min_threshold:.6f}")
                return False
            if current_atr > self.p.long_atr_max_threshold:
                if self.p.verbose_debug:
                    print(f"ATR Filter: LONG entry rejected - ATR {current_atr:.6f} > max threshold {self.p.long_atr_max_threshold:.6f}")
                return False

        return True

    def _standard_short_entry_signal(self, dt):
        """Standard SHORT entry logic without pullback system"""        
        # 1. Previous candle bearish check (optional)
        try:
            prev_bear = self.data.close[-1] < self.data.open[-1]
        except IndexError:
            prev_bear = False

        # Check candle direction filter (optional)
        candle_direction_ok = True
        if self.p.short_use_candle_direction_filter:
            candle_direction_ok = prev_bear
            if not candle_direction_ok:
                return False

        # 2. EMA crossover check (ANY of the three) - BELOW for SHORT
        cross_fast = self._cross_below(self.ema_confirm, self.ema_fast)
        cross_medium = self._cross_below(self.ema_confirm, self.ema_medium) 
        cross_slow = self._cross_below(self.ema_confirm, self.ema_slow)
        cross_any = cross_fast or cross_medium or cross_slow
        
        if not (prev_bear and cross_any):
            return False

        # 3. EMA order condition (SHORT: confirm < others)
        if self.p.short_use_ema_order_condition:
            ema_order_ok = (
                self.ema_confirm[0] < self.ema_fast[0] and
                self.ema_confirm[0] < self.ema_medium[0] and
                self.ema_confirm[0] < self.ema_slow[0]
            )
            if not ema_order_ok:
                return False

        # 4. Price filter EMA (SHORT: close < filter)
        if self.p.short_use_price_filter_ema:
            price_below_filter = self.data.close[0] < self.ema_filter_price[0]
            if not price_below_filter:
                return False

        # 5. Angle filter (SHORT: negative angle range)
        if self.p.short_use_angle_filter:
            current_angle = self._angle()
            angle_ok = self.p.short_min_angle <= current_angle <= self.p.short_max_angle
            if not angle_ok:
                if self.p.verbose_debug:
                    print(f"Angle Filter: SHORT entry rejected - angle {current_angle:.1f}° outside range [{self.p.short_min_angle:.1f}°, {self.p.short_max_angle:.1f}°]")
                return False

        # 6. ATR volatility filter (SHORT)
        if self.p.short_use_atr_filter:
            current_atr = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
            if current_atr < self.p.short_atr_min_threshold:
                if self.p.verbose_debug:
                    print(f"ATR Filter: SHORT entry rejected - ATR {current_atr:.6f} < min threshold {self.p.short_atr_min_threshold:.6f}")
                return False
            if current_atr > self.p.short_atr_max_threshold:
                if self.p.verbose_debug:
                    print(f"ATR Filter: SHORT entry rejected - ATR {current_atr:.6f} > max threshold {self.p.short_atr_max_threshold:.6f}")
                return False

        return True
    
    def _handle_pullback_entry(self, dt, direction='LONG'):
        """Pullback entry state machine logic
        
        Args:
            dt: Current datetime
            direction: 'LONG' or 'SHORT' signal direction
            
        Returns:
            Boolean indicating if entry should be executed
        """
        if direction == 'SHORT':
            return self._handle_short_pullback_entry(dt)
        else:
            return self._handle_long_pullback_entry(dt)
    
    def _handle_long_pullback_entry(self, dt):
        """LONG pullback entry state machine logic - 3-phase precise implementation"""
        # Check time range filter first
        if not self._is_in_trading_time_range(dt):
            if self.p.verbose_debug:
                print(f"Time Filter: LONG entry rejected - {dt.hour:02d}:{dt.minute:02d} outside {self.p.entry_start_hour:02d}:{self.p.entry_start_minute:02d}-{self.p.entry_end_hour:02d}:{self.p.entry_end_minute:02d} UTC")
            return False
            
        current_bar = len(self)
        current_close = float(self.data.close[0])
        current_open = float(self.data.open[0])
        current_high = float(self.data.high[0])
        
        # Check if current candle is red (bearish)
        is_red_candle = current_close < current_open
        
        # PHASE 1: SIGNAL DETECTION
        if self.pullback_state == "NORMAL":
            # Check for initial entry conditions (EMA crossover + previous bullish candle + filters)
            if self._basic_entry_conditions():
                # Store ATR value and bar number when signal is detected
                current_atr = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
                self.signal_detection_atr = current_atr
                self.signal_detection_bar = len(self)  # Track bar number when signal was detected
                
                # Check ATR range threshold if filter is enabled
                if self.p.long_use_atr_filter:
                    if current_atr < self.p.long_atr_min_threshold:
                        if self.p.verbose_debug:
                            print(f"ATR Filter: Signal rejected - ATR {current_atr:.6f} < min threshold {self.p.long_atr_min_threshold:.6f}")
                        return False
                    if current_atr > self.p.long_atr_max_threshold:
                        if self.p.verbose_debug:
                            print(f"ATR Filter: Signal rejected - ATR {current_atr:.6f} > max threshold {self.p.long_atr_max_threshold:.6f}")
                        return False
                
                # Transition to Phase 2: Wait for pullback
                self.pullback_state = "WAITING_PULLBACK"
                self.pullback_red_count = 0
                self.first_red_high = None
                self.breakout_target = None  # Will be set by first pullback candle
                return False  # Don't enter yet, wait for pullback
            return False
            
        # PHASE 2: PULLBACK WAIT & SETTING THE BREAKOUT LEVEL
        elif self.pullback_state == "WAITING_PULLBACK":
            if is_red_candle:
                self.pullback_red_count += 1
                
                # CRITICAL: Set breakout level ONLY from the FIRST red candle
                if self.pullback_red_count == 1:
                    self.first_red_high = current_high
                    # Set breakout target immediately when first pullback candle appears
                    self.breakout_target = self.first_red_high
                
                # Check if we exceeded max red candles
                if self.pullback_red_count > self.p.long_pullback_max_candles:
                    self._reset_pullback_state()
                    return False
                    
            else:  # Green candle - pullback sequence ended
                if self.pullback_red_count >= self.p.long_pullback_max_candles:
                    # Pullback sequence complete (required number of red candles occurred)
                    # Store ATR value when pullback phase ends
                    current_atr = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
                    self.pullback_start_atr = current_atr
                    
                    # Check ATR increment/decrement condition if filter is enabled
                    if self.p.long_use_atr_filter and self.signal_detection_atr is not None:
                        atr_change = current_atr - self.signal_detection_atr
                        
                        # ATR CHANGE FILTERING LOGIC
                        # Rule 1: If ATR is incrementing (positive change: low → high volatility)
                        if atr_change > 0:
                            if self.p.long_use_atr_increment_filter:
                                # Increment filter is ENABLED - check if within allowed range
                                if not (self.p.long_atr_increment_min_threshold <= atr_change <= self.p.long_atr_increment_max_threshold):
                                    if self.p.verbose_debug:
                                        print(f"ATR INCREMENT Filter: LONG pullback rejected - ATR increment {atr_change:+.6f} outside range [{self.p.long_atr_increment_min_threshold:.6f}, {self.p.long_atr_increment_max_threshold:.6f}]")
                                    self._reset_pullback_state()
                                    return False
                            else:
                                # Increment filter is DISABLED - reject ALL increments (based on analysis)
                                if self.p.verbose_debug:
                                    print(f"ATR INCREMENT Filter: LONG pullback rejected - ATR increment {atr_change:+.6f} (increment filter disabled, all increments rejected)")
                                self._reset_pullback_state()
                                return False
                        
                        # Rule 2: If ATR is decrementing (negative change: high → low volatility)
                        elif atr_change < 0:
                            if self.p.long_use_atr_decrement_filter:
                                # Decrement filter is ENABLED - check if atr_change is within optimal negative range
                                if not (self.p.long_atr_decrement_min_threshold <= atr_change <= self.p.long_atr_decrement_max_threshold):
                                    if self.p.verbose_debug:
                                        print(f"ATR DECREMENT Filter: LONG pullback rejected - ATR change {atr_change:+.6f} outside range [{self.p.long_atr_decrement_min_threshold:.6f}, {self.p.long_atr_decrement_max_threshold:.6f}]")
                                    self._reset_pullback_state()
                                    return False
                            # If decrement filter is DISABLED, allow all decrements (pass through)
                        
                        # Rule 3: If ATR change is exactly zero, allow it (no volatility change)
                    
                    # Transition to Phase 3: Start entry window countdown
                    self.pullback_state = "WAITING_BREAKOUT"
                    self.entry_window_start = current_bar
                else:
                    # No pullback occurred (no red candles), reset
                    self._reset_pullback_state()
            return False
            
        # PHASE 3: BREAKOUT CONFIRMATION AND ENTRY
        elif self.pullback_state == "WAITING_BREAKOUT":
            # Check if entry window expired
            bars_in_window = current_bar - self.entry_window_start
            if bars_in_window >= self.p.long_entry_window_periods:
                self._reset_pullback_state()
                return False
            
            # Entry Trigger Condition: current high >= breakout_target (already includes pip offset)
            if current_high >= self.breakout_target:
                # 🔧 CRITICAL FIX: Validate ALL filters BEFORE any entry processing
                if not self._validate_all_entry_filters():
                    if self.p.verbose_debug:
                        print(f"❌ ENTRY BLOCKED: LONG entry validation failed at breakout")
                    return False
                
                # Breakout detected! All entry conditions passed
                # Calculate ATR increment for validation and recording
                current_atr = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
                
                # Always calculate ATR change for reporting purposes
                if self.signal_detection_atr is not None:
                    atr_change = current_atr - self.signal_detection_atr
                    # Store values for trade recording (always, regardless of filter status)
                    self.entry_atr_increment = atr_change
                    self.entry_signal_detection_atr = self.signal_detection_atr
                else:
                    self.entry_atr_increment = None
                    self.entry_signal_detection_atr = None
                
                # Check ATR increment/decrement threshold if ATR filter is enabled
                if self.p.long_use_atr_filter and self.signal_detection_atr is not None:
                    atr_change = current_atr - self.signal_detection_atr
                    
                    # ATR CHANGE FILTERING LOGIC (ROBUST) 
                    # Rule 1: If ATR is incrementing (positive change: low → high volatility)
                    if atr_change > 0:
                        if self.p.long_use_atr_increment_filter:
                            # Increment filter is ENABLED - check if within allowed range
                            if not (self.p.long_atr_increment_min_threshold <= atr_change <= self.p.long_atr_increment_max_threshold):
                                if self.p.print_signals:
                                    print(f"ATR INCREMENT Filter: LONG entry rejected - ATR increment {atr_change:+.6f} outside range [{self.p.long_atr_increment_min_threshold:.6f}, {self.p.long_atr_increment_max_threshold:.6f}]")
                                return False
                        else:
                            # Increment filter is DISABLED - reject ALL increments (based on analysis)
                            if self.p.print_signals:
                                print(f"ATR INCREMENT Filter: LONG entry rejected - ATR increment {atr_change:+.6f} (increment filter disabled, all increments rejected)")
                            return False
                    
                    # Rule 2: If ATR is decrementing (negative change: high → low volatility)
                    elif atr_change < 0:
                        if self.p.long_use_atr_decrement_filter:
                            # Decrement filter is ENABLED - check if atr_change is within optimal negative range
                            if not (self.p.long_atr_decrement_min_threshold <= atr_change <= self.p.long_atr_decrement_max_threshold):
                                if self.p.print_signals:
                                    print(f"ATR DECREMENT Filter: LONG entry rejected - ATR change {atr_change:+.6f} outside range [{self.p.long_atr_decrement_min_threshold:.6f}, {self.p.long_atr_decrement_max_threshold:.6f}]")
                                return False
                        # If decrement filter is DISABLED, allow all decrements (pass through)
                    
                    # Rule 3: If ATR change is exactly zero, allow it (no volatility change)
                    
                    if self.p.print_signals:
                        atr_info = ""
                        if self.p.long_use_atr_filter and self.signal_detection_atr is not None:
                            atr_change = self.entry_atr_increment if self.entry_atr_increment is not None else current_atr - self.signal_detection_atr
                            atr_info = f" | ATR: {current_atr:.6f} (signal: {self.signal_detection_atr:.6f}, inc: {atr_change:+.6f})"
                        print(f"LONG BREAKOUT ENTRY! High={current_high:.5f} >= target={self.breakout_target:.5f}{atr_info}")
                    
                    # ✅ CRITICAL FIX: Store ATR values BEFORE reset to preserve them for trade recording
                    temp_signal_detection_atr = self.signal_detection_atr
                    temp_entry_atr_increment = self.entry_atr_increment
                    print(f"🔍 DEBUG LONG: Before reset - signal_detection_atr={temp_signal_detection_atr}, entry_atr_increment={temp_entry_atr_increment}")  # DEBUG
                    
                    # Reset state machine and trigger entry
                    self._reset_pullback_state()
                    
                    # ✅ CRITICAL FIX: Restore ATR values AFTER reset for trade recording
                    self.entry_signal_detection_atr = temp_signal_detection_atr
                    self.entry_atr_increment = temp_entry_atr_increment
                    print(f"🔍 DEBUG LONG: After restore - entry_signal_detection_atr={self.entry_signal_detection_atr}, entry_atr_increment={self.entry_atr_increment}")  # DEBUG
                    
                    return True
            return False
        
        return False
    
    def _handle_short_pullback_entry(self, dt):
        """SHORT pullback entry state machine logic - 3-phase precise implementation"""
        # Check time range filter first
        if not self._is_in_trading_time_range(dt):
            if self.p.verbose_debug:
                print(f"Time Filter: SHORT entry rejected - {dt.hour:02d}:{dt.minute:02d} outside {self.p.entry_start_hour:02d}:{self.p.entry_start_minute:02d}-{self.p.entry_end_hour:02d}:{self.p.entry_end_minute:02d} UTC")
            return False
            
        current_bar = len(self)
        current_close = float(self.data.close[0])
        current_open = float(self.data.open[0])
        current_low = float(self.data.low[0])
        
        # Check if current candle is green (bullish) - opposite for SHORT
        is_green_candle = current_close > current_open
        
        # PHASE 1: SIGNAL DETECTION
        if self.pullback_state == "NORMAL":
            # Check for initial SHORT entry conditions (EMA crossunder + previous bearish candle + filters)
            if self._basic_short_entry_conditions():
                # Store ATR value and bar number when signal is detected
                current_atr = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
                self.signal_detection_atr = current_atr
                self.signal_detection_bar = len(self)  # Track bar number when signal was detected
                
                # Check ATR range threshold if filter is enabled
                if self.p.short_use_atr_filter:
                    if current_atr < self.p.short_atr_min_threshold:
                        if self.p.verbose_debug:
                            print(f"SHORT ATR Filter: Signal rejected - ATR {current_atr:.6f} < min threshold {self.p.short_atr_min_threshold:.6f}")
                        return False
                    if current_atr > self.p.short_atr_max_threshold:
                        if self.p.verbose_debug:
                            print(f"SHORT ATR Filter: Signal rejected - ATR {current_atr:.6f} > max threshold {self.p.short_atr_max_threshold:.6f}")
                        return False
                
                # Transition to Phase 2: Wait for pullback
                self.pullback_state = "WAITING_PULLBACK"
                self.pullback_green_count = 0  # Count GREEN candles for SHORT
                self.first_green_low = None    # Store LOW of first green candle
                self.breakout_target = None    # Will be set by first pullback candle
                return False  # Don't enter yet, wait for pullback
            return False
            
        # PHASE 2: PULLBACK WAIT & SETTING THE BREAKOUT LEVEL
        elif self.pullback_state == "WAITING_PULLBACK":
            if is_green_candle:  # GREEN candles for SHORT pullback
                self.pullback_green_count += 1
                
                # CRITICAL: Set breakout level ONLY from the FIRST green candle
                if self.pullback_green_count == 1:
                    self.first_green_low = current_low
                    # Set breakout target immediately when first pullback candle appears
                    self.breakout_target = self.first_green_low
                
                # Check if we exceeded max green candles
                if self.pullback_green_count > self.p.short_pullback_max_candles:
                    self._reset_pullback_state()
                    return False
                    
            else:  # Red candle - pullback sequence ended
                if self.pullback_green_count >= self.p.short_pullback_max_candles:
                    # Pullback sequence complete (required number of green candles occurred)
                    # Store ATR value when pullback phase ends
                    current_atr = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
                    self.pullback_start_atr = current_atr
                    
                    # Check ATR increment/decrement condition if filter is enabled
                    if self.p.short_use_atr_filter and self.signal_detection_atr is not None:
                        atr_change = current_atr - self.signal_detection_atr
                        
                        # ATR CHANGE FILTERING LOGIC
                        # Rule 1: If ATR is incrementing (positive change: low → high volatility)
                        if atr_change > 0:
                            if self.p.short_use_atr_increment_filter:
                                # Increment filter is ENABLED - check if within allowed range
                                if not (self.p.short_atr_increment_min_threshold <= atr_change <= self.p.short_atr_increment_max_threshold):
                                    if self.p.verbose_debug:
                                        print(f"ATR INCREMENT Filter: SHORT pullback rejected - ATR increment {atr_change:+.6f} outside range [{self.p.short_atr_increment_min_threshold:.6f}, {self.p.short_atr_increment_max_threshold:.6f}]")
                                    self._reset_pullback_state()
                                    return False
                            # If increment filter is DISABLED, allow all increments for SHORT (different strategy)
                        
                        # Rule 2: If ATR is decrementing (negative change: high → low volatility)
                        elif atr_change < 0:
                            if self.p.short_use_atr_decrement_filter:
                                # Decrement filter is ENABLED - check if atr_change is within optimal negative range
                                if not (self.p.short_atr_decrement_min_threshold <= atr_change <= self.p.short_atr_decrement_max_threshold):
                                    if self.p.verbose_debug:
                                        print(f"ATR DECREMENT Filter: SHORT pullback rejected - ATR change {atr_change:+.6f} outside range [{self.p.short_atr_decrement_min_threshold:.6f}, {self.p.short_atr_decrement_max_threshold:.6f}]")
                                    self._reset_pullback_state()
                                    return False
                            # If decrement filter is DISABLED, allow all decrements (pass through)
                        
                        # Rule 3: If ATR change is exactly zero, allow it (no volatility change)
                    
                    # Transition to Phase 3: Start entry window countdown
                    self.pullback_state = "WAITING_BREAKOUT"
                    self.entry_window_start = current_bar
                else:
                    # No pullback occurred (no green candles), reset
                    self._reset_pullback_state()
            return False
            
        # PHASE 3: BREAKOUT CONFIRMATION AND ENTRY
        elif self.pullback_state == "WAITING_BREAKOUT":
            # Check if entry window expired
            bars_in_window = current_bar - self.entry_window_start
            # SAFETY CHECK: If bars_in_window is unreasonably high, reset state
            if bars_in_window > 50:  # Safety limit - should never exceed this
                self._reset_pullback_state()
                return False
            if bars_in_window >= self.p.short_entry_window_periods:
                self._reset_pullback_state()
                return False
            
            # Entry Trigger Condition: current low <= breakout_target (already includes pip offset)
            if current_low <= self.breakout_target:
                # 🔧 CRITICAL FIX: Validate ALL filters BEFORE any entry processing
                if not self._validate_all_short_entry_filters():
                    if self.p.verbose_debug:
                        print(f"❌ ENTRY BLOCKED: SHORT entry validation failed at breakout")
                    return False
                
                # Breakout detected! All SHORT entry conditions passed
                # Calculate ATR increment for validation and recording
                current_atr = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
                
                # Always calculate ATR change for reporting purposes
                if self.signal_detection_atr is not None:
                    atr_change = current_atr - self.signal_detection_atr
                    # Store values for trade recording (always, regardless of filter status)
                    self.entry_atr_increment = atr_change
                    self.entry_signal_detection_atr = self.signal_detection_atr
                else:
                    self.entry_atr_increment = None
                    self.entry_signal_detection_atr = None
                
                # Check ATR increment/decrement threshold if ATR filter is enabled
                if self.p.short_use_atr_filter and self.signal_detection_atr is not None:
                    atr_change = current_atr - self.signal_detection_atr
                    
                    # ATR CHANGE FILTERING LOGIC (ROBUST)
                    # Rule 1: If ATR is incrementing (positive change: low → high volatility)
                    if atr_change > 0:
                        if self.p.short_use_atr_increment_filter:
                            # Increment filter is ENABLED - check if within allowed range
                            if not (self.p.short_atr_increment_min_threshold <= atr_change <= self.p.short_atr_increment_max_threshold):
                                if self.p.print_signals:
                                    print(f"ATR INCREMENT Filter: SHORT entry rejected - ATR increment {atr_change:+.6f} outside range [{self.p.short_atr_increment_min_threshold:.6f}, {self.p.short_atr_increment_max_threshold:.6f}]")
                                return False
                        # If increment filter is DISABLED, allow all increments for SHORT (different strategy)
                    
                    # Rule 2: If ATR is decrementing (negative change: high → low volatility)
                    elif atr_change < 0:
                        if self.p.short_use_atr_decrement_filter:
                            # Decrement filter is ENABLED - check if atr_change is within optimal negative range
                            if not (self.p.short_atr_decrement_min_threshold <= atr_change <= self.p.short_atr_decrement_max_threshold):
                                if self.p.print_signals:
                                    print(f"ATR DECREMENT Filter: SHORT entry rejected - ATR change {atr_change:+.6f} outside range [{self.p.short_atr_decrement_min_threshold:.6f}, {self.p.short_atr_decrement_max_threshold:.6f}]")
                                return False
                        # If decrement filter is DISABLED, allow all decrements (pass through)
                    
                    # Rule 3: If ATR change is exactly zero, allow it (no volatility change)
                
                if self.p.print_signals:
                    atr_info = ""
                    if self.p.short_use_atr_filter and self.signal_detection_atr is not None:
                        atr_change = self.entry_atr_increment if self.entry_atr_increment is not None else current_atr - self.signal_detection_atr
                        atr_info = f" | ATR: {current_atr:.6f} (signal: {self.signal_detection_atr:.6f}, inc: {atr_change:+.6f})"
                    print(f"SHORT BREAKOUT ENTRY! Low={current_low:.5f} <= target={self.breakout_target:.5f}{atr_info}")
                
                # ✅ CRITICAL FIX: Store ATR values BEFORE reset to preserve them for trade recording
                temp_signal_detection_atr = self.signal_detection_atr
                temp_entry_atr_increment = self.entry_atr_increment
                print(f"🔍 DEBUG SHORT: Before reset - signal_detection_atr={temp_signal_detection_atr}, entry_atr_increment={temp_entry_atr_increment}")  # DEBUG
                
                # Reset state machine and trigger entry
                self._reset_pullback_state()
                
                # ✅ CRITICAL FIX: Restore ATR values AFTER reset for trade recording
                self.entry_signal_detection_atr = temp_signal_detection_atr
                self.entry_atr_increment = temp_entry_atr_increment
                print(f"🔍 DEBUG SHORT: After restore - entry_signal_detection_atr={self.entry_signal_detection_atr}, entry_atr_increment={self.entry_atr_increment}")  # DEBUG
                
                return True
            return False
        
        return False
    
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
    
    def _basic_entry_conditions(self):
        """Check basic entry conditions 1 & 2 for pullback system"""
        # 1. Previous candle bullish check (optional)
        try:
            prev_bull = self.data.close[-1] > self.data.open[-1]
        except IndexError:
            prev_bull = False

        # Check candle direction filter (optional)
        candle_direction_ok = True
        if self.p.long_use_candle_direction_filter:
            candle_direction_ok = prev_bull
            if not candle_direction_ok:
                return False

        # 2. EMA crossover check (ANY of the three)
        cross_fast = self._cross_above(self.ema_confirm, self.ema_fast)
        cross_medium = self._cross_above(self.ema_confirm, self.ema_medium) 
        cross_slow = self._cross_above(self.ema_confirm, self.ema_slow)
        cross_any = cross_fast or cross_medium or cross_slow
        
        return candle_direction_ok and cross_any
    
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

        # 5. Angle filter
        if self.p.long_use_angle_filter:
            current_angle = self._angle()
            angle_ok = self.p.long_min_angle <= current_angle <= self.p.long_max_angle
            if self.p.verbose_debug:
                print(f"🔍 ANGLE VALIDATION DEBUG - LONG Pullback Entry:")
                print(f"   📐 Current Angle: {current_angle:.2f}°")
                print(f"   📏 Required Range: {self.p.long_min_angle:.1f}° to {self.p.long_max_angle:.1f}°")
                print(f"   ✅ Angle OK: {angle_ok}")
            if not angle_ok:
                if self.p.verbose_debug:
                    print(f"❌ ANGLE FILTER REJECTED: LONG entry blocked - angle {current_angle:.2f}° outside range [{self.p.long_min_angle:.1f}°, {self.p.long_max_angle:.1f}°]")
                return False

        return True
    
    def _basic_short_entry_conditions(self):
        """Check basic SHORT entry conditions 1 & 2 for pullback system"""
        # 1. Previous candle bearish check (optional - opposite of LONG)
        try:
            prev_bear = self.data.close[-1] < self.data.open[-1]
        except IndexError:
            prev_bear = False

        # Check candle direction filter (optional)
        candle_direction_ok = True
        if self.p.short_use_candle_direction_filter:
            candle_direction_ok = prev_bear
            if not candle_direction_ok:
                return False

        # 2. EMA crossunder check (ANY of the three) - opposite of LONG
        cross_fast = self._cross_below(self.ema_confirm, self.ema_fast)
        cross_medium = self._cross_below(self.ema_confirm, self.ema_medium) 
        cross_slow = self._cross_below(self.ema_confirm, self.ema_slow)
        cross_any = cross_fast or cross_medium or cross_slow
        
        return candle_direction_ok and cross_any
    
    def _validate_all_short_entry_filters(self):
        """Validate all SHORT entry filters (3-6) for pullback entry"""
        # 3. EMA order condition (opposite of LONG)
        if self.p.short_use_ema_order_condition:
            ema_order_ok = (
                self.ema_confirm[0] < self.ema_fast[0] and
                self.ema_confirm[0] < self.ema_medium[0] and
                self.ema_confirm[0] < self.ema_slow[0]
            )
            if not ema_order_ok:
                return False

        # 4. Price filter EMA (opposite of LONG)
        if self.p.short_use_price_filter_ema:
            price_below_filter = self.data.close[0] < self.ema_filter_price[0]
            if not price_below_filter:
                return False

        # 5. Angle filter (opposite of LONG) - FIX: Use SHORT scale factor
        if self.p.short_use_angle_filter:
            # Calculate angle with SHORT scale factor (not LONG)
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
        # Reset LONG pullback variables
        self.pullback_red_count = 0
        self.first_red_high = None
        # Reset SHORT pullback variables
        self.pullback_green_count = 0
        self.first_green_low = None
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
        """Enhanced order notification with robust OCA group for SL/TP supporting both LONG and SHORT positions."""
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
                        print(f"✅ {entry_type} EXECUTED at {order.executed.price:.5f} size={order.executed.size}")

                    # Place SHORT protective orders (SELL SL/TP for LONG position)
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
                            print(f"🛡️  LONG PROTECTIVE OCA ORDERS: SL={self.stop_level:.5f} TP={self.take_level:.5f}")
                
                else:  # order.issell()
                    # SHORT position entry (SELL order)
                    entry_type = " SHORT SELL"
                    if self.p.print_signals:
                        print(f"✅ {entry_type} EXECUTED at {order.executed.price:.5f} size={order.executed.size}")

                    # Place LONG protective orders (BUY SL/TP for SHORT position)
                    if self.stop_level and self.take_level:
                        self.stop_order = self.buy(
                            size=order.executed.size,
                            exectype=bt.Order.Stop,
                            price=self.stop_level,  # Stop above entry for SHORT
                            oco=self.limit_order  # Link to TP order
                        )
                        self.limit_order = self.buy(
                            size=order.executed.size,
                            exectype=bt.Order.Limit,
                            price=self.take_level,  # Take below entry for SHORT
                            oco=self.stop_order  # Link to SL order
                        )
                        if self.p.print_signals:
                            print(f"🛡️  SHORT PROTECTIVE OCA ORDERS: SL={self.stop_level:.5f} TP={self.take_level:.5f}")
                
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
                position_type = " LONG" if order.issell() else " SHORT"
                
                if self.p.print_signals:
                    print(f"🔚 {position_type} EXIT EXECUTED at {exit_price:.5f} size={order.executed.size} reason={exit_reason}")

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
        # For LONG trades: PnL = (exit_price - entry_price) * size - commission
        # For SHORT trades: PnL = (entry_price - exit_price) * size - commission
        # In both cases: exit_price can be calculated from entry_price and pnl
        
        entry_price = self.last_entry_price if self.last_entry_price else 0
        position_direction = 'LONG' if trade.size > 0 else 'SHORT'
        
        if entry_price > 0 and trade.size != 0:
            # Calculate exit price from PnL
            if position_direction == 'LONG':
                # LONG: exit = entry + (pnl / size)
                exit_price = entry_price + (pnl / trade.size)
            else:
                # SHORT: exit = entry - (pnl / size) [size is negative for SHORT]
                exit_price = entry_price + (pnl / trade.size)  # This works for both since size is negative for SHORT
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
            # Calculate pips based on position direction
            if position_direction == 'LONG':
                pips = (exit_price - entry_price) / self.p.forex_pip_value if self.p.forex_pip_value and entry_price > 0 else 0
            else:  # SHORT
                pips = (entry_price - exit_price) / self.p.forex_pip_value if self.p.forex_pip_value and entry_price > 0 else 0
            
            print(f"{position_direction} TRADE CLOSED {dt:%Y-%m-%d %H:%M} reason={exit_reason} PnL={pnl:.2f} Pips={pips:.1f}")
            print(f"  Entry: {entry_price:.5f} -> Exit: {exit_price:.5f} | Size: {trade.size}")

        # Record trade exit for reporting
        self._record_trade_exit(dt, exit_price, pnl, exit_reason)

        # Reset levels
        self.stop_level = None
        self.take_level = None
        self.initial_stop_level = None
        
        # Reset pullback state after trade completion (both LONG and SHORT)
        if self.p.long_use_pullback_entry or self.p.short_use_pullback_entry:
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
        
        # Enhanced summary calculation with debug stats
        print("=== SUNRISE OGLE SUMMARY ===")
        
        # Calculate metrics
        wr = (self.wins / self.trades * 100.0) if self.trades else 0.0
        pf = (self.gross_profit / self.gross_loss) if self.gross_loss > 0 else float('inf')
        
        # Backtrader portfolio value
        final_value = self.broker.get_value()
        starting_cash = 100000.0  # Known starting value
        total_pnl = final_value - starting_cash
        
        print(f"Trades: {self.trades} Wins: {self.wins} Losses: {self.losses} WinRate: {wr:.2f}% PF: {pf:.2f}")
        print(f"Final Value: {final_value:,.2f} | Total PnL: {total_pnl:+,.2f}")
        
        # DEBUG STATISTICS
        print(f"\n=== ENTRY SIGNAL DEBUG STATS ===")
        print(f"Total Entry Signals Evaluated: {self.entry_signal_count}")
        print(f"Blocked Entries: {self.blocked_entry_count}")
        print(f"Successful Entries: {self.successful_entry_count}")
        if self.entry_signal_count > 0:
            block_rate = (self.blocked_entry_count / self.entry_signal_count) * 100
            success_rate = (self.successful_entry_count / self.entry_signal_count) * 100
            print(f"Block Rate: {block_rate:.1f}% | Success Rate: {success_rate:.1f}%")
        
        # Validation
        calculated_pnl = self.gross_profit - self.gross_loss
        pnl_diff = abs(calculated_pnl - total_pnl)
        if pnl_diff > 10.0:  # Allow for small rounding/fee differences
            print(f"INFO: PnL difference: {pnl_diff:.2f} (calculated: {calculated_pnl:+.2f})")

        if self.p.long_use_pullback_entry or self.p.short_use_pullback_entry:
            self._reset_pullback_state()
        
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


if __name__ == '__main__':
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
    STRAT_KWARGS = dict(
        plot_result=ENABLE_PLOT,
        use_forex_position_calc=ENABLE_FOREX_CALC,
        forex_instrument=FOREX_INSTRUMENT
    )
    
    if TEST_FOREX_MODE:
        # Quick test with forex calculations - reduce time period
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
    cerebro.adddata(data)
    cerebro.broker.setcash(STARTING_CASH)
    cerebro.broker.setcommission(leverage=30.0)
    cerebro.addstrategy(SunriseOgle, **STRAT_KWARGS)
    try: cerebro.addobserver(bt.observers.BuySell, barplot=False, plotdist=SunriseOgle.params.buy_sell_plotdist)
    except Exception: pass
    if SunriseOgle.params.plot_sltp_lines:
        try: cerebro.addobserver(SLTPObserver)
        except Exception: pass
    try: cerebro.addobserver(bt.observers.Value)
    except Exception: pass

    if LIMIT_BARS > 0:
        # Monkey-patch next() to stop early after LIMIT_BARS bars for quick experimentation.
        orig_next = SunriseOgle.next
        def limited_next(self):
            if len(self.data) >= LIMIT_BARS:
                self.env.runstop(); return
            orig_next(self)
        SunriseOgle.next = limited_next

    print(f"=== SUNRISE OGLE === (from {FROMDATE} to {TODATE})")
    if ENABLE_FOREX_CALC:
        print(f">> FOREX MODE ENABLED - Data: {DATA_FILENAME}")
        print(f">> Instrument: USDCHF (USD/CHF)")
    else:
        print(f" STANDARD MODE - Data: {DATA_FILENAME}")

    if RUN_DUAL_CEREBRO and ENABLE_LONG_TRADES and ENABLE_SHORT_TRADES:
        print(" DUAL CEREBRO MODE: Running separate LONG-only and SHORT-only strategies")
        
        # === LONG-ONLY CEREBRO ===
        print("\n RUNNING LONG-ONLY STRATEGY...")
        cerebro_long = bt.Cerebro(stdstats=False)
        data_long = bt.feeds.GenericCSVData(**feed_kwargs)
        cerebro_long.adddata(data_long)
        cerebro_long.broker.setcash(STARTING_CASH)
        cerebro_long.broker.setcommission(leverage=30.0)
        
        # Override to LONG-only
        long_kwargs = STRAT_KWARGS.copy()
        long_kwargs.update({
            'long_enabled': True,
            'short_enabled': False,
            'print_signals': True
        })
        cerebro_long.addstrategy(SunriseOgle, **long_kwargs)
        
        try: cerebro_long.addobserver(bt.observers.BuySell, barplot=False, plotdist=SunriseOgle.params.buy_sell_plotdist)
        except Exception: pass
        if SunriseOgle.params.plot_sltp_lines:
            try: cerebro_long.addobserver(SLTPObserver)
            except Exception: pass
        try: cerebro_long.addobserver(bt.observers.Value)
        except Exception: pass
        
        results_long = cerebro_long.run()
        final_value_long = cerebro_long.broker.getvalue()
        
        # === SHORT-ONLY CEREBRO ===
        print("\n RUNNING SHORT-ONLY STRATEGY...")
        cerebro_short = bt.Cerebro(stdstats=False)
        data_short = bt.feeds.GenericCSVData(**feed_kwargs)
        cerebro_short.adddata(data_short)
        cerebro_short.broker.setcash(STARTING_CASH)
        cerebro_short.broker.setcommission(leverage=30.0)
        
        # Override to SHORT-only
        short_kwargs = STRAT_KWARGS.copy()
        short_kwargs.update({
            'long_enabled': False,
            'short_enabled': True,
            'print_signals': True
        })
        cerebro_short.addstrategy(SunriseOgle, **short_kwargs)
        
        try: cerebro_short.addobserver(bt.observers.BuySell, barplot=False, plotdist=SunriseOgle.params.buy_sell_plotdist)
        except Exception: pass
        if SunriseOgle.params.plot_sltp_lines:
            try: cerebro_short.addobserver(SLTPObserver)
            except Exception: pass
        try: cerebro_short.addobserver(bt.observers.Value)
        except Exception: pass
        
        results_short = cerebro_short.run()
        final_value_short = cerebro_short.broker.getvalue()
        
        # === COMBINED RESULTS ===
        print("\n=== DUAL CEREBRO SUMMARY ===")
        long_pnl = final_value_long - STARTING_CASH
        short_pnl = final_value_short - STARTING_CASH
        combined_pnl = long_pnl + short_pnl
        combined_value = STARTING_CASH + combined_pnl
        
        # Extract individual strategy metrics
        long_strategy = results_long[0]
        short_strategy = results_short[0]
        
        # Calculate combined metrics
        combined_trades = long_strategy.trades + short_strategy.trades
        combined_wins = long_strategy.wins + short_strategy.wins
        combined_losses = long_strategy.losses + short_strategy.losses
        combined_gross_profit = long_strategy.gross_profit + short_strategy.gross_profit
        combined_gross_loss = long_strategy.gross_loss + short_strategy.gross_loss
        
        # Calculate combined ratios
        combined_win_rate = (combined_wins / combined_trades * 100) if combined_trades > 0 else 0
        combined_pf = (combined_gross_profit / abs(combined_gross_loss)) if combined_gross_loss != 0 else float('inf')
        
        print(f" LONG-ONLY  PnL: {long_pnl:+,.2f} | Final: {final_value_long:,.2f}")
        print(f" SHORT-ONLY PnL: {short_pnl:+,.2f} | Final: {final_value_short:,.2f}")
        print(f" COMBINED   PnL: {combined_pnl:+,.2f} | Final: {combined_value:,.2f}")
        print(f" COMBINED Stats: Trades: {combined_trades} | Wins: {combined_wins} | Losses: {combined_losses} | WinRate: {combined_win_rate:.2f}% | PF: {combined_pf:.2f}")
        
        # === COMBINED PLOT ===
        if ENABLE_PLOT and getattr(long_strategy.p, 'plot_result', False):
            print("\n📊 Creating combined portfolio performance chart with 5-minute time axis...")
            try:
                import matplotlib.pyplot as plt
                import numpy as np
                
                # Extract actual portfolio values from cerebros
                long_portfolio_values = []
                short_portfolio_values = []
                
                # Get data from LONG cerebro
                long_strat = cerebro_long.runstrats[0][0]  # First strategy instance
                if hasattr(long_strat, '_portfolio_values') and len(long_strat._portfolio_values) > 0:
                    long_portfolio_values = long_strat._portfolio_values
                    print(f" LONG portfolio data: {len(long_portfolio_values)} points")
                else:
                    print("⚠️  No LONG portfolio tracking data found")
                    long_portfolio_values = []
                
                # Get data from SHORT cerebro  
                short_strat = cerebro_short.runstrats[0][0]  # First strategy instance
                if hasattr(short_strat, '_portfolio_values') and len(short_strat._portfolio_values) > 0:
                    short_portfolio_values = short_strat._portfolio_values
                    print(f" SHORT portfolio data: {len(short_portfolio_values)} points")
                else:
                    print("⚠️  No SHORT portfolio tracking data found")
                    short_portfolio_values = []
                
                # If we have real portfolio data, plot it
                if len(long_portfolio_values) > 0 and len(short_portfolio_values) > 0:
                    # Make sure arrays are same length
                    min_len = min(len(long_portfolio_values), len(short_portfolio_values))
                    long_values = long_portfolio_values[:min_len]
                    short_values = short_portfolio_values[:min_len]
                    
                    # Calculate combined portfolio values
                    combined_values = [(l + s - STARTING_CASH) for l, s in zip(long_values, short_values)]
                    
                    # Create simple index for x-axis (5-minute intervals)
                    x_axis = list(range(len(combined_values)))
                    
                    # Create the portfolio chart
                    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
                    
                    # Main combined portfolio chart
                    ax1.plot(x_axis, combined_values, 
                            label=f' Combined Portfolio (+${combined_pnl:.2f})', 
                            linewidth=3, color='purple')
                    ax1.plot(x_axis, long_values, 
                            label=f' LONG Only (+${long_pnl:.2f})', 
                            linewidth=2, alpha=0.8, color='green')
                    ax1.plot(x_axis, short_values, 
                            label=f' SHORT Only (+${short_pnl:.2f})', 
                            linewidth=2, alpha=0.8, color='red')
                    ax1.axhline(y=STARTING_CASH, color='gray', linestyle='--', alpha=0.5, label='Break Even')
                    
                    ax1.set_title(f'SUNRISE DUAL CEREBRO - Portfolio Performance (5-minute bars)\n' +
                                 f'Combined: {combined_trades} trades | Win Rate: {combined_win_rate:.1f}% | PF: {combined_pf:.2f}', 
                                 fontsize=14, fontweight='bold')
                    ax1.set_ylabel('Portfolio Value ($)', fontweight='bold')
                    ax1.set_xlabel('5-Minute Bars', fontweight='bold')
                    ax1.legend(loc='upper left')
                    ax1.grid(True, alpha=0.3)
                    
                    # Performance metrics comparison
                    strategies = ['LONG Only', 'SHORT Only', 'Combined']
                    pnls = [long_pnl, short_pnl, combined_pnl]
                    colors = ['green', 'red', 'purple']
                    
                    bars = ax2.bar(strategies, pnls, color=colors, alpha=0.7)
                    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
                    ax2.set_title('Strategy Performance Comparison', fontweight='bold')
                    ax2.set_ylabel('P&L ($)', fontweight='bold')
                    ax2.grid(True, alpha=0.3, axis='y')
                    
                    # Add value labels on bars
                    for bar, pnl in zip(bars, pnls):
                        height = bar.get_height()
                        ax2.text(bar.get_x() + bar.get_width()/2., height + (100 if height >= 0 else -200),
                                f'${pnl:.0f}', ha='center', va='bottom' if height >= 0 else 'top', fontweight='bold')
                    
                    plt.tight_layout()
                    plt.show()
                    
                    print(f"✅ Combined portfolio chart created with {len(combined_values)} 5-minute intervals!")
                    
                else:
                    print("⚠️  Insufficient portfolio data, using simplified chart")
                    # Simple final values chart
                    strategies = ['LONG Only', 'SHORT Only', 'Combined']
                    final_values = [final_value_long, final_value_short, combined_value]
                    pnls = [long_pnl, short_pnl, combined_pnl]
                    colors = ['green', 'red', 'purple']
                    
                    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
                    
                    # Final values
                    bars1 = ax1.bar(strategies, final_values, color=colors, alpha=0.7)
                    ax1.axhline(y=STARTING_CASH, color='gray', linestyle='--', alpha=0.5, label='Starting Cash')
                    ax1.set_title(f'SUNRISE DUAL CEREBRO - Final Portfolio Values\n' +
                                 f'Combined: {combined_trades} trades | Win Rate: {combined_win_rate:.1f}% | PF: {combined_pf:.2f}', 
                                 fontweight='bold')
                    ax1.set_ylabel('Final Portfolio Value ($)', fontweight='bold')
                    ax1.legend()
                    ax1.grid(True, alpha=0.3, axis='y')
                    
                    # P&L comparison
                    bars2 = ax2.bar(strategies, pnls, color=colors, alpha=0.7)
                    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
                    ax2.set_title('Strategy Performance Comparison', fontweight='bold')
                    ax2.set_ylabel('P&L ($)', fontweight='bold')
                    ax2.grid(True, alpha=0.3, axis='y')
                    
                    # Add value labels
                    for bar, val in zip(bars1, final_values):
                        height = bar.get_height()
                        ax1.text(bar.get_x() + bar.get_width()/2., height + 500,
                                f'${val:,.0f}', ha='center', va='bottom', fontweight='bold')
                    
                    for bar, pnl in zip(bars2, pnls):
                        height = bar.get_height()
                        ax2.text(bar.get_x() + bar.get_width()/2., height + (100 if height >= 0 else -200),
                                f'${pnl:.0f}', ha='center', va='bottom' if height >= 0 else 'top', fontweight='bold')
                    
                    plt.tight_layout()
                    plt.show()
                    
                    print("✅ Simplified portfolio comparison chart created!")
                
                # Optional: Show individual strategy plots with backtrader native charts
                if SHOW_INDIVIDUAL_PLOTS:
                    try:
                        user_input = input("\n📊 Show individual Backtrader charts with entries/exits? (y/n): ").lower().strip()
                        if user_input in ['y', 'yes']:
                            print(" Showing LONG strategy chart...")
                            long_title = f'LONG STRATEGY | PnL: +${long_pnl:.2f} | Trades: {long_strategy.trades}'
                            cerebro_long.plot(style='candlestick', subtitle=long_title)
                            
                            print(" Showing SHORT strategy chart...")
                            short_title = f'SHORT STRATEGY | PnL: +${short_pnl:.2f} | Trades: {short_strategy.trades}'
                            cerebro_short.plot(style='candlestick', subtitle=short_title)
                    except:
                        pass
                
            except Exception as e:
                print(f"Combined plot error: {e}")
                print("� Falling back to separate strategy plots...")
                
                # Fallback: Show LONG strategy plot with combined info
                plot_title = f'LONG STRATEGY (Part of Dual Cerebro)\nLONG PnL: {long_pnl:+,.0f} ({long_strategy.trades} trades) | COMBINED PnL: {combined_pnl:+,.0f}'
                print("� Showing LONG strategy plot...")
                cerebro_long.plot(style='candlestick', subtitle=plot_title)
                
                # Ask if user wants to see SHORT plot separately
                try:
                    user_input = input("\n Show SHORT strategy plot separately? (y/n): ").lower().strip()
                    if user_input in ['y', 'yes']:
                        short_title = f'SHORT STRATEGY (Part of Dual Cerebro)\nSHORT PnL: {short_pnl:+,.0f} ({short_strategy.trades} trades)'
                        print(" Showing SHORT strategy plot...")
                        cerebro_short.plot(style='candlestick', subtitle=short_title)
                except:
                    pass
        
        # Use combined results as the final result
        final_value = combined_value
        
    else:
        # === SINGLE CEREBRO MODE ===
        cerebro = bt.Cerebro(stdstats=False)
        cerebro.adddata(data)
        cerebro.broker.setcash(STARTING_CASH)
        cerebro.broker.setcommission(leverage=30.0)
        cerebro.addstrategy(SunriseOgle, **STRAT_KWARGS)
        try: cerebro.addobserver(bt.observers.BuySell, barplot=False, plotdist=SunriseOgle.params.buy_sell_plotdist)
        except Exception: pass
        if SunriseOgle.params.plot_sltp_lines:
            try: cerebro.addobserver(SLTPObserver)
            except Exception: pass
        try: cerebro.addobserver(bt.observers.Value)
        except Exception: pass

        if LIMIT_BARS > 0:
            # Monkey-patch next() to stop early after LIMIT_BARS bars for quick experimentation.
            orig_next = SunriseOgle.next
            def limited_next(self):
                if len(self.data) >= LIMIT_BARS:
                    self.env.runstop(); return
                orig_next(self)
            SunriseOgle.next = limited_next

        results = cerebro.run()
        final_value = cerebro.broker.getvalue()
    
    print(f"Final Value: {final_value:,.2f}")
    
    # Enhanced plotting logic for single mode - FIX: Include AUTO_PLOT_SINGLE_MODE condition
    if not RUN_DUAL_CEREBRO and (ENABLE_PLOT or AUTO_PLOT_SINGLE_MODE):
        # Determine trading mode for plot title
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
