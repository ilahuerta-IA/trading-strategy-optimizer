import backtrader as bt
import torch
import joblib
import json
import pandas as pd
import numpy as np
from pathlib import Path
from transformers import TimeSeriesTransformerConfig, TimeSeriesTransformerForPrediction
from datetime import timedelta

# --- WARNING SUPPRESSION ---
import warnings
from transformers.utils import logging
logging.set_verbosity_error()
warnings.filterwarnings("ignore", category=UserWarning)
# --- END WARNING SUPPRESSION ---

# --- Path setup for model artifacts ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = PROJECT_ROOT / 'src' / 'ml_models'

def create_time_features_for_window(dt_index: pd.DatetimeIndex) -> np.ndarray:
    """Generates and scales time features for a given datetime window."""
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
        # --- This is the key line for overlaying the plot on the main chart ---
        self.plotinfo.plotmaster = self.data
        
        self.p.models_dir = Path(self.p.models_dir)

        with open(self.p.models_dir / 'model_config.json', 'r') as f:
            model_config_dict = json.load(f)
        config = TimeSeriesTransformerConfig.from_dict(model_config_dict)

        self.scaler = joblib.load(self.p.models_dir / 'target_scaler.pkl')

        self.model = TimeSeriesTransformerForPrediction(config)
        self.model.load_state_dict(torch.load(self.p.models_dir / 'best_transformer_model.pth', map_location='cpu'))
        self.model.eval()

        self.context_length = config.context_length
        self.max_lag = max(config.lags_sequence) if config.lags_sequence else 0
        self.history_len = self.context_length + self.max_lag

        self.addminperiod(self.history_len)
        print("--- TransformerPredictionIndicator Initialized ---")

    def next(self):
        close_prices = np.array(self.data.close.get(size=self.history_len))
        
        datetimes = [self.data.num2date(self.data.datetime[-i]) for i in range(self.history_len)]
        datetimes.reverse()
        dt_index = pd.to_datetime(datetimes)

        scaled_prices = self.scaler.transform(close_prices.reshape(-1, 1)).flatten()
        past_time_features_np = create_time_features_for_window(dt_index)
        
        future_dt_index = pd.to_datetime([dt_index[-1] + timedelta(minutes=5)])
        future_time_features_np = create_time_features_for_window(future_dt_index)

        past_values = torch.tensor(scaled_prices, dtype=torch.float32).unsqueeze(0)
        past_time_features = torch.tensor(past_time_features_np, dtype=torch.float32).unsqueeze(0)
        future_time_features = torch.tensor(future_time_features_np, dtype=torch.float32).unsqueeze(0)
        past_observed_mask = torch.ones_like(past_values)

        with torch.no_grad():
            outputs = self.model.generate(
                past_values=past_values,
                past_time_features=past_time_features,
                past_observed_mask=past_observed_mask,
                future_time_features=future_time_features
            )
            scaled_prediction = outputs.sequences.mean(dim=1).cpu().numpy()

        # --- CRITICAL CHANGE: Select the LAST point of the prediction horizon ---
        # scaled_prediction shape is (1, 6). We want the final value at index -1.
        final_step_prediction = scaled_prediction[:, -1].reshape(-1, 1)

        # Inverse-transform the final step and set the indicator line
        predicted_price = self.scaler.inverse_transform(final_step_prediction)[0][0]
        self.lines.prediction[0] = predicted_price

# --- Final Trading Strategy ---
class TransformerSignalStrategy(bt.Strategy):
    params = (
        ('sma_period', 5),
        ('pred_smooth_period', 5),
        ('sma_momentum_period', 50),  # New configurable SMA for momentum filter
        ('show_candlesticks', False),  # Parameter to switch between line and candlestick
        ('position_size', 10000),  # Position size in units (10000 = 0.1 standard lot for forex)
    )

    def __init__(self):
        print("--- Initializing TransformerSignalStrategy ---")
        
        # 1. Instantiate our custom prediction indicator
        self.prediction = TransformerPredictionIndicator(self.data)
        self.prediction.plotinfo.plotmaster = self.data
        self.prediction.plotinfo.plotname = 'Transformer_Prediction'
        self.prediction.plotinfo.color = 'cyan'
        self.prediction.plotinfo.linestyle = '--'

        # 2. Apply smoothing to the prediction using the parameter
        self.smoothed_prediction = bt.indicators.SMA(
            self.prediction.lines.prediction, 
            period=self.p.pred_smooth_period,
            plotname=f'Smoothed_Prediction({self.p.pred_smooth_period})'
        )

        # 3. Create the long-term trend filter (hidden from chart)
        self.sma_long = bt.indicators.SMA(
            self.data.close, 
            period=self.p.sma_period,
            plotname=f'SMA({self.p.sma_period})'
        )
        self.sma_long.plotinfo.plot = True #False  # Show on chart

        # 4. Add a longer-term SMA for additional context
        self.sma_50 = bt.indicators.SMA(
            self.data.close,
            period=100,
            plotname='SMA(50)'
        )

        # 5. Add configurable momentum SMA
        self.sma_momentum = bt.indicators.SMA(
            self.data.close,
            period=self.p.sma_momentum_period,
            plotname=f'SMA_Momentum({self.p.sma_momentum_period})'
        )

        # 6. Create crossover signals
        # Crossover between smoothed prediction and momentum SMA
        self.smooth_cross_momentum = bt.indicators.CrossOver(self.smoothed_prediction, self.sma_momentum)
        
        print("--- Strategy Initialization Complete ---")

    def next(self):
        # --- Long-Only Strategy with 2-Period Momentum Confirmation ---

        # Check if we are already in the market
        if self.position:
            # Exit long if smoothed prediction crosses down below momentum SMA
            if self.smooth_cross_momentum[0] < 0:
                print(f'{self.data.datetime.date(0)}: CLOSE LONG @ {self.data.close[0]:.5f}')
                self.close()
            return

        # --- Entry Logic (Long Only) with 2-Period Rising Confirmation ---
        # Entry conditions:
        # 1. SMA(50) and Momentum SMA must be below transformer prediction
        # 2. All indicators must be rising for 2 consecutive periods
        # 3. Smoothed prediction crosses up above Momentum SMA
        if (self.sma_50[0] < self.prediction[0] and 
            self.sma_momentum[0] < self.prediction[0] and
            # 2-period rising confirmation for SMA50
            self.sma_50[0] > self.sma_50[-1] and
            self.sma_50[-1] > self.sma_50[-2] and
            # 2-period rising confirmation for momentum SMA
            self.sma_momentum[0] > self.sma_momentum[-1] and
            self.sma_momentum[-1] > self.sma_momentum[-2] and
            # 2-period rising confirmation for transformer prediction
            self.prediction[0] > self.prediction[-1] and
            self.prediction[-1] > self.prediction[-2] and
            # 2-period rising confirmation for smoothed prediction
            self.smoothed_prediction[0] > self.smoothed_prediction[-1] and
            self.smoothed_prediction[-1] > self.smoothed_prediction[-2] and
            # Smoothed prediction crosses up above momentum SMA
            self.smooth_cross_momentum[0] > 0):
            print(f'{self.data.datetime.date(0)}: BUY CREATE @ {self.data.close[0]:.5f} - Size: {self.p.position_size}')
            print(f'  SMA50 < Prediction: {self.sma_50[0]:.5f} < {self.prediction[0]:.5f}')
            print(f'  SMA Momentum < Prediction: {self.sma_momentum[0]:.5f} < {self.prediction[0]:.5f}')
            print(f'  SMA50 2-Period Rising: {self.sma_50[-2]:.5f} -> {self.sma_50[-1]:.5f} -> {self.sma_50[0]:.5f}')
            print(f'  SMA Momentum 2-Period Rising: {self.sma_momentum[-2]:.5f} -> {self.sma_momentum[-1]:.5f} -> {self.sma_momentum[0]:.5f}')
            print(f'  Prediction 2-Period Rising: {self.prediction[-2]:.5f} -> {self.prediction[-1]:.5f} -> {self.prediction[0]:.5f}')
            print(f'  Smoothed Pred 2-Period Rising: {self.smoothed_prediction[-2]:.5f} -> {self.smoothed_prediction[-1]:.5f} -> {self.smoothed_prediction[0]:.5f}')
            print(f'  Smoothed Pred crosses UP Momentum SMA: {self.smoothed_prediction[0]:.5f} > {self.sma_momentum[0]:.5f}')
            # Use the configurable position size
            self.buy(size=self.p.position_size)

# --- Cerebro Setup ---
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
    
    # Use the parameter to determine chart style
    strategy_instance = cerebro.runstrats[0][0]
    if strategy_instance.p.show_candlesticks:
        cerebro.plot(style='candlestick', barup='green', bardown='red')
    else:
        cerebro.plot(style='line')