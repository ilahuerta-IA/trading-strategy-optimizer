# File: scripts/preprocess_data.py
"""
Script to preprocess raw CSV time-series data and save it in Parquet format.

Reads CSV files containing OHLCV data with separate Date and Time columns,
cleans them, standardizes column names, handles missing values, and saves
the processed DataFrame to the 'data/processed/' directory using the
more efficient Parquet format.
"""

import sys
import os
import pandas as pd

# --- Add project root to Python path ---
# Allows importing modules from 'src' if needed in the future,
# and helps locate the 'data' directory consistently.
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ---------------------------------------

# --- Configuration ---
# Base directory where raw data CSVs are located
input_data_dir = os.path.join(project_root, 'data')
# Directory where processed Parquet files will be saved
output_data_dir = os.path.join(project_root, 'data', 'processed')

# Dictionary mapping input CSV filenames to desired output Parquet filenames
# Add other files here as needed.
input_files_map = {
    'XAUUSD_M15_6Months.csv': 'XAUUSD_M15.parquet',
    'SPX500_M15_6Months.csv': 'SPX500_M15.parquet',
    # Add more files like:
    # 'EURUSD_H1_1Year.csv': 'EURUSD_H1.parquet',
}

# Datetime format expected in the CSV files (after combining Date and Time)
# Assumes CSV Date is like 'YYYY-MM-DD' and Time is like 'HH:MM:SS'
EXPECTED_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

# --- Ensure output directory exists ---
os.makedirs(output_data_dir, exist_ok=True)
print(f"Ensured output directory exists: {output_data_dir}")

# --- Processing Loop ---
print("\nStarting data preprocessing...")

for input_filename, output_filename in input_files_map.items():
    input_filepath = os.path.join(input_data_dir, input_filename)
    output_filepath = os.path.join(output_data_dir, output_filename)

    print(f"\nProcessing file: {input_filename}")

    # Check if input file exists
    if not os.path.exists(input_filepath):
        print(f"  WARNING: Input file not found: {input_filepath}. Skipping.")
        continue

    try:
        # 1. Load CSV using pandas
        print(f"  - Loading CSV: {input_filepath}")
        df = pd.read_csv(input_filepath, header=0)
        print(f"    - Initial shape: {df.shape}")

        # Check for required columns before proceeding
        required_cols = ['Date', 'Time', 'Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required_cols):
             missing = [col for col in required_cols if col not in df.columns]
             print(f"  ERROR: Missing required columns: {missing}. Skipping.")
             continue

        # 2. Combine Date and Time into a single DateTime index
        print("  - Combining Date and Time columns...")
        # Convert to string first to ensure consistent concatenation
        df['DateTime_str'] = df['Date'].astype(str) + ' ' + df['Time'].astype(str)
        # Convert to datetime objects using the specified format
        df['DateTime'] = pd.to_datetime(df['DateTime_str'], format=EXPECTED_DATETIME_FORMAT)
        # Set the new DateTime column as the index
        df.set_index('DateTime', inplace=True)
        print(f"    - Index type after conversion: {df.index.dtype}")

        # 3. Ensure standard OHLCV column names (lowercase)
        print("  - Renaming columns to lowercase...")
        df.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
            # Add more renames if input headers differ
        }, inplace=True)

        # 4. Add OpenInterest column if missing (set to 0)
        if 'openinterest' not in df.columns:
            print("  - Adding 'openinterest' column (initialized to 0.0)...")
            df['openinterest'] = 0.0
        else:
             # Ensure openinterest is numeric if it exists
             df['openinterest'] = pd.to_numeric(df['openinterest'], errors='coerce')


        # 5. Select and reorder final columns
        final_columns = ['open', 'high', 'low', 'close', 'volume', 'openinterest']
        print(f"  - Selecting final columns: {final_columns}")
        processed_df = df[final_columns].copy() # Create a copy to avoid SettingWithCopyWarning

        # 6. Handle potential missing values (NaNs)
        initial_nan_count = processed_df.isnull().sum().sum()
        if initial_nan_count > 0:
            print(f"  - Handling {initial_nan_count} missing values (NaNs)...")
            # Strategy: Forward fill first, then backfill (common for time series)
            processed_df.fillna(method='ffill', inplace=True)
            processed_df.fillna(method='bfill', inplace=True) # Backfill any remaining NaNs at the beginning
            remaining_nan_count = processed_df.isnull().sum().sum()
            if remaining_nan_count > 0:
                print(f"    - WARNING: {remaining_nan_count} NaNs remain after ffill/bfill. Dropping rows.")
                processed_df.dropna(inplace=True)
            else:
                 print("    - NaNs handled using forward/backward fill.")
        else:
            print("  - No missing values found.")


        # 7. Final Check and Info
        print("  - Final data structure check:")
        processed_df.info() # Prints summary including dtypes and non-null counts

        # 8. Save the processed DataFrame to Parquet format
        print(f"  - Saving processed data to Parquet: {output_filepath}")
        processed_df.to_parquet(output_filepath, engine='pyarrow') # 'pyarrow' is generally recommended
        print("    - Saved successfully.")

    except Exception as e:
        print(f"  ERROR processing {input_filename}: {e}")
        import traceback
        traceback.print_exc()
        print(f"  Skipping file {input_filename} due to error.")
        continue # Move to the next file

print("\nData preprocessing finished.")