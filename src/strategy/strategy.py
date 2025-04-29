#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

# Reference
# Backtrader in github by Daniel Rodriguez

import argparse
import datetime
import numpy as np

from pathlib import Path

import scipy.stats

import backtrader as bt

import matplotlib.pyplot as plt



# --- Helper Function to Safely Parse Kwargs Strings ---
def parse_kwargs_str(kwargs_str):
    """
    Safely parses a string like "key1=value1,key2=value2" into a dictionary.
    Attempts to convert values to numbers (int/float) if possible.
    """
    parsed_kwargs = {}
    if not kwargs_str:
        return parsed_kwargs
    
    # Handle the special case from argparse where --plot with no args becomes '{}'
    if kwargs_str == '{}':
        return parsed_kwargs # Return empty dict for plotting defaults

    pairs = kwargs_str.split(',')
    for pair in pairs:
        pair = pair.strip()
        if not pair:
            continue
        try:
            key, value = pair.split('=', 1)
            key = key.strip()
            value = value.strip()

            # Attempt to convert value to numeric if possible
            try:
                if '.' in value:
                    parsed_kwargs[key] = float(value)
                else:
                    parsed_kwargs[key] = int(value)
            except ValueError:
                # Keep as string if conversion fails (handle simple cases)
                # More robust parsing might be needed for quoted strings etc.
                 # Basic check for boolean True/False strings
                if value.lower() == 'true':
                    parsed_kwargs[key] = True
                elif value.lower() == 'false':
                    parsed_kwargs[key] = False
                else:
                    # Remove potential quotes if they exist at start/end
                    if (value.startswith("'") and value.endswith("'")) or \
                       (value.startswith('"') and value.endswith('"')):
                        parsed_kwargs[key] = value[1:-1]
                    else:
                        parsed_kwargs[key] = value

        except ValueError:
            print(f"Warning: Skipping malformed kwarg pair: {pair}")
            continue # Skip pairs that don't contain '='
    return parsed_kwargs
# --- End Helper Function ---

class PearsonR(bt.ind.PeriodN):
    _mindatas = 2  # hint to the platform

    lines = ('correlation',)
    params = (('period', 20),)

    def next(self):
        # Get the data slices for the period
        data0_slice = self.data0.get(size=self.p.period)
        data1_slice = self.data1.get(size=self.p.period)

        # Ensure we have enough data points in both slices
        if len(data0_slice) < self.p.period or len(data1_slice) < self.p.period:
             self.lines.correlation[0] = float('nan') # Not enough data yet
             return
        
        # Check for constant series (std dev = 0) which cause pearsonr errors
        if np.std(data0_slice) == 0 or np.std(data1_slice) == 0:
             self.lines.correlation[0] = 0.0 if np.std(data0_slice) == 0 and np.std(data1_slice) == 0 else float('nan') # Correlation is NaN if one is constant, 0 if both are constant? (Check definition or set NaN)
             return

        try:
            c, p = scipy.stats.pearsonr(data0_slice, data1_slice)
            self.lines.correlation[0] = c
        except ValueError as e:
             print(f"Error calculating Pearson R: {e}. Data0: {data0_slice}, Data1: {data1_slice}")
             self.lines.correlation[0] = float('nan') # Handle potential errors from pearsonr


class MACrossOver(bt.Strategy):
    params = (
        ('ma', bt.ind.MovAv.SMA),
        ('pd1', 20),
        ('pd2', 20),
        # Add period for PearsonR if you want it configurable
        ('corr_period', 20),
        # --- CCI Indicator ---
        ('cci_period', 20),  # Period for CCI
        ('atr_period', 14),  # Period for ATR
        ('atr_multiplier', 1.5)
    )

    def __init__(self):
        # Keep references to datas for convenience
        self.spy = self.data0
        self.gld = self.data1

         # SPY Indicators
        self.sma_spy = self.p.ma(self.spy, period=self.p.pd1, plotmaster=self.spy)
        self.cci_spy = bt.ind.CommodityChannelIndex(self.spy, period=self.p.cci_period)
        self.atr_spy = bt.ind.AverageTrueRange(self.spy, period=self.p.atr_period, plotmaster=self.spy) # Keep ATR if needed later

        # GLD Indicators
        self.sma_gld = self.p.ma(self.gld, period=self.p.pd2, plotmaster=self.spy) # Plot GLD SMA on SPY's chart
        self.cci_gld = bt.ind.CommodityChannelIndex(self.gld, period=self.p.cci_period) # CCI for GLD

        # Cross-Asset Indicators
        self.correlation = PearsonR(self.spy, self.gld, period=self.p.corr_period)

        # Optional: Add levels to CCI plots for visual reference
        self.cci_spy.plotinfo.plotyhlines = [-20, 20, 70] # Add lines to SPY CCI plot
        self.cci_gld.plotinfo.plotyhlines = [-20, 20, 70] # Add lines to GLD CCI plot

        # Calculate minimum periods needed + a small buffer
        self.min_period = max(self.p.pd1, self.p.pd2, self.p.corr_period, self.p.cci_period, self.p.atr_period)
        self.warmup_bars = self.min_period + 5 # e.g., wait 5 bars after indicators are ready

        # To keep track of pending orders (optional but good practice)
        self.order = None

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.datetime(0) # Use system datetime
        print(f'{dt.isoformat()} | {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            self.bar_executed = len(self) # Bar number when order was executed

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order Canceled/Margin/Rejected: Status {order.getstatusname()}')

        # Write down: no pending order
        self.order = None   
    
    # Add a minimal next method to make the strategy complete
    def next(self):
         # --- Use datetime from data0 for consistency in logs ---
        current_dt = self.datas[0].datetime.datetime(0)
        
         # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            self.log(f'Pending order detected, skipping bar {len(self)}')
            return
        
        if len(self) < self.warmup_bars:
            return # Wait for all indicators and buffer period
        
        # --- Explicitly check position sizes for BOTH assets ---
        spy_position_size = self.getposition(self.spy).size
        gld_position_size = self.getposition(self.gld).size
        is_position_open = spy_position_size != 0 or gld_position_size != 0

        # --- Entry Logic ---
        if not is_position_open:
            # --- Potential SPY Long Entry ---
            spy_cci_cond = self.cci_spy[0] > 70
            spy_sma_cond = self.sma_spy[0] > self.sma_spy[-1]
            gld_sma_cond = self.sma_gld[0] < self.sma_gld[-1] # GLD SMA falling
            gld_cci_cond = self.cci_gld[0] < -20

            if spy_cci_cond and spy_sma_cond and gld_sma_cond and gld_cci_cond:
                self.log(f'SPY LONG ENTRY SIGNAL: CCI_SPY={self.cci_spy[0]:.2f}, SMA_SPY Rising, SMA_GLD Falling, CCI_GLD={self.cci_gld[0]:.2f}')
                # --- Place Buy Order ---
                self.order = self.buy(data=self.spy)
                # Set stop price attribute *if* using a sizer that needs it
                # self.calculated_stop_price = potential_spy_stop

            # --- Potential GLD Long Entry ---
            # Only check if SPY entry didn't trigger and still no position
            else: # No SPY signal found, check GLD
                gld_cci_entry_cond = self.cci_gld[0] > 100
                gld_sma_rising_cond = self.sma_gld[0] > self.sma_gld[-1]
                spy_sma_falling_cond = self.sma_spy[0] < self.sma_spy[-1] # SPY SMA falling
                spy_cci_cond = self.cci_spy[0] < 0

                if gld_cci_entry_cond and gld_sma_rising_cond and spy_sma_falling_cond and spy_cci_cond:
                    self.log(f'GLD LONG ENTRY SIGNAL: CCI_GLD={self.cci_gld[0]:.2f}, SMA_GLD Rising, SMA_SPY Falling, CCI_SPY={self.cci_spy[0]:.2f}')
                    # --- Place Buy Order ---
                    self.order = self.buy(data=self.gld)
                    
        # --- Exit Logic ---
        else: # is_position_open is True
            # --- Check SPY Exit ---
            if spy_position_size != 0: # Check if specifically holding SPY
                #self.log(f'Position Check: In SPY. Checking exit. CCI_SPY={self.cci_spy[0]:.2f}') # Debug Log
                if self.cci_spy[0] < 20:
                    #self.log(f'SPY LONG EXIT SIGNAL: CCI_SPY={self.cci_spy[0]:.2f} < 20')
                    self.order = self.close(data=self.spy) # Close SPY position

            # --- Check GLD Exit ---
            elif gld_position_size != 0: # Check if specifically holding GLD
                #self.log(f'Position Check: In GLD. Checking exit. CCI_GLD={self.cci_gld[0]:.2f}') # Debug Log
                if self.cci_gld[0] < 20:
                    #self.log(f'GLD LONG EXIT SIGNAL: CCI_GLD={self.cci_gld[0]:.2f} < 20')
                    self.order = self.close(data=self.gld) # Close GLD positionn


def runstrat(args=None):
    args = parse_args(args)

    cerebro = bt.Cerebro()

    # Data feed kwargs
    data_kwargs = dict()

    # Parse from/to-date
    dtfmt, tmfmt = '%Y-%m-%d', 'T%H:%M:%S'
    for arg_name in ['fromdate', 'todate']:
        date_str = getattr(args, arg_name)
        if date_str: # Only process if date string is provided
             try:
                 # Check if time component is likely present
                 if 'T' in date_str or ':' in date_str:
                      # More robust check for combined date/time format
                      if 'T' in date_str:
                           strpfmt = dtfmt + tmfmt
                      elif len(date_str) > 10: # Guessing time is included if longer than YYYY-MM-DD
                           # Assuming space separator if T is missing
                           strpfmt = f"{dtfmt} %H:%M:%S" # Adjust format if needed
                      else: # Assume date only
                           strpfmt = dtfmt
                 else: # Date only
                      strpfmt = dtfmt

                 data_kwargs[arg_name] = datetime.datetime.strptime(date_str, strpfmt)
                 print(f"Parsed {arg_name}: {data_kwargs[arg_name]} using format {strpfmt}")
             except ValueError as e:
                  print(f"Warning: Error parsing date string '{date_str}' for {arg_name}: {e}")
                  print(f"         '{arg_name}' filter will not be applied.")


    # --- Select CSV Feed ---
    # Force using GenericCSVData
    CSVDataFeed = bt.feeds.GenericCSVData
    print(f"Using CSV data feed: {CSVDataFeed}")
    # --- End Select CSV Feed ---


    # --- CSV Data Feed Parameters ---
    # These parameters MUST match the structure of your CSV files
    # Inspect your SPY_5m_1Mon.csv and GLD_5m_1Mon.csv headers
    csv_params = dict(
        dataname=None, # Will be set per data feed below
        nullvalue=float('NaN'), # How NaNs are represented
        headers=True,    # Indicate the CSV has a header row
        skiprows=1,      # Skip the header row when reading data lines
        dtformat=('%Y-%m-%d %H:%M:%S%z'), # CSV has timezone like '2023-10-27 15:55:00-04:00'
        datetime=0,      # Use index 0 for Datetime column
        time=-1,         # Keep -1 as time is part of datetime
        high=2,          # Use index 2 for High column
        low=3,           # Use index 3 for Low column
        open=1,          # Use index 1 for Open column
        close=4,         # Use index 4 for Close column
        volume=5,        # Use index 5 for Volume column
        openinterest=-1, # No Open Interest column
        timeframe=bt.TimeFrame.Minutes, # Data timeframe
        compression=5                  # Number of minutes
    )
    # --- End CSV Data Feed Parameters ---

    # --- Load Data Feeds ---
    print(f"Attempting to load data0 from: {args.data0}")
    feed_params_0 = csv_params.copy()
    feed_params_0['dataname'] = args.data0
    try:
        data0 = CSVDataFeed(**feed_params_0, **data_kwargs) # Combine CSV params and date filters
        data0.plotinfo.plotvolume = False # Don´t show volumen
        data0.plotinfo.plotvolsubplot = False
        print(f"Adding data0 (5 min) to Cerebro. Date Filters: {data_kwargs}")
        cerebro.adddata(data0) # Use adddata, NO RESAMPLING
    except Exception as e:
        print(f"FATAL ERROR loading data0 from {args.data0}: {e}")
        print("Check file path, file format, and CSV parameters in the script.")
        return # Exit if loading fails

    print(f"Attempting to load data1 from: {args.data1}")
    feed_params_1 = csv_params.copy()
    feed_params_1['dataname'] = args.data1
    try:
        data1 = CSVDataFeed(**feed_params_1, **data_kwargs) # Combine CSV params and date filters
        print(f"Adding data1 (5 min) to Cerebro. Date Filters: {data_kwargs}")
        cerebro.adddata(data1) # Use adddata, NO RESAMPLING
        data1.plotinfo.plotmaster = data0 # Plot prices on the same chart
        data1.plotinfo.plotvolume = False # Don´t show volumen
        data1.plotinfo.plotvolsubplot = False
    except Exception as e:
        print(f"FATAL ERROR loading data1 from {args.data1}: {e}")
        print("Check file path, file format, and CSV parameters in the script.")
        return # Exit if loading fails
    # --- End Load Data Feeds ---

    # --- Broker ---
    print(f"Parsing broker args: '{args.broker}'")
    broker_kwargs = parse_kwargs_str(args.broker)
    broker_init_kwargs = broker_kwargs.copy()
    commission_config = {}
    if 'commission' in broker_init_kwargs:
        # Remove commission from the dictionary used for initial broker creation
        commission_value = broker_init_kwargs.pop('commission')
        # Store how we want to apply it later (e.g., as percentage)
        commission_config['commission'] = commission_value
        commission_config['percabs'] = True # Assume 0.001 means 0.1%

    print(f"Initial Broker kwargs (commission removed if present): {broker_init_kwargs}")
    cerebro.broker = bt.brokers.BackBroker(**broker_init_kwargs)

    if commission_config:
        commission_value = commission_config['commission']
        commission_perc = commission_value * 100
        print(f"Setting commission explicitly via setcommission: {commission_perc:.3f}%")
        cerebro.broker.setcommission(**commission_config)
    else:
        print("No commission specified or parsed for setcommission.")

    # --- Sizer ---
    print(f"Parsing sizer args: '{args.sizer}'")
    sizer_kwargs = parse_kwargs_str(args.sizer)
    print(f"Applying sizer kwargs: {sizer_kwargs}")
    cerebro.addsizer(bt.sizers.FixedSize, **sizer_kwargs) # Assuming FixedSize is always desired

    # --- Strategy ---
    print(f"Parsing strategy args: '{args.strat}'")
    strat_kwargs = parse_kwargs_str(args.strat)
    print(f"Applying strategy kwargs: {strat_kwargs}")
    cerebro.addstrategy(MACrossOver, **strat_kwargs)

    # --- ADD ANALYZERS ---
    print("Adding Analyzers: TradeAnalyzer, DrawDown")
    # Standard Trade Analyzer
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='tradeanalyzer')
    # Drawdown Analyzer
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    # --- END ANALYZERS ---

    # --- Observer ---
    print("Adding Value Observer")
    cerebro.addobserver(bt.observers.Value)
    # Calculate 5-day rolling log returns (based on daily closes)
    # print("Adding LogReturns2 Observer (Daily, 5-day compression)")
    # cerebro.addobserver(bt.observers.LogReturns2,
                    #timeframe=bt.TimeFrame.Days,
                    #compression=5) # Example: 5-day rolling period

    # --- Execute ---
    print(f"Parsing cerebro args: '{args.cerebro}'")
    run_kwargs = parse_kwargs_str(args.cerebro)
    print(f"Applying cerebro.run kwargs: {run_kwargs}")
    print("Running Cerebro...")
    # Store the result of run() to access analyzers
    results = cerebro.run(**run_kwargs)
    print("Cerebro run finished.")

    # --- Get Strategy Instance (assuming only one) ---
    strat_instance = results[0]

    # --- Process Analyzer Results ---
    print("\n--- Backtest Analysis Results ---")
    drawdown_analysis = None
    trade_analysis = None

    # --- Extract Drawdown ---
    if hasattr(strat_instance.analyzers, 'drawdown'):
        try:
            drawdown_analysis = strat_instance.analyzers.drawdown.get_analysis()
            print(f"\nMax Drawdown:       {drawdown_analysis.max.drawdown:.2f}%")
            print(f"Max Drawdown ($):   {drawdown_analysis.max.moneydown:.2f}")
        except Exception as e:
            print(f"Error processing DrawDown Analyzer: {e}")
    else:
        print("\nDrawDown analyzer results not found.")

    # --- Extract and Print Trade Analysis ---
    if hasattr(strat_instance.analyzers, 'tradeanalyzer'):
        try:
            trade_analysis = strat_instance.analyzers.tradeanalyzer.get_analysis()

            print("\n--- Trade Analysis ---")
            if trade_analysis.total.total > 0: # Check if any trades were analyzed
                print(f"Total Closed Trades:{trade_analysis.total.closed:6d}")
                print(f"Total Open Trades:  {trade_analysis.total.open:6d}")
                print("")
                print(f"Winning Trades:     {trade_analysis.won.total:6d}")
                print(f"Losing Trades:      {trade_analysis.lost.total:6d}")
                print("")

                # PnL Stats
                print(f"Total Net PnL:    ${trade_analysis.pnl.net.total:9.2f}")
                print(f"Avg Net PnL:      ${trade_analysis.pnl.net.average:9.2f}")
                print("")
                print(f"Total Winning PnL:${trade_analysis.won.pnl.total:9.2f}")
                print(f"Avg Winning PnL:  ${trade_analysis.won.pnl.average:9.2f}")
                print(f"Max Winning PnL:  ${trade_analysis.won.pnl.max:9.2f}")
                print("")
                print(f"Total Losing PnL: ${trade_analysis.lost.pnl.total:9.2f}")
                print(f"Avg Losing PnL:   ${trade_analysis.lost.pnl.average:9.2f}")
                print(f"Max Losing PnL:   ${trade_analysis.lost.pnl.max:9.2f}")
                print("")

                # Profit Factor
                if trade_analysis.lost.total > 0 and trade_analysis.lost.pnl.total != 0:
                     profit_factor = abs(trade_analysis.won.pnl.total / trade_analysis.lost.pnl.total)
                     print(f"Profit Factor:      {profit_factor:9.2f}")
                else:
                     print(f"Profit Factor:           N/A (No Losses)")

                # SQN (System Quality Number) - Requires Returns Analyzer, skip for now or use simplified approx if needed
                # print(f"SQN:              {trade_analysis.sqn:9.2f}") # Might be None without Returns

                # --- Print PnL for Each Closed Trade ---
                print("\n--- PnL per Closed Trade ---")
                if 'trades' in trade_analysis and isinstance(trade_analysis.trades, list) and len(trade_analysis.trades) > 0:
                    # The 'trades' key holds a list of dicts, each dict has 'pnl', 'pnlcomm'
                    trade_num = 0
                    for trade_info in trade_analysis.trades:
                        # Need to access underlying dict items
                        if isinstance(trade_info, dict) and 'pnl' in trade_info and 'pnlcomm' in trade_info:
                             trade_num += 1
                             pnl = trade_info['pnl']        # PnL before commission
                             pnlcomm = trade_info['pnlcomm'] # PnL after commission
                             status = "WIN" if pnlcomm > 0 else "LOSS" if pnlcomm < 0 else "FLAT"
                             # We don't easily get the asset name here without more complex analysis
                             print(f"Trade #{trade_num:3d}: Status: {status:4s}, Net PnL: ${pnlcomm:8.2f} (Gross PnL: ${pnl:8.2f})")
                        else:
                             print(f"Warning: Unexpected format for trade_info: {trade_info}")
                else:
                    print("No individual trade PnL data available in TradeAnalyzer output.")
                # --- End PnL per Trade ---

            else:
                 print("No trades were executed or analyzed.")

        except Exception as e:
            print(f"Error processing Trade Analyzer: {e}")
            import traceback
            traceback.print_exc() # Print full traceback for debugging analyzer errors

    else:
        print("TradeAnalyzer results not found.")

    # --- End Process Analyzer Results ---
    
    # --- Plot ---
    if args.plot is not None:
        print(f"Parsing plot args: '{args.plot}'")
        plot_kwargs = parse_kwargs_str(args.plot)
        # Set default plot style to candlestick if not specified by user
        #plot_kwargs.setdefault('style', 'candlestick')
        plot_kwargs.setdefault('style', 'line')      # Default style = line
        plot_kwargs.setdefault('figsize', (20, 10))  # Default figsize (NOTE: This is a tuple!)
        print(f"Applying plot kwargs: {plot_kwargs}")
        print("Generating plot...")
        try:
             cerebro.plot(**plot_kwargs)
             print("Plot generation finished.")
             plt.show()
        except Exception as e_plot:
             print(f"ERROR generating plot: {e_plot}")
             print("Plotting might require 'matplotlib'. Install with: pip install matplotlib")

    else:
        print("Plotting not requested.")

def parse_args(pargs=None):

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            'Offline CSV Strategy Runner (Gold vs SP500 example)')
    )

    data_base_path = Path(r"C:\Iván\Yosoybuendesarrollador\Python\Portafolio\quant_bot_project\data")

    default_data0_path = str(data_base_path / "SPY_5m_1Mon.csv") # Use str() for argparse
    default_data1_path = str(data_base_path / "GLD_5m_1Mon.csv") # Use str() for argparse

    parser.add_argument('--data0', required=False,
                        default=default_data0_path, # Default to SPY CSV path
                        metavar='FILEPATH', help='Path to CSV data file for data0')

    parser.add_argument('--data1', required=False,
                        default=default_data1_path, # Default to GLD CSV path
                        metavar='FILEPATH', help='Path to CSV data file for data1')

    # Defaults for dates
    parser.add_argument('--fromdate', required=False, default=None,
                        help='Start Date[time] in YYYY-MM-DD[THH:MM:SS] format')

    parser.add_argument('--todate', required=False, default=None,
                        help='End Date[time] in YYYY-MM-DD[THH:MM:SS] format')

    # Keep kwargs arguments
    parser.add_argument('--cerebro', required=False, default='',
                        metavar='kwargs', help='kwargs for cerebro.run (e.g., stdstats=False)')

    parser.add_argument('--broker', required=False, default='cash=100000,commission=0.001', # Example default
                        metavar='kwargs', help='kwargs for BackBroker (e.g., cash=10000)')

    parser.add_argument('--sizer', required=False, default='stake=5', # Example default
                        metavar='kwargs', help='kwargs for FixedSize sizer (e.g., stake=100)')

    parser.add_argument('--strat', required=False, default='',
                        metavar='kwargs', help='kwargs for strategy (e.g., pd1=15,pd2=45)')

    # Adjusted plot argument check in runstrat, const='{}' is fine
    parser.add_argument('--plot', required=False, default={}, # Default None means "don't plot"
                        nargs='?', const='{}', # If flag exists, value is '{}'
                        metavar='kwargs', help='Enable plotting and pass plot kwargs (e.g., style=line)')

    return parser.parse_args(pargs)


if __name__ == '__main__':
    runstrat()