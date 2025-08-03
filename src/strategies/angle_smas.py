# -----------------------------------------------------------------------------
# DISCLAIMER:
# This software is for educational and research purposes only.
# It is not intended for live trading or financial advice.
# Trading in financial markets involves substantial risk of loss.
# Use at your own risk. The author assumes no liability for any losses.
# -----------------------------------------------------------------------------

import backtrader as bt
import pandas as pd
import numpy as np
from pathlib import Path
import math

# --- GLOBAL PATH CONFIGURATION ---
try:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    DATA_PATH = PROJECT_ROOT / 'data' /  'USDCHF_5m_1Yea.csv'#'GBPUSD_5m_2Mon.csv'#'EURUSD_5m_2Yea.csv'#'EURUSD_5m_2Mon.csv'
    if not DATA_PATH.exists():
        print(f"FATAL: Data file not found at {DATA_PATH}")
        exit()
except Exception:
    print("FATAL: Could not determine project paths. Please run from the project root.")
    exit()

# --- INDICATOR: ANGLE OF A LINE (Unchanged) ---
class AngleIndicator(bt.Indicator):
    lines = ('angle',)
    params = (('angle_lookback', 5), ('scale_factor', 50000),)
    plotinfo = dict(subplot=True, plotname='Angle (Degrees)')
    
    def __init__(self):
        self.addminperiod(self.p.angle_lookback)
        super().__init__()

    def next(self):
        rise = (self.data0[0] - self.data0[-self.p.angle_lookback + 1]) * self.p.scale_factor
        run = self.p.angle_lookback
        self.lines.angle[0] = np.degrees(np.arctan2(rise, run))

# --- MAIN TRADING STRATEGY with ROBUST TRADE MANAGEMENT ---
class StableSMAStrategy(bt.Strategy):
    params = (
        ('signal_sma_period', 14), #14
        ('sma_momentum_period', 50),
        ('sma_long_term_period', 100),
        ('sma_short_term_period', 11), #11
        ('min_angle_for_entry', 65.0), #65
        ('max_abs_divergence_entry', 10.0),
        ('risk_percent', 0.01),
        ('stop_loss_pips', 10),
        ('pip_value', 0.0001),
        ('cooldown_period', 5),
    )

    def __init__(self):
        # Indicators
        self.prediction = self.data.close
        self.smoothed_prediction = bt.indicators.SMA(self.data.close, period=self.p.signal_sma_period)
        self.sma_short_term = bt.indicators.SMA(self.data.close, period=self.p.sma_short_term_period)
        self.sma_long_term = bt.indicators.SMA(self.data.close, period=self.p.sma_long_term_period)
        self.sma_momentum = bt.indicators.SMA(self.data.close, period=self.p.sma_momentum_period)
        self.smooth_cross_momentum = bt.indicators.CrossOver(self.smoothed_prediction, self.sma_momentum)
        self.angle_prediction = AngleIndicator(self.smoothed_prediction, angle_lookback=self.p.signal_sma_period)
        self.angle_price = AngleIndicator(self.sma_short_term, angle_lookback=self.p.sma_short_term_period)
        
        # State Management
        self.cooldown_counter = 0 
        self.current_order = None
        
        # --- CORRECTED: Manual PnL and Trade Tracking ---
        self.total_gross_profit = 0.0
        self.total_gross_loss = 0.0
        self.num_closed_trades = 0
        self.num_won_trades = 0
        self.num_lost_trades = 0
        self.total_trades_opened = 0 # This was missing

    def calculate_order_size(self, stop_price):
        risked_value = self.broker.get_value() * self.p.risk_percent
        entry_price = self.data.close[0]
        pnl_per_unit = abs(entry_price - stop_price)
        if pnl_per_unit == 0: return 0
        position_size = risked_value / pnl_per_unit
        return math.floor(position_size)

    def next(self):
        if self.cooldown_counter > 0:
            self.cooldown_counter -= 1
            return
        if self.current_order:
            return
        if self.position:
            if self.smooth_cross_momentum[0] < 0:
                print(f"--- EXIT SIGNAL @ {self.data.datetime.date(0)}: Closing position. ---")
                self.current_order = self.close() 
            return
        if np.isnan(self.angle_prediction[0]) or np.isnan(self.angle_price[0]):
            return
        abs_divergence = abs(self.angle_prediction[0] - self.angle_price[0])
        is_bullish_filter = (self.sma_long_term[0] < self.prediction[0] and self.sma_momentum[0] < self.prediction[0])
        is_strong_momentum = self.smoothed_prediction[0] > self.smoothed_prediction[-1]
        is_crossover_signal = self.smooth_cross_momentum[0] > 0
        is_steep_angle = self.angle_prediction[0] > self.p.min_angle_for_entry
        is_coherent_signal = abs_divergence < self.p.max_abs_divergence_entry
        if is_bullish_filter and is_strong_momentum and is_crossover_signal and is_steep_angle and is_coherent_signal:
            stop_price = self.data.close[0] - (self.p.stop_loss_pips * self.p.pip_value)
            size = self.calculate_order_size(stop_price)
            if size <= 0: return
            print(f"--- ATTEMPTING BUY @ {self.data.datetime.date(0)} (Size: {size}, Stop: {stop_price:.5f}) ---")
            brackets = self.buy_bracket(
                size=size,
                stopprice=stop_price,
                exectype=bt.Order.Market, # Use market order for entry
                limitprice=self.data.close[0] * 2.0, # A very high take-profit to not interfere
            )
            self.current_order = brackets[0]

    def notify_order(self, order):
        if order.ref == getattr(self.current_order, 'ref', -1) and order.status in [order.Completed, order.Canceled, order.Rejected, order.Margin]:
            self.current_order = None
        if order.status in [order.Completed]:
            if order.isbuy():
                # --- CORRECTED: Increment opened trades counter ---
                self.total_trades_opened += 1
                print(f"BUY EXECUTED @ Price: {order.executed.price:.5f}, Size: {order.executed.size}")
            elif order.issell():
                print(f"SELL EXECUTED @ Price: {order.executed.price:.5f}, Size: {order.executed.size}")
                self.cooldown_counter = self.p.cooldown_period
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f"--- ORDER FAILED/CANCELED: {order.getstatusname()} for {order.size} @ {order.created.price:.5f} ---")
            self.current_order = None

    def notify_trade(self, trade):
        if trade.isclosed:
            self.num_closed_trades += 1
            pnl = trade.pnlcomm
            if pnl > 0:
                self.num_won_trades += 1
                self.total_gross_profit += pnl
            else:
                self.num_lost_trades += 1
                self.total_gross_loss += abs(pnl)
            print(f"TRADE CLOSED: PnL: {pnl:.2f}, Gross Profit: {self.total_gross_profit:.2f}, Gross Loss: {self.total_gross_loss:.2f}")

    def stop(self):
        print("\n--- Strategy execution finished. Final report will be generated. ---")

# --- Cerebro Execution (Unchanged) ---
if __name__ == '__main__':
    cerebro = bt.Cerebro(runonce=False)
    cerebro.addstrategy(StableSMAStrategy)
    
    data = bt.feeds.GenericCSVData(
        dataname=str(DATA_PATH), dtformat=('%Y%m%d'), tmformat=('%H:%M:%S'),
        datetime=0, time=1, open=2, high=3, low=4, close=5, volume=6,
        timeframe=bt.TimeFrame.Minutes, compression=5)
    cerebro.adddata(data)
    
    start_cash = 100000.0
    cerebro.broker.setcash(start_cash)
    cerebro.broker.setcommission(leverage=30.0)

    print("--- Running Backtest with Stable SMA Strategy ---")
    
    results = cerebro.run()
    
    # --- FINAL, ROBUST REPORTING BLOCK ---
    print("\n" + "="*50)
    print("--- FINAL BACKTEST REPORT ---")
    
    final_value = cerebro.broker.getvalue()
    print(f"Starting Portfolio Value: {start_cash:.2f}")
    print(f"Final Portfolio Value:    {final_value:.2f}")
    
    the_strategy = results[0] 
    
    # --- CORRECTED: Use the explicitly tracked variables ---
    total_trades_opened = the_strategy.total_trades_opened
    total_closed_trades = the_strategy.num_closed_trades
    won_trades = the_strategy.num_won_trades
    lost_trades = the_strategy.num_lost_trades
    total_gross_profit = the_strategy.total_gross_profit
    total_gross_loss = the_strategy.total_gross_loss

    print(f"\nTotal Trades Opened (Entries): {total_trades_opened}")
    
    if total_closed_trades > 0:
        print(f"Total Closed Trades: {total_closed_trades} (Won: {won_trades}, Lost: {lost_trades})")
        
        if total_gross_loss > 0:
            profit_factor = total_gross_profit / total_gross_loss
            print(f"Profit Factor: {profit_factor:.2f}")
        else:
            print("Profit Factor: Inf (No losing trades)")
    else:
        print("Profit Factor: N/A (No trades were closed)")

    print("="*50 + "\n")
    
    print("Generating Plot...")
    cerebro.plot(style='line', volume=False)