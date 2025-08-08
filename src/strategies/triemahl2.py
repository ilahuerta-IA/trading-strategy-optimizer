# -----------------------------------------------------------------------------
# TRIEMAHL2 TRADING STRATEGY
# -----------------------------------------------------------------------------
# A technical analysis-based trading strategy that uses 3 configurable EMAs based on
# median price (H+L)/2 with EMA crossover pattern detection and angle momentum validation.
# 
# Strategy Concept:
# - 3 Primary EMAs: Fast (5), Medium (7), Slow (9) periods on median price (H+L)/2
# - 2 Exit EMAs: Exit1 (12), Exit2 (15) periods on median price (H+L)/2
# - Entry Signal: Fast EMA crosses up over others + next period confirmation
# - Angle Validation: Historical angle requirements before entry signal
# - Multiple Exit Options: Stop-loss, Take-profit, EMA crossover exit
# 
# DISCLAIMER:
# This software is for educational and research purposes only.
# It is not intended for live trading or financial advice.
# Trading in financial markets involves substantial risk of loss.
# Use at your own risk. The author assumes no liability for any losses.
# -----------------------------------------------------------------------------

# --- LIBRARY IMPORTS ---
import backtrader as bt
import pandas as pd
import numpy as np
from pathlib import Path
import math

# === CONFIGURATION SECTION ===
# All configuration parameters in one place for easy modification

# Data Configuration
DATA_FILE = 'EURUSD_15m_5Yea.csv'  # Select data file to use (5 years of data)
# Alternative files: 'GBPUSD_5m_2Mon.csv', 'EURUSD_5m_2Yea.csv', 'EURUSD_5m_8Yea.csv', 'USDCHF_5m_2Yea.csv', 'USDCHF_5m_8Yea.csv'

# Execution Mode Configuration
OPTIMIZATION_MODE = False  # Set to True to enable parameter optimization

# Strategy Default Parameters (used when OPTIMIZATION_MODE = False)
DEFAULT_PARAMS = {
    # Primary EMAs (Entry Analysis) - Based on Median Price (H+L)/2
    'ema_fast_period': 5,               # Fast EMA period (shortest)
    'ema_medium_period': 7,             # Medium EMA period
    'ema_slow_period': 9,               # Slow EMA period (longest)
    
    # Exit EMAs (Exit Analysis) - Based on Median Price (H+L)/2
    'exit_ema1_period': 5,             # First exit EMA period
    'exit_ema2_period': 14,             # Second exit EMA period
    # Entry threshold EMA (all EMAs must be above this for a valid long entry)
    'entry_ema_period': 14,
    
    # Angle Analysis Parameters
    'min_angle_threshold': 45.0,        # Minimum angle (degrees) for EMA entry validation
    # Max angle divergences (degrees) treated separately for F-M and M-S
    'max_angle_divergence_fm': 4.0,    # Max divergence between Fast and Medium EMA angles
    'max_angle_divergence_ms': 8.0,    # Max divergence between Medium and Slow EMA angles
    'angle_validation_periods': 1,      # Periods to validate angles before entry signal
    
    # Risk Management
    'risk_percent': 0.01,               # Portfolio risk per trade (1%)
    'stop_loss_pips': 10.0,             # Stop-loss distance in pips
    'take_profit_pips': 50.0,           # Take-profit distance in pips (2:1 R/R)
    'pip_value': 0.0001,                # Pip value for EUR/USD (0.0001)
    
    # Exit Options Control
    'enable_stop_loss': True,           # Enable stop-loss exit
    'enable_take_profit': True,         # Enable take-profit exit
    'enable_ema_exit': True,            # Enable EMA crossover exit
    
    # General Parameters
    'enable_long_entries': True,        # Flag to enable long entries
    'cooldown_period': 3,               # Bars to wait after trade closure
}

# Optimization Parameters (used when OPTIMIZATION_MODE = True)
OPTIMIZATION_PARAMS = {
    # Primary EMA periods
    'ema_fast_period': [5],                 # Test: 3, 4, 5, 6, 7
    'ema_medium_period': [7],              # Test: 6, 7, 8, 9
    'ema_slow_period': [9],                # Test: 8, 9, 10, 11, 12

    # Angle analysis
    'min_angle_threshold': [60],        # Test: 30, 35, 40, 45, 50, 55, 60
    # Separate sweeps for angle divergences
    'max_angle_divergence_fm': range(4, 11, 1),     # Test: 5, 10, 15
    'max_angle_divergence_ms': range(4, 11, 1),     # Test: 5, 10, 15
    'angle_validation_periods': [1],          # Test: 1, 2, 3 periods
    
    # Risk management
    'stop_loss_pips': [10],             # Test: 10, 15, 20, 25
    'take_profit_pips': [50],           # Test: 20, 25, 30, 35, 40
    'risk_percent': [0.01],           # Test different risk levels
}

# Broker Configuration
BROKER_CONFIG = {
    'start_cash': 100000.0,         # Initial portfolio value
    'leverage': 30.0,               # Broker leverage
}

# === END CONFIGURATION SECTION ===

# --- PROJECT PATH CONFIGURATION ---
try:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    DATA_PATH = PROJECT_ROOT / 'data' / DATA_FILE
    
    if not DATA_PATH.exists():
        print(f"FATAL: Data file not found at {DATA_PATH}")
        exit()
except Exception:
    print("FATAL: Could not determine project paths. Please run from the project root.")
    exit()

# --- CUSTOM INDICATORS ---

class MedianPriceIndicator(bt.Indicator):
    """
    Custom indicator that calculates median price as (High + Low) / 2.
    This provides a smoother price series compared to closing prices.
    """
    lines = ('median_price',)
    plotinfo = dict(subplot=False, plotname='Median Price (H+L)/2')
    
    def next(self):
        """Calculate median price for current bar."""
        median = (self.data.high[0] + self.data.low[0]) / 2.0
        self.lines.median_price[0] = median
    # No noisy debug prints

class EMAAngleIndicator(bt.Indicator):
    """
    Custom indicator that calculates the angle (in degrees) of EMA movement
    over a specified lookback period. Optimized for EMA angle analysis.
    """
    lines = ('angle',)
    params = (
        ('angle_lookback', 5),     # Periods to look back for angle calculation
        ('scale_factor', 50000),   # Scale factor to amplify small price movements
    )
    plotinfo = dict(subplot=True, plotname='EMA Angle (Degrees)')
    
    def __init__(self):
        self.addminperiod(self.p.angle_lookback)
        super().__init__()

    def next(self):
        """Calculate the angle of EMA movement over the lookback period."""
        try:
            rise = (self.data0[0] - self.data0[-self.p.angle_lookback + 1]) * self.p.scale_factor
            run = self.p.angle_lookback
            angle = np.degrees(np.arctan2(rise, run))
            self.lines.angle[0] = angle
            # No noisy debug prints
        except (IndexError, ValueError) as e:
            # Handle edge cases with insufficient data
            self.lines.angle[0] = 0.0

# --- MAIN TRADING STRATEGY ---

class Triemahl2Strategy(bt.Strategy):
    """
    Triemahl2 trading strategy using 3 configurable EMAs with crossover pattern detection
    and angle momentum validation.
    
    Strategy Logic:
    1. Calculate EMAs on median price (H+L)/2: Fast, Medium, Slow + Exit EMAs
    2. Stage 1: Detect Fast EMA crossing UP over Medium and Slow EMAs
    3. Stage 2: Next period confirmation - Fast EMA remains ABOVE others
    4. Angle Validation: Historical angle requirements for EMA momentum
    5. Multiple Exits: Stop-loss, Take-profit, EMA crossover exit
    
    Key Features:
    - Median price EMAs for smoother signals
    - Two-stage entry confirmation system
    - Angle-based momentum validation
    - Configurable multi-exit strategy
    - Full optimization framework support
    """
    
    params = (
        # Primary EMA parameters (Entry Analysis)
        ('ema_fast_period', DEFAULT_PARAMS['ema_fast_period']),
        ('ema_medium_period', DEFAULT_PARAMS['ema_medium_period']),
        ('ema_slow_period', DEFAULT_PARAMS['ema_slow_period']),
        
    # Exit EMA parameters
    ('exit_ema1_period', DEFAULT_PARAMS['exit_ema1_period']),
    ('exit_ema2_period', DEFAULT_PARAMS['exit_ema2_period']),
    ('entry_ema_period', DEFAULT_PARAMS['entry_ema_period']),
        
        # Angle analysis parameters
    ('min_angle_threshold', DEFAULT_PARAMS['min_angle_threshold']),
    ('max_angle_divergence_fm', DEFAULT_PARAMS['max_angle_divergence_fm']),
    ('max_angle_divergence_ms', DEFAULT_PARAMS['max_angle_divergence_ms']),
        ('angle_validation_periods', DEFAULT_PARAMS['angle_validation_periods']),
        
        # Risk management
        ('risk_percent', DEFAULT_PARAMS['risk_percent']),
        ('stop_loss_pips', DEFAULT_PARAMS['stop_loss_pips']),
        ('take_profit_pips', DEFAULT_PARAMS['take_profit_pips']),
        ('pip_value', DEFAULT_PARAMS['pip_value']),
        
        # Exit options control
        ('enable_stop_loss', DEFAULT_PARAMS['enable_stop_loss']),
        ('enable_take_profit', DEFAULT_PARAMS['enable_take_profit']),
        ('enable_ema_exit', DEFAULT_PARAMS['enable_ema_exit']),
        
        # General parameters
        ('enable_long_entries', DEFAULT_PARAMS['enable_long_entries']),
        ('cooldown_period', DEFAULT_PARAMS['cooldown_period']),
    ('verbose', True),               # Enable/disable detailed output (True by default for standard runs)
    )

    def __init__(self):
        """Initialize strategy indicators and state management variables."""
        # --- Median Price Calculation ---
        self.median_price = MedianPriceIndicator(self.data)

        # --- Primary EMAs (Entry Analysis) based on Median Price ---
        self.ema_fast = bt.indicators.EMA(self.median_price.median_price, period=self.p.ema_fast_period)
        self.ema_medium = bt.indicators.EMA(self.median_price.median_price, period=self.p.ema_medium_period)
        self.ema_slow = bt.indicators.EMA(self.median_price.median_price, period=self.p.ema_slow_period)
        self.ema_fast.plotinfo.plotname = f"EMA Fast ({self.p.ema_fast_period})"
        self.ema_medium.plotinfo.plotname = f"EMA Medium ({self.p.ema_medium_period})"
        self.ema_slow.plotinfo.plotname = f"EMA Slow ({self.p.ema_slow_period})"

        # --- Exit EMAs based on Median Price ---
        self.exit_ema1 = bt.indicators.EMA(self.median_price.median_price, period=self.p.exit_ema1_period)
        self.exit_ema2 = bt.indicators.EMA(self.median_price.median_price, period=self.p.exit_ema2_period)

        # --- Entry Threshold EMA ---
        self.entry_ema = bt.indicators.EMA(self.median_price.median_price, period=self.p.entry_ema_period)
        self.entry_ema.plotinfo.plotname = f"Entry EMA ({self.p.entry_ema_period})"

        # --- EMA Angle Indicators ---
        self.angle_fast = EMAAngleIndicator(self.ema_fast, angle_lookback=self.p.ema_fast_period)
        self.angle_medium = EMAAngleIndicator(self.ema_medium, angle_lookback=self.p.ema_medium_period)
        self.angle_slow = EMAAngleIndicator(self.ema_slow, angle_lookback=self.p.ema_slow_period)

        # --- Exit Signal Crossover ---
        self.exit_crossover = bt.indicators.CrossOver(self.exit_ema1, self.exit_ema2)
        self.exit_crossover.plotinfo.plot = True

        # Plot visible angle lines on separate subplot
        self.angle_fast.plotinfo.plotname = f"Angle Fast ({self.p.ema_fast_period})"
        self.angle_medium.plotinfo.plotname = f"Angle Medium ({self.p.ema_medium_period})"
        self.angle_slow.plotinfo.plotname = f"Angle Slow ({self.p.ema_slow_period})"

        # Additional visual crossovers for entries
        self.entry_cross_fast_med = bt.indicators.CrossOver(self.ema_fast, self.ema_medium)
        self.entry_cross_fast_slow = bt.indicators.CrossOver(self.ema_fast, self.ema_slow)
        self.entry_cross_fast_med.plotinfo.plot = True
        self.entry_cross_fast_slow.plotinfo.plot = True
        
        # --- State Management Variables ---
        self.crossover_detected = False     # Flag for Stage 1 crossover detection
        self.cooldown_counter = 0           # Prevents immediate re-entry after trade closure
        self.stop_order = None              # Reference to current stop-loss order
        self.profit_order = None            # Reference to current take-profit order
        self.order_pending = False          # Flag to prevent overlapping entry orders
        self.buy_price = None               # Entry price for stop/profit calculation
        self.sell_price = None              # Exit price for PnL calculation
        
        # --- Performance Tracking ---
        self.num_closed_trades = 0
        self.num_won_trades = 0
        self.num_lost_trades = 0
        self.total_gross_profit = 0.0
        self.total_gross_loss = 0.0
        self.entry_angles = None            # Store entry angles for reporting
        self.entry_divergences = None       # Store angle divergences for reporting
        self.exit_method = None             # Track which exit method was used
        
        # --- Optimization Mode Detection ---
        self.verbose = self.p.verbose

    def start(self):
        """Called when the strategy starts."""
        if self.verbose:
            print(f"=== TRIEMAHL2 STRATEGY STARTED ===")

    def calculate_order_size(self, stop_price):
        """
        Calculate position size based on risk percentage of current portfolio (triangle.py style).
        
        Args:
            stop_price: The stop-loss price level
            
        Returns:
            Position size (number of units to trade)
        """
        # Risk 1% (configurable) of current portfolio value
        risked_value = self.broker.get_value() * self.p.risk_percent
        entry_price = self.data.close[0]
        pnl_per_unit = abs(entry_price - stop_price)
        
        if pnl_per_unit == 0:
            return 0
            
        position_size = risked_value / pnl_per_unit
        calculated_size = math.floor(position_size)
        
        # Debug: Print position calculation details
        if self.verbose:
            print(f"POSITION CALC DEBUG: Risk={self.p.risk_percent*100:.2f}% (${risked_value:,.2f}), Entry={entry_price:.5f}, Stop={stop_price:.5f}")
            print(f"  PnL per unit={pnl_per_unit:.5f}, Raw size={position_size:.2f}, Final size={calculated_size}")
            
        return calculated_size

    def detect_stage1_crossover(self):
        """
        Stage 1: Detect if Fast EMA crossed UP over Medium and Slow EMAs.
        
        Returns:
            bool: True if crossover detected, False otherwise
        """
        # Current bar: Fast EMA is above both Medium and Slow
        current_fast_above = (self.ema_fast[0] > self.ema_medium[0] and 
                             self.ema_fast[0] > self.ema_slow[0])
        
        # Previous bar: Fast EMA was NOT above both (at least one was higher)
        try:
            previous_fast_above = (self.ema_fast[-1] > self.ema_medium[-1] and 
                                  self.ema_fast[-1] > self.ema_slow[-1])
        except IndexError:
            return False  # Not enough historical data
            
        # Crossover detected when current is above but previous was not
        return current_fast_above and not previous_fast_above

    def validate_stage2_confirmation(self):
        """
        Stage 2: Confirm Fast EMA remains ABOVE Medium and Slow EMAs.
        
        Returns:
            bool: True if Fast EMA is above others, False otherwise
        """
        return (self.ema_fast[0] > self.ema_medium[0] and 
                self.ema_fast[0] > self.ema_slow[0])

    def validate_historical_angles(self):
        """
        Validate that EMA angles met requirements for the specified historical periods.
        RELAXED RULES: Fast EMA must be positive, and at least 2/3 EMAs must be above threshold
        
        Returns:
            bool: True if historical angle requirements met, False otherwise
        """
        # Check if we have enough historical data
        if (len(self.angle_fast.lines.angle) < self.p.angle_validation_periods or
            len(self.angle_medium.lines.angle) < self.p.angle_validation_periods or
            len(self.angle_slow.lines.angle) < self.p.angle_validation_periods):
            return False
            
        # Check each required historical period
        for i in range(self.p.angle_validation_periods):
            lookback = -1 - i  # -1, -2, -3, etc. (previous bars before current)
            
            try:
                # Get historical angles
                hist_angle_fast = self.angle_fast.lines.angle[lookback]
                hist_angle_medium = self.angle_medium.lines.angle[lookback]
                hist_angle_slow = self.angle_slow.lines.angle[lookback]
                
                # RELAXED RULE 1: Fast EMA (most important) must be above threshold
                if hist_angle_fast <= self.p.min_angle_threshold:
                    return False
                
                # RELAXED RULE 2: At least 2 out of 3 EMAs must be above threshold
                positive_angles = 0
                if hist_angle_fast > self.p.min_angle_threshold:
                    positive_angles += 1
                if hist_angle_medium > self.p.min_angle_threshold:
                    positive_angles += 1
                if hist_angle_slow > self.p.min_angle_threshold:
                    positive_angles += 1
                    
                if positive_angles < 2:
                    return False
                
                # RELAXED RULE 3: Fast and Medium should have same direction (ignore slow EMA)
                # Both should be positive or both negative
                if not ((hist_angle_fast > 0 and hist_angle_medium > 0) or 
                       (hist_angle_fast < 0 and hist_angle_medium < 0)):
                    return False
                    
            except (IndexError, ValueError):
                return False  # Not enough data or invalid values
                
        return True

    def next(self):
        """Main strategy logic executed on each bar."""
        # Quiet bar processing
        
        # --- State Checks ---
        if self.cooldown_counter > 0: 
            self.cooldown_counter -= 1
            return
        if self.order_pending: 
            return

        # --- Exit Logic (Process if in position) ---
        if self.position:
            exit_triggered = False
            exit_reason = ""
            
            # Check EMA Exit Signal (Exit EMA1 crosses below Exit EMA2)
            if self.p.enable_ema_exit and self.exit_crossover[0] < 0:
                exit_triggered = True
                exit_reason = "EMA Exit (Exit1 crossed below Exit2)"
                
            if exit_triggered:
                if self.verbose:
                    print(f"--- EXIT SIGNAL @ {self.data.datetime.date(0)}: {exit_reason} ---")
                
                # Cancel pending orders first
                if self.stop_order:
                    self.cancel(self.stop_order)
                    self.stop_order = None
                if self.profit_order:
                    self.cancel(self.profit_order)
                    self.profit_order = None
                    
                # Close position
                self.close()
                self.exit_method = exit_reason
                
            return

        # --- Entry Logic (Process if not in position) ---
        
        # Skip if EMA indicators have invalid values
        if (np.isnan(self.ema_fast[0]) or np.isnan(self.ema_medium[0]) or 
            np.isnan(self.ema_slow[0]) or np.isnan(self.angle_fast[0]) or
            np.isnan(self.angle_medium[0]) or np.isnan(self.angle_slow[0])): 
            return
        
        # Stage 1: Detect EMA Crossover Pattern
        if not self.crossover_detected:
            if self.detect_stage1_crossover():
                self.crossover_detected = True
            return

        # Stage 2: Confirm Fast EMA Remains Above Others
        if not self.validate_stage2_confirmation():
            # Reset crossover flag if confirmation fails
            self.crossover_detected = False
            return
        
        # Angle Validation: Check Historical Angle Requirements
        if not self.validate_historical_angles():
            # Reset crossover flag if angle validation fails
            self.crossover_detected = False
            return
        
        # --- LONG ENTRY CONDITIONS (ALL REQUIREMENTS MET) ---
        if self.p.enable_long_entries:
            # Calculate current angles and divergences for reporting
            angle_fast = self.angle_fast[0]
            angle_medium = self.angle_medium[0]
            angle_slow = self.angle_slow[0]
            
            divergence_fast_medium = abs(angle_fast - angle_medium)
            divergence_medium_slow = abs(angle_medium - angle_slow)

            # Enforce max allowed divergence before entry (divergence must be < respective max)
            if (divergence_fast_medium >= self.p.max_angle_divergence_fm or
                divergence_medium_slow >= self.p.max_angle_divergence_ms):
                self.crossover_detected = False
                return

            # Additional entry condition: all three EMAs must be above the entry EMA
            if not (self.ema_fast[0] > self.entry_ema[0] and
                    self.ema_medium[0] > self.entry_ema[0] and
                    self.ema_slow[0] > self.entry_ema[0]):
                self.crossover_detected = False
                return
            
            # Calculate stop-loss and position size
            stop_price = self.data.close[0] - (self.p.stop_loss_pips * self.p.pip_value)
            size = self.calculate_order_size(stop_price)
            
            if size <= 0:
                if self.verbose:
                    print(f"DEBUG: Invalid position size ({size}) @ {self.data.datetime.date(0)}")
                self.crossover_detected = False
                return
            
            # Prepare profit and stop targets
            
            # Execute bracketed long order (parent + OCO children: TP/SL)
            profit_price = self.data.close[0] + (self.p.take_profit_pips * self.p.pip_value)
            stop_price = self.data.close[0] - (self.p.stop_loss_pips * self.p.pip_value)

            # Entry report similar to triangle.py (only if verbose)
            if self.verbose:
                entry_price = self.data.close[0]
                rr = (self.p.take_profit_pips / self.p.stop_loss_pips) if self.p.stop_loss_pips else 0.0
                est_risk_usd = abs((entry_price - stop_price) * size)
                risked_value = self.broker.get_value() * self.p.risk_percent
                print(f"ENTRY LONG @ {self.data.datetime.date(0)} | Price={entry_price:.5f} | Size={size}")
                print(f"  SL: {stop_price:.5f} ({self.p.stop_loss_pips:.1f} pips)  TP: {profit_price:.5f} ({self.p.take_profit_pips:.1f} pips)  R:R={rr:.2f}")
                print(f"  Risk Config: {self.p.risk_percent*100:.2f}% of equity ≈ ${risked_value:,.2f} | Est. $ risk at SL ≈ ${est_risk_usd:,.2f}")
                print(f"  Angles: Fast={angle_fast:.1f}°, Med={angle_medium:.1f}°, Slow={angle_slow:.1f}°  Div(F-M/M-S)={divergence_fast_medium:.1f}°/{divergence_medium_slow:.1f}°")
                print(f"  EMAs: Fast={self.ema_fast[0]:.5f}, Med={self.ema_medium[0]:.5f}, Slow={self.ema_slow[0]:.5f}, EntryEMA({self.p.entry_ema_period})={self.entry_ema[0]:.5f}")
                print(f"  Entry Validation: Angles>={self.p.min_angle_threshold}°, Divergences<F-M:{self.p.max_angle_divergence_fm}/M-S:{self.p.max_angle_divergence_ms}°, Fast>Med>Slow, All>EntryEMA")

            parent, take_profit, stop_loss = self.buy_bracket(
                size=size,
                limitprice=profit_price,
                stopprice=stop_price,
            )

            # Track orders (Backtrader returns: parent, takeprofit, stoploss)
            self.stop_order = stop_loss
            self.profit_order = take_profit
            self.order_pending = True
            self.crossover_detected = False  # Reset for next signal

            # Store entry data for reporting
            self.entry_angles = (angle_fast, angle_medium, angle_slow)
            self.entry_divergences = (divergence_fast_medium, divergence_medium_slow)

    def notify_order(self, order):
        """Handle order status notifications."""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
                if self.verbose:
                    print(f"LONG EXECUTED @ {order.executed.price:.5f} (Size: {order.executed.size})")

            elif order.issell():
                # This is a sell exit (closing long position)
                self.sell_price = order.executed.price
                if self.verbose:
                    print(f"SELL EXECUTED @ {order.executed.price:.5f}")
                
                # Determine exit method if not already set
                if not self.exit_method:
                    if order == self.stop_order:
                        self.exit_method = "Stop-Loss"
                    elif order == self.profit_order:
                        self.exit_method = "Take-Profit"
                    else:
                        self.exit_method = "Manual/Other"
                
                # Clear order references when any sell executes
                self.stop_order = None
                self.profit_order = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if self.verbose:
                print(f"ORDER FAILED/CANCELED: {order.getstatusname()}")
            
            # Clear order references when orders are canceled
            if order == self.stop_order:
                self.stop_order = None
            elif order == self.profit_order:
                self.profit_order = None

        # Clear pending flag regardless of outcome
        self.order_pending = False

    def notify_trade(self, trade):
        """Handle trade closure notifications and calculate performance metrics."""
        if trade.isclosed:
            self.num_closed_trades += 1
            pnl = trade.pnlcomm
            
            # Track win/loss statistics
            if pnl > 0: 
                self.total_gross_profit += pnl
                self.num_won_trades += 1
            else: 
                self.total_gross_loss += abs(pnl)
                self.num_lost_trades += 1
            
            # Apply cooldown after trade closure
            self.cooldown_counter = self.p.cooldown_period
            
            # Calculate PnL in pips using the stored entry and exit prices (long-only)
            if (hasattr(self, 'buy_price') and self.buy_price is not None and 
                hasattr(self, 'sell_price') and self.sell_price is not None):
                # For LONG positions: Exit price - Entry price
                price_diff = self.sell_price - self.buy_price
                pnl_pips = price_diff / self.p.pip_value
            else:
                pnl_pips = 0.0
            
            # Format reporting strings
            angles_str = "N/A"
            divergences_str = "N/A"
            if self.entry_angles:
                angles_str = f"Fast={self.entry_angles[0]:.1f}°, Med={self.entry_angles[1]:.1f}°, Slow={self.entry_angles[2]:.1f}°"
            if self.entry_divergences:
                divergences_str = f"F-M={self.entry_divergences[0]:.1f}°, M-S={self.entry_divergences[1]:.1f}°"
            
            # Print trade summary (only in verbose mode) - matches triangle.py format
            if self.verbose:
                print(f"--- TRADE CLOSED #{self.num_closed_trades} ---")
                print(f"  PnL: ${pnl:.2f}, PnL (pips): {pnl_pips:.1f}")
                print(f"  Entry Angles: {angles_str}")
                print(f"  Entry Divergences: {divergences_str}")
                print("-" * 50)
            
            # Reset entry and exit data
            self.entry_angles = None
            self.entry_divergences = None
            self.exit_method = None
            self.buy_price = None
            self.sell_price = None

    def stop(self):
        """Called when the strategy stops."""
        if self.verbose:
            print(f"\n=== TRIEMAHL2 STRATEGY STOPPED ===")
            print(f"Total trades executed: {self.num_closed_trades}")
            print(f"Data range: {self.data.datetime.date(0)} (last date)")
            print(f"Total bars processed: {len(self.data)}")
            print("=== END OF EXECUTION ===\n")

# --- STRATEGY EXECUTION ---

if __name__ == '__main__':
    # Initialize Cerebro engine (force bar-by-bar execution for optimization)
    cerebro = bt.Cerebro(runonce=False, optreturn=False)
    
    # Configure strategy based on mode
    if OPTIMIZATION_MODE:
        print("=== TRIEMAHL2 OPTIMIZATION MODE ENABLED ===")
        print("Running parameter optimization...")
        
        # Add strategy with parameter ranges for optimization
        cerebro.optstrategy(
            Triemahl2Strategy,
            ema_fast_period=OPTIMIZATION_PARAMS['ema_fast_period'],
            ema_medium_period=OPTIMIZATION_PARAMS['ema_medium_period'],
            ema_slow_period=OPTIMIZATION_PARAMS['ema_slow_period'],
            min_angle_threshold=OPTIMIZATION_PARAMS['min_angle_threshold'],
            max_angle_divergence_fm=OPTIMIZATION_PARAMS['max_angle_divergence_fm'],
            max_angle_divergence_ms=OPTIMIZATION_PARAMS['max_angle_divergence_ms'],
            angle_validation_periods=OPTIMIZATION_PARAMS['angle_validation_periods'],
            stop_loss_pips=OPTIMIZATION_PARAMS['stop_loss_pips'],
            take_profit_pips=OPTIMIZATION_PARAMS['take_profit_pips'],
            risk_percent=OPTIMIZATION_PARAMS['risk_percent'],
            verbose=[False]  # Silent during optimization
        )
        
        # Add analyzers for performance metrics
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='tradeanalyzer')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        
    else:
        print("=== TRIEMAHL2 STANDARD MODE ===")
        # Add strategy with default parameters
        cerebro.addstrategy(Triemahl2Strategy)
    
    # Load and configure data feed
    data = bt.feeds.GenericCSVData(
        dataname=str(DATA_PATH), 
        dtformat=('%Y%m%d'), 
        tmformat=('%H:%M:%S'),
        datetime=0, time=1, open=2, high=3, low=4, close=5, volume=6,
        timeframe=bt.TimeFrame.Minutes, 
        compression=5
    )
    cerebro.adddata(data)
    
    # Configure broker settings from configuration
    cerebro.broker.setcash(BROKER_CONFIG['start_cash'])
    cerebro.broker.setcommission(leverage=BROKER_CONFIG['leverage'])

    # Run backtest based on mode
    if OPTIMIZATION_MODE:
        total_combinations = (len(OPTIMIZATION_PARAMS['ema_fast_period']) *
                              len(OPTIMIZATION_PARAMS['ema_medium_period']) *
                              len(OPTIMIZATION_PARAMS['ema_slow_period']) *
                              len(OPTIMIZATION_PARAMS['min_angle_threshold']) *
                              len(OPTIMIZATION_PARAMS['max_angle_divergence_fm']) *
                              len(OPTIMIZATION_PARAMS['max_angle_divergence_ms']) *
                              len(OPTIMIZATION_PARAMS['angle_validation_periods']) *
                              len(OPTIMIZATION_PARAMS['stop_loss_pips']) *
                              len(OPTIMIZATION_PARAMS['take_profit_pips']) *
                              len(OPTIMIZATION_PARAMS['risk_percent']))

        print(f"Testing {total_combinations} parameter combinations...")

        # Run optimization
        optimization_results = cerebro.run()

        # Process and Print the Results
        final_results_list = []
        for single_run_results in optimization_results:
            for strategy_result in single_run_results:
                # Access parameters for this run
                params = strategy_result.p

                # Access analyzers for this run
                trade_analysis = strategy_result.analyzers.tradeanalyzer.get_analysis()
                return_analysis = strategy_result.analyzers.returns.get_analysis()

                total_trades = trade_analysis.get('total', {}).get('total', 0)

                # Calculate Profit Factor
                profit_factor = 0.0
                if 'won' in trade_analysis and 'lost' in trade_analysis:
                    total_won = trade_analysis.get('won', {}).get('pnl', {}).get('total', 0)
                    total_lost = abs(trade_analysis.get('lost', {}).get('pnl', {}).get('total', 0))
                    if total_lost > 0:
                        profit_factor = total_won / total_lost

                final_results_list.append({
                    'fast': params.ema_fast_period,
                    'medium': params.ema_medium_period,
                    'slow': params.ema_slow_period,
                    'angle': params.min_angle_threshold,
                    'div_fm': params.max_angle_divergence_fm,
                    'div_ms': params.max_angle_divergence_ms,
                    'validation': params.angle_validation_periods,
                    'stop': params.stop_loss_pips,
                    'profit': params.take_profit_pips,
                    'risk': params.risk_percent,
                    'profit_factor': profit_factor,
                    'total_trades': total_trades,
                    'final_value': return_analysis.get('rtot', 1) * cerebro.broker.startingcash
                })

        # Sort results to find the best combination
        sorted_results = sorted(final_results_list, key=lambda x: x['profit_factor'], reverse=True)

        print("\n--- Top Parameter Combinations by Profit Factor ---")
        print(f"{'Fast':<4} {'Med':<3} {'Slow':<4} {'Angle':<5} {'DivFM':<5} {'DivMS':<5} {'Val':<3} {'Stop':<4} {'Profit':<6} {'Risk%':<5} {'P.Factor':<8} {'Trades':<6} {'FinalValue':<10}")
        print("-" * 85)
        for res in sorted_results[:20]:  # Show top 20 results
            print(f"{res['fast']:<4} {res['medium']:<3} {res['slow']:<4} {res['angle']:<5.0f} {res['div_fm']:<5} {res['div_ms']:<5} {res['validation']:<3} {res['stop']:<4.0f} {res['profit']:<6.0f} {res['risk']:<5.3f} {res['profit_factor']:<8.2f} {res['total_trades']:<6} {res['final_value']:<10.0f}")

    else:
        print("--- Running Triemahl2 Strategy Backtest ---")
        results = cerebro.run()

        # Generate detailed performance report
        the_strategy = results[0]
        print("\n" + "=" * 60)
        print("--- FINAL BACKTEST REPORT ---")
        print(f"Initial Portfolio Value:  ${BROKER_CONFIG['start_cash']:,.2f}")
        print(f"Final Portfolio Value:    ${cerebro.broker.getvalue():,.2f}")
        print(f"Total Return:             ${cerebro.broker.getvalue() - BROKER_CONFIG['start_cash']:,.2f}")
        print(f"Total Trades Closed:      {the_strategy.num_closed_trades}")
        print(f"Won Trades:               {the_strategy.num_won_trades}")
        print(f"Lost Trades:              {the_strategy.num_lost_trades}")

        # Calculate and display profit factor and win rate
        if the_strategy.num_closed_trades > 0:
            win_rate = (the_strategy.num_won_trades / the_strategy.num_closed_trades) * 100
            print(f"Win Rate:                 {win_rate:.1f}%")

            if the_strategy.total_gross_loss > 0:
                profit_factor = the_strategy.total_gross_profit / the_strategy.total_gross_loss
                print(f"Profit Factor:            {profit_factor:.2f}")
            elif the_strategy.total_gross_profit > 0:
                print("Profit Factor:            Inf (No losing trades)")
            else:
                print("Profit Factor:            N/A (No closed trades with PnL)")
        else:
            print("Win Rate:                 N/A (No trades closed)")
            print("Profit Factor:            N/A (No trades closed)")

        print("=" * 60 + "\n")

        # Generate strategy performance plot
        print("Generating strategy performance plot...")
        try:
            cerebro.plot(style='line', volume=False, plotdist=1.0, figsize=(16, 10))
            print("Plot generated successfully!")
        except Exception as e:
            print(f"Plot generation failed: {e}")
            print("This is normal in some environments. The backtest results are still valid.")
