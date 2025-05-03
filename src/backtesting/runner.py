# backtesting/runner.py
import backtrader as bt
import datetime
from pathlib import Path
import matplotlib.pyplot as plt
import importlib
import traceback # Import traceback for detailed error printing
from typing import Dict, Any, Callable # For type hinting

# --- Import the Analyzer ---
from analyzers.value_capture import ValueCaptureAnalyzer

# Assuming parse_kwargs_str is in utils.parsing
from utils.parsing import parse_kwargs_str
from config import settings

# Define a structure for results
class BacktestResult:
    """Holds the structured results from a backtest run."""
    def __init__(self, run_name, strategy_name, parameters):
        self.run_name = run_name
        self.strategy_name = strategy_name
        self.parameters = parameters
        self.metrics = {} # For standard analyzers like Drawdown, TradeAnalyzer
        self.value_analysis = None # Keep placeholder if needed later

def setup_and_run_backtest(args, parse_kwargs_func: Callable[[str], Dict[str, Any]]):
    """Sets up and runs the Backtrader Cerebro engine."""

    cerebro = bt.Cerebro()

    # --- Date Filtering ---
    data_kwargs = dict()
    dtfmt, tmfmt = '%Y-%m-%d', 'T%H:%M:%S'
    for arg_name in ['fromdate', 'todate']:
        date_str = getattr(args, arg_name)
        if date_str:
             try:
                 if 'T' in date_str or ':' in date_str:
                      if 'T' in date_str: strpfmt = dtfmt + tmfmt
                      elif len(date_str) > 10: strpfmt = f"{dtfmt} %H:%M:%S"
                      else: strpfmt = dtfmt
                 else: strpfmt = dtfmt
                 data_kwargs[arg_name] = datetime.datetime.strptime(date_str, strpfmt)
                 print(f"Parsed {arg_name}: {data_kwargs[arg_name]} using format {strpfmt}")
             except ValueError as e:
                  print(f"Warning: Error parsing date string '{date_str}' for {arg_name}: {e}. Filter ignored.")

    # --- CSV Feed Setup ---
    CSVDataFeed = bt.feeds.GenericCSVData
    csv_params = settings.CSV_PARAMS.copy()
    print(f"Using CSV data feed: {CSVDataFeed}")

    # --- Load Data Feeds AND Set Name ---
    data0_name = "data0" # Default names
    data1_name = "data1"
    try:
        print(f"Attempting to load data 1 from: {args.data_path_1}")
        feed_params_0 = csv_params.copy()
        feed_params_0['dataname'] = args.data_path_1
        data0 = CSVDataFeed(**feed_params_0, **data_kwargs)
        data0.plotinfo.plotvolume = False
        data0.plotinfo.plotvolsubplot = False
        data0_name = Path(args.data_path_1).stem # Update name from file
        data0._name = data0_name
        print(f"Adding data feed '{data0._name}' to Cerebro. Date Filters: {data_kwargs}")
        cerebro.adddata(data0)
    except Exception as e:
        print(f"FATAL ERROR loading data from {args.data_path_1}: {e}")
        traceback.print_exc()
        return None

    try:
        print(f"Attempting to load data 2 from: {args.data_path_2}")
        feed_params_1 = csv_params.copy()
        feed_params_1['dataname'] = args.data_path_2
        data1 = CSVDataFeed(**feed_params_1, **data_kwargs)
        data1.plotinfo.plotmaster = data0 # Plot on same chart as data0
        data1.plotinfo.plotvolume = False
        data1.plotinfo.plotvolsubplot = False
        data1_name = Path(args.data_path_2).stem # Update name from file
        data1._name = data1_name
        print(f"Adding data feed '{data1._name}' to Cerebro. Date Filters: {data_kwargs}")
        cerebro.adddata(data1)
    except Exception as e:
        print(f"FATAL ERROR loading data from {args.data_path_2}: {e}")
        traceback.print_exc()
        return None

    # --- Broker ---
    print(f"Parsing broker args: '{args.broker}'")
    broker_kwargs = parse_kwargs_func(args.broker)
    broker_init_kwargs = broker_kwargs.copy()
    commission_config = {}
    if 'commission' in broker_init_kwargs:
        commission_value = broker_init_kwargs.pop('commission')
        commission_config['commission'] = commission_value
        commission_config['percabs'] = True
    print(f"Initial Broker kwargs: {broker_init_kwargs}")
    cerebro.broker = bt.brokers.BackBroker(**broker_init_kwargs)
    if commission_config:
        print(f"Setting commission: {commission_config['commission']*100:.3f}%")
        cerebro.broker.setcommission(**commission_config)
    else: print("No commission specified.")

    # --- Sizer ---
    print(f"Parsing sizer args: '{args.sizer}'")
    sizer_kwargs = parse_kwargs_func(args.sizer)
    print(f"Applying sizer kwargs: {sizer_kwargs}")
    cerebro.addsizer(bt.sizers.FixedSize, **sizer_kwargs)

    # --- Dynamic Strategy Selection ---
    strategy_name = args.strategy_name
    print(f"Selecting strategy: {strategy_name}")
    strat_kwargs = parse_kwargs_func(args.strat)
    strat_kwargs['run_name'] = args.run_name # Inject run_name

    strategy_class = None
    try:
        # Map strategy name argument to module and class name
        if strategy_name == 'SMACrossOver':
            module_name = 'strategies.sma_crossover'
            class_name = 'SMACrossOverStrategy'
        elif strategy_name == 'MACrossOver':
             module_name = 'strategies.ma_cci_crossover'
             class_name = 'MACrossOver'
        elif strategy_name == 'CorrelatedSMACross':
             module_name = 'strategies.correlated_sma_cross'
             class_name = 'CorrelatedSMACrossStrategy'
        elif strategy_name == 'BBandPearsonDivergence':
             module_name = 'strategies.bband_pearson_divergence'
             class_name = 'BBandPearsonDivergence'
        elif strategy_name == 'NullStrategy': # Ensure NullStrategy is mapped
             module_name = 'strategies.null_strategy'
             class_name = 'NullStrategy'
        else:
            raise ValueError(f"Unknown strategy name provided: {strategy_name}")

        strategy_module = importlib.import_module(module_name)
        strategy_class = getattr(strategy_module, class_name)

    except (ImportError, AttributeError, ValueError) as e:
        print(f"FATAL ERROR: Could not load strategy '{strategy_name}': {e}")
        print("Check --strategy-name argument and ensure the strategy file/class exists and is mapped correctly in runner.py.")
        return None # Return None on error

    if strategy_class:
        print(f"Applying strategy kwargs for {strategy_name}: {strat_kwargs}")
        cerebro.addstrategy(strategy_class, **strat_kwargs)
    else:
        print("FATAL: Strategy class not loaded.")
        return None # Return None on error

    # --- Add Standard Analyzers ---
    print("Adding Standard Analyzers: TradeAnalyzer, DrawDown")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='tradeanalyzer')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

    # --- Add Custom Value Capture Analyzer ---
    print("Adding Custom Analyzer: ValueCaptureAnalyzer")
    cerebro.addanalyzer(ValueCaptureAnalyzer, _name='valuecapture')

    # --- Observer (COMMENTED OUT) ---
    # print("Adding Value Observer")
    # cerebro.addobserver(bt.observers.Value)

    # --- Execute ---
    print(f"--- Starting Cerebro Run ({args.run_name}) ---")
    results = None
    run_kwargs = {} # Initialize run_kwargs
    try:
        run_kwargs = parse_kwargs_func(args.cerebro)
        print(f"Applying cerebro.run kwargs: {run_kwargs}")
        results = cerebro.run(**run_kwargs)
    except Exception as e:
         print(f"FATAL ERROR during cerebro.run: {e}")
         traceback.print_exc()
         return None # Return None on error
    print(f"--- Cerebro Run Finished ({args.run_name}) ---")


    # --- Process and Package Results ---
    print("\n--- Processing Backtest Results ---")
    # Use strat_kwargs captured earlier for parameters
    output_result = BacktestResult(args.run_name, strategy_name, strat_kwargs)

    # --- Refined Checks on Results list ---
    if results is None:
         print("Error: Cerebro run did not return results.")
         return output_result
    if not isinstance(results, list) or len(results) == 0:
         print("Error: Cerebro run returned invalid or empty results list.")
         return output_result
    if results[0] is None:
        print("Error: The first element in the results list (strategy instance) is None.")
        return output_result
    # --- End Refined Checks ---

    # If checks passed, get the instance
    strat_instance = results[0]
    print(f"Strategy instance obtained: {type(strat_instance)}")

    # --- Extract and Print Standard Analyzer Results ---
    drawdown_analysis = None # Initialize local variable
    trade_analysis = None    # Initialize local variable

    # --- Drawdown ---
    print("\n--- Drawdown Analysis ---")
    try:
        # Use hasattr for robust check before accessing analyzer
        if hasattr(strat_instance.analyzers, 'drawdown'):
            drawdown_analysis = strat_instance.analyzers.drawdown.get_analysis()
            output_result.metrics['drawdown'] = drawdown_analysis # Store it
            if drawdown_analysis and hasattr(drawdown_analysis, 'max'): # Check structure before printing
                 print(f"Max Drawdown:       {drawdown_analysis.max.drawdown:.2f}%")
                 print(f"Max Drawdown ($):   {drawdown_analysis.max.moneydown:.2f}")
            else:
                 print("Drawdown analysis structure incomplete or None.")
        else:
             print("DrawDown analyzer attribute not found.")
    except Exception as e: # Catch any other exception during processing
         print(f"Error processing DrawDown Analyzer: {e}")

    # --- Trade Analysis ---
    print("\n--- Trade Analysis ---")
    try:
        # Use hasattr for robust check
        if hasattr(strat_instance.analyzers, 'tradeanalyzer'):
            trade_analysis = strat_instance.analyzers.tradeanalyzer.get_analysis()
            output_result.metrics['trade_analysis'] = trade_analysis # Store it

            # --- Print details ONLY if analysis is valid ---
            if trade_analysis: # Check if analysis object is not None/empty
                # Use .get() with defaults for safe access
                total_trades = trade_analysis.get('total', {}).get('total', 0)
                closed_trades = trade_analysis.get('total', {}).get('closed', 0)

                if total_trades > 0:
                    print(f"Total Closed Trades:{closed_trades:6d}")
                    print(f"Total Open Trades:  {trade_analysis.get('total', {}).get('open', 0):6d}")
                    print("")
                    print(f"Winning Trades:     {trade_analysis.get('won', {}).get('total', 0):6d}")
                    print(f"Losing Trades:      {trade_analysis.get('lost', {}).get('total', 0):6d}")
                    print("")

                    # PnL Stats
                    print(f"Total Net PnL:    ${trade_analysis.get('pnl', {}).get('net', {}).get('total', 0.0):9.2f}")
                    print(f"Avg Net PnL:      ${trade_analysis.get('pnl', {}).get('net', {}).get('average', 0.0):9.2f}")
                    print("")
                    print(f"Total Winning PnL:${trade_analysis.get('won', {}).get('pnl', {}).get('total', 0.0):9.2f}")
                    print(f"Avg Winning PnL:  ${trade_analysis.get('won', {}).get('pnl', {}).get('average', 0.0):9.2f}")
                    print(f"Max Winning PnL:  ${trade_analysis.get('won', {}).get('pnl', {}).get('max', 0.0):9.2f}")
                    print("")
                    print(f"Total Losing PnL: ${trade_analysis.get('lost', {}).get('pnl', {}).get('total', 0.0):9.2f}")
                    print(f"Avg Losing PnL:   ${trade_analysis.get('lost', {}).get('pnl', {}).get('average', 0.0):9.2f}")
                    print(f"Max Losing PnL:   ${trade_analysis.get('lost', {}).get('pnl', {}).get('max', 0.0):9.2f}")
                    print("")

                    # Profit Factor
                    lost_total_pnl = trade_analysis.get('lost', {}).get('pnl', {}).get('total', 0.0)
                    won_total_pnl = trade_analysis.get('won', {}).get('pnl', {}).get('total', 0.0)
                    if lost_total_pnl != 0:
                         profit_factor = abs(won_total_pnl / lost_total_pnl)
                         print(f"Profit Factor:      {profit_factor:9.2f}")
                    elif won_total_pnl > 0:
                          print(f"Profit Factor:      Infinity (No Losses)")
                    else:
                          print(f"Profit Factor:      N/A (No Wins or Losses)")

                    # --- Print PnL for Each Closed Trade ---
                    print("\n--- PnL per Closed Trade ---")
                    trades_list = trade_analysis.get('trades', [])
                    if isinstance(trades_list, list) and len(trades_list) > 0:
                        trade_num = 0
                        for trade_info in trades_list:
                            if isinstance(trade_info, dict) and 'pnl' in trade_info and 'pnlcomm' in trade_info:
                                 trade_num += 1
                                 pnl = trade_info.get('pnl', 0.0)
                                 pnlcomm = trade_info.get('pnlcomm', 0.0)
                                 status = "WIN" if pnlcomm > 0 else "LOSS" if pnlcomm < 0 else "FLAT"
                                 print(f"Trade #{trade_num:3d}: Status: {status:4s}, Net PnL: ${pnlcomm:8.2f} (Gross PnL: ${pnl:8.2f})")
                            else:
                                 print(f"Warning: Unexpected format for trade_info item: {type(trade_info)}")
                    elif closed_trades > 0:
                         print("Trade list structure unexpected or missing, but closed trades exist.")
                    else:
                         print("No individual closed trade PnL data available.")
                    # --- End PnL per Trade ---
                else:
                     print("No trades were executed or analyzed.")
            else:
                print("Trade analysis returned None or was empty.")
        else:
            print("TradeAnalyzer attribute not found.")
    except Exception as e: # Catch any other exception during processing
         print(f"Error processing Trade Analyzer: {e}")
         traceback.print_exc()

    # --- Custom Analyzer Results ---
    print("\n--- Custom Analyzer Results ---")
    print("\n--- Custom Analyzer Results ---")
    try:
        # Use hasattr for safety, though we added it, good practice
        if hasattr(strat_instance.analyzers, 'valuecapture'):
            value_analysis = strat_instance.analyzers.valuecapture.get_analysis()
            output_result.value_analysis = value_analysis # Store the result
            print(f"ValueCapture: Captured {len(value_analysis.get('values', []))} portfolio value points.")
        else:
             print("ValueCapture analyzer attribute not found.")
    except Exception as e: # Catch potential errors during get_analysis
         print(f"Error processing ValueCapture Analyzer: {e}")
         # Ensure value_analysis is None if extraction fails
         output_result.value_analysis = None

    # --- Generate Default Plot (if requested via args.plot) ---
    if args.plot:
        print("\n--- Generating Default Backtrader Plot ---")
        plot_kwargs = {} # Define dictionary for plot args
        # Set preferred defaults
        plot_kwargs.setdefault('style', 'line')
        plot_kwargs.setdefault('volume', False)
        plot_kwargs.setdefault('value', False) # Disable observer plot line (if observer was added)
        plot_kwargs.setdefault('broker', False)
        plot_kwargs.setdefault('figsize', (20, 10))

        # Allow overriding via command line (this part might need adjustment if --plot becomes just a flag)
        # If args.plot is just a flag, how do we pass kwargs?
        # We might need a separate --plot-args argument in main.py in the future.
        # For now, this only applies our defaults if --plot flag is present.
        # plot_user_kwargs = parse_kwargs_func(args.plot if isinstance(args.plot, str) else '{}') # Safely parse if it's a string
        # plot_kwargs.update(plot_user_kwargs) # Merge user args

        plot_title = f"Backtest: {args.run_name} ({strategy_name} on {data0_name} / {data1_name})"
        print(f"Plot Title Hint (Default Plot): {plot_title}")
        print(f"Applying plot kwargs (Default Plot): {plot_kwargs}")
        try:
             cerebro.plot(**plot_kwargs)
             print("Default plot generation finished.")
             # If plt.show() is in main.py, don't call it here
        except Exception as e_plot:
             print(f"ERROR generating default plot: {e_plot}")

    # --- Return the packaged results ---
    print("--- Backtest Runner Finished ---")
    return output_result