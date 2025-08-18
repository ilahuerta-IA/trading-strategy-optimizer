# -----------------------------------------------------------------------------
# TRIBBHL2 FUNNEL STRATEGY (Backtrader)
# -----------------------------------------------------------------------------
# Disclaimer
# This code is for research and education only. It is NOT financial advice.
# Trading involves substantial risk. Backtest results are not indicative of
# future performance. Use at your own risk.
# -----------------------------------------------------------------------------
# Strategy idea
# Long-only "volatility funnel" breakout:
# - Over the last N bars, the confirmation EMA is strictly rising.
# - At the first bar of that window, the custom bands (built on EMA stdev) are
#   tight around the confirmation EMA (both sides close).
# - At the current bar, at least one side of the bands opens wide (expansion).
# - Optional: confirmation EMA is above fast/medium/slow EMAs across the window.
# - SL/TP derived from ATR. Optional time-based exit after M bars.
# - Real entries counted only on order fills (notify_order) and plotted by
#   Backtrader via bracket orders (parent + limit + stop).
# -----------------------------------------------------------------------------

import backtrader as bt
from pathlib import Path
import math
import csv
from datetime import datetime


# ==== CONFIGURATION SECTION ====
DATA_FILE = 'EURUSD_5m_8Yea.csv'
OPTIMIZATION_MODE = False

DEFAULT_PARAMS = {
    # EMA periods
    'ema_fast_period': 10,
    'ema_medium_period': 12,
    'ema_slow_period': 15,
    'ema_confirm_period': 1,
    # ATR settings
    'atr_period': 20,
    'atr_multiplier_sl': 1.0,
    'atr_multiplier_tp': 7.6,
    # Funnel band (StdDev over EMA blend)
    'bb_stdev_period': 10,
    'bb_upper_pips': 50,       # loosen tightness to increase candidates
    'bb_lower_pips': 50,
    'bb_min_open_pips': 5,     # small open threshold
    # Window and exits
    'confirm_bars': 2,         # looser rising requirement
    'time_exit_bars': 4,       # bars in position before time-based close
    # Filters / flags
    'use_ema_order_filter': False,  # disable to widen entries
    'enable_time_exit': True,
    'enable_risk_sizing': True,    # risk-based position sizing using risk_percent
    # Risk, pip, misc
    'risk_percent': 0.01,
    'pip_value': 0.0001,           # 0.0001 for most FX; 0.01 for JPY pairs
    'enable_long_entries': True,
    'cooldown_bars': 3,            # optional re-entry throttle
    'verbose': False,
    # Research logging (set enable_research=True to log)
    'enable_research': False,          # log features and outcomes
    'research_mode': 'signal',         # 'signal' (on entry) or 'bar' (every bar)
    'research_output': 'research/funnel_signals.csv',
    # Study mode (no orders): label fixed-horizon outcomes
    'study_mode': False,              # if True, do not place orders, just log signals and forward outcomes
    'study_exit_bars': 5,             # horizon for forward return labeling
    'study_ignore_funnel': True,      # in study_mode, only require rising EMA, ignore funnel/order filters
    # Filter candidates (disabled by default)
    'min_open_ratio': 0.0,             # require expansion ratio >= this value
    'allow_hours': (),                 # tuple of hours (0-23) allowed; empty disables filter
    'allow_dow': (),                   # tuple of weekdays (Mon=0..Sun=6) allowed; empty disables filter
}

OPTIMIZATION_PARAMS = {
    'ema_fast_period': [5, 7, 9],
    'ema_medium_period': [9, 11],
    'ema_slow_period': [14, 18],
    'ema_confirm_period': [3, 5, 8],
    'atr_period': [10, 14, 21],
    'atr_multiplier_sl': [1.0, 1.5, 2.0],
    'atr_multiplier_tp': [2.0, 2.5, 3.0, 3.5],
    'confirm_bars': [2, 3, 4],
    'time_exit_bars': [4, 5, 6],
    'bb_upper_pips': [8, 10, 12, 15],
    'bb_lower_pips': [8, 10, 12, 15],
    'bb_min_open_pips': [18, 22, 25, 30],
    'use_ema_order_filter': [True, False],
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
        raise SystemExit(1)
except Exception:
    print("FATAL: Could not determine project paths. Run from project root.")
    raise SystemExit(1)


class MedianPrice(bt.Indicator):
    lines = ('median',)
    plotinfo = dict(subplot=False, plotname='Median Price (H+L)/2')
    def next(self):
        self.lines.median[0] = (self.data.high[0] + self.data.low[0]) / 2.0


class StatsDict(dict):
    """
    Dict-like counter that is robust to accidental append() calls.
    - Missing keys default to 0 for +={1} patterns
    - append(item) stores items in an internal log list for debugging
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._events = []
    def __missing__(self, key):
        return 0
    def append(self, item):  # tolerate list-like usage
        self._events.append(item)
    @property
    def events(self):
        return list(self._events)


class Tribbhl2FunnelStrategy(bt.Strategy):
    params = (
        # EMA periods
        ('ema_fast_period', DEFAULT_PARAMS['ema_fast_period']),
        ('ema_medium_period', DEFAULT_PARAMS['ema_medium_period']),
        ('ema_slow_period', DEFAULT_PARAMS['ema_slow_period']),
        ('ema_confirm_period', DEFAULT_PARAMS['ema_confirm_period']),
        # ATR
        ('atr_period', DEFAULT_PARAMS['atr_period']),
        ('atr_multiplier_sl', DEFAULT_PARAMS['atr_multiplier_sl']),
        ('atr_multiplier_tp', DEFAULT_PARAMS['atr_multiplier_tp']),
        # Funnel stddev
        ('bb_stdev_period', DEFAULT_PARAMS['bb_stdev_period']),
        ('bb_upper_pips', DEFAULT_PARAMS['bb_upper_pips']),
        ('bb_lower_pips', DEFAULT_PARAMS['bb_lower_pips']),
        ('bb_min_open_pips', DEFAULT_PARAMS['bb_min_open_pips']),
        # Window and exits
        ('confirm_bars', DEFAULT_PARAMS['confirm_bars']),
        ('time_exit_bars', DEFAULT_PARAMS['time_exit_bars']),
        # Flags
        ('use_ema_order_filter', DEFAULT_PARAMS['use_ema_order_filter']),
        ('enable_time_exit', DEFAULT_PARAMS['enable_time_exit']),
        ('enable_risk_sizing', DEFAULT_PARAMS['enable_risk_sizing']),
    ('enable_funnel_gate', True),  # allow disabling tight-then-open funnel gate for experimentation
        # Risk / misc
        ('risk_percent', DEFAULT_PARAMS['risk_percent']),
        ('pip_value', DEFAULT_PARAMS['pip_value']),
        ('enable_long_entries', DEFAULT_PARAMS['enable_long_entries']),
        ('cooldown_bars', DEFAULT_PARAMS['cooldown_bars']),
        ('verbose', DEFAULT_PARAMS['verbose']),
    # Research
    ('enable_research', DEFAULT_PARAMS['enable_research']),
    ('research_mode', DEFAULT_PARAMS['research_mode']),
    ('research_output', DEFAULT_PARAMS['research_output']),
    ('study_mode', DEFAULT_PARAMS['study_mode']),
    ('study_exit_bars', DEFAULT_PARAMS['study_exit_bars']),
    ('study_ignore_funnel', DEFAULT_PARAMS['study_ignore_funnel']),
    ('asset_label', ''),
    # Filters
    ('min_open_ratio', DEFAULT_PARAMS['min_open_ratio']),
    ('allow_hours', DEFAULT_PARAMS['allow_hours']),
    ('allow_dow', DEFAULT_PARAMS['allow_dow']),
    # Extra research-derived filters (None disables)
    ('filter_divergence_max', None),        # e.g., 5.0 pips
    ('filter_band_pos_abs_max', None),      # e.g., 0.6 normalized band position
    )

    def __init__(self):
        # Indicators
        self.median = MedianPrice(self.data)
        self.ema_fast = bt.ind.EMA(self.median.median, period=self.p.ema_fast_period)
        self.ema_medium = bt.ind.EMA(self.median.median, period=self.p.ema_medium_period)
        self.ema_slow = bt.ind.EMA(self.median.median, period=self.p.ema_slow_period)
        self.ema_confirm = bt.ind.EMA(self.median.median, period=self.p.ema_confirm_period)

        self.atr = bt.ind.ATR(period=self.p.atr_period)

        # Funnel bands: StdDev over EMA blend
        ema_blend = (self.ema_fast + self.ema_medium + self.ema_slow) / 3.0
        stdev = bt.ind.StdDev(ema_blend, period=self.p.bb_stdev_period)
        self.bb_upper = self.ema_confirm + (stdev * 2.0)
        self.bb_lower = self.ema_confirm - (stdev * 2.0)

        # Orders & state
        self.stop_order = None
        self.limit_order = None
        self.order_pending = False
        self.bars_in_position = 0
        self.cooldown = 0

        # Stats
        self.num_closed_trades = 0
        self.num_won_trades = 0
        self.num_lost_trades = 0
        self.gross_profit = 0.0
        self.gross_loss = 0.0

        # Diagnostics for gating (avoid clashing with Backtrader's Strategy.stats)
        self.gate_stats = StatsDict({
            'ascending_fail': 0,
            'tight_fail': 0,
            'open_fail': 0,
            'order_filter_fail': 0,
            'hour_filter_fail': 0,
            'dow_filter_fail': 0,
            'openratio_fail': 0,
            'size_fail': 0,
            'entries': 0,
        })

        if self.p.verbose:
            print(f"Funnel Flags: ema_order={self.p.use_ema_order_filter} time_exit={self.p.enable_time_exit} risk_sizing={self.p.enable_risk_sizing}")

        # Research logging state
        self._pending_signal = None   # dict captured at entry until trade closes
        self._last_exit_reason = None # 'TimeExit' | 'Stop' | 'Limit' | None
        self.research_rows = []
        # Study queue: list of dicts with remaining bars to finalize forward outcome
        self._study_queue = []
        # Ensure research directory exists (best-effort)
        try:
            out_path = (Path(__file__).resolve().parent.parent.parent / self.p.research_output).resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    # --- Utility methods ---
    def _has_history(self, lookback: int) -> bool:
        try:
            _ = self.data.close[-lookback]
            return True
        except IndexError:
            return False

    def _ema_confirm_rising(self) -> bool:
        n = self.p.confirm_bars
        if n <= 0 or not self._has_history(n):
            return False
        # Strict increase: ema_confirm[0] > ema_confirm[1] > ... > ema_confirm[n-1]
        for i in range(n - 1):
            if not (self.ema_confirm[-i] > self.ema_confirm[-i - 1]):
                return False
        return True

    def _ema_order_ok(self) -> bool:
        if not self.p.use_ema_order_filter:
            return True
        n = self.p.confirm_bars
        if n <= 0 or not self._has_history(n):
            return False
        for i in range(n):
            if not (self.ema_confirm[-i] > self.ema_fast[-i] and
                    self.ema_confirm[-i] > self.ema_medium[-i] and
                    self.ema_confirm[-i] > self.ema_slow[-i]):
                return False
        return True

    def _funnel_tight_then_open(self) -> bool:
        n = self.p.confirm_bars
        if n <= 0 or not self._has_history(n):
            return False
        first_idx = -(n - 1)
        # Tight at first bar of window
        dist_upper_first = abs(self.bb_upper[first_idx] - self.ema_confirm[first_idx]) / self.p.pip_value
        dist_lower_first = abs(self.bb_lower[first_idx] - self.ema_confirm[first_idx]) / self.p.pip_value
        tight_ok = (dist_upper_first < self.p.bb_upper_pips) and (dist_lower_first < self.p.bb_lower_pips)
        if not tight_ok:
            self.gate_stats['tight_fail'] += 1
            return False
        # Open at last (current) bar
        dist_upper_last = abs(self.bb_upper[0] - self.ema_confirm[0]) / self.p.pip_value
        dist_lower_last = abs(self.bb_lower[0] - self.ema_confirm[0]) / self.p.pip_value
        open_ok = (dist_upper_last > self.p.bb_min_open_pips) or (dist_lower_last > self.p.bb_min_open_pips)
        if not open_ok:
            self.gate_stats['open_fail'] += 1
        return open_ok

    def _compute_features(self):
        """Collects per-bar funnel features for research/analysis."""
        n = self.p.confirm_bars
        if n <= 0 or not self._has_history(n):
            return None
        first_idx = -(n - 1)
        # distances (pips)
        dist_upper_first = abs(self.bb_upper[first_idx] - self.ema_confirm[first_idx]) / self.p.pip_value
        dist_lower_first = abs(self.bb_lower[first_idx] - self.ema_confirm[first_idx]) / self.p.pip_value
        dist_upper_last = abs(self.bb_upper[0] - self.ema_confirm[0]) / self.p.pip_value
        dist_lower_last = abs(self.bb_lower[0] - self.ema_confirm[0]) / self.p.pip_value
        tight_ok = (dist_upper_first < self.p.bb_upper_pips) and (dist_lower_first < self.p.bb_lower_pips)
        open_ok = (dist_upper_last > self.p.bb_min_open_pips) or (dist_lower_last > self.p.bb_min_open_pips)
        # slopes
        confirm_slope = float(self.ema_confirm[0] - self.ema_confirm[first_idx])
        fast_slope = float(self.ema_fast[0] - self.ema_fast[first_idx])
        # hour/dow for seasonal effects
        dt = bt.num2date(self.data.datetime[0])
        hour = dt.hour
        dow = dt.weekday()
        # stdev and atr now
        atr_now = float(self.atr[0])
        stdev_now = float((self.bb_upper[0] - self.ema_confirm[0]) / 2.0)
        # flags
        rising_ok = self._ema_confirm_rising()
        order_ok = self._ema_order_ok()
        # ratios
        denom = max(1e-9, max(dist_upper_first, dist_lower_first))
        open_ratio = (max(dist_upper_last, dist_lower_last) / denom)
        # divergence (price to EMA confirm) and band metrics
        price = float(self.data.close[0])
        ema_c = float(self.ema_confirm[0])
        divergence_pips = abs(price - ema_c) / self.p.pip_value
        band_width_pips = float(dist_upper_last + dist_lower_last)
        # Position within bands normalized to [-1,1] (0 = on EMA)
        if price >= ema_c:
            denom_pos = max(1e-9, float(self.bb_upper[0] - self.ema_confirm[0]))
            band_pos = (price - ema_c) / denom_pos
        else:
            denom_pos = max(1e-9, float(self.ema_confirm[0] - self.bb_lower[0]))
            band_pos = (price - ema_c) / denom_pos
        band_pos = max(-5.0, min(5.0, band_pos))  # clamp extremes
        return {
            'asset': self.p.asset_label or '',
            'datetime': dt.strftime('%Y-%m-%d %H:%M:%S'),
            'hour': hour,
            'dow': dow,
            'atr_now': atr_now,
            'stdev_now': stdev_now,
            'dist_upper_first': float(dist_upper_first),
            'dist_lower_first': float(dist_lower_first),
            'dist_upper_last': float(dist_upper_last),
            'dist_lower_last': float(dist_lower_last),
            'tight_ok': bool(tight_ok),
            'open_ok': bool(open_ok),
            'rising_ok': bool(rising_ok),
            'order_ok': bool(order_ok),
            'confirm_slope': float(confirm_slope),
            'fast_slope': float(fast_slope),
            'price': price,
            'open_ratio': float(open_ratio),
            'divergence_pips': float(divergence_pips),
            'band_width_pips': float(band_width_pips),
            'band_pos': float(band_pos),
        }

    def _calc_size(self, stop_price: float) -> int:
        if not self.p.enable_risk_sizing:
            return 1
        risk_value = self.broker.get_value() * self.p.risk_percent
        entry_price = float(self.data.close[0])
        per_unit_risk = abs(entry_price - stop_price)
        if per_unit_risk <= 0:
            return 0
        return max(0, math.floor(risk_value / per_unit_risk))

    def next(self):
        # cooldown
        if self.cooldown > 0:
            self.cooldown -= 1
            return
        if self.order_pending:
            return

        # Research: per-bar capture (can generate large files)
        if self.p.enable_research and self.p.research_mode == 'bar':
            feats = self._compute_features()
            if feats is not None:
                feats['kind'] = 'bar'
                self.research_rows.append(feats)

        # Study mode: decrement and finalize pending signals
        if self.p.study_mode and self._study_queue:
            new_queue = []
            for item in self._study_queue:
                item['remaining'] -= 1
                if item['remaining'] <= 0:
                    # finalize at current bar
                    entry_price = item['entry_price']
                    # forward return
                    fwd_return_pips = (float(self.data.close[0]) - entry_price) / self.p.pip_value
                    # compute MFE/MAE over the window [entry..now]
                    win = item['window']
                    # at finalize, entry is -win bars ago
                    mfe_pips = 0.0
                    mae_pips = 0.0
                    try:
                        max_high = float(self.data.high[-win])
                        min_low = float(self.data.low[-win])
                        for k in range(win + 1):
                            idx = -win + k
                            h = float(self.data.high[idx])
                            l = float(self.data.low[idx])
                            if h > max_high: max_high = h
                            if l < min_low: min_low = l
                        mfe_pips = (max_high - entry_price) / self.p.pip_value
                        mae_pips = (entry_price - min_low) / self.p.pip_value
                    except IndexError:
                        pass
                    row = dict(item['features'])
                    row.update({
                        'kind': 'study',
                        'entry_price': float(entry_price),
                        'fwd_return_pips': float(fwd_return_pips),
                        'mfe_pips': float(mfe_pips),
                        'mae_pips': float(mae_pips),
                        'horizon_bars': int(win),
                    })
                    self.research_rows.append(row)
                else:
                    new_queue.append(item)
            self._study_queue = new_queue

        # Time-based exit when in position
        if self.position and not self.p.study_mode:
            self.bars_in_position += 1
            if self.p.enable_time_exit and self.bars_in_position >= self.p.time_exit_bars:
                if self.p.verbose:
                    print(f"TIME EXIT {self.data.datetime.date(0)} after {self.bars_in_position} bars")
                # Close position: cancel children to avoid conflicts, then close
                if self.stop_order:
                    try:
                        self.cancel(self.stop_order)
                    except Exception:
                        pass
                    self.stop_order = None
                if self.limit_order:
                    try:
                        self.cancel(self.limit_order)
                    except Exception:
                        pass
                    self.limit_order = None
                self._last_exit_reason = 'TimeExit'
                self.close()
            return

        # Validate inputs
        if not self.p.enable_long_entries:
            return
        if not self._has_history(max(self.p.confirm_bars, self.p.atr_period, self.p.bb_stdev_period)):
            return

        # Gating conditions
        if not self._ema_confirm_rising():
            self.gate_stats['ascending_fail'] += 1
            return
        # In study mode with ignore_funnel, skip the rest of gating to collect more signals
        if not (self.p.study_mode and self.p.study_ignore_funnel):
            if not self._ema_order_ok():
                self.gate_stats['order_filter_fail'] += 1
                return
            if self.p.enable_funnel_gate:
                if not self._funnel_tight_then_open():
                    return

        # Feature-based filters
        feats = self._compute_features()
        if feats is None:
            return
        # Feature filters only if not in study_ignore_funnel mode
        if not (self.p.study_mode and self.p.study_ignore_funnel):
            # Hour filter
            if self.p.allow_hours:
                hr = feats['hour']
                if hr not in self.p.allow_hours:
                    self.gate_stats['hour_filter_fail'] += 1
                    return
            # Day-of-week filter
            if self.p.allow_dow:
                dow = feats['dow']
                if dow not in self.p.allow_dow:
                    self.gate_stats['dow_filter_fail'] += 1
                    return
            # Open ratio filter
            if self.p.min_open_ratio and feats.get('open_ratio', 0.0) < float(self.p.min_open_ratio):
                self.gate_stats['openratio_fail'] += 1
                return
            # Research-derived feature filters
            if self.p.filter_divergence_max is not None:
                if feats.get('divergence_pips', 0.0) > float(self.p.filter_divergence_max):
                    return
            if self.p.filter_band_pos_abs_max is not None:
                if abs(feats.get('band_pos', 0.0)) > float(self.p.filter_band_pos_abs_max):
                    return

        # Precompute prices for research and potential orders
        atr_now = float(self.atr[0])
        stop_price = float(self.data.low[0]) - (atr_now * self.p.atr_multiplier_sl)
        limit_price = float(self.data.high[0]) + (atr_now * self.p.atr_multiplier_tp)

        # Research: capture features for this signal
        if self.p.enable_research and self.p.research_mode == 'signal':
            feats_sig = dict(feats)
            feats_sig.update({
                'kind': 'signal',
                'entry_rr': (self.p.atr_multiplier_tp / self.p.atr_multiplier_sl) if self.p.atr_multiplier_sl else 0,
                'calc_stop': float(stop_price),
                'calc_limit': float(limit_price),
            })
            if self.p.study_mode:
                # queue for forward labeling (no size gating)
                self._study_queue.append({
                    'remaining': int(self.p.study_exit_bars),
                    'window': int(self.p.study_exit_bars),
                    'entry_price': float(self.data.close[0]),
                    'features': feats_sig,
                })
            else:
                self._pending_signal = feats_sig

        # Live orders only when not in study mode
        if not self.p.study_mode:
            size = self._calc_size(stop_price)
            if size <= 0:
                self.gate_stats['size_fail'] += 1
                return
            if self.p.verbose:
                rr = (self.p.atr_multiplier_tp / self.p.atr_multiplier_sl) if self.p.atr_multiplier_sl else 0
                print(f"ENTRY LONG {self.data.datetime.date(0)} Price={self.data.close[0]:.5f} Size={size} RR≈{rr:.2f}")
            parent, tp, sl = self.buy_bracket(size=size, limitprice=limit_price, stopprice=stop_price)
            self.limit_order = tp
            self.stop_order = sl
            self.order_pending = True

    # --- Notifications ---
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                if self.p.verbose:
                    print(f"LONG FILLED {order.executed.price:.5f} size={order.executed.size}")
                self.gate_stats['entries'] += 1
                self.bars_in_position = 0
                if self._pending_signal is not None:
                    self._pending_signal['filled_price'] = float(order.executed.price)
                    self._pending_signal['filled_size'] = int(order.executed.size)
            elif order.issell():
                # A child order completed
                if order == self.stop_order:
                    self.stop_order = None
                    self._last_exit_reason = 'Stop'
                if order == self.limit_order:
                    self.limit_order = None
                    self._last_exit_reason = 'Limit'
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if order == self.stop_order:
                self.stop_order = None
            if order == self.limit_order:
                self.limit_order = None
        # parent completes immediately in many brokers; release pending flag
        self.order_pending = False

    def notify_trade(self, trade):
        if trade.isclosed:
            self.num_closed_trades += 1
            pnl = float(trade.pnlcomm)
            if pnl > 0:
                self.num_won_trades += 1
                self.gross_profit += pnl
            else:
                self.num_lost_trades += 1
                self.gross_loss += abs(pnl)
            self.cooldown = self.p.cooldown_bars
            if self.p.verbose:
                print(f"TRADE CLOSED #{self.num_closed_trades} PnL=${pnl:.2f}")
            # Research: finalize row
            if self.p.enable_research and self._pending_signal is not None:
                row = dict(self._pending_signal)
                row.update({
                    'exit_reason': self._last_exit_reason,
                    'pnl': pnl,
                    'bars_held': int(self.bars_in_position),
                })
                self.research_rows.append(row)
                self._pending_signal = None
                self._last_exit_reason = None

    def stop(self):
        if self.p.verbose:
            print("\n=== FUNNEL STRATEGY STOPPED ===")
            print(f"Trades: {self.num_closed_trades} Wins: {self.num_won_trades} Losses: {self.num_lost_trades}")
            if self.gross_loss > 0:
                pf = self.gross_profit / self.gross_loss
                print(f"Profit Factor: {pf:.2f}")
            if self.num_closed_trades > 0:
                wr = (self.num_won_trades / self.num_closed_trades) * 100.0
                print(f"Win Rate: {wr:.2f}%")
            print("Gating stats:")
            for k, v in self.gate_stats.items():
                print(f"  {k}: {v}")
            if getattr(self.gate_stats, 'events', None):
                print(f"  events_logged: {len(self.gate_stats.events)}")

        # Write research CSV
        if self.p.enable_research and self.research_rows:
            out_path = (Path(__file__).resolve().parent.parent.parent / self.p.research_output).resolve()
            # union of keys
            keys = set()
            for r in self.research_rows:
                keys.update(r.keys())
            fieldnames = sorted(keys)
            try:
                with open(out_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for r in self.research_rows:
                        writer.writerow(r)
                if self.p.verbose:
                    print(f"Research CSV written: {out_path}")
            except Exception as e:
                print(f"Failed to write research CSV: {e}")


# --- Execution ---
if __name__ == '__main__':
    cerebro = bt.Cerebro(runonce=False, optreturn=False)
    if OPTIMIZATION_MODE:
        cerebro.optstrategy(
            Tribbhl2FunnelStrategy,
            ema_fast_period=OPTIMIZATION_PARAMS['ema_fast_period'],
            ema_medium_period=OPTIMIZATION_PARAMS['ema_medium_period'],
            ema_slow_period=OPTIMIZATION_PARAMS['ema_slow_period'],
            ema_confirm_period=OPTIMIZATION_PARAMS['ema_confirm_period'],
            atr_period=OPTIMIZATION_PARAMS['atr_period'],
            atr_multiplier_sl=OPTIMIZATION_PARAMS['atr_multiplier_sl'],
            atr_multiplier_tp=OPTIMIZATION_PARAMS['atr_multiplier_tp'],
            confirm_bars=OPTIMIZATION_PARAMS['confirm_bars'],
            time_exit_bars=OPTIMIZATION_PARAMS['time_exit_bars'],
            bb_upper_pips=OPTIMIZATION_PARAMS['bb_upper_pips'],
            bb_lower_pips=OPTIMIZATION_PARAMS['bb_lower_pips'],
            bb_min_open_pips=OPTIMIZATION_PARAMS['bb_min_open_pips'],
            use_ema_order_filter=OPTIMIZATION_PARAMS['use_ema_order_filter'],
            verbose=[False],
        )
    else:
        # Enable research mode for broad dataset; no restrictive filters here
        cerebro.addstrategy(
            Tribbhl2FunnelStrategy,
            enable_research=True,
            research_mode='signal',
        )

    data = bt.feeds.GenericCSVData(
        dataname=str(DATA_PATH), dtformat=('%Y%m%d'), tmformat=('%H:%M:%S'),
        datetime=0, time=1, open=2, high=3, low=4, close=5, volume=6,
        timeframe=bt.TimeFrame.Minutes, compression=5)

    cerebro.adddata(data)
    cerebro.broker.setcash(BROKER_CONFIG['start_cash'])
    cerebro.broker.setcommission(leverage=BROKER_CONFIG['leverage'])
    print("=== TRIBBHL2 FUNNEL MODE ===")
    results = cerebro.run()
    print(f"Final Value: {cerebro.broker.getvalue():,.2f}")
    try:
        cerebro.plot(style='line', volume=False)
    except Exception as e:
        print(f"Plot failed: {e}")
