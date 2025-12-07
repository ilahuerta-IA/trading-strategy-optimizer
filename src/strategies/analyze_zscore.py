"""Quick Z-Score range analysis for ERIS optimization."""
import re
from pathlib import Path

def parse_trades(filepath):
    trades = []
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    entries = re.split(r'ENTRY #(\d+)', content)
    for i in range(1, len(entries), 2):
        if i+1 >= len(entries):
            break
        block = entries[i+1]
        trade = {}
        zscore = re.search(r'Z-Score: ([-\d.]+)', block)
        if zscore:
            trade['zscore'] = float(zscore.group(1))
        candles = re.search(r'Candles in Oversold: (\d+)', block)
        if candles:
            trade['candles'] = int(candles.group(1))
        pnl = re.search(r'P&L: ([-\d.]+)', block)
        if pnl:
            trade['pnl'] = float(pnl.group(1))
        result = re.search(r'Result: (WIN|LOSS)', block)
        if result:
            trade['result'] = result.group(1)
        if 'zscore' in trade and 'result' in trade:
            trades.append(trade)
    return trades

def calc(trades):
    if not trades:
        return 0, 0, 0, 0
    wins = sum(1 for t in trades if t['result'] == 'WIN')
    gp = sum(t['pnl'] for t in trades if t['pnl'] > 0)
    gl = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
    pf = gp/gl if gl > 0 else 999
    pnl = sum(t['pnl'] for t in trades)
    return len(trades), wins/len(trades)*100 if trades else 0, pf, pnl

# Get latest report
report_dir = Path('temp_reports')
reports = list(report_dir.glob('ERIS_USDCHF_*.txt'))
latest = max(reports, key=lambda p: p.stat().st_mtime)
print(f'Analyzing: {latest.name}')

trades = parse_trades(latest)
print(f'Total trades with Z-Score: {len(trades)}')

# Filter by candles >= 6 (current filter)
trades_filtered = [t for t in trades if t.get('candles', 0) >= 6]
print(f'Trades with candles >= 6: {len(trades_filtered)}')

print()
print('='*70)
print('Z-SCORE RANGES (with candles >= 6 filter)')
print('='*70)

# Detailed Z-Score analysis
zscore_ranges = [
    (-3.0, -2.5),
    (-3.0, -2.0),
    (-3.0, -1.5),
    (-3.0, -1.0),
    (-2.5, -2.0),
    (-2.5, -1.5),
    (-2.5, -1.0),
    (-2.5, -0.5),
    (-2.0, -1.5),
    (-2.0, -1.0),
    (-2.0, -0.5),
    (-1.5, -1.0),
    (-1.5, -0.5),
]

header = f"{'Z-Score Range':<18} {'Trades':>7} {'WinRate':>8} {'PF':>8} {'Net PnL':>12}"
print(header)
print('-'*60)

results = []
for zmin, zmax in zscore_ranges:
    filtered = [t for t in trades_filtered if zmin <= t['zscore'] < zmax]
    n, wr, pf, pnl = calc(filtered)
    results.append((zmin, zmax, n, wr, pf, pnl))
    indicator = '***' if pf >= 1.5 else '**' if pf >= 1.3 else '*' if pf >= 1.0 else ''
    label = f'{zmin} to {zmax}'
    print(f'{label:<18} {n:>7} {wr:>7.1f}% {pf:>7.2f} {pnl:>11.2f} {indicator}')

# Find best balance
print()
print('='*70)
print('RECOMMENDATIONS (sorted by PF, min 100 trades)')
print('='*70)
good = [(z[0], z[1], z[2], z[3], z[4], z[5]) for z in results if z[2] >= 100]
good.sort(key=lambda x: x[4], reverse=True)
for zmin, zmax, n, wr, pf, pnl in good[:5]:
    print(f'  Z-Score [{zmin}, {zmax}): {n} trades, WR={wr:.1f}%, PF={pf:.2f}, PnL=${pnl:.0f}')

print()
print('='*70)
print('RECOMMENDATIONS (sorted by PF, min 50 trades)')
print('='*70)
good50 = [(z[0], z[1], z[2], z[3], z[4], z[5]) for z in results if z[2] >= 50]
good50.sort(key=lambda x: x[4], reverse=True)
for zmin, zmax, n, wr, pf, pnl in good50[:5]:
    print(f'  Z-Score [{zmin}, {zmax}): {n} trades, WR={wr:.1f}%, PF={pf:.2f}, PnL=${pnl:.0f}')
