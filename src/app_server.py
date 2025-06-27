# src/app_server.py
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import datetime
import traceback # For detailed error logging
import multiprocessing

# --- Add project root to path so modules in 'src' can find each other ---
# If app_server.py is in src/, then src.parent is the project_root
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
# Additionally, ensure 'src' itself is in the path for direct src imports
# if src directory is not directly in sys.path
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

# --- Additional imports ---
import backtrader as bt
from typing import Callable, Dict, Any
import importlib

# --- Imports from your project ---
# Ensure these paths are correct relative to how Python resolves them now
try:
    from backtesting.runner import setup_and_run_backtest
    from config import settings
    from utils.parsing import parse_kwargs_str
    from strategies import get_strategy_class, list_available_strategies
    from strategies.base_strategy import ParameterDefinition
except ImportError as e:
    print(f"Error importing project modules: {e}")
    print("Ensure app_server.py is in the 'src' directory or adjust Python path.")
    sys.exit(1)

# --- Global variable to store backtest results ---
CACHED_BACKTEST_DATA = None # This will store a dictionary with value_analysis, metrics_report, and run_config

# --- Initialize Flask App ---
# By explicitly setting the folder paths, we make the app more robust
# and ensure it can always find the CSS, JS, and HTML files.
app = Flask(__name__,
            static_folder='static',
            template_folder='templates')
CORS(app) # Enable CORS for all routes

def run_simulation_and_cache():
    """Runs the backtest and stores the results in CACHED_BACKTEST_DATA."""
    global CACHED_BACKTEST_DATA
    print("Flask Server: Running backtest simulation...")

    # --- Use default settings for a standard run ---
    class ArgsMock:
        def __init__(self):
            self.data_path_1 = str(settings.DEFAULT_DATA_PATH_1)
            self.data_path_2 = str(settings.DEFAULT_DATA_PATH_2)
            self.strategy_name = settings.DEFAULT_STRATEGY_NAME # e.g., SMACrossOver
            self.fromdate = settings.DEFAULT_FROM_DATE
            self.todate = settings.DEFAULT_TO_DATE
            self.broker = settings.DEFAULT_BROKER_ARGS
            self.sizer = settings.DEFAULT_SIZER_ARGS
            self.strat = settings.DEFAULT_STRAT_ARGS # Ensure these match the default strategy
            self.cerebro = settings.DEFAULT_CEREBRO_ARGS
            self.run_name = f"web_run_{datetime.datetime.now():%Y%m%d_%H%M%S}"
            self.plot = False # Plotting is handled by the frontend JS

    args = ArgsMock()

    results_data_object = setup_and_run_backtest(args, parse_kwargs_func=parse_kwargs_str)

    if results_data_object:
        print("Flask Server: Simulation complete. Caching data.")
        CACHED_BACKTEST_DATA = {
            "value_analysis": getattr(results_data_object, 'value_analysis', None),
            "metrics_report": getattr(results_data_object, 'metrics', {}),
            "run_config": getattr(results_data_object, 'run_config_summary', {})
        }
        if not CACHED_BACKTEST_DATA["value_analysis"]:
            print("Flask Server: Warning - 'value_analysis' is missing from results_data_object.")
        if not CACHED_BACKTEST_DATA["metrics_report"]:
            print("Flask Server: Warning - 'metrics' is missing from results_data_object.")
        if not CACHED_BACKTEST_DATA["run_config"]:
            print("Flask Server: Warning - 'run_config_summary' is missing from results_data_object.")
    else:
        print("Flask Server: Simulation failed or no results_data_object returned.")
        CACHED_BACKTEST_DATA = { # Ensure it's a dict even on failure for consistent API response
            "value_analysis": None,
            "metrics_report": {},
            "run_config": {}
        }

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/api/chart_data', methods=['GET'])
def get_chart_data():
    """API endpoint to provide chart data and backtest report in JSON format."""
    global CACHED_BACKTEST_DATA
    if CACHED_BACKTEST_DATA is None or CACHED_BACKTEST_DATA.get("value_analysis") is None:
        print("API Error: Backtest data (value_analysis) not cached or simulation failed.")
        return jsonify({"error": "Backtest chart data not available. Simulation might have failed or not run."}), 404

    output_json = {
        "data0_ohlc": [],
        "data1_line": [],
        "data1_ohlc": [],
        "portfolio_value_line": [],
        "indicator_configs": [],
        "indicator_series": {},
        "trade_signals": [],
        "report_data": {}
    }
    
    value_analysis_data = CACHED_BACKTEST_DATA.get('value_analysis', {})
    metrics_report = CACHED_BACKTEST_DATA.get('metrics_report', {})
    run_config_summary = CACHED_BACKTEST_DATA.get('run_config', {})

    try:
        datetimes = value_analysis_data.get('datetimes', [])
        times_sec = [dt.timestamp() for dt in datetimes]

        # Data0 OHLC
        d0_ohlc_data = value_analysis_data.get('d0_ohlc', {})
        if times_sec and d0_ohlc_data.get('close'):
            if all(len(d0_ohlc_data.get(k, [])) == len(datetimes) for k in ['open', 'high', 'low', 'close']):
                for i in range(len(times_sec)):
                    output_json["data0_ohlc"].append({
                        "time": times_sec[i],
                        "open": d0_ohlc_data['open'][i],
                        "high": d0_ohlc_data['high'][i],
                        "low": d0_ohlc_data['low'][i],
                        "close": d0_ohlc_data['close'][i]
                    })
            else:
                print("API Warning: Data0 OHLC lists length mismatch with datetimes.")
        else:
            print("API Warning: Insufficient data for Data0 OHLC.")

        # Data1 Line (existing logic, kept for potential other uses)
        d1_ohlc_data_for_line = value_analysis_data.get('d1_ohlc', {})
        d1_close_values = d1_ohlc_data_for_line.get('close', [])
        if times_sec and d1_close_values and len(times_sec) == len(d1_close_values):
            for i in range(len(times_sec)):
                output_json["data1_line"].append({"time": times_sec[i], "value": d1_close_values[i]})
        else:
            print("API Warning: Insufficient or mismatched data for Data1 line (close values).")

        # Data1 OHLC for Candlestick Chart
        d1_ohlc_full_data = value_analysis_data.get('d1_ohlc', {})
        if times_sec and d1_ohlc_full_data.get('close'):
            if all(len(d1_ohlc_full_data.get(k, [])) == len(datetimes) for k in ['open', 'high', 'low', 'close']):
                for i in range(len(times_sec)):
                    output_json["data1_ohlc"].append({
                        "time": times_sec[i],
                        "open": d1_ohlc_full_data['open'][i],
                        "high": d1_ohlc_full_data['high'][i],
                        "low": d1_ohlc_full_data['low'][i],
                        "close": d1_ohlc_full_data['close'][i]
                    })
            else:
                print("API Warning: Data1 OHLC lists length mismatch with datetimes. Data1 candlestick chart may be empty.")
                output_json["data1_ohlc"] = []
        else:
            print("API Warning: Insufficient data for Data1 OHLC. Data1 candlestick chart will be empty.")
            output_json["data1_ohlc"] = []

        # Portfolio Value Line
        portfolio_values = value_analysis_data.get('values', [])
        if times_sec and portfolio_values and len(times_sec) == len(portfolio_values):
            for i in range(len(times_sec)):
                output_json["portfolio_value_line"].append({"time": times_sec[i], "value": portfolio_values[i]})
        else:
            print("API Warning: Insufficient or mismatched data for Portfolio Value line.")

        # Process and add indicator data
        indicator_configs = value_analysis_data.get('indicator_configs', [])
        indicator_series_data = value_analysis_data.get('indicators', {})
        output_json['indicator_configs'] = indicator_configs
        for internal_id, series_values in indicator_series_data.items():
            if times_sec and series_values and len(times_sec) == len(series_values):
                output_json['indicator_series'][internal_id] = [
                    {"time": times_sec[i], "value": series_values[i]} 
                    for i in range(len(times_sec))
                    if not np.isnan(series_values[i])
                ]
            else:
                print(f"API Warning: Mismatched lengths or no data for indicator {internal_id}")
        
        # Process trade signals
        signals = value_analysis_data.get('signals', [])
        for sig in signals:
            try:
                ts = datetime.datetime.fromisoformat(sig['datetime']).timestamp()
            except Exception:
                ts = None
            output_json['trade_signals'].append({
                'type': sig.get('type'),
                'time': ts,
                'price': sig.get('price')
            })

        # --- Populate Backtest Report Data ---
        report_data = {
            "run_config": {
                "strategy_name": run_config_summary.get('strategy_name', 'N/A'),
                "parameters": run_config_summary.get('parameters', {}),
                "data_path_1": run_config_summary.get('data_path_1', 'N/A'),
                "fromdate": run_config_summary.get('fromdate', 'N/A'),
                "todate": run_config_summary.get('todate', 'N/A'),
            },
            "performance_summary": {},
            "trade_stats": {}
        }

        # Helper to safely get nested dictionary values
        def get_nested_value(data_dict, keys, default_val=None):
            current = data_dict
            for key in keys:
                if isinstance(current, dict) and key in current and current[key] is not None:
                    current = current[key]
                else:
                    return default_val
            return current

        ta = metrics_report.get('tradeanalyzer', {})
        dd = metrics_report.get('drawdown', {})
        sh = metrics_report.get('sharpe', {})
        sq = metrics_report.get('sqn', {})

        # Performance Summary
        report_data["performance_summary"]["total_net_pnl"] = get_nested_value(ta, ['pnl', 'net', 'total'], 0.0)
        report_data["performance_summary"]["max_drawdown_pct"] = get_nested_value(dd, ['max', 'drawdown'], 0.0) 
        report_data["performance_summary"]["sharpe_ratio"] = get_nested_value(sh, ['sharperatio'], "N/A")
        report_data["performance_summary"]["sqn"] = get_nested_value(sq, ['sqn'], "N/A")

        # Trade Stats
        total_closed_trades = get_nested_value(ta, ['total', 'closed'], 0)
        won_total = get_nested_value(ta, ['won', 'total'], 0)
        lost_total = get_nested_value(ta, ['lost', 'total'], 0)
        
        pnl_gross_total = get_nested_value(ta, ['pnl', 'gross', 'total'], 0.0)
        lost_pnl_total_val = get_nested_value(ta, ['lost', 'pnl', 'total'], 0.0)

        report_data["trade_stats"]["total_closed_trades"] = total_closed_trades
        report_data["trade_stats"]["win_rate_pct"] = (won_total / total_closed_trades * 100) if total_closed_trades > 0 else 0.0
        
        if lost_pnl_total_val == 0:
            profit_factor = "N/A" if pnl_gross_total == 0 else float('inf')
        else:
            profit_factor = pnl_gross_total / abs(lost_pnl_total_val)
        report_data["trade_stats"]["profit_factor"] = profit_factor
        
        report_data["trade_stats"]["avg_pnl_per_trade"] = get_nested_value(ta, ['pnl', 'net', 'average'], 0.0)
        report_data["trade_stats"]["total_winning_trades"] = won_total
        report_data["trade_stats"]["total_losing_trades"] = lost_total
        report_data["trade_stats"]["avg_win_pnl"] = get_nested_value(ta, ['won', 'pnl', 'average'], 0.0)
        report_data["trade_stats"]["avg_loss_pnl"] = get_nested_value(ta, ['lost', 'pnl', 'average'], 0.0)
        report_data["trade_stats"]["max_win_pnl"] = get_nested_value(ta, ['won', 'pnl', 'max'], 0.0)
        report_data["trade_stats"]["max_loss_pnl"] = get_nested_value(ta, ['lost', 'pnl', 'max'], 0.0)

        output_json['report_data'] = report_data

    except Exception as e:
        print(f"API Error formatting data: {e}")
        traceback.print_exc()
        return jsonify({"error": "Error formatting data on server."}), 500

    return jsonify(output_json)

def get_strategy_parameter_definitions(strategy_name: str):
    """Retrieve parameter definitions for a given strategy."""
    try:
        strategy_class = get_strategy_class(strategy_name)
        
        if hasattr(strategy_class, 'get_parameter_definitions'):
            return strategy_class.get_parameter_definitions()
        else:
            print(f"Strategy {strategy_name} does not have parameter definitions")
            return []
            
    except (ValueError, ImportError, AttributeError) as e:
        print(f"Error loading strategy parameter definitions for '{strategy_name}': {e}")
        return []
    except Exception as e:
        print(f"Unexpected error loading strategy '{strategy_name}': {e}")
        return []

# NEW: Add endpoint to list all available strategies
@app.route('/api/strategies')
def get_available_strategies():
    """API endpoint to get all available strategy names."""
    try:
        strategies = list_available_strategies()
        return jsonify({
            'strategies': strategies,
            'count': len(strategies)
        })
    except Exception as e:
        return jsonify({'error': f'Failed to load strategies: {e}'}), 500

# Update the existing parameter endpoint to handle errors better
@app.route('/api/strategy_parameters/<strategy_name>')
def get_strategy_parameters(strategy_name):
    """API endpoint to get parameter definitions for a strategy."""
    try:
        param_defs = get_strategy_parameter_definitions(strategy_name)
        
        # Convert to JSON-serializable format
        param_data = []
        for param_def in param_defs:
            param_data.append({
                'name': param_def.name,
                'default_value': param_def.default_value,
                'ui_label': param_def.ui_label,
                'type': param_def.type,
                'description': param_def.description,
                'min_value': param_def.min_value,
                'max_value': param_def.max_value,
                'step': param_def.step,
                'choices': param_def.choices,
                'group': param_def.group
            })
        
        return jsonify({
            'strategy_name': strategy_name,
            'parameters': param_data
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to get parameters for strategy {strategy_name}: {e}',
            'available_strategies': list_available_strategies()
        }), 404

@app.route('/api/strategies_info', methods=['GET'])
def get_strategies_info():
    """
    API endpoint to get comprehensive information about all available strategies,
    including their parameter definitions.
    
    Returns:
        JSON response with list of strategy objects containing name and parameters
    """
    try:
        # Get all available strategy names
        strategy_names = list_available_strategies()
        strategies_info = []
        
        for strategy_name in strategy_names:
            try:
                # Get the strategy class
                strategy_class = get_strategy_class(strategy_name)
                
                # Get parameter definitions if available
                parameters = []
                if hasattr(strategy_class, 'get_parameter_definitions'):
                    param_defs = strategy_class.get_parameter_definitions()
                    
                    # Convert ParameterDefinition objects to JSON-serializable dictionaries
                    for param_def in param_defs:
                        parameters.append({
                            'name': param_def.name,
                            'default_value': param_def.default_value,
                            'ui_label': param_def.ui_label,
                            'type': param_def.type,
                            'description': param_def.description,
                            'min_value': param_def.min_value,
                            'max_value': param_def.max_value,
                            'step': param_def.step,
                            'choices': param_def.choices,
                            'group': param_def.group
                        })
                else:
                    print(f"Warning: Strategy '{strategy_name}' does not have parameter definitions")
                
                # Add strategy info to the list
                strategies_info.append({
                    'name': strategy_name,
                    'parameters': parameters
                })
                
            except Exception as e:
                print(f"Error loading strategy '{strategy_name}': {e}")
                # Add strategy with error info for debugging
                strategies_info.append({
                    'name': strategy_name,
                    'parameters': [],
                    'error': f"Failed to load strategy: {e}"
                })
        
        return jsonify({
            'strategies': strategies_info,
            'total_count': len(strategies_info)
        })
        
    except Exception as e:
        print(f"Error in get_strategies_info: {e}")
        return jsonify({
            'error': f'Failed to retrieve strategies information: {e}',
            'strategies': []
        }), 500

@app.route('/api/data_files', methods=['GET'])
def get_data_files():
    """
    API endpoint to get list of available CSV data files.
    
    Returns:
        JSON response with list of CSV filenames in the data/ directory
    """
    try:
        # Get the project root directory (parent of src)
        project_root = Path(__file__).resolve().parent.parent
        data_dir = project_root / 'data'
        
        # Check if data directory exists
        if not data_dir.exists():
            return jsonify({
                'error': 'Data directory not found',
                'data_files': [],
                'data_dir_path': str(data_dir)
            }), 404
        
        # Scan for CSV files
        csv_files = []
        for file_path in data_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() == '.csv':
                csv_files.append(file_path.name)
        
        # Sort files alphabetically for consistent ordering
        csv_files.sort()
        
        return jsonify({
            'data_files': csv_files,
            'count': len(csv_files),
            'data_dir_path': str(data_dir)
        })
        
    except Exception as e:
        print(f"Error scanning data directory: {e}")
        return jsonify({
            'error': f'Failed to scan data directory: {e}',
            'data_files': []
        }), 500

@app.route('/api/run_single_backtest', methods=['POST'])
def run_single_backtest():
    """
    Receives backtest parameters, logs them, and returns an immediate
    confirmation. In the future, this will queue the backtest.
    """
    try:
        if not request.json:
            return jsonify({'status': 'error', 'message': 'Invalid request: No JSON payload provided.'}), 400
        
        payload = request.json
        print("--- BACKEND RECEIVED NEW BACKTEST REQUEST ---")
        print(f"Received payload: {payload}")

        # --- Extract and Validate Parameters (more comprehensively) ---
        strategy_name = payload.get('strategy_name')
        strategy_params = payload.get('strategy_parameters', {}) # Expect parameters to be nested
        
        if not strategy_name:
            return jsonify({'status': 'error', 'message': '`strategy_name` is a required field.'}), 400

        # Extract a specific parameter for logging, e.g., p_fast_d0
        p_fast_d0_value = strategy_params.get('p_fast_d0')

        # --- Log the received data clearly on the backend console ---
        print("\n--- Parsed Configuration ---")
        print(f"Strategy: {strategy_name}")
        # Log the specific parameter you're testing
        print(f"Parameter 'p_fast_d0' received with value: {p_fast_d0_value}")
        # Log all received strategy parameters
        print(f"Full Strategy Params: {strategy_params}")
        print("--------------------------\n")

        # --- Placeholder for queuing logic ---
        # In the future, this is where you would:
        # 1. Generate a unique task_id.
        # 2. Add the `payload` and `task_id` to the in-memory queue.
        # 3. Add a new row to the SQLite database with the task_id and 'queued' status.
        # 4. Return the task_id to the user.

        # For this "little step", we just return success.
        task_id_placeholder = f"task_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

        return jsonify({
            'status': 'queued', # Use a more descriptive status for the future
            'message': f"Backtest for strategy '{strategy_name}' has been successfully queued. (This is a test response).",
            'task_id': task_id_placeholder # Return a placeholder task_id
        }), 202 # Use HTTP status 202 Accepted, which is standard for async tasks

    except Exception as e:
        print(f"ERROR in /api/run_single_backtest: {str(e)}")
        traceback.print_exc() # Print full traceback for better debugging
        return jsonify({'status': 'error', 'message': f'An unexpected server error occurred: {str(e)}'}), 500

if __name__ == '__main__':
    multiprocessing.freeze_support() # For Windows compatibility if using multiprocessing internally
    print("Starting Flask server and initial backtest simulation...")
    run_simulation_and_cache() # Run the backtest once when the server starts
    print("Initial simulation complete. Starting Flask development server...")
    app.run(host='127.0.0.1', port=5000, debug=True)