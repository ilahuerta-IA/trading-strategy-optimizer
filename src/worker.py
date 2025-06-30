# src/worker.py - NEW ROBUST VERSION WITHOUT DEBUG FILE EXPORT

import time
from queue import Empty
import multiprocessing
import sqlite3
import json
import datetime
import traceback
from pathlib import Path
import sys
import collections
import numpy as np
from pprint import pprint # Import for debugging

# --- Path setup ---
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

# --- Import project modules ---
try:
    from database import DB_FILE
    from backtesting.runner import setup_and_run_backtest, BacktestResult
    from utils.parsing import parse_kwargs_str
    from config import settings
except ImportError as e:
    print(f"Error importing project modules in worker: {e}")
    sys.exit(1)


def worker_main(task_queue):
    """Background worker process that processes backtest tasks from the queue."""
    print("Worker process started successfully")
    
    while True:
        try:
            print("Worker: Waiting for tasks...")
            task_id, payload = task_queue.get()
            print(f"Worker: Got task {task_id}")
            
            update_task_status(task_id, 'running')
            
            try:
                args = convert_payload_to_args(payload, task_id)
                print(f"Worker: Running backtest for task {task_id}")
                results = setup_and_run_backtest(args, parse_kwargs_str)
                
                if results:
                    # Direct serialization for database storage
                    results_json_string = json_dumps_safe(results.__dict__)
                    
                    update_task_status(task_id, 'completed', result_json=results_json_string)
                    print(f"Worker: Task {task_id} completed successfully")
                else:
                    update_task_status(task_id, 'failed', error_message='Backtest runner returned no results.')
                    
            except Exception as e:
                error_msg = f"Error during backtest execution: {e}"
                print(f"Worker: Task {task_id} failed with error: {error_msg}")
                traceback.print_exc()
                update_task_status(task_id, 'failed', error_message=error_msg)
                
        except (KeyboardInterrupt, SystemExit):
            print("Worker: Received interrupt signal, shutting down...")
            break
        except Exception as e:
            print(f"Worker: FATAL unexpected error: {e}")
            traceback.print_exc()

def json_dumps_safe(obj):
    """
    A robust JSON serializer that recursively handles all common edge cases
    from backtrader, numpy, and datetime objects.
    """
    def clean_data(o):
        if isinstance(o, dict):
            # Handle dictionary keys more carefully
            cleaned_dict = {}
            for k, v in o.items():
                # Convert keys to strings, but preserve the structure
                if isinstance(k, (datetime.date, datetime.datetime)):
                    key_str = k.isoformat()
                elif isinstance(k, (int, float, str)):
                    key_str = str(k)
                else:
                    key_str = str(k)  # Fallback for other types
                
                cleaned_dict[key_str] = clean_data(v)
            return cleaned_dict
            
        elif isinstance(o, (list, tuple)):
            return [clean_data(i) for i in o]
            
        # Handle numpy types
        elif isinstance(o, (np.int_, np.intc, np.intp, np.int8,
                            np.int16, np.int32, np.int64, np.uint8,
                            np.uint16, np.uint32, np.uint64)):
            return int(o)
            
        elif isinstance(o, (np.float_, np.float16, np.float32, np.float64)):
            # Explicitly check for NaN/inf and convert to None (JSON null)
            if np.isnan(o) or np.isinf(o):
                return None
            return float(o)
            
        elif isinstance(o, np.ndarray):
            # Convert numpy arrays to lists recursively
            return clean_data(o.tolist())
            
        # Handle standard Python types
        elif isinstance(o, (datetime.date, datetime.datetime)):
            return o.isoformat()
            
        elif isinstance(o, float) and (np.isnan(o) or np.isinf(o)):
            return None  # Handle standard float NaN/inf
            
        # Handle None, bool, int, str - these are JSON-safe
        elif o is None or isinstance(o, (bool, int, str)):
            return o
            
        else:
            # For any other type, convert to string representation
            return str(o)

    cleaned_obj = clean_data(obj)
    return json.dumps(cleaned_obj, indent=None)

def update_task_status(task_id, status, result_json=None, error_message=None):
    """Updates the status and result of a task in the database."""
    con = None
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        now = datetime.datetime.now().isoformat()
        if status == 'running':
            cur.execute("UPDATE backtest_tasks SET status = ?, started_at = ? WHERE task_id = ?", (status, now, task_id))
        elif status in ['completed', 'failed']:
            cur.execute("UPDATE backtest_tasks SET status = ?, finished_at = ?, result_json = ?, error_message = ? WHERE task_id = ?", (status, now, result_json, error_message, task_id))
        con.commit()
    except Exception as e:
        print(f"DATABASE ERROR: Failed to update task {task_id} status: {e}")
    finally:
        if con: con.close()

def convert_payload_to_args(payload, task_id):
    """Converts the JSON payload from the web API into an args object."""
    class Args: pass
    args = Args()
    args.strategy_name = payload.get('strategy_name', settings.DEFAULT_STRATEGY_NAME)
    data_files = payload.get('data_files', {})
    args.data_path_1 = str(project_root / 'data' / data_files.get('data_path_1', Path(settings.DEFAULT_DATA_PATH_1).name))
    args.data_path_2 = str(project_root / 'data' / data_files.get('data_path_2', Path(settings.DEFAULT_DATA_PATH_2).name))
    args.fromdate, args.todate = None, None
    strategy_params = payload.get('strategy_parameters', {})
    args.strat = ','.join([f"{key}={value}" for key, value in strategy_params.items()])
    args.broker, args.sizer, args.cerebro = settings.DEFAULT_BROKER_ARGS, settings.DEFAULT_SIZER_ARGS, settings.DEFAULT_CEREBRO_ARGS
    args.run_name, args.plot = task_id, False
    return args