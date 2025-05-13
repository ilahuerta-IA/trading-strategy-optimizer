# src/app_server.py
from flask import Flask, jsonify, render_template
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


# --- Imports from your project ---
# Ensure these paths are correct relative to how Python resolves them now
try:
    from backtesting.runner import setup_and_run_backtest, BacktestResult
    from config import settings
    from utils.parsing import parse_kwargs_str
except ImportError as e:
    print(f"Error importing project modules: {e}")
    print("Ensure app_server.py is in the 'src' directory or adjust Python path.")
    sys.exit(1)

# --- Global variable to store backtest results ---
CACHED_BACKTEST_DATA = None # This will store the value_analysis dictionary

# --- Initialize Flask App ---
# Flask automatically looks for 'templates' folder in the same dir as the app file.
# If app_server.py is in src/ and templates/ is in src/templates/, this is correct.
app = Flask(__name__)
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
            # Add any other arguments your parse_args in main.py might define as default
            # For example, if 'candlestick' was still there:
            # self.candlestick = False # Default for candlestick flag

    args = ArgsMock()

    # Ensure ValueCaptureAnalyzer is active and working in runner.py
    results_data_object = setup_and_run_backtest(args, parse_kwargs_func=parse_kwargs_str)

    if results_data_object and hasattr(results_data_object, 'value_analysis') and results_data_object.value_analysis:
        print("Flask Server: Simulation complete. Caching value_analysis data.")
        CACHED_BACKTEST_DATA = results_data_object.value_analysis
    else:
        print("Flask Server: Simulation failed or no 'value_analysis' data found in results.")
        print(f"Type of results_data_object: {type(results_data_object)}")
        if results_data_object:
            print(f"Has 'value_analysis' attr: {hasattr(results_data_object, 'value_analysis')}")
        CACHED_BACKTEST_DATA = None

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/api/chart_data', methods=['GET'])
def get_chart_data():
    """API endpoint to provide chart data in JSON format."""
    global CACHED_BACKTEST_DATA
    if CACHED_BACKTEST_DATA is None:
        print("API Error: Backtest data not cached.")
        return jsonify({"error": "Backtest data not available. Simulation might have failed or not run."}), 404

    output_json = {
        "data0_ohlc": [],
        "data1_line": [],
        "portfolio_value_line": [],
        "indicator_configs": [],
        "indicator_series": {},
        "trade_signals": []  # NUEVO: lista de señales buy/sell
    }
    try:
        datetimes = CACHED_BACKTEST_DATA.get('datetimes', [])
        times_sec = [dt.timestamp() for dt in datetimes] # UNIX timestamp in seconds


        # Data0 OHLC
        d0_ohlc_data = CACHED_BACKTEST_DATA.get('d0_ohlc', {})
        if times_sec and d0_ohlc_data.get('close'):
            # Ensure all OHLC lists have the same length as datetimes
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


        # Data1 Line
        d1_ohlc_data = CACHED_BACKTEST_DATA.get('d1_ohlc', {})
        d1_close_values = d1_ohlc_data.get('close', [])
        if times_sec and d1_close_values and len(times_sec) == len(d1_close_values):
            for i in range(len(times_sec)):
                output_json["data1_line"].append({"time": times_sec[i], "value": d1_close_values[i]})
        else:
            print("API Warning: Insufficient or mismatched data for Data1 line.")


        # Portfolio Value Line
        portfolio_values = CACHED_BACKTEST_DATA.get('values', [])
        if times_sec and portfolio_values and len(times_sec) == len(portfolio_values):
            for i in range(len(times_sec)):
                output_json["portfolio_value_line"].append({"time": times_sec[i], "value": portfolio_values[i]})
        else:
            print("API Warning: Insufficient or mismatched data for Portfolio Value line.")

         # Process and add indicator data
        indicator_configs = CACHED_BACKTEST_DATA.get('indicator_configs', [])
        indicator_series_data = CACHED_BACKTEST_DATA.get('indicators', {})

        output_json['indicator_configs'] = indicator_configs # Pass configs directly

        for internal_id, series_values in indicator_series_data.items():
            if times_sec and series_values and len(times_sec) == len(series_values):
                output_json['indicator_series'][internal_id] = [
                    {"time": times_sec[i], "value": series_values[i]} 
                    for i in range(len(times_sec))
                    if not np.isnan(series_values[i]) # Filter out NaNs for plotting
                ]
            else:
                print(f"API Warning: Mismatched lengths or no data for indicator {internal_id}")
        
        # --- NUEVO: Agregar señales buy/sell ---
        signals = CACHED_BACKTEST_DATA.get('signals', [])
        for sig in signals:
            # Convertir datetime ISO a timestamp para el plot
            try:
                ts = datetime.datetime.fromisoformat(sig['datetime']).timestamp()
            except Exception:
                ts = None
            output_json['trade_signals'].append({
                'type': sig.get('type'),
                'time': ts,
                'price': sig.get('price')
            })

    except Exception as e:
        print(f"API Error formatting data: {e}")
        traceback.print_exc()
        return jsonify({"error": "Error formatting data on server."}), 500

    # print(f"API: Sending {len(output_json['data0_ohlc'])} OHLC points, {len(output_json['data1_line'])} D1 points, {len(output_json['portfolio_value_line'])} Value points.")
    return jsonify(output_json)

if __name__ == '__main__':
    multiprocessing.freeze_support() # For Windows compatibility if using multiprocessing internally
    print("Starting Flask server and initial backtest simulation...")
    run_simulation_and_cache() # Run the backtest once when the server starts
    print("Initial simulation complete. Starting Flask development server...")
    # host='0.0.0.0' makes it accessible on your network (use 127.0.0.1 for local only)
    app.run(host='127.0.0.1', port=5000, debug=True)