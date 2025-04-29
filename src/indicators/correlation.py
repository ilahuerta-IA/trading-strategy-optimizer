import backtrader as bt
import numpy as np
import scipy.stats

# Pearson Correlation
class PearsonR(bt.ind.PeriodN):
    _mindatas = 2  # hint to the platform

    lines = ('correlation',)
    params = (('period', 20),)

    def next(self):
        # Get the data slices for the period
        data0_slice = self.data0.get(size=self.p.period)
        data1_slice = self.data1.get(size=self.p.period)

        # Ensure we have enough data points in both slices
        if len(data0_slice) < self.p.period or len(data1_slice) < self.p.period:
             self.lines.correlation[0] = float('nan') # Not enough data yet
             return
        
        # Check for constant series (std dev = 0) which cause pearsonr errors
        if np.std(data0_slice) == 0 or np.std(data1_slice) == 0:
             # Correlation is NaN if one is constant, 0 if both are constant? (Check definition or set NaN)
             self.lines.correlation[0] = 0.0 if np.std(data0_slice) == 0 and np.std(data1_slice) == 0 else float('nan') 
             return

        try:
            c, p = scipy.stats.pearsonr(data0_slice, data1_slice)
            self.lines.correlation[0] = c
        except ValueError as e:
             print(f"Error calculating Pearson R: {e}. Data0: {data0_slice}, Data1: {data1_slice}")
             self.lines.correlation[0] = float('nan') # Handle potential errors from pearsonr