# strategies/correlated_sma_cross.py
import backtrader as bt
from .base_strategy import ParameterizedStrategy, ParameterDefinition

class CorrelatedSMACrossStrategy(bt.Strategy, ParameterizedStrategy):
    """
    Buys data0 when its Fast SMA crosses above its Slow SMA AND
    data1's Fast SMA crosses below its Slow SMA.
    Exits data0 when its Fast SMA crosses below its Slow SMA.
    """
    
    # Keep existing Backtrader params for compatibility
    params = (
        ('p_fast_d0', 20),
        ('p_slow_d0', 50),
        ('p_fast_d1', 20),
        ('p_slow_d1', 50),
        ('run_name', 'corr_sma_run')
    )

    @classmethod
    def get_parameter_definitions(cls):
        """Define structured parameter metadata for UI generation."""
        return [
            ParameterDefinition(
                name='p_fast_d0',
                default_value=20,
                ui_label='Data0 Fast SMA Period',
                type='int',
                description='Period for the fast Simple Moving Average on the primary data feed',
                min_value=1,
                max_value=200,
                step=1,
                group='Data0 Parameters'
            ),
            ParameterDefinition(
                name='p_slow_d0',
                default_value=50,
                ui_label='Data0 Slow SMA Period',
                type='int',
                description='Period for the slow Simple Moving Average on the primary data feed',
                min_value=2,
                max_value=500,
                step=1,
                group='Data0 Parameters'
            ),
            ParameterDefinition(
                name='p_fast_d1',
                default_value=20,
                ui_label='Data1 Fast SMA Period',
                type='int',
                description='Period for the fast Simple Moving Average on the secondary data feed',
                min_value=1,
                max_value=200,
                step=1,
                group='Data1 Parameters'
            ),
            ParameterDefinition(
                name='p_slow_d1',
                default_value=50,
                ui_label='Data1 Slow SMA Period',
                type='int',
                description='Period for the slow Simple Moving Average on the secondary data feed',
                min_value=2,
                max_value=500,
                step=1,
                group='Data1 Parameters'
            ),
            ParameterDefinition(
                name='run_name',
                default_value='corr_sma_run',
                ui_label='Run Name',
                type='str',
                description='Identifier name for this backtest run',
                group='General'
            )
        ]

    # Define with base display names or placeholders
    _plottable_indicators_template = [
        ('sma_fast_d0', 'sma', 'Fast SMA D0 ({})', 'main', {'color': 'yellow'}, 'p_fast_d0'),
        ('sma_slow_d0', 'sma', 'Slow SMA D0 ({})', 'main', {'color': 'purple'}, 'p_slow_d0'),
        ('d1_close_line', 'close', 'Data 1 Close', 'data1_pane', {'color': 'orange', 'lineWidth': 1.5}),
        ('sma_fast_d1', 'sma', 'Fast SMA D1 ({})', 'data1_pane', {'color': '#FF8C00'}, 'p_fast_d1'),
        ('sma_slow_d1', 'sma', 'Slow SMA D1 ({})', 'data1_pane', {'color': '#FF4500'}, 'p_slow_d1'),
    ]

    def __init__(self):
        # Keep references to the data feeds generically
        self.d0 = self.data0
        self.d1 = self.data1

        # Get Data Feed Names
        self.d0_name = self.d0._name if hasattr(self.d0, '_name') else 'data0'
        self.d1_name = self.d1._name if hasattr(self.d1, '_name') else 'data1'
        
        # Assign data1.close to an attribute
        self.d1_close_line = self.d1.close

        # Indicators for data0
        self.sma_fast_d0 = bt.indicators.SMA(self.d0.close, period=self.p.p_fast_d0)
        self.sma_slow_d0 = bt.indicators.SMA(self.d0.close, period=self.p.p_slow_d0)
        self.crossover_d0 = bt.indicators.CrossOver(self.sma_fast_d0, self.sma_slow_d0)

        # Indicators for data1
        self.sma_fast_d1 = bt.indicators.SMA(self.d1.close, period=self.p.p_fast_d1)
        self.sma_slow_d1 = bt.indicators.SMA(self.d1.close, period=self.p.p_slow_d1)
        self.crossover_d1 = bt.indicators.CrossOver(self.sma_fast_d1, self.sma_slow_d1)

        # Store run name from params
        self.run_name = self.p.run_name

        # For order tracking
        self.order = None

        # List to store entry/exit signals
        self.signals = []

        # Process plottable indicators template
        self._plottable_indicators = []
        for item_tuple in self._plottable_indicators_template:
            if len(item_tuple) == 6:
                attr, line, fmt_str, pane, opts, param_key = item_tuple
                param_value = getattr(self.p, param_key, '')
                display_name = fmt_str.format(param_value)
            elif len(item_tuple) == 5:
                attr, line, display_name_direct, pane, opts = item_tuple
                display_name = display_name_direct
            else:
                print(f"Warning: Skipping misformatted item in _plottable_indicators_template: {item_tuple}")
                continue

            self._plottable_indicators.append(
                (attr, line, display_name, pane, opts)
            )

        print(f"Initialized CorrelatedSMACrossStrategy:")
        print(f"  - {self.d0_name}: Fast SMA({self.p.p_fast_d0}), Slow SMA({self.p.p_slow_d0})")
        print(f"  - {self.d1_name}: Fast SMA({self.p.p_fast_d1}), Slow SMA({self.p.p_slow_d1})")

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.datetime(0)
        print(f'{self.run_name} | {dt.isoformat()} | {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            asset_name = self.d0_name # Trades are only on data0
            dt = self.datas[0].datetime.datetime(0)
            if order.isbuy():
                self.log(f'BUY EXECUTED [{asset_name}], Price: {order.executed.price:.2f}, Size: {order.executed.size}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                self.signals.append({'type': 'buy', 'datetime': dt, 'price': order.executed.price})
            elif order.issell():
                self.log(f'SELL EXECUTED [{asset_name}], Price: {order.executed.price:.2f}, Size: {order.executed.size}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                self.signals.append({'type': 'sell', 'datetime': dt, 'price': order.executed.price})
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