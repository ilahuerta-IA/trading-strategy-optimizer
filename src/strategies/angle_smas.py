# -----------------------------------------------------------------------------
# ANGLE SMA TRADING STRATEGY
# -----------------------------------------------------------------------------
# A technical analysis-based trading strategy that combines:
# - Multiple SMA (Simple Moving Average) filters for trend confirmation
# - Custom angle indicators for momentum analysis
# - Robust stop-loss and exit signal management
# - Risk-based position sizing
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

# --- PROJECT PATH CONFIGURATION ---
try:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    DATA_PATH = PROJECT_ROOT / 'data' / 'EURUSD_5m_8Yea.csv'  # Multiple data files available
    # Alternative data files:
    # 'XAUUSD_5m_1Yea(new).csv', 'GBPUSD_5m_2Mon.csv', 'EURUSD_5m_2Yea.csv', 'EURUSD_5m_2Mon.csv', 'USDCHF_5m_1Yea.csv'
    
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

class StableSMAStrategy(bt.Strategy):
    """
    Technical analysis-based trading strategy using multiple SMA filters and angle indicators.
    
    Strategy Logic:
    1. Entry: Uses multiple SMA confirmation signals with angle-based momentum analysis
    2. Exit: Implements both stop-loss orders and crossover-based exit signals
    3. Risk Management: Position sizing based on portfolio risk percentage and stop-loss distance
    
    Key Features:
    - Multiple moving average filters for trend confirmation
    - Angle-based momentum analysis for entry timing
    - Robust order management with cooldown periods
    - Detailed trade reporting with pip-based PnL calculation
    """
    
    params = (
        # Indicator periods (IDENTICAL to transformer strategy)
        ('pred_smooth_period', 5),       # SMA period for smoothing predictions
        ('sma_momentum_period', 28),     # Momentum SMA period  #50
        ('sma_long_term_period', 100),   # Long-term trend SMA period
        ('sma_short_term_period', 7),    # Short-term SMA period
        
        # Entry signal filters (IDENTICAL to transformer strategy)
        ('min_angle_for_entry', 85.0),   # Minimum angle (degrees) for entry signal
        ('max_abs_divergence_entry', 10.0),  # Max divergence between prediction/price angles
        
        # Risk management (IDENTICAL to transformer strategy)
        ('risk_percent', 0.01),          # Portfolio risk per trade (1%)
        ('stop_loss_pips', 10.0),        # Stop-loss distance in pips
        ('pip_value', 0.0001),           # Pip value for EUR/USD (0.0001)
        ('cooldown_period', 5),          # Bars to wait after trade closure
    )

    def __init__(self):
        """Initialize strategy indicators and state management variables."""
        # --- Technical Indicators (IDENTICAL to transformer strategy) ---
        self.prediction = self.data.close  # Use close price as "prediction" for comparison
        self.smoothed_prediction = bt.indicators.SMA(self.prediction, period=self.p.pred_smooth_period)
        self.sma_short_term = bt.indicators.SMA(self.data.close, period=self.p.sma_short_term_period)
        self.sma_long_term = bt.indicators.SMA(self.data.close, period=self.p.sma_long_term_period)
        self.sma_momentum = bt.indicators.SMA(self.data.close, period=self.p.sma_momentum_period)
        self.smooth_cross_momentum = bt.indicators.CrossOver(self.smoothed_prediction, self.sma_momentum)
        self.angle_prediction = AngleIndicator(self.smoothed_prediction, angle_lookback=self.p.pred_smooth_period)
        self.angle_price = AngleIndicator(self.sma_short_term, angle_lookback=self.p.sma_short_term_period)
        
        # --- State Management Variables ---
        self.cooldown_counter = 0           # Prevents immediate re-entry after trade closure
        self.stop_order = None              # Reference to current stop-loss order
        self.order_pending = False          # Flag to prevent overlapping entry orders
        self.buy_price = None               # Entry price for stop-loss calculation
        self.sell_price = None              # Exit price for PnL calculation
        
        # --- Performance Tracking ---
        self.total_gross_profit = 0.0
        self.total_gross_loss = 0.0
        self.num_closed_trades = 0
        self.num_won_trades = 0
        self.num_lost_trades = 0
        self.entry_angle = None             # Store entry angle for reporting
        self.entry_divergence = None        # Store entry divergence for reporting 

    def calculate_order_size(self, stop_price):
        """
        Calculate position size based on risk percentage and stop-loss distance.
        
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
            # Check for crossover exit signal
            if self.smooth_cross_momentum[0] < 0:
                print(f"--- EXIT SIGNAL @ {self.data.datetime.date(0)}: Crossover exit ---")
                # Cancel pending stop-loss first
                if self.stop_order:
                    self.cancel(self.stop_order)
                    self.stop_order = None
                # Then close position
                self.close()
            return

        # --- Entry Logic ---
        # Skip if angle indicators have invalid values
        if np.isnan(self.angle_prediction[0]) or np.isnan(self.angle_price[0]): 
            return
        
        # Calculate entry conditions
        abs_divergence = abs(self.angle_prediction[0] - self.angle_price[0])
        is_bullish_filter = (self.sma_long_term[0] < self.prediction[0] and 
                           self.sma_momentum[0] < self.prediction[0])
        is_strong_momentum = (self.smoothed_prediction[0] > self.smoothed_prediction[-1] and 
                             self.sma_short_term[0] > self.sma_short_term[-1] and
                             self.sma_long_term[0] > self.sma_long_term[-1] and
                             self.sma_momentum[0] > self.sma_momentum[-1])
        is_crossover_signal = self.smooth_cross_momentum[0] > 0
        is_steep_angle = self.angle_prediction[0] > self.p.min_angle_for_entry
        is_coherent_signal = abs_divergence < self.p.max_abs_divergence_entry

        # Enter position if all conditions are met
        if (is_bullish_filter and is_strong_momentum and is_crossover_signal and 
            is_steep_angle and is_coherent_signal):
            
            stop_price = self.data.close[0] - (self.p.stop_loss_pips * self.p.pip_value)
            size = self.calculate_order_size(stop_price)
            if size <= 0: 
                return

            # VALIDATION: Double-check angle at execution time to prevent timing issues
            current_angle = self.angle_prediction[0]
            if current_angle <= self.p.min_angle_for_entry:
                print(f"--- ENTRY REJECTED @ {self.data.datetime.date(0)}: Angle dropped to {current_angle:.2f}° (need >{self.p.min_angle_for_entry}°) ---")
                return

            print(f"--- ATTEMPTING BUY @ {self.data.datetime.date(0)} (Size: {size}, Stop: {stop_price:.5f}) ---")
            print(f"  Entry Validation: Angle={current_angle:.2f}°, Divergence={abs_divergence:.2f}°")
            
            # Simple buy order (no brackets)
            self.buy(size=size)
            self.order_pending = True
            
            # Store entry data for reporting (store the VALIDATED values when signal was generated)
            self.entry_angle = current_angle
            self.entry_divergence = abs_divergence

    def notify_order(self, order):
        """Handle order status notifications."""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
                print(f"BUY EXECUTED @ {order.executed.price:.5f} (Size: {order.executed.size})")
                # Place stop-loss order after buy execution
                if not self.stop_order:
                    stop_price = self.buy_price - (self.p.stop_loss_pips * self.p.pip_value)
                    self.stop_order = self.sell(
                        size=order.executed.size, 
                        exectype=bt.Order.Stop, 
                        price=stop_price
                    )
                    print(f"STOP-LOSS PLACED @ {stop_price:.5f}")
            elif order.issell():
                self.sell_price = order.executed.price  # Store sell price for PnL calculation
                print(f"SELL EXECUTED @ {order.executed.price:.5f}")
                self.stop_order = None  # Clear stop order reference

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f"ORDER FAILED/CANCELED: {order.getstatusname()}")

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
            
            # Calculate PnL in pips using the stored entry and exit prices
            if (hasattr(self, 'buy_price') and self.buy_price is not None and 
                hasattr(self, 'sell_price') and self.sell_price is not None):
                price_diff = self.sell_price - self.buy_price  # Exit price - Entry price
                pnl_pips = price_diff / self.p.pip_value
            else:
                pnl_pips = 0.0
            
            # Format reporting strings
            angle_str = f"{self.entry_angle:.2f}°" if self.entry_angle is not None else "N/A"
            divergence_str = f"{self.entry_divergence:.2f}°" if self.entry_divergence is not None else "N/A"
            
            # Print trade summary
            print(f"--- TRADE CLOSED #{self.num_closed_trades} ---")
            print(f"  PnL: ${pnl:.2f}, PnL (pips): {pnl_pips:.1f}")
            print(f"  Entry Angle: {angle_str}, Entry Divergence: {divergence_str}")
            print("-" * 50)
            
            # Reset entry data
            self.entry_angle, self.entry_divergence = None, None

    def stop(self):
        """Called when the strategy stops. Final cleanup if needed."""
        print(f"\n=== STRATEGY STOPPED ===")
        print(f"Total trades executed: {self.num_closed_trades}")
        print("=== END OF EXECUTION ===\n")

# --- STRATEGY EXECUTION ---

if __name__ == '__main__':
    # Initialize Cerebro engine
    cerebro = bt.Cerebro(runonce=False)
    cerebro.addstrategy(StableSMAStrategy)
    
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
    
    # Configure broker settings (no commission/slippage as requested)
    start_cash = 100000.0
    cerebro.broker.setcash(start_cash)
    cerebro.broker.setcommission(leverage=30.0)

    # Run backtest
    print("--- Running Angle SMA Strategy Backtest ---")
    results = cerebro.run()
    
    # Generate final performance report
    the_strategy = results[0]
    print("\n" + "=" * 60)
    print("--- FINAL BACKTEST REPORT ---")
    print(f"Initial Portfolio Value:  ${start_cash:,.2f}")
    print(f"Final Portfolio Value:    ${cerebro.broker.getvalue():,.2f}")
    print(f"Total Return:             ${cerebro.broker.getvalue() - start_cash:,.2f}")
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