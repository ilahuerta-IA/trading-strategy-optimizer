# visualization/custom_plotter.py
from lightweight_charts import Chart
import pandas as pd
# import numpy as np
import traceback
import time # For a small delay if needed

def plot_with_lightweight_charts(analysis_data, run_name="Backtest", data0_name="Data0", data1_name="Data1"):
    """
    Creates an interactive chart using lightweight-charts-python:
    - Subchart 1 (Top): Data1 Close (Real Data)
    - Main Chart (Middle): Data0 OHLC (Real Data)
    - Subchart 2 (Bottom): Portfolio Value (Real Data)
    Attempts to show the full time range.
    """
    print("Attempting plot with lightweight-charts using Top/Bottom subcharts...")

    # --- Extract Real Data ---
    datetimes = analysis_data.get('datetimes', [])
    values = analysis_data.get('values', [])
    d0_ohlc = analysis_data.get('d0_ohlc', {})
    d1_ohlc = analysis_data.get('d1_ohlc', {})

    # --- Basic Validation ---
    min_len = 10
    if (not datetimes or len(datetimes) < min_len or
        not d0_ohlc or not d0_ohlc.get('close') or len(d0_ohlc['close']) < min_len or
        not values or len(values) < min_len or
        not d1_ohlc or not d1_ohlc.get('close') or len(d1_ohlc['close']) < min_len):
        print("Lightweight Charts Plotter Warning: Missing or insufficient essential data.")
        return

    # --- Prepare DataFrames ---
    try:
        d0_df = pd.DataFrame({ 'time': pd.to_datetime(datetimes), 'open': d0_ohlc.get('open', []), 'high': d0_ohlc.get('high', []), 'low': d0_ohlc.get('low', []), 'close': d0_ohlc.get('close', []) })
        d0_df.dropna(subset=['time', 'open', 'high', 'low', 'close'], inplace=True)
        if d0_df.empty: raise ValueError("Data0 DataFrame is empty.")
        print(f"DEBUG: Real d0_df length: {len(d0_df)}")

        d1_line_name = f'{data1_name} Close'; d1_close = d1_ohlc.get('close', [])
        if len(datetimes) == len(d1_close): d1_line_df = pd.DataFrame({'time': pd.to_datetime(datetimes), d1_line_name: d1_close}); d1_line_df.dropna(inplace=True)
        else: print(f"LW Warning: Data1 length mismatch, skipping."); d1_line_df = pd.DataFrame()
        print(f"DEBUG: Real d1_line_df length: {len(d1_line_df)}")

        value_line_name = 'Portfolio Value'
        if len(datetimes) == len(values): value_line_df = pd.DataFrame({'time': pd.to_datetime(datetimes), value_line_name: values}); value_line_df.dropna(inplace=True)
        else: print(f"LW Warning: Value length mismatch, skipping."); value_line_df = pd.DataFrame()
        print(f"DEBUG: Real value_line_df length: {len(value_line_df)}")

    except Exception as e:
        print(f"Lightweight Charts Plotter Error creating DataFrames: {e}"); traceback.print_exc(); return

    # --- Create and Configure Chart ---
    try:
        top_subchart_height = 0.45
        main_chart_height = 0.45 # Give main chart more space
        bottom_subchart_height = 0.1

        chart = Chart(inner_width=1, inner_height=main_chart_height)
        chart.legend(visible=True)
        chart.layout(background_color='#131722', text_color='#D9D9D9')
        chart.grid(vert_enabled=True, horz_enabled=True, color='#3C4043')
        chart.candle_style(up_color='#26A69A', down_color='#EF5350', wick_up_color='#26A69A', wick_down_color='#EF5350', border_visible=False, wick_visible=True)
        chart.watermark(f'{data0_name} OHLC (Main)', color='rgba(180, 180, 180, 0.5)')

        subchart_1 = None; line_1 = None
        if not d1_line_df.empty:
            print("Creating subchart 1 (Top) for Data 1...")
            subchart_1 = chart.create_subchart(position='top', width=1.0, height=top_subchart_height, sync=True)
            line_1 = subchart_1.create_line(d1_line_name, color='orange', width=1, price_label=True)

        subchart_2 = None; line_2 = None
        if not value_line_df.empty:
             print("Creating subchart 2 (Bottom) for Portfolio Value...")
             subchart_2 = chart.create_subchart(position='bottom', width=1.0, height=bottom_subchart_height, sync=True)
             line_2 = subchart_2.create_line(value_line_name, color='green', width=2, style='dashed', price_label=True)

        # Set data
        print("Setting main chart data...")
        chart.set(d0_df)
        if subchart_1 and line_1 and not d1_line_df.empty: print("Setting data for subchart 1..."); line_1.set(d1_line_df)
        if subchart_2 and line_2 and not value_line_df.empty: print("Setting data for subchart 2..."); line_2.set(value_line_df)

        print("Displaying lightweight chart...")
        chart.show(block=False) # Show non-blocking to allow sending more commands
        print("Chart window opened (non-blocking).")

        # --- Attempt to adjust view AFTER chart is shown ---
        # Give the JS a moment to initialize the chart fully in the webview
        # This is a bit of a hack; a proper solution might involve JS callbacks
        # from the chart confirming it's ready.
        time.sleep(1) # Wait 1 second

        if not d0_df.empty:
            first_bar_index = 0 # The JS library uses logical bar indices
            # For the first bar visible, you can try to use a negative offset or a large negative number
            # to push the view as far left as possible.
            # However, let's try fitContent first as it's simpler.
            
            print("Attempting to fit content to view...")
            chart.fit() # Try this first

            # If fit() doesn't work, try scrolling to the first bar index.
            # The bar index for scrollToPosition is the logical index (0 for first bar, 1 for second, etc.)
            # It seems scrollToPosition might be for a different purpose or API version.
            # Let's focus on what the current Python wrapper definitely exposes.
            # The `set_visible_range` expects timestamps.
            
            # Get actual start and end times from the DataFrame that was set
            actual_start_time = d0_df['time'].iloc[0]
            actual_end_time = d0_df['time'].iloc[-1]
            print(f"Attempting chart.set_visible_range from {actual_start_time} to {actual_end_time}")
            try:
                chart.set_visible_range(actual_start_time, actual_end_time)
                print("set_visible_range command sent.")
            except Exception as e_svr:
                print(f"Error calling set_visible_range: {e_svr}")
        else:
            print("d0_df is empty, cannot set visible range.")


        print("Waiting for chart window to be closed by user (script will keep running)...")
        # Keep the script alive so the chart window doesn't close immediately
        # This is a common pattern if `chart.show(block=False)` is used.
        # The `chart.show_async()` with `asyncio.run()` is the more robust way.
        # For now, a simple loop or long sleep can work for testing.
        while chart.is_alive: # Check a flag that lightweight-charts sets
            time.sleep(0.1)
        print("Lightweight chart process seems to have ended or window closed.")

    except Exception as e:
        print(f"ERROR generating/displaying lightweight chart: {e}")
        traceback.print_exc()