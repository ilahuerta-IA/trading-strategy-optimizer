import backtrader as bt
import datetime
from pathlib import Path
import matplotlib.pyplot as plt # Keep if plotting results

# Adjust import paths
from utils.parsing import parse_kwargs_str
from strategies.ma_cci_crossover import MACrossOver
from config import settings # Import the settings

def setup_and_run_backtest(args): # Accepts parsed args
    """Sets up and runs the Backtrader Cerebro engine."""

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
    csv_params = settings.CSV_PARAMS.copy()
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