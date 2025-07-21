import backtrader as bt
import torch
import torch.nn as nn
import joblib
import json
import pandas as pd
import numpy as np
from pathlib import Path
from transformers import TimeSeriesTransformerConfig, TimeSeriesTransformerModel

# --- Path setup for model artifacts ---
# Assumes the script is run from the project root (e.g., .../quant_bot_project/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = PROJECT_ROOT / 'src' / 'ml_models'

class TransformerForPointPrediction(nn.Module):
    """
    Custom wrapper for the TimeSeriesTransformerModel to add a prediction head.
    This is necessary to match the architecture of the saved .pth file.
    """
    def __init__(self, config: TimeSeriesTransformerConfig):
        super().__init__()
        self.model = TimeSeriesTransformerModel(config)
        # Add a linear layer to map the transformer's output to a single point prediction
        self.prediction_head = nn.Linear(config.d_model, 1)

    def forward(self, *args, **kwargs):
        outputs = self.model(*args, **kwargs)
        # We use the last hidden state for prediction
        last_hidden_state = outputs.last_hidden_state
        # Pass the output of the last time step to the prediction head
        return self.prediction_head(last_hidden_state[:, -1, :])

class TransformerSignalStrategy(bt.Strategy):
    """
    A backtrader strategy that uses a pre-trained Transformer model
    to generate trading signals.
    """
    def __init__(self):
        print("--- Initializing TransformerSignalStrategy ---")
        
        # 1. Load Model Configuration
        config_path = MODELS_DIR / 'model_config.json'
        print(f"Loading config from: {config_path}")
        with open(config_path, 'r') as f:
            model_config_dict = json.load(f)
        
        # The transformers library expects specific keys, so we map them if needed
        # For this example, we assume the JSON is already in the correct format.
        config = TimeSeriesTransformerConfig.from_dict(model_config_dict)
        
        # 2. Load Target Scaler
        scaler_path = MODELS_DIR / 'target_scaler.pkl'
        print(f"Loading scaler from: {scaler_path}")
        self.scaler = joblib.load(scaler_path)

        # 3. Instantiate the Custom Model
        print("Instantiating TransformerForPointPrediction model...")
        self.model = TransformerForPointPrediction(config)

        # 4. Load Trained Weights
        weights_path = MODELS_DIR / 'best_transformer_model.pth'
        print(f"Loading weights from: {weights_path}")
        # Load weights onto the CPU, adaptable for systems without a GPU
        self.model.load_state_dict(torch.load(weights_path, map_location=torch.device('cpu')))
        
        # 5. Set Model to Evaluation Mode
        self.model.eval()
        print("Model set to evaluation mode.")

        # 6. Store Model Parameters
        self.context_length = config.context_length
        self.max_lag = 7  # As specified, using a default of 7
        print(f"Context length: {self.context_length}, Max lag: {self.max_lag}")

        # 7. Create a standard Backtrader indicator
        self.sma = bt.indicators.SMA(self.data.close, period=50)
        
        print("--- Strategy Initialization Complete ---")

    def next(self):
        """
        Main strategy logic. Will be implemented in the next step.
        """
        pass

if __name__ == '__main__':
    # --- Cerebro Engine Setup ---
    cerebro = bt.Cerebro()

    # --- Add Strategy ---
    cerebro.addstrategy(TransformerSignalStrategy)

    # --- Add Data Feed ---
    # This assumes you have a data file at the specified path.
    # Update the path to your actual data file.
    data_path = PROJECT_ROOT / 'data' / 'EURUSD_5_minute_data.csv'
    
    data = bt.feeds.GenericCSVData(
        dataname=data_path,
        dtformat=('%Y-%m-%d %H:%M:%S'),
        datetime=0,
        open=1,
        high=2,
        low=3,
        close=4,
        volume=5,
        openinterest=-1,
        timeframe=bt.TimeFrame.Minutes,
        compression=5
    )
    cerebro.adddata(data)

    # --- Set Initial Capital and Run ---
    cerebro.broker.setcash(100000.0)
    print(f'Starting Portfolio Value: {cerebro.broker.getvalue():.2f}')