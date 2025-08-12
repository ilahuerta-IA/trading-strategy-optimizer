# -----------------------------------------------------------------------------
# TRIEMAHL2 PRO TRADING STRATEGY (Extended / Optional Entry Filters)
# -----------------------------------------------------------------------------
# Based on original triemahl2.py. Adds toggleable entry filter options so you can
# enable/disable components without modifying core logic:
#   - enable_two_stage: classic 2-step crossover confirmation (Stage1 + Stage2)
#   - enable_strict_order: require Fast > Medium > Slow ordering
#   - enable_trend_filter: require all EMAs above baseline (EMA or optional SMA)
#   - use_sma_entry: replace entry EMA with SMA for baseline filter
#   - enable_angle_divergence_limits: enforce max angle divergence thresholds
# All new flags default to True (matching original behaviour) except use_sma_entry.
# -----------------------------------------------------------------------------

import backtrader as bt
import numpy as np
from pathlib import Path
import math

# === CONFIGURATION SECTION (same defaults as original) ===
DATA_FILE =  'GBPUSD_5m_8Yea.csv' #'GBPUSD_5m_8Yea.csv'#'GBPUSD_5m_2Mon.csv' GBPUSD_5m_8Yea.csv
OPTIMIZATION_MODE = False

DEFAULT_PARAMS = {
    'ema_fast_period': 7,
    'ema_medium_period': 9,
    'ema_slow_period': 11,
    'exit_ema1_period': 5,
    'exit_ema2_period': 14,
    'entry_ema_period': 12,
    # Improved momentum threshold / divergence limits
    'min_angle_threshold': 48.0,          # tuned by grid: improves PF and entries
    'max_angle_divergence_fm': 3.0,       # was 4.0
    'max_angle_divergence_ms': 6.0,       # was 8.0
    'angle_validation_periods': 1,
    'risk_percent': 0.01,
    # Adjusted R multiple (approx 3R) to improve hit-rate vs extreme 5R
    'stop_loss_pips': 14.0,               # grid best
    'take_profit_pips': 24.0,             # grid best
    'pip_value': 0.0001,
    'enable_stop_loss': True,
    'enable_take_profit': True,
    'enable_ema_exit': False,
    'enable_long_entries': True,
    'cooldown_period': 1,                 # allow quicker re-entries in trends
    # --- New optional filters ---
    'enable_two_stage': True,
    'enable_strict_order': True,
    'enable_trend_filter': True,
    'use_sma_entry': True,
    'enable_angle_divergence_limits': True,
    # --- Commercial add-on filters (all off by default) ---
    'enable_delta_filter': True,          # Early ΔStd filter at holding==2
    'enable_percentile_filter': True,     # Percentile gating of ΔStd
    'keep_percent': 55,                   # grid best: keep top 55%
    'min_trades_for_threshold': 300,      # Calibration trades before percentile active
    'enable_angle_trailing': True,        # Contraction-based trailing exit
    'angle_trail_factor': 0.8,            # grid best
    'enable_max_hold': True,              # Max holding bars safety exit
    'max_hold_bars': 5,                   # Max post-entry bars (excluding entry)
    # Angle relaxation controls
    'angle_required_count': 1,            # relax multi-angle requirement to 1-of-3 (fast still mandatory)
    'enforce_angle_same_sign': True,      # keep sign coherence
    'use_fast_only_threshold': False,     # can set True later if still few entries
}

OPTIMIZATION_PARAMS = {  # unchanged placeholder (not expanded for new flags)
    'ema_fast_period': [7],
    'ema_medium_period': [9],
    'ema_slow_period': [11],
    'min_angle_threshold': [45.0],
    'max_angle_divergence_fm': [4.0],
    'max_angle_divergence_ms': [8.0],
    'angle_validation_periods': [1],
    'stop_loss_pips': [10.0],
    'take_profit_pips': [50.0],
    'risk_percent': [0.01],
}

BROKER_CONFIG = {
    'start_cash': 100000.0,
    'leverage': 30.0,
}

# --- Paths ---
try:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    DATA_PATH = PROJECT_ROOT / 'data' / DATA_FILE
    if not DATA_PATH.exists():
        print(f"FATAL: Data file not found at {DATA_PATH}")
        exit()
except Exception:
    print("FATAL: Could not determine project paths. Run from project root.")
    exit()

# --- Indicators ---
class MedianPriceIndicator(bt.Indicator):
    lines = ('median_price',)
    plotinfo = dict(subplot=False, plotname='Median Price (H+L)/2')
    def next(self):
        self.lines.median_price[0] = (self.data.high[0] + self.data.low[0]) / 2.0

class EMAAngleIndicator(bt.Indicator):
    lines = ('angle',)
    params = (('angle_lookback', 5), ('scale_factor', 50000))
    plotinfo = dict(subplot=True, plotname='EMA Angle (Degrees)')
    def __init__(self):
        self.addminperiod(self.p.angle_lookback)
        super().__init__()
    def next(self):
        try:
            rise = (self.data0[0] - self.data0[-self.p.angle_lookback + 1]) * self.p.scale_factor
            run = self.p.angle_lookback
            self.lines.angle[0] = np.degrees(np.arctan2(rise, run))
        except Exception:
            self.lines.angle[0] = 0.0

class Triemahl2ProStrategy(bt.Strategy):
    params = (
        ('ema_fast_period', DEFAULT_PARAMS['ema_fast_period']),
        ('ema_medium_period', DEFAULT_PARAMS['ema_medium_period']),
        ('ema_slow_period', DEFAULT_PARAMS['ema_slow_period']),
        ('exit_ema1_period', DEFAULT_PARAMS['exit_ema1_period']),
        ('exit_ema2_period', DEFAULT_PARAMS['exit_ema2_period']),
        ('entry_ema_period', DEFAULT_PARAMS['entry_ema_period']),
        ('min_angle_threshold', DEFAULT_PARAMS['min_angle_threshold']),
        ('max_angle_divergence_fm', DEFAULT_PARAMS['max_angle_divergence_fm']),
        ('max_angle_divergence_ms', DEFAULT_PARAMS['max_angle_divergence_ms']),
        ('angle_validation_periods', DEFAULT_PARAMS['angle_validation_periods']),
        ('risk_percent', DEFAULT_PARAMS['risk_percent']),
        ('stop_loss_pips', DEFAULT_PARAMS['stop_loss_pips']),
        ('take_profit_pips', DEFAULT_PARAMS['take_profit_pips']),
        ('pip_value', DEFAULT_PARAMS['pip_value']),
        ('enable_stop_loss', DEFAULT_PARAMS['enable_stop_loss']),
        ('enable_take_profit', DEFAULT_PARAMS['enable_take_profit']),
        ('enable_ema_exit', DEFAULT_PARAMS['enable_ema_exit']),
        ('enable_long_entries', DEFAULT_PARAMS['enable_long_entries']),
        ('cooldown_period', DEFAULT_PARAMS['cooldown_period']),
        # New flags
        ('enable_two_stage', DEFAULT_PARAMS['enable_two_stage']),
        ('enable_strict_order', DEFAULT_PARAMS['enable_strict_order']),
        ('enable_trend_filter', DEFAULT_PARAMS['enable_trend_filter']),
        ('use_sma_entry', DEFAULT_PARAMS['use_sma_entry']),
        ('enable_angle_divergence_limits', DEFAULT_PARAMS['enable_angle_divergence_limits']),
    # Commercial add-on flags
    ('enable_delta_filter', DEFAULT_PARAMS['enable_delta_filter']),
    ('enable_percentile_filter', DEFAULT_PARAMS['enable_percentile_filter']),
    ('keep_percent', DEFAULT_PARAMS['keep_percent']),
    ('min_trades_for_threshold', DEFAULT_PARAMS['min_trades_for_threshold']),
    ('enable_angle_trailing', DEFAULT_PARAMS['enable_angle_trailing']),
    ('angle_trail_factor', DEFAULT_PARAMS['angle_trail_factor']),
    ('enable_max_hold', DEFAULT_PARAMS['enable_max_hold']),
    ('max_hold_bars', DEFAULT_PARAMS['max_hold_bars']),
    # Angle relaxation params
    ('angle_required_count', DEFAULT_PARAMS['angle_required_count']),
    ('enforce_angle_same_sign', DEFAULT_PARAMS['enforce_angle_same_sign']),
    ('use_fast_only_threshold', DEFAULT_PARAMS['use_fast_only_threshold']),
        ('verbose', True),
    )

    def __init__(self):
        self.median_price = MedianPriceIndicator(self.data)
        # Primary EMAs
        self.ema_fast = bt.ind.EMA(self.median_price.median_price, period=self.p.ema_fast_period)
        self.ema_medium = bt.ind.EMA(self.median_price.median_price, period=self.p.ema_medium_period)
        self.ema_slow = bt.ind.EMA(self.median_price.median_price, period=self.p.ema_slow_period)
        # Exit EMAs
        self.exit_ema1 = bt.ind.EMA(self.median_price.median_price, period=self.p.exit_ema1_period)
        self.exit_ema2 = bt.ind.EMA(self.median_price.median_price, period=self.p.exit_ema2_period)
        # Baseline EMA or SMA
        self.entry_ema = bt.ind.EMA(self.median_price.median_price, period=self.p.entry_ema_period)
        self.entry_sma = bt.ind.SMA(self.median_price.median_price, period=self.p.entry_ema_period) if self.p.use_sma_entry else None
        # Angles
        self.angle_fast = EMAAngleIndicator(self.ema_fast, angle_lookback=self.p.ema_fast_period)
        self.angle_medium = EMAAngleIndicator(self.ema_medium, angle_lookback=self.p.ema_medium_period)
        self.angle_slow = EMAAngleIndicator(self.ema_slow, angle_lookback=self.p.ema_slow_period)
        # Visual crossovers
        self.entry_cross_fast_med = bt.ind.CrossOver(self.ema_fast, self.ema_medium)
        self.entry_cross_fast_slow = bt.ind.CrossOver(self.ema_fast, self.ema_slow)
        self.exit_crossover = bt.ind.CrossOver(self.exit_ema1, self.exit_ema2)
        # State
        self.crossover_detected = False
        self.cooldown_counter = 0
        self.stop_order = None
        self.profit_order = None
        self.order_pending = False
        self.buy_price = None
        self.sell_price = None
        # Stats
        self.num_closed_trades = 0
        self.num_won_trades = 0
        self.num_lost_trades = 0
        self.total_gross_profit = 0.0
        self.total_gross_loss = 0.0
        self.entry_angles = None
        self.entry_divergences = None
        self.exit_method = None
        self.verbose = self.p.verbose
        # Post-entry tracking for commercial filters
        self.post_std = []
        self.post_angle_diffs = []
        self.holding = 0               # number of post-entry bars (excludes entry bar)
        self.running_max_angle = None
        self.delta_history_positive = []  # learning store for positive ΔStd
        if self.verbose:
            print(f"Pro Strategy Flags: two_stage={self.p.enable_two_stage} strict_order={self.p.enable_strict_order} "
                  f"trend_filter={self.p.enable_trend_filter} sma_entry={self.p.use_sma_entry} divergence_limits={self.p.enable_angle_divergence_limits}")
            print(f"AddOn Filters: delta={self.p.enable_delta_filter} percentile={self.p.enable_percentile_filter} angle_trail={self.p.enable_angle_trailing} max_hold={self.p.enable_max_hold}")
        # Filter attrition counters (diagnostics)
        self.filter_stats = {
            'candidates': 0,          # raw potential (fast top) events
            'stage1_latched': 0,
            'stage2_fail': 0,
            'angle_fail': 0,
            'divergence_fail': 0,
            'strict_fail': 0,
            'trend_fail': 0,
            'long_disabled': 0,
            'size_fail': 0,
            'entries': 0
        }

    # --- Utility Methods ---
    def calculate_order_size(self, stop_price):
        risked_value = self.broker.get_value() * self.p.risk_percent
        entry_price = self.data.close[0]
        pnl_per_unit = abs(entry_price - stop_price)
        if pnl_per_unit <= 0:
            return 0
        raw = risked_value / pnl_per_unit
        size = math.floor(raw)
        return size

    def detect_stage1_crossover(self):
        current_fast_above = (self.ema_fast[0] > self.ema_medium[0] and self.ema_fast[0] > self.ema_slow[0])
        try:
            previous_fast_above = (self.ema_fast[-1] > self.ema_medium[-1] and self.ema_fast[-1] > self.ema_slow[-1])
        except IndexError:
            return False
        return current_fast_above and not previous_fast_above

    def validate_stage2_confirmation(self):
        return (self.ema_fast[0] > self.ema_medium[0] and self.ema_fast[0] > self.ema_slow[0])

    def validate_historical_angles(self):
        # Minimum history available check
        if (len(self.angle_fast.lines.angle) < self.p.angle_validation_periods or
            len(self.angle_medium.lines.angle) < self.p.angle_validation_periods or
            len(self.angle_slow.lines.angle) < self.p.angle_validation_periods):
            return False
        required = max(1, self.p.angle_required_count)
        for i in range(self.p.angle_validation_periods):
            idx = -1 - i
            try:
                a_f = self.angle_fast.lines.angle[idx]
                a_m = self.angle_medium.lines.angle[idx]
                a_s = self.angle_slow.lines.angle[idx]
            except (IndexError, ValueError):
                return False
            # Fast angle must always clear threshold (core momentum)
            if a_f <= self.p.min_angle_threshold:
                return False
            if self.p.use_fast_only_threshold:
                # Skip broader multi-angle thresholding
                if self.p.enforce_angle_same_sign and not ((a_f > 0 and a_m > 0) or (a_f < 0 and a_m < 0)):
                    return False
                continue
            positives = 0
            if a_f > self.p.min_angle_threshold: positives += 1
            if a_m > self.p.min_angle_threshold: positives += 1
            if a_s > self.p.min_angle_threshold: positives += 1
            if positives < required:
                return False
            if self.p.enforce_angle_same_sign and not ((a_f > 0 and a_m > 0) or (a_f < 0 and a_m < 0)):
                return False
        return True

    # --- Commercial helper methods ---
    def _percentile_active(self):
        if not (self.p.enable_percentile_filter and self.p.keep_percent < 100):
            return False
        return len(self.delta_history_positive) >= self.p.min_trades_for_threshold

    def _current_threshold(self):
        if not self._percentile_active():
            return None
        q = 1 - (self.p.keep_percent / 100.0)
        # Count accepted entries
        self.filter_stats['entries'] += 1
        return float(np.quantile(self.delta_history_positive, q))

        self.filter_stats['entries'] += 1
    def _manual_exit(self, reason:str):
        if self.verbose:
            print(f"MANUAL EXIT {reason} {self.data.datetime.date(0)}")
        if self.stop_order:
            try: self.cancel(self.stop_order)
            except Exception: pass
            self.stop_order = None
        if self.profit_order:
            try: self.cancel(self.profit_order)
            except Exception: pass
            self.profit_order = None
        self.exit_method = reason
        self.close()

    # --- Core Logic ---
    def next(self):
        if self.cooldown_counter > 0:
            self.cooldown_counter -= 1
            return
        if self.order_pending:
            return
        # Count raw structural candidates (fast above both others)
        if self.ema_fast[0] > self.ema_medium[0] and self.ema_fast[0] > self.ema_slow[0]:
            self.filter_stats['candidates'] += 1

        # Exit logic
        if self.position:
            # --- Post-entry metrics update (only if trade just filled previously) ---
            try:
                std_now = float(np.std([self.ema_fast[0], self.ema_medium[0], self.ema_slow[0]], ddof=0))
            except Exception:
                std_now = 0.0
            angle_diff = abs(self.angle_fast[0] - self.angle_slow[0])
            self.post_std.append(std_now)
            self.post_angle_diffs.append(angle_diff)
            self.holding += 1

            # Early ΔStd filter at holding==2
            if self.p.enable_delta_filter and self.holding == 2 and len(self.post_std) >= 2:
                delta_val = self.post_std[1] - self.post_std[0]
                if delta_val > 0:
                    # store for percentile learning (only positives like commercial)
                    self.delta_history_positive.append(delta_val)
                if delta_val <= 0:
                    return self._manual_exit('EarlyExitDeltaNeg')
                if self.p.enable_percentile_filter:
                    thr = self._current_threshold()
                    if thr is not None and delta_val < thr:
                        return self._manual_exit('EarlyExitBelowPercentile')
                # seed running max angle after passing early filter
                self.running_max_angle = angle_diff
                return  # wait next bar

            # Angle trailing from holding >=3
            if self.p.enable_angle_trailing and self.holding >= 3:
                prev_angle = self.post_angle_diffs[-2] if len(self.post_angle_diffs) >= 2 else angle_diff
                if self.running_max_angle is None or prev_angle > self.running_max_angle:
                    self.running_max_angle = prev_angle
                if (self.running_max_angle and
                        angle_diff <= self.p.angle_trail_factor * self.running_max_angle):
                    return self._manual_exit('AngleTrail')

            # Max hold safety
            if self.p.enable_max_hold and self.holding >= self.p.max_hold_bars:
                return self._manual_exit('MaxHold')

            # EMA exit (optional) evaluated after other exits so reason priority retained
            if self.p.enable_ema_exit and self.exit_crossover[0] < 0:
                return self._manual_exit('EMAExit')
            return

        # Validate indicators
        if any(map(np.isnan, [self.ema_fast[0], self.ema_medium[0], self.ema_slow[0], self.angle_fast[0], self.angle_medium[0], self.angle_slow[0]])):
            return

        # Two-stage or single-stage
        if self.p.enable_two_stage:
            if not self.crossover_detected:
                if self.detect_stage1_crossover():
                    self.filter_stats['stage1_latched'] += 1
                    self.crossover_detected = True
                return
            if not self.validate_stage2_confirmation():
                self.filter_stats['stage2_fail'] += 1
                self.crossover_detected = False
                return
        else:
            if not (self.ema_fast[0] > self.ema_medium[0] and self.ema_fast[0] > self.ema_slow[0]):
                return

        # Angle validation
        if not self.validate_historical_angles():
            self.filter_stats['angle_fail'] += 1
            self.crossover_detected = False
            return

        # Divergence limits (optional)
        angle_fast = self.angle_fast[0]
        angle_medium = self.angle_medium[0]
        angle_slow = self.angle_slow[0]
        div_fm = abs(angle_fast - angle_medium)
        div_ms = abs(angle_medium - angle_slow)
        if self.p.enable_angle_divergence_limits:
            if div_fm >= self.p.max_angle_divergence_fm or div_ms >= self.p.max_angle_divergence_ms:
                self.filter_stats['divergence_fail'] += 1
                self.crossover_detected = False
                return

        # Strict ordering (optional)
        if self.p.enable_strict_order and not (self.ema_fast[0] > self.ema_medium[0] > self.ema_slow[0]):
            self.filter_stats['strict_fail'] += 1
            self.crossover_detected = False
            return

        # Trend filter (optional) all above baseline
        if self.p.enable_trend_filter:
            baseline = self.entry_sma[0] if self.entry_sma is not None else self.entry_ema[0]
            if not (self.ema_fast[0] > baseline and self.ema_medium[0] > baseline and self.ema_slow[0] > baseline):
                self.filter_stats['trend_fail'] += 1
                self.crossover_detected = False
                return

        if not self.p.enable_long_entries:
            self.filter_stats['long_disabled'] += 1
            self.crossover_detected = False
            return

        # Order sizing & risk
        stop_price = self.data.close[0] - (self.p.stop_loss_pips * self.p.pip_value)
        size = self.calculate_order_size(stop_price)
        if size <= 0:
            self.filter_stats['size_fail'] += 1
            self.crossover_detected = False
            return

        profit_price = self.data.close[0] + (self.p.take_profit_pips * self.p.pip_value)
        stop_price = self.data.close[0] - (self.p.stop_loss_pips * self.p.pip_value)

        if self.verbose:
            entry_price = self.data.close[0]
            rr = (self.p.take_profit_pips / self.p.stop_loss_pips) if self.p.stop_loss_pips else 0
            print(f"ENTRY LONG {self.data.datetime.date(0)} Price={entry_price:.5f} Size={size} RR={rr:.2f}")
            print(f"  Angles F/M/S={angle_fast:.1f}/{angle_medium:.1f}/{angle_slow:.1f} Div FM/MS={div_fm:.1f}/{div_ms:.1f}")

        parent, tp, sl = self.buy_bracket(size=size, limitprice=profit_price, stopprice=stop_price)
        self.stop_order = sl
        self.profit_order = tp
        self.order_pending = True
        self.crossover_detected = False
        self.entry_angles = (angle_fast, angle_medium, angle_slow)
        self.entry_divergences = (div_fm, div_ms)
    # Entry submitted (will count only after fill)

    # --- Backtrader Notifications ---
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
                if self.verbose:
                    print(f"LONG FILLED {order.executed.price:.5f} size={order.executed.size}")
                if hasattr(self, 'filter_stats'):
                    self.filter_stats['entries'] += 1
                # Initialize post-entry tracking on actual fill
                self.post_std = []
                self.post_angle_diffs = []
                self.holding = 0
                self.running_max_angle = None
            elif order.issell():
                self.sell_price = order.executed.price
                if not self.exit_method:
                    if order == self.stop_order:
                        self.exit_method = 'Stop'
                    elif order == self.profit_order:
                        self.exit_method = 'TakeProfit'
                    else:
                        self.exit_method = 'Other'
                self.stop_order = None
                self.profit_order = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if order == self.stop_order: self.stop_order = None
            if order == self.profit_order: self.profit_order = None
        self.order_pending = False

    def notify_trade(self, trade):
        if trade.isclosed:
            self.num_closed_trades += 1
            pnl = trade.pnlcomm
            if pnl > 0:
                self.total_gross_profit += pnl
                self.num_won_trades += 1
            else:
                self.total_gross_loss += abs(pnl)
                self.num_lost_trades += 1
            self.cooldown_counter = self.p.cooldown_period
            if self.buy_price is not None and self.sell_price is not None:
                pnl_pips = (self.sell_price - self.buy_price) / self.p.pip_value
            else:
                pnl_pips = 0.0
            if self.verbose:
                print(f"TRADE CLOSED #{self.num_closed_trades} PnL=${pnl:.2f} ({pnl_pips:.1f} pips) Method={self.exit_method}")
            self.buy_price = None
            self.sell_price = None
            self.exit_method = None
            self.entry_angles = None
            self.entry_divergences = None

    def stop(self):
        if self.verbose:
            print(f"\n=== PRO STRATEGY STOPPED ===")
            print(f"Trades Closed: {self.num_closed_trades} Wins: {self.num_won_trades} Losses: {self.num_lost_trades}")
            if self.total_gross_loss > 0:
                pf = self.total_gross_profit / self.total_gross_loss
                print(f"Profit Factor: {pf:.2f}")
            if self.num_closed_trades > 0:
                win_rate = (self.num_won_trades / self.num_closed_trades) * 100.0
                print(f"Win Rate: {win_rate:.2f}%")
            # Diagnostic: filter attrition summary
            if hasattr(self, 'filter_stats'):
                print("Filter Attrition:")
                for k, v in self.filter_stats.items():
                    print(f"  {k}: {v}")
                try:
                    cand = self.filter_stats.get('candidates', 0) or 0
                    stage1 = self.filter_stats.get('stage1_latched', 0) or 0
                    entries = self.filter_stats.get('entries', 0) or 0
                    if cand > 0:
                        print(f"Conversion cand->stage1: {stage1/cand*100:.2f}%")
                    if stage1 > 0:
                        print(f"Conversion stage1->entry: {entries/stage1*100:.2f}%")
                except Exception:
                    pass

# --- EXECUTION ---
if __name__ == '__main__':
    cerebro = bt.Cerebro(runonce=False, optreturn=False)
    if OPTIMIZATION_MODE:
        cerebro.optstrategy(Triemahl2ProStrategy,
                            ema_fast_period=OPTIMIZATION_PARAMS['ema_fast_period'],
                            ema_medium_period=OPTIMIZATION_PARAMS['ema_medium_period'],
                            ema_slow_period=OPTIMIZATION_PARAMS['ema_slow_period'],
                            min_angle_threshold=OPTIMIZATION_PARAMS['min_angle_threshold'],
                            max_angle_divergence_fm=OPTIMIZATION_PARAMS['max_angle_divergence_fm'],
                            max_angle_divergence_ms=OPTIMIZATION_PARAMS['max_angle_divergence_ms'],
                            angle_validation_periods=OPTIMIZATION_PARAMS['angle_validation_periods'],
                            stop_loss_pips=OPTIMIZATION_PARAMS['stop_loss_pips'],
                            take_profit_pips=OPTIMIZATION_PARAMS['take_profit_pips'],
                            risk_percent=OPTIMIZATION_PARAMS['risk_percent'],
                            verbose=[False])
    else:
        cerebro.addstrategy(Triemahl2ProStrategy)

    data = bt.feeds.GenericCSVData(
        dataname=str(DATA_PATH), dtformat=('%Y%m%d'), tmformat=('%H:%M:%S'),
        datetime=0, time=1, open=2, high=3, low=4, close=5, volume=6,
        timeframe=bt.TimeFrame.Minutes, compression=5)
    cerebro.adddata(data)
    cerebro.broker.setcash(BROKER_CONFIG['start_cash'])
    cerebro.broker.setcommission(leverage=BROKER_CONFIG['leverage'])
    print("=== TRIEMAHL2 PRO MODE ===")
    results = cerebro.run()
    strat = results[0]
    print(f"Final Value: {cerebro.broker.getvalue():,.2f}")
    try:
        cerebro.plot(style='line', volume=False)
    except Exception as e:
        print(f"Plot failed: {e}")
