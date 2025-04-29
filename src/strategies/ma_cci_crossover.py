import backtrader as bt
import datetime
# Adjust import path based on your project setup / PYTHONPATH
# If running main.py from the project root:
from indicators.correlation import PearsonR
# Or if src is in your path: from indicators.correlation import PearsonR


class MACrossOver(bt.Strategy):
    params = (
        ('ma', bt.ind.MovAv.SMA),
        ('pd1', 20),
        ('pd2', 20),
        # Add period for PearsonR if you want it configurable
        ('corr_period', 20),
        # --- CCI Indicator ---
        ('cci_period', 20),  # Period for CCI
        ('atr_period', 14),  # Period for ATR
        ('atr_multiplier', 1.5)
    )

    def __init__(self):
        # Keep references to datas for convenience
        self.spy = self.data0
        self.gld = self.data1

         # SPY Indicators
        self.sma_spy = self.p.ma(self.spy, period=self.p.pd1, plotmaster=self.spy)
        self.cci_spy = bt.ind.CommodityChannelIndex(self.spy, period=self.p.cci_period)
        self.atr_spy = bt.ind.AverageTrueRange(self.spy, period=self.p.atr_period, plotmaster=self.spy) # Keep ATR if needed later

        # GLD Indicators
        self.sma_gld = self.p.ma(self.gld, period=self.p.pd2, plotmaster=self.spy) # Plot GLD SMA on SPY's chart
        self.cci_gld = bt.ind.CommodityChannelIndex(self.gld, period=self.p.cci_period) # CCI for GLD

        # Cross-Asset Indicators
        self.correlation = PearsonR(self.spy, self.gld, period=self.p.corr_period)

        # Optional: Add levels to CCI plots for visual reference
        self.cci_spy.plotinfo.plotyhlines = [-20, 20, 70] # Add lines to SPY CCI plot
        self.cci_gld.plotinfo.plotyhlines = [-20, 20, 70] # Add lines to GLD CCI plot

        # Calculate minimum periods needed + a small buffer
        self.min_period = max(self.p.pd1, self.p.pd2, self.p.corr_period, self.p.cci_period, self.p.atr_period)
        self.warmup_bars = self.min_period + 5 # e.g., wait 5 bars after indicators are ready

        # To keep track of pending orders (optional but good practice)
        self.order = None

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.datetime(0) # Use system datetime
        print(f'{dt.isoformat()} | {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            self.bar_executed = len(self) # Bar number when order was executed

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order Canceled/Margin/Rejected: Status {order.getstatusname()}')

        # Write down: no pending order
        self.order = None   
    
    # Add a minimal next method to make the strategy complete
    def next(self):
         # --- Use datetime from data0 for consistency in logs ---
        current_dt = self.datas[0].datetime.datetime(0)
        
         # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            self.log(f'Pending order detected, skipping bar {len(self)}')
            return
        
        if len(self) < self.warmup_bars:
            return # Wait for all indicators and buffer period
        
        # --- Explicitly check position sizes for BOTH assets ---
        spy_position_size = self.getposition(self.spy).size
        gld_position_size = self.getposition(self.gld).size
        is_position_open = spy_position_size != 0 or gld_position_size != 0

        # --- Entry Logic ---
        if not is_position_open:
            # --- Potential SPY Long Entry ---
            spy_cci_cond = self.cci_spy[0] > 70
            spy_sma_cond = self.sma_spy[0] > self.sma_spy[-1]
            gld_sma_cond = self.sma_gld[0] < self.sma_gld[-1] # GLD SMA falling
            gld_cci_cond = self.cci_gld[0] < -20
            #pearson_cond = self.correlation[0] < -0.0

            if spy_cci_cond and spy_sma_cond and gld_sma_cond and gld_cci_cond:
                self.log(f'SPY LONG ENTRY SIGNAL: CCI_SPY={self.cci_spy[0]:.2f}, SMA_SPY Rising, SMA_GLD Falling, CCI_GLD={self.cci_gld[0]:.2f}')
                # --- Place Buy Order ---
                self.order = self.buy(data=self.spy)
                # Set stop price attribute *if* using a sizer that needs it
                # self.calculated_stop_price = potential_spy_stop

            # --- Potential GLD Long Entry ---
            # Only check if SPY entry didn't trigger and still no position
            else: # No SPY signal found, check GLD
                gld_cci_entry_cond = self.cci_gld[0] > 100
                gld_sma_rising_cond = self.sma_gld[0] > self.sma_gld[-1]
                spy_sma_falling_cond = self.sma_spy[0] < self.sma_spy[-1] # SPY SMA falling
                spy_cci_cond = self.cci_spy[0] < 0

                if gld_cci_entry_cond and gld_sma_rising_cond and spy_sma_falling_cond and spy_cci_cond:
                    self.log(f'GLD LONG ENTRY SIGNAL: CCI_GLD={self.cci_gld[0]:.2f}, SMA_GLD Rising, SMA_SPY Falling, CCI_SPY={self.cci_spy[0]:.2f}')
                    # --- Place Buy Order ---
                    self.order = self.buy(data=self.gld)
                    
        # --- Exit Logic ---
        else: # is_position_open is True
            # --- Check SPY Exit ---
            if spy_position_size != 0: # Check if specifically holding SPY
                #self.log(f'Position Check: In SPY. Checking exit. CCI_SPY={self.cci_spy[0]:.2f}') # Debug Log
                if self.cci_spy[0] < 20:
                    self.log(f'SPY LONG EXIT SIGNAL: CCI_SPY={self.cci_spy[0]:.2f} < 20')
                    self.order = self.close(data=self.spy) # Close SPY position

            # --- Check GLD Exit ---
            elif gld_position_size != 0: # Check if specifically holding GLD
                #self.log(f'Position Check: In GLD. Checking exit. CCI_GLD={self.cci_gld[0]:.2f}') # Debug Log
                if self.cci_gld[0] < 20:
                    self.log(f'GLD LONG EXIT SIGNAL: CCI_GLD={self.cci_gld[0]:.2f} < 20')
                    self.order = self.close(data=self.gld) # Close GLD position