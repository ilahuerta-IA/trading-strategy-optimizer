# File: scripts/test_m1_data_loading_plotly.py

import sys
import os
import backtrader as bt
import pandas as pd
import plotly.graph_objects as go # Import Plotly
from plotly.subplots import make_subplots # Import make_subplots
import webbrowser # Import webbrowser to open the HTML file

# --- Add project root to Python path ---
# This allows importing modules from the 'src' directory (if needed)
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ---------------------------------------

# --- Configuration ---
datapath_base = os.path.join(os.path.dirname(__file__), '..', 'data')

# !!! USE SHORT FILES FOR QUICK TESTS !!!
# Make sure these filenames match your short CSV files
assets_m1_files = {
    'SPX500_M1': 'SPX500_M1_short.csv', # <-- USE SHORT FILE
    'XAUUSD_M1': 'XAUUSD_M1_short.csv', # <-- USE SHORT FILE
}

# --- Create Cerebro Instance ---
cerebro = bt.Cerebro(stdstats=False) # Use False to add analyzers manually

# --- Load and Preprocess Data with Pandas ---
print("Loading and preprocessing M1 SHORT data with Pandas...")
loaded_m1_dataframes = {} # Dictionary to store processed DataFrames
for name, filename in assets_m1_files.items():
    filepath = os.path.join(datapath_base, filename)
    if not os.path.exists(filepath):
        print(f"  WARNING: M1 SHORT data file not found: {filepath}")
        continue # Skip this file
    print(f"  - Preprocessing {name} from {filepath}")
    try:
        # Load CSV using pandas
        df = pd.read_csv(
            filepath,
            header=0, # Assumes first line is header: Date, Time, Open, High, Low, Close, Volume
        )

        # **CRITICAL FIX:** Combine Date and Time columns into a single DateTime index
        df['DateTime'] = pd.to_datetime(
            df['Date'].astype(str) + ' ' + df['Time'].astype(str),
            format='%Y-%m-%d %H:%M:%S' # CORRECTED FORMAT to match "YYYY-MM-DD HH:MM:SS"
        )
        df.set_index('DateTime', inplace=True)

        # Ensure standard OHLCV column names (lowercase)
        df.rename(columns={
            'Open': 'open', 'High': 'high', 'Low': 'low',
            'Close': 'close', 'Volume': 'volume'
        }, inplace=True)

        # Add OpenInterest column if missing (set to 0)
        if 'openinterest' not in df.columns:
             df['openinterest'] = 0.0

        # Drop original Date and Time columns if no longer needed
        if 'Date' in df.columns and 'Time' in df.columns:
            df.drop(columns=['Date', 'Time'], inplace=True)

        # Store the processed DataFrame
        loaded_m1_dataframes[name] = df
        print(f"  - Finished preprocessing {name}. DataFrame shape: {df.shape}, Index type: {df.index.dtype}")

    except Exception as e:
        print(f"  ERROR preprocessing {name}: {e}")
        import traceback
        traceback.print_exc()
        continue # Skip this file if preprocessing fails


# --- Feed Processed DataFrames to Backtrader ---
print("\nAdding preprocessed M1 SHORT data feeds to Cerebro...")
m1_feeds_added_to_cerebro = {} # Keep track of feeds added
for name, df in loaded_m1_dataframes.items():
     # Check if DataFrame is not empty
     if df.empty:
         print(f"  WARNING: DataFrame for {name} is empty after processing. Skipping.")
         continue
     # Check if index is DatetimeIndex
     if not isinstance(df.index, pd.DatetimeIndex):
         print(f"  ERROR: DataFrame index for {name} is not DatetimeIndex. Type: {type(df.index)}. Skipping.")
         continue

     print(f"  - Adding {name} DataFrame to Cerebro (as M1)")
     # Use PandasData feed - explicitly state it's M1 data
     data_feed_m1 = bt.feeds.PandasData(
         dataname=df,
         name=name, # Assign name for reference
         timeframe=bt.TimeFrame.Minutes, # Specify original timeframe
         compression=1                   # Specify original compression (1 minute)
     )
     cerebro.adddata(data_feed_m1)
     m1_feeds_added_to_cerebro[name] = data_feed_m1 # Store reference using original name


# --- NO RESAMPLING SECTION ---
# We are using the M1 feeds directly as loaded.
print("\nSkipping resampling step. Using M1 feeds directly.")


# --- Add a Simple Test Strategy (can be mostly empty for now) ---
class TestStrategyM1(bt.Strategy):
    def __init__(self):
        # Store references to feeds just in case, not heavily used here
        self.spx_feed = self.getdatabyname('SPX500_M1')
        self.xau_feed = self.getdatabyname('XAUUSD_M1')
        print("\n--- Strategy Initialized ---")
        # No need to print feeds again if already done

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0) # Use date from the first data feed
        print(f'{dt.isoformat()} {txt}') # Print date and message

    def prenext(self):
        # Called BEFORE next, once all feeds have data for the current step
        # Useful for seeing synchronization if needed later
        pass

    def nextstart(self):
        # Called ONCE, when all data feeds have minimum period requirements met
        # print("--- Nextstart Called (Strategy ready) ---")
        self.next() # Call next immediately

    def next(self):
        # For now, no logic needed here for basic price visualization.
        # Simple logging could be added if desired.
        # if len(self.data.datetime) % 100 == 0: # Print every 100 M1 bars
        #    self.log(f'Close SPX: {self.spx_feed.close[0]:.2f}, Close XAU: {self.xau_feed.close[0]:.2f}')
        pass

    def stop(self):
        # Called when the backtest ends
        print("--- Strategy Stop Called ---")


# --- Add Strategy and Analyzers ---
if m1_feeds_added_to_cerebro:
    cerebro.addstrategy(TestStrategyM1)
    # Adding Analyzers is good practice for future metrics
    print("\nAdding Analyzers...")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='tradeanalyzer')
    cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    # You could add more: SharpeRatio, VWR, etc.
else:
    print("\nSkipping strategy and analyzer addition as no M1 data was successfully added.")


# --- Define the Plotting Function ---
def plot_results(cerebro_results, data_feeds):
    """
    Generates an interactive dual chart using Plotly and saves it to an HTML file.

    Args:
        cerebro_results: The list returned by cerebro.run(). Can contain analyzers.
        data_feeds (dict): Dictionary with the original data feeds added to cerebro
                           {'feed_name': feed_object, ...}.
                           We need the feeds to get the OHLCV data.
    """
    print("\nGenerating Plotly chart...")
    if not data_feeds:
        print("  ERROR: No data feeds found to plot.")
        return

    if not cerebro_results:
        print("  WARNING: cerebro_results is empty or None. Cannot retrieve analyzers.")
        # We can still try to plot prices if feeds are available

    # Configure subplots: 1 row, number of columns = number of feeds
    num_feeds = len(data_feeds)
    fig = make_subplots(rows=1, cols=num_feeds,
                        shared_xaxes=True, # Share X axis
                        subplot_titles=[name for name in data_feeds.keys()],
                        vertical_spacing=0.05, # Reduce vertical space
                        horizontal_spacing=0.05 # Reduce horizontal space
                        )

    col_index = 1
    for name, feed in data_feeds.items():
        print(f"  - Processing feed for plotting: {name}")
        try:
            # Extract data from the feed AFTER cerebro.run()
            # The feeds now contain all processed bars.
            # We need to convert Backtrader dates (floats) to Pandas/Python datetime
            # Use slice [:] to get all elements from the line arrays
            dates = [bt.num2date(dt) for dt in feed.datetime.array[:]]
            opens = feed.open.array[:]
            highs = feed.high.array[:]
            lows = feed.low.array[:]
            closes = feed.close.array[:]
            volumes = feed.volume.array[:] # Volume might not be used in candlestick, but good to have

            # Create DataFrame for Plotly
            df_plot = pd.DataFrame({
                'open': opens,
                'high': highs,
                'low': lows,
                'close': closes,
                'volume': volumes
            }, index=pd.to_datetime(dates)) # Use converted dates as index

            if df_plot.empty:
                 print(f"    WARNING: DataFrame for {name} is empty after extraction. Skipping plot for this feed.")
                 col_index += 1 # Move to the next column
                 continue

            print(f"    - Extracted {len(df_plot)} bars for {name}")

            # Add Candlestick chart to the corresponding subplot
            fig.add_trace(go.Candlestick(x=df_plot.index,
                                         open=df_plot['open'],
                                         high=df_plot['high'],
                                         low=df_plot['low'],
                                         close=df_plot['close'],
                                         name=f'{name} Price'), # Name for legend
                          row=1, col=col_index)

            # (Optional Future) Add Indicators or Signals here as go.Scatter
            # Example: sma = df_plot['close'].rolling(window=20).mean()
            # fig.add_trace(go.Scatter(x=df_plot.index, y=sma, mode='lines', name='SMA(20)'), row=1, col=col_index)

            # (Optional Future) Add Trade markers (requires processing TradeAnalyzer)
            # trades = cerebro_results[0].analyzers.tradeanalyzer.get_analysis() if cerebro_results else None
            # if trades and 'trades' in trades: # Check if trades dict exists
            #    # ... (logic to extract and plot trades) ...
            #    pass


            print(f"    - Added Candlestick for {name} to column {col_index}")
            col_index += 1

        except IndexError:
             print(f"    WARNING: IndexError encountered for feed {name}. Possibly not enough data points after run? Skipping plot.")
             col_index += 1
        except Exception as e:
            print(f"    ERROR processing or plotting feed {name}: {e}")
            import traceback
            traceback.print_exc()
            col_index += 1 # Move to the next column even if there's an error

    # Update layout for better visualization
    fig.update_layout(
        title_text=f'M1 Visualization ({", ".join(data_feeds.keys())}) - Backtrader + Plotly',
        xaxis_rangeslider_visible=False, # Hide bottom rangeslider
        height=700, # Adjust height
        showlegend=True # Show legend
    )
    # Ensure X axes pan/zoom together
    fig.update_xaxes(matches='x')

    # --- USE write_html ---
    # Instead of showing directly, save to an HTML file
    output_filename = "backtest_plot.html"
    # Create the full path in the same directory as the script
    output_filepath = os.path.join(script_dir, output_filename)
    print(f"  Saving plot to HTML file: {output_filepath}")
    try:
        fig.write_html(output_filepath)
        print(f"  Plot saved successfully.")
    except Exception as e:
        print(f"  ERROR saving plot to HTML: {e}")
        return # Stop if saving failed

    # Optional: Try to open the HTML file automatically in the browser
    try:
        # Use file:// protocol and absolute path
        webbrowser.open(f'file://{output_filepath}')
        print(f"  Attempted to open {output_filepath} in default browser.")
    except Exception as e:
        print(f"  Could not automatically open browser: {e}")
    # --- END OF write_html ---


# --- Run Cerebro ---
print("\nRunning cerebro with M1 SHORT data...")
if not cerebro.datas:
     print("Cerebro has no data feeds to run.")
else:
    try:
        # Add initial cash and commission (examples)
        initial_cash = 100000.0
        cerebro.broker.set_cash(initial_cash)
        # Example commission: 0.1% per trade value
        # cerebro.broker.setcommission(commission=0.001)
        print(f"Broker initial cash: {initial_cash}")

        print("\nStarting Cerebro run...")
        # Store the execution results (contains analyzers)
        results = cerebro.run()
        print("\nCerebro run finished successfully.")

        # Print analyzer metrics (if they exist)
        if results and hasattr(results[0], 'analyzers'):
            print("\n--- Analyzer Results ---")
            try:
                # Access analyzers safely using get() with default values
                trade_analysis = results[0].analyzers.tradeanalyzer.get_analysis() if hasattr(results[0].analyzers, 'tradeanalyzer') else {}
                sqn_analysis = results[0].analyzers.sqn.get_analysis() if hasattr(results[0].analyzers, 'sqn') else {}
                drawdown_analysis = results[0].analyzers.drawdown.get_analysis() if hasattr(results[0].analyzers, 'drawdown') else {}

                print(f"SQN: {sqn_analysis.get('sqn', 'N/A')}") # SQN might be None if no trades
                # Handle potential None/empty dicts for drawdown/trades
                max_dd = drawdown_analysis.get('max', {})
                print(f"Max Drawdown: {max_dd.get('drawdown', 'N/A') if max_dd else 'N/A'}%")

                total_trades = trade_analysis.get('total', {})
                print(f"Total Trades: {total_trades.get('total', 'N/A') if total_trades else 'N/A'}")
                print(f"Total Closed Trades: {total_trades.get('closed', 'N/A') if total_trades else 'N/A'}")
                # You can print more details from trade_analysis if needed

            except AttributeError as ae:
                 print(f"  Could not access an analyzer attribute: {ae}")
            except Exception as e:
                print(f"  Error accessing or printing analyzer results: {e}")

        # --- CALL THE PLOTTING FUNCTION ---
        # Pass the results and the dictionary of added feeds
        plot_results(results, m1_feeds_added_to_cerebro)

    except Exception as e:
        print(f"\nERROR during cerebro run: {e}")
        import traceback
        traceback.print_exc()

print("\nScript finished.")