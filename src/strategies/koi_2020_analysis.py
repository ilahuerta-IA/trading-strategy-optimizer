"""Quick analysis of 2020 trades to find filter improvements."""
import re

# Read the trade log
with open('temp_reports/KOI_USDCHF_trades_20251214_212113.txt', 'r') as f:
    content = f.read()

# Parse trades
trades = []
pattern = r'ENTRY #(\d+)\nTime: ([\d-]+ [\d:]+).*?Entry Price: ([\d.]+).*?SL Pips: ([\d.]+).*?ATR: ([\d.]+).*?CCI: ([\d.]+).*?EXIT #\d+.*?Exit Reason: (\w+).*?P&L: \$([^\n]+)'
entries = re.findall(pattern, content, re.DOTALL)

for e in entries:
    year = int(e[1][:4])
    pnl_str = e[7].replace(',', '')
    pnl = float(pnl_str)
    trades.append({
        'num': int(e[0]),
        'year': year,
        'month': int(e[1][5:7]),
        'sl_pips': float(e[3]),
        'atr': float(e[4]),
        'cci': float(e[5]),
        'reason': e[6],
        'pnl': pnl,
        'win': pnl > 0
    })

print(f"Parsed {len(trades)} trades")

# === BUSQUEDA EXHAUSTIVA: PF>=1.5 + TODOS LOS AÑOS POSITIVOS ===
print("\n" + "="*70)
print("=== BUSQUEDA: PF>=1.5 + TODOS AÑOS POSITIVOS ===")
print("="*70)

results = []
for sl_min in [10, 10.5, 11, 11.5, 12, 12.5]:
    for sl_max in [13, 13.5, 14, 14.5, 15]:
        if sl_min >= sl_max:
            continue
        for cci_min in [100, 105, 110, 115, 120, 125, 130, 135, 140]:
            filtered = [t for t in trades if sl_min <= t['sl_pips'] <= sl_max and t['cci'] >= cci_min]
            if len(filtered) < 60:
                continue
            
            gross_profit = sum(t['pnl'] for t in filtered if t['pnl'] > 0)
            gross_loss = abs(sum(t['pnl'] for t in filtered if t['pnl'] < 0))
            pf = gross_profit / gross_loss if gross_loss > 0 else 0
            
            if pf < 1.5:
                continue
            
            # Check yearly
            yearly = {}
            for y in range(2020, 2026):
                yf = [t for t in filtered if t['year'] == y]
                yearly[y] = sum(t['pnl'] for t in yf) if yf else 0
            
            all_positive = all(yearly[y] >= 0 for y in yearly if yearly[y] != 0)
            
            w = sum(1 for t in filtered if t['win'])
            total_pnl = sum(t['pnl'] for t in filtered)
            
            results.append({
                'sl_min': sl_min, 'sl_max': sl_max, 'cci_min': cci_min,
                'trades': len(filtered), 'wr': w/len(filtered)*100, 'pf': pf,
                'total': total_pnl, 'yearly': yearly, 'all_pos': all_positive
            })

# Sort by all_positive then PF
results.sort(key=lambda x: (-x['all_pos'], -x['pf']))

print("\n--- Mejores con TODOS años positivos ---")
pos_results = [r for r in results if r['all_pos']]
if pos_results:
    for r in pos_results[:10]:
        print(f"SL {r['sl_min']:.1f}-{r['sl_max']:.1f} CCI>={r['cci_min']:3d}: {r['trades']:3d} tr | WR={r['wr']:.1f}% | PF={r['pf']:.2f} | Total=${r['total']:+,.0f}")
        print(f"   2020=${r['yearly'][2020]:+,.0f} | 2021=${r['yearly'][2021]:+,.0f} | 2022=${r['yearly'][2022]:+,.0f} | 2023=${r['yearly'][2023]:+,.0f} | 2024=${r['yearly'][2024]:+,.0f} | 2025=${r['yearly'][2025]:+,.0f}")
else:
    print("No hay combinación con todos los años positivos y PF>=1.5")
    print("\n--- Mejores con 2020 más cercano a 0 ---")
    results.sort(key=lambda x: (abs(x['yearly'][2020]), -x['pf']))
    for r in results[:10]:
        print(f"SL {r['sl_min']:.1f}-{r['sl_max']:.1f} CCI>={r['cci_min']:3d}: {r['trades']:3d} tr | WR={r['wr']:.1f}% | PF={r['pf']:.2f} | Total=${r['total']:+,.0f}")
        print(f"   2020=${r['yearly'][2020]:+,.0f} | 2021=${r['yearly'][2021]:+,.0f} | 2022=${r['yearly'][2022]:+,.0f} | 2023=${r['yearly'][2023]:+,.0f} | 2024=${r['yearly'][2024]:+,.0f} | 2025=${r['yearly'][2025]:+,.0f}")

# 2020 Analysis
print('\n=== 2020 TRADE ANALYSIS ===')
y2020 = [t for t in trades if t['year'] == 2020]
wins_2020 = [t for t in y2020 if t['win']]
losses_2020 = [t for t in y2020 if not t['win']]

print(f'Total: {len(y2020)} trades, {len(wins_2020)} wins, {len(losses_2020)} losses')
if y2020:
    print(f'WR: {len(wins_2020)/len(y2020)*100:.1f}%')
    print(f'Total PnL: ${sum(t["pnl"] for t in y2020):,.0f}')

    print('\n--- Wins 2020 ---')
    for t in wins_2020:
        print(f'  #{t["num"]:3d} M{t["month"]:02d} | SL={t["sl_pips"]:.1f} | CCI={t["cci"]:.0f} | PnL=${t["pnl"]:+,.0f}')

    print('\n--- Big Losses 2020 (> -$300) ---')
    big_losses = [t for t in losses_2020 if t['pnl'] < -300]
    for t in big_losses:
        print(f'  #{t["num"]:3d} M{t["month"]:02d} | SL={t["sl_pips"]:.1f} | CCI={t["cci"]:.0f} | PnL=${t["pnl"]:,.0f}')

print('\n=== FILTER ANALYSIS ===')

# CCI filter
print('\n--- CCI Minimum Threshold ---')
for cci_min in [110, 120, 130, 140, 150]:
    filtered = [t for t in trades if t['cci'] >= cci_min]
    if filtered:
        w = sum(1 for t in filtered if t['win'])
        total_pnl = sum(t['pnl'] for t in filtered)
        wr = w/len(filtered)*100
        y2020_f = [t for t in filtered if t['year'] == 2020]
        y2020_pnl = sum(t['pnl'] for t in y2020_f) if y2020_f else 0
        print(f'CCI >= {cci_min}: {len(filtered):3d} trades | WR={wr:.1f}% | Total=${total_pnl:+,.0f} | 2020=${y2020_pnl:+,.0f}')

# SL range filter
print('\n--- SL Range Filter ---')
for sl_min, sl_max in [(10, 14), (10.5, 14), (11, 14), (11, 13.5), (11, 13), (11.5, 14), (11.5, 13.5)]:
    filtered = [t for t in trades if sl_min <= t['sl_pips'] <= sl_max]
    if filtered:
        w = sum(1 for t in filtered if t['win'])
        total_pnl = sum(t['pnl'] for t in filtered)
        wr = w/len(filtered)*100
        y2020_f = [t for t in filtered if t['year'] == 2020]
        y2020_pnl = sum(t['pnl'] for t in y2020_f) if y2020_f else 0
        print(f'SL {sl_min:.1f}-{sl_max:.1f}: {len(filtered):3d} trades | WR={wr:.1f}% | Total=${total_pnl:+,.0f} | 2020=${y2020_pnl:+,.0f}')

# Month filter
print('\n--- 2020 by Month ---')
for m in range(1, 13):
    m_trades = [t for t in y2020 if t['month'] == m]
    if m_trades:
        w = sum(1 for t in m_trades if t['win'])
        pnl = sum(t['pnl'] for t in m_trades)
        print(f'M{m:02d}: {len(m_trades):2d} trades | W={w} L={len(m_trades)-w} | PnL=${pnl:+,.0f}')

# Combined filters
print('\n=== COMBINED FILTERS ===')
for cci_min in [120, 130, 140]:
    for sl_min, sl_max in [(10, 14), (11, 14), (11, 13)]:
        filtered = [t for t in trades if t['cci'] >= cci_min and sl_min <= t['sl_pips'] <= sl_max]
        if filtered:
            w = sum(1 for t in filtered if t['win'])
            total_pnl = sum(t['pnl'] for t in filtered)
            wr = w/len(filtered)*100
            y2020_f = [t for t in filtered if t['year'] == 2020]
            y2020_pnl = sum(t['pnl'] for t in y2020_f) if y2020_f else 0
            gross_profit = sum(t['pnl'] for t in filtered if t['pnl'] > 0)
            gross_loss = abs(sum(t['pnl'] for t in filtered if t['pnl'] < 0))
            pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            print(f'CCI>={cci_min} SL={sl_min}-{sl_max}: {len(filtered):3d} tr | WR={wr:.1f}% | PF={pf:.2f} | Total=${total_pnl:+,.0f} | 2020=${y2020_pnl:+,.0f}')
