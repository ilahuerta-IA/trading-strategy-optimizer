# visualization/custom_plotter.py
# import plotly.graph_objects as go # Keep if plot_backtest_data is still present
from lightweight_charts import Chart
import pandas as pd
import traceback # For detailed error printing

# --- Keep the old Plotly function for reference if needed ---
# You can comment out or delete this entire function if you are
# only using lightweight-charts going forward.
def plot_backtest_data(analysis_data, run_name="Backtest", data0_name="Data0", data1_name="Data1", use_candlestick=False):
    """
    (DEPRECATED - Use plot_with_lightweight_charts)
    Creates a Plotly chart showing:
    - Data0 as Candlestick or Line (Left Y-axis) based on use_candlestick flag
    - Data1 as Line (Right Y-axis)
    - Portfolio Value as Line (Right Offset Y-axis)
    Attempts to remove weekend gaps from X-axis.
    """
    print("--- NOTE: plot_backtest_data (Plotly) is likely deprecated. Use plot_with_lightweight_charts. ---")
    # --- Data extraction ---
    # ... (Implementation using Plotly - kept for reference) ...
    # ... (Make sure necessary Plotly imports are present if uncommented) ...
    pass # Placeholder if function body removed


# --- Lightweight Charts Plotting Function with Subcharts ---
def plot_with_lightweight_charts(analysis_data, run_name="Backtest", data0_name="Data0", data1_name="Data1"):
    """
    Creates an interactive chart using lightweight-charts-python:
    - Main Chart: Data0 as Candles/OHLC
    - Subchart 1: Data1 Close as Line
    - Subchart 2: Portfolio Value as Line
    """
    print("Attempting plot with lightweight-charts using subcharts...")

    # --- Extract Data ---
    datetimes = analysis_data.get('datetimes', [])
    values = analysis_data.get('values', [])
    d0_ohlc = analysis_data.get('d0_ohlc', {})
    d1_ohlc = analysis_data.get('d1_ohlc', {})

    # --- Basic Validation ---
    # Check for presence and minimum length if desired
    min_len = 10 # Example minimum length
    if (not datetimes or len(datetimes) < min_len or
        not d0_ohlc or not d0_ohlc.get('close') or len(d0_ohlc['close']) < min_len or
        not values or len(values) < min_len or
        not d1_ohlc or not d1_ohlc.get('close') or len(d1_ohlc['close']) < min_len):
        print("Lightweight Charts Plotter Warning: Missing or insufficient essential data.")
        # Optionally check lengths match if strict alignment needed
        # if not (len(datetimes) == len(values) == len(d0_ohlc['close']) == len(d1_ohlc['close'])):
        #    print("Lightweight Charts Plotter Warning: Data lengths mismatch.")
        #    return # Or proceed carefully
        return


    # --- Prepare DataFrames ---
    try:
        # Main Data 0 (OHLC)
        d0_df = pd.DataFrame({
            'time': pd.to_datetime(datetimes),
            'open': d0_ohlc.get('open', []),
            'high': d0_ohlc.get('high', []),
            'low': d0_ohlc.get('low', []),
            'close': d0_ohlc.get('close', [])
        })
        # Drop rows where essential OHLC data might be NaN (or zero if that indicates missing)
        d0_df.dropna(subset=['time', 'open', 'high', 'low', 'close'], inplace=True)
        # Optional: Set time as index if preferred, though library handles 'time' column
        # d0_df.set_index('time', inplace=True)
        if d0_df.empty: raise ValueError("Data0 DataFrame is empty after processing.")
        print(f"DEBUG: d0_df length: {len(d0_df)}")

        # Data 1 Line (Needs 'time' and column matching line name)
        d1_line_name = f'{data1_name} Close'
        d1_close = d1_ohlc.get('close', [])
        if len(datetimes) == len(d1_close):
             d1_line_df = pd.DataFrame({'time': pd.to_datetime(datetimes), d1_line_name: d1_close})
             d1_line_df.dropna(inplace=True)
        else: d1_line_df = pd.DataFrame() # Will be empty if lengths mismatch
        if d1_line_df.empty: print("Lightweight Charts Plotter Warning: Data1 DataFrame is empty.")
        print(f"DEBUG: d1_line_df length: {len(d1_line_df)}")

        # Portfolio Value Line (Needs 'time' and column matching line name)
        value_line_name = 'Portfolio Value'
        if len(datetimes) == len(values):
            value_line_df = pd.DataFrame({'time': pd.to_datetime(datetimes), value_line_name: values})
            value_line_df.dropna(inplace=True)
        else: value_line_df = pd.DataFrame() # Will be empty if lengths mismatch
        if value_line_df.empty: print("Lightweight Charts Plotter Warning: Value DataFrame is empty.")
        print(f"DEBUG: value_line_df length: {len(value_line_df)}")

    except Exception as e:
        print(f"Lightweight Charts Plotter Error creating DataFrames: {e}")
        traceback.print_exc()
        return

    # --- Create and Configure Chart with Subcharts ---
    try:
        chart = Chart(width=1000, height=400) # Initial height for main pane
        chart.legend(visible=True)

        # Apply Styling
        chart.layout(background_color='#131722', text_color='#D9D9D9', font_size=12, font_family='Trebuchet MS')
        chart.grid(vert_enabled=True, horz_enabled=True, color='#3C4043')
        chart.candle_style(up_color='#26A69A', down_color='#EF5350', wick_up_color='#26A69A', wick_down_color='#EF5350', border_visible=False, wick_visible=True)
        chart.watermark(f'{run_name} - {data0_name}', color='rgba(180, 180, 180, 0.5)')

        # Set main data (Data 0 OHLC)
        chart.set(d0_df)

        # --- Create Subchart for Data 1 ---
        if not d1_line_df.empty:
            print("Creating subchart for Data 1...")
            # Adjust height fraction as needed
            subchart_d1 = chart.create_subchart(position='bottom', width=1.0, height=0.25, sync=True)
            subchart_d1.watermark(f'{data1_name}', color='rgba(180, 180, 180, 0.4)', font_size=16)
            # Create line ON THE SUBCHART
            line_d1 = subchart_d1.create_line(d1_line_name, color='orange', width=1, price_label=True)
            line_d1.set(d1_line_df)

        # --- Create Subchart for Portfolio Value ---
        if not value_line_df.empty:
             print("Creating subchart for Portfolio Value...")
             # Adjust height fraction as needed
             subchart_value = chart.create_subchart(position='bottom', width=1.0, height=0.25, sync=True)
             subchart_value.watermark('Portfolio Value', color='rgba(180, 180, 180, 0.4)', font_size=16)
             # Create line ON THE SUBCHART
             line_value = subchart_value.create_line(value_line_name, color='green', width=2, style='dashed', price_label=True)
             line_value.set(value_line_df)


        print("Displaying lightweight chart with subcharts...")
        # block=True pauses script until chart window closed
        # block=False opens chart and script continues (might exit too soon)
        chart.show(block=True)
        print("Lightweight chart closed.")

    except Exception as e:
        print(f"ERROR generating/displaying lightweight chart: {e}")
        traceback.print_exc()

