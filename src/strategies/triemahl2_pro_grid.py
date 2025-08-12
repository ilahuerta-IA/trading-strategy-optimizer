import backtrader as bt
from pathlib import Path
import itertools
import csv
from statistics import mean
from datetime import datetime
import sys

# Ensure project src root on path when executing directly
CURRENT_FILE = Path(__file__).resolve()
SRC_ROOT = CURRENT_FILE.parent.parent  # /src
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from strategies.triemahl2_pro import Triemahl2ProStrategy, DATA_FILE, BROKER_CONFIG

"""Expanded grid executor for triemahl2_pro.
Focus: Increase entries + maintain/improve PF.
Outputs: Console top results + CSV file with all combos + aggregate stats per parameter value.

Runtime caution: 8 years * many combos is heavy. Use MAX_COMBOS or trim grids if needed.
"""

DATA_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / DATA_FILE
RESULTS_DIR = Path(__file__).resolve().parent / 'grid_results'
RESULTS_DIR.mkdir(exist_ok=True)

class ResultCollector(bt.Analyzer):
    def __init__(self):
        self.trades = 0
        self.win = 0
        self.loss = 0
        self.gross_profit = 0.0
        self.gross_loss = 0.0
    def notify_trade(self, trade):
        if trade.isclosed:
            self.trades += 1
            if trade.pnlcomm > 0:
                self.win += 1
                self.gross_profit += trade.pnlcomm
            else:
                self.loss += 1
                self.gross_loss += abs(trade.pnlcomm)

    def get_analysis(self):
        pf = (self.gross_profit / self.gross_loss) if self.gross_loss > 0 else 0
        win_rate = (self.win / self.trades * 100.0) if self.trades else 0
        return dict(trades=self.trades, wins=self.win, losses=self.loss, pf=pf, win_rate=win_rate)

# Parameter grids (expanded)
PARAM_GRID = {
    'min_angle_threshold': [48.0, 50.0, 52.0, 54.0],
    'stop_loss_pips': [10.0, 12.0, 14.0],
    'take_profit_pips': [24.0, 28.0, 30.0, 34.0],
    'angle_required_count': [1, 2],
    'use_fast_only_threshold': [False, True],
    'keep_percent': [55, 65, 75],
    'angle_trail_factor': [0.80, 0.85, 0.90],
}

MAX_COMBOS = 400  # safety cap

# Fixed baseline (could be added to grid if needed)
BASE_PARAMS = dict(
    enable_two_stage=True,
    enable_strict_order=True,
    enable_trend_filter=True,
    enable_angle_divergence_limits=True,
    cooldown_period=1,
    enable_delta_filter=True,
    enable_percentile_filter=True,
    min_trades_for_threshold=300,
    enable_angle_trailing=True,
    enable_max_hold=True,
    max_hold_bars=5,
    enforce_angle_same_sign=True,
)

def iter_param_sets(grid_dict):
    keys = list(grid_dict.keys())
    for values in itertools.product(*(grid_dict[k] for k in keys)):
        yield dict(zip(keys, values))


def run_combo(combo):
    cerebro = bt.Cerebro(runonce=False, optreturn=False)
    data = bt.feeds.GenericCSVData(
        dataname=str(DATA_PATH), dtformat=('%Y%m%d'), tmformat=('%H:%M:%S'),
        datetime=0, time=1, open=2, high=3, low=4, close=5, volume=6,
        timeframe=bt.TimeFrame.Minutes, compression=5)
    cerebro.adddata(data)
    cerebro.broker.setcash(BROKER_CONFIG['start_cash'])
    cerebro.broker.setcommission(leverage=BROKER_CONFIG['leverage'])

    strat_params = {**BASE_PARAMS, **combo}
    cerebro.addstrategy(Triemahl2ProStrategy, **strat_params, verbose=False)
    cerebro.addanalyzer(ResultCollector, _name='results')

    results = cerebro.run()
    strat = results[0]
    res = strat.analyzers.results.get_analysis()
    final_val = cerebro.broker.getvalue()
    res['final_value'] = final_val
    res['combo'] = combo
    return res


def score(res):
    # Weighted scoring prioritizing PF, ensuring trade count significance
    return (res['pf'], min(res['trades'], 1000), res['win_rate'])

def aggregate(results, key):
    buckets = {}
    for r in results:
        val = r['combo'][key]
        buckets.setdefault(val, []).append(r)
    summary = []
    for v, rows in buckets.items():
        summary.append(dict(param=key, value=v,
                            combos=len(rows),
                            avg_pf=mean(x['pf'] for x in rows if x['pf']>0) if rows else 0,
                            avg_trades=mean(x['trades'] for x in rows),
                            avg_win_rate=mean(x['win_rate'] for x in rows)))
    return sorted(summary, key=lambda x: (-x['avg_pf'], -x['avg_trades']))


def main():
    keys = list(PARAM_GRID.keys())
    total_combo = 1
    for k in keys:
        total_combo *= len(PARAM_GRID[k])
    print(f"Planned combinations: {total_combo}")
    limited = False
    combos_iter = list(iter_param_sets(PARAM_GRID))
    if len(combos_iter) > MAX_COMBOS:
        combos_iter = combos_iter[:MAX_COMBOS]
        limited = True
    print(f"Executing {len(combos_iter)} combos{' (LIMITED)' if limited else ''}...")

    best = None
    results = []
    for i, combo in enumerate(combos_iter, 1):
        res = run_combo(combo)
        results.append(res)
        s = score(res)
        if best is None or s > score(best):
            best = res
        if i % 10 == 0 or i == len(combos_iter):
            print(f"[{i}/{len(combos_iter)}] PF {res['pf']:.2f} Trades {res['trades']} Win {res['win_rate']:.1f}% combo {combo}")

    print("\n=== TOP RESULTS ===")
    for r in sorted(results, key=score, reverse=True)[:15]:
        c = r['combo']
        print(f"PF {r['pf']:.2f} Trades {r['trades']} Win {r['win_rate']:.1f}% SL {c['stop_loss_pips']} TP {c['take_profit_pips']} thr {c['min_angle_threshold']} angReq {c['angle_required_count']} fastOnly {c['use_fast_only_threshold']} keep {c['keep_percent']} trailF {c['angle_trail_factor']}")

    # Aggregations
    print("\n=== PARAMETER AGGREGATES ===")
    for k in keys:
        agg = aggregate(results, k)
        print(f"-- {k} --")
        for row in agg:
            print(f" {row['value']}: avgPF {row['avg_pf']:.2f} avgTrades {row['avg_trades']:.1f} avgWin {row['avg_win_rate']:.1f}% combos {row['combos']}")

    # Export CSV
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_file = RESULTS_DIR / f'pro_grid_results_{ts}.csv'
    fieldnames = ['pf','trades','wins','losses','win_rate','final_value'] + list(keys)
    with open(out_file, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(fieldnames)
        for r in results:
            row = [r['pf'], r['trades'], r['wins'], r['losses'], r['win_rate'], r['final_value']] + [r['combo'][k] for k in keys]
            w.writerow(row)
    print(f"\nCSV saved: {out_file}")
    if best:
        print("\nBEST COMBO:", best['combo'])
        print(f"PF {best['pf']:.2f} Trades {best['trades']} Win {best['win_rate']:.1f}% Final {best['final_value']:.2f}")

if __name__ == '__main__':
    main()
