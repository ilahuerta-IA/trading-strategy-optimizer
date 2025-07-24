import backtrader as bt
import torch
import joblib
import json
import pandas as pd
import numpy as np
from pathlib import Path
from transformers import TimeSeriesTransformerConfig, TimeSeriesTransformerForPrediction
from datetime import timedelta

# --- WARNING SUPPRESSION (DEFINITIVE FIX) ---
import warnings
from transformers.utils import logging

# Suppress transformers' own logging and UserWarnings from that library
logging.set_verbosity_error() 
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")

# --- CRITICAL FIX: Suppress the scikit-learn feature name warning ---
# UserWarning is a built-in category, so no special import is needed.
warnings.filterwarnings("ignore", category=UserWarning, message="X does not have valid feature names")
# --- END OF WARNING SUPPRESSION ---


# --- Path setup for model artifacts ---
# Assumes the script is run from the directory containing the 'src' folder
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent 
MODELS_DIR = PROJECT_ROOT / 'src' / 'ml_models'

def create_time_features_for_window(dt_index: pd.DatetimeIndex) -> np.ndarray:
    """
    Generates and scales time features for a given datetime window.
    """
    features = pd.DataFrame(index=dt_index)
    features['hour'] = (dt_index.hour / 23.0) - 0.5
    features['day_of_week'] = (dt_index.dayofweek / 6.0) - 0.5
    features['day_of_month'] = ((dt_index.day - 1) / 30.0) - 0.5
    features['month'] = ((dt_index.month - 1) / 11.0) - 0.5
    return features.values

# --- Custom Indicator for Transformer Predictions ---
class TransformerPredictionIndicator(bt.Indicator):
    lines = ('prediction',)
    params = (
        ('models_dir', str(MODELS_DIR)),
    )

    def __init__(self):
        super().__init__()
        self.p.models_dir = Path(self.p.models_dir)

        # 1. Load Config
        with open(self.p.models_dir / 'model_config.json', 'r') as f:
            model_config_dict = json.load(f)
        config = TimeSeriesTransformerConfig.from_dict(model_config_dict)

        # 2. Load Scaler
        self.scaler = joblib.load(self.p.models_dir / 'target_scaler.pkl')

        # 3. Load Model
        self.model = TimeSeriesTransformerForPrediction(config)
        self.model.load_state_dict(torch.load(self.p.models_dir / 'best_transformer_model.pth', map_location='cpu'))
        self.model.eval()

        # 4. Set parameters
        self.context_length = config.context_length
        self.prediction_length = config.prediction_length
        self.max_lag = max(config.lags_sequence) if config.lags_sequence else 0
        self.history_len = self.context_length + self.max_lag

        # Let Backtrader know the minimum period needed before starting
        self.addminperiod(self.history_len)
        
        print("--- TransformerPredictionIndicator Initialized ---")

    def next(self):
        # Get the required window of close prices as a NumPy array
        close_prices = np.array(self.data.close.get(size=self.history_len))
        
        # Get the corresponding datetimes
        datetimes = [self.data.num2date(self.data.datetime[-i]) for i in range(self.history_len)]
        datetimes.reverse()
        dt_index = pd.to_datetime(datetimes)

        # Preprocess Data
        scaled_prices = self.scaler.transform(close_prices.reshape(-1, 1)).flatten()
        past_time_features_np = create_time_features_for_window(dt_index)
        
        # Create time features for the single future step we are predicting
        future_dt_index = pd.to_datetime([dt_index[-1] + timedelta(minutes=5)])
        future_time_features_np = create_time_features_for_window(future_dt_index)

        # Convert to Tensors
        past_values = torch.tensor(scaled_prices, dtype=torch.float32).unsqueeze(0)
        past_time_features = torch.tensor(past_time_features_np, dtype=torch.float32).unsqueeze(0)
        future_time_features = torch.tensor(future_time_features_np, dtype=torch.float32).unsqueeze(0)
        past_observed_mask = torch.ones_like(past_values)

        # Make Prediction using the generate method for inference
        with torch.no_grad():
            outputs = self.model.generate(
                past_values=past_values,
                past_time_features=past_time_features,
                past_observed_mask=past_observed_mask,
                future_time_features=future_time_features
            )
            scaled_prediction = outputs.sequences.mean(dim=1).cpu().numpy()

        # Inverse-transform and set the indicator line
        predicted_price = self.scaler.inverse_transform(scaled_prediction)[0][0]
        self.lines.prediction[0] = predicted_price

# --- Strategy and Cerebro Setup ---
class TransformerSignalStrategy(bt.Strategy):
    def __init__(self):
        print("--- Initializing TransformerSignalStrategy ---")
        self.prediction = TransformerPredictionIndicator(self.data)
        self.prediction.plotinfo.plot = True
        self.prediction.plotinfo.plotname = 'Prediction'
        self.smoothed_prediction = bt.indicators.SMA(self.prediction.lines.prediction, period=3, plotname='Smoothed Prediction')
        self.sma = bt.indicators.SMA(self.data.close, period=50)
        print("--- Strategy Initialization Complete ---")

    def next(self):
        pass

if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(TransformerSignalStrategy)
    
    data_path = PROJECT_ROOT / 'data' / 'EURUSD_5m_2Mon.csv'
    
    data = bt.feeds.GenericCSVData(
        dataname=str(data_path),
        dtformat=('%Y%m%d'),
        tmformat=('%H:%M:%S'),
        datetime=0, time=1, open=2, high=3, low=4, close=5, volume=6, openinterest=-1,
        timeframe=bt.TimeFrame.Minutes,
        compression=5
    )
    cerebro.adddata(data)
    
    cerebro.broker.setcash(100000.0)
    print(f'Starting Portfolio Value: {cerebro.broker.getvalue():.2f}')
    
    cerebro.run()
    
    print(f'Final Portfolio Value: {cerebro.broker.getvalue():.2f}')
    
    print("Backtest complete. Generating plot...")
    cerebro.plot(style='candlestick', barup='green', bardown='red')