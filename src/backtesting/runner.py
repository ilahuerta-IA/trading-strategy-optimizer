# backtesting/runner.py
import backtrader as bt
import datetime
from pathlib import Path
import matplotlib.pyplot as plt
import importlib
import traceback # Import traceback for detailed error printing
from typing import Dict, Any, Callable # For type hinting
import collections # Import collections for OrderedDict if used in analyzers
from pprint import pprint # For pretty printing dicts

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

    # --- Add Analyzers ---
    print("Adding Standard Analyzers: TradeAnalyzer, DrawDown")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='tradeanalyzer')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    print("Adding More Analyzers: SharpeRatio, SQN, TimeReturn (Monthly), Transactions")
    # Sharpe Ratio (assuming default risk-free rate for now)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe',
                        # timeframe=bt.TimeFrame.Days, # Adjust if needed
                        # annualization=252 # Adjust based on timeframe
                        )
    # System Quality Number
    cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
    # Monthly Returns
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='monthlyreturns',
                        timeframe=bt.TimeFrame.Months)
    # Detailed Trade List or Transactions
    cerebro.addanalyzer(bt.analyzers.Transactions, _name='transactions')

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
    output_result = BacktestResult(args.run_name, strategy_name, strat_kwargs)

    if results is None or not isinstance(results, list) or len(results) == 0 or results[0] is None:
         print("Error: Cerebro run did not return valid results.")
         return output_result # Return potentially empty results object

    strat_instance = results[0]
    print(f"Strategy instance obtained: {type(strat_instance)}")

    # --- Create dictionary to hold all extracted analysis ---
    analysis_results = {}

    # --- Function to safely get analysis ---
    def get_analyzer_output(analyzer_name):
        analysis = None # Default to None
        try:
            # --- Use direct attribute access ---
            if hasattr(strat_instance.analyzers, analyzer_name):
                # Access the analyzer directly by its _name attribute
                analyzer = getattr(strat_instance.analyzers, analyzer_name)
                analysis = analyzer.get_analysis()
                print(f"Successfully extracted '{analyzer_name}' analysis.")
            # --- End direct attribute access ---
            else:
                print(f"Analyzer attribute '{analyzer_name}' not found.")
        except Exception as e:
            print(f"Error processing Analyzer '{analyzer_name}': {e}")
            # traceback.print_exc() # Optional for more detail
        return analysis # Return analysis or None

    # --- Extract from all analyzers ---
    analysis_results['drawdown'] = get_analyzer_output('drawdown')
    analysis_results['tradeanalyzer'] = get_analyzer_output('tradeanalyzer')
    analysis_results['sharpe'] = get_analyzer_output('sharpe')
    analysis_results['sqn'] = get_analyzer_output('sqn')
    analysis_results['monthlyreturns'] = get_analyzer_output('monthlyreturns')
    analysis_results['transactions'] = get_analyzer_output('transactions') 
    analysis_results['valuecapture'] = get_analyzer_output('valuecapture')

    # Store metrics dict in the final result object
    output_result.metrics = analysis_results
    output_result.value_analysis = analysis_results.get('valuecapture')

    # --- Detailed Terminal Printing ---
    print("\n\n" + "="*80)
    print(f"BACKTEST REPORT: {args.run_name}")
    print("="*80)

    # --- Run Configuration ---
    print("\n--- Run Configuration ---")
    print(f"Strategy:         {strategy_name}")
    print(f"Parameters:")
    pprint(strat_kwargs, indent=4) # Pretty print parameters
    print(f"Data 0:           {data0_name}.csv") # Assumes csv extension
    print(f"Data 1:           {data1_name}.csv")
    print(f"From Date:        {args.fromdate or 'Start of Data'}")
    print(f"To Date:          {args.todate or 'End of Data'}")
    # Extract initial cash if possible (might require accessing broker obj before run)
    # print(f"Initial Cash:     {cerebro.broker.startingcash:.2f}") # Example
    print(f"Broker Args:      '{args.broker}'")
    print(f"Sizer Args:       '{args.sizer}'")

    # --- Overall Performance Metrics ---
    print("\n--- Overall Performance ---")
    ta = analysis_results.get('tradeanalyzer')
    dd = analysis_results.get('drawdown')
    sharpe = analysis_results.get('sharpe')
    sqn = analysis_results.get('sqn')

    total_net_pnl = ta.get('pnl', {}).get('net', {}).get('total', 0.0) if ta else 0.0
    print(f"Total Net PnL:      ${total_net_pnl:12.2f}")

    if dd:
        print(f"Max Drawdown:        {dd.get('max', {}).get('drawdown', 0.0):.2f}%")
        print(f"Max Drawdown ($):   ${dd.get('max', {}).get('moneydown', 0.0):12.2f}")
    else:
        print("Max Drawdown:       N/A")
        print("Max Drawdown ($):   N/A")

    if sharpe and sharpe.get('sharperatio'):
         print(f"Sharpe Ratio:        {sharpe['sharperatio']:.3f}")
    else:
         print(f"Sharpe Ratio:       N/A")

    if sqn and sqn.get('sqn'):
        print(f"SQN:                 {sqn['sqn']:.3f}")
    else:
        print(f"SQN:                N/A")


    # Trade Stats from TradeAnalyzer
    if ta:
        closed_trades = ta.get('total', {}).get('closed', 0)
        won_total = ta.get('won', {}).get('total', 0)
        lost_total = ta.get('lost', {}).get('total', 0)
        print(f"Total Closed Trades:{closed_trades:6d}")
        print(f"Winning Trades:     {won_total:6d}")
        print(f"Losing Trades:      {lost_total:6d}")
        win_rate = (won_total / closed_trades * 100) if closed_trades > 0 else 0.0
        print(f"Win Rate (%):       {win_rate:8.2f}%")

        # PnL Stats
        won_pnl_total = ta.get('won', {}).get('pnl', {}).get('total', 0.0)
        lost_pnl_total = ta.get('lost', {}).get('pnl', {}).get('total', 0.0)
        if lost_pnl_total != 0:
            profit_factor = abs(won_pnl_total / lost_pnl_total)
            print(f"Profit Factor:       {profit_factor:9.2f}")
        elif won_pnl_total > 0:
            print(f"Profit Factor:       Infinity")
        else:
            print(f"Profit Factor:       N/A")

        print(f"Avg Trade Net PnL:  ${ta.get('pnl', {}).get('net', {}).get('average', 0.0):9.2f}")
        print(f"Avg Winning Trade:  ${ta.get('won', {}).get('pnl', {}).get('average', 0.0):9.2f}")
        print(f"Avg Losing Trade:   ${ta.get('lost', {}).get('pnl', {}).get('average', 0.0):9.2f}")
        print(f"Max Winning Trade:  ${ta.get('won', {}).get('pnl', {}).get('max', 0.0):9.2f}")
        print(f"Max Losing Trade:   ${ta.get('lost', {}).get('pnl', {}).get('max', 0.0):9.2f}")
    else:
        print("Trade statistics N/A (TradeAnalyzer failed or no trades).")


    # --- Detailed Transactions List ---
    print("\n--- Transactions List ---") # Update title
    transactions_output = analysis_results.get('transactions')
    if isinstance(transactions_output, dict) and len(transactions_output) > 0:
        # Header for Transactions output
        print(f"{'Date':<19s} | {'Symbol':<15s} | {'Amount':>8s} | {'Price':>11s} | {'Value':>12s}")
        print("-"*70) # Adjusted width

        # Sort transactions by datetime keys
        sorted_dts = sorted(transactions_output.keys())
        tx_num = 0
        for dt in sorted_dts:
            for tx_list in transactions_output[dt]:
                 tx_num += 1
                 # Unpack the list safely
                 amount = tx_list[0] if len(tx_list) > 0 else 0
                 price = tx_list[1] if len(tx_list) > 1 else 0.0
                 # sid = tx_list[2] # sid might not be useful here
                 symbol = str(tx_list[3])[:15] if len(tx_list) > 3 else 'N/A'
                 value = tx_list[4] if len(tx_list) > 4 else 0.0
                 dt_str = dt.strftime('%Y-%m-%d %H:%M:%S')

                 print(f"{dt_str:<19s} | {symbol:<15s} | {amount:>8d} | {price:>11.2f} | {value:>12.2f}")

    else:
        print("No detailed transaction list available (Transactions analyzer missing, no transactions, or unexpected format).")

    # --- Monthly Returns ---
    print("\n--- Monthly Returns ---")
    monthly_returns = analysis_results.get('monthlyreturns')
    if monthly_returns:
        # The keys are datetime objects representing the start of the month
        # Sort by date just in case
        sorted_months = sorted(monthly_returns.keys())
        print(f"{'Month':<10s} | {'Return (%)':>10s}")
        print("-"*25)
        for month_start_dt in sorted_months:
            ret = monthly_returns[month_start_dt] * 100 # Convert to percentage
            # Format month as YYYY-MM
            month_str = month_start_dt.strftime('%Y-%m')
            print(f"{month_str:<10s} | {ret:>10.2f}%")
    else:
        print("No monthly returns data available (TimeReturn analyzer missing).")

    print("\n" + "="*80)
    print("--- End of Report ---")
    
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