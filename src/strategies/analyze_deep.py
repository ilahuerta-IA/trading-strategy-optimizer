"""
Deep analysis of ERIS trade report.
Finds optimal parameter ranges for Z-Score, Candles in Oversold, ATR, and Hours.
"""
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

def parse_trade_report(filepath):
    trades = []
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    entries = re.split(r'ENTRY #(\d+)', content)
    
    for i in range(1, len(entries), 2):
        if i+1 >= len(entries):
            break
        trade_block = entries[i+1]
        trade = {'num': int(entries[i])}
        
        time_match = re.search(r'Time: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', trade_block)
        if time_match:
            trade['entry_time'] = datetime.strptime(time_match.group(1), '%Y-%m-%d %H:%M:%S')
            trade['hour'] = trade['entry_time'].hour
            trade['weekday'] = trade['entry_time'].weekday()
        
        atr_match = re.search(r'ATR: ([\d.]+)', trade_block)
        if atr_match:
            trade['atr'] = float(atr_match.group(1))
        
        zscore_match = re.search(r'Z-Score: ([-\d.]+)', trade_block)
        if zscore_match:
            trade['zscore'] = float(zscore_match.group(1))
        
        candles_match = re.search(r'Candles in Oversold: (\d+)', trade_block)
        if candles_match:
            trade['candles_oversold'] = int(candles_match.group(1))
        
        exit_reason_match = re.search(r'Exit Reason: (\w+)', trade_block)
        if exit_reason_match:
            trade['exit_reason'] = exit_reason_match.group(1)
            trade['result'] = 'WIN' if trade['exit_reason'] == 'TAKE_PROFIT' else 'LOSS'
        
        pnl_match = re.search(r'P&L: ([-\d.]+)', trade_block)
        if pnl_match:
            trade['pnl'] = float(pnl_match.group(1))
        
        if 'result' in trade:
            trades.append(trade)
    
    return trades


def calc_metrics(trades):
    """Calculate key metrics for a trade list."""
    if not trades:
        return {'trades': 0, 'wins': 0, 'wr': 0, 'pf': 0, 'pnl': 0}
    total = len(trades)
    wins = sum(1 for t in trades if t['result'] == 'WIN')
    gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
    gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else 999
    pnl = sum(t['pnl'] for t in trades)
    wr = wins / total * 100 if total > 0 else 0
    return {'trades': total, 'wins': wins, 'wr': wr, 'pf': pf, 'pnl': pnl}


def print_metrics_table(results, label_name="Range"):
    """Print a metrics table."""
    header = f"{label_name:<18} {'Trades':>7} {'Wins':>6} {'WinRate':>8} {'PF':>8} {'Total PnL':>12}"
    print(header)
    print("-" * len(header))
    for label, m in results:
        if m['trades'] > 0:
            indicator = '***' if m['pf'] >= 1.5 else '**' if m['pf'] >= 1.2 else '*' if m['pf'] >= 1.0 else ''
            print(f"{label:<18} {m['trades']:>7} {m['wins']:>6} {m['wr']:>7.1f}% {m['pf']:>7.2f} {m['pnl']:>11.2f} {indicator}")


def analyze_zscore(trades):
    """Analyze by Z-Score ranges."""
    print("\n" + "=" * 70)
    print("ANALYSIS BY Z-SCORE RANGE")
    print("=" * 70)
    
    ranges = [
        (-5.0, -3.0, '-5.0 to -3.0'),
        (-3.0, -2.5, '-3.0 to -2.5'),
        (-2.5, -2.0, '-2.5 to -2.0'),
        (-2.0, -1.5, '-2.0 to -1.5'),
        (-1.5, -1.0, '-1.5 to -1.0'),
        (-1.0, -0.5, '-1.0 to -0.5'),
        (-0.5, 0.0, '-0.5 to  0.0'),
        (0.0, 1.0, ' 0.0 to  1.0'),
    ]
    
    results = []
    for min_z, max_z, label in ranges:
        filtered = [t for t in trades if 'zscore' in t and min_z <= t['zscore'] < max_z]
        results.append((label, calc_metrics(filtered)))
    
    print_metrics_table(results, "Z-Score Range")
    
    # Find optimal range
    valid_results = [(l, m) for l, m in results if m['trades'] >= 20]
    if valid_results:
        best = max(valid_results, key=lambda x: x[1]['pf'])
        print(f"\n>>> BEST Z-Score range: {best[0]} (PF={best[1]['pf']:.2f}, {best[1]['trades']} trades)")


def analyze_candles_oversold(trades):
    """Analyze by Candles in Oversold."""
    print("\n" + "=" * 70)
    print("ANALYSIS BY CANDLES IN OVERSOLD")
    print("=" * 70)
    
    by_candles = defaultdict(list)
    for t in trades:
        if 'candles_oversold' in t:
            by_candles[t['candles_oversold']].append(t)
    
    results = []
    for candles in sorted(by_candles.keys()):
        results.append((str(candles), calc_metrics(by_candles[candles])))
    
    print_metrics_table(results, "Candles")
    
    # Grouped analysis
    print("\n--- GROUPED RANGES ---")
    ranges = [
        (1, 3, '1-3 candles'),
        (3, 6, '3-5 candles'),
        (6, 9, '6-8 candles'),
        (9, 12, '9-11 candles'),
        (12, 20, '12+ candles'),
    ]
    
    grouped = []
    for min_c, max_c, label in ranges:
        filtered = [t for t in trades if 'candles_oversold' in t and min_c <= t['candles_oversold'] < max_c]
        grouped.append((label, calc_metrics(filtered)))
    
    print_metrics_table(grouped, "Candle Range")


def analyze_atr(trades):
    """Analyze by ATR ranges."""
    print("\n" + "=" * 70)
    print("ANALYSIS BY ATR RANGE")
    print("=" * 70)
    
    ranges = [
        (0.0001, 0.0002, '0.0001-0.0002'),
        (0.0002, 0.00025, '0.0002-0.00025'),
        (0.00025, 0.0003, '0.00025-0.0003'),
        (0.0003, 0.00035, '0.0003-0.00035'),
        (0.00035, 0.0004, '0.00035-0.0004'),
        (0.0004, 0.00045, '0.0004-0.00045'),
        (0.00045, 0.0005, '0.00045-0.0005'),
        (0.0005, 0.0006, '0.0005-0.0006'),
        (0.0006, 0.001, '0.0006+'),
    ]
    
    results = []
    for min_a, max_a, label in ranges:
        filtered = [t for t in trades if 'atr' in t and min_a <= t['atr'] < max_a]
        results.append((label, calc_metrics(filtered)))
    
    print_metrics_table(results, "ATR Range")
    
    # Find optimal range
    valid_results = [(l, m) for l, m in results if m['trades'] >= 20]
    if valid_results:
        best = max(valid_results, key=lambda x: x[1]['pf'])
        print(f"\n>>> BEST ATR range: {best[0]} (PF={best[1]['pf']:.2f}, {best[1]['trades']} trades)")


def analyze_hours(trades):
    """Analyze by entry hour."""
    print("\n" + "=" * 70)
    print("ANALYSIS BY ENTRY HOUR")
    print("=" * 70)
    
    by_hour = defaultdict(list)
    for t in trades:
        if 'hour' in t:
            by_hour[t['hour']].append(t)
    
    results = []
    for hour in sorted(by_hour.keys()):
        results.append((f"Hour {hour:02d}:00", calc_metrics(by_hour[hour])))
    
    print_metrics_table(results, "Hour")
    
    # Find worst hours
    valid_results = [(l, m, h) for h, (l, m) in enumerate(results) if m['trades'] >= 10]
    if valid_results:
        worst = [x for x in valid_results if x[1]['pf'] < 1.0]
        if worst:
            print("\n>>> WORST hours to consider avoiding:")
            for label, m, _ in sorted(worst, key=lambda x: x[1]['pf']):
                print(f"    {label}: PF={m['pf']:.2f}, PnL={m['pnl']:.2f}")


def analyze_weekday(trades):
    """Analyze by weekday."""
    print("\n" + "=" * 70)
    print("ANALYSIS BY WEEKDAY")
    print("=" * 70)
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    by_day = defaultdict(list)
    for t in trades:
        if 'weekday' in t:
            by_day[t['weekday']].append(t)
    
    results = []
    for day_num in sorted(by_day.keys()):
        results.append((days[day_num], calc_metrics(by_day[day_num])))
    
    print_metrics_table(results, "Day")


def find_optimal_combination(trades):
    """Try different filter combinations to find optimal parameters."""
    print("\n" + "=" * 70)
    print("FILTER COMBINATION ANALYSIS")
    print("=" * 70)
    
    baseline = calc_metrics(trades)
    print(f"\nBASELINE: {baseline['trades']} trades, WR={baseline['wr']:.1f}%, PF={baseline['pf']:.2f}, PnL={baseline['pnl']:.2f}")
    
    # Test different Z-Score min/max combinations
    print("\n--- Z-SCORE FILTER OPTIONS ---")
    zscore_tests = [
        (-3.0, -1.0, 'Z: -3.0 to -1.0'),
        (-3.0, -0.5, 'Z: -3.0 to -0.5'),
        (-2.5, -1.0, 'Z: -2.5 to -1.0'),
        (-2.5, -0.5, 'Z: -2.5 to -0.5'),
        (-2.0, -0.5, 'Z: -2.0 to -0.5'),
        (-2.0, 0.0, 'Z: -2.0 to  0.0'),
        (-1.5, 0.0, 'Z: -1.5 to  0.0'),
        (None, None, 'NO FILTER'),
    ]
    
    results = []
    for min_z, max_z, label in zscore_tests:
        if min_z is None:
            filtered = trades
        else:
            filtered = [t for t in trades if 'zscore' in t and min_z <= t['zscore'] < max_z]
        results.append((label, calc_metrics(filtered)))
    
    print_metrics_table(results, "Z-Score Filter")
    
    # Test Candles in Oversold
    print("\n--- CANDLES OVERSOLD FILTER OPTIONS ---")
    candle_tests = [
        (3, 11, 'Candles: 3-11'),
        (3, 15, 'Candles: 3-15'),
        (2, 12, 'Candles: 2-12'),
        (4, 10, 'Candles: 4-10'),
        (1, 20, 'Candles: 1-20'),
        (None, None, 'NO FILTER'),
    ]
    
    results = []
    for min_c, max_c, label in candle_tests:
        if min_c is None:
            filtered = trades
        else:
            filtered = [t for t in trades if 'candles_oversold' in t and min_c <= t['candles_oversold'] <= max_c]
        results.append((label, calc_metrics(filtered)))
    
    print_metrics_table(results, "Candles Filter")
    
    # Test ATR ranges
    print("\n--- ATR FILTER OPTIONS ---")
    atr_tests = [
        (0.0002, 0.0004, 'ATR: 0.0002-0.0004'),
        (0.00025, 0.0004, 'ATR: 0.00025-0.0004'),
        (0.0002, 0.00045, 'ATR: 0.0002-0.00045'),
        (0.00025, 0.00045, 'ATR: 0.00025-0.00045'),
        (0.0002, 0.0005, 'ATR: 0.0002-0.0005'),
        (None, None, 'NO FILTER'),
    ]
    
    results = []
    for min_a, max_a, label in atr_tests:
        if min_a is None:
            filtered = trades
        else:
            filtered = [t for t in trades if 'atr' in t and min_a <= t['atr'] < max_a]
        results.append((label, calc_metrics(filtered)))
    
    print_metrics_table(results, "ATR Filter")


def find_minimal_filters(trades):
    """Find minimal effective filters for simplicity."""
    print("\n" + "=" * 70)
    print("MINIMAL FILTER COMBINATIONS (Balance: PF vs Trade Count)")
    print("=" * 70)
    
    baseline = calc_metrics(trades)
    
    # Combinations to test
    combinations = [
        # (z_min, z_max, c_min, c_max, atr_min, atr_max, label)
        (-3.0, 0.0, 1, 20, None, None, 'Z: -3 to 0 ONLY'),
        (-3.0, -0.5, 1, 20, None, None, 'Z: -3 to -0.5 ONLY'),
        (None, None, 3, 15, None, None, 'Candles: 3-15 ONLY'),
        (None, None, 2, 12, None, None, 'Candles: 2-12 ONLY'),
        (-3.0, 0.0, 3, 15, None, None, 'Z:-3/0 + C:3-15'),
        (-3.0, -0.5, 3, 15, None, None, 'Z:-3/-0.5 + C:3-15'),
        (-2.5, 0.0, 2, 15, None, None, 'Z:-2.5/0 + C:2-15'),
        (-3.0, 0.0, 3, 15, 0.0002, 0.0005, 'Z + C + ATR'),
        (None, None, None, None, None, None, 'NO FILTERS'),
    ]
    
    results = []
    for z_min, z_max, c_min, c_max, atr_min, atr_max, label in combinations:
        filtered = trades
        
        if z_min is not None:
            filtered = [t for t in filtered if 'zscore' in t and z_min <= t['zscore'] < z_max]
        if c_min is not None:
            filtered = [t for t in filtered if 'candles_oversold' in t and c_min <= t['candles_oversold'] <= c_max]
        if atr_min is not None:
            filtered = [t for t in filtered if 'atr' in t and atr_min <= t['atr'] < atr_max]
        
        m = calc_metrics(filtered)
        results.append((label, m))
    
    print_metrics_table(results, "Combination")
    
    # Rank by score: PF * sqrt(trades)  to balance quality and quantity
    print("\n--- RANKED BY SCORE (PF * sqrt(trades)) ---")
    import math
    ranked = []
    for label, m in results:
        if m['trades'] > 0:
            score = m['pf'] * math.sqrt(m['trades'])
            ranked.append((label, m, score))
    
    ranked.sort(key=lambda x: x[2], reverse=True)
    print(f"{'Rank':<6} {'Combination':<25} {'Trades':>7} {'PF':>6} {'Score':>8}")
    print("-" * 60)
    for i, (label, m, score) in enumerate(ranked[:10], 1):
        print(f"{i:<6} {label:<25} {m['trades']:>7} {m['pf']:>5.2f} {score:>8.1f}")


if __name__ == '__main__':
    import sys
    
    # Find most recent report
    report_dir = Path(__file__).parent / "temp_reports"
    reports = list(report_dir.glob("ERIS_USDCHF_*.txt"))
    
    if not reports:
        print("No report files found")
        sys.exit(1)
    
    latest_report = max(reports, key=lambda p: p.stat().st_mtime)
    print(f"Analyzing: {latest_report.name}")
    
    trades = parse_trade_report(latest_report)
    print(f"Parsed {len(trades)} trades")
    
    baseline = calc_metrics(trades)
    print(f"\nBASELINE: {baseline['trades']} trades, WR={baseline['wr']:.1f}%, PF={baseline['pf']:.2f}, PnL=${baseline['pnl']:.2f}")
    
    analyze_zscore(trades)
    analyze_candles_oversold(trades)
    analyze_atr(trades)
    analyze_hours(trades)
    analyze_weekday(trades)
    find_optimal_combination(trades)
    find_minimal_filters(trades)
