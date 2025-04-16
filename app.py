# File: app.py
"""
Streamlit application for the Quant Bot Project.

Allows selecting and viewing two preprocessed Parquet data files
as interactive candlestick charts, displayed one above the other,
with a synchronized initial time view.
"""

import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import numpy as np

# --- Configuration ---
PROJECT_ROOT = os.path.dirname(__file__)
PROCESSED_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'processed')
INITIAL_BARS_TO_SHOW = 50 # Number of recent bars to show by default in synchronized view
Y_AXIS_PADDING_FACTOR = 0.05 # Add 5% padding above max high and below min low

# --- Helper Function to Load Data (with Caching) ---
@st.cache_data
def load_parquet_data(file_path):
    """Loads a Parquet file into a Pandas DataFrame."""
    if not file_path or not os.path.exists(file_path):
        st.error(f"Error: Invalid or non-existent file path: {file_path}")
        return None
    try:
        df = pd.read_parquet(file_path)
        if not isinstance(df.index, pd.DatetimeIndex):
             st.warning(f"Data index for {os.path.basename(file_path)} is not DatetimeIndex. Attempting conversion.")
             df.index = pd.to_datetime(df.index)
        return df
    except FileNotFoundError: # Should be caught by os.path.exists, but belt-and-suspenders
        st.error(f"Error: File not found at {file_path}")
        return None
    except Exception as e:
        st.error(f"Error loading Parquet file {os.path.basename(file_path)}: {e}")
        return None

# --- Function to Create Candlestick Figure ---
def create_candlestick_figure(df, title, initial_xaxis_range=None):
    """Creates a Plotly Candlestick figure with specific initial ranges."""
    if df is None or df.empty:
        st.warning(f"No data provided for chart: {title}")
        return go.Figure() # Return an empty figure

    fig = go.Figure()

    # Add trace using the full dataframe passed
    fig.add_trace(go.Candlestick(x=df.index,
                                 open=df['open'],
                                 high=df['high'],
                                 low=df['low'],
                                 close=df['close'],
                                 name=title.replace(' Candlestick (M15)','')))

    # --- Calculate Y-axis range based ONLY on data within the initial X-axis range ---
    initial_yaxis_range = None
    if initial_xaxis_range and not df.empty:
        # Filter the dataframe to the visible time window
        visible_df = df[(df.index >= initial_xaxis_range[0]) & (df.index <= initial_xaxis_range[1])]
        if not visible_df.empty:
            min_low = visible_df['low'].min()
            max_high = visible_df['high'].max()
            padding = (max_high - min_low) * Y_AXIS_PADDING_FACTOR
            if padding < (max_high * 0.01): padding = max_high * 0.01
            if padding == 0: padding = 1.0
            initial_yaxis_range = [min_low - padding, max_high + padding]

    # --- Customize Layout ---
    fig.update_layout(
        title=title,
        xaxis_title=None, # Remove individual x-axis titles, use one below plots
        yaxis_title="Price",
        height=450, # Adjust height for two charts
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
        margin=dict(l=50, r=50, t=50, b=10), # Adjust margins
        xaxis_range=initial_xaxis_range, # Set initial horizontal zoom
        yaxis_range=initial_yaxis_range  # Set initial vertical zoom
    )
    return fig

# --- Streamlit App Layout ---

st.set_page_config(layout="wide")
st.title("📈 Quant Bot Project: Dual Asset Viewer")
st.markdown("Visualize two assets side-by-side with a synchronized initial time view.")

# --- Data Loading Section ---
st.sidebar.header("Data Selection")

available_files = []
if os.path.exists(PROCESSED_DATA_DIR):
    try:
        available_files = sorted([f for f in os.listdir(PROCESSED_DATA_DIR) if f.endswith('.parquet')])
    except Exception as e:
        st.sidebar.error(f"Error listing files in {PROCESSED_DATA_DIR}: {e}")
else:
    st.sidebar.warning(f"Processed data directory not found: {PROCESSED_DATA_DIR}")

if len(available_files) < 2:
    st.warning("Need at least two processed Parquet files in 'data/processed/' to display dual charts. "
               "Please run 'scripts/preprocess_data.py' if needed.")
    st.stop()

# --- Asset Selection for Two Charts ---
st.sidebar.markdown("### Chart 1 Asset")
selected_file_1 = st.sidebar.selectbox(
    "Select data for top chart:",
    options=available_files,
    index=0, # Default to the first file
    key="select_asset_1" # Unique key is important
)

st.sidebar.markdown("### Chart 2 Asset")
# Ensure default is different from chart 1 if possible
default_index_2 = 1 if len(available_files) > 1 else 0
if available_files[default_index_2] == selected_file_1 and len(available_files) > 1:
     default_index_2 = 0 # Fallback if second choice was same as first

selected_file_2 = st.sidebar.selectbox(
    "Select data for bottom chart:",
    options=available_files,
    index=default_index_2,
    key="select_asset_2" # Unique key
)

# Prevent selecting the same asset twice
if selected_file_1 == selected_file_2:
    st.warning("Please select two different assets for comparison.")
    st.stop()

# --- Load Data for Both Selected Assets ---
file_path_1 = os.path.join(PROCESSED_DATA_DIR, selected_file_1)
file_path_2 = os.path.join(PROCESSED_DATA_DIR, selected_file_2)

st.header(f"Comparing: {selected_file_1.replace('.parquet','')} vs {selected_file_2.replace('.parquet','')}")

data_df_1 = load_parquet_data(file_path_1)
data_df_2 = load_parquet_data(file_path_2)

# --- Create and Display Charts ---
if data_df_1 is not None and data_df_2 is not None:
    if data_df_1.empty or data_df_2.empty:
        st.warning("One or both selected datasets are empty.")
    else:
        # --- Determine Shared Initial X-Axis Range ---
        # Find the latest timestamp across both datasets
        latest_end_dt_1 = data_df_1.index[-1]
        latest_end_dt_2 = data_df_2.index[-1]
        combined_latest_end = max(latest_end_dt_1, latest_end_dt_2)

        # Calculate start time based on the combined latest end
        # Use timedelta for robustness against gaps
        start_dt = combined_latest_end - pd.Timedelta(minutes=15 * (INITIAL_BARS_TO_SHOW -1)) # -1 because N bars span N-1 intervals

        # Ensure start_dt is not before the actual start of either dataset
        earliest_start_dt_1 = data_df_1.index[0]
        earliest_start_dt_2 = data_df_2.index[0]
        combined_earliest_start = min(earliest_start_dt_1, earliest_start_dt_2)
        start_dt = max(start_dt, combined_earliest_start) # Don't go before the actual data begins

        shared_initial_xaxis_range = [start_dt, combined_latest_end]
        st.caption(f"Charts initially showing synchronized time window: {start_dt.strftime('%Y-%m-%d %H:%M')} to {combined_latest_end.strftime('%Y-%m-%d %H:%M')}")

        # --- Create Figures ---
        title1 = f"{selected_file_1.replace('.parquet', '')} Candlestick (M15)"
        fig1 = create_candlestick_figure(data_df_1, title1, shared_initial_xaxis_range)

        title2 = f"{selected_file_2.replace('.parquet', '')} Candlestick (M15)"
        fig2 = create_candlestick_figure(data_df_2, title2, shared_initial_xaxis_range)

        # --- Display Figures ---
        st.plotly_chart(fig1, use_container_width=True)
        st.plotly_chart(fig2, use_container_width=True)

        # Add a shared note about interaction
        st.caption("Use mouse wheel/pinch to zoom, click/drag to pan on individual charts. Initial view is time-synchronized.")

        # Expander for basic info remains optional
        with st.expander("Show Basic Data Info for Both Assets"):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader(f"Info: {selected_file_1}")
                st.metric("Rows", f"{data_df_1.shape[0]:,}")
                st.dataframe(data_df_1.head(3))
            with col2:
                st.subheader(f"Info: {selected_file_2}")
                st.metric("Rows", f"{data_df_2.shape[0]:,}")
                st.dataframe(data_df_2.head(3))


else:
    st.error("Failed to load data for one or both selected assets. Cannot display charts.")


# --- Footer ---
st.markdown("---")
st.markdown("End of dual asset viewer section.")