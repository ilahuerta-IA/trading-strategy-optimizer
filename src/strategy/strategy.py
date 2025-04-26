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
    )

    def __init__(self):
        # Assign indicators to self attributes
        self.ma1 = self.p.ma(self.data0, period=self.p.pd1, subplot=True)
        # Assign the second MA also to self, using self.ma1 for plotmaster
        self.ma2 = self.p.ma(self.data1, period=self.p.pd2, plotmaster=self.ma1)
        # Assign PearsonR to self, using its own period parameter
        self.correlation = PearsonR(self.data0, self.data1, period=self.p.corr_period)
    
    # Add a minimal next method to make the strategy complete
    def next(self):
        # Strategy logic would go here (e.g., check for crossovers)
        # For now, just pass to allow running and plotting
        # You can print values here for debugging if needed:
        # if len(self.ma1) > 0 and len(self.ma2) > 0 and len(self.correlation) > 0:
        #    print(f"Date: {self.datas[0].datetime.date(0)}, MA1: {self.ma1[0]:.2f}, MA2: {self.ma2[0]:.2f}, Corr: {self.correlation[0]:.2f}")
        pass


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
        dtformat=('%Y-%m-%d %H:%M:%S%z'), # CSV has timezone like '2023-10-27 15:55:00-04:00'
        datetime=0,  # Column index for datetime
        time=-1,     # Time is part of datetime column
        high=2,      # Column index for High
        low=3,       # Column index for Low
        open=1,      # Column index for Open
        close=4,     # Column index for Close
        volume=5,    # Column index for Volume
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
    except Exception as e:
        print(f"FATAL ERROR loading data1 from {args.data1}: {e}")
        print("Check file path, file format, and CSV parameters in the script.")
        return # Exit if loading fails
    # --- End Load Data Feeds ---

    # --- Broker ---
    print(f"Parsing broker args: '{args.broker}'")
    broker_kwargs = parse_kwargs_str(args.broker)
    print(f"Applying broker kwargs: {broker_kwargs}")
    cerebro.broker = bt.brokers.BackBroker(**broker_kwargs)

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

    # --- Observer ---
    # Calculate 5-day rolling log returns (based on daily closes)
    print("Adding LogReturns2 Observer (Daily, 5-day compression)")
    cerebro.addobserver(bt.observers.LogReturns2,
                    timeframe=bt.TimeFrame.Days,
                    compression=5) # Example: 5-day rolling period

    # --- Execute ---
    print(f"Parsing cerebro args: '{args.cerebro}'")
    run_kwargs = parse_kwargs_str(args.cerebro)
    print(f"Applying cerebro.run kwargs: {run_kwargs}")
    print("Running Cerebro...")
    cerebro.run(**run_kwargs)
    print("Cerebro run finished.")

    # --- Plot ---
    if args.plot is not None:
        print(f"Parsing plot args: '{args.plot}'")
        plot_kwargs = parse_kwargs_str(args.plot)
        # Set default plot style to candlestick if not specified by user
        plot_kwargs.setdefault('style', 'candlestick')
        print(f"Applying plot kwargs: {plot_kwargs}")
        print("Generating plot...")
        try:
             cerebro.plot(**plot_kwargs)
             print("Plot generation finished.")
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

    parser.add_argument('--broker', required=False, default='cash=10000,commission=0.001', # Example default
                        metavar='kwargs', help='kwargs for BackBroker (e.g., cash=10000)')

    parser.add_argument('--sizer', required=False, default='stake=10', # Example default
                        metavar='kwargs', help='kwargs for FixedSize sizer (e.g., stake=100)')

    parser.add_argument('--strat', required=False, default='',
                        metavar='kwargs', help='kwargs for strategy (e.g., pd1=15,pd2=45)')

    # Adjusted plot argument check in runstrat, const='{}' is fine
    parser.add_argument('--plot', required=False, default=None, # Default None means "don't plot"
                        nargs='?', const='{}', # If flag exists, value is '{}'
                        metavar='kwargs', help='Enable plotting and pass plot kwargs (e.g., style=line)')

    return parser.parse_args(pargs)


if __name__ == '__main__':
    runstrat()