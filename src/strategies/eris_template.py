"""ERIS Strategy - Simplified Pullback Breakout System (Long-Only)
================================================================
ERIS (Expert Robotic Investment System) - A lean, simplified strategy
based on lessons learned from Sunrise Ogle, following SOLID principles.

PATTERN DESCRIPTION
-------------------
1. Bullish candle (close > open) - marked as candle "1"
2. Exactly N bearish pullback candles (close < open) - candles "2", "3", etc.
3. Entry on breakout above the HIGH of candle "1"
4. Optional: require N green candles BEFORE the bullish candle "1"

CONFIGURABLE PARAMETERS
-----------------------
- LONG_PULLBACK_NUM_CANDLES: Exact number of bearish candles required (default: 2)
- LONG_BREAKOUT_DELAY: Enable/disable delay after pullback (default: True)
- LONG_BREAKOUT_DELAY_CANDLES: Number of candles to ignore after pullback (default: 1)
- LONG_ENTRY_MAX_CANDLES: Maximum candles to wait for breakout (default: 7)
- LONG_BEFORE_CANDLES: Enable requirement for green candles before pattern (default: False)
- LONG_BEFORE_NUM_CANDLES: Number of green candles required before pattern (default: 1)

EXIT SYSTEM
-----------
ATR-based Stop Loss and Take Profit (OCA orders):
- Stop Loss = entry_price - (ATR x long_atr_sl_multiplier)
- Take Profit = entry_price + (ATR x long_atr_tp_multiplier)

DISCLAIMER
----------
Educational and research purposes ONLY. Not investment advice.
Trading involves substantial risk of loss. Past performance does not
guarantee future results.
"""
from __future__ import annotations
import math
from pathlib import Path
from datetime import datetime, timedelta
import backtrader as bt


# =============================================================================
# CONFIGURATION PARAMETERS
# =============================================================================

# === INSTRUMENT SELECTION ===
DATA_FILENAME = 'USDCHF_5m_5Yea.csv'

# === BACKTEST SETTINGS ===
FROMDATE = '2020-01-01'
TODATE = '2025-12-01'
STARTING_CASH = 100000.0
ENABLE_PLOT = True

# === FOREX CONFIGURATION ===
FOREX_INSTRUMENT = 'USDCHF'

# === TRADE REPORTING ===
EXPORT_TRADE_REPORTS = True

# =============================================================================
# ERIS PATTERN PARAMETERS
# =============================================================================

# Exact number of bearish pullback candles required after bullish candle
LONG_PULLBACK_NUM_CANDLES = 1  # OPTIMIZED: Reduced from 2 to 1

# Breakout delay - ignore N candles after pullback before allowing entry
LONG_BREAKOUT_DELAY = False
LONG_BREAKOUT_DELAY_CANDLES = 1

# Maximum candles to wait for breakout after pullback (expiry)
LONG_ENTRY_MAX_CANDLES = 5  # OPTIMIZED: Reduced from 7 to 5

# Require N green candles before the bullish trigger candle
LONG_BEFORE_CANDLES = True  # OPTIMIZED: Enabled
LONG_BEFORE_NUM_CANDLES = 1

# =============================================================================
# TIME FILTER PARAMETERS
# =============================================================================

# Enable time range filter (best performing hours)
# Analysis: [14:00-22:00) has PF 1.51 with 239 trades
USE_TIME_RANGE_FILTER = False  # OPTIMIZED: Enabled for better quality entries
TRADING_START_HOUR = 14   # Start trading at 14:00 (US session overlap)
TRADING_END_HOUR = 22     # Stop trading at 22:00

# =============================================================================
# ATR FILTER PARAMETERS  
# =============================================================================

# Filter trades by ATR range (avoid extreme volatility)
USE_ATR_FILTER = False
ATR_MIN_THRESHOLD = 0.00025  # Minimum ATR for trade (based on analysis)
ATR_MAX_THRESHOLD = 0.00040  # Maximum ATR for trade (based on analysis)

# =============================================================================
# HOURS TO AVOID FILTER PARAMETERS
# =============================================================================

# Enable filter to avoid specific hours with poor performance
# Disabled: Using TIME_RANGE_FILTER instead for simpler implementation
USE_HOURS_TO_AVOID_FILTER = False  # Disabled, using TIME_RANGE_FILTER

# Hours to avoid (UTC) - based on analysis showing PF < 1.0
# Hour 3: PF 0.93 | Hour 6: PF 0.89 | Hour 7: PF 0.88 | Hour 10: PF 0.77
# Hour 13: PF 0.71 | Hour 20: PF 0.38
# Avoiding these hours: 515 trades, WR 45.4%, PF 1.59, Net $30,182
HOURS_TO_AVOID = [3, 6, 7, 10, 13, 20]

# =============================================================================
# RISK MANAGEMENT PARAMETERS
# =============================================================================

# ATR settings for SL/TP calculation
ATR_LENGTH = 10  # OPTIMIZED: Increased from 10 to 14
LONG_ATR_SL_MULTIPLIER = 1.0  # Restored to 1.0 for proper risk management
LONG_ATR_TP_MULTIPLIER = 5.0  # Restored to 2.0 for 1:2 R:R

# Position sizing
RISK_PERCENT = 0.01  # 1% risk per trade

# =============================================================================
# MEAN REVERSION INDICATOR PARAMETERS (Ernest P. Chan)
# =============================================================================

# Enable Mean Reversion visualization indicator
USE_MEAN_REVERSION_INDICATOR = True

# EMA period for the mean (center line)
MEAN_REVERSION_EMA_PERIOD = 70

# ATR period for deviation calculation
MEAN_REVERSION_ATR_PERIOD = 10

# Deviation multiplier (how many ATRs from mean to draw bands)
MEAN_REVERSION_DEVIATION_MULT = 2.0

# Z-Score thresholds for overbought/oversold zones
MEAN_REVERSION_ZSCORE_UPPER = 2.0   # Above this = overbought
MEAN_REVERSION_ZSCORE_LOWER = -2.0  # Below this = oversold

# =============================================================================
# MEAN REVERSION ENTRY FILTER PARAMETERS
# =============================================================================

# Enable Mean Reversion as entry filter (only enter when price is in oversold zone)
USE_MEAN_REVERSION_ENTRY_FILTER = True

# Z-Score range for valid entries (only enter when Z-Score is within this range)
# Analysis: Z-Score -3.0 to -2.0 has PF=1.44 with 234 trades (good balance)
MR_ENTRY_ZSCORE_MIN = -3.0   # Minimum Z-Score (more oversold limit)
MR_ENTRY_ZSCORE_MAX = -1.0   # Maximum Z-Score (more restrictive for quality)

# =============================================================================
# OVERSOLD DURATION FILTER PARAMETERS
# =============================================================================

# Enable filter based on how long price has been in oversold zone
# Filters out quick bounces (too few candles) and strong downtrends (too many)
USE_OVERSOLD_DURATION_FILTER = True

# Minimum candles price must be in oversold zone (Z-Score < threshold) before entry
# Too few = likely noise/quick bounce, not real reversal
# Analysis: Avoid hours [3,6,7,10,13,20] + candles >= 6 -> 515 trades, PF 1.59
OVERSOLD_MIN_CANDLES = 6  # Restored to 6, hours filter handles quality

# Maximum candles price can be in oversold zone before entry
# Too many = likely strong downtrend, may not revert
OVERSOLD_MAX_CANDLES = 11

# Z-Score threshold to consider price in oversold zone for duration counting
# Usually same as MR_ENTRY_ZSCORE_MAX or MEAN_REVERSION_ZSCORE_LOWER
OVERSOLD_ZSCORE_THRESHOLD = -1.0


# =============================================================================
# CUSTOM INDICATORS FOR MEAN REVERSION
# =============================================================================

class MeanReversionBands(bt.Indicator):
    """
    Mean Reversion Bands Indicator (Ernest P. Chan)
    
    Plots:
    - Central EMA (mean)
    - Upper band: EMA + (multiplier x ATR)
    - Lower band: EMA - (multiplier x ATR)
    """
    lines = ('mean', 'upper', 'lower',)
    
    params = (
        ('ema_period', 70),
        ('atr_period', 14),
        ('deviation_mult', 2.0),
    )
    
    plotinfo = dict(
        plot=True,
        subplot=False,  # Plot on main price chart
    )
    
    plotlines = dict(
        mean=dict(color='blue', linewidth=1.0),
        upper=dict(color='red', linestyle='--', linewidth=0.8),
        lower=dict(color='green', linestyle='--', linewidth=0.8),
    )
    
    def __init__(self):
        self.ema = bt.ind.EMA(self.data.close, period=self.p.ema_period)
        self.atr = bt.ind.ATR(self.data, period=self.p.atr_period)
        
        self.lines.mean = self.ema
        self.lines.upper = self.ema + (self.atr * self.p.deviation_mult)
        self.lines.lower = self.ema - (self.atr * self.p.deviation_mult)


class ZScoreIndicator(bt.Indicator):
    """
    Z-Score Oscillator: (Price - EMA) / ATR
    
    Shows how many ATRs the price has deviated from the mean.
    """
    lines = ('zscore',)
    
    params = (
        ('ema_period', 70),
        ('atr_period', 14),
        ('upper_threshold', 2.0),
        ('lower_threshold', -2.0),
    )
    
    plotinfo = dict(
        plot=True,
        subplot=True,  # Separate subplot
        plotname='Z-Score',
    )
    
    plotlines = dict(
        zscore=dict(color='purple', linewidth=1.0),
    )
    
    def __init__(self):
        self.ema = bt.ind.EMA(self.data.close, period=self.p.ema_period)
        self.atr = bt.ind.ATR(self.data, period=self.p.atr_period)
        
        self.lines.zscore = (self.data.close - self.ema) / self.atr
        
        # Add horizontal lines for thresholds
        self.plotinfo.plotyhlines = [
            self.p.upper_threshold,
            0,
            self.p.lower_threshold
        ]


class Eris(bt.Strategy):
    """
    ERIS Strategy - Simplified Pullback Breakout System
    
    State Machine:
    - SCANNING: Looking for bullish candle (candle 1)
    - PULLBACK: Counting bearish candles
    - WAITING: Delay period after pullback (if enabled)
    - BREAKOUT: Monitoring for price to break above candle 1 high
    """
    
    params = dict(
        # Pattern parameters
        long_pullback_num_candles=LONG_PULLBACK_NUM_CANDLES,
        long_breakout_delay=LONG_BREAKOUT_DELAY,
        long_breakout_delay_candles=LONG_BREAKOUT_DELAY_CANDLES,
        long_entry_max_candles=LONG_ENTRY_MAX_CANDLES,
        long_before_candles=LONG_BEFORE_CANDLES,
        long_before_num_candles=LONG_BEFORE_NUM_CANDLES,
        
        # Time filter
        use_time_filter=USE_TIME_RANGE_FILTER,
        trading_start_hour=TRADING_START_HOUR,
        trading_end_hour=TRADING_END_HOUR,
        
        # ATR filter
        use_atr_filter=USE_ATR_FILTER,
        atr_min_threshold=ATR_MIN_THRESHOLD,
        atr_max_threshold=ATR_MAX_THRESHOLD,
        
        # Hours to avoid filter
        use_hours_to_avoid_filter=USE_HOURS_TO_AVOID_FILTER,
        hours_to_avoid=HOURS_TO_AVOID,
        
        # ATR settings
        atr_length=ATR_LENGTH,
        long_atr_sl_multiplier=LONG_ATR_SL_MULTIPLIER,
        long_atr_tp_multiplier=LONG_ATR_TP_MULTIPLIER,
        
        # Position sizing
        risk_percent=RISK_PERCENT,
        contract_size=100000,
        
        # Forex settings
        forex_instrument=FOREX_INSTRUMENT,
        forex_pip_value=0.0001,
        forex_lot_size=100000,
        
        # Display settings
        print_signals=True,
        
        # Mean Reversion Indicator parameters
        use_mean_reversion_indicator=USE_MEAN_REVERSION_INDICATOR,
        mean_reversion_ema_period=MEAN_REVERSION_EMA_PERIOD,
        mean_reversion_atr_period=MEAN_REVERSION_ATR_PERIOD,
        mean_reversion_deviation_mult=MEAN_REVERSION_DEVIATION_MULT,
        mean_reversion_zscore_upper=MEAN_REVERSION_ZSCORE_UPPER,
        mean_reversion_zscore_lower=MEAN_REVERSION_ZSCORE_LOWER,
        
        # Mean Reversion Entry Filter parameters
        use_mean_reversion_entry_filter=USE_MEAN_REVERSION_ENTRY_FILTER,
        mr_entry_zscore_min=MR_ENTRY_ZSCORE_MIN,
        mr_entry_zscore_max=MR_ENTRY_ZSCORE_MAX,
        
        # Oversold Duration Filter parameters
        use_oversold_duration_filter=USE_OVERSOLD_DURATION_FILTER,
        oversold_min_candles=OVERSOLD_MIN_CANDLES,
        oversold_max_candles=OVERSOLD_MAX_CANDLES,
        oversold_zscore_threshold=OVERSOLD_ZSCORE_THRESHOLD,
    )

    def __init__(self):
        """Initialize strategy indicators and state variables."""
        # ATR indicator for SL/TP calculation
        self.atr = bt.ind.ATR(self.data, period=self.p.atr_length)
        
        # =================================================================
        # MEAN REVERSION INDICATOR (Ernest P. Chan)
        # =================================================================
        if self.p.use_mean_reversion_indicator:
            # Mean Reversion Bands (EMA + Upper/Lower bands)
            self.mr_bands = MeanReversionBands(
                self.data,
                ema_period=self.p.mean_reversion_ema_period,
                atr_period=self.p.mean_reversion_atr_period,
                deviation_mult=self.p.mean_reversion_deviation_mult,
            )
            
            # Z-Score Oscillator (separate subplot)
            self.mr_zscore = ZScoreIndicator(
                self.data,
                ema_period=self.p.mean_reversion_ema_period,
                atr_period=self.p.mean_reversion_atr_period,
                upper_threshold=self.p.mean_reversion_zscore_upper,
                lower_threshold=self.p.mean_reversion_zscore_lower,
            )
        
        # Order management
        self.order = None
        self.stop_order = None
        self.limit_order = None
        
        # Price levels
        self.stop_level = None
        self.take_level = None
        
        # State machine variables
        self.state = "SCANNING"
        self.trigger_candle_high = None  # High of candle 1
        self.trigger_candle_bar = None   # Bar number of candle 1
        
        # Oversold duration tracking
        self.candles_in_oversold = 0  # Counter for consecutive candles in oversold zone
        self.pullback_count = 0          # Count of bearish candles
        self.pullback_complete_bar = None  # Bar when pullback completed
        self.delay_count = 0             # Count of delay candles
        self.breakout_start_bar = None   # Bar when breakout monitoring started
        
        # Trade tracking
        self.last_entry_bar = None
        self.last_entry_price = None
        self.last_exit_reason = "UNKNOWN"
        self.trades = 0
        self.wins = 0
        self.losses = 0
        self.gross_profit = 0.0
        self.gross_loss = 0.0
        
        # Trade reporting
        self.trade_reports = []
        self.trade_report_file = None
        self._init_trade_reporting()
        
        # Store data filename
        self._data_filename = getattr(self.data._dataname, 'name',
                                      getattr(self.data, '_dataname', ''))
        if isinstance(self._data_filename, str):
            self._data_filename = Path(self._data_filename).name

    def _init_trade_reporting(self):
        """Initialize trade reporting file."""
        if not EXPORT_TRADE_REPORTS:
            return
            
        try:
            report_dir = Path(__file__).parent / "temp_reports"
            report_dir.mkdir(exist_ok=True)
            
            asset_name = FOREX_INSTRUMENT
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"ERIS_{asset_name}_{timestamp}.txt"
            report_path = report_dir / report_filename
            
            self.trade_report_file = open(report_path, 'w', encoding='utf-8')
            
            # Write header
            self.trade_report_file.write("=== ERIS STRATEGY TRADE REPORT ===\n")
            self.trade_report_file.write(f"Asset: {asset_name}\n")
            self.trade_report_file.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Configuration
            self.trade_report_file.write("CONFIGURATION:\n")
            self.trade_report_file.write("-" * 40 + "\n")
            self.trade_report_file.write(f"Pullback Candles: {self.p.long_pullback_num_candles}\n")
            self.trade_report_file.write(f"Breakout Delay: {self.p.long_breakout_delay} ({self.p.long_breakout_delay_candles} candles)\n")
            self.trade_report_file.write(f"Max Entry Candles: {self.p.long_entry_max_candles}\n")
            self.trade_report_file.write(f"Before Candles Filter: {self.p.long_before_candles} ({self.p.long_before_num_candles})\n")
            self.trade_report_file.write(f"Time Filter: {self.p.use_time_filter} ({self.p.trading_start_hour}:00-{self.p.trading_end_hour}:00)\n")
            self.trade_report_file.write(f"ATR Filter: {self.p.use_atr_filter} (min={self.p.atr_min_threshold}, max={self.p.atr_max_threshold})\n")
            self.trade_report_file.write(f"Hours to Avoid Filter: {self.p.use_hours_to_avoid_filter} (Hours: {list(self.p.hours_to_avoid)})\n")
            self.trade_report_file.write(f"ATR Length: {self.p.atr_length}\n")
            self.trade_report_file.write(f"SL Multiplier: {self.p.long_atr_sl_multiplier}\n")
            self.trade_report_file.write(f"TP Multiplier: {self.p.long_atr_tp_multiplier}\n")
            self.trade_report_file.write(f"Risk Percent: {self.p.risk_percent * 100:.1f}%\n")
            self.trade_report_file.write(f"Mean Reversion Entry Filter: {self.p.use_mean_reversion_entry_filter} (Z-Score: [{self.p.mr_entry_zscore_min}, {self.p.mr_entry_zscore_max}])\n")
            self.trade_report_file.write(f"Oversold Duration Filter: {self.p.use_oversold_duration_filter} (Candles: [{self.p.oversold_min_candles}, {self.p.oversold_max_candles}], Threshold: {self.p.oversold_zscore_threshold})\n")
            self.trade_report_file.write("\n" + "=" * 60 + "\n")
            self.trade_report_file.write("TRADE DETAILS\n")
            self.trade_report_file.write("=" * 60 + "\n\n")
            self.trade_report_file.flush()
            
            print(f"Trade report: {report_path}")
            
        except Exception as e:
            print(f"Trade reporting init error: {e}")
            self.trade_report_file = None

    def _is_bullish_candle(self, offset=0):
        """Check if candle at offset is bullish (close > open)."""
        try:
            return self.data.close[offset] > self.data.open[offset]
        except IndexError:
            return False

    def _is_bearish_candle(self, offset=0):
        """Check if candle at offset is bearish (close < open)."""
        try:
            return self.data.close[offset] < self.data.open[offset]
        except IndexError:
            return False

    def _check_before_candles(self):
        """Check if required number of green candles exist before trigger."""
        if not self.p.long_before_candles:
            return True
            
        required = self.p.long_before_num_candles
        for i in range(1, required + 1):
            offset = -i - 1  # Go back from the candle before current
            if not self._is_bullish_candle(offset):
                return False
        return True

    def _reset_state(self):
        """Reset state machine to scanning mode."""
        self.state = "SCANNING"
        self.trigger_candle_high = None
        self.trigger_candle_bar = None
        self.pullback_count = 0
        self.pullback_complete_bar = None
        self.delay_count = 0
        self.breakout_start_bar = None

    def next(self):
        """Main strategy logic - executed on each bar close."""
        current_bar = len(self)
        dt = self.data.datetime.datetime(0)
        
        # Cancel phantom orders when no position
        if not self.position:
            if self.order:
                self.cancel(self.order)
                self.order = None
            if self.stop_order:
                self.cancel(self.stop_order)
                self.stop_order = None
            if self.limit_order:
                self.cancel(self.limit_order)
                self.limit_order = None
        
        # Skip if waiting for order execution
        if self.order:
            return
        
        # Skip entry logic if in position
        if self.position:
            return
        
        # =================================================================
        # FILTER CHECKS (OPTIMIZED)
        # =================================================================
        
        # Update oversold duration counter (must be called every bar)
        self._update_oversold_duration()
        
        # TIME FILTER: Only trade during specified hours
        if self.p.use_time_filter:
            current_hour = dt.hour
            if current_hour < self.p.trading_start_hour or current_hour >= self.p.trading_end_hour:
                # Reset state if outside trading hours
                if self.state != "SCANNING":
                    self._reset_state()
                return
        
        # ATR FILTER: Check volatility is within range
        if self.p.use_atr_filter:
            current_atr = float(self.atr[0])
            if math.isnan(current_atr):
                return
            if current_atr < self.p.atr_min_threshold or current_atr > self.p.atr_max_threshold:
                # Reset state if ATR out of range
                if self.state != "SCANNING":
                    self._reset_state()
                return
        
        # HOURS TO AVOID FILTER: Skip specific hours with poor performance
        if self.p.use_hours_to_avoid_filter:
            current_hour = dt.hour
            if current_hour in self.p.hours_to_avoid:
                # Reset state if in bad hour
                if self.state != "SCANNING":
                    self._reset_state()
                return
        
        # =================================================================
        # STATE MACHINE
        # =================================================================
        
        if self.state == "SCANNING":
            # Look for bullish candle (candle 1)
            # Check previous candle (index -1) as potential trigger
            if self._is_bullish_candle(-1):
                # Check before candles requirement if enabled
                if self._check_before_candles():
                    # Found potential trigger candle
                    self.trigger_candle_high = float(self.data.high[-1])
                    self.trigger_candle_bar = current_bar - 1
                    self.pullback_count = 0
                    self.state = "PULLBACK"
                    
                    if self.p.print_signals:
                        print(f"ERIS SIGNAL: Bullish candle detected at {dt}")
                        print(f"   Trigger High: {self.trigger_candle_high:.5f}")
        
        elif self.state == "PULLBACK":
            # Count bearish pullback candles (check CURRENT candle)
            # NOTE: Removed restriction that pullback highs must be below trigger level
            # to allow more flexible entries (especially with Mean Reversion filter)
            
            if self._is_bearish_candle(0):
                self.pullback_count += 1
                
                if self.p.print_signals:
                    print(f"ERIS PULLBACK: Bearish candle {self.pullback_count}/{self.p.long_pullback_num_candles}")
                
                # Check if pullback complete
                if self.pullback_count >= self.p.long_pullback_num_candles:
                    self.pullback_complete_bar = current_bar
                    
                    if self.p.long_breakout_delay:
                        self.state = "WAITING"
                        self.delay_count = 0
                        if self.p.print_signals:
                            print(f"ERIS: Pullback complete, entering delay period")
                        return  # Wait for next bar
                    else:
                        self.state = "BREAKOUT"
                        self.breakout_start_bar = current_bar
                        if self.p.print_signals:
                            print(f"ERIS: Pullback complete, monitoring for breakout")
                        return  # Wait for next bar to check breakout
            else:
                # Current candle is NOT bearish
                # Check if we already have enough pullback candles - if so, transition to BREAKOUT
                if self.pullback_count >= self.p.long_pullback_num_candles:
                    # Pullback was complete, now this non-bearish candle can be checked for breakout
                    if self.pullback_complete_bar is None:
                        self.pullback_complete_bar = current_bar - 1
                    self.state = "BREAKOUT"
                    self.breakout_start_bar = current_bar
                    # Fall through to BREAKOUT check below
                else:
                    # Not enough pullback candles and got a non-bearish candle - invalidate
                    if self.p.print_signals:
                        print(f"ERIS INVALIDATED: Non-bearish candle during pullback (count={self.pullback_count})")
                    self._reset_state()
                    return
        
        elif self.state == "WAITING":
            # Count delay candles
            self.delay_count += 1
            
            if self.delay_count >= self.p.long_breakout_delay_candles:
                self.state = "BREAKOUT"
                self.breakout_start_bar = current_bar
                if self.p.print_signals:
                    print(f"ERIS: Delay complete, monitoring for breakout")
                return  # IMPORTANT: Wait for next bar before checking breakout
        
        # Check BREAKOUT state (can be reached from PULLBACK transition in same bar)
        if self.state == "BREAKOUT":
            # Check for expiry
            candles_since_pullback = current_bar - self.pullback_complete_bar
            if candles_since_pullback > self.p.long_entry_max_candles:
                if self.p.print_signals:
                    print(f"ERIS EXPIRED: No breakout within {self.p.long_entry_max_candles} candles")
                self._reset_state()
                return
            
            # Check for breakout above trigger candle high
            current_high = float(self.data.high[0])
            
            if self.p.print_signals:
                print(f"ERIS BREAKOUT CHECK: Current High={current_high:.5f} vs Trigger={self.trigger_candle_high:.5f}")
            
            if current_high > self.trigger_candle_high:  # Changed >= to > (must BREAK above, not just touch)
                # BREAKOUT DETECTED - CHECK ALL ENTRY FILTERS
                mr_filter_ok = self._check_mean_reversion_entry_filter()
                duration_filter_ok = self._check_oversold_duration_filter()
                
                if mr_filter_ok and duration_filter_ok:
                    self._execute_entry(dt, current_bar)
                else:
                    if self.p.print_signals:
                        print(f"ERIS FILTERED: Entry rejected by filters")
                    self._reset_state()
        
    def _update_oversold_duration(self):
        """Update the counter for consecutive candles in oversold zone.
        
        Called on each bar to track how long price has been in oversold territory.
        Resets to 0 when price exits oversold zone.
        """
        if not self.p.use_oversold_duration_filter:
            return
        
        if not self.p.use_mean_reversion_indicator:
            return
        
        try:
            current_zscore = float(self.mr_zscore.zscore[0])
            if math.isnan(current_zscore):
                return
        except (AttributeError, IndexError):
            return
        
        # Check if currently in oversold zone
        if current_zscore < self.p.oversold_zscore_threshold:
            self.candles_in_oversold += 1
        else:
            # Exited oversold zone, reset counter
            self.candles_in_oversold = 0
    
    def _check_oversold_duration_filter(self):
        """Check if oversold duration is within valid range for entry.
        
        Returns True if:
        - Filter is disabled
        - Duration is between min and max candles
        
        Rationale:
        - Too few candles (< min): Quick bounce, likely noise
        - Too many candles (> max): Strong downtrend, may not revert
        """
        if not self.p.use_oversold_duration_filter:
            return True  # Filter disabled
        
        duration = self.candles_in_oversold
        is_valid = self.p.oversold_min_candles <= duration <= self.p.oversold_max_candles
        
        if self.p.print_signals:
            status = "VALID" if is_valid else "REJECTED"
            print(f"ERIS OVERSOLD DURATION: {duration} candles Range=[{self.p.oversold_min_candles}, {self.p.oversold_max_candles}] -> {status}")
        
        return is_valid
    
    def _check_mean_reversion_entry_filter(self):
        """Check if current price is in valid Mean Reversion zone for entry.
        
        Returns True if:
        - Filter is disabled (use_mean_reversion_entry_filter = False)
        - Filter is enabled AND Z-Score is within the valid range
        """
        if not self.p.use_mean_reversion_entry_filter:
            return True  # Filter disabled, allow all entries
        
        # Check if Mean Reversion indicator is available
        if not self.p.use_mean_reversion_indicator:
            if self.p.print_signals:
                print(f"WARNING: Mean Reversion entry filter enabled but indicator disabled")
            return True  # Can't filter without indicator
        
        # Get current Z-Score
        try:
            current_zscore = float(self.mr_zscore.zscore[0])
            if math.isnan(current_zscore):
                return True  # Allow entry if Z-Score not available yet
        except (AttributeError, IndexError):
            return True  # Allow entry if indicator not ready
        
        # Check if Z-Score is within valid range for entry
        is_valid = self.p.mr_entry_zscore_min <= current_zscore <= self.p.mr_entry_zscore_max
        
        if self.p.print_signals:
            status = "VALID" if is_valid else "REJECTED"
            print(f"ERIS MR FILTER: Z-Score={current_zscore:.2f} Range=[{self.p.mr_entry_zscore_min}, {self.p.mr_entry_zscore_max}] -> {status}")
        
        return is_valid
        
    def _execute_entry(self, dt, current_bar):
        """Execute long entry order."""
        # Get ATR for SL/TP calculation
        atr_value = float(self.atr[0])
        if math.isnan(atr_value) or atr_value <= 0:
            if self.p.print_signals:
                print(f"ERIS BLOCKED: Invalid ATR value")
            self._reset_state()
            return
        
        entry_price = float(self.data.close[0])
        
        # Calculate SL/TP from entry price
        self.stop_level = entry_price - (atr_value * self.p.long_atr_sl_multiplier)
        self.take_level = entry_price + (atr_value * self.p.long_atr_tp_multiplier)
        
        # Position sizing
        risk_distance = entry_price - self.stop_level
        if risk_distance <= 0:
            self._reset_state()
            return
            
        equity = self.broker.get_value()
        risk_amount = equity * self.p.risk_percent
        risk_per_contract = risk_distance * self.p.contract_size
        
        if risk_per_contract <= 0:
            self._reset_state()
            return
            
        contracts = max(int(risk_amount / risk_per_contract), 1)
        
        # For Forex: Use simple lot sizing (max 5 lots)
        max_lots = 5
        contracts = min(contracts, max_lots)
        bt_size = contracts * self.p.contract_size
        
        # Safety check: ensure we have enough margin (leverage=30)
        # Margin required = position_value / leverage
        position_value = bt_size * entry_price
        margin_required = position_value / 30.0
        available_cash = self.broker.get_cash()
        
        if margin_required > available_cash * 0.8:  # Use max 80% of available cash
            # Reduce size to fit margin
            max_position = available_cash * 0.8 * 30.0  # Max position with 80% margin usage
            bt_size = int(max_position / entry_price / self.p.contract_size) * self.p.contract_size
            if bt_size < self.p.contract_size:
                bt_size = self.p.contract_size
        
        if self.p.print_signals:
            print(f"   Position: {bt_size/self.p.contract_size:.1f} lots | Value: {bt_size * entry_price:,.0f} | Margin: {margin_required:,.0f}")
        
        # Place buy order
        self.order = self.buy(size=bt_size)
        
        # Calculate R:R
        rr = (self.take_level - entry_price) / risk_distance if risk_distance > 0 else 0
        
        if self.p.print_signals:
            print(f"ERIS ENTRY: LONG BUY at {dt}")
            print(f"   Price: {entry_price:.5f} | SL: {self.stop_level:.5f} | TP: {self.take_level:.5f}")
            print(f"   ATR: {atr_value:.6f} | R:R = 1:{rr:.2f}")
        
        # Record entry
        self._record_entry(dt, entry_price, bt_size, atr_value)
        
        self.last_entry_price = entry_price
        self.last_entry_bar = current_bar
        
        # DO NOT reset state here - will be reset in notify_order when order completes
        # self._reset_state()  # REMOVED - was causing multiple orders

    def _record_entry(self, dt, entry_price, size, atr_value):
        """Record trade entry for reporting with all indicator values."""
        if not self.trade_report_file:
            return
        
        # Gather all indicator values for analysis
        zscore_value = None
        ema_value = None
        upper_band = None
        lower_band = None
        
        if self.p.use_mean_reversion_indicator:
            try:
                zscore_value = float(self.mr_zscore.zscore[0])
                ema_value = float(self.mr_bands.mean[0])
                upper_band = float(self.mr_bands.upper[0])
                lower_band = float(self.mr_bands.lower[0])
            except (AttributeError, IndexError):
                pass
        
        # Calculate distance from bands (for analysis)
        dist_to_ema = entry_price - ema_value if ema_value else None
        dist_to_lower = entry_price - lower_band if lower_band else None
        dist_to_upper = upper_band - entry_price if upper_band else None
            
        try:
            self.trade_reports.append({
                'entry_time': dt,
                'entry_price': entry_price,
                'size': size,
                'atr': atr_value,
                'stop_level': self.stop_level,
                'take_level': self.take_level,
                'zscore': zscore_value,
                'candles_in_oversold': self.candles_in_oversold,
                'ema': ema_value,
                'upper_band': upper_band,
                'lower_band': lower_band
            })
            
            self.trade_report_file.write(f"ENTRY #{len(self.trade_reports)}\n")
            self.trade_report_file.write(f"Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.trade_report_file.write(f"Direction: LONG\n")
            self.trade_report_file.write(f"Entry Price: {entry_price:.5f}\n")
            self.trade_report_file.write(f"Stop Loss: {self.stop_level:.5f}\n")
            self.trade_report_file.write(f"Take Profit: {self.take_level:.5f}\n")
            self.trade_report_file.write(f"ATR: {atr_value:.6f}\n")
            
            # Mean Reversion indicator values
            if zscore_value is not None:
                self.trade_report_file.write(f"Z-Score: {zscore_value:.3f}\n")
            if self.p.use_oversold_duration_filter:
                self.trade_report_file.write(f"Candles in Oversold: {self.candles_in_oversold}\n")
            if ema_value is not None:
                self.trade_report_file.write(f"EMA({self.p.mean_reversion_ema_period}): {ema_value:.5f}\n")
            if upper_band is not None:
                self.trade_report_file.write(f"Upper Band: {upper_band:.5f}\n")
            if lower_band is not None:
                self.trade_report_file.write(f"Lower Band: {lower_band:.5f}\n")
            if dist_to_ema is not None:
                self.trade_report_file.write(f"Distance to EMA: {dist_to_ema:.5f}\n")
            if dist_to_lower is not None:
                self.trade_report_file.write(f"Distance to Lower: {dist_to_lower:.5f}\n")
            
            self.trade_report_file.write("-" * 40 + "\n\n")
            self.trade_report_file.flush()
            
        except Exception as e:
            print(f"Entry recording error: {e}")

    def _record_exit(self, dt, exit_price, pnl, exit_reason):
        """Record trade exit for reporting."""
        if not self.trade_report_file or not self.trade_reports:
            return
            
        try:
            last_trade = self.trade_reports[-1]
            entry_price = last_trade.get('entry_price', 0)
            pips = (exit_price - entry_price) / self.p.forex_pip_value if entry_price > 0 else 0
            result = "WIN" if pnl > 0 else "LOSS"
            
            # Add result to trade record for analysis
            last_trade['exit_price'] = exit_price
            last_trade['pnl'] = pnl
            last_trade['result'] = result
            last_trade['exit_reason'] = exit_reason
            
            self.trade_report_file.write(f"EXIT #{len(self.trade_reports)}\n")
            self.trade_report_file.write(f"Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.trade_report_file.write(f"Exit Price: {exit_price:.5f}\n")
            self.trade_report_file.write(f"Exit Reason: {exit_reason}\n")
            self.trade_report_file.write(f"Result: {result}\n")
            self.trade_report_file.write(f"P&L: {pnl:.2f}\n")
            self.trade_report_file.write(f"Pips: {pips:.1f}\n")
            
            # Include entry indicator values for correlation analysis
            if 'zscore' in last_trade and last_trade['zscore'] is not None:
                self.trade_report_file.write(f"Entry Z-Score: {last_trade['zscore']:.3f}\n")
            if 'candles_in_oversold' in last_trade:
                self.trade_report_file.write(f"Entry Candles in Oversold: {last_trade['candles_in_oversold']}\n")
            if 'atr' in last_trade:
                self.trade_report_file.write(f"Entry ATR: {last_trade['atr']:.6f}\n")
            
            self.trade_report_file.write("=" * 60 + "\n\n")
            self.trade_report_file.flush()
            
        except Exception as e:
            print(f"Exit recording error: {e}")

    def notify_order(self, order):
        """Handle order notifications with OCA orders (same as Ogle)."""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status == order.Completed:
            if order == self.order:
                # Entry order completed
                self.last_entry_price = order.executed.price
                self.last_entry_bar = len(self)
                
                if self.p.print_signals:
                    print(f"ERIS: LONG BUY EXECUTED at {order.executed.price:.5f} size={order.executed.size}")
                
                # Place protective OCA orders (linked together)
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
                        print(f"ERIS: OCA ORDERS PLACED - SL={self.stop_level:.5f} TP={self.take_level:.5f}")
                
                self.order = None
                # Reset state AFTER order completes successfully
                self._reset_state()
                
            else:
                # Exit order completed (SL or TP)
                exit_price = order.executed.price
                
                # Determine exit reason
                if order.exectype == bt.Order.Stop:
                    exit_reason = "STOP_LOSS"
                elif order.exectype == bt.Order.Limit:
                    exit_reason = "TAKE_PROFIT"
                else:
                    exit_reason = "MANUAL_CLOSE"
                
                self.last_exit_reason = exit_reason
                
                if self.p.print_signals:
                    print(f"ERIS: EXIT at {exit_price:.5f} reason={exit_reason}")
                
                # Clean up - OCA should auto-cancel the other order
                self.stop_order = None
                self.limit_order = None
                self.order = None
                self.stop_level = None
                self.take_level = None
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # With OCA, one order is canceled when the other executes - this is expected
            is_expected_cancel = (self.stop_order and self.limit_order)
            if not is_expected_cancel and self.p.print_signals:
                print(f"Order {order.getstatusname()}: {order.ref}")
            
            # Clean up references
            if self.order and order.ref == self.order.ref:
                self.order = None
                self._reset_state()
            if self.stop_order and order.ref == self.stop_order.ref:
                self.stop_order = None
            if self.limit_order and order.ref == self.limit_order.ref:
                self.limit_order = None
            if order == self.stop_order:
                self.stop_order = None
            if order == self.limit_order:
                self.limit_order = None

    def notify_trade(self, trade):
        """Handle trade notifications (same as Ogle)."""
        if not trade.isclosed:
            return
        
        dt = self.data.datetime.datetime(0)
        pnl = trade.pnlcomm
        
        # Get entry and exit prices
        entry_price = self.last_entry_price if self.last_entry_price else 0
        
        # Calculate exit price correctly
        if entry_price > 0 and abs(trade.size) > 0:
            # PnL = (exit - entry) * size for LONG
            exit_price = entry_price + (pnl / abs(trade.size))
        else:
            exit_price = trade.price
        
        # Use stored exit reason from notify_order
        exit_reason = getattr(self, 'last_exit_reason', 'UNKNOWN')
        
        # Fallback: price comparison
        if exit_reason == 'UNKNOWN':
            if self.stop_level and abs(exit_price - self.stop_level) < 0.0002:
                exit_reason = "STOP_LOSS"
            elif self.take_level and abs(exit_price - self.take_level) < 0.0002:
                exit_reason = "TAKE_PROFIT"
        
        # Update statistics
        self.trades += 1
        if pnl > 0:
            self.wins += 1
            self.gross_profit += pnl
        else:
            self.losses += 1
            self.gross_loss += abs(pnl)
        
        if self.p.print_signals:
            pips = (exit_price - entry_price) / self.p.forex_pip_value if entry_price > 0 and self.p.forex_pip_value > 0 else 0
            print(f"ERIS TRADE CLOSED: Entry={entry_price:.5f} Exit={exit_price:.5f} P&L={pnl:.2f} Pips={pips:.1f} ({exit_reason})")
        
        # Record exit
        self._record_exit(dt, exit_price, pnl, exit_reason)
        
        # Reset levels after trade close
        self.stop_level = None
        self.take_level = None

    def stop(self):
        """Strategy end - print summary and close reporting."""
        # Close any open position
        if self.position:
            self.close()
        
        # Print summary
        print("\n" + "=" * 60)
        print("=== ERIS STRATEGY SUMMARY ===")
        print("=" * 60)
        
        win_rate = (self.wins / self.trades * 100) if self.trades > 0 else 0
        profit_factor = (self.gross_profit / self.gross_loss) if self.gross_loss > 0 else float('inf')
        
        final_value = self.broker.get_value()
        total_pnl = final_value - STARTING_CASH
        
        print(f"Total Trades: {self.trades}")
        print(f"Wins: {self.wins} | Losses: {self.losses}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Profit Factor: {profit_factor:.2f}")
        print(f"Gross Profit: {self.gross_profit:.2f}")
        print(f"Gross Loss: {self.gross_loss:.2f}")
        print(f"Net P&L: {total_pnl:.2f}")
        print(f"Final Value: {final_value:,.2f}")
        print("=" * 60)
        
        # Close trade report
        if self.trade_report_file:
            try:
                self.trade_report_file.write("\n" + "=" * 60 + "\n")
                self.trade_report_file.write("SUMMARY\n")
                self.trade_report_file.write("=" * 60 + "\n")
                self.trade_report_file.write(f"Total Trades: {self.trades}\n")
                self.trade_report_file.write(f"Wins: {self.wins} | Losses: {self.losses}\n")
                self.trade_report_file.write(f"Win Rate: {win_rate:.1f}%\n")
                self.trade_report_file.write(f"Profit Factor: {profit_factor:.2f}\n")
                self.trade_report_file.write(f"Net P&L: {total_pnl:.2f}\n")
                self.trade_report_file.write(f"Final Value: {final_value:,.2f}\n")
                self.trade_report_file.close()
            except Exception as e:
                print(f"Report close error: {e}")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == '__main__':
    # Data path
    BASE = Path(__file__).resolve().parent.parent.parent
    DATA_FILE = BASE / 'data' / DATA_FILENAME
    
    if not DATA_FILE.exists():
        print(f"Data file not found: {DATA_FILE}")
        raise SystemExit(1)
    
    # Parse dates
    def parse_date(s):
        try:
            return datetime.strptime(s, '%Y-%m-%d')
        except Exception:
            return None
    
    # Create data feed
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
    if fd:
        feed_kwargs['fromdate'] = fd
    if td:
        feed_kwargs['todate'] = td
    
    data = bt.feeds.GenericCSVData(**feed_kwargs)
    
    # Create cerebro
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.adddata(data)
    cerebro.broker.setcash(STARTING_CASH)
    
    # Forex broker configuration - proper margin/leverage setup
    cerebro.broker.setcommission(
        commission=0.0,       # No commission (spread included in price)
        leverage=100.0,       # 100:1 leverage for Forex
        mult=1.0,             # Multiplier (1 for Forex)
        margin=None,          # Auto-calculate margin from leverage
        automargin=True       # Enable auto margin calculation
    )
    
    cerebro.addstrategy(Eris)
    
    # Add observers
    cerebro.addobserver(bt.observers.BuySell, barplot=False)
    cerebro.addobserver(bt.observers.Value)
    
    print(f"=== ERIS STRATEGY === ({FROMDATE} to {TODATE})")
    print(f"Data: {DATA_FILENAME}")
    print(f"Pullback Candles: {LONG_PULLBACK_NUM_CANDLES}")
    print(f"Breakout Delay: {LONG_BREAKOUT_DELAY} ({LONG_BREAKOUT_DELAY_CANDLES} candles)")
    print(f"Max Entry Candles: {LONG_ENTRY_MAX_CANDLES}")
    print(f"Before Candles: {LONG_BEFORE_CANDLES} ({LONG_BEFORE_NUM_CANDLES})")
    print()
    
    # Run backtest
    results = cerebro.run()
    final_value = cerebro.broker.getvalue()
    
    print(f"\nFinal Portfolio Value: {final_value:,.2f}")
    
    # Plot if enabled
    if ENABLE_PLOT:
        try:
            cerebro.plot(style='candlestick')
        except Exception as e:
            print(f"Plot error: {e}")
