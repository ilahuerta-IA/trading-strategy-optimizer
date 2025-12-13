"""ERIS Trade Pattern Analysis"""
import re

with open(r'C:\Iván\Yosoybuendesarrollador\Python\Portafolio\quant_bot_project\src\strategies\temp_reports\ERIS_USDCHF_20251213_193129.txt', 'r') as f:
    content = f.read()

trades = re.findall(r'ENTRY #(\d+)[\s\S]*?Time: (\d{4})-(\d{2})[\s\S]*?ATR: ([\d.]+)[\s\S]*?Z-Score: ([-\d.]+)[\s\S]*?Candles in Oversold: (\d+)[\s\S]*?EXIT #\1[\s\S]*?Result: (WIN|LOSS)[\s\S]*?P&L: ([-\d.]+)', content)

print('=== Combined Filter Analysis ===\n')

# Test different filter combinations
filters = [
    ('Current: ATR any, Candles>=6', lambda t: int(t[5]) >= 6),
    ('ATR < 0.0004, Candles>=6', lambda t: float(t[3]) < 0.0004 and int(t[5]) >= 6),
    ('ATR < 0.00035, Candles>=6', lambda t: float(t[3]) < 0.00035 and int(t[5]) >= 6),
    ('ATR < 0.0003, Candles>=6', lambda t: float(t[3]) < 0.0003 and int(t[5]) >= 6),
    ('ATR < 0.0004, Candles>=9', lambda t: float(t[3]) < 0.0004 and int(t[5]) >= 9),
    ('ATR < 0.0004, Candles>=10', lambda t: float(t[3]) < 0.0004 and int(t[5]) >= 10),
    ('ATR < 0.00035, Candles>=10', lambda t: float(t[3]) < 0.00035 and int(t[5]) >= 10),
    ('ATR < 0.0003, Candles>=10', lambda t: float(t[3]) < 0.0003 and int(t[5]) >= 10),
    ('ATR 0.00015-0.00035, Candles>=9', lambda t: 0.00015 <= float(t[3]) < 0.00035 and int(t[5]) >= 9),
    ('ATR 0.0002-0.0004, Candles>=10', lambda t: 0.0002 <= float(t[3]) < 0.0004 and int(t[5]) >= 10),
    ('ATR 0.00015-0.0003, Candles>=10', lambda t: 0.00015 <= float(t[3]) < 0.0003 and int(t[5]) >= 10),
    ('ATR 0.00015-0.00025, Candles>=9', lambda t: 0.00015 <= float(t[3]) < 0.00025 and int(t[5]) >= 9),
]

print(f"{'Filter':<40} {'Trades':>7} {'Wins':>6} {'WR%':>7} {'PnL':>12} {'PF':>6}")
print('-' * 80)

for name, filt in filters:
    filtered = [t for t in trades if filt(t)]
    wins = len([t for t in filtered if t[6] == 'WIN'])
    total = len(filtered)
    wr = wins/total*100 if total > 0 else 0
    pnl = sum([float(t[7]) for t in filtered])
    
    # Calculate approx PF
    win_pnl = sum([float(t[7]) for t in filtered if t[6] == 'WIN'])
    loss_pnl = abs(sum([float(t[7]) for t in filtered if t[6] == 'LOSS']))
    pf = win_pnl / loss_pnl if loss_pnl > 0 else 0
    
    print(f'{name:<40} {total:>7} {wins:>6} {wr:>6.1f}% ${pnl:>10,.0f}  {pf:.2f}')

# Year breakdown for promising filters
for filter_name, best_filter in [
    ('ATR < 0.0004, Candles>=10', lambda t: float(t[3]) < 0.0004 and int(t[5]) >= 10),
    ('ATR < 0.0003, Candles>=10', lambda t: float(t[3]) < 0.0003 and int(t[5]) >= 10),
]:
    print(f'\n=== Year breakdown: {filter_name} ===')
    filtered = [t for t in trades if best_filter(t)]
    years = {}
    for t in filtered:
        year = t[1]
        if year not in years:
            years[year] = {'wins': 0, 'losses': 0, 'pnl': 0}
        if t[6] == 'WIN':
            years[year]['wins'] += 1
        else:
            years[year]['losses'] += 1
        years[year]['pnl'] += float(t[7])

    for year in sorted(years.keys()):
        y = years[year]
        total = y['wins'] + y['losses']
        wr = y['wins']/total*100 if total > 0 else 0
        status = '✅' if y['pnl'] > 0 else '❌'
        print(f"  {year}: {total:>3} trades, WR={wr:>5.1f}%, PnL=${y['pnl']:>8,.0f} {status}")
