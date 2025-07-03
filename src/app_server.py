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
import sqlite3
import json

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
    from worker import worker_main # Import the worker function
    from database import DB_FILE, init_db
except ImportError as e:
    print(f"Error importing project modules: {e}")
    print("Ensure app_server.py is in the 'src' directory or adjust Python path.")
    sys.exit(1)

# --- Keep track of the worker process and queue globally ---
task_queue = multiprocessing.Queue()
worker_process = None

# --- Initialize Flask App ---
# By explicitly setting the folder paths, we make the app more robust
# and ensure it can always find the CSS, JS, and HTML files.
app = Flask(__name__,
            static_folder='static',
            template_folder='templates')
CORS(app) # Enable CORS for all routes

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/api/chart_data', methods=['GET'])
def get_chart_data():
    """API endpoint to provide chart data and backtest report in JSON format."""
    # For now, return empty data structure since we're moving away from cached data
    # This endpoint will be updated to fetch data from database based on task_id
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

@app.route('/api/run_single_backtest', methods=['POST'])
def run_single_backtest():
    """Queues a backtest task and returns a task_id."""
    try:
        payload = request.json
        if not payload:
            return jsonify({'status': 'error', 'message': 'Invalid request: No JSON payload provided.'}), 400
        
        # 1. Generate a unique task_id
        task_id = f"task_{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        # 2. Add task to the database with 'queued' status
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        now = datetime.datetime.now().isoformat()
        cur.execute(
            "INSERT INTO backtest_tasks (task_id, status, payload, created_at) VALUES (?, ?, ?, ?)",
            (task_id, 'queued', json.dumps(payload), now)
        )
        con.commit()
        con.close()

        # 3. Put the task (id and payload) into the in-memory queue for the worker
        task_queue.put((task_id, payload))

        print(f"--- BACKEND QUEUED NEW TASK: {task_id} ---")

        # 4. Return the task_id to the user
        return jsonify({
            'status': 'queued',
            'message': f"Backtest for strategy '{payload.get('strategy_name')}' has been successfully queued.",
            'task_id': task_id
        }), 202

    except Exception as e:
        print(f"ERROR in /api/run_single_backtest: {str(e)}")
        traceback.print_exc() # Print full traceback for better debugging
        return jsonify({'status': 'error', 'message': f'An unexpected server error occurred: {str(e)}'}), 500

# --- Endpoint to check the status of a task ---
@app.route('/api/backtest_status/<task_id>', methods=['GET'])
def get_backtest_status(task_id):
    """Checks the status of a backtest task from the database."""
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row # This allows accessing columns by name
    cur = con.cursor()
    cur.execute("SELECT * FROM backtest_tasks WHERE task_id = ?", (task_id,))
    task_row = cur.fetchone()
    con.close()

    if task_row is None:
        return jsonify({'status': 'not_found', 'message': 'Task ID not found.'}), 404

    return jsonify(dict(task_row)) # Convert the row object to a dictionary

# Endpoint to get a list of all tasks
@app.route('/api/list_tasks', methods=['GET'])
def list_tasks():
    """Returns a list of all backtest tasks from the database."""
    try:
        con = sqlite3.connect(DB_FILE)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        # Fetch all tasks, newest first, without the giant result_json blob
        cur.execute("SELECT task_id, status, error_message, created_at, finished_at, payload FROM backtest_tasks ORDER BY created_at DESC")
        tasks = [dict(row) for row in cur.fetchall()]
        con.close()
        return jsonify(tasks)
    except Exception as e:
        print(f"ERROR in /api/list_tasks: {str(e)}")
        return jsonify({'error': f'Failed to fetch tasks: {str(e)}'}), 500

# Endpoint to get the full result for a completed task
@app.route('/api/get_result/<task_id>', methods=['GET'])
def get_result(task_id):
    """Returns the full result_json for a completed task."""
    try:
        con = sqlite3.connect(DB_FILE)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT result_json FROM backtest_tasks WHERE task_id = ? AND status = 'completed'", (task_id,))
        row = cur.fetchone()
        con.close()
        
        if row and row['result_json']:
            # The result is already a JSON string, so we can return it directly,
            # but it's better to parse it and re-jsonify to ensure it's valid.
            try:
                results_data = json.loads(row['result_json'])
                return jsonify(results_data)
            except json.JSONDecodeError:
                return jsonify({'error': 'Failed to parse stored result JSON.'}), 500
        else:
            return jsonify({'error': 'Result not found or task not completed.'}), 404
    except Exception as e:
        print(f"ERROR in /api/get_result/{task_id}: {str(e)}")
        return jsonify({'error': f'Failed to fetch result: {str(e)}'}), 500
    
# Endpoint to scan the 'data/' directory and return available CSV files
@app.route('/api/data_files', methods=['GET'])
def get_data_files():
    """
    Scans the 'data/' directory and returns a list of available CSV files.
    """
    try:
        data_dir = project_root / 'data'
        if not data_dir.is_dir():
            return jsonify({'error': 'Data directory not found on server.'}), 404
        
        # Find all files ending with .csv (case-insensitive)
        csv_files = [f.name for f in data_dir.glob('*.csv')]
        csv_files.sort() # Sort alphabetically for a consistent order
        
        return jsonify(csv_files)

    except Exception as e:
        print(f"Error scanning data directory: {e}")
        traceback.print_exc()
        return jsonify({'error': 'An error occurred while scanning for data files.'}), 500

if __name__ == '__main__':
    multiprocessing.freeze_support() # For Windows compatibility if using multiprocessing internally
    
    # --- OPTIONAL: Clear database on startup for fresh start ---
    print("Checking for existing database...")
    if Path(DB_FILE).exists():
        print(f"Removing old database file: {DB_FILE}")
        Path(DB_FILE).unlink() # This deletes the file
        print("✅ Old database cleared")
    else:
        print("No existing database found")
    # --- END OPTIONAL CLEARING ---

    # 1. Initialize the (now empty) database
    print("Initializing database...")
    init_db()

    # 2. Start the background worker process
    print("Starting background worker process...")
    worker_process = multiprocessing.Process(target=worker_main, args=(task_queue,))
    worker_process.start()
    
    # 3. Start the Flask development server
    print("Starting Flask development server...")
    app.run(host='127.0.0.1', port=5000, debug=False) # Important: Turn OFF debug mode when using multiprocessing

    # After app.run() finishes (e.g., Ctrl+C), we can clean up
    print("Shutting down worker process...")
    worker_process.terminate() # A simple way to stop it
    worker_process.join()