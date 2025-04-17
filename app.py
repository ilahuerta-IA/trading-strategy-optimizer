# File: app.py (Dash - Ensure Full Data in Trace)

import dash
from dash import dcc, html, Input, Output, State, Patch, callback_context, no_update, ClientsideFunction
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import os
import numpy as np

# --- Configuration ---
PROJECT_ROOT = os.path.dirname(__file__)
PROCESSED_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'processed')
Y_AXIS_PADDING_FACTOR = 0.05
PLOTLY_THEME = "plotly_dark"
INITIAL_BARS_TO_SHOW = 20 # Show ~20 bars initially

# --- Set Default Plotly Template ---
pio.templates.default = PLOTLY_THEME

# --- Helper Function to Load Data ---
def load_parquet_data(file_path):
    # (Keep function the same)
    # ... (previous code) ...
    if not file_path or not os.path.exists(file_path):
        print(f"Error: Invalid or non-existent file path: {file_path}")
        return None
    try:
        df = pd.read_parquet(file_path)
        if not isinstance(df.index, pd.DatetimeIndex):
             print(f"Warning: Data index for {os.path.basename(file_path)} is not DatetimeIndex. Converting.")
             df.index = pd.to_datetime(df.index)
        print(f"Loaded {os.path.basename(file_path)}, shape: {df.shape}")
        return df
    except Exception as e:
        print(f"Error loading Parquet file {os.path.basename(file_path)}: {e}")
        return None


# --- Function to Create Candlestick Figure ---
def create_candlestick_figure(df, title, xaxis_range=None, yaxis_range=None):
    # --- Ensure layout applies theme correctly ---
    layout = go.Layout(
        title=title, xaxis_title=None, yaxis_title="Price", height=400,
        hovermode="x unified", xaxis_rangeslider_visible=False,
        margin=dict(l=50, r=50, t=50, b=50), template=PLOTLY_THEME,
        plot_bgcolor='rgba(17, 17, 17, 1)', paper_bgcolor='rgba(17, 17, 17, 1)',
        font=dict(color='white'),
        xaxis=dict(gridcolor='rgba(255, 255, 255, 0.1)', linecolor='rgba(255, 255, 255, 0.2)', zerolinecolor='rgba(255, 255, 255, 0.2)', range=xaxis_range), # Apply initial range here
        yaxis=dict(gridcolor='rgba(255, 255, 255, 0.1)', linecolor='rgba(255, 255, 255, 0.2)', zerolinecolor='rgba(255, 255, 255, 0.2)', range=yaxis_range)   # Apply initial range here
    )
    fig = go.Figure(layout=layout)

    if df is None or df.empty:
        # Make sure empty figure still uses dark theme
        fig.add_annotation(text="No data loaded.", align='center', valign='middle', font_size=20, showarrow=False, font=dict(color="white"))
        fig.update_layout(template=PLOTLY_THEME, plot_bgcolor='rgba(17,17,17,1)', paper_bgcolor='rgba(17,17,17,1)')
        return fig

    # --- CRUCIAL: Add trace using the FULL dataframe 'df' ---
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        name=title.replace(' Candlestick',''),
        increasing_line_color='#2ECC71', decreasing_line_color='#E74C3C'
    ))
    # ---------------------------------------------------------

    # --- Calculate Y-axis range ONLY if not provided ---
    # Calculate based on the VISIBLE x-axis range for better initial zoom
    if yaxis_range is None:
        visible_df = df # Assume full df initially
        if xaxis_range and len(xaxis_range) == 2:
            # Filter df to visible range for y-axis calculation
            try:
                 # Use pandas slicing for datetime index
                 visible_df = df[xaxis_range[0]:xaxis_range[1]]
            except Exception as e:
                 print(f"Warning: Could not filter dataframe for y-axis calculation based on x-range {xaxis_range}. Using full data range. Error: {e}")
                 visible_df = df # Fallback to full df if filtering fails

        if not visible_df.empty:
            min_low = visible_df['low'].min()
            max_high = visible_df['high'].max()
            padding = (max_high - min_low) * Y_AXIS_PADDING_FACTOR
            if padding < (max_high * 0.01) or np.isclose(padding, 0): # Check for close to zero padding
                padding = max(max_high * 0.01, 1.0) # Ensure some minimum padding
            yaxis_range_calc = [min_low - padding, max_high + padding]
            fig.update_layout(yaxis_range=yaxis_range_calc) # Update yaxis range based on visible data
            # print(f"Calculated yaxis range for '{title}': {yaxis_range_calc}")
        else:
             print(f"Warning: No visible data in range {xaxis_range} for '{title}' to calculate Y range.")
             # Let Plotly auto-range Y axis if visible_df is empty after filtering
             fig.update_layout(yaxis_range=None)


    return fig

# --- Find Available Data Files ---
# (Keep file finding logic as before)
available_files = []
if os.path.exists(PROCESSED_DATA_DIR):
    try:
        available_files = sorted([f for f in os.listdir(PROCESSED_DATA_DIR) if f.endswith('.parquet') and not f.startswith('.')])
    except Exception as e:
        print(f"Error listing files in {PROCESSED_DATA_DIR}: {e}")
if len(available_files) < 1: print("CRITICAL: No processed Parquet files found.")


# --- Initialize the Dash App ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
server = app.server

# --- App Layout ---
# (Keep layout the same as before)
app.layout = dbc.Container([
    # ... (rest of layout) ...
     dbc.Row(dbc.Col(html.H1("📈 Quant Bot Project: Dash Analysis Dashboard"), width=12, className="text-center my-4")),
    dbc.Row([
        dbc.Col([ # Sidebar
            html.H4("Controls"), html.Hr(),
            dbc.Label("Select Asset for Chart 1:"),
            dcc.Dropdown(id='asset-dropdown-1', options=[{'label': f.replace('.parquet',''), 'value': f} for f in available_files], value=available_files[0] if available_files else None, clearable=False, className="mb-3"),
            dbc.Label("Select Asset for Chart 2:"),
            dcc.Dropdown(id='asset-dropdown-2', options=[{'label': f.replace('.parquet',''), 'value': f} for f in available_files], value=available_files[1] if len(available_files) > 1 else None, clearable=False, className="mb-3"),
            html.Hr(), dbc.Label("Backtest Controls (Placeholder):"),
            dbc.Button("Run Backtest", id="run-backtest-button", color="primary", className="mt-2", n_clicks=0, disabled=True)
        ], width=12, lg=3, className="p-4 border rounded"),
        dbc.Col([ # Charts
            dbc.Row(dbc.Col(dcc.Graph(id={'type': 'synced-chart', 'index': 1}), width=12)),
            html.Hr(),
            dbc.Row(dbc.Col(dcc.Graph(id={'type': 'synced-chart', 'index': 2}), width=12))
        ], width=12, lg=9)
    ])
], fluid=True)


# --- Callbacks ---

# Callback to initially load/update figures AND set initial zoom
@app.callback(
    Output({'type': 'synced-chart', 'index': 1}, 'figure', allow_duplicate=True),
    Output({'type': 'synced-chart', 'index': 2}, 'figure', allow_duplicate=True),
    Input('asset-dropdown-1', 'value'),
    Input('asset-dropdown-2', 'value'),
    prevent_initial_call='initial_duplicate'
)
def update_charts_on_load_or_change(selected_file_1, selected_file_2):
    print(f"Load/Update triggered: Asset 1={selected_file_1}, Asset 2={selected_file_2}")

    # --- Load Data ---
    data_df_1, data_df_2 = None, None
    if selected_file_1:
        file_path_1 = os.path.join(PROCESSED_DATA_DIR, selected_file_1)
        data_df_1 = load_parquet_data(file_path_1)
    if selected_file_2 and selected_file_1 != selected_file_2:
        file_path_2 = os.path.join(PROCESSED_DATA_DIR, selected_file_2)
        data_df_2 = load_parquet_data(file_path_2)

    # --- Determine Initial Shared X-Axis Range (Last N Bars) ---
    initial_xaxis_range = None
    dfs_available = [df for df in [data_df_1, data_df_2] if df is not None and not df.empty]

    if dfs_available:
        try:
            latest_end = max(df.index[-1] for df in dfs_available)
            # Ensure we have enough data points to look back
            can_look_back = all(len(df) >= INITIAL_BARS_TO_SHOW for df in dfs_available)

            if can_look_back:
                 # Estimate start time based on intervals from the latest end
                 # Assuming M15 data. If using different TFs, this needs adjustment.
                 interval_minutes = 15
                 start_dt_calc = latest_end - pd.Timedelta(minutes=interval_minutes * (INITIAL_BARS_TO_SHOW - 1))

                 # Ensure start is not before the actual beginning of *any* dataset
                 earliest_start = min(df.index[0] for df in dfs_available)
                 start_dt = max(start_dt_calc, earliest_start)
                 initial_xaxis_range = [start_dt, latest_end]
                 print(f"Calculated initial shared x-range: {initial_xaxis_range}")
            else:
                 print("Not enough data points in one or both dataframes to show initial bars. Defaulting to auto range.")
                 # Fallback to Plotly's auto range if not enough data
                 initial_xaxis_range = None

        except Exception as e:
            print(f"Error calculating initial x-range: {e}. Defaulting to auto range.")
            initial_xaxis_range = None
    else:
        print("No valid dataframes to calculate initial range.")

    # --- Create Figures with Initial Range ---
    # Pass the FULL dataframes and the calculated initial x-range
    title_1 = f"{selected_file_1.replace('.parquet', '')} Candlestick" if selected_file_1 else "Select Asset 1"
    fig1 = create_candlestick_figure(data_df_1, title_1, xaxis_range=initial_xaxis_range) # Pass FULL df

    title_2 = f"{selected_file_2.replace('.parquet', '')} Candlestick" if selected_file_2 else "Select Asset 2"
    if selected_file_1 == selected_file_2 and selected_file_1 is not None:
         title_2 = "Select Different Asset 2"
         fig2 = create_candlestick_figure(None, title_2)
    else:
         # Pass the FULL dataframe and the initial x-range
         fig2 = create_candlestick_figure(data_df_2, title_2, xaxis_range=initial_xaxis_range)

    print(f"Returning initial figures.")
    return fig1, fig2


# --- Client-Side Callback for Synchronization ---
# (Keep this exactly the same as the previous working JS version in assets/clientside.js)
# It should return the full figure object for the target chart.
app.clientside_callback(
    ClientsideFunction(namespace='clientside', function_name='syncAxes'),
    Output({'type': 'synced-chart', 'index': 1}, 'figure', allow_duplicate=True),
    Output({'type': 'synced-chart', 'index': 2}, 'figure', allow_duplicate=True),
    Input({'type': 'synced-chart', 'index': 1}, 'relayoutData'),
    Input({'type': 'synced-chart', 'index': 2}, 'relayoutData'),
    State({'type': 'synced-chart', 'index': 1}, 'figure'),
    State({'type': 'synced-chart', 'index': 2}, 'figure'),
    prevent_initial_call=True
)

# --- Run the App ---
if __name__ == '__main__':
    app.run(debug=True)