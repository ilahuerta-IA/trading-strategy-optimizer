"""Análisis profundo de USDJPY para encontrar edge adicional"""
import re
import pandas as pd
import numpy as np

# Leer archivo de trades
with open('temp_reports/ERIS_USDJPY_20251208_172346.txt', 'r') as f:
    content = f.read()

# Extraer trades con todos los datos
pattern = r'ENTRY #(\d+)\nTime: (\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):\d{2}.*?Entry Price: ([\d.]+).*?ATR: ([\d.]+).*?Z-Score: ([-\d.]+).*?EMA\(70\): ([\d.]+).*?Distance to EMA: ([\d.]+).*?Distance to Lower: ([\d.]+).*?EXIT #\1.*?Exit Reason: (\w+).*?Result: (\w+).*?P&L: ([-\d.]+).*?Entry Candles in Oversold: (\d+)'

trades_raw = re.findall(pattern, content, re.DOTALL)
print(f'Total trades extraídos: {len(trades_raw)}')

trades = []
for t in trades_raw:
    trades.append({
        'trade_num': int(t[0]),
        'year': int(t[1]),
        'month': int(t[2]),
        'day': int(t[3]),
        'hour': int(t[4]),
        'minute': int(t[5]),
        'entry_price': float(t[6]),
        'atr': float(t[7]),
        'zscore': float(t[8]),
        'ema': float(t[9]),
        'dist_ema': float(t[10]),
        'dist_lower': float(t[11]),
        'exit_reason': t[12],
        'result': t[13],
        'pnl': float(t[14]),
        'candles_oversold': int(t[15])
    })

df = pd.DataFrame(trades)

def calc_stats(subset, label=""):
    if len(subset) == 0:
        return {'n': 0, 'wr': 0, 'pf': 0, 'net': 0}
    wins = (subset['result'] == 'WIN').sum()
    wr = wins / len(subset) * 100
    gp = subset[subset['pnl'] > 0]['pnl'].sum()
    gl = abs(subset[subset['pnl'] < 0]['pnl'].sum())
    pf = gp/gl if gl > 0 else 0
    net = subset['pnl'].sum()
    return {'n': len(subset), 'wr': wr, 'pf': pf, 'net': net}

print('='*80)
print('1. ANÁLISIS POR ATR (Volatilidad)')
print('='*80)

# Percentiles de ATR
atr_percentiles = df['atr'].quantile([0.1, 0.25, 0.5, 0.75, 0.9]).values
print(f"ATR Percentiles: 10%={atr_percentiles[0]:.4f}, 25%={atr_percentiles[1]:.4f}, 50%={atr_percentiles[2]:.4f}, 75%={atr_percentiles[3]:.4f}, 90%={atr_percentiles[4]:.4f}")
print()

atr_ranges = [
    ('ATR < 0.03 (muy bajo)', df['atr'] < 0.03),
    ('0.03 <= ATR < 0.05', (df['atr'] >= 0.03) & (df['atr'] < 0.05)),
    ('0.05 <= ATR < 0.07', (df['atr'] >= 0.05) & (df['atr'] < 0.07)),
    ('0.07 <= ATR < 0.10', (df['atr'] >= 0.07) & (df['atr'] < 0.10)),
    ('0.10 <= ATR < 0.15', (df['atr'] >= 0.10) & (df['atr'] < 0.15)),
    ('ATR >= 0.15 (alto)', df['atr'] >= 0.15),
]

print(f"{'Rango ATR':<25} {'Trades':>8} {'WR%':>8} {'PF':>8} {'Net':>12}")
print('-'*65)
for name, mask in atr_ranges:
    s = calc_stats(df[mask])
    marker = ' ***' if s['pf'] >= 1.15 else (' BAD' if s['pf'] < 0.95 else '')
    print(f"{name:<25} {s['n']:>8} {s['wr']:>7.1f}% {s['pf']:>8.2f} ${s['net']:>10,.0f}{marker}")

print()
print('='*80)
print('2. ANÁLISIS POR Z-SCORE (Rangos más finos)')
print('='*80)

zscore_ranges = [
    ('Z < -3', df['zscore'] < -3),
    ('-3 <= Z < -2.5', (df['zscore'] >= -3) & (df['zscore'] < -2.5)),
    ('-2.5 <= Z < -2', (df['zscore'] >= -2.5) & (df['zscore'] < -2)),
    ('-2 <= Z < -1.5', (df['zscore'] >= -2) & (df['zscore'] < -1.5)),
    ('-1.5 <= Z < -1', (df['zscore'] >= -1.5) & (df['zscore'] < -1)),
    ('-1 <= Z < -0.5', (df['zscore'] >= -1) & (df['zscore'] < -0.5)),
    ('-0.5 <= Z < 0', (df['zscore'] >= -0.5) & (df['zscore'] < 0)),
    ('0 <= Z < 0.5', (df['zscore'] >= 0) & (df['zscore'] < 0.5)),
    ('0.5 <= Z < 1', (df['zscore'] >= 0.5) & (df['zscore'] < 1)),
    ('1 <= Z < 1.5', (df['zscore'] >= 1) & (df['zscore'] < 1.5)),
    ('1.5 <= Z < 2', (df['zscore'] >= 1.5) & (df['zscore'] < 2)),
    ('2 <= Z < 3', (df['zscore'] >= 2) & (df['zscore'] < 3)),
    ('Z >= 3', df['zscore'] >= 3),
]

print(f"{'Rango Z-Score':<25} {'Trades':>8} {'WR%':>8} {'PF':>8} {'Net':>12}")
print('-'*65)
for name, mask in zscore_ranges:
    s = calc_stats(df[mask])
    marker = ' ***' if s['pf'] >= 1.15 else (' BAD' if s['pf'] < 0.95 else '')
    print(f"{name:<25} {s['n']:>8} {s['wr']:>7.1f}% {s['pf']:>8.2f} ${s['net']:>10,.0f}{marker}")

print()
print('='*80)
print('3. ANÁLISIS POR CANDLES EN OVERSOLD')
print('='*80)

for candles in range(0, 15):
    subset = df[df['candles_oversold'] == candles]
    if len(subset) > 50:
        s = calc_stats(subset)
        marker = ' ***' if s['pf'] >= 1.15 else (' BAD' if s['pf'] < 0.95 else '')
        print(f"Candles={candles:<3} {s['n']:>6} trades | WR: {s['wr']:.1f}% | PF: {s['pf']:.2f} | Net: ${s['net']:>10,.0f}{marker}")

# Rangos de candles
print()
print("Rangos de Candles Oversold:")
candle_ranges = [
    ('0 candles', df['candles_oversold'] == 0),
    ('1-3 candles', (df['candles_oversold'] >= 1) & (df['candles_oversold'] <= 3)),
    ('4-6 candles', (df['candles_oversold'] >= 4) & (df['candles_oversold'] <= 6)),
    ('7-10 candles', (df['candles_oversold'] >= 7) & (df['candles_oversold'] <= 10)),
    ('11+ candles', df['candles_oversold'] >= 11),
]

for name, mask in candle_ranges:
    s = calc_stats(df[mask])
    marker = ' ***' if s['pf'] >= 1.15 else (' BAD' if s['pf'] < 0.95 else '')
    print(f"  {name:<15} {s['n']:>6} trades | WR: {s['wr']:.1f}% | PF: {s['pf']:.2f} | Net: ${s['net']:>10,.0f}{marker}")

print()
print('='*80)
print('4. ANÁLISIS POR DISTANCIA A EMA')
print('='*80)

dist_percentiles = df['dist_ema'].quantile([0.1, 0.25, 0.5, 0.75, 0.9]).values
print(f"Dist EMA Percentiles: 10%={dist_percentiles[0]:.4f}, 25%={dist_percentiles[1]:.4f}, 50%={dist_percentiles[2]:.4f}, 75%={dist_percentiles[3]:.4f}, 90%={dist_percentiles[4]:.4f}")

dist_ranges = [
    ('Dist < 0.05', df['dist_ema'] < 0.05),
    ('0.05 <= Dist < 0.10', (df['dist_ema'] >= 0.05) & (df['dist_ema'] < 0.10)),
    ('0.10 <= Dist < 0.15', (df['dist_ema'] >= 0.10) & (df['dist_ema'] < 0.15)),
    ('0.15 <= Dist < 0.20', (df['dist_ema'] >= 0.15) & (df['dist_ema'] < 0.20)),
    ('0.20 <= Dist < 0.30', (df['dist_ema'] >= 0.20) & (df['dist_ema'] < 0.30)),
    ('Dist >= 0.30', df['dist_ema'] >= 0.30),
]

print(f"{'Distancia a EMA':<25} {'Trades':>8} {'WR%':>8} {'PF':>8} {'Net':>12}")
print('-'*65)
for name, mask in dist_ranges:
    s = calc_stats(df[mask])
    marker = ' ***' if s['pf'] >= 1.15 else (' BAD' if s['pf'] < 0.95 else '')
    print(f"{name:<25} {s['n']:>8} {s['wr']:>7.1f}% {s['pf']:>8.2f} ${s['net']:>10,.0f}{marker}")

print()
print('='*80)
print('5. COMBINACIONES DE FILTROS')
print('='*80)

# Combinación 1: ATR medio + Z-Score bajo
print("\n--- ATR 0.05-0.10 + Z-Score < 0 ---")
mask = (df['atr'] >= 0.05) & (df['atr'] < 0.10) & (df['zscore'] < 0)
s = calc_stats(df[mask])
print(f"Trades: {s['n']} | WR: {s['wr']:.1f}% | PF: {s['pf']:.2f} | Net: ${s['net']:,.0f}")

# Combinación 2: ATR medio + Z-Score < -1
print("\n--- ATR 0.05-0.10 + Z-Score < -1 ---")
mask = (df['atr'] >= 0.05) & (df['atr'] < 0.10) & (df['zscore'] < -1)
s = calc_stats(df[mask])
print(f"Trades: {s['n']} | WR: {s['wr']:.1f}% | PF: {s['pf']:.2f} | Net: ${s['net']:,.0f}")

# Combinación 3: Candles oversold >= 5
print("\n--- Candles Oversold >= 5 ---")
mask = df['candles_oversold'] >= 5
s = calc_stats(df[mask])
print(f"Trades: {s['n']} | WR: {s['wr']:.1f}% | PF: {s['pf']:.2f} | Net: ${s['net']:,.0f}")

# Combinación 4: Candles oversold >= 5 + Z-Score < -1
print("\n--- Candles Oversold >= 5 + Z-Score < -1 ---")
mask = (df['candles_oversold'] >= 5) & (df['zscore'] < -1)
s = calc_stats(df[mask])
print(f"Trades: {s['n']} | WR: {s['wr']:.1f}% | PF: {s['pf']:.2f} | Net: ${s['net']:,.0f}")

# Combinación 5: Distancia a EMA baja
print("\n--- Distancia EMA < 0.10 ---")
mask = df['dist_ema'] < 0.10
s = calc_stats(df[mask])
print(f"Trades: {s['n']} | WR: {s['wr']:.1f}% | PF: {s['pf']:.2f} | Net: ${s['net']:,.0f}")

# Combinación 6: Mejores horas + ATR medio
print("\n--- Mejores Horas [0,4,7,14,15,22] + ATR 0.05-0.12 ---")
best_hours = [0, 4, 7, 14, 15, 22]
mask = (df['hour'].isin(best_hours)) & (df['atr'] >= 0.05) & (df['atr'] < 0.12)
s = calc_stats(df[mask])
print(f"Trades: {s['n']} | WR: {s['wr']:.1f}% | PF: {s['pf']:.2f} | Net: ${s['net']:,.0f}")

# Combinación 7: Mejores horas + Z-Score < 0
print("\n--- Mejores Horas [0,4,7,14,15,22] + Z-Score < 0 ---")
mask = (df['hour'].isin(best_hours)) & (df['zscore'] < 0)
s = calc_stats(df[mask])
print(f"Trades: {s['n']} | WR: {s['wr']:.1f}% | PF: {s['pf']:.2f} | Net: ${s['net']:,.0f}")

print()
print('='*80)
print('6. ANÁLISIS POR DÍA DE LA SEMANA')
print('='*80)

# Crear columna de día de semana
df['date'] = pd.to_datetime(df[['year', 'month', 'day']])
df['weekday'] = df['date'].dt.dayofweek  # 0=Monday, 6=Sunday

weekday_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
for wd in range(7):
    subset = df[df['weekday'] == wd]
    if len(subset) > 0:
        s = calc_stats(subset)
        marker = ' ***' if s['pf'] >= 1.15 else (' BAD' if s['pf'] < 0.95 else '')
        print(f"{weekday_names[wd]:<12} {s['n']:>6} trades | WR: {s['wr']:.1f}% | PF: {s['pf']:.2f} | Net: ${s['net']:>10,.0f}{marker}")

print()
print('='*80)
print('7. ANÁLISIS POR MES')
print('='*80)

for month in range(1, 13):
    subset = df[df['month'] == month]
    if len(subset) > 0:
        s = calc_stats(subset)
        marker = ' ***' if s['pf'] >= 1.15 else (' BAD' if s['pf'] < 0.95 else '')
        print(f"Mes {month:>2} {s['n']:>6} trades | WR: {s['wr']:.1f}% | PF: {s['pf']:.2f} | Net: ${s['net']:>10,.0f}{marker}")

print()
print('='*80)
print('8. BÚSQUEDA EXHAUSTIVA DE MEJORES COMBINACIONES')
print('='*80)

best_combos = []

# Iterar sobre rangos de ATR
atr_thresholds = [(0.03, 0.05), (0.04, 0.07), (0.05, 0.08), (0.05, 0.10), (0.06, 0.10), (0.07, 0.12), (0.08, 0.15)]
zscore_thresholds = [(-3, -2), (-3, -1.5), (-3, -1), (-2.5, -1), (-2, -0.5), (-2, 0), (-1.5, 0), (-1, 0.5)]
candle_thresholds = [(0, 3), (3, 6), (5, 10), (6, 15), (8, 20)]

for atr_min, atr_max in atr_thresholds:
    mask = (df['atr'] >= atr_min) & (df['atr'] < atr_max)
    s = calc_stats(df[mask])
    if s['n'] >= 500 and s['pf'] >= 1.10:
        best_combos.append({
            'filter': f'ATR [{atr_min}-{atr_max}]',
            'n': s['n'], 'wr': s['wr'], 'pf': s['pf'], 'net': s['net']
        })

for z_min, z_max in zscore_thresholds:
    mask = (df['zscore'] >= z_min) & (df['zscore'] < z_max)
    s = calc_stats(df[mask])
    if s['n'] >= 500 and s['pf'] >= 1.10:
        best_combos.append({
            'filter': f'Z-Score [{z_min} to {z_max}]',
            'n': s['n'], 'wr': s['wr'], 'pf': s['pf'], 'net': s['net']
        })

for c_min, c_max in candle_thresholds:
    mask = (df['candles_oversold'] >= c_min) & (df['candles_oversold'] <= c_max)
    s = calc_stats(df[mask])
    if s['n'] >= 500 and s['pf'] >= 1.10:
        best_combos.append({
            'filter': f'Candles [{c_min}-{c_max}]',
            'n': s['n'], 'wr': s['wr'], 'pf': s['pf'], 'net': s['net']
        })

# Combinaciones dobles
for atr_min, atr_max in atr_thresholds:
    for z_min, z_max in zscore_thresholds:
        mask = (df['atr'] >= atr_min) & (df['atr'] < atr_max) & (df['zscore'] >= z_min) & (df['zscore'] < z_max)
        s = calc_stats(df[mask])
        if s['n'] >= 300 and s['pf'] >= 1.15:
            best_combos.append({
                'filter': f'ATR [{atr_min}-{atr_max}] + Z [{z_min} to {z_max}]',
                'n': s['n'], 'wr': s['wr'], 'pf': s['pf'], 'net': s['net']
            })

# Ordenar por PF
best_combos.sort(key=lambda x: -x['pf'])

print("\nMEJORES COMBINACIONES ENCONTRADAS (ordenadas por PF):")
print(f"{'Filtro':<50} {'N':>6} {'WR%':>7} {'PF':>6} {'Net':>12}")
print('-'*85)
for combo in best_combos[:20]:
    print(f"{combo['filter']:<50} {combo['n']:>6} {combo['wr']:>6.1f}% {combo['pf']:>6.2f} ${combo['net']:>10,.0f}")

print()
print('='*80)
print('9. ANÁLISIS POR PRECIO (Tendencia)')
print('='*80)

# Rangos de precio
price_ranges = [
    ('< 110', df['entry_price'] < 110),
    ('110-120', (df['entry_price'] >= 110) & (df['entry_price'] < 120)),
    ('120-130', (df['entry_price'] >= 120) & (df['entry_price'] < 130)),
    ('130-140', (df['entry_price'] >= 130) & (df['entry_price'] < 140)),
    ('140-150', (df['entry_price'] >= 140) & (df['entry_price'] < 150)),
    ('>= 150', df['entry_price'] >= 150),
]

print(f"{'Rango Precio':<20} {'Trades':>8} {'WR%':>8} {'PF':>8} {'Net':>12}")
print('-'*60)
for name, mask in price_ranges:
    s = calc_stats(df[mask])
    if s['n'] > 0:
        marker = ' ***' if s['pf'] >= 1.15 else (' BAD' if s['pf'] < 0.95 else '')
        print(f"{name:<20} {s['n']:>8} {s['wr']:>7.1f}% {s['pf']:>8.2f} ${s['net']:>10,.0f}{marker}")
