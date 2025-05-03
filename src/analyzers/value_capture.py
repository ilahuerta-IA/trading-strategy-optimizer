# analyzers/value_capture.py
import backtrader as bt
import collections

class ValueCaptureAnalyzer(bt.Analyzer):
    """
    Analyzer to capture portfolio value and corresponding datetimes
    at each step of the strategy.
    """
    def __init__(self):
        self.values = []
        self.datetimes = []
        self.d0_closes = []
        self.d1_closes = []

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
        # --- Capture closing prices ---
        try:
            self.d0_closes.append(self.strategy.data0.close[0])
        except IndexError:
            self.d0_closes.append(float('nan')) # Handle potential initial missing data
        try:
            self.d1_closes.append(self.strategy.data1.close[0])
        except IndexError:
             self.d1_closes.append(float('nan')) # Handle potential initial missing data
        # ---

    def stop(self):
        # Nothing specific needed here usually, data is in lists
        pass

    def get_analysis(self):
        # Return the collected data in a standard dictionary format
        return collections.OrderedDict(
            datetimes=self.datetimes,
            values=self.values,
            d0_close=self.d0_closes,
            d1_close=self.d1_closes
        )