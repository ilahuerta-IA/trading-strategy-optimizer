"""
ERIS USDCAD Trade Report Analyzer
Analiza el reporte de trades para encontrar patrones óptimos
"""

import re
from collections import defaultdict
import statistics

def parse_report(filepath):
    """Parse el reporte de trades y extrae datos estructurados"""
    trades = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Patrón para extraer cada trade completo (entry + exit)
    trade_pattern = r'ENTRY #(\d+)\n(.*?)EXIT #\1\n(.*?)(?=ENTRY #|\n={12}\nSUMMARY|$)'
    
    for match in re.finditer(trade_pattern, content, re.DOTALL):
        trade_num = int(match.group(1))
        entry_block = match.group(2)
        exit_block = match.group(3)
        
        trade = {'trade_num': trade_num}
        
        # Parse entry data
        entry_patterns = {
            'entry_time': r'Time: (.+)',
            'direction': r'Direction: (.+)',
            'entry_price': r'Entry Price: ([\d.]+)',
            'stop_loss': r'Stop Loss: ([\d.]+)',
            'take_profit': r'Take Profit: ([\d.]+)',
            'atr': r'ATR: ([\d.]+)',
            'z_score': r'Z-Score: ([-\d.]+)',
            'ema': r'EMA\(70\): ([\d.]+)',
            'upper_band': r'Upper Band: ([\d.]+)',
            'lower_band': r'Lower Band: ([\d.]+)',
            'dist_ema': r'Distance to EMA: ([-\d.]+)',
            'dist_lower': r'Distance to Lower: ([-\d.]+)',
        }
        
        for key, pattern in entry_patterns.items():
            m = re.search(pattern, entry_block)
            if m:
                val = m.group(1).strip()
                try:
                    trade[key] = float(val) if key != 'entry_time' and key != 'direction' else val
                except:
                    trade[key] = val
        
        # Parse exit data
        exit_patterns = {
            'exit_time': r'Time: (.+)',
            'exit_price': r'Exit Price: ([\d.]+)',
            'exit_reason': r'Exit Reason: (.+)',
            'result': r'Result: (.+)',
            'pnl': r'P&L: ([-\d.]+)',
            'pips': r'Pips: ([-\d.]+)',
            'entry_oversold_candles': r'Entry Candles in Oversold: (\d+)',
        }
        
        for key, pattern in exit_patterns.items():
            m = re.search(pattern, exit_block)
            if m:
                val = m.group(1).strip()
                try:
                    trade[key] = float(val) if key not in ['exit_time', 'exit_reason', 'result'] else val
                except:
                    trade[key] = val
        
        if 'result' in trade:
            trades.append(trade)
    
    return trades


def analyze_by_zscore_ranges(trades):
    """Analiza rendimiento por rangos de Z-Score"""
    print("\n" + "="*70)
    print("ANÁLISIS POR RANGOS DE Z-SCORE")
    print("="*70)
    
    ranges = [
        (-10, -3, "Muy oversold (< -3)"),
        (-3, -2, "Oversold fuerte (-3 a -2)"),
        (-2, -1, "Oversold moderado (-2 a -1)"),
        (-1, 0, "Ligeramente oversold (-1 a 0)"),
        (0, 1, "Neutral (0 a 1)"),
        (1, 2, "Overbought ligero (1 a 2)"),
        (2, 3, "Overbought moderado (2 a 3)"),
        (3, 5, "Overbought fuerte (3 a 5)"),
        (5, 10, "Muy overbought (> 5)"),
    ]
    
    results = []
    for low, high, label in ranges:
        range_trades = [t for t in trades if 'z_score' in t and low <= t['z_score'] < high]
        if not range_trades:
            continue
        
        wins = sum(1 for t in range_trades if t.get('result') == 'WIN')
        losses = len(range_trades) - wins
        wr = wins / len(range_trades) * 100 if range_trades else 0
        
        gross_profit = sum(t['pnl'] for t in range_trades if t.get('result') == 'WIN')
        gross_loss = abs(sum(t['pnl'] for t in range_trades if t.get('result') == 'LOSS'))
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        net_pnl = sum(t['pnl'] for t in range_trades)
        
        results.append({
            'label': label,
            'low': low,
            'high': high,
            'trades': len(range_trades),
            'wins': wins,
            'losses': losses,
            'wr': wr,
            'pf': pf,
            'net_pnl': net_pnl
        })
        
        print(f"\n{label}:")
        print(f"  Trades: {len(range_trades)} | Wins: {wins} | Losses: {losses}")
        print(f"  Win Rate: {wr:.1f}% | PF: {pf:.2f} | Net P&L: ${net_pnl:,.2f}")
    
    # Encontrar mejores rangos
    print("\n" + "-"*70)
    print("TOP 3 MEJORES RANGOS POR PROFIT FACTOR:")
    sorted_pf = sorted([r for r in results if r['trades'] >= 100], key=lambda x: x['pf'], reverse=True)[:3]
    for r in sorted_pf:
        print(f"  {r['label']}: PF={r['pf']:.2f}, WR={r['wr']:.1f}%, Trades={r['trades']}")
    
    return results


def analyze_by_oversold_duration(trades):
    """Analiza rendimiento por duración en zona oversold"""
    print("\n" + "="*70)
    print("ANÁLISIS POR DURACIÓN EN ZONA OVERSOLD")
    print("="*70)
    
    # Nota: El reporte muestra entry_oversold_candles siempre como 0 porque 
    # los filtros estaban desactivados. Necesitamos otro enfoque.
    
    # Análisis por distancia a banda inferior (proxy de oversold)
    print("\nUsando 'Distancia a Banda Inferior' como proxy de condición oversold:")
    
    ranges = [
        (-0.001, 0, "Dentro de banda inferior (< 0)"),
        (0, 0.0003, "Muy cerca de banda (0-3 pips)"),
        (0.0003, 0.0006, "Cerca de banda (3-6 pips)"),
        (0.0006, 0.001, "Moderado (6-10 pips)"),
        (0.001, 0.002, "Lejos de banda (10-20 pips)"),
        (0.002, 0.005, "Muy lejos (> 20 pips)"),
    ]
    
    for low, high, label in ranges:
        range_trades = [t for t in trades if 'dist_lower' in t and low <= t['dist_lower'] < high]
        if not range_trades:
            continue
        
        wins = sum(1 for t in range_trades if t.get('result') == 'WIN')
        wr = wins / len(range_trades) * 100 if range_trades else 0
        
        gross_profit = sum(t['pnl'] for t in range_trades if t.get('result') == 'WIN')
        gross_loss = abs(sum(t['pnl'] for t in range_trades if t.get('result') == 'LOSS'))
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        net_pnl = sum(t['pnl'] for t in range_trades)
        
        print(f"\n{label}:")
        print(f"  Trades: {len(range_trades)} | Wins: {wins}")
        print(f"  Win Rate: {wr:.1f}% | PF: {pf:.2f} | Net P&L: ${net_pnl:,.2f}")


def analyze_by_atr(trades):
    """Analiza rendimiento por ATR"""
    print("\n" + "="*70)
    print("ANÁLISIS POR ATR (VOLATILIDAD)")
    print("="*70)
    
    ranges = [
        (0.0001, 0.00015, "ATR muy bajo (1-1.5 pips)"),
        (0.00015, 0.0002, "ATR bajo (1.5-2 pips)"),
        (0.0002, 0.00025, "ATR normal bajo (2-2.5 pips)"),
        (0.00025, 0.0003, "ATR normal (2.5-3 pips)"),
        (0.0003, 0.0004, "ATR alto (3-4 pips)"),
        (0.0004, 0.0005, "ATR muy alto (4-5 pips)"),
        (0.0005, 0.001, "ATR extremo (> 5 pips)"),
    ]
    
    results = []
    for low, high, label in ranges:
        range_trades = [t for t in trades if 'atr' in t and low <= t['atr'] < high]
        if not range_trades:
            continue
        
        wins = sum(1 for t in range_trades if t.get('result') == 'WIN')
        wr = wins / len(range_trades) * 100 if range_trades else 0
        
        gross_profit = sum(t['pnl'] for t in range_trades if t.get('result') == 'WIN')
        gross_loss = abs(sum(t['pnl'] for t in range_trades if t.get('result') == 'LOSS'))
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        net_pnl = sum(t['pnl'] for t in range_trades)
        
        results.append({
            'label': label,
            'trades': len(range_trades),
            'pf': pf,
            'wr': wr,
            'net_pnl': net_pnl
        })
        
        print(f"\n{label}:")
        print(f"  Trades: {len(range_trades)} | Wins: {wins}")
        print(f"  Win Rate: {wr:.1f}% | PF: {pf:.2f} | Net P&L: ${net_pnl:,.2f}")
    
    return results


def analyze_by_hour(trades):
    """Analiza rendimiento por hora del día"""
    print("\n" + "="*70)
    print("ANÁLISIS POR HORA DEL DÍA")
    print("="*70)
    
    hour_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0})
    
    for t in trades:
        if 'entry_time' in t:
            try:
                hour = int(t['entry_time'].split()[1].split(':')[0])
                if t.get('result') == 'WIN':
                    hour_stats[hour]['wins'] += 1
                else:
                    hour_stats[hour]['losses'] += 1
                hour_stats[hour]['pnl'] += t.get('pnl', 0)
            except:
                pass
    
    print(f"\n{'Hour':<6} {'Trades':<8} {'Wins':<6} {'Losses':<8} {'WR%':<8} {'Net P&L':<12}")
    print("-" * 60)
    
    best_hours = []
    worst_hours = []
    
    for hour in sorted(hour_stats.keys()):
        stats = hour_stats[hour]
        total = stats['wins'] + stats['losses']
        wr = stats['wins'] / total * 100 if total > 0 else 0
        
        # Calcular PF para esta hora
        hour_trades = [t for t in trades if 'entry_time' in t and int(t['entry_time'].split()[1].split(':')[0]) == hour]
        gross_profit = sum(t['pnl'] for t in hour_trades if t.get('result') == 'WIN')
        gross_loss = abs(sum(t['pnl'] for t in hour_trades if t.get('result') == 'LOSS'))
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        
        print(f"{hour:02d}:00  {total:<8} {stats['wins']:<6} {stats['losses']:<8} {wr:>5.1f}%  ${stats['pnl']:>10,.2f}")
        
        if total >= 100:
            if pf > 1.1:
                best_hours.append((hour, pf, wr, total))
            elif pf < 0.9:
                worst_hours.append((hour, pf, wr, total))
    
    print("\n" + "-"*60)
    print("MEJORES HORAS (PF > 1.1):")
    for h, pf, wr, cnt in sorted(best_hours, key=lambda x: x[1], reverse=True):
        print(f"  {h:02d}:00 - PF: {pf:.2f}, WR: {wr:.1f}%, Trades: {cnt}")
    
    print("\nPEORES HORAS (PF < 0.9):")
    for h, pf, wr, cnt in sorted(worst_hours, key=lambda x: x[1]):
        print(f"  {h:02d}:00 - PF: {pf:.2f}, WR: {wr:.1f}%, Trades: {cnt}")
    
    return best_hours, worst_hours


def analyze_mean_reversion_success(trades):
    """Analiza si el precio realmente regresa a la media después de entrar"""
    print("\n" + "="*70)
    print("ANÁLISIS DE MEAN REVERSION")
    print("="*70)
    
    # Trades con Z-Score negativo (precio por debajo de media)
    oversold_trades = [t for t in trades if 'z_score' in t and t['z_score'] < 0]
    overbought_trades = [t for t in trades if 'z_score' in t and t['z_score'] >= 0]
    
    print(f"\nTrades con Z-Score < 0 (Oversold - DEBERÍAN funcionar para LONG):")
    if oversold_trades:
        wins = sum(1 for t in oversold_trades if t.get('result') == 'WIN')
        wr = wins / len(oversold_trades) * 100
        gross_profit = sum(t['pnl'] for t in oversold_trades if t.get('result') == 'WIN')
        gross_loss = abs(sum(t['pnl'] for t in oversold_trades if t.get('result') == 'LOSS'))
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        net_pnl = sum(t['pnl'] for t in oversold_trades)
        print(f"  Total: {len(oversold_trades)} | Wins: {wins} | WR: {wr:.1f}%")
        print(f"  PF: {pf:.2f} | Net P&L: ${net_pnl:,.2f}")
    
    print(f"\nTrades con Z-Score >= 0 (Overbought - NO deberían funcionar para LONG):")
    if overbought_trades:
        wins = sum(1 for t in overbought_trades if t.get('result') == 'WIN')
        wr = wins / len(overbought_trades) * 100
        gross_profit = sum(t['pnl'] for t in overbought_trades if t.get('result') == 'WIN')
        gross_loss = abs(sum(t['pnl'] for t in overbought_trades if t.get('result') == 'LOSS'))
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        net_pnl = sum(t['pnl'] for t in overbought_trades)
        print(f"  Total: {len(overbought_trades)} | Wins: {wins} | WR: {wr:.1f}%")
        print(f"  PF: {pf:.2f} | Net P&L: ${net_pnl:,.2f}")
    
    # Análisis más detallado
    print("\n" + "-"*70)
    print("DETALLE POR DISTANCIA A EMA:")
    
    ranges = [
        (-0.003, -0.001, "Muy por debajo de EMA (< -10 pips)"),
        (-0.001, -0.0005, "Por debajo de EMA (-10 a -5 pips)"),
        (-0.0005, 0, "Ligeramente debajo (0 a -5 pips)"),
        (0, 0.0005, "Ligeramente arriba (0 a 5 pips)"),
        (0.0005, 0.001, "Por encima de EMA (5 a 10 pips)"),
        (0.001, 0.003, "Muy por encima (> 10 pips)"),
    ]
    
    for low, high, label in ranges:
        range_trades = [t for t in trades if 'dist_ema' in t and low <= t['dist_ema'] < high]
        if not range_trades:
            continue
        
        wins = sum(1 for t in range_trades if t.get('result') == 'WIN')
        wr = wins / len(range_trades) * 100 if range_trades else 0
        
        gross_profit = sum(t['pnl'] for t in range_trades if t.get('result') == 'WIN')
        gross_loss = abs(sum(t['pnl'] for t in range_trades if t.get('result') == 'LOSS'))
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        net_pnl = sum(t['pnl'] for t in range_trades)
        
        print(f"\n{label}:")
        print(f"  Trades: {len(range_trades)} | Wins: {wins}")
        print(f"  Win Rate: {wr:.1f}% | PF: {pf:.2f} | Net P&L: ${net_pnl:,.2f}")


def find_optimal_filters(trades):
    """Encuentra la combinación óptima de filtros"""
    print("\n" + "="*70)
    print("BÚSQUEDA DE COMBINACIÓN ÓPTIMA DE FILTROS")
    print("="*70)
    
    best_combinations = []
    
    # Probar diferentes combinaciones de Z-Score + ATR
    zscore_ranges = [
        (-5, 0), (-4, 0), (-3, 0), (-2, 0), (-3, 1), (-2, 1), (-2, 2), 
        (-1, 1), (-1, 2), (0, 2), (0, 3), (1, 3), (1, 4), (2, 5)
    ]
    
    atr_ranges = [
        (0.0001, 0.0003), (0.00015, 0.00035), (0.0002, 0.0004), 
        (0.00025, 0.00045), (0.0002, 0.0005), (0.00015, 0.0005)
    ]
    
    for z_low, z_high in zscore_ranges:
        for atr_low, atr_high in atr_ranges:
            filtered = [t for t in trades 
                       if 'z_score' in t and 'atr' in t
                       and z_low <= t['z_score'] <= z_high
                       and atr_low <= t['atr'] <= atr_high]
            
            if len(filtered) < 50:  # Mínimo 50 trades para significancia
                continue
            
            wins = sum(1 for t in filtered if t.get('result') == 'WIN')
            wr = wins / len(filtered) * 100
            
            gross_profit = sum(t['pnl'] for t in filtered if t.get('result') == 'WIN')
            gross_loss = abs(sum(t['pnl'] for t in filtered if t.get('result') == 'LOSS'))
            pf = gross_profit / gross_loss if gross_loss > 0 else 0
            net_pnl = sum(t['pnl'] for t in filtered)
            
            if pf > 1.0:
                best_combinations.append({
                    'z_range': (z_low, z_high),
                    'atr_range': (atr_low, atr_high),
                    'trades': len(filtered),
                    'wr': wr,
                    'pf': pf,
                    'net_pnl': net_pnl
                })
    
    # Ordenar por PF
    best_combinations.sort(key=lambda x: x['pf'], reverse=True)
    
    print("\nTOP 10 COMBINACIONES DE FILTROS:")
    print("-" * 80)
    for i, combo in enumerate(best_combinations[:10], 1):
        print(f"\n{i}. Z-Score: [{combo['z_range'][0]:.1f}, {combo['z_range'][1]:.1f}]")
        print(f"   ATR: [{combo['atr_range'][0]*10000:.1f}, {combo['atr_range'][1]*10000:.1f}] pips")
        print(f"   Trades: {combo['trades']} | WR: {combo['wr']:.1f}% | PF: {combo['pf']:.2f}")
        print(f"   Net P&L: ${combo['net_pnl']:,.2f}")
    
    return best_combinations


def analyze_by_year(trades):
    """Analiza rendimiento por año"""
    print("\n" + "="*70)
    print("ANÁLISIS POR AÑO")
    print("="*70)
    
    year_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0, 'trades': []})
    
    for t in trades:
        if 'entry_time' in t:
            try:
                year = int(t['entry_time'].split('-')[0])
                if t.get('result') == 'WIN':
                    year_stats[year]['wins'] += 1
                else:
                    year_stats[year]['losses'] += 1
                year_stats[year]['pnl'] += t.get('pnl', 0)
                year_stats[year]['trades'].append(t)
            except:
                pass
    
    print(f"\n{'Year':<6} {'Trades':<8} {'Wins':<6} {'WR%':<8} {'PF':<8} {'Net P&L':<12}")
    print("-" * 60)
    
    for year in sorted(year_stats.keys()):
        stats = year_stats[year]
        total = stats['wins'] + stats['losses']
        wr = stats['wins'] / total * 100 if total > 0 else 0
        
        gross_profit = sum(t['pnl'] for t in stats['trades'] if t.get('result') == 'WIN')
        gross_loss = abs(sum(t['pnl'] for t in stats['trades'] if t.get('result') == 'LOSS'))
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        
        print(f"{year}   {total:<8} {stats['wins']:<6} {wr:>5.1f}%  {pf:>6.2f}  ${stats['pnl']:>10,.2f}")


def main():
    filepath = r"c:\Iván\Yosoybuendesarrollador\Python\Portafolio\quant_bot_project\src\strategies\temp_reports\ERIS_USDCAD_20251207_215624.txt"
    
    print("Parseando reporte de trades...")
    trades = parse_report(filepath)
    print(f"Total trades parseados: {len(trades)}")
    
    # Verificar datos
    wins = sum(1 for t in trades if t.get('result') == 'WIN')
    print(f"Wins: {wins} | Losses: {len(trades) - wins}")
    
    # Ejecutar análisis
    analyze_by_year(trades)
    analyze_by_zscore_ranges(trades)
    analyze_mean_reversion_success(trades)
    analyze_by_atr(trades)
    analyze_by_hour(trades)
    analyze_by_oversold_duration(trades)
    
    # Buscar filtros óptimos
    best = find_optimal_filters(trades)
    
    print("\n" + "="*70)
    print("RECOMENDACIONES PARA ERIS USDCAD")
    print("="*70)
    if best:
        top = best[0]
        print(f"\nMEJOR CONFIGURACIÓN ENCONTRADA:")
        print(f"  Z-Score Range: [{top['z_range'][0]:.1f}, {top['z_range'][1]:.1f}]")
        print(f"  ATR Range: [{top['atr_range'][0]*10000:.2f}, {top['atr_range'][1]*10000:.2f}] pips")
        print(f"  Trades esperados: {top['trades']}")
        print(f"  Win Rate esperado: {top['wr']:.1f}%")
        print(f"  Profit Factor esperado: {top['pf']:.2f}")
        print(f"  Net P&L esperado: ${top['net_pnl']:,.2f}")


if __name__ == "__main__":
    main()
