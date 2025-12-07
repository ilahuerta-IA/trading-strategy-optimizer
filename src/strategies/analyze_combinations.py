"""
Análisis de combinaciones para llegar a PF >= 1.5
Probamos combinaciones de:
- Rango de horas (usar TIME_RANGE vs HOURS_TO_AVOID)
- Candles in oversold (mínimo 9, 10, o exactamente 11)
"""
import re
from collections import defaultdict

FILE_PATH = r"temp_reports\ERIS_USDCHF_20251207_162400.txt"

def parse_trades(filepath):
    trades = []
    with open(filepath, 'r') as f:
        content = f.read()
    
    entry_pattern = r"ENTRY #(\d+)\nTime: ([^\n]+)\nDirection: ([^\n]+)\nEntry Price: ([^\n]+)\nStop Loss: ([^\n]+)\nTake Profit: ([^\n]+)\nATR: ([^\n]+)\nZ-Score: ([^\n]+)\nCandles in Oversold: ([^\n]+)\nEMA\(70\): ([^\n]+)\nUpper Band: ([^\n]+)\nLower Band: ([^\n]+)\nDistance to EMA: ([^\n]+)\nDistance to Lower: ([^\n]+)"
    exit_pattern = r"EXIT #(\d+)\nTime: ([^\n]+)\nExit Price: ([^\n]+)\nExit Reason: ([^\n]+)\nResult: ([^\n]+)\nP&L: ([^\n]+)"
    
    entries = re.findall(entry_pattern, content)
    exits = re.findall(exit_pattern, content)
    
    for entry, exit_data in zip(entries, exits):
        trade = {
            'id': int(entry[0]),
            'entry_time': entry[1],
            'atr': float(entry[6]),
            'zscore': float(entry[7]),
            'candles_oversold': int(entry[8]),
            'result': exit_data[4],
            'pnl': float(exit_data[5])
        }
        trade['hour'] = int(trade['entry_time'].split(' ')[1].split(':')[0])
        trades.append(trade)
    
    return trades


def calc_stats(filtered):
    if len(filtered) < 20:
        return None
    wins = sum(1 for t in filtered if t['result'] == 'WIN')
    gp = sum(t['pnl'] for t in filtered if t['result'] == 'WIN')
    gl = sum(abs(t['pnl']) for t in filtered if t['result'] == 'LOSS')
    pf = gp/gl if gl > 0 else 999
    wr = wins/len(filtered)*100
    net = gp - gl
    return {'trades': len(filtered), 'wr': wr, 'pf': pf, 'net': net}


def main():
    trades = parse_trades(FILE_PATH)
    print(f"Total trades: {len(trades)}")
    
    baseline = calc_stats(trades)
    print(f"\nBaseline: {baseline['trades']} trades, WR {baseline['wr']:.1f}%, PF {baseline['pf']:.2f}, Net ${baseline['net']:,.0f}")
    
    print("\n" + "="*80)
    print(" OPCIÓN 1: RANGO DE HORAS (USE_TIME_RANGE_FILTER)")
    print("="*80)
    
    # Probar diferentes rangos de horas
    hour_ranges = [
        (8, 20),   # Horario normal de trading
        (8, 22),   # Extendido tarde
        (9, 21),   # Más conservador
        (12, 22),  # Solo tarde/noche
        (14, 22),  # Solo tarde/noche más restringido
        (15, 24),  # Tarde/noche extendido
        (16, 24),  # Solo sesión americana tarde + asiática temprana
        (16, 22),  # Solo tardes
    ]
    
    for start, end in hour_ranges:
        if end <= 24:
            filtered = [t for t in trades if start <= t['hour'] < end]
        else:
            # Wrap around midnight
            filtered = [t for t in trades if t['hour'] >= start or t['hour'] < (end - 24)]
        stats = calc_stats(filtered)
        if stats:
            print(f"  Horas [{start:02d}:00 - {end:02d}:00): {stats['trades']:>4} trades, WR {stats['wr']:>5.1f}%, PF {stats['pf']:.2f}, Net ${stats['net']:>8,.0f}")
    
    print("\n" + "="*80)
    print(" OPCIÓN 2: CANDLES IN OVERSOLD MÍNIMO")
    print("="*80)
    
    for min_candles in [6, 7, 8, 9, 10, 11]:
        filtered = [t for t in trades if t['candles_oversold'] >= min_candles]
        stats = calc_stats(filtered)
        if stats:
            marker = " <-- IDEAL" if min_candles == 11 else ""
            print(f"  candles >= {min_candles:>2}: {stats['trades']:>4} trades, WR {stats['wr']:>5.1f}%, PF {stats['pf']:.2f}, Net ${stats['net']:>8,.0f}{marker}")
    
    print("\n" + "="*80)
    print(" OPCIÓN 3: COMBINACIÓN HORAS + CANDLES (buscando PF >= 1.5)")
    print("="*80)
    
    # Probar combinaciones
    best_combos = []
    
    for start, end in [(8, 20), (8, 22), (12, 22), (14, 22), (15, 24), (16, 24)]:
        for min_candles in [6, 7, 8, 9, 10, 11]:
            if end <= 24:
                filtered = [t for t in trades if start <= t['hour'] < end and t['candles_oversold'] >= min_candles]
            else:
                filtered = [t for t in trades if (t['hour'] >= start or t['hour'] < (end - 24)) and t['candles_oversold'] >= min_candles]
            
            stats = calc_stats(filtered)
            if stats and stats['pf'] >= 1.45:
                best_combos.append({
                    'hours': f"[{start:02d}:00-{end:02d}:00)",
                    'candles': min_candles,
                    **stats
                })
    
    # Ordenar por PF descendente
    best_combos.sort(key=lambda x: (-x['pf'], -x['trades']))
    
    print(f"\n  {'Horas':<20} {'Candles':>8} {'Trades':>8} {'WR':>8} {'PF':>8} {'Net P&L':>12}")
    print(f"  {'-'*70}")
    for combo in best_combos[:15]:
        pf_marker = " ***" if combo['pf'] >= 1.5 else ""
        print(f"  {combo['hours']:<20} {'>= ' + str(combo['candles']):>8} {combo['trades']:>8} {combo['wr']:>7.1f}% {combo['pf']:>8.2f} ${combo['net']:>11,.0f}{pf_marker}")
    
    print("\n" + "="*80)
    print(" OPCIÓN 4: HOURS_TO_AVOID + CANDLES (filtro actual mejorado)")
    print("="*80)
    
    hours_to_avoid_options = [
        [3, 6, 7, 10, 13, 20],  # Actual
        [3, 6, 7, 10, 13],      # Sin hora 20
        [6, 7, 10, 13, 20],     # Sin hora 3
        [6, 7, 10, 13],         # Más conservador
        [3, 6, 7, 10],          # Madrugada + mañana
    ]
    
    for hours_avoid in hours_to_avoid_options:
        for min_candles in [6, 7, 8, 9, 10, 11]:
            filtered = [t for t in trades if t['hour'] not in hours_avoid and t['candles_oversold'] >= min_candles]
            stats = calc_stats(filtered)
            if stats and stats['pf'] >= 1.45:
                pf_marker = " ***" if stats['pf'] >= 1.5 else ""
                print(f"  Avoid {str(hours_avoid):<25} candles >= {min_candles}: {stats['trades']:>4} trades, WR {stats['wr']:>5.1f}%, PF {stats['pf']:.2f}, Net ${stats['net']:>8,.0f}{pf_marker}")
    
    print("\n" + "="*80)
    print(" OPCIÓN 5: SOLO CANDLES = 11 (sin filtro de horas adicional)")
    print("="*80)
    
    # Solo candles = 11 (exactamente)
    filtered = [t for t in trades if t['candles_oversold'] == 11]
    stats = calc_stats(filtered)
    if stats:
        print(f"  candles == 11: {stats['trades']:>4} trades, WR {stats['wr']:>5.1f}%, PF {stats['pf']:.2f}, Net ${stats['net']:>8,.0f}")
    
    # Candles >= 10 (10 y 11)
    filtered = [t for t in trades if t['candles_oversold'] >= 10]
    stats = calc_stats(filtered)
    if stats:
        print(f"  candles >= 10: {stats['trades']:>4} trades, WR {stats['wr']:>5.1f}%, PF {stats['pf']:.2f}, Net ${stats['net']:>8,.0f}")
    
    # Candles >= 9
    filtered = [t for t in trades if t['candles_oversold'] >= 9]
    stats = calc_stats(filtered)
    if stats:
        print(f"  candles >= 9:  {stats['trades']:>4} trades, WR {stats['wr']:>5.1f}%, PF {stats['pf']:.2f}, Net ${stats['net']:>8,.0f}")
    
    print("\n" + "="*80)
    print(" RECOMENDACIÓN FINAL")
    print("="*80)
    
    # Mejor opción que mantiene trades razonables
    print("\n  Opciones para PF >= 1.5 con menos restricción:")
    
    # Opción A: Solo subir candles mínimo a 9
    filtered = [t for t in trades if t['candles_oversold'] >= 9]
    stats = calc_stats(filtered)
    print(f"\n  A) candles >= 9 (sin cambiar horas):")
    print(f"     {stats['trades']} trades, WR {stats['wr']:.1f}%, PF {stats['pf']:.2f}, Net ${stats['net']:,.0f}")
    
    # Opción B: Mantener candles 6-11 pero usar rango de horas 8-22
    filtered = [t for t in trades if 8 <= t['hour'] < 22]
    stats = calc_stats(filtered)
    print(f"\n  B) Horas [08:00-22:00) + candles >= 6:")
    print(f"     {stats['trades']} trades, WR {stats['wr']:.1f}%, PF {stats['pf']:.2f}, Net ${stats['net']:,.0f}")
    
    # Opción C: Horas 8-22 + candles >= 9
    filtered = [t for t in trades if 8 <= t['hour'] < 22 and t['candles_oversold'] >= 9]
    stats = calc_stats(filtered)
    print(f"\n  C) Horas [08:00-22:00) + candles >= 9:")
    print(f"     {stats['trades']} trades, WR {stats['wr']:.1f}%, PF {stats['pf']:.2f}, Net ${stats['net']:,.0f}")
    
    # Opción D: Candles >= 9 + evitar horas malas reducidas
    filtered = [t for t in trades if t['hour'] not in [3, 6, 7, 10, 13, 20] and t['candles_oversold'] >= 9]
    stats = calc_stats(filtered)
    print(f"\n  D) Avoid [3,6,7,10,13,20] + candles >= 9:")
    print(f"     {stats['trades']} trades, WR {stats['wr']:.1f}%, PF {stats['pf']:.2f}, Net ${stats['net']:,.0f}")


if __name__ == "__main__":
    main()
