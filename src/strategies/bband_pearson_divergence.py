# strategies/bband_pearson_divergence.py
import backtrader as bt
import numpy as np # Needed for isnan if Pearson returns NaN
# Ensure PearsonR can be imported (adjust path if necessary)
from indicators.correlation import PearsonR

class BBandPearsonDivergence(bt.Strategy):
    """
    Enters long on data0 if:
    1. data0 price touches or exceeds its upper Bollinger Band.
    2. data1 price is below its middle Bollinger Band.
    3. Pearson correlation(d0, d1) has decreased significantly recently.
    Exits long on data0 if price crosses below its middle Bollinger Band.
    """
    params = (
        # Bollinger Bands parameters
        ('bb_period_d0', 100),
        ('bb_dev_d0', 2.0),
        ('bb_period_d1', 5),
        ('bb_dev_d1', 2.0),
        # Pearson Correlation parameters
        ('pearson_period', 20),          # Period for Pearson calculation
        ('pearson_decrease_lookback', 2), # How many bars back (N) to check decrease
        ('pearson_decrease_pct', 0.6),   # Min % decrease (P) required (0.0 to 1.0)
        # Exit parameter (kept for potential future flexibility)
        ('exit_on_bbmid', True),
        # Run name
        ('run_name', 'bband_pearson_div')
    )

    def __init__(self):
        # Data feed references and names
        self.d0 = self.data0
        self.d1 = self.data1
        self.d0_name = self.d0._name if hasattr(self.d0, '_name') else 'data0'
        self.d1_name = self.d1._name if hasattr(self.d1, '_name') else 'data1'

        # Bollinger Bands - Plot directly on the master data plots
        # data0 BBands on data0 chart
        self.bb_d0 = bt.indicators.BollingerBands(self.d0.close,
                                                  period=self.p.bb_period_d0,
                                                  devfactor=self.p.bb_dev_d0,
                                                  plotname=f'{self.d0_name} BB({self.p.bb_period_d0},{self.p.bb_dev_d0})',
                                                  plotmaster=self.d0, subplot=False)
        # data1 BBands on data1's plot (which is mastered to d0)
        # Note: Plotting BBands from d1 onto d0's chart can be messy if price scales differ significantly.
        # Consider plotting d1 bands separately if needed, or not plotting them visually.
        self.bb_d1 = bt.indicators.BollingerBands(self.d1.close,
                                                  period=self.p.bb_period_d1,
                                                  devfactor=self.p.bb_dev_d1,
                                                  # Option A: Plot on d1's line (mastered to d0)
                                                  plotmaster=self.d1, subplot=False,
                                                  plotname=f'{self.d1_name} BB({self.p.bb_period_d1},{self.p.bb_dev_d1})')

        # Pearson Correlation
        self.pearson = PearsonR(self.d0.close, self.d1.close, # Use close prices
                                period=self.p.pearson_period)

        # Calculate minimum period for indicators to be ready
        # Need enough history for Pearson AND the lookback for its decrease check
        pearson_total_lookback = self.p.pearson_period + self.p.pearson_decrease_lookback
        self.min_period = max(self.p.bb_period_d0, self.p.bb_period_d1, pearson_total_lookback)
        self.warmup_bars = self.min_period + 5 # Add a small buffer

        # Order tracking
        self.order = None
        self.run_name = self.p.run_name

        print(f"Initialized BBandPearsonDivergence Strategy ({self.run_name}):")
        print(f"  - {self.d0_name}: BB({self.p.bb_period_d0}, {self.p.bb_dev_d0})")
        print(f"  - {self.d1_name}: BB({self.p.bb_period_d1}, {self.p.bb_dev_d1})")
        print(f"  - Pearson: Period={self.p.pearson_period}, DecreaseLookback={self.p.pearson_decrease_lookback}, DecreasePct={self.p.pearson_decrease_pct:.2f}")
        print(f"  - Exit: On {self.d0_name} crossing BB Mid ({self.p.exit_on_bbmid})")
        print(f"  - Min Period: {self.min_period}, Warmup Bars: {self.warmup_bars}")


    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        print(f'{self.run_name} | {dt.isoformat()} | {txt}')

    def notify_order(self, order):
        asset_name = order.data._name if hasattr(order.data, '_name') else 'UnknownData'
        if order.status in [order.Submitted, order.Accepted]:
            self.log(f'Order {order.getstatusname()} [{asset_name}] Ref: {order.ref}')
            # Keep self.order assigned
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED [{asset_name}], Ref: {order.ref}, Price: {order.executed.price:.2f}, Size: {order.executed.size}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            elif order.issell():
                 self.log(f'SELL EXECUTED [{asset_name}], Ref: {order.ref}, Price: {order.executed.price:.2f}, Size: {order.executed.size}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            pos_d0 = self.getposition(self.d0).size
            self.log(f'Post-Exec Position: {self.d0_name}={pos_d0}') # Only log d0 as we only trade d0

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order Canceled/Margin/Rejected [{asset_name}] Ref: {order.ref}, Status: {order.getstatusname()}')

        # Reset self.order ONLY when the order is definitively finished
        self.order = None

    def next(self):
        # 1. Check for pending order
        if self.order:
            # self.log(f"Pending order (Ref: {self.order.ref}), skipping bar.") # Optional Debug
            return

        # 2. Check if indicators are ready (warmup period)
        # Use current bar index len(self) which Backtrader makes available
        if len(self) < self.warmup_bars:
             # self.log(f"Warming up {len(self)}/{self.warmup_bars}") # Optional Debug
             return

        # 3. Get current position status (only care about d0)
        pos_d0 = self.getposition(self.d0)

        # 4. Exit Logic (if holding a position in d0)
        if pos_d0.size != 0:
            if self.p.exit_on_bbmid:
                exit_cond = self.d0.close[0] < self.bb_d0.lines.mid[0]
                # Log current status for debugging exit
                self.log(f"Holding {self.d0_name} ({pos_d0.size}). Checking Exit: Close={self.d0.close[0]:.2f} < BB Mid={self.bb_d0.lines.mid[0]:.2f}? -> {exit_cond}")
                if exit_cond:
                    self.log(f'SELL CREATE (Close) [{self.d0_name}] Signal: Close < BB Mid')
                    self.order = self.close(data=self.d0)
                    return # Exit order placed, do no more this bar
            # else: Add other exit logic here if needed
            # If no exit condition met, do nothing else (don't check entry)
            return

        # 5. Entry Logic (only if no position in d0 and no pending order)
        if pos_d0.size == 0:
            # Condition 1: d0 touches or exceeds upper BB
            cond1 = self.d0.close[0] >= self.bb_d0.lines.top[0]

            # Condition 2: d1 is below middle BB
            cond2 = self.d1.close[0] < self.bb_d1.lines.mid[0]

            # Condition 3: Pearson correlation decrease
            cond3 = False # Default to false
            # Ensure we have enough history in the pearson indicator itself
            # Note: len(self.pearson.lines.correlation) might be more direct
            if len(self.pearson) > self.p.pearson_decrease_lookback:
                p_start = self.pearson.lines.correlation[-self.p.pearson_decrease_lookback]
                p_now = self.pearson.lines.correlation[0]

                # Check for NaN values from Pearson calculation
                if not np.isnan(p_start) and not np.isnan(p_now):
                    drop = p_start - p_now
                    max_drop = p_start + 1.0 # Potential drop down to -1

                    # Check if drop is positive and max_drop is valid
                    if drop > 1e-6 and max_drop > 1e-6: # Use small epsilon to avoid division by near zero
                        pct_decrease = drop / max_drop
                        if pct_decrease >= self.p.pearson_decrease_pct:
                            cond3 = True
                            # Log Pearson details only when condition might trigger
                            # self.log(f"Pearson Check: Start={p_start:.3f}, Now={p_now:.3f}, Drop={drop:.3f}, MaxDrop={max_drop:.3f}, Pct={pct_decrease:.3f} >= {self.p.pearson_decrease_pct:.3f} -> {cond3}")

            # Log conditions status for debugging entry
            # self.log(f"Entry Check: Cond1(d0>=TopBB)={cond1}, Cond2(d1<MidBB)={cond2}, Cond3(PearsonDrop)={cond3}")

            # Check if all conditions met
            if cond1 and cond2 and cond3:
                self.log(f"BUY CREATE [{self.d0_name}] Signal: d0>=TopBB AND d1<MidBB AND Pearson Decreased")
                self.order = self.buy(data=self.d0)

    def stop(self):
        # Log final portfolio value at the end of the backtest
        final_value = self.broker.getvalue()
        self.log(f'Ending Portfolio Value: {final_value:.2f}')