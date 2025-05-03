# visualization/custom_plotter.py
import plotly.graph_objects as go
# from plotly.subplots import make_subplots # Keep if needed later

def plot_backtest_data(analysis_data, run_name="Backtest", data0_name="Data0", data1_name="Data1"):
    """
    Creates a Plotly chart showing asset prices and portfolio value
    using multiple y-axes.
    """
    # Data extraction and validation
    datetimes = analysis_data.get('datetimes', [])
    values = analysis_data.get('values', [])
    d0_closes = analysis_data.get('d0_close', [])
    d1_closes = analysis_data.get('d1_close', [])
    if not datetimes or (not d0_closes and not d1_closes and not values):
        print("Custom Plotter Warning: Not enough valid data series for plotting.")
        return
    # Add length check if desired

    print("Generating custom plot with multiple axes...")
    fig = go.Figure()

    # --- Add Traces (remain the same) ---
    if d0_closes:
        fig.add_trace(go.Scatter(x=datetimes,
                                y=d0_closes,
                                mode='lines',
                                name=f'{data0_name} Close', 
                                yaxis='y1', 
                                line=dict(color='blue', width=1)))
    if d1_closes:
        fig.add_trace(go.Scatter(x=datetimes, 
                                y=d1_closes, 
                                mode='lines', 
                                name=f'{data1_name} Close', 
                                yaxis='y2', 
                                line=dict(color='orange', width=1)))
    if values:
        fig.add_trace(go.Scatter(x=datetimes, 
                                y=values, 
                                mode='lines', 
                                name='Portfolio Value', 
                                yaxis='y3', 
                                line=dict(color='green', width=2, dash='dash')))

    # Configure Layout with Multiple Axes
    fig.update_layout(
        title=f'{run_name} - Price & Portfolio Value Over Time',
        xaxis_title='Date',
        hovermode='x unified',

        # Define Y-axis 1 (Data0) - Left side
        yaxis=dict(
            title=dict(                     # Title is a dict
                text=f"{data0_name} Price", # Text inside title dict
                font=dict(color="blue")     # Font inside title dict
            ),
            tickfont=dict(color="blue")      # tickfont is separate
        ),

        # Define Y-axis 2 (Data1) - Right side
        yaxis2=dict(
            title=dict(                      # Title is a dict
                text=f"{data1_name} Price",  # Text inside title dict
                font=dict(color="orange")    # Font inside title dict
            ),
            tickfont=dict(color="orange"),   # tickfont is separate
            anchor="x",
            overlaying="y",
            side="right"
        ),

        # Define Y-axis 3 (Portfolio Value) - Right side, slightly shifted
        yaxis3=dict(
            title=dict(                       # Title is a dict
                text="Portfolio Value ($)",   # Text inside title dict
                font=dict(color="green")      # Font inside title dict
            ),
            tickfont=dict(color="green"),     # tickfont is separate
            anchor="free",
            overlaying="y",
            side="right",
            position=1.0 # Adjust position as needed (e.g., 0.95 might look better)
            # autoshift=True # Optional
        ),

        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            )
    )

    # Show the plot - Explicitly set renderer
    try:
        fig.show(renderer="browser")
        print("Custom plot display initiated via browser.")
    except Exception as e:
        print(f"ERROR displaying custom plot: {e}")
        print("Attempting static PNG rendering as fallback...")
        try:
            # Fallback: Try saving/showing as PNG (requires kaleido)
            fig.show(renderer="png", width=1200, height=700) # Requires kaleido
            print("Displayed static PNG fallback.")
        except Exception as e_png:
             print(f"ERROR displaying static PNG: {e_png}")
             print("Please ensure 'kaleido' is installed (`pip install -U kaleido`) for static image export.")