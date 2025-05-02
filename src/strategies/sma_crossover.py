# strategies/sma_crossover.py
import backtrader as bt

class SMACrossOverStrategy(bt.Strategy):
    """
    Buys data0 when its Fast SMA crosses above its Slow SMA AND
    data1's Fast SMA crosses below its Slow SMA.
    Exits data0 when its Fast SMA crosses below its Slow SMA.
    """
    params = (
        # Parameters for data0 (e.g., XAUUSD)
        ('p_fast_d0', 20),  # Period for the fast SMA on data0
        ('p_slow_d0', 50),  # Period for the slow SMA on data0
        # Parameters for data1 (e.g., SP500)
        ('p_fast_d1', 20),  # Period for the fast SMA on data1
        ('p_slow_d1', 50),  # Period for the slow SMA on data1
        # ---
        ('run_name', 'corr_sma_run') # Default run name
    )

    def __init__(self):
        # Keep references to the data feeds generically
        self.d0 = self.data0
        self.d1 = self.data1

        # --- Get Data Feed Names ---
        self.d0_name = self.d0._name if hasattr(self.d0, '_name') else 'data0'
        self.d1_name = self.d1._name if hasattr(self.d1, '_name') else 'data1'

        # --- Indicators for data0 ---
        self.sma_fast_d0 = bt.indicators.SMA(self.d0.close, period=self.p.p_fast_d0)
        self.sma_slow_d0 = bt.indicators.SMA(self.d0.close, period=self.p.p_slow_d0)
        self.crossover_d0 = bt.indicators.CrossOver(self.sma_fast_d0, self.sma_slow_d0) # Signal for data0

        # --- Indicators for data1 ---
        self.sma_fast_d1 = bt.indicators.SMA(self.d1.close, period=self.p.p_fast_d1)
        self.sma_slow_d1 = bt.indicators.SMA(self.d1.close, period=self.p.p_slow_d1)
        self.crossover_d1 = bt.indicators.CrossOver(self.sma_fast_d1, self.sma_slow_d1) # Signal for data1

        # Store run name from params
        self.run_name = self.p.run_name

        # For order tracking
        self.order = None

        print(f"Initialized CorrelatedSMACrossStrategy:")
        print(f"  - {self.d0_name}: Fast SMA({self.p.p_fast_d0}), Slow SMA({self.p.p_slow_d0})")
        print(f"  - {self.d1_name}: Fast SMA({self.p.p_fast_d1}), Slow SMA({self.p.p_slow_d1}) for correlation")

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.datetime(0)
        print(f'{self.run_name} | {dt.isoformat()} | {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            asset_name = self.d0_name # Trades are only on data0
            if order.isbuy():
                self.log(f'BUY EXECUTED [{asset_name}], Price: {order.executed.price:.2f}, Size: {order.executed.size}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED [{asset_name}], Price: {order.executed.price:.2f}, Size: {order.executed.size}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order Canceled/Margin/Rejected: Status {order.getstatusname()}')

        self.order = None # Reset order status

    def next(self):
        # Check if an order is pending
        if self.order:
            return

        # Check if we are in the market (only tracking data0 position)
        position_size = self.getposition(self.d0).size

        # --- Entry Logic ---
        if not position_size: # Not in the market
            # Condition 1: Fast SMA crosses above Slow SMA on data0 (e.g., XAUUSD)
            d0_cross_up = self.crossover_d0[0] > 0
            # Condition 2: Fast SMA crosses BELOW Slow SMA on data1 (e.g., SP500)
            d1_cross_down = self.crossover_d1[0] < 0

            # Enter if BOTH conditions are true
            if d0_cross_up and d1_cross_down:
                self.log(f'BUY CREATE [{self.d0_name}], Signal: {self.d0_name} Cross Up AND {self.d1_name} Cross Down')
                # Buy data0
                self.order = self.buy(data=self.d0)

        # --- Exit Logic ---
        else: # In the market (holding data0)
            # Condition: Fast SMA crosses below Slow SMA on data0 (Exit condition unchanged)
            if self.crossover_d0[0] < 0:
                self.log(f'SELL CREATE (Close) [{self.d0_name}], Signal: {self.d0_name} Cross Down')
                # Close position in data0
                self.order = self.close(data=self.d0)

    def stop(self):
        final_value = self.broker.getvalue()
        self.log(f'({self.d0_name} F:{self.p.p_fast_d0}/S:{self.p.p_slow_d0}, {self.d1_name} F:{self.p.p_fast_d1}/S:{self.p.p_slow_d1}) Ending Value {final_value:.2f}')