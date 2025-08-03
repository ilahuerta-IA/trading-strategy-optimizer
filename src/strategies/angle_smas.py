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

# --- GLOBAL PATH CONFIGURATION ---
try:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    DATA_PATH = PROJECT_ROOT / 'data' /  'EURUSD_5m_2Yea.csv'#'EURUSD_5m_2Mon.csv'
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

# --- MAIN TRADING STRATEGY (Unchanged) ---
class StableSMAStrategy(bt.Strategy):
    params = (
        ('signal_sma_period', 7),
        ('sma_momentum_period', 50),
        ('sma_long_term_period', 100),
        ('sma_short_term_period', 5),
        ('min_angle_for_entry', 55.0),
        ('max_abs_divergence_entry', 10.0),
        ('position_size', 10000),
    )

    def __init__(self):
        self.prediction = self.data.close
        self.smoothed_prediction = bt.indicators.SMA(
            self.data.close, period=self.p.signal_sma_period
        )
        self.sma_short_term = bt.indicators.SMA(self.data.close, period=self.p.sma_short_term_period)
        self.sma_long_term = bt.indicators.SMA(self.data.close, period=self.p.sma_long_term_period)
        self.sma_momentum = bt.indicators.SMA(self.data.close, period=self.p.sma_momentum_period)
        self.smooth_cross_momentum = bt.indicators.CrossOver(self.smoothed_prediction, self.sma_momentum)
        self.angle_prediction = AngleIndicator(self.smoothed_prediction, angle_lookback=self.p.signal_sma_period)
        self.angle_price = AngleIndicator(self.sma_short_term, angle_lookback=self.p.sma_short_term_period)

    def next(self):
        if np.isnan(self.angle_prediction[0]) or np.isnan(self.angle_price[0]):
            return
            
        abs_divergence = abs(self.angle_prediction[0] - self.angle_price[0])

        if self.position:
            if self.smooth_cross_momentum[0] < 0:
                self.close()
            return
            
        is_bullish_filter = (self.sma_long_term[0] < self.prediction[0] and self.sma_momentum[0] < self.prediction[0])
        is_strong_momentum = self.smoothed_prediction[0] > self.smoothed_prediction[-1]
        is_crossover_signal = self.smooth_cross_momentum[0] > 0
        is_steep_angle = self.angle_prediction[0] > self.p.min_angle_for_entry
        is_coherent_signal = abs_divergence < self.p.max_abs_divergence_entry
        
        if is_bullish_filter and is_strong_momentum and is_crossover_signal and is_steep_angle and is_coherent_signal:
            print(f"--- BUY SIGNAL @ {self.data.datetime.date(0)} (Angle: {self.angle_prediction[0]:.2f}°) ---")
            self.buy(size=self.p.position_size)
    
    def stop(self):
        print("\n--- Strategy execution finished. Final report will be generated. ---")

# --- Cerebro Execution ---
if __name__ == '__main__':
    cerebro = bt.Cerebro(runonce=False)
    
    cerebro.addstrategy(StableSMAStrategy)
    
    # --- THE DEFINITIVE FIX: RESTORED ORIGINAL DATA LOADER CONFIGURATION ---
    data = bt.feeds.GenericCSVData(
        dataname=str(DATA_PATH),
        dtformat=('%Y%m%d'),          # Format for the date column
        tmformat=('%H:%M:%S'),          # Format for the time column
        datetime=0,                     # Date is in Column 0
        time=1,                         # Time is in Column 1
        open=2,                         # Open is in Column 2
        high=3,
        low=4,
        close=5,
        volume=6,
        timeframe=bt.TimeFrame.Minutes,
        compression=5)
    
    cerebro.adddata(data)
    
    start_cash = 100000.0
    cerebro.broker.setcash(start_cash)
    
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='tradeanalyzer')

    print("--- Running Backtest with Stable SMA Strategy ---")
    
    results = cerebro.run()
    
    # --- Final Reporting Block (Unchanged, uses correct logic) ---
    print("\n" + "="*50)
    print("--- FINAL BACKTEST REPORT ---")
    
    final_value = cerebro.broker.getvalue()
    print(f"Starting Portfolio Value: {start_cash:.2f}")
    print(f"Final Portfolio Value:    {final_value:.2f}")
    
    the_strategy = results[0] 
    
    try:
        trade_analysis = the_strategy.analyzers.tradeanalyzer.get_analysis()
        
        total_trades = trade_analysis.total.get('total', 0)
        print(f"\nTotal Trades Opened (Entries): {total_trades}")

        total_closed = trade_analysis.total.get('closed', 0)
        if total_closed > 0:
            total_won_pnl = trade_analysis.get('won', {}).get('pnl', {}).get('total', 0.0)
            total_lost_pnl = abs(trade_analysis.get('lost', {}).get('pnl', {}).get('total', 0.0))
            
            if total_lost_pnl > 0:
                profit_factor = total_won_pnl / total_lost_pnl
                print(f"Profit Factor (on {total_closed} closed trades): {profit_factor:.2f}")
            else:
                print("Profit Factor: Inf (No losing trades)")
        else:
            print("Profit Factor: N/A (No trades were closed)")

    except (KeyError, AttributeError) as e:
        print(f"\nCould not generate trade analysis. Error: {e}")

    print("="*50 + "\n")
    
    print("Generating Plot...")
    cerebro.plot(style='line')