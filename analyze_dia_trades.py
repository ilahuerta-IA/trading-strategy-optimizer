"""Analisis de trades DIA para encontrar filtros optimos."""
import re

with open('temp_reports/KOI_USDCHF_trades_20260111_154101.txt', 'r') as f:
    content = f.read()

# Parse entries
entry_pattern = r'ENTRY #(\d+)\nTime: (\d{4}-\d{2}-\d{2}) (\d{2}):\d{2}:\d{2}\nEntry Price: [\d.]+\nStop Loss: [\d.]+\nTake Profit: [\d.]+\nSL Pips: ([\d.]+)\nATR: ([\d.]+)\nCCI: ([\d.]+)'
entries = {}
for m in re.finditer(entry_pattern, content):
    entries[m.group(1)] = {
        'hr': int(m.group(3)),
        'sl': float(m.group(4)),
        'atr': float(m.group(5)),
        'cci': float(m.group(6))
    }

# Parse exits  
exit_pattern = r'EXIT #(\d+)\nTime: [^\n]+\nExit Reason: (\w+)\nP&L: \$([-\d,.]+)'
exits = {}
for m in re.finditer(exit_pattern, content):
    pnl_str = m.group(3).replace(',', '')
    exits[m.group(1)] = float(pnl_str)

# Merge
trades = []
for tid, entry in entries.items():
    if tid in exits:
        entry['pnl'] = exits[tid]
        trades.append(entry)

print(f'Total trades con exit: {len(trades)}')
wins = sum(1 for t in trades if t['pnl'] > 0)
losses = len(trades) - wins
gross_p = sum(t['pnl'] for t in trades if t['pnl'] > 0)
gross_l = abs(sum(t['pnl'] for t in trades if t['pnl'] <= 0))
pf_total = gross_p / gross_l if gross_l > 0 else 0
print(f'Wins: {wins}, Losses: {losses}, WR: {wins/len(trades)*100:.1f}%')
print(f'PF Total: {pf_total:.2f}')
print(f'Net PnL: ${sum(t["pnl"] for t in trades):,.0f}')

def analyze_range(trades, key, ranges, label):
    print(f'\n=== POR RANGO {label} ===')
    for low, high in ranges:
        subset = [t for t in trades if low <= t[key] < high]
        if subset:
            w = sum(1 for t in subset if t['pnl'] > 0)
            gp = sum(t['pnl'] for t in subset if t['pnl'] > 0)
            gl = abs(sum(t['pnl'] for t in subset if t['pnl'] <= 0))
            pf = gp / gl if gl > 0 else float('inf')
            net = sum(t['pnl'] for t in subset)
            print(f'{label} {low:>6}-{high:<6}: {len(subset):3d} trades, WR={w/len(subset)*100:5.1f}%, PF={pf:5.2f}, Net=${net:>9,.0f}')

# Analyze by SL
sl_ranges = [(0, 40), (40, 60), (60, 100), (100, 150), (150, 250), (250, 500)]
analyze_range(trades, 'sl', sl_ranges, 'SL')

# Analyze by ATR
atr_ranges = [(0, 0.2), (0.2, 0.35), (0.35, 0.5), (0.5, 0.8), (0.8, 5)]
analyze_range(trades, 'atr', atr_ranges, 'ATR')

# Analyze by CCI
cci_ranges = [(100, 120), (120, 150), (150, 200), (200, 300), (300, 600)]
analyze_range(trades, 'cci', cci_ranges, 'CCI')

# Best combinations
print('\n=== COMBINACIONES PROMETEDORAS ===')
# SL 40-100 + ATR 0.2-0.5
subset = [t for t in trades if 40 <= t['sl'] < 100 and 0.2 <= t['atr'] < 0.5]
if subset:
    w = sum(1 for t in subset if t['pnl'] > 0)
    gp = sum(t['pnl'] for t in subset if t['pnl'] > 0)
    gl = abs(sum(t['pnl'] for t in subset if t['pnl'] <= 0))
    pf = gp / gl if gl > 0 else 0
    print(f'SL 40-100 + ATR 0.2-0.5: {len(subset)} trades, WR={w/len(subset)*100:.1f}%, PF={pf:.2f}')

# SL 40-80 + CCI 120-200
subset = [t for t in trades if 40 <= t['sl'] < 80 and 120 <= t['cci'] < 200]
if subset:
    w = sum(1 for t in subset if t['pnl'] > 0)
    gp = sum(t['pnl'] for t in subset if t['pnl'] > 0)
    gl = abs(sum(t['pnl'] for t in subset if t['pnl'] <= 0))
    pf = gp / gl if gl > 0 else 0
    print(f'SL 40-80 + CCI 120-200: {len(subset)} trades, WR={w/len(subset)*100:.1f}%, PF={pf:.2f}')

# ATR 0.2-0.4 only
subset = [t for t in trades if 0.2 <= t['atr'] < 0.4]
if subset:
    w = sum(1 for t in subset if t['pnl'] > 0)
    gp = sum(t['pnl'] for t in subset if t['pnl'] > 0)
    gl = abs(sum(t['pnl'] for t in subset if t['pnl'] <= 0))
    pf = gp / gl if gl > 0 else 0
    print(f'ATR 0.2-0.4: {len(subset)} trades, WR={w/len(subset)*100:.1f}%, PF={pf:.2f}')

# CCI 120-180
subset = [t for t in trades if 120 <= t['cci'] < 180]
if subset:
    w = sum(1 for t in subset if t['pnl'] > 0)
    gp = sum(t['pnl'] for t in subset if t['pnl'] > 0)
    gl = abs(sum(t['pnl'] for t in subset if t['pnl'] <= 0))
    pf = gp / gl if gl > 0 else 0
    print(f'CCI 120-180: {len(subset)} trades, WR={w/len(subset)*100:.1f}%, PF={pf:.2f}')
