"""Sunrise Strategy (clean version with USD PnL)

Implements:
 - Entry: EMA confirm crosses above any of trend EMAs (+ optional ordering)
 - Filters: previous bullish candle, price above filter EMA, angle threshold
 - Risk: ATR based SL/TP, optional percent equity risk sizing (contract notionals)
 - Exits: TP / SL via brackets, optional bar-count, optional EMA crossover exit
 - Logging: Entry risk in USD, Exit PnL in price, pips, USD
"""
# -----------------------------------------------------------------------------
# DISCLAIMER:
# This software is for educational and research purposes only.
# It is not intended for live trading or financial advice.
# Trading in financial markets involves substantial risk of loss.
# Use at your own risk. The author assumes no liability for any losses.
# -----------------------------------------------------------------------------

import math
import backtrader as bt


class Sunrise(bt.Strategy):
    params = dict(
        ema_fast_length=7, # fast EMA for trend 16
        ema_medium_length=9, # medium EMA for trend 18
        ema_slow_length=11, # slow EMA for trend 20
        ema_confirm_length=1,
        atr_length=20,
        atr_sl_multiplier=1.0,
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
        print_signals=True,
        size=1,
        pip_value=0.0001,
        contract_size=100000,  # notional units per contract
        enable_risk_sizing=False,
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

    def next(self):
        if self.position:
            self.holding_bars += 1
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

        if self.p.enable_risk_sizing:
            raw_price_risk = entry - stop_price
            if raw_price_risk <= 0:
                return
            equity = self.broker.get_value()
            risk_value = equity * self.p.risk_percent
            risk_per_contract_usd = raw_price_risk * self.p.contract_size
            if risk_per_contract_usd <= 0:
                return
            size = max(int(risk_value / risk_per_contract_usd), 1)
        else:
            size = int(self.p.size)
        if size <= 0:
            return

        # Convert logical contracts to actual backtrader size (notional units)
        bt_size = size * self.p.contract_size

        if self.p.print_signals:
            rr = (take_price - entry) / (entry - stop_price) if (entry - stop_price) > 0 else float('nan')
            dt = bt.num2date(self.data.datetime[0])
            usd_risk = (entry - stop_price) * bt_size if (entry - stop_price) > 0 else float('nan')
            print(f"ENTRY {dt:%Y-%m-%d %H:%M} price={entry:.5f} contracts={size} bt_size={bt_size} SL={stop_price:.5f} TP={take_price:.5f} angle={ang:.1f} RR={rr:.2f} risk_usd={usd_risk:.2f}")

        parent, stop_o, limit_o = self.buy_bracket(size=bt_size, stopprice=stop_price, limitprice=take_price)
        self.stop_order, self.tp_order = stop_o, limit_o
        self.order_pending = True
        self.holding_bars = 0
        self.exit_reason = None
        self._entry_price = entry
        self._exit_price = None
        self._entry_size = bt_size

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.order_pending = False
                self.holding_bars = 0
            elif order.issell():
                if order == self.stop_order and not self.exit_reason:
                    self.exit_reason = 'STOP'
                elif order == self.tp_order and not self.exit_reason:
                    self.exit_reason = 'TP'
                self._exit_price = order.executed.price
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.order_pending = False

    def notify_trade(self, trade):
        if trade.isclosed:
            self.trades += 1
            pnl_usd = trade.pnlcomm  # now in account currency (USD)
            if pnl_usd > 0:
                self.wins += 1; self.gross_profit += pnl_usd
            else:
                self.losses += 1; self.gross_loss += abs(pnl_usd)
            exit_price = self._exit_price if self._exit_price is not None else float(self.data.close[0])
            entry_price = self._entry_price if self._entry_price is not None else exit_price
            diff = exit_price - entry_price
            pips = diff / self.p.pip_value if self.p.pip_value > 0 else float('nan')
            pnl_price = diff  # raw price move
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
    import argparse
    from pathlib import Path
    from datetime import datetime

    def parse_date(s):
        if not s:
            return None
        try:
            return datetime.strptime(s, '%Y-%m-%d')
        except Exception:
            return None

    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default='data/EURUSD_5m_5Yea.csv')
    ap.add_argument('--fromdate', default=None)
    ap.add_argument('--todate', default=None)
    ap.add_argument('--no-price-filter', action='store_true')
    ap.add_argument('--use-ema-order', action='store_true')
    ap.add_argument('--use-angle-filter', action='store_true')
    ap.add_argument('--bar-exit-off', action='store_true')
    ap.add_argument('--use-ema-exit', action='store_true')
    ap.add_argument('--cash', type=float, default=100000)
    ap.add_argument('--size', type=int, default=1)
    ap.add_argument('--risk-sizing', action='store_true')
    ap.add_argument('--risk-percent', type=float, default=0.01)
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()

    path = Path(args.data)
    if not path.exists():
        print(f"Data file not found: {path}")
        raise SystemExit(1)
    feed_kwargs = dict(
        dataname=str(path), dtformat='%Y%m%d', tmformat='%H:%M:%S',
        datetime=0, time=1, open=2, high=3, low=4, close=5, volume=6,
        timeframe=bt.TimeFrame.Minutes, compression=5,
    )
    fd = parse_date(args.fromdate); td = parse_date(args.todate)
    if fd: feed_kwargs['fromdate'] = fd
    if td: feed_kwargs['todate'] = td
    data = bt.feeds.GenericCSVData(**feed_kwargs)
    cerebro = bt.Cerebro()
    cerebro.adddata(data)
    cerebro.broker.setcash(args.cash)
    cerebro.broker.setcommission(leverage=30.0)
    cerebro.addstrategy(
        Sunrise,
        use_price_filter_ema=not args.no_price_filter,
        use_ema_order_condition=args.use_ema_order,
        use_angle_filter=args.use_angle_filter,
        use_bar_count_exit=not args.bar_exit_off,
        use_ema_crossover_exit=args.use_ema_exit,
        size=args.size,
        enable_risk_sizing=args.risk_sizing,
        risk_percent=args.risk_percent,
        print_signals=not args.quiet,
    )
    print("=== RUNNING SUNRISE ===")
    cerebro.run()
    print(f"Final Value: {cerebro.broker.getvalue():,.2f}")
