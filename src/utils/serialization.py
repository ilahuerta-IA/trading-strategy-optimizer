# src/utils/serialization.py - FINAL CORRECTED VERSION WITH TYPOS FIXED

import json
import datetime
import numpy as np

def clean_for_json(obj):
    """
    Recursively traverses a Python object and converts all non-JSON-compliant
    data types (datetime, numpy types, NaN, Infinity) into JSON-compliant ones.
    This function prepares the object to be safely passed to json.dumps.
    """
    if isinstance(obj, dict):
        # First, ensure keys are strings, then recurse on values
        return {str(k): clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        # Recurse on each item in the list/tuple
        return [clean_for_json(v) for v in obj]
    elif isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
                        np.int16, np.int32, np.int64, np.uint8,
                        np.uint16, np.uint32, np.uint64)):
        return int(obj)
    elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64, float)):
        # Handle all float types, including standard Python floats
        # FIX: Changed 'o' to 'obj' here
        if np.isnan(obj) or np.isinf(obj):
            return None  # Convert NaN and Infinity to None (which becomes JSON null)
        return float(obj)
    elif isinstance(obj, np.ndarray):
        # FIX: Changed 'o' to 'obj' here
        return clean_for_json(obj.tolist())
    elif isinstance(obj, (datetime.date, datetime.datetime)):
        # FIX: Changed 'o' to 'obj' here
        return obj.isoformat()
    # If the object is already a safe type, return it as is
    elif obj is None or isinstance(obj, (bool, int, str)):
        return obj
    
    # As a last resort, convert any other unknown type to a string
    return str(obj)


def json_dumps_safe(obj):
    """
    Takes a complex Python object, cleans it for JSON compatibility,
    and then dumps it to a JSON string.
    """
    # 1. First, run the object through our comprehensive cleaning function.
    cleaned_object = clean_for_json(obj)
    
    # 2. Now that the object is clean, a standard json.dumps call will work perfectly.
    return json.dumps(cleaned_object)