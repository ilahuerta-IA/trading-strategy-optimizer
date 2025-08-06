# -----------------------------------------------------------------------------
# TRIANGLE TRADING STRATEGY
# -----------------------------------------------------------------------------
# A technical analysis-based trading strategy that uses 3 SMAs forming a "triangle"
# of trend analysis to determine entry conditions based on angle momentum.
# 
# Strategy Concept:
# - 3 SMAs: Fast (7), Medium (9), Slow (11) periods
# - All 3 angles must exceed minimum thresholds for long entry
# - Long-only strategy with crossover exit signals
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
DATA_FILE = 'EURUSD_5m_2Yea.csv'  # Select data file to use (2 months of data)
# Alternative files: 'XAUUSD_5m_1Yea(new).csv', 'GBPUSD_5m_2Mon.csv', 'EURUSD_5m_2Yea.csv', 'EURUSD_5m_8Yea.csv', 'USDCHF_5m_1Yea.csv'

# Execution Mode Configuration
OPTIMIZATION_MODE = False  # Set to True to enable parameter optimization

# Strategy Default Parameters (used when OPTIMIZATION_MODE = False)
DEFAULT_PARAMS = {
    'sma_fast_period': 7,               # Fast SMA period (shortest)
    'sma_medium_period': 9,             # Medium SMA period
    'sma_slow_period': 11,               # Slow SMA period (longest)
    'min_angle_for_long_entry': 60.0,   # Minimum angle (degrees) for long entry
    'max_angle_divergence': 2.0,       # Max angle divergence between SMAs (degrees)
    'angle_persistence_bars': 2,        # Bars angles must stay above threshold (persistence)
    'enable_long_entries': True,         # Flag to enable long entries
    'risk_percent': 0.005,               # Portfolio risk per trade (0.5%)
    'stop_loss_pips': 10.0,             # Stop-loss distance in pips
    'pip_value': 0.0001,                # Pip value for EUR/USD (0.0001)
    'cooldown_period': 5,               # Bars to wait after trade closure
}

# Optimization Parameters (used when OPTIMIZATION_MODE = True)
OPTIMIZATION_PARAMS = {
    'min_angle_for_long_entry': range(55, 85, 5),      # Test: 55, 60, 65, 70, 75, 80
    'max_angle_divergence': range(10, 21, 5),          # Test: 10, 15, 20
    'angle_persistence_bars': [1, 2, 3],               # Test: 1, 2, 3 bars persistence
    'risk_percent': [0.005, 0.01],              # Test different risk levels
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

class AngleIndicator(bt.Indicator):
    """
    Custom indicator that calculates the angle (in degrees) of price movement
    over a specified lookback period. Useful for measuring momentum steepness.
    """
    lines = ('angle',)
    params = (
        ('angle_lookback', 5),     # Periods to look back for angle calculation
        ('scale_factor', 50000),   # Scale factor to amplify small price movements
    )
    plotinfo = dict(subplot=True, plotname='Angle (Degrees)')
    
    def __init__(self):
        self.addminperiod(self.p.angle_lookback)
        super().__init__()

    def next(self):
        """Calculate the angle of price movement over the lookback period."""
        rise = (self.data0[0] - self.data0[-self.p.angle_lookback + 1]) * self.p.scale_factor
        run = self.p.angle_lookback
        self.lines.angle[0] = np.degrees(np.arctan2(rise, run))

# --- MAIN TRADING STRATEGY ---

class TriangleStrategy(bt.Strategy):
    """
    Triangle trading strategy using 3 SMAs with angle-based entry conditions.
    
    Strategy Logic:
    1. Calculate angles for 3 SMAs (Fast, Medium, Slow periods)
    2. Long Entry: All angles > min_angle_for_long_entry
    3. Exit: Stop-loss orders and crossover exit signals
    
    Key Features:
    - 3 SMA triangle analysis for trend confirmation
    - Angle-based momentum analysis for long entries only
    - Risk-based position sizing with stop-loss protection
    """
    
    params = (
        # Strategy parameters - defaults from configuration section
        ('sma_fast_period', DEFAULT_PARAMS['sma_fast_period']),
        ('sma_medium_period', DEFAULT_PARAMS['sma_medium_period']),
        ('sma_slow_period', DEFAULT_PARAMS['sma_slow_period']),
        ('min_angle_for_long_entry', DEFAULT_PARAMS['min_angle_for_long_entry']),
        ('max_angle_divergence', DEFAULT_PARAMS['max_angle_divergence']),
        ('angle_persistence_bars', DEFAULT_PARAMS['angle_persistence_bars']),
        ('enable_long_entries', DEFAULT_PARAMS['enable_long_entries']),
        ('risk_percent', DEFAULT_PARAMS['risk_percent']),
        ('stop_loss_pips', DEFAULT_PARAMS['stop_loss_pips']),
        ('pip_value', DEFAULT_PARAMS['pip_value']),
        ('cooldown_period', DEFAULT_PARAMS['cooldown_period']),
        ('verbose', True),               # Enable/disable detailed output (False for optimization)
    )

    def __init__(self):
        """Initialize strategy indicators and state management variables."""
        # --- Technical Indicators (Triangle SMAs) ---
        self.sma_fast = bt.indicators.SMA(self.data.close, period=self.p.sma_fast_period)
        self.sma_medium = bt.indicators.SMA(self.data.close, period=self.p.sma_medium_period)
        self.sma_slow = bt.indicators.SMA(self.data.close, period=self.p.sma_slow_period)
        
        # --- Angle Indicators for each SMA ---
        self.angle_fast = AngleIndicator(self.sma_fast, angle_lookback=self.p.sma_fast_period)
        self.angle_medium = AngleIndicator(self.sma_medium, angle_lookback=self.p.sma_medium_period)
        self.angle_slow = AngleIndicator(self.sma_slow, angle_lookback=self.p.sma_slow_period)
        
        # --- Simple Crossover Exit Signal (like angle_smas.py) ---
        self.fast_cross_medium = bt.indicators.CrossOver(self.sma_fast, self.sma_medium)
        
        # --- State Management Variables ---
        self.cooldown_counter = 0           # Prevents immediate re-entry after trade closure
        self.stop_order = None              # Reference to current stop-loss order
        self.order_pending = False          # Flag to prevent overlapping entry orders
        self.buy_price = None               # Entry price for stop-loss calculation
        self.sell_price = None              # Exit price for PnL calculation
        
        # --- Performance Tracking ---
        self.num_closed_trades = 0
        self.num_won_trades = 0
        self.num_lost_trades = 0
        self.total_gross_profit = 0.0
        self.total_gross_loss = 0.0
        self.entry_angles = None            # Store entry angles for reporting
        self.entry_divergences = None       # Store angle divergences for reporting
        
        # --- Optimization Mode Detection ---
        self.verbose = self.p.verbose  # Use parameter to control verbosity

    def start(self):
        """Called when the strategy starts."""
        if self.verbose:
            print(f"=== TRIANGLE STRATEGY STARTED ===")
            print(f"Data start date: {self.data.datetime.date(0)}")
            print(f"Strategy parameters:")
            print(f"  SMAs: Fast={self.p.sma_fast_period}, Medium={self.p.sma_medium_period}, Slow={self.p.sma_slow_period}")
            print(f"  Entry angle threshold: {self.p.min_angle_for_long_entry}°")
            print(f"  Max angle divergence: {self.p.max_angle_divergence}°")
            print(f"  Angle persistence: {self.p.angle_persistence_bars} consecutive bars")
            print(f"  Entry conditions: All angles > threshold + Fast SMA crosses above Medium SMA + Angle coherence + Persistence")
            print(f"  Risk per trade: {self.p.risk_percent*100}%")
            print(f"  Stop-loss: {self.p.stop_loss_pips} pips")
            print(f"  Exit condition: Fast SMA crosses below Medium SMA (simple crossover)")
            print(f"  Long entries: {'Enabled' if self.p.enable_long_entries else 'Disabled'}")
            print("========================\n")

    def calculate_order_size(self, stop_price):
        """
        Calculate position size based on risk percentage and stop-loss distance.
        (Following angle_smas.py approach)
        
        Args:
            stop_price: The stop-loss price level
            
        Returns:
            Position size (number of units to trade)
        """
        risked_value = self.broker.get_value() * self.p.risk_percent
        entry_price = self.data.close[0]
        pnl_per_unit = abs(entry_price - stop_price)
        
        if pnl_per_unit == 0:
            return 0
            
        position_size = risked_value / pnl_per_unit
        return math.floor(position_size)

    def check_angle_persistence(self, angle_fast, angle_medium, angle_slow):
        """
        Check if all angles have been above threshold for the required consecutive bars.
        
        Args:
            angle_fast: Current fast angle
            angle_medium: Current medium angle  
            angle_slow: Current slow angle
            
        Returns:
            bool: True if all angles have persistence, False otherwise
        """
        # Check if we have enough historical data
        if len(self.angle_fast.lines.angle) < self.p.angle_persistence_bars:
            return False
            
        # Check each required consecutive bar
        for i in range(self.p.angle_persistence_bars):
            lookback = -i  # 0, -1, -2, etc. (current bar to past bars)
            
            # Get historical angles for this bar
            try:
                hist_fast = self.angle_fast.lines.angle[lookback]
                hist_medium = self.angle_medium.lines.angle[lookback]
                hist_slow = self.angle_slow.lines.angle[lookback]
            except IndexError:
                return False  # Not enough data
                
            # Check if any angle was below threshold on this historical bar
            if (hist_fast <= self.p.min_angle_for_long_entry or
                hist_medium <= self.p.min_angle_for_long_entry or
                hist_slow <= self.p.min_angle_for_long_entry):
                return False
                
        return True

    def next(self):
        """Main strategy logic executed on each bar."""
        # --- State Checks ---
        if self.cooldown_counter > 0: 
            self.cooldown_counter -= 1
            return
        if self.order_pending: 
            return

        # --- Exit Logic ---
        if self.position:
            # Simple crossover exit: fast crosses below medium (bearish signal)
            if self.fast_cross_medium[0] < 0:
                if self.verbose:
                    print(f"--- EXIT SIGNAL @ {self.data.datetime.date(0)}: Fast SMA crossed below Medium SMA ---")
                # Cancel pending stop-loss first (critical fix like angle_smas)
                if self.stop_order:
                    if self.verbose:
                        print(f"CANCELING STOP-LOSS ORDER")
                    self.cancel(self.stop_order)
                    self.stop_order = None
                # Then close position
                self.close()
            return

        # --- Entry Logic ---
        # Skip if angle indicators have invalid values
        if (np.isnan(self.angle_fast[0]) or np.isnan(self.angle_medium[0]) or 
            np.isnan(self.angle_slow[0])): 
            return
        
        # Get current angles
        angle_fast = self.angle_fast[0]
        angle_medium = self.angle_medium[0]
        angle_slow = self.angle_slow[0]
        
        # Calculate angle divergences (coherence check)
        divergence_fast_medium = abs(angle_fast - angle_medium)
        divergence_medium_slow = abs(angle_medium - angle_slow)
        
        # Check angle persistence (complex condition)
        has_persistence = self.check_angle_persistence(angle_fast, angle_medium, angle_slow)
        
        # --- LONG ENTRY CONDITIONS (ONLY) ---
        if (self.p.enable_long_entries and 
            angle_fast > self.p.min_angle_for_long_entry and
            angle_medium > self.p.min_angle_for_long_entry and
            angle_slow > self.p.min_angle_for_long_entry and
            self.fast_cross_medium[0] > 0 and  # Fast crosses above Medium (bullish signal)
            divergence_fast_medium < self.p.max_angle_divergence and  # Coherent angles
            divergence_medium_slow < self.p.max_angle_divergence and    # Coherent angles
            has_persistence):  # NEW: Angle persistence check
            
            stop_price = self.data.close[0] - (self.p.stop_loss_pips * self.p.pip_value)
            size = self.calculate_order_size(stop_price)
            
            if size <= 0:
                return
            
            # VALIDATION: Double-check angles and persistence at execution time
            if (angle_fast <= self.p.min_angle_for_long_entry or 
                angle_medium <= self.p.min_angle_for_long_entry or 
                angle_slow <= self.p.min_angle_for_long_entry or
                divergence_fast_medium >= self.p.max_angle_divergence or
                divergence_medium_slow >= self.p.max_angle_divergence or
                not has_persistence):
                if self.verbose:
                    print(f"--- ENTRY REJECTED @ {self.data.datetime.date(0)}: Angles/divergences/persistence weakened ---")
                return
            
            if self.verbose:
                print(f"--- ATTEMPTING LONG @ {self.data.datetime.date(0)} (Size: {size}, Stop: {stop_price:.5f}) ---")
                print(f"  Triangle Angles: Fast={angle_fast:.2f}°, Medium={angle_medium:.2f}°, Slow={angle_slow:.2f}°")
                print(f"  Angle Divergences: Fast-Med={divergence_fast_medium:.2f}°, Med-Slow={divergence_medium_slow:.2f}°")
                print(f"  Angle Persistence: {self.p.angle_persistence_bars} bars ✓")
                print(f"  SMA Values: Fast={self.sma_fast[0]:.5f}, Med={self.sma_medium[0]:.5f}, Slow={self.sma_slow[0]:.5f}")
                print(f"  Entry Validation: All angles > {self.p.min_angle_for_long_entry}° + Divergences < {self.p.max_angle_divergence}° + Crossover + Persistence")
                print(f"  Crossover Signal: {self.fast_cross_medium[0]} (1=bullish crossover, 0=no crossover, -1=bearish crossover)")
            
            # Simple buy order (following angle_smas approach)
            self.buy(size=size)
            self.order_pending = True
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
                # Place stop-loss order after buy execution
                if not self.stop_order:
                    stop_price = self.buy_price - (self.p.stop_loss_pips * self.p.pip_value)
                    self.stop_order = self.sell(
                        size=order.executed.size, 
                        exectype=bt.Order.Stop, 
                        price=stop_price
                    )
                    if self.verbose:
                        print(f"STOP-LOSS PLACED @ {stop_price:.5f}")
            elif order.issell():
                # This is a sell exit (closing long position)
                self.sell_price = order.executed.price
                if self.verbose:
                    print(f"SELL EXECUTED @ {order.executed.price:.5f}")
                # CRITICAL FIX: Clear stop order reference when any sell executes
                self.stop_order = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if self.verbose:
                print(f"ORDER FAILED/CANCELED: {order.getstatusname()}")
            # CRITICAL FIX: Clear stop order reference when order is canceled
            if order == self.stop_order:
                self.stop_order = None

        # Clear pending flag regardless of outcome
        self.order_pending = False

    def notify_trade(self, trade):
        """Handle trade closure notifications and calculate performance metrics."""
        if trade.isclosed:
            self.num_closed_trades += 1
            pnl = trade.pnlcomm
            
            # Track win/loss statistics correctly
            if pnl > 0: 
                self.total_gross_profit += pnl
                self.num_won_trades += 1
            else: 
                self.total_gross_loss += abs(pnl)
                self.num_lost_trades += 1
            
            # Apply cooldown after trade closure to prevent immediate re-entry
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
            
            # Print trade summary (only in verbose mode)
            if self.verbose:
                print(f"--- TRADE CLOSED #{self.num_closed_trades} ---")
                print(f"  PnL: ${pnl:.2f}, PnL (pips): {pnl_pips:.1f}")
                print(f"  Entry Angles: {angles_str}")
                print(f"  Entry Divergences: {divergences_str}")
                print("-" * 50)
            
            # Reset entry data
            self.entry_angles = None
            self.entry_divergences = None
            self.buy_price = None
            self.sell_price = None

    def stop(self):
        """Called when the strategy stops. Final cleanup if needed."""
        if self.verbose:
            print(f"\n=== STRATEGY STOPPED ===")
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
        print("=== OPTIMIZATION MODE ENABLED ===")
        print("Running parameter optimization...")
        
        # Add strategy with parameter ranges for optimization
        cerebro.optstrategy(
            TriangleStrategy,
            min_angle_for_long_entry=OPTIMIZATION_PARAMS['min_angle_for_long_entry'],
            max_angle_divergence=OPTIMIZATION_PARAMS['max_angle_divergence'],
            angle_persistence_bars=OPTIMIZATION_PARAMS['angle_persistence_bars'],
            risk_percent=OPTIMIZATION_PARAMS['risk_percent'],
            verbose=[False]  # Silent during optimization
        )
        
        # Add analyzers for performance metrics
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='tradeanalyzer')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        
    else:
        print("=== STANDARD MODE ===")
        # Add strategy with default parameters
        cerebro.addstrategy(TriangleStrategy)
    
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
        print(f"Testing {len(OPTIMIZATION_PARAMS['min_angle_for_long_entry']) * len(OPTIMIZATION_PARAMS['max_angle_divergence']) * len(OPTIMIZATION_PARAMS['angle_persistence_bars']) * len(OPTIMIZATION_PARAMS['risk_percent'])} parameter combinations...")
        
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
                    'long_angle': params.min_angle_for_long_entry,
                    'max_divergence': params.max_angle_divergence,
                    'persistence_bars': params.angle_persistence_bars,
                    'risk_pct': params.risk_percent,
                    'profit_factor': profit_factor,
                    'total_trades': total_trades,
                    'final_value': return_analysis.get('rtot', 1) * cerebro.broker.startingcash
                })

        # Sort results to find the best combination
        sorted_results = sorted(final_results_list, key=lambda x: x['profit_factor'], reverse=True)
        
        print("\n--- Top Parameter Combinations by Profit Factor ---")
        print(f"{'LongAngle':<10} {'MaxDiv':<7} {'Persist':<8} {'Risk%':<6} {'P.Factor':<9} {'Trades':<7} {'Final Value':<12}")
        print("-" * 68)
        for res in sorted_results:
            print(f"{res['long_angle']:<10.0f} {res['max_divergence']:<7.0f} {res['persistence_bars']:<8} {res['risk_pct']:<6.3f} {res['profit_factor']:<9.2f} {res['total_trades']:<7} {res['final_value']:<12.2f}")
        
    else:
        print("--- Running Triangle Strategy Backtest ---")
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
