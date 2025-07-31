import backtrader as bt
import torch
import joblib
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import timedelta

# --- WARNING SUPPRESSION ---
# Suppress common warnings from the libraries to keep the output clean.
import warnings
from transformers.utils import logging
logging.set_verbosity_error()
warnings.filterwarnings("ignore", category=UserWarning)
# --- END WARNING SUPPRESSION ---

# --- GLOBAL PATH CONFIGURATION ---
# Define project paths in one place for easy management.
try:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    MODELS_DIR = PROJECT_ROOT / 'src' / 'ml_models'
    DATA_PATH = PROJECT_ROOT / 'data' / 'EURUSD_5m_2Mon.csv'
    if not DATA_PATH.exists():
        print(f"FATAL: Data file not found at {DATA_PATH}")
        exit()
except Exception:
    print("FATAL: Could not determine project paths. Please run from the project root.")
    exit()

# --- HELPER FUNCTION ---
def create_time_features_for_window(dt_index: pd.DatetimeIndex) -> np.ndarray:
    """
    Generates time-based features (hour, day of week, etc.) required by the
    Time Series Transformer model for a given datetime index.
    """
    features = pd.DataFrame(index=dt_index)
    features['hour'] = (dt_index.hour / 23.0) - 0.5
    features['day_of_week'] = (dt_index.dayofweek / 6.0) - 0.5
    features['day_of_month'] = ((dt_index.day - 1) / 30.0) - 0.5
    features['month'] = ((dt_index.month - 1) / 11.0) - 0.5
    return features.values

# --- INDICATOR: AI PRICE PREDICTION  ---
class TransformerPredictionIndicator(bt.Indicator):
    """
    A custom Backtrader indicator that loads a pre-trained Time Series Transformer
    model to generate a price prediction for the next timestep on each bar.
    """
    lines = ('prediction',)
    params = (('models_dir', str(MODELS_DIR)),)
    plotinfo = dict(subplot=False, plotname='AI Prediction')
    
    def __init__(self):
        super().__init__()
        self.p.models_dir = Path(self.p.models_dir)
        from transformers import TimeSeriesTransformerConfig, TimeSeriesTransformerForPrediction
        with open(self.p.models_dir / 'model_config.json', 'r') as f:
            config = TimeSeriesTransformerConfig.from_dict(json.load(f))
        self.scaler = joblib.load(self.p.models_dir / 'target_scaler.pkl')
        self.model = TimeSeriesTransformerForPrediction(config)
        self.model.load_state_dict(torch.load(self.p.models_dir / 'best_transformer_model.pth', map_location='cpu'))
        self.model.eval()
        self.history_len = config.context_length + max(config.lags_sequence or [0])
        self.addminperiod(self.history_len)

    def next(self):
        datetimes = [self.data.num2date(self.data.datetime[-i]) for i in range(self.history_len)]
        datetimes.reverse(); dt_index = pd.to_datetime(datetimes)
        close_prices = np.array(self.data.close.get(size=self.history_len))
        scaled_prices = self.scaler.transform(close_prices.reshape(-1, 1)).flatten()
        past_time_features = torch.tensor(create_time_features_for_window(dt_index), dtype=torch.float32).unsqueeze(0)
        future_dt_index = pd.to_datetime([dt_index[-1] + timedelta(minutes=5)])
        future_time_features = torch.tensor(create_time_features_for_window(future_dt_index), dtype=torch.float32).unsqueeze(0)
        past_values = torch.tensor(scaled_prices, dtype=torch.float32).unsqueeze(0)
        past_observed_mask = torch.ones_like(past_values)
        with torch.no_grad():
            outputs = self.model.generate(past_values=past_values, past_time_features=past_time_features, past_observed_mask=past_observed_mask, future_time_features=future_time_features)
        final_pred = self.scaler.inverse_transform(outputs.sequences.mean(dim=1).cpu().numpy()[:, -1].reshape(-1, 1))[0][0]
        self.lines.prediction[0] = final_pred

# --- INDICATOR: ANGLE OF A LINE ---
class AngleIndicator(bt.Indicator):
    """
    Calculates the angle of an input data line over a lookback period.
    The angle (in degrees) indicates the steepness of the line's ascent or descent.
    """
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

# --- MAIN TRADING STRATEGY ---
class TransformerSignalStrategy(bt.Strategy):
    """
    A trend-following strategy that uses an AI prediction as a leading signal,
    confirmed by multiple momentum conditions and the steepness (angle) of the signal.
    """
    # --- STRATEGY PARAMETERS ---
    # All tunable variables are defined here for easy optimization and testing.
    params = (
        ('pred_smooth_period', 5),
        ('sma_momentum_period', 50),
        ('sma_long_term_period', 100),
        ('sma_short_term_period', 5),
        ('min_angle_for_entry', 85.0),
        ('position_size', 10000),
    )

    def __init__(self):
        """Define all indicators that will be used in the strategy."""
        
        self.prediction = TransformerPredictionIndicator(self.data)
        self.smoothed_prediction = bt.indicators.SMA(
            self.prediction, 
            period=self.p.pred_smooth_period
        )
        
        self.angle = AngleIndicator(
            self.smoothed_prediction, 
            angle_lookback=self.p.pred_smooth_period
        )
        
        self.sma_short_term = bt.indicators.SMA(
            self.data.close,
            period=self.p.sma_short_term_period
        )
        self.sma_long_term = bt.indicators.SMA(
            self.data.close, 
            period=self.p.sma_long_term_period
        )
        self.sma_momentum = bt.indicators.SMA(
            self.data.close, 
            period=self.p.sma_momentum_period
        )
        self.smooth_cross_momentum = bt.indicators.CrossOver(
            self.smoothed_prediction, 
            self.sma_momentum
        )

    def next(self):
        """This method is called for each bar of data and contains the trading logic."""
        
        if np.isnan(self.angle[0]):
            return

        if self.position:
            if self.smooth_cross_momentum[0] < 0:
                self.close()
            return

        is_bullish_filter = (self.sma_long_term[0] < self.prediction[0] and 
                             self.sma_momentum[0] < self.prediction[0])

        is_strong_momentum = self.smoothed_prediction[0] > self.smoothed_prediction[-1]

        is_crossover_signal = self.smooth_cross_momentum[0] > 0

        is_steep_angle = self.angle[0] > self.p.min_angle_for_entry
        
        if is_bullish_filter and is_strong_momentum and is_crossover_signal and is_steep_angle:
            print(f"--- BUY SIGNAL @ {self.data.datetime.date(0)} (Angle: {self.angle[0]:.2f}° > {self.p.min_angle_for_entry}°) ---")
            self.buy(size=self.p.position_size)

# --- Cerebro Execution ---
if __name__ == '__main__':
    cerebro = bt.Cerebro(runonce=False)
    
    cerebro.addstrategy(TransformerSignalStrategy)
    
    # Load the data feed
    data = bt.feeds.GenericCSVData(
        # --- FIX: Corrected parameter name from 'datame' to 'dataname' ---
        dataname=str(DATA_PATH), 
        dtformat=('%Y%m%d'), 
        tmformat=('%H:%M:%S'),
        datetime=0, time=1, open=2, high=3, low=4, close=5, volume=6,
        timeframe=bt.TimeFrame.Minutes, compression=5)
    
    cerebro.adddata(data)
    cerebro.broker.setcash(100000.0)
    
    print("--- Running Backtest ---")
    cerebro.run()
    
    print("\n--- Backtest Finished. Generating Plot... ---")
    cerebro.plot(style='line')