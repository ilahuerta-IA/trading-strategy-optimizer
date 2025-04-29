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