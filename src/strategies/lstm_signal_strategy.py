# lstm_signal_strategy.py

# -----------------------------------------------------------------------------
# DISCLAIMER:
# This software is for educational and research purposes only.
# It is not intended for live trading or financial advice.
# Trading in financial markets involves substantial risk of loss.
# Use at your own risk. The author assumes no liability for any losses.
# -----------------------------------------------------------------------------

import backtrader as bt
import joblib
import pandas as pd
import numpy as np
from pathlib import Path

# --- WARNING SUPPRESSION ---
import warnings
# --- MODIFIED: Suppress TensorFlow/Keras warnings instead of Transformers ---
warnings.filterwarnings("ignore", category=UserWarning)
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' # Suppress TensorFlow INFO/WARNING messages
# --- END WARNING SUPPRESSION ---

# --- GLOBAL PATH CONFIGURATION (MODIFIED) ---
try:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    MODELS_DIR = PROJECT_ROOT / 'src' / 'ml_models' # Assuming LSTM models are here
    
    # --- MODIFIED: Point to LSTM model and scaler files ---
    LSTM_MODEL_PATH = MODELS_DIR / 'lstm_eurusd_5m_close_only_v1.keras'
    LSTM_SCALER_PATH = MODELS_DIR / 'scaler_eurusd_5m_close_only_v1.pkl'
    
    DATA_PATH = PROJECT_ROOT / 'data' / 'EURUSD_5m_2Mon.csv'
    
    if not LSTM_MODEL_PATH.exists():
        print(f"FATAL: LSTM Model file not found at {LSTM_MODEL_PATH}")
        exit()
    if not LSTM_SCALER_PATH.exists():
        print(f"FATAL: LSTM Scaler file not found at {LSTM_SCALER_PATH}")
        exit()
    if not DATA_PATH.exists():
        print(f"FATAL: Data file not found at {DATA_PATH}")
        exit()
except Exception as e:
    print(f"FATAL: Could not determine project paths. Please run from the project root. Error: {e}")
    exit()

# --- HELPER FUNCTION (REMOVED) ---
# The 'create_time_features_for_window' function is no longer needed as the LSTM
# model was trained only on 'Close' prices and does not require time features.

# --- INDICATOR: AI PRICE PREDICTION (REPLACED WITH LSTM) ---
class LSTMPredictionIndicator(bt.Indicator):
    """
    Indicator that wraps a pre-trained Keras/TensorFlow LSTM model to predict
    the next closing price.
    """
    lines = ('prediction',)
    params = (
        ('model_path', str(LSTM_MODEL_PATH)),
        ('scaler_path', str(LSTM_SCALER_PATH)),
        # From Experiment 11: The LSTM model uses a window of 30 periods.
        ('window_size', 30), 
    )
    plotinfo = dict(subplot=False, plotname='AI Prediction (LSTM)')
    
    def __init__(self):
        super().__init__()
        
        # --- NEW: Import TF/Keras locally to keep namespace clean ---
        import tensorflow as tf

        # Load the pre-trained Keras model and the scaler
        self.scaler = joblib.load(self.p.scaler_path)
        self.model = tf.keras.models.load_model(self.p.model_path)
        
        # Set the minimum period required for the indicator to calculate
        self.addminperiod(self.p.window_size)

    def next(self):
        # 1. Get the required history of close prices (window_size)
        close_prices = np.array(self.data.close.get(size=self.p.window_size))
        
        # 2. Scale the data using the same scaler from training
        # Reshape for the scaler which expects a 2D array
        scaled_prices = self.scaler.transform(close_prices.reshape(-1, 1))
        
        # 3. Reshape the data for the LSTM model input
        # LSTM expects: (batch_size, timesteps, features)
        # Here: (1, 30, 1)
        input_data = scaled_prices.reshape(1, self.p.window_size, 1)
        
        # 4. Make the prediction (disable verbose output from Keras)
        prediction_scaled = self.model.predict(input_data, verbose=0)
        
        # 5. Inverse transform the prediction to get the real price value
        final_pred = self.scaler.inverse_transform(prediction_scaled)[0][0]
        
        # 6. Set the indicator's output line
        self.lines.prediction[0] = final_pred

# --- INDICATOR: ANGLE OF A LINE (Unchanged) ---
class AngleIndicator(bt.Indicator):
    lines = ('angle',)
    params = (('angle_lookback', 5), ('scale_factor', 50000),)
    plotinfo = dict(subplot=True, plotname='Angle (Degrees)')
    
    def __init__(self):
        self.addminperiod(self.p.angle_lookback)
        super().__init__()

    def next(self):
        rise = (self.data0[0] - self.data0[-self.p.angle_lookback + 1]) * self.p.scale_factor
        run = self.p.angle_lookback
        self.lines.angle[0] = np.degrees(np.arctan2(rise, run))

# --- MAIN TRADING STRATEGY (MODIFIED) ---
class MLSignalStrategy(bt.Strategy): # Renamed for generality
    params = (
        # These parameters are unchanged to ensure a fair comparison
        ('pred_smooth_period', 5),
        ('sma_momentum_period', 50),
        ('sma_long_term_period', 100),
        ('sma_short_term_period', 5),
        ('min_angle_for_entry', 55.0),
        ('max_abs_divergence_entry', 0.10),
        ('position_size', 10000),
    )

    def __init__(self):
        # --- MODIFIED: Instantiate the LSTMPredictionIndicator ---
        self.prediction = LSTMPredictionIndicator(self.data)
        
        # --- The rest of the strategy is IDENTICAL to the Transformer version ---
        self.smoothed_prediction = bt.indicators.SMA(self.prediction, period=self.p.pred_smooth_period)
        self.sma_short_term = bt.indicators.SMA(self.data.close, period=self.p.sma_short_term_period)
        self.sma_long_term = bt.indicators.SMA(self.data.close, period=self.p.sma_long_term_period)
        self.sma_momentum = bt.indicators.SMA(self.data.close, period=self.p.sma_momentum_period)
        self.smooth_cross_momentum = bt.indicators.CrossOver(self.smoothed_prediction, self.sma_momentum)
        
        # Angle Calculations
        self.angle_prediction = AngleIndicator(self.smoothed_prediction, angle_lookback=self.p.pred_smooth_period)
        self.angle_price = AngleIndicator(self.sma_short_term, angle_lookback=self.p.sma_short_term_period)
        
        # Min/Max Tracking Variables
        self.max_abs_divergence = 0.0
        self.min_abs_divergence = float('inf')

    def next(self):
        # --- This entire 'next' method is IDENTICAL to the Transformer version ---
        
        # Synchronization Gate
        if np.isnan(self.angle_prediction[0]) or np.isnan(self.angle_price[0]):
            return

        # Calculate Absolute Divergence and Update Min/Max
        divergence = self.angle_prediction[0] - self.angle_price[0]
        abs_divergence = abs(divergence)
        
        self.max_abs_divergence = max(self.max_abs_divergence, abs_divergence)
        if abs_divergence > 0:
            self.min_abs_divergence = min(self.min_abs_divergence, abs_divergence)

        # Exit Logic
        if self.position:
            if self.smooth_cross_momentum[0] < 0:
                self.close()
            return

        # Entry Conditions
        is_bullish_filter = (self.sma_long_term[0] < self.prediction[0] and self.sma_momentum[0] < self.prediction[0])
        is_strong_momentum = self.smoothed_prediction[0] > self.smoothed_prediction[-1]
        is_crossover_signal = self.smooth_cross_momentum[0] > 0
        is_steep_angle = self.angle_prediction[0] > self.p.min_angle_for_entry
        is_coherent_signal = abs_divergence < self.p.max_abs_divergence_entry

        # Trade Execution
        if is_bullish_filter and is_strong_momentum and is_crossover_signal and is_steep_angle and is_coherent_signal:
            print(f"--- BUY SIGNAL @ {self.data.datetime.date(0)} (Angle: {self.angle_prediction[0]:.2f}°, Abs Divergence: {abs_divergence:.2f}° < {self.p.max_abs_divergence_entry}°) ---")
            self.buy(size=self.p.position_size)
    
    def stop(self):
        """
        Called at the end of the backtest to print the final summary.
        """
        print("\n--- Backtest Finished (LSTM Model) ---")
        print(f"Final Portfolio Value: {self.broker.getvalue():.2f}")
        
        print("\n--- Absolute Divergence Angle Analysis ---")
        if self.min_abs_divergence == float('inf'):
            print("No divergence data was calculated.")
        else:
            print(f"  - Minimum Absolute Divergence Recorded: {self.min_abs_divergence:.2f}°")
            print(f"  - Maximum Absolute Divergence Recorded: {self.max_abs_divergence:.2f}°")
        print("----------------------------------------\n")

# --- Cerebro Execution (Unchanged) ---
if __name__ == '__main__':
    cerebro = bt.Cerebro(runonce=False)
    # --- MODIFIED: Add the general MLSignalStrategy ---
    cerebro.addstrategy(MLSignalStrategy)
    
    data = bt.feeds.GenericCSVData(
        dataname=str(DATA_PATH), dtformat=('%Y%m%d'), tmformat=('%H:%M:%S'),
        datetime=0, time=1, open=2, high=3, low=4, close=5, volume=6,
        timeframe=bt.TimeFrame.Minutes, compression=5)
    
    cerebro.adddata(data)
    cerebro.broker.setcash(100000.0)
    
    print("--- Running Backtest with LSTM Model ---")
    cerebro.run()
    
    # Optional: uncomment to see the plot.
    print("Generating Plot...")
    cerebro.plot(style='line')