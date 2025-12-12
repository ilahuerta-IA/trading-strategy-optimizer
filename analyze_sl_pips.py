"""Análisis de SL en pips para filtrar trades óptimos."""
import re
from collections import defaultdict

# Leer el reporte
with open('src/strategies/temp_reports/ERIS_USDCHF_20251212_160653.txt', 'r') as f:
    content = f.read()

# Extraer trades con regex
pattern = r'ENTRY #(\d+).*?Entry Price: ([\d.]+).*?Stop Loss: ([\d.]+).*?ATR: ([\d.]+).*?EXIT #\d+.*?Result: (\w+).*?P&L: ([-\d.]+).*?Pips: ([-\d.]+)'
matches = re.findall(pattern, content, re.DOTALL)

print(f'Total trades encontrados: {len(matches)}')
print()

# Calcular SL en pips para cada trade
trades = []
for m in matches:
    trade_num, entry, sl, atr, result, pnl, exit_pips = m
    entry_price = float(entry)
    sl_price = float(sl)
    sl_pips = abs(entry_price - sl_price) / 0.0001  # USDCHF pip = 0.0001
    trades.append({
        'sl_pips': sl_pips,
        'result': result,
        'pnl': float(pnl),
        'atr': float(atr)
    })

# Análisis por rangos de SL
ranges = [
    (0, 2),
    (2, 3),
    (3, 4),
    (4, 5),
    (5, 7),
    (7, 10),
    (10, 15),
    (15, 20),
    (20, 50)
]

print('=' * 85)
print('ANÁLISIS POR RANGO DE SL (pips)')
print('=' * 85)
header = f"{'Rango':<12} {'Trades':>8} {'Wins':>6} {'WR%':>8} {'Profit':>12} {'Loss':>12} {'Net':>12} {'PF':>8}"
print(header)
print('-' * 85)

for r_min, r_max in ranges:
    subset = [t for t in trades if r_min <= t['sl_pips'] < r_max]
    if not subset:
        continue
    
    wins = sum(1 for t in subset if t['result'] == 'WIN')
    losses = len(subset) - wins
    wr = wins / len(subset) * 100 if subset else 0
    
    profit = sum(t['pnl'] for t in subset if t['pnl'] > 0)
    loss = abs(sum(t['pnl'] for t in subset if t['pnl'] < 0))
    net = profit - loss
    pf = profit / loss if loss > 0 else float('inf')
    
    print(f'{r_min}-{r_max} pips   {len(subset):>8} {wins:>6} {wr:>7.1f}% {profit:>11,.0f} {loss:>11,.0f} {net:>+11,.0f} {pf:>7.2f}')

print('=' * 85)

# Análisis de filtros acumulativos (mínimo SL)
print()
print('=' * 85)
print('EFECTO DE FILTRO MÍNIMO SL (excluir trades con SL < X pips)')
print('=' * 85)
print(f"{'Min SL':>8} {'Trades':>8} {'Wins':>6} {'WR%':>8} {'Net PnL':>14} {'PF':>8} {'Excluidos':>10}")
print('-' * 85)

for min_sl in [0, 1, 2, 3, 4, 5, 6, 7, 8, 10]:
    subset = [t for t in trades if t['sl_pips'] >= min_sl]
    if not subset:
        continue
    
    wins = sum(1 for t in subset if t['result'] == 'WIN')
    wr = wins / len(subset) * 100
    
    profit = sum(t['pnl'] for t in subset if t['pnl'] > 0)
    loss = abs(sum(t['pnl'] for t in subset if t['pnl'] < 0))
    net = profit - loss
    pf = profit / loss if loss > 0 else float('inf')
    excluded = len(trades) - len(subset)
    
    print(f'{min_sl:>7} {len(subset):>8} {wins:>6} {wr:>7.1f}% {net:>+13,.0f} {pf:>7.2f} {excluded:>10}')

print('=' * 85)

# Análisis de filtros de rango (mínimo Y máximo SL)
print()
print('=' * 85)
print('MEJORES COMBINACIONES DE RANGO SL')
print('=' * 85)
print(f"{'Rango':>12} {'Trades':>8} {'WR%':>8} {'Net PnL':>14} {'PF':>8}")
print('-' * 85)

best_combos = []
for min_sl in range(0, 10):
    for max_sl in range(min_sl + 2, 25):
        subset = [t for t in trades if min_sl <= t['sl_pips'] <= max_sl]
        if len(subset) < 50:  # Mínimo 50 trades para significancia
            continue
        
        wins = sum(1 for t in subset if t['result'] == 'WIN')
        wr = wins / len(subset) * 100
        
        profit = sum(t['pnl'] for t in subset if t['pnl'] > 0)
        loss = abs(sum(t['pnl'] for t in subset if t['pnl'] < 0))
        net = profit - loss
        pf = profit / loss if loss > 0 else float('inf')
        
        best_combos.append((min_sl, max_sl, len(subset), wr, net, pf))

# Ordenar por PF
best_combos.sort(key=lambda x: x[5], reverse=True)

for combo in best_combos[:15]:
    min_sl, max_sl, n, wr, net, pf = combo
    print(f'{min_sl}-{max_sl} pips  {n:>8} {wr:>7.1f}% {net:>+13,.0f} {pf:>7.2f}')

print('=' * 85)
