# strategies/ma_cci_crossover.py
import backtrader as bt
from indicators.correlation import PearsonR # Make sure this import is correct

class MACrossOver(bt.Strategy):
    params = (
        ('ma', bt.ind.MovAv.SMA),
        ('pd1', 50),
        ('pd2', 50),
        ('corr_period', 20),
        ('cci_period', 20),
        ('atr_period', 14),
        ('atr_multiplier', 1.5),
        ('run_name', 'default_ma_cci_run'),
         # --- Add CCI Exit Threshold ---
        ('cci_exit_level', 20)
    )

    def __init__(self):
        # References to data0 and data1 are fine
        self.d0 = self.data0 # Generic reference
        self.d1 = self.data1 # Generic reference

        # Get data feed names for logging
        self.d0_name = self.d0._name if hasattr(self.d0, '_name') else 'data0'
        self.d1_name = self.d1._name if hasattr(self.d1, '_name') else 'data1'

        # --- Determine Moving Average type ---
        if isinstance(self.p.ma, str):
            ma_name = self.p.ma.upper()
            if ma_name == 'SMA': selected_ma = bt.ind.MovAv.SMA
            elif ma_name == 'EMA': selected_ma = bt.ind.MovAv.EMA
            else:
                print(f"Warning: Unknown MA type '{self.p.ma}'. Defaulting to SMA.")
                selected_ma = bt.ind.MovAv.SMA
        else:
            selected_ma = self.p.ma

        # --- Setup Indicators ---
        self.sma_d0 = selected_ma(self.d0, period=self.p.pd1, plotmaster=self.d0)
        self.cci_d0 = bt.ind.CommodityChannelIndex(self.d0, period=self.p.cci_period)
        self.atr_d0 = bt.ind.AverageTrueRange(self.d0, period=self.p.atr_period) # Keep ATR if needed later

        self.sma_d1 = selected_ma(self.d1, period=self.p.pd2, plotmaster=self.d0)
        self.cci_d1 = bt.ind.CommodityChannelIndex(self.d1, period=self.p.cci_period)

        self.correlation = PearsonR(self.d0, self.d1, period=self.p.corr_period)

        # Plotting lines
        self.cci_d0.plotinfo.plotyhlines = [-100, 0, 100]
        self.cci_d1.plotinfo.plotyhlines = [-100, 0, 100]

        # Warmup calculation
        self.min_period = max(self.p.pd1, self.p.pd2, self.p.corr_period, self.p.cci_period, self.p.atr_period)
        self.warmup_bars = self.min_period + 5

        self.order = None # Track pending orders
        self.run_name = self.p.run_name

        print(f"Initialized MACrossOver Strategy:")
        print(f"  - {self.d0_name}: MA({self.p.ma}/{self.p.pd1}), CCI({self.p.cci_period}), ExitCCI(<{self.p.cci_exit_level})")
        print(f"  - {self.d1_name}: MA({self.p.ma}/{self.p.pd2}), CCI({self.p.cci_period}), ExitCCI(<{self.p.cci_exit_level})")
        print(f"  - Correlation Period: {self.p.corr_period}")

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        print(f'{self.run_name} | {dt.isoformat()} | {txt}')

    def notify_order(self, order):
        asset_name = order.data._name if hasattr(order.data, '_name') else 'UnknownData'

        if order.status in [order.Submitted, order.Accepted]:
            # An order is active, strategy should wait
            self.log(f'Order {order.getstatusname()} [{asset_name}] Ref: {order.ref}')
            # Keep self.order = order # Do NOT reset self.order here
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED [{asset_name}], Ref: {order.ref}, Price: {order.executed.price:.2f}, Size: {order.executed.size}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            elif order.issell():
                 self.log(f'SELL EXECUTED [{asset_name}], Ref: {order.ref}, Price: {order.executed.price:.2f}, Size: {order.executed.size}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            # Log position size after execution
            pos_d0 = self.getposition(self.d0).size
            pos_d1 = self.getposition(self.d1).size
            self.log(f'Post-Exec Position: {self.d0_name}={pos_d0}, {self.d1_name}={pos_d1}')

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order Canceled/Margin/Rejected [{asset_name}] Ref: {order.ref}, Status: {order.getstatusname()}')

        # Reset self.order ONLY when the order is definitively finished (completed, canceled, rejected)
        self.order = None

    def next(self):
        # --- 1. Check if an order is pending ---
        if self.order:
            self.log(f"Pending order (Ref: {self.order.ref}), skipping bar.")
            return # Do nothing if an order is pending

        # --- 2. Wait for warmup period ---
        if len(self) < self.warmup_bars:
            return

        # --- 3. Get current position status ---
        pos_d0 = self.getposition(self.d0)
        pos_d1 = self.getposition(self.d1)

        # --- 4. Decision Logic ---

        # --- Exit Logic (Check First) ---
        # Check exit condition for d0 if position exists
        if pos_d0.size != 0:
            # Log current status for debugging exit
            self.log(f"Holding {self.d0_name} ({pos_d0.size}). Checking exit. CCI={self.cci_d0[0]:.2f} vs <{self.p.cci_exit_level}")
            if self.cci_d0[0] < self.p.cci_exit_level:
                self.log(f'SELL CREATE (Close) [{self.d0_name}] Signal: CCI < {self.p.cci_exit_level}')
                self.order = self.close(data=self.d0) # Close d0
                return # Exit submitted, do nothing else this bar

        # Check exit condition for d1 if position exists (using elif assumes we only hold one at a time)
        elif pos_d1.size != 0:
            # Log current status for debugging exit
            self.log(f"Holding {self.d1_name} ({pos_d1.size}). Checking exit. CCI={self.cci_d1[0]:.2f} vs <{self.p.cci_exit_level}")
            if self.cci_d1[0] < self.p.cci_exit_level:
                self.log(f'SELL CREATE (Close) [{self.d1_name}] Signal: CCI < {self.p.cci_exit_level}')
                self.order = self.close(data=self.d1) # Close d1
                return # Exit submitted, do nothing else this bar

        # --- Entry Logic (Only if NOT in market and NO order is pending) ---
        # (The order pending check is at the top, if we are here, self.order is None)
        # We only enter if *both* positions are zero.
        if pos_d0.size == 0 and pos_d1.size == 0:
            # Check D0 Buy Signal Conditions
            d0_cci_cond = self.cci_d0[0] > 70
            d0_sma_cond = self.sma_d0[0] > self.sma_d0[-1]
            d1_sma_cond = self.sma_d1[0] < self.sma_d1[-1]
            d1_cci_cond = self.cci_d1[0] < -70
            pearson_cond = self.correlation[0] < -0.8

            if d0_cci_cond and d0_sma_cond and d1_sma_cond and d1_cci_cond and pearson_cond:
                self.log(f'BUY CREATE [{self.d0_name}] Signal: CCI>70, SMA Up, {self.d1_name} SMA Down, CCI<-20, Corr<-0.8')
                self.order = self.buy(data=self.d0) # Buy d0
                # No return here, let D1 check proceed if D0 didn't trigger

            # Check D1 Buy Signal Conditions (Only if D0 conditions were not met)
            if self.order is None: # Check if D0 buy order was placed above
                d1_cci_entry_cond = self.cci_d1[0] > 70
                d1_sma_rising_cond = self.sma_d1[0] > self.sma_d1[-1]
                d0_sma_falling_cond = self.sma_d0[0] < self.sma_d0[-1]
                d0_cci_cond_entry2 = self.cci_d0[0] < -70
                # pearson_cond is the same as calculated above

                if d1_cci_entry_cond and d1_sma_rising_cond and d0_sma_falling_cond and d0_cci_cond_entry2 and pearson_cond:
                    self.log(f'BUY CREATE [{self.d1_name}] Signal: CCI>70, SMA Up, {self.d0_name} SMA Down, CCI<-20, Corr<-0.8')
                    self.order = self.buy(data=self.d1) # Buy d1

        # If we are here and have a position, it means exit conditions were not met
        # elif pos_d0.size != 0 or pos_d1.size != 0:
            # self.log(f"Holding Position - No Exit Signal. Pos D0: {pos_d0.size}, Pos D1: {pos_d1.size}")

    def stop(self):
        # Log final portfolio value at the end of the backtest
        final_value = self.broker.getvalue()
        self.log(f'Ending Portfolio Value: {final_value:.2f}')