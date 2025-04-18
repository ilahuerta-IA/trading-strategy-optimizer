# File: app.py (Dash - Debugging Initial Figure Callback)

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
Y_AXIS_PADDING_FACTOR: float = 0.05
PLOTLY_THEME: str = "plotly_dark"
DEFAULT_BARS_TO_SHOW: int = 20
MIN_BARS: int = 5
MAX_BARS: int = 300
Y_ZOOM_FACTOR: float = 0.25
HIDE_PLOTLY_MODEBAR: bool = True

pio.templates.default = PLOTLY_THEME

# ==============================================================================
# Helper Functions (Keep as before)
# ==============================================================================
_data_cache = {}
def load_parquet_data(file_path: str) -> Optional[pd.DataFrame]:
    _data_cache.clear()
    if not file_path or not os.path.exists(file_path): print(f"Error: Invalid file path: {file_path}"); return None
    try:
        df = pd.read_parquet(file_path); df.index = pd.to_datetime(df.index); df.sort_index(inplace=True)
        _data_cache[file_path] = df; print(f"Loaded {os.path.basename(file_path)}, shape: {df.shape}"); return df
    except Exception as e: print(f"Error loading {os.path.basename(file_path)}: {e}"); return None

def _calculate_y_range(min_val: float, max_val: float) -> Optional[List[float]]:
    if min_val is None or max_val is None or not np.isfinite(min_val) or not np.isfinite(max_val): return None
    padding = (max_val - min_val) * Y_AXIS_PADDING_FACTOR
    if padding < (abs(max_val) * 0.01) or np.isclose(padding, 0): padding = max(abs(max_val) * 0.01, 1.0)
    return [min_val - padding, max_val + padding]

def _annotation_defaults() -> Dict: return dict(align='center', valign='middle', font_size=16, showarrow=False, font=dict(color="grey"))

# --- Base Figure Creation ---
def create_base_dual_subplot_figure(df1, title1, df2, title2) -> go.Figure:
    print("DEBUG: Entering create_base_dual_subplot_figure...")
    try:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, subplot_titles=(title1, title2))
        # Add Traces
        if df1 is not None and not df1.empty: fig.add_trace(go.Candlestick(x=df1.index, open=df1['open'], high=df1['high'], low=df1['low'], close=df1['close'], name=title1, increasing_line_color='#2ECC71', decreasing_line_color='#E74C3C'), row=1, col=1)
        else: fig.add_annotation(text=f"{title1}: No data", row=1, col=1, **_annotation_defaults())
        if df2 is not None and not df2.empty: fig.add_trace(go.Candlestick(x=df2.index, open=df2['open'], high=df2['high'], low=df2['low'], close=df2['close'], name=title2, increasing_line_color='#2ECC71', decreasing_line_color='#E74C3C'), row=2, col=1)
        else: fig.add_annotation(text=f"{title2}: No data", row=2, col=1, **_annotation_defaults())
        # Basic Layout
        fig.update_layout(
            height=750, hovermode="x unified", xaxis_rangeslider_visible=False,
            margin=dict(l=50, r=50, t=60, b=50), template=PLOTLY_THEME,
            plot_bgcolor='rgba(17, 17, 17, 1)', paper_bgcolor='rgba(17, 17, 17, 1)',
            font=dict(color='white'), showlegend=False,
            xaxis=dict(gridcolor='rgba(255, 255, 255, 0.1)', linecolor='rgba(255, 255, 255, 0.2)', autorange=True), # Start with autorange
            xaxis2=dict(showticklabels=False),
            yaxis=dict(title="Price 1", gridcolor='rgba(255, 255, 255, 0.1)', linecolor='rgba(255, 255, 255, 0.2)', autorange=True),
            yaxis2=dict(title="Price 2", gridcolor='rgba(255, 255, 255, 0.1)', linecolor='rgba(255, 255, 255, 0.2)', autorange=True)
        )
        print("DEBUG: Base figure created successfully.")
        return fig
    except Exception as e:
        print(f"!!! ERROR in create_base_dual_subplot_figure: {e}")
        # Return a minimal empty figure on error
        return go.Figure(layout=go.Layout(template=PLOTLY_THEME, title="Error Creating Figure"))


# ==============================================================================
# Data Discovery & App Init (Keep as before)
# ==============================================================================
available_files = []
if os.path.exists(PROCESSED_DATA_DIR):
    try: available_files = sorted([f for f in os.listdir(PROCESSED_DATA_DIR) if f.endswith('.parquet') and not f.startswith('.')])
    except Exception as e: print(f"Error listing files: {e}")
if len(available_files) < 1: print("CRITICAL: No processed Parquet files found.")

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
server = app.server

# ==============================================================================
# App Layout (Keep as before)
# ==============================================================================
app.layout = dbc.Container([
    dcc.Store(id='sidebar-state', data={'is_open': True}),
    # Removed intermediate stores
    dbc.Row([dbc.Col(html.H3("📈 Quant Bot Project: Dash Analysis Dashboard"), width=11, className="text-center my-3"), dbc.Col(dbc.Button("☰", id="sidebar-toggle-button", n_clicks=0, className="mt-3"), width=1)], align="center"),
    dbc.Row([
        dbc.Col([ # Sidebar
            html.H4("Controls"), html.Hr(),
            dbc.Label("Asset 1 (Top):"), dcc.Dropdown(id='asset-dropdown-1', options=[{'label': f.replace('.parquet',''), 'value': f} for f in available_files], value=available_files[0] if available_files else None, clearable=False, className="mb-3"),
            dbc.Label("Asset 2 (Bottom):"), dcc.Dropdown(id='asset-dropdown-2', options=[{'label': f.replace('.parquet',''), 'value': f} for f in available_files], value=available_files[1] if len(available_files) > 1 else None, clearable=False, className="mb-3"),
            html.Hr(), dbc.Label("Y-Axis Zoom:", className="fw-bold"), dbc.RadioItems(options=[{'label': 'Top', 'value': 1}, {'label': 'Bottom', 'value': 2}, {'label': 'Both', 'value': 0}], value=1, id="y-zoom-target-radio", inline=True, className="mb-2"),
            dbc.Row([dbc.Col(dbc.Button("In (+)", id="y-zoom-in-button", color="success", size="sm", n_clicks=0)), dbc.Col(dbc.Button("Out (-)", id="y-zoom-out-button", color="danger", size="sm", n_clicks=0)), dbc.Col(dbc.Button("Reset", id="y-zoom-reset-button", color="warning", size="sm", n_clicks=0))], className="mb-2"),
            html.Hr(), dbc.Label("Backtest (Placeholder):"), dbc.Button("Run Backtest", id="run-backtest-button", color="primary", className="mt-2", n_clicks=0, disabled=True)
        ], id="sidebar-column", width=12, lg=3, className="p-4 border rounded"),
        dbc.Col([ # Chart Area
            dcc.Graph(id='dual-subplot-chart', config={'displayModeBar': not HIDE_PLOTLY_MODEBAR})
        ], id="main-content-column", width=12, lg=9)
    ])
], fluid=True)

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
    is_open = current_state.get('is_open', True); new_state = not is_open
    if new_state: return 12, 3, "p-4 border rounded", 12, 9, {'is_open': new_state}
    else: return 0, 0, "d-none", 12, 12, {'is_open': new_state}


# --- Main Figure Creation Callback (Triggered ONLY by Dropdowns) ---
@app.callback(
    Output('dual-subplot-chart', 'figure'),
    Input('asset-dropdown-1', 'value'),
    Input('asset-dropdown-2', 'value'),
    # State('bars-input', 'value') # Temporarily remove dependency
)
#def create_figure_on_asset_change(selected_file_1: str, selected_file_2: str, initial_bars: int) -> go.Figure:
def create_figure_on_asset_change(selected_file_1: str, selected_file_2: str) -> go.Figure:
    """Creates/Recreates the figure ONLY when asset selection changes, applying initial zoom."""
    print(f"DEBUG: Asset change triggered: Asset 1={selected_file_1}, Asset 2={selected_file_2}")
    # Clear cache to reload
    _data_cache.clear()
    # initial_bars = initial_bars or DEFAULT_BARS_TO_SHOW # Use default if None

    # --- Load Data ---
    df1, df2 = None, None
    title_1 = "Select Asset 1"
    title_2 = "Select Asset 2"
    try:
        if selected_file_1:
            file_path_1 = os.path.join(PROCESSED_DATA_DIR, selected_file_1)
            df1 = load_parquet_data(file_path_1)
            title_1 = f"{selected_file_1.replace('.parquet', '')}" if df1 is not None else "Error Loading Asset 1"
        if selected_file_2:
            if selected_file_1 == selected_file_2: title_2 = "Select Different Asset"
            else:
                file_path_2 = os.path.join(PROCESSED_DATA_DIR, selected_file_2)
                df2 = load_parquet_data(file_path_2)
                title_2 = f"{selected_file_2.replace('.parquet', '')}" if df2 is not None else "Error Loading Asset 2"
        print(f"DEBUG: Data loaded. DF1 valid: {df1 is not None and not df1.empty}, DF2 valid: {df2 is not None and not df2.empty}")
    except Exception as e:
        print(f"!!! ERROR during data loading phase in callback: {e}")
        # Return an empty figure indicating error
        return create_base_dual_subplot_figure(None, "Error Loading Data", None, "Error Loading Data")

    # --- Calculate Initial X Range ---
    initial_xaxis_range = None
    available_dfs = [df for df in [df1, df2] if df is not None and not df.empty]
    if available_dfs:
        try:
            combined_index = pd.DatetimeIndex(np.unique(np.concatenate([df.index.values for df in available_dfs]))).sort_values()
            num_bars = DEFAULT_BARS_TO_SHOW # Use fixed default for now
            if len(combined_index) >= num_bars:
                start = combined_index[-(min(num_bars, len(combined_index)))]
                end = combined_index[-1]
                initial_xaxis_range = [start, end]
            print(f"DEBUG: Calculated initial x-range: {initial_xaxis_range}")
        except Exception as e: print(f"Error calc initial x-range: {e}")

    # --- Calculate Initial Y Ranges ---
    yaxis_range1, yaxis_range2 = None, None
    if initial_xaxis_range: # Only calculate if X range is valid
        visible_df1, visible_df2 = df1, df2
        try:
            start_dt, end_dt = initial_xaxis_range
            if df1 is not None: visible_df1 = df1.loc[start_dt:end_dt]
            if df2 is not None: visible_df2 = df2.loc[start_dt:end_dt]
        except Exception as e: print(f"Warn: Filter error for Y zoom: {e}")
        if visible_df1 is not None and not visible_df1.empty: yaxis_range1 = _calculate_y_range(visible_df1['low'].min(), visible_df1['high'].max())
        if visible_df2 is not None and not visible_df2.empty: yaxis_range2 = _calculate_y_range(visible_df2['low'].min(), visible_df2['high'].max())
    print(f"DEBUG: Calculated initial Y-Ranges: Y1={yaxis_range1}, Y2={yaxis_range2}")


    # --- Create the figure with ALL calculated ranges ---
    try:
        fig = create_base_dual_subplot_figure(df1, title_1, df2, title_2)
        # Apply calculated ranges AFTER base figure creation
        fig.update_layout(xaxis_range=initial_xaxis_range, yaxis_range=yaxis_range1, yaxis2_range=yaxis_range2)
        print("DEBUG: Returning new figure from asset change.")
        return fig
    except Exception as e:
        print(f"!!! ERROR creating or updating final figure: {e}")
        # Return a minimal empty figure on error
        return go.Figure(layout=go.Layout(template=PLOTLY_THEME, title="Error Displaying Figure"))


# --- Callback for Y-Axis Zoom Buttons (Keep this - Patches existing figure) ---
@app.callback(
    Output('dual-subplot-chart', 'figure', allow_duplicate=True),
    Input('y-zoom-in-button', 'n_clicks'), Input('y-zoom-out-button', 'n_clicks'), Input('y-zoom-reset-button', 'n_clicks'),
    State('y-zoom-target-radio', 'value'), State('dual-subplot-chart', 'figure'),
    prevent_initial_call=True
)
def adjust_y_zoom_subplot(n_in: int, n_out: int, n_reset: int, target_chart: int, current_figure_state: Dict) -> Any:
    # (Keep logic the same - calculates new Y range and returns Patch)
    ctx = dash.callback_context; patch_fig = Patch(); update_needed = False
    if not ctx.triggered or not ctx.triggered[0]['value'] or not current_figure_state: return dash.no_update
    button_id = ctx.triggered_id; print(f"DEBUG: Y-Zoom Trigger: {button_id}, Target: {target_chart}")
    charts_to_update = [1] if target_chart == 1 else ([2] if target_chart == 2 else [1, 2])
    for chart_index in charts_to_update:
        axis_name = 'yaxis' if chart_index == 1 else 'yaxis2'; current_layout = current_figure_state.get('layout', {}); current_axis = current_layout.get(axis_name)
        if not current_axis: print(f"DEBUG: Y-Zoom Error: {axis_name} missing."); continue
        current_y_range = current_axis.get('range'); new_y_range = None # Default reset
        if button_id == 'y-zoom-reset-button': update_needed = True; print(f"DEBUG: Resetting {axis_name}")
        elif current_y_range and len(current_y_range) == 2:
            current_min, current_max = current_y_range; range_height = current_max - current_min
            if np.isclose(range_height, 0): print(f"DEBUG: Warn: {axis_name} range is zero."); continue
            zoom_amount = range_height * Y_ZOOM_FACTOR
            if button_id == 'y-zoom-in-button': new_y_range = [current_min + zoom_amount / 2, current_max - zoom_amount / 2]
            elif button_id == 'y-zoom-out-button': new_y_range = [current_min - zoom_amount / 2, current_max + zoom_amount / 2]
            if new_y_range and new_y_range[0] < new_y_range[1]: update_needed = True; print(f"DEBUG: Zooming {axis_name}: {new_y_range}")
            else: print(f"DEBUG: Warn: Invalid Y range calc for {axis_name}, resetting."); new_y_range = None; update_needed = True
        elif button_id != 'y-zoom-reset-button': print(f"DEBUG: Cannot calc zoom for {axis_name} (autorange?).")
        if update_needed: patch_fig['layout'][axis_name]['range'] = new_y_range; patch_fig['layout'][axis_name]['autorange'] = new_y_range is None
    return patch_fig if update_needed else dash.no_update


# ==============================================================================
# Run App
# ==============================================================================
if __name__ == '__main__':
    app.run(debug=True)