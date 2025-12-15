"""Búsqueda balanceada de filtros - maximizar peor año manteniendo PF>=1.5"""
import re

with open('temp_reports/KOI_USDCHF_trades_20251214_212113.txt', 'r') as f:
    content = f.read()

trades = []
pattern = r'ENTRY #(\d+)\nTime: ([\d-]+ [\d:]+).*?Entry Price: ([\d.]+).*?SL Pips: ([\d.]+).*?ATR: ([\d.]+).*?CCI: ([\d.]+).*?EXIT #\d+.*?Exit Reason: (\w+).*?P&L: \$([^\n]+)'
entries = re.findall(pattern, content, re.DOTALL)

for e in entries:
    pnl = float(e[7].replace(',', ''))
    trades.append({
        'year': int(e[1][:4]), 
        'month': int(e[1][5:7]), 
        'sl_pips': float(e[3]), 
        'cci': float(e[5]), 
        'pnl': pnl, 
        'win': pnl > 0
    })

print(f"Parsed {len(trades)} trades")
print()
print("=" * 70)
print("=== BUSQUEDA BALANCEADA: PF>=1.5 + maximizar peor año ===")
print("=" * 70)

results = []
for sl_min in [10, 10.5, 11, 11.5]:
    for sl_max in [13.5, 14, 14.5, 15]:
        if sl_min >= sl_max:
            continue
        for cci_min in [100, 110, 120, 130]:
            filtered = [t for t in trades if sl_min <= t['sl_pips'] <= sl_max and t['cci'] >= cci_min]
            if len(filtered) < 100:
                continue
            
            gross_profit = sum(t['pnl'] for t in filtered if t['pnl'] > 0)
            gross_loss = abs(sum(t['pnl'] for t in filtered if t['pnl'] < 0))
            pf = gross_profit / gross_loss if gross_loss > 0 else 0
            if pf < 1.5:
                continue
            
            yearly = {y: sum(t['pnl'] for t in filtered if t['year'] == y) for y in range(2020, 2026)}
            min_year_pnl = min(yearly.values())
            w = sum(1 for t in filtered if t['win'])
            total_pnl = sum(t['pnl'] for t in filtered)
            
            results.append({
                'sl_min': sl_min, 'sl_max': sl_max, 'cci_min': cci_min,
                'trades': len(filtered), 'wr': w/len(filtered)*100, 'pf': pf,
                'total': total_pnl, 'yearly': yearly, 'min_year': min_year_pnl
            })

# Ordenar por mejor peor año y luego por PF
results.sort(key=lambda x: (-x['min_year'], -x['pf']))

print()
print("--- TOP 10: Mejor peor año + PF>=1.5 ---")
for i, r in enumerate(results[:10], 1):
    sl_min = r['sl_min']
    sl_max = r['sl_max']
    cci_min = r['cci_min']
    trades_n = r['trades']
    wr = r['wr']
    pf = r['pf']
    total = r['total']
    y = r['yearly']
    
    print(f"{i:2d}. SL {sl_min:.1f}-{sl_max:.1f} CCI>={cci_min:3d}: {trades_n:3d} tr | WR={wr:.1f}% | PF={pf:.2f} | Total=${total:+,.0f}")
    print(f"    2020=${y[2020]:+,.0f} | 2021=${y[2021]:+,.0f} | 2022=${y[2022]:+,.0f} | 2023=${y[2023]:+,.0f} | 2024=${y[2024]:+,.0f} | 2025=${y[2025]:+,.0f}")

# También mostrar actual (SL 10-15, CCI>=100) como referencia
print()
print("--- REFERENCIA: Config actual SL 10-15, CCI>=100 ---")
ref = [t for t in trades if 10 <= t['sl_pips'] <= 15 and t['cci'] >= 100]
ref_gp = sum(t['pnl'] for t in ref if t['pnl'] > 0)
ref_gl = abs(sum(t['pnl'] for t in ref if t['pnl'] < 0))
ref_pf = ref_gp / ref_gl if ref_gl > 0 else 0
ref_yearly = {y: sum(t['pnl'] for t in ref if t['year'] == y) for y in range(2020, 2026)}
ref_w = sum(1 for t in ref if t['win'])
ref_total = sum(t['pnl'] for t in ref)
print(f"    SL 10-15 CCI>=100: {len(ref):3d} tr | WR={ref_w/len(ref)*100:.1f}% | PF={ref_pf:.2f} | Total=${ref_total:+,.0f}")
print(f"    2020=${ref_yearly[2020]:+,.0f} | 2021=${ref_yearly[2021]:+,.0f} | 2022=${ref_yearly[2022]:+,.0f} | 2023=${ref_yearly[2023]:+,.0f} | 2024=${ref_yearly[2024]:+,.0f} | 2025=${ref_yearly[2025]:+,.0f}")
