"""Análisis de Log KOI USDJPY - Buscar patrones para filtros"""
import re
from collections import defaultdict
from pathlib import Path

LOG_FILE = Path(__file__).parent.parent.parent / 'temp_reports' / 'KOI_USDJPY_trades_20251225_121020.txt'

def parse_log():
    """Parse trade log file"""
    with open(LOG_FILE, 'r') as f:
        content = f.read()
    
    # Parse entries
    entry_pattern = r'ENTRY #(\d+)\nTime: (\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):\d{2}\nEntry Price: ([\d.]+)\nStop Loss: ([\d.]+)\nTake Profit: ([\d.]+)\nSL Pips: ([\d.]+)\nATR: ([\d.]+)\nCCI: ([\d.]+)'
    entries = re.findall(entry_pattern, content)
    
    # Parse exits
    exit_pattern = r'EXIT #(\d+)\nTime: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\nExit Reason: (\w+)\nP&L: \$([-\d,.]+)'
    exits = re.findall(exit_pattern, content)
    
    trades = []
    for i, entry in enumerate(entries):
        if i >= len(exits):
            break
        
        pnl_str = exits[i][3].replace(',', '')
        pnl = float(pnl_str)
        
        trades.append({
            'id': int(entry[0]),
            'year': int(entry[1]),
            'month': int(entry[2]),
            'day': int(entry[3]),
            'hour': int(entry[4]),
            'minute': int(entry[5]),
            'entry_price': float(entry[6]),
            'sl': float(entry[7]),
            'tp': float(entry[8]),
            'sl_pips': float(entry[9]),
            'atr': float(entry[10]),
            'cci': float(entry[11]),
            'exit_reason': exits[i][2],
            'pnl': pnl,
            'is_win': pnl > 0
        })
    
    return trades


def analyze_hourly(trades):
    """Análisis por hora de entrada"""
    print("\n" + "="*70)
    print("ANÁLISIS POR HORA DE ENTRADA (UTC)")
    print("="*70)
    
    hourly = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0.0})
    
    for t in trades:
        hourly[t['hour']]['trades'] += 1
        hourly[t['hour']]['pnl'] += t['pnl']
        if t['is_win']:
            hourly[t['hour']]['wins'] += 1
    
    print(f"{'Hour':>4} {'Trades':>7} {'Wins':>5} {'WR%':>7} {'PnL':>12} {'AvgPnL':>10}")
    print("-"*70)
    
    for hour in sorted(hourly.keys()):
        h = hourly[hour]
        wr = (h['wins'] / h['trades'] * 100) if h['trades'] > 0 else 0
        avg = h['pnl'] / h['trades'] if h['trades'] > 0 else 0
        status = "✓" if h['pnl'] > 0 else "✗"
        print(f"{hour:>4} {h['trades']:>7} {h['wins']:>5} {wr:>6.1f}% ${h['pnl']:>10,.0f} ${avg:>9,.0f} {status}")
    
    # Best/Worst hours
    sorted_hours = sorted(hourly.items(), key=lambda x: x[1]['pnl'], reverse=True)
    print()
    print(f"BEST HOURS (PnL > 0):  {[h[0] for h in sorted_hours if h[1]['pnl'] > 0]}")
    print(f"WORST HOURS (PnL < 0): {[h[0] for h in sorted_hours if h[1]['pnl'] < 0]}")
    
    return hourly


def analyze_atr(trades):
    """Análisis por rango ATR"""
    print("\n" + "="*70)
    print("ANÁLISIS POR ATR (Volatilidad)")
    print("="*70)
    
    # Define ATR buckets for JPY (ATR values like 0.03 = 3 pips)
    buckets = [
        (0, 0.015, "< 1.5 pips"),
        (0.015, 0.025, "1.5-2.5 pips"),
        (0.025, 0.035, "2.5-3.5 pips"),
        (0.035, 0.050, "3.5-5.0 pips"),
        (0.050, 0.070, "5.0-7.0 pips"),
        (0.070, 0.100, "7.0-10 pips"),
        (0.100, 999, "> 10 pips"),
    ]
    
    atr_stats = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0.0})
    
    for t in trades:
        for low, high, label in buckets:
            if low <= t['atr'] < high:
                atr_stats[label]['trades'] += 1
                atr_stats[label]['pnl'] += t['pnl']
                if t['is_win']:
                    atr_stats[label]['wins'] += 1
                break
    
    print(f"{'ATR Range':>15} {'Trades':>7} {'Wins':>5} {'WR%':>7} {'PnL':>12} {'AvgPnL':>10}")
    print("-"*70)
    
    for _, _, label in buckets:
        if label in atr_stats:
            s = atr_stats[label]
            wr = (s['wins'] / s['trades'] * 100) if s['trades'] > 0 else 0
            avg = s['pnl'] / s['trades'] if s['trades'] > 0 else 0
            status = "✓" if s['pnl'] > 0 else "✗"
            print(f"{label:>15} {s['trades']:>7} {s['wins']:>5} {wr:>6.1f}% ${s['pnl']:>10,.0f} ${avg:>9,.0f} {status}")
    
    return atr_stats


def analyze_cci(trades):
    """Análisis por rango CCI"""
    print("\n" + "="*70)
    print("ANÁLISIS POR CCI (Momentum)")
    print("="*70)
    
    buckets = [
        (120, 140, "120-140"),
        (140, 160, "140-160"),
        (160, 180, "160-180"),
        (180, 200, "180-200"),
        (200, 250, "200-250"),
        (250, 999, "> 250"),
    ]
    
    cci_stats = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0.0})
    
    for t in trades:
        for low, high, label in buckets:
            if low <= t['cci'] < high:
                cci_stats[label]['trades'] += 1
                cci_stats[label]['pnl'] += t['pnl']
                if t['is_win']:
                    cci_stats[label]['wins'] += 1
                break
    
    print(f"{'CCI Range':>15} {'Trades':>7} {'Wins':>5} {'WR%':>7} {'PnL':>12} {'AvgPnL':>10}")
    print("-"*70)
    
    for _, _, label in buckets:
        if label in cci_stats:
            s = cci_stats[label]
            wr = (s['wins'] / s['trades'] * 100) if s['trades'] > 0 else 0
            avg = s['pnl'] / s['trades'] if s['trades'] > 0 else 0
            status = "✓" if s['pnl'] > 0 else "✗"
            print(f"{label:>15} {s['trades']:>7} {s['wins']:>5} {wr:>6.1f}% ${s['pnl']:>10,.0f} ${avg:>9,.0f} {status}")
    
    return cci_stats


def analyze_sl_pips(trades):
    """Análisis por SL en pips"""
    print("\n" + "="*70)
    print("ANÁLISIS POR SL PIPS (Tamaño del Stop)")
    print("="*70)
    
    buckets = [
        (0, 5, "< 5 pips"),
        (5, 10, "5-10 pips"),
        (10, 15, "10-15 pips"),
        (15, 20, "15-20 pips"),
        (20, 30, "20-30 pips"),
        (30, 999, "> 30 pips"),
    ]
    
    sl_stats = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0.0})
    
    for t in trades:
        for low, high, label in buckets:
            if low <= t['sl_pips'] < high:
                sl_stats[label]['trades'] += 1
                sl_stats[label]['pnl'] += t['pnl']
                if t['is_win']:
                    sl_stats[label]['wins'] += 1
                break
    
    print(f"{'SL Range':>15} {'Trades':>7} {'Wins':>5} {'WR%':>7} {'PnL':>12} {'AvgPnL':>10}")
    print("-"*70)
    
    for _, _, label in buckets:
        if label in sl_stats:
            s = sl_stats[label]
            wr = (s['wins'] / s['trades'] * 100) if s['trades'] > 0 else 0
            avg = s['pnl'] / s['trades'] if s['trades'] > 0 else 0
            status = "✓" if s['pnl'] > 0 else "✗"
            print(f"{label:>15} {s['trades']:>7} {s['wins']:>5} {wr:>6.1f}% ${s['pnl']:>10,.0f} ${avg:>9,.0f} {status}")
    
    return sl_stats


def analyze_yearly(trades):
    """Análisis por año"""
    print("\n" + "="*70)
    print("ANÁLISIS POR AÑO")
    print("="*70)
    
    yearly = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0.0})
    
    for t in trades:
        yearly[t['year']]['trades'] += 1
        yearly[t['year']]['pnl'] += t['pnl']
        if t['is_win']:
            yearly[t['year']]['wins'] += 1
    
    print(f"{'Year':>6} {'Trades':>7} {'Wins':>5} {'WR%':>7} {'PnL':>12}")
    print("-"*50)
    
    for year in sorted(yearly.keys()):
        y = yearly[year]
        wr = (y['wins'] / y['trades'] * 100) if y['trades'] > 0 else 0
        status = "✓" if y['pnl'] > 0 else "✗"
        print(f"{year:>6} {y['trades']:>7} {y['wins']:>5} {wr:>6.1f}% ${y['pnl']:>10,.0f} {status}")
    
    return yearly


def suggest_filters(trades, hourly, atr_stats, cci_stats, sl_stats):
    """Sugerir filtros basados en análisis"""
    print("\n" + "="*70)
    print("FILTROS SUGERIDOS")
    print("="*70)
    
    # Hour filter
    good_hours = [h for h, stats in hourly.items() if stats['pnl'] > 0 and stats['trades'] >= 10]
    bad_hours = [h for h, stats in hourly.items() if stats['pnl'] < -1000]
    
    if good_hours:
        print(f"\n1. FILTRO HORARIO:")
        print(f"   Mantener horas: {sorted(good_hours)}")
        print(f"   Evitar horas:   {sorted(bad_hours)}")
        
        # Calculate potential improvement
        filtered_pnl = sum(hourly[h]['pnl'] for h in good_hours)
        filtered_trades = sum(hourly[h]['trades'] for h in good_hours)
        filtered_wins = sum(hourly[h]['wins'] for h in good_hours)
        print(f"   Resultado filtrado: {filtered_trades} trades, WR={filtered_wins/filtered_trades*100:.1f}%, PnL=${filtered_pnl:,.0f}")
    
    print("\n2. FILTROS DISPONIBLES EN KOI:")
    print("   - Session Filter (ENTRY_START_HOUR, ENTRY_END_HOUR)")
    print("   - ATR Filter (ATR_MIN_THRESHOLD, ATR_MAX_THRESHOLD)")
    print("   - SL Range Filter (MIN_SL_PIPS, MAX_SL_PIPS)")
    print("   - CCI Threshold (CCI_THRESHOLD)")


def main():
    print("="*70)
    print("ANÁLISIS DE LOG KOI USDJPY")
    print("="*70)
    
    trades = parse_log()
    print(f"\nTotal trades parseados: {len(trades)}")
    
    total_pnl = sum(t['pnl'] for t in trades)
    total_wins = sum(1 for t in trades if t['is_win'])
    print(f"PnL Total: ${total_pnl:,.0f}")
    print(f"Win Rate: {total_wins/len(trades)*100:.1f}%")
    
    # Run analyses
    hourly = analyze_hourly(trades)
    atr_stats = analyze_atr(trades)
    cci_stats = analyze_cci(trades)
    sl_stats = analyze_sl_pips(trades)
    yearly = analyze_yearly(trades)
    
    # Suggestions
    suggest_filters(trades, hourly, atr_stats, cci_stats, sl_stats)


if __name__ == "__main__":
    main()
