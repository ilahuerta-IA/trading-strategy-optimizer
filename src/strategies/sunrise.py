"""Sunrise Strategy (no CLI) with trailing stop and USD PnL logging.

Trailing logic (green candle only): trail stop to open + (close-open)*factor
where factor = trailing_body_factor (0 < f <= 1). For f=1 we nudge just below
close. Initial SL/TP still ATR-based; only dynamic trails use body fraction.

Edit configuration at bottom of the file to change data path, dates, capital
or override strategy parameters. All previous CLI flags removed.
"""

import math
import backtrader as bt


class Sunrise(bt.Strategy):
    params = dict(
        ema_fast_length=16,
        ema_medium_length=18,
        ema_slow_length=20,
        ema_confirm_length=1,
        atr_length=20,
        atr_sl_multiplier=1.5,
        atr_tp_multiplier=3.5,
        bar_count_exit=7,
        ema_filter_price_length=50,
        ema_exit_length=25,
        min_angle=55.0,
        angle_scale_factor=10000.0,
        use_ema_order_condition=False,
        use_price_filter_ema=True,
        use_angle_filter=True,
        use_bar_count_exit=True,
        use_ema_crossover_exit=True,
        use_trailing_stop=False,
        trailing_body_factor=0.5,  # 0<f<=1 fraction of body
        print_signals=True,
        size=1,
        pip_value=0.0001,
        contract_size=100000,
        enable_risk_sizing=True,
        risk_percent=0.01,
    )

    @staticmethod
    def _cross_above(a, b):
        try:
            return a[0] > b[0] and a[-1] <= b[-1]
        except IndexError:
            return False

    def _angle(self):
        try:
            rise = (self.ema_confirm[0] - self.ema_confirm[-1]) * self.p.angle_scale_factor
            return math.degrees(math.atan(rise))
        except Exception:
            return float('nan')

    def __init__(self):
        d = self.data
        self.ema_fast = bt.ind.EMA(d.close, period=self.p.ema_fast_length)
        self.ema_medium = bt.ind.EMA(d.close, period=self.p.ema_medium_length)
        self.ema_slow = bt.ind.EMA(d.close, period=self.p.ema_slow_length)
        self.ema_confirm = bt.ind.EMA(d.close, period=self.p.ema_confirm_length)
        self.ema_filter_price = bt.ind.EMA(d.close, period=self.p.ema_filter_price_length)
        self.ema_exit = bt.ind.EMA(d.close, period=self.p.ema_exit_length)
        self.atr = bt.ind.ATR(d, period=self.p.atr_length)

        self.stop_order = None
        self.tp_order = None
        self.order_pending = False
        self.holding_bars = 0

        self.trades = 0
        self.wins = 0
        self.losses = 0
        self.gross_profit = 0.0
        self.gross_loss = 0.0
        self.exit_reason = None
        self._entry_price = None
        self._exit_price = None
        self._entry_size = 0
        self.current_stop_price = None
        self.initial_stop_price = None

    def next(self):
        # Manage open position (trailing / time / ema exits)
        if self.position:
            self.holding_bars += 1

            # Trailing stop adjustment (BODY FRACTION method)
            # new_stop = open + (close-open)*factor ensures it remains within the candle body for 0<factor<1
            if self.p.use_trailing_stop and self.stop_order and not self.order_pending:
                if self.data.close[0] > self.data.open[0]:  # only trail on green candle
                    factor = max(0.0, min(1.0, float(self.p.trailing_body_factor)))  # clamp
                    if factor <= 0.0:
                        # nothing to do (factor disabled)
                        pass
                    else:
                        body_price = self.data.open[0] + (self.data.close[0] - self.data.open[0]) * factor
                        # If factor == 1.0 body_price equals close; nudge below close to remain valid stop
                        if body_price >= self.data.close[0]:
                            # use a small epsilon based on pip_value (fallback to 1e-6)
                            eps = self.p.pip_value * 0.1 if self.p.pip_value else 1e-6
                            body_price = self.data.close[0] - eps
                        new_stop = body_price
                        # Conditions to accept new stop
                        cond1 = self.current_stop_price is not None
                        cond2 = new_stop > (self.current_stop_price if cond1 else -float('inf'))
                        cond3 = new_stop < self.data.close[0]  # must stay below current close
                        if cond1 and cond2 and cond3:
                            try:
                                self.cancel(self.stop_order)
                            except Exception:
                                pass
                            self.stop_order = self.sell(exectype=bt.Order.Stop,
                                                        price=new_stop,
                                                        size=self.position.size)
                            if self.p.print_signals:
                                dt = bt.num2date(self.data.datetime[0])
                                print(f"TRAIL {dt:%Y-%m-%d %H:%M} stop_raise {self.current_stop_price:.5f} -> {new_stop:.5f} (factor={factor:.2f})")
                            self.current_stop_price = new_stop
                        elif self.p.print_signals:
                            # Debug why trailing not applied
                            dt = bt.num2date(self.data.datetime[0])
                            reason_parts = []
                            if not cond1:
                                reason_parts.append('no_current_stop')
                            if cond1 and not cond2:
                                reason_parts.append('not_higher')
                            if not cond3:
                                reason_parts.append('>=close')
                            reasons = ','.join(reason_parts) if reason_parts else 'unknown'
                            print(f"TRAIL_SKIP {dt:%Y-%m-%d %H:%M} candidate={new_stop:.5f} curr_stop={self.current_stop_price} close={self.data.close[0]:.5f} factor={factor:.2f} reasons={reasons}")

            trigger = False
            reason = None
            if self.p.use_bar_count_exit and self.holding_bars >= self.p.bar_count_exit:
                trigger = True; reason = 'BAR_EXIT'
            if (not trigger and self.p.use_ema_crossover_exit and
                    self._cross_above(self.ema_exit, self.ema_confirm)):
                trigger = True; reason = 'EMA_EXIT'
            if trigger:
                for o in (self.stop_order, self.tp_order):
                    if o:
                        try:
                            self.cancel(o)
                        except Exception:
                            pass
                self.exit_reason = reason or 'UNKNOWN'
                self.close()
                return

        if self.order_pending or self.position:
            return

        # Entry filters
        try:
            prev_bull = self.data.close[-1] > self.data.open[-1]
        except IndexError:
            return
        cross_any = (self._cross_above(self.ema_confirm, self.ema_fast) or
                     self._cross_above(self.ema_confirm, self.ema_medium) or
                     self._cross_above(self.ema_confirm, self.ema_slow))
        if not (cross_any and prev_bull):
            return
        if self.p.use_ema_order_condition:
            if not (self.ema_confirm[0] > self.ema_fast[0] and
                    self.ema_confirm[0] > self.ema_medium[0] and
                    self.ema_confirm[0] > self.ema_slow[0]):
                return
        if self.p.use_price_filter_ema and not (self.data.close[0] > self.ema_filter_price[0]):
            return
        ang = self._angle()
        if self.p.use_angle_filter and not (ang > self.p.min_angle):
            return

        atr_now = float(self.atr[0])
        if atr_now <= 0 or math.isnan(atr_now):
            return
        entry = float(self.data.close[0])
        stop_price = entry - atr_now * self.p.atr_sl_multiplier
        take_price = entry + atr_now * self.p.atr_tp_multiplier

        # Position sizing
        if self.p.enable_risk_sizing:
            raw_risk = entry - stop_price
            if raw_risk <= 0:
                return
            equity = self.broker.get_value()
            risk_val = equity * self.p.risk_percent
            risk_per_contract = raw_risk * self.p.contract_size
            if risk_per_contract <= 0:
                return
            contracts = max(int(risk_val / risk_per_contract), 1)
        else:
            contracts = int(self.p.size)
        if contracts <= 0:
            return
        bt_size = contracts * self.p.contract_size

        if self.p.print_signals:
            rr = (take_price - entry) / (entry - stop_price) if (entry - stop_price) > 0 else float('nan')
            dt = bt.num2date(self.data.datetime[0])
            usd_risk = (entry - stop_price) * bt_size if (entry - stop_price) > 0 else float('nan')
            print(f"ENTRY {dt:%Y-%m-%d %H:%M} price={entry:.5f} contracts={contracts} bt_size={bt_size} SL={stop_price:.5f} TP={take_price:.5f} angle={ang:.1f} RR={rr:.2f} risk_usd={usd_risk:.2f}")

        parent, stop_o, limit_o = self.buy_bracket(size=bt_size, stopprice=stop_price, limitprice=take_price)
        self.stop_order, self.tp_order = stop_o, limit_o
        self.order_pending = True
        self.holding_bars = 0
        self.exit_reason = None
        self._entry_price = entry
        self._exit_price = None
        self._entry_size = bt_size
        self.current_stop_price = stop_price
        self.initial_stop_price = stop_price

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.order_pending = False
                self.holding_bars = 0
            elif order.issell():
                if order == self.stop_order and not self.exit_reason:
                    if (self.p.use_trailing_stop and self.initial_stop_price is not None and
                            self.current_stop_price is not None and
                            self.current_stop_price > self.initial_stop_price + 1e-10):
                        self.exit_reason = 'TRAIL_STOP'
                    else:
                        self.exit_reason = 'STOP'
                elif order == self.tp_order and not self.exit_reason:
                    self.exit_reason = 'TP'
                self._exit_price = order.executed.price
                self.current_stop_price = None
                self.initial_stop_price = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.order_pending = False

    def notify_trade(self, trade):
        if trade.isclosed:
            self.trades += 1
            pnl_usd = trade.pnlcomm
            if pnl_usd > 0:
                self.wins += 1; self.gross_profit += pnl_usd
            else:
                self.losses += 1; self.gross_loss += abs(pnl_usd)
            exit_price = self._exit_price if self._exit_price is not None else float(self.data.close[0])
            entry_price = self._entry_price if self._entry_price is not None else exit_price
            diff = exit_price - entry_price
            pips = diff / self.p.pip_value if self.p.pip_value > 0 else float('nan')
            if self.p.print_signals:
                dt = bt.num2date(self.data.datetime[0])
                print(f"EXIT  {dt:%Y-%m-%d %H:%M} pnl_usd={pnl_usd:.2f} ({pips:.1f} pips) reason={self.exit_reason or 'UNKNOWN'} hold_bars={self.holding_bars} entry={entry_price:.5f} exit={exit_price:.5f} diff_price={diff:.5f}")
            self.stop_order = None
            self.tp_order = None
            self.exit_reason = None
            self._entry_price = None
            self._exit_price = None
            self._entry_size = 0

    def stop(self):
        wr = (self.wins / self.trades * 100.0) if self.trades else 0.0
        pf = (self.gross_profit / self.gross_loss) if self.gross_loss > 0 else float('inf')
        print("=== SUNRISE SUMMARY ===")
        print(f"Trades: {self.trades} Wins: {self.wins} Losses: {self.losses} WinRate: {wr:.2f}% PF: {pf:.2f}")


if __name__ == '__main__':
    from pathlib import Path
    from datetime import datetime

    # ---------------- Configuration (edit here) -----------------
    from pathlib import Path as _Path
    _BASE_DIR = _Path(__file__).resolve().parent.parent.parent  # project root
    DATA_FILE = str((_BASE_DIR / 'data' / 'EURUSD_15m_2Mon.csv').resolve())  # absolute path
    FROMDATE = '2025-06-02'  # None
    TODATE = '2025-08-17'  # optional
    STARTING_CASH = 100000.0
    STRAT_KWARGS = dict(
        # Example overrides (uncomment/edit):
        # trailing_body_factor=0.9,
        # print_signals=False,
        # enable_risk_sizing=True,
        # risk_percent=0.01,
    )
    # -----------------------------------------------------------

    def parse_date(s):
        if not s:
            return None
        try:
            return datetime.strptime(s, '%Y-%m-%d')
        except Exception:
            return None

    path = Path(DATA_FILE)
    if not path.exists():
        print(f"Data file not found: {path}")
        raise SystemExit(1)
    feed_kwargs = dict(
        dataname=str(path), dtformat='%Y%m%d', tmformat='%H:%M:%S',
        datetime=0, time=1, open=2, high=3, low=4, close=5, volume=6,
        timeframe=bt.TimeFrame.Minutes, compression=5,
    )
    fd = parse_date(FROMDATE); td = parse_date(TODATE)
    if fd: feed_kwargs['fromdate'] = fd
    if td: feed_kwargs['todate'] = td
    data = bt.feeds.GenericCSVData(**feed_kwargs)
    cerebro = bt.Cerebro()
    cerebro.adddata(data)
    cerebro.broker.setcash(STARTING_CASH)
    cerebro.broker.setcommission(leverage=30.0)
    cerebro.addstrategy(Sunrise, **STRAT_KWARGS)
    print("=== RUNNING SUNRISE (config section) ===")
    cerebro.run()
    print(f"Final Value: {cerebro.broker.getvalue():,.2f}")
