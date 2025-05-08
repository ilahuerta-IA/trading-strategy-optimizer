# test_lwc_subcharts.py
import pandas as pd
import numpy as np
from lightweight_charts import Chart
from datetime import datetime, timedelta
import traceback
import multiprocessing # Import multiprocessing

# --- Functions (Keep outside the main block) ---
# (No functions defined in this simple script yet, but good practice)


# --- Main Execution Block ---
if __name__ == '__main__': # <-- Add this condition
    multiprocessing.freeze_support() # <-- Add this line for Windows compatibility

    print(f"Pandas version: {pd.__version__}")
    print(f"Numpy version: {np.__version__}")

    # --- 1. Generate Simple Dummy Data ---
    print("Generating dummy data...")
    num_points = 500
    start_date = datetime(2023, 1, 1)
    time_index = [start_date + timedelta(days=i) for i in range(num_points)]

    # Main OHLC Data
    price_ohlc = np.linspace(100, 150, num_points) + np.random.randn(num_points).cumsum() * 0.5
    dummy_ohlc_data = {
        'time': time_index,
        'open': price_ohlc,
        'high': price_ohlc + np.random.rand(num_points) * 2,
        'low': price_ohlc - np.random.rand(num_points) * 2,
        'close': price_ohlc + np.random.randn(num_points) * 0.5
    }
    dummy_ohlc_data['high'] = np.maximum.reduce([dummy_ohlc_data['high'], dummy_ohlc_data['open'], dummy_ohlc_data['close']])
    dummy_ohlc_data['low'] = np.minimum.reduce([dummy_ohlc_data['low'], dummy_ohlc_data['open'], dummy_ohlc_data['close']])
    dummy_ohlc_df = pd.DataFrame(dummy_ohlc_data)
    dummy_ohlc_df.dropna(inplace=True)
    if dummy_ohlc_df.empty: raise ValueError("Dummy OHLC DataFrame empty.")
    print(f"DEBUG: dummy_ohlc_df length: {len(dummy_ohlc_df)}")

    # Subchart 1 Line Data
    line1_name = "Subchart 1 Indicator (Sine)"
    line1_values = np.sin(np.linspace(0, 8 * np.pi, num_points)) * 10 + 50
    dummy_line1_df = pd.DataFrame({'time': time_index, line1_name: line1_values})
    dummy_line1_df.dropna(inplace=True)
    if dummy_line1_df.empty: raise ValueError("Dummy Line 1 DataFrame empty.")
    print(f"DEBUG: dummy_line1_df length: {len(dummy_line1_df)}")

    # Subchart 2 Line Data
    line2_name = "Subchart 2 Indicator (Ramp)"
    line2_values = np.linspace(20, 80, num_points) + np.random.randn(num_points) * 3
    dummy_line2_df = pd.DataFrame({'time': time_index, line2_name: line2_values})
    dummy_line2_df.dropna(inplace=True)
    if dummy_line2_df.empty: raise ValueError("Dummy Line 2 DataFrame empty.")
    print(f"DEBUG: dummy_line2_df length: {len(dummy_line2_df)}")
    # --- End Dummy Data Generation ---


    # --- 2. Create Chart and Subcharts (Minimal Configuration) ---
    print("Creating chart objects...")
    try:
        chart = Chart(inner_width=1, inner_height=0.6)
        chart.set(dummy_ohlc_df)
        print("Main chart data set.")

        subchart1 = chart.create_subchart(position='top',width=1, height=0.2, sync=True)
        print("Subchart 1 object created.")
        line1 = subchart1.create_line(line1_name, color='cyan', width=2) # Use width=2 for visibility
        line1.set(dummy_line1_df)
        print("Line 1 data set on subchart 1.")

        subchart2 = chart.create_subchart(position='bottom', width=1, height=0.2)
        print("Subchart 2 object created.")
        line2 = subchart2.create_line(line2_name, color='magenta', width=2) # Use width=2
        line2.set(dummy_line2_df)
        print("Line 2 data set on subchart 2.")

        # --- 3. Show Chart ---
        print("Showing chart...")
        chart.show(block=True)
        print("Chart closed by user.")

    except Exception as e:
        print(f"\n--- AN ERROR OCCURRED ---")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Details: {e}")
        print("Traceback:")
        traceback.print_exc()
        print("------------------------")

    print("Test script finished.")