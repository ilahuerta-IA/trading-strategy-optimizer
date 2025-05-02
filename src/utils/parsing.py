# utils/parsing.py

def parse_kwargs_str(kwargs_str):
    """
    Safely parses a string like "key1=value1,key2=value2" into a dictionary.
    Attempts to convert values to numbers (int/float) if possible.
    Handles basic boolean strings ('true'/'false') and quoted strings.
    """
    parsed_kwargs = {}
    if not kwargs_str:
        return parsed_kwargs

    if kwargs_str == '{}': # Handle empty plot args special case
        return parsed_kwargs

    pairs = kwargs_str.split(',')
    for pair in pairs:
        pair = pair.strip()
        if not pair or '=' not in pair:
            # Skip empty pairs or pairs without '='
            if pair: print(f"Warning: Skipping malformed kwarg item (no '='): {pair}")
            continue
        try:
            key, value = pair.split('=', 1)
            key = key.strip()
            value = value.strip()

            # Attempt numeric conversion first
            try:
                if '.' in value:
                    parsed_kwargs[key] = float(value)
                else:
                    parsed_kwargs[key] = int(value)
            except ValueError:
                # Not numeric, check for boolean or keep as string
                lower_val = value.lower()
                if lower_val == 'true':
                    parsed_kwargs[key] = True
                elif lower_val == 'false':
                    parsed_kwargs[key] = False
                else:
                    # Handle quoted strings
                    if (value.startswith("'") and value.endswith("'")) or \
                       (value.startswith('"') and value.endswith('"')):
                        parsed_kwargs[key] = value[1:-1]
                    else:
                        # Keep as potentially meaningful string (e.g., 'SMA')
                        parsed_kwargs[key] = value

        except ValueError:
            # This might catch the split error if '=' wasn't present, but covered above
            print(f"Warning: Skipping malformed kwarg pair: {pair}")
            continue
    return parsed_kwargs