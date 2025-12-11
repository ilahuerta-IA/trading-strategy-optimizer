"""Análisis de Mean Reversion para USDJPY"""
import re
import pandas as pd

with open('temp_reports/ERIS_USDJPY_20251208_164548.txt', 'r') as f:
    content = f.read()

trades_raw = re.findall(r'ENTRY #(\d+)\nTime: (\d{4}-\d{2}-\d{2} (\d{2}):\d{2}:\d{2}).*?Z-Score: ([-\d.]+).*?EXIT #\1.*?Result: (\w+).*?P&L: ([-\d.]+)', content, re.DOTALL)

trades = []
for t in trades_raw:
    trades.append({
        'hour': int(t[2]),
        'zscore': float(t[3]),
        'result': t[4],
        'pnl': float(t[5])
    })

df = pd.DataFrame(trades)

print('='*70)
print('ANALISIS POR HORA - USDJPY')
print('='*70)

def calc_stats(subset):
    if len(subset) == 0:
        return 0, 0, 0, 0
    wins = (subset['result'] == 'WIN').sum()
    wr = wins / len(subset) * 100
    gp = subset[subset['pnl'] > 0]['pnl'].sum()
    gl = abs(subset[subset['pnl'] < 0]['pnl'].sum())
    pf = gp/gl if gl > 0 else 0
    net = subset['pnl'].sum()
    return len(subset), wr, pf, net

print('Hora   Trades      WR%       PF      Net PnL')
print('-'*50)

hour_stats = []
for h in range(24):
    subset = df[df['hour'] == h]
    trades_n, wr, pf, net = calc_stats(subset)
    hour_stats.append({'hour': h, 'trades': trades_n, 'wr': wr, 'pf': pf, 'net': net})
    marker = ' OK' if pf >= 1.15 else (' BAD' if pf < 0.95 else '')
    print(f'{h:>4} {trades_n:>8} {wr:>7.1f}% {pf:>8.2f} {net:>10,.0f}{marker}')

print()
print('='*70)
print('MEJORES HORAS (PF >= 1.10)')
print('='*70)
best = [h for h in hour_stats if h['pf'] >= 1.10]
best.sort(key=lambda x: -x['pf'])
for h in best:
    print(f"H{h['hour']:02d}: PF={h['pf']:.2f} WR={h['wr']:.1f}% N={h['trades']} Net=${h['net']:,.0f}")

print()
print('='*70)
print('PEORES HORAS (PF < 0.95)')
print('='*70)
worst = [h for h in hour_stats if h['pf'] < 0.95]
worst.sort(key=lambda x: x['pf'])
for h in worst:
    print(f"H{h['hour']:02d}: PF={h['pf']:.2f} WR={h['wr']:.1f}% N={h['trades']} Net=${h['net']:,.0f}")

bad_hours = [h['hour'] for h in hour_stats if h['pf'] < 0.95]

print()
print('='*70)
print('SIMULACION: EVITAR PEORES HORAS')
print('='*70)
filtered = df[~df['hour'].isin(bad_hours)]
_, wr, pf, net = calc_stats(filtered)
print(f'Horas a evitar: {bad_hours}')
print(f'Trades: {len(filtered):,} de {len(df):,}')
print(f'WR: {wr:.1f}% PF: {pf:.2f} Net: ${net:,.0f}')

print()
print('='*70)
print('SIMULACION: SOLO MEJORES HORAS (PF >= 1.10)')
print('='*70)
good_hours = [h['hour'] for h in hour_stats if h['pf'] >= 1.10]
filtered2 = df[df['hour'].isin(good_hours)]
_, wr2, pf2, net2 = calc_stats(filtered2)
print(f'Solo horas: {good_hours}')
print(f'Trades: {len(filtered2):,} de {len(df):,}')
print(f'WR: {wr2:.1f}% PF: {pf2:.2f} Net: ${net2:,.0f}')

# Análisis por sesión de trading
print()
print('='*70)
print('ANALISIS POR SESION DE TRADING')
print('='*70)

sessions = {
    'Asia (0-8)': list(range(0, 8)),
    'London (8-14)': list(range(8, 14)),
    'NY (14-20)': list(range(14, 20)),
    'Overnight (20-24)': list(range(20, 24)),
}

for name, hours in sessions.items():
    subset = df[df['hour'].isin(hours)]
    n, wr, pf, net = calc_stats(subset)
    print(f'{name:<20}: {n:>5} trades | WR: {wr:.1f}% | PF: {pf:.2f} | Net: ${net:,.0f}')
