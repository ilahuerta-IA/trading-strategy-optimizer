# analyzers/value_capture.py
import backtrader as bt
import collections
import numpy as np # For nan

class ValueCaptureAnalyzer(bt.Analyzer):
    def __init__(self):
        self.values = []
        self.datetimes = []
        self.d0_ohlc = {'open': [], 'high': [], 'low': [], 'close': []}
        self.d1_ohlc = {'open': [], 'high': [], 'low': [], 'close': []}
        # --- NEW: Dictionary to store captured indicator data ---
        self.indicator_data = collections.defaultdict(list)
        self.indicator_configs = [] # To store (display_name, target_pane)
        # --- END NEW ---

    def start(self):
        super().start()
        # Get plottable indicators from strategy
        if hasattr(self.strategy, '_plottable_indicators'):
            for indicator_config_tuple in self.strategy._plottable_indicators:
                # Unpack, handling optional options dict
                attr_name, line_name, display_name, target_pane = indicator_config_tuple[:4]
                options_dict = indicator_config_tuple[4] if len(indicator_config_tuple) > 4 else {} # Get options

                if hasattr(self.strategy, attr_name):
                    self.indicator_configs.append({
                        'internal_id': f"{attr_name}_{line_name}",
                        'display_name': display_name,
                        'target_pane': target_pane,
                        'attr_name': attr_name,
                        'line_name': line_name,
                        'options': options_dict # Store the options
                    })
                else:
                    print(f"ValueCapture Warning: Indicator attribute '{attr_name}' not found in strategy.")


    def next(self):
        current_dt = self.strategy.datetime.datetime(0)
        current_value = self.strategy.broker.getvalue()
        self.datetimes.append(current_dt)
        self.values.append(current_value)
        # ... (OHLC capture remains) ...
        try:
            self.d0_ohlc['open'].append(self.strategy.data0.open[0])
            self.d0_ohlc['high'].append(self.strategy.data0.high[0])
            self.d0_ohlc['low'].append(self.strategy.data0.low[0])
            self.d0_ohlc['close'].append(self.strategy.data0.close[0])
        except IndexError:
            for key in self.d0_ohlc:
                self.d0_ohlc[key].append(float('nan'))
        try: self.d1_ohlc['open'].append(self.strategy.data1.open[0]); ... # and so on for H,L,C
        except IndexError:
            for key in self.d1_ohlc:
                self.d1_ohlc[key].append(float('nan'))


        # Capture configured indicator values
        for config in self.indicator_configs:
            try:
                indicator_obj = getattr(self.strategy, config['attr_name'])
                # Access the specific line of the indicator
                if config['line_name'] == 'lines_def': # Special case for multi-line default access
                    line_val = indicator_obj.lines[0][0] # Example: first line of default lines object
                elif hasattr(indicator_obj.lines, config['line_name']):
                    line_obj = getattr(indicator_obj.lines, config['line_name'])
                    line_val = indicator_obj[0] # Get current value
                elif hasattr(indicator_obj, config['line_name']): # For indicators like PearsonR where line is direct attribute
                    line_obj = getattr(indicator_obj, config['line_name'])
                    line_val = line_obj[0]
                else: # Fallback: try accessing as lines[0] if single-line indicator
                    line_val = indicator_obj.lines[0][0]

                self.indicator_data[config['internal_id']].append(line_val)
            except (AttributeError, IndexError, Exception) as e:
                # print(f"ValueCapture Error capturing {config['internal_id']}: {e}") # Verbose
                self.indicator_data[config['internal_id']].append(np.nan) # Append NaN on error

    def get_analysis(self):
        # Captura señales si existen en la estrategia
        signals = []
        if hasattr(self.strategy, 'signals'):
            for sig in self.strategy.signals:
                # Convertir datetime a string ISO para JSON
                sig_copy = sig.copy()
                if isinstance(sig_copy.get('datetime'), (str, type(None))):
                    pass
                else:
                    sig_copy['datetime'] = sig_copy['datetime'].isoformat()
                signals.append(sig_copy)
        return collections.OrderedDict(
            datetimes=self.datetimes,
            values=self.values,
            d0_ohlc=self.d0_ohlc,
            d1_ohlc=self.d1_ohlc,
            # Add indicator data and configs to output ---
            indicator_configs=self.indicator_configs, # How to plot them
            indicators=dict(self.indicator_data),      # The actual data series
            signals=signals                           # NUEVO: señales buy/sell
        )