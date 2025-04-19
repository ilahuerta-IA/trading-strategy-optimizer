# File: app.py (Dash - CORRECTED Figure Creation Call)

import dash
from dash import dcc, html, Input, Output, State, Patch, callback_context, no_update
import dash_bootstrap_components as dbc
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import os
import numpy as np
from typing import List, Dict, Any, Tuple, Optional

# ==============================================================================
# Configuration (Keep as before)
# ==============================================================================
PROJECT_ROOT: str = os.path.dirname(__file__)
PROCESSED_DATA_DIR: str = os.path.join(PROJECT_ROOT, 'data', 'processed')
PLOTLY_THEME: str = "plotly_dark"
DEFAULT_BARS_TO_SHOW: int = 50
HIDE_PLOTLY_MODEBAR: bool = True

pio.templates.default = PLOTLY_THEME

# ==============================================================================
# Helper Functions (Keep as before)
# ==============================================================================
_data_cache = {}
def load_parquet_data(file_path: str) -> Optional[pd.DataFrame]:
    # (Keep function the same)
    _data_cache.clear();
    if not file_path or not os.path.exists(file_path): print(f"Error: Invalid file path: {file_path}"); return None
    try: df = pd.read_parquet(file_path); df.index = pd.to_datetime(df.index); df.sort_index(inplace=True); _data_cache[file_path] = df; print(f"LOADED: {os.path.basename(file_path)}, Shape: {df.shape}"); return df
    except Exception as e: print(f"Error loading {os.path.basename(file_path)}: {e}"); return None

def _annotation_defaults() -> Dict: return dict(align='center', valign='middle', font_size=16, showarrow=False, font=dict(color="grey"))

# --- Figure Creation (Accepts ONLY initial X range, adds rangebreaks) ---
def create_dual_subplot_figure(
    df1: Optional[pd.DataFrame], title1: str,
    df2: Optional[pd.DataFrame], title2: str,
    xaxis_range: Optional[List] = None # Accept initial X range only
) -> go.Figure:
    """Creates the Plotly figure with 2 subplots, applying initial X range and hiding weekends."""
    # This function definition is CORRECT - only accepts xaxis_range
    print(f"DEBUG [create_figure]: Args - XRange: {xaxis_range}")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06, subplot_titles=(title1, title2))

    # Add Traces
    if df1 is not None and not df1.empty: fig.add_trace(go.Candlestick(x=df1.index, open=df1['open'], high=df1['high'], low=df1['low'], close=df1['close'], name=title1, increasing_line_color='#2ECC71', decreasing_line_color='#E74C3C'), row=1, col=1)
    else: fig.add_annotation(text=f"{title1}: No data", row=1, col=1, **_annotation_defaults())
    if df2 is not None and not df2.empty: fig.add_trace(go.Candlestick(x=df2.index, open=df2['open'], high=df2['high'], low=df2['low'], close=df2['close'], name=title2, increasing_line_color='#2ECC71', decreasing_line_color='#E74C3C'), row=2, col=1)
    else: fig.add_annotation(text=f"{title2}: No data", row=2, col=1, **_annotation_defaults())

    # Layout Updates - Let Y autorange, apply X range, ADD rangebreaks
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
    for annotation in fig.layout.annotations: annotation.font.color = 'white'; annotation.font.size = 14
    print(f"DEBUG [create_figure]: Final Applied - X:{fig.layout.xaxis.range}, Y1: Autorange, Y2: Autorange")
    return fig

# ==============================================================================
# Data Discovery & App Init (Keep as before)
# ==============================================================================
# ... (find available_files code) ...
available_files = []
if os.path.exists(PROCESSED_DATA_DIR):
    try: available_files = sorted([f for f in os.listdir(PROCESSED_DATA_DIR) if f.endswith('.parquet') and not f.startswith('.')])
    except Exception as e: print(f"Error listing files: {e}")
if len(available_files) < 1: print("CRITICAL: No processed Parquet files found.")

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
server = app.server
print("DEBUG: Dash app initialized.")

# ==============================================================================
# App Layout (Simplified Sidebar - NO X/Y Controls)
# ==============================================================================
# ... (Keep layout the same - no Y controls) ...
print("DEBUG: Setting up app layout...")
app.layout = dbc.Container([
    dcc.Store(id='sidebar-state', data={'is_open': True}),
    dbc.Row([dbc.Col(html.H3("📈 Quant Bot Project: Dash Analysis Dashboard"), width=11, className="text-center my-3"), dbc.Col(dbc.Button("☰", id="sidebar-toggle-button", n_clicks=0, className="mt-3"), width=1)], align="center"),
    dbc.Row([
        dbc.Col([ # Sidebar
            html.H4("Controls"), html.Hr(),
            dbc.Label("Asset 1 (Top):"), dcc.Dropdown(id='asset-dropdown-1', options=[{'label': f.replace('.parquet',''), 'value': f} for f in available_files], value=available_files[0] if available_files else None, clearable=False, className="mb-3"),
            dbc.Label("Asset 2 (Bottom):"), dcc.Dropdown(id='asset-dropdown-2', options=[{'label': f.replace('.parquet',''), 'value': f} for f in available_files], value=available_files[1] if len(available_files) > 1 else None, clearable=False, className="mb-3"),
            html.Hr(), dbc.Label("Backtest (Placeholder):"), dbc.Button("Run Backtest", id="run-backtest-button", color="primary", className="mt-2", n_clicks=0, disabled=True)
        ], id="sidebar-column", width=12, lg=3, className="p-4 border rounded"),
        dbc.Col([ dcc.Graph(id='dual-subplot-chart', config={'displayModeBar': not HIDE_PLOTLY_MODEBAR}) ], id="main-content-column", width=12, lg=9)
    ])
], fluid=True)
print("DEBUG: App layout defined.")

# ==============================================================================
# Callbacks
# ==============================================================================

# --- Sidebar Toggle Callback (Keep this) ---
@app.callback(
    Output("sidebar-column", "width"), Output("sidebar-column", "lg"), Output("sidebar-column", "className"),
    Output("main-content-column", "width"), Output("main-content-column", "lg"), Output("sidebar-state", "data"),
    Input("sidebar-toggle-button", "n_clicks"), State("sidebar-state", "data"), prevent_initial_call=True
)
def toggle_sidebar(n_clicks: int, current_state: Dict) -> Tuple[int, int, str, int, int, Dict]:
    # (Logic remains the same)
    is_open = current_state.get('is_open', True); new_state = not is_open
    if new_state: return 12, 3, "p-4 border rounded", 12, 9, {'is_open': new_state}
    else: return 0, 0, "d-none", 12, 12, {'is_open': new_state}


# --- Main Figure Creation Callback (Corrected Call) ---
@app.callback(
    Output('dual-subplot-chart', 'figure'),
    Input('asset-dropdown-1', 'value'),
    Input('asset-dropdown-2', 'value'),
)
def create_figure_on_asset_change(selected_file_1: str, selected_file_2: str) -> go.Figure:
    """Creates/Recreates the figure ONLY when asset selection changes, applying initial zoom."""
    print(f"DEBUG [create_figure_on_asset_change]: Triggered. Asset 1='{selected_file_1}', Asset 2='{selected_file_2}'")
    _data_cache.clear()

    # Load Data
    df1, df2 = None, None; title_1, title_2 = "Select Asset 1", "Select Asset 2"
    try:
        if selected_file_1: df1 = load_parquet_data(os.path.join(PROCESSED_DATA_DIR, selected_file_1)); title_1 = f"{selected_file_1.replace('.parquet', '')}" if df1 is not None else "Error Load 1"
        if selected_file_2:
            if selected_file_1 == selected_file_2: title_2 = "Select Different Asset"
            else: df2 = load_parquet_data(os.path.join(PROCESSED_DATA_DIR, selected_file_2)); title_2 = f"{selected_file_2.replace('.parquet', '')}" if df2 is not None else "Error Load 2"
        print(f"DEBUG [create_figure_on_asset_change]: Data loaded. DF1: {df1 is not None}, DF2: {df2 is not None}")
    except Exception as e: print(f"!!! ERROR loading data: {e}"); return create_dual_subplot_figure(None, "Error", None, "Error")

    # Calculate Initial X Range
    initial_xaxis_range = None; available_dfs = [df for df in [df1, df2] if df is not None and not df.empty]
    if available_dfs:
        try:
            combined_index = pd.DatetimeIndex(np.unique(np.concatenate([df.index.values for df in available_dfs]))).sort_values()
            num_bars = DEFAULT_BARS_TO_SHOW
            if len(combined_index) >= num_bars: start = combined_index[-(min(num_bars, len(combined_index)))]; end = combined_index[-1]; initial_xaxis_range = [start, end]
            print(f"DEBUG [create_figure_on_asset_change]: Initial x-range: {initial_xaxis_range}")
        except Exception as e: print(f"Error calc initial x-range: {e}")
    else: print("DEBUG [create_figure_on_asset_change]: No data for initial x-range.")

    # --- Create the figure passing ONLY initial X range ---
    try:
        # ***** CORRECTED CALL HERE *****
        fig = create_dual_subplot_figure(df1, title_1, df2, title_2, xaxis_range=initial_xaxis_range)
        # *******************************
        print("DEBUG [create_figure_on_asset_change]: Returning new figure.")
        return fig
    except Exception as e:
        print(f"!!! ERROR creating final figure: {e}")
        return go.Figure(layout=go.Layout(template=PLOTLY_THEME, title="Error Displaying Figure"))


# --- REMOVED Y-Zoom Callback ---

# ==============================================================================
# Run App
# ==============================================================================
if __name__ == '__main__':
    print("DEBUG: Starting Dash server...")
    app.run(debug=True)
    print("DEBUG: Dash server stopped.")