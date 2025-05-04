# analyzers/value_capture.py
import backtrader as bt
import collections

class ValueCaptureAnalyzer(bt.Analyzer):
    """
    Analyzer to capture portfolio value, asset OHLC prices,
    and corresponding datetimes at each step of the strategy.
    """
    def __init__(self):
        self.values = []
        self.datetimes = []
        self.d0_closes = []
        self.d1_closes = []
        # Capture OHLC for both data feeds
        self.d0_ohlc = {'open': [], 'high': [], 'low': [], 'close': []}
        self.d1_ohlc = {'open': [], 'high': [], 'low': [], 'close': []}
        

    def start(self):
        # Optional: Initialize with starting cash if needed,
        # but next() captures the value at the END of the bar anyway.
        super().start()

    def next(self):
        # Capture data at the end of each bar
        # Use datetime(0) for the current bar's datetime object
        current_dt = self.strategy.datetime.datetime(0)
        current_value = self.strategy.broker.getvalue()
        self.datetimes.append(current_dt)
        self.values.append(current_value)
        # print(f"DEBUG ValueCapture: {current_dt} - {current_value}") # Optional Debug
        

        # Capture OHLC prices
        try:
            self.d0_ohlc['open'].append(self.strategy.data0.open[0])
            self.d0_ohlc['high'].append(self.strategy.data0.high[0])
            self.d0_ohlc['low'].append(self.strategy.data0.low[0])
            self.d0_ohlc['close'].append(self.strategy.data0.close[0])
        except IndexError: # Handle potential initial missing data
            for key in self.d0_ohlc: self.d0_ohlc[key].append(float('nan'))
        try:
            self.d1_ohlc['open'].append(self.strategy.data1.open[0])
            self.d1_ohlc['high'].append(self.strategy.data1.high[0])
            self.d1_ohlc['low'].append(self.strategy.data1.low[0])
            self.d1_ohlc['close'].append(self.strategy.data1.close[0])
        except IndexError: # Handle potential initial missing data
            for key in self.d1_ohlc: self.d1_ohlc[key].append(float('nan'))

    def stop(self):
        # Nothing specific needed here usually, data is in lists
        pass

    def get_analysis(self):
        # Return the collected data in a standard dictionary format
        return collections.OrderedDict(
            datetimes=self.datetimes,
            values=self.values,
            d0_ohlc=self.d0_ohlc,
            d1_ohlc=self.d1_ohlc
        )