# File: app.py (Dash - FIXED SyntaxError, Stable Base, Hide Weekends)

import dash
from dash import dcc, html, Input, Output, State, callback_context, no_update
import dash_bootstrap_components as dbc
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import os
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import traceback

# ==============================================================================
# Configuration
# ==============================================================================
PROJECT_ROOT: str = os.path.dirname(__file__)
PROCESSED_DATA_DIR: str = os.path.join(PROJECT_ROOT, 'data', 'processed')
PLOTLY_THEME: str = "plotly_dark"
DEFAULT_BARS_TO_SHOW: int = 50
HIDE_PLOTLY_MODEBAR: bool = True

pio.templates.default = PLOTLY_THEME

# ==============================================================================
# Helper Functions
# ==============================================================================

# --- Data Loading ---
_data_cache = {}
def load_parquet_data(file_path: str) -> Optional[pd.DataFrame]:
    """Loads a Parquet file into a Pandas DataFrame, ensuring DatetimeIndex."""
    _data_cache.clear() # Simple cache clear
    if not file_path or not os.path.exists(file_path): print(f"Error: Invalid file path: {file_path}"); return None
    try:
        df = pd.read_parquet(file_path)
        if not isinstance(df.index, pd.DatetimeIndex): df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        _data_cache[file_path] = df
        print(f"LOADED: {os.path.basename(file_path)}, Shape: {df.shape}")
        return df.copy()
    except Exception as e: print(f"!!! ERROR loading Parquet file {os.path.basename(file_path)}: {e}"); return None

# --- Empty Plot Annotations ---
def _annotation_defaults() -> Dict:
    """Default settings for annotations on empty plots."""
    return dict(align='center', valign='middle', font_size=16, showarrow=False, font=dict(color="grey"))

# --- Y-Range Calculation ---
def _calculate_y_range(min_val: Optional[float], max_val: Optional[float]) -> Optional[List[float]]:
    """Calculates padded Y-axis range, returns None if invalid or for autorange."""
    y_axis_padding_factor = 0.05
    if min_val is None or max_val is None or not np.isfinite(min_val) or not np.isfinite(max_val): return None
    try:
        if np.isclose(min_val, max_val): padding = abs(max_val * 0.05) if not np.isclose(max_val, 0) else 1.0
        else: padding = (max_val - min_val) * y_axis_padding_factor
        if padding < (abs(max_val) * 0.01): padding = max(abs(max_val) * 0.01, 0.5)
        return [min_val - padding, max_val + padding]
    except Exception as e: print(f"!!! ERROR calculating Y range: {e}"); return None

# --- Figure Creation (Accepts ONLY initial X range, adds rangebreaks) ---
def create_dual_subplot_figure(
    df1: Optional[pd.DataFrame], title1: str,
    df2: Optional[pd.DataFrame], title2: str,
    xaxis_range: Optional[List] = None # Accept initial X range only
) -> go.Figure:
    """Creates the Plotly figure with 2 subplots, applying initial X range and hiding weekends."""
    print(f"DEBUG [create_figure]: Args - XRange: {xaxis_range}")
    fig = go.Figure() # Initialize empty figure for robustness
    try:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06, subplot_titles=(title1, title2))

        # Add Traces
        if df1 is not None and not df1.empty: fig.add_trace(go.Candlestick(x=df1.index, open=df1['open'], high=df1['high'], low=df1['low'], close=df1['close'], name=title1, increasing_line_color='#2ECC71', decreasing_line_color='#E74C3C'), row=1, col=1)
        else: fig.add_annotation(text=f"{title1}: No data", row=1, col=1, **_annotation_defaults())
        if df2 is not None and not df2.empty: fig.add_trace(go.Candlestick(x=df2.index, open=df2['open'], high=df2['high'], low=df2['low'], close=df2['close'], name=title2, increasing_line_color='#2ECC71', decreasing_line_color='#E74C3C'), row=2, col=1)
        else: fig.add_annotation(text=f"{title2}: No data", row=2, col=1, **_annotation_defaults())

        # Layout Updates - Let Y AUTORANGE, apply X range, ADD rangebreaks
        fig.update_layout(
            height=750, hovermode="x unified", xaxis_rangeslider_visible=False,
            margin=dict(l=50, r=50, t=60, b=50), template=PLOTLY_THEME,
            plot_bgcolor='rgba(17, 17, 17, 1)', paper_bgcolor='rgba(17, 17, 17, 1)',
            font=dict(color='white'), showlegend=False,
            xaxis=dict(gridcolor='rgba(255, 255, 255, 0.1)', linecolor='rgba(255, 255, 255, 0.2)', range=xaxis_range, autorange=xaxis_range is None, rangebreaks=[dict(bounds=["sat", "mon"])]), # Apply X range
            xaxis2=dict(showticklabels=False, rangeslider_visible=False, rangebreaks=[dict(bounds=["sat", "mon"])]), # Apply rangebreaks
            yaxis=dict(title="Price 1", gridcolor='rgba(255, 255, 255, 0.1)', linecolor='rgba(255, 255, 255, 0.2)', autorange=True), # Autorange Y1
            yaxis2=dict(title="Price 2", gridcolor='rgba(255, 255, 255, 0.1)', linecolor='rgba(255, 255, 255, 0.2)', autorange=True)  # Autorange Y2
        )
        # Style subplot titles
        for annotation in fig.layout.annotations: annotation.font.color = 'white'; annotation.font.size = 14
        print(f"DEBUG [create_figure]: Final Applied - X:{fig.layout.xaxis.range}, Y1: Autorange, Y2: Autorange")

    except Exception as e:
        print(f"!!! ERROR during figure creation/layout: {e}")
        # Return minimal error figure
        fig = go.Figure(layout=go.Layout(template=PLOTLY_THEME, title=f"Error Creating Figure: {e}"))
        fig.add_annotation(text="Error during figure update", **_annotation_defaults())

    return fig

# ==============================================================================
# Data Discovery & App Init
# ==============================================================================
print("DEBUG: Finding available data files...")
available_files = []
if os.path.exists(PROCESSED_DATA_DIR):
    try:
        available_files = sorted([f for f in os.listdir(PROCESSED_DATA_DIR) if f.endswith('.parquet') and not f.startswith('.')])
        print(f"DEBUG: Found files: {available_files}")
    except Exception as e: print(f"!!! ERROR listing files: {e}")
if not available_files: print("!!! WARNING: No processed Parquet files found.")

print("DEBUG: Initializing Dash app...")
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
server = app.server
print("DEBUG: Dash app initialized.")

# ==============================================================================
# App Layout (Simplified Sidebar)
# ==============================================================================
print("DEBUG: Setting up app layout...")
# --- Define Sidebar Content ---
sidebar_content = [
    html.H4("Controls"), html.Hr(),
    dbc.Label("Asset 1 (Top):"),
    dcc.Dropdown(id='asset-dropdown-1', options=[{'label': f.replace('.parquet',''), 'value': f} for f in available_files], value=available_files[0] if available_files else None, clearable=False, className="mb-3"),
    dbc.Label("Asset 2 (Bottom):"),
    dcc.Dropdown(id='asset-dropdown-2', options=[{'label': f.replace('.parquet',''), 'value': f} for f in available_files], value=available_files[1] if len(available_files) > 1 else None, clearable=False, className="mb-3"),
    html.Hr(), dbc.Label("Backtest (Placeholder):"),
    dbc.Button("Run Backtest", id="run-backtest-button", color="primary", className="mt-2", n_clicks=0, disabled=True)
]
# --- Assemble Final Layout ---
app.layout = dbc.Container([
    dcc.Store(id='sidebar-state', data={'is_open': True}),
    dbc.Row([dbc.Col(html.H3("📈 Quant Bot Project: Dash Analysis Dashboard"), width=11, className="text-center my-3"), dbc.Col(dbc.Button("☰", id="sidebar-toggle-button", n_clicks=0, className="mt-3"), width=1)], align="center"),
    dbc.Row([
        dbc.Col(sidebar_content, id="sidebar-column", width=12, lg=3, className="p-4 border rounded"), # Sidebar
        dbc.Col(dcc.Graph(id='dual-subplot-chart', config={'displayModeBar': not HIDE_PLOTLY_MODEBAR}), id="main-content-column", width=12, lg=9) # Chart Area
    ])
], fluid=True)
print("DEBUG: App layout defined.")

# ==============================================================================
# Callbacks
# ==============================================================================

# --- Sidebar Toggle Callback ---
@app.callback(
    Output("sidebar-column", "width"), Output("sidebar-column", "lg"), Output("sidebar-column", "className"),
    Output("main-content-column", "width"), Output("main-content-column", "lg"), Output("sidebar-state", "data"),
    Input("sidebar-toggle-button", "n_clicks"), State("sidebar-state", "data"), prevent_initial_call=True
)
def toggle_sidebar(n_clicks: int, current_state: Dict): # Removed Tuple return hint for simplicity
    print("DEBUG [toggle_sidebar]: Triggered.")
    is_open = current_state.get('is_open', True); new_state = not is_open
    if new_state: return 12, 3, "p-4 border rounded", 12, 9, {'is_open': new_state}
    else: return 0, 0, "d-none", 12, 12, {'is_open': new_state}


# --- Main Figure Creation Callback (Triggered ONLY by Dropdowns) ---
@app.callback(
    Output('dual-subplot-chart', 'figure'),
    Input('asset-dropdown-1', 'value'),
    Input('asset-dropdown-2', 'value'),
)
def create_figure_on_asset_change(selected_file_1: str, selected_file_2: str) -> go.Figure:
    """Creates/Recreates the figure ONLY when asset selection changes, applying initial zoom."""
    print(f"DEBUG [create_figure_on_asset_change]: Triggered. Asset 1='{selected_file_1}', Asset 2='{selected_file_2}'")
    _data_cache.clear() # Clear cache on asset change

    # --- Load Data ---
    df1, df2 = None, None
    title_1, title_2 = "Select Asset 1", "Select Asset 2"
    try:
        if selected_file_1:
            df1 = load_parquet_data(os.path.join(PROCESSED_DATA_DIR, selected_file_1))
            title_1 = f"{selected_file_1.replace('.parquet', '')}" if df1 is not None else "Error Load 1"
        if selected_file_2:
            if selected_file_1 == selected_file_2: title_2 = "Select Different Asset"
            else:
                df2 = load_parquet_data(os.path.join(PROCESSED_DATA_DIR, selected_file_2))
                title_2 = f"{selected_file_2.replace('.parquet', '')}" if df2 is not None else "Error Load 2"
        print(f"DEBUG [create_figure_on_asset_change]: Data loaded. DF1 valid: {df1 is not None}, DF2 valid: {df2 is not None}")
    except Exception as e:
        print(f"!!! ERROR during data loading phase in callback: {e}")
        # Pass error titles to figure creation
        return create_dual_subplot_figure(None, "Error Loading", None, "Error Loading")

    # --- Calculate Initial X Range ---
    initial_xaxis_range = None
    available_dfs = [df for df in [df1, df2] if df is not None and not df.empty]
    if available_dfs:
        try:
            # Combine index from available, non-empty dataframes
            combined_index = pd.DatetimeIndex(np.unique(np.concatenate([df.index.values for df in available_dfs]))).sort_values()
            num_bars = DEFAULT_BARS_TO_SHOW
            if len(combined_index) >= num_bars:
                # Select last N timestamps from the combined sorted index
                start = combined_index[-(min(num_bars, len(combined_index)))]
                end = combined_index[-1]
                initial_xaxis_range = [start, end]
            else: # Not enough data, show all available
                initial_xaxis_range = [combined_index[0], combined_index[-1]] if not combined_index.empty else None
            print(f"DEBUG [create_figure_on_asset_change]: Calculated initial x-range: {initial_xaxis_range}")
        except Exception as e:
            print(f"!!! ERROR calculating initial x-range: {e}")
            initial_xaxis_range = None # Fallback to autorange
    else:
        print("DEBUG [create_figure_on_asset_change]: No data available for initial x-range.")

    # --- Create the figure passing ONLY initial X range ---
    # Y ranges will be autoranged by the create function
    try:
        fig = create_dual_subplot_figure(df1, title_1, df2, title_2, xaxis_range=initial_xaxis_range)
        print("DEBUG [create_figure_on_asset_change]: Returning new figure.")
        return fig
    except Exception as e:
        print(f"!!! ERROR creating final figure: {e}")
        # Return minimal error figure
        error_layout = go.Layout(template=PLOTLY_THEME, title="Error Displaying Figure")
        error_fig = go.Figure(layout=error_layout)
        error_fig.add_annotation(text=f"Error: {e}", **_annotation_defaults())
        return error_fig

# ==============================================================================
# Run App
# ==============================================================================
if __name__ == '__main__':
    print("DEBUG: Starting Dash server...")
    app.run(debug=True)
    print("DEBUG: Dash server stopped.")