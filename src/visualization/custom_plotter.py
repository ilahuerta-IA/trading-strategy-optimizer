# visualization/custom_plotter.py
import plotly.graph_objects as go
# from plotly.subplots import make_subplots # Keep if needed later

def plot_backtest_data(analysis_data, 
                    run_name="Backtest", 
                    data0_name="Data0", 
                    data1_name="Data1",
                    use_candlestick=False):
    """
    Creates a Plotly chart showing:
    - Data0 as Candlestick or Line (Left Y-axis) based on use_candlestick flag
    - Data1 as Line (Right Y-axis)
    - Portfolio Value as Line (Right Offset Y-axis)
    Attempts to remove weekend gaps from X-axis.
    """
    # --- Data extraction ---
    datetimes = analysis_data.get('datetimes', [])
    values = analysis_data.get('values', [])
    d0_ohlc = analysis_data.get('d0_ohlc', {}) # Get the OHLC dict
    d1_ohlc = analysis_data.get('d1_ohlc', {}) # Get the OHLC dict

    # --- Extract individual OHLC lists for convenience ---
    d0_open = d0_ohlc.get('open', [])
    d0_high = d0_ohlc.get('high', [])
    d0_low = d0_ohlc.get('low', [])
    d0_close = d0_ohlc.get('close', [])
    # Use d1_close for the line plot
    d1_close = d1_ohlc.get('close', [])

    # --- Basic validation ---
    if not datetimes or not d0_close or not d1_close or not values:
        print("Custom Plotter Warning: Missing essential data series for plotting.")
        return

    chart_type = "Candlestick" if use_candlestick else "Line"
    print(f"Generating custom plot with Data0 as {chart_type}...")
    fig = go.Figure()
    
    # --- Add Traces ---
    # Add Data0 Candlestick trace (Primary Y-axis: yaxis='y1' - LEFT)
    if use_candlestick:
        if all([d0_open, d0_high, d0_low, d0_close]): # Check if all OHLC lists are present and not empty
            fig.add_trace(go.Candlestick(
                x=datetimes, 
                open=d0_open, 
                high=d0_high, 
                low=d0_low, 
                close=d0_close,
                name=f'{data0_name} OHLC', 
                yaxis='y1'
            ))
        else: # Fallback if OHLC is missing
            print("Custom Plotter Warning: Candlestick style requested, but OHLC data incomplete. Plotting Close as line.")
            if d0_close:
                 fig.add_trace(go.Scatter(x=datetimes,
                                        y=d0_close,
                                        mode='lines',
                                        name=f'{data0_name} Close',
                                        yaxis='y1',
                                        line=dict(color='blue', width=1.5)))
    else: # Default to line plot if use_candlestick is False
        if d0_close:
             fig.add_trace(go.Scatter(
                 x=datetimes, 
                 y=d0_close, 
                 mode='lines', 
                 name=f'{data0_name} Close',
                 yaxis='y1', 
                 line=dict(color='blue', width=1.5)
             ))

    # Add Data1 Close trace (Secondary Y-axis: yaxis='y2' - RIGHT)
    if d1_close:
        fig.add_trace(go.Scatter(
            x=datetimes,
            y=d1_close,
            mode='lines',
            name=f'{data1_name} Close',
            yaxis='y2', # Assign to y2 (right)
            line=dict(color='orange', width=1.5)
        ))

    # Add Portfolio Value trace (Tertiary Y-axis: yaxis='y3' - RIGHT OFFSET)
    if values:
        fig.add_trace(go.Scatter(
            x=datetimes,
            y=values,
            mode='lines',
            name='Portfolio Value',
            yaxis='y3', # Assign to y3 (right offset)
            line=dict(color='green', width=2, dash='dash')
        ))

    # --- Configure Layout ---
    fig.update_layout(
        title=f'{run_name} - Candlestick & Value Over Time',
        xaxis_title='Date',
        hovermode='x unified',

        # --- X-Axis Configuration for Removing Gaps ---
        xaxis=dict(
            # Attempt to remove non-trading days (weekends, holidays)
            # This works best for daily or higher timeframes. May not be perfect for intraday.
            rangebreaks=[
                dict(bounds=["sat", "mon"]), # Hide weekends
            ],
            # Disable rangeslider for clarity (optional)
            rangeslider_visible=False
        ),

        # --- Y-Axes Configuration (remains the same as 3-axis setup) ---
        yaxis=dict( # Y1 (Left) - Data0 OHLC
            title=dict(text=f"{data0_name} Price",
            font=dict(color="blue")),
            tickfont=dict(color="blue"),
            side='left'
        ),
        yaxis2=dict( # Y2 (Right) - Data1 Close
            title=dict(text=f"{data1_name} Price", 
            font=dict(color="orange")),
            tickfont=dict(color="orange"),
            anchor="x", overlaying="y", side="right"
        ),
        yaxis3=dict( # Y3 (Right Offset) - Portfolio Value
            title=dict(text="Portfolio Value ($)", 
            font=dict(color="green")),
            tickfont=dict(color="green"),
            anchor="free", overlaying="y", side="right", position=0.95
        ),

        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            )
    )

    # --- Show the plot ---
    try:
        fig.show(renderer="browser")
        print("Custom plot display initiated via browser.")
    except Exception as e:
        print(f"ERROR displaying custom plot: {e}")
        