"""
Análisis profundo de patrones en trades ERIS
Busca correlaciones para mejorar PF sin ahogar entradas
"""
import re
from collections import defaultdict
import statistics

# Archivo a analizar
FILE_PATH = r"temp_reports\ERIS_USDCHF_20251207_162400.txt"

def parse_trades(filepath):
    """Parsea el archivo de trades y extrae toda la información"""
    trades = []
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Patrón para extraer cada trade completo
    entry_pattern = r"ENTRY #(\d+)\nTime: ([^\n]+)\nDirection: ([^\n]+)\nEntry Price: ([^\n]+)\nStop Loss: ([^\n]+)\nTake Profit: ([^\n]+)\nATR: ([^\n]+)\nZ-Score: ([^\n]+)\nCandles in Oversold: ([^\n]+)\nEMA\(70\): ([^\n]+)\nUpper Band: ([^\n]+)\nLower Band: ([^\n]+)\nDistance to EMA: ([^\n]+)\nDistance to Lower: ([^\n]+)"
    
    exit_pattern = r"EXIT #(\d+)\nTime: ([^\n]+)\nExit Price: ([^\n]+)\nExit Reason: ([^\n]+)\nResult: ([^\n]+)\nP&L: ([^\n]+)"
    
    entries = re.findall(entry_pattern, content)
    exits = re.findall(exit_pattern, content)
    
    for i, (entry, exit_data) in enumerate(zip(entries, exits)):
        trade = {
            'id': int(entry[0]),
            'entry_time': entry[1],
            'direction': entry[2],
            'entry_price': float(entry[3]),
            'stop_loss': float(entry[4]),
            'take_profit': float(entry[5]),
            'atr': float(entry[6]),
            'zscore': float(entry[7]),
            'candles_oversold': int(entry[8]),
            'ema': float(entry[9]),
            'upper_band': float(entry[10]),
            'lower_band': float(entry[11]),
            'dist_to_ema': float(entry[12]),
            'dist_to_lower': float(entry[13]),
            'exit_time': exit_data[1],
            'exit_price': float(exit_data[2]),
            'exit_reason': exit_data[3],
            'result': exit_data[4],
            'pnl': float(exit_data[5])
        }
        # Calcular métricas adicionales
        trade['hour'] = int(trade['entry_time'].split(' ')[1].split(':')[0])
        trade['weekday'] = None  # Podríamos calcularlo si fuera necesario
        trade['dist_to_lower_ratio'] = trade['dist_to_lower'] / trade['atr'] if trade['atr'] > 0 else 0
        trade['dist_to_ema_ratio'] = trade['dist_to_ema'] / trade['atr'] if trade['atr'] > 0 else 0
        trade['band_width'] = trade['upper_band'] - trade['lower_band']
        trade['band_width_ratio'] = trade['band_width'] / trade['atr'] if trade['atr'] > 0 else 0
        
        trades.append(trade)
    
    return trades


def analyze_by_metric(trades, metric_name, bins):
    """Analiza trades agrupados por rangos de una métrica"""
    results = defaultdict(lambda: {'wins': 0, 'losses': 0, 'gross_profit': 0, 'gross_loss': 0})
    
    for trade in trades:
        value = trade[metric_name]
        # Encontrar el bin correspondiente
        bin_label = None
        for i, (low, high) in enumerate(bins):
            if low <= value < high:
                bin_label = f"[{low}, {high})"
                break
        if bin_label is None:
            continue
        
        if trade['result'] == 'WIN':
            results[bin_label]['wins'] += 1
            results[bin_label]['gross_profit'] += trade['pnl']
        else:
            results[bin_label]['losses'] += 1
            results[bin_label]['gross_loss'] += abs(trade['pnl'])
    
    return results


def print_analysis(title, results, bins):
    """Imprime análisis formateado"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")
    print(f"{'Range':<20} {'Trades':>8} {'WR':>8} {'PF':>8} {'Net P&L':>12}")
    print(f"{'-'*60}")
    
    for low, high in bins:
        bin_label = f"[{low}, {high})"
        if bin_label in results:
            data = results[bin_label]
            total = data['wins'] + data['losses']
            wr = (data['wins'] / total * 100) if total > 0 else 0
            pf = (data['gross_profit'] / data['gross_loss']) if data['gross_loss'] > 0 else float('inf')
            net = data['gross_profit'] - data['gross_loss']
            print(f"{bin_label:<20} {total:>8} {wr:>7.1f}% {pf:>8.2f} {net:>12.2f}")


def analyze_combined(trades, metric1, bins1, metric2, bins2, metric1_filter_range):
    """Analiza métrica2 filtrada por un rango de métrica1"""
    filtered = [t for t in trades if metric1_filter_range[0] <= t[metric1] < metric1_filter_range[1]]
    results = analyze_by_metric(filtered, metric2, bins2)
    return results, len(filtered)


def main():
    trades = parse_trades(FILE_PATH)
    print(f"\nTotal trades parseados: {len(trades)}")
    
    # Estadísticas generales
    wins = sum(1 for t in trades if t['result'] == 'WIN')
    losses = len(trades) - wins
    gross_profit = sum(t['pnl'] for t in trades if t['result'] == 'WIN')
    gross_loss = sum(abs(t['pnl']) for t in trades if t['result'] == 'LOSS')
    
    print(f"\n=== ESTADÍSTICAS ACTUALES ===")
    print(f"Trades: {len(trades)} | Wins: {wins} | Losses: {losses}")
    print(f"Win Rate: {wins/len(trades)*100:.1f}%")
    print(f"Profit Factor: {gross_profit/gross_loss:.2f}")
    print(f"Net P&L: ${gross_profit - gross_loss:,.2f}")
    
    # 1. ANÁLISIS POR Z-SCORE
    zscore_bins = [(-3.0, -2.5), (-2.5, -2.0), (-2.0, -1.5), (-1.5, -1.0)]
    results = analyze_by_metric(trades, 'zscore', zscore_bins)
    print_analysis("ANÁLISIS POR Z-SCORE", results, zscore_bins)
    
    # 2. ANÁLISIS POR CANDLES IN OVERSOLD
    candles_bins = [(6, 7), (7, 8), (8, 9), (9, 10), (10, 11), (11, 12)]
    results = analyze_by_metric(trades, 'candles_oversold', candles_bins)
    print_analysis("ANÁLISIS POR CANDLES IN OVERSOLD", results, candles_bins)
    
    # 3. ANÁLISIS POR HORA
    hour_bins = [(0, 4), (4, 8), (8, 12), (12, 16), (16, 20), (20, 24)]
    results = analyze_by_metric(trades, 'hour', hour_bins)
    print_analysis("ANÁLISIS POR HORA", results, hour_bins)
    
    # 4. ANÁLISIS POR ATR (volatilidad)
    atr_bins = [(0.0001, 0.0002), (0.0002, 0.0003), (0.0003, 0.0004), (0.0004, 0.0005), (0.0005, 0.001)]
    results = analyze_by_metric(trades, 'atr', atr_bins)
    print_analysis("ANÁLISIS POR ATR (VOLATILIDAD)", results, atr_bins)
    
    # 5. ANÁLISIS POR DISTANCE TO LOWER (importante!)
    # Valores típicos parecen ser -0.001 a +0.001
    dist_lower_bins = [(-0.0005, 0), (0, 0.0002), (0.0002, 0.0004), (0.0004, 0.0006), (0.0006, 0.001)]
    results = analyze_by_metric(trades, 'dist_to_lower', dist_lower_bins)
    print_analysis("ANÁLISIS POR DISTANCE TO LOWER BAND", results, dist_lower_bins)
    
    # 6. ANÁLISIS POR DISTANCE TO LOWER RATIO (normalizado por ATR)
    dist_ratio_bins = [(-2, -1), (-1, 0), (0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0)]
    results = analyze_by_metric(trades, 'dist_to_lower_ratio', dist_ratio_bins)
    print_analysis("ANÁLISIS POR DIST TO LOWER / ATR (ratio)", results, dist_ratio_bins)
    
    # 7. ANÁLISIS POR DISTANCE TO EMA RATIO
    ema_ratio_bins = [(-3, -2), (-2, -1.5), (-1.5, -1), (-1, -0.5), (-0.5, 0)]
    results = analyze_by_metric(trades, 'dist_to_ema_ratio', ema_ratio_bins)
    print_analysis("ANÁLISIS POR DIST TO EMA / ATR (ratio)", results, ema_ratio_bins)
    
    # ============================================================
    # ANÁLISIS COMBINADOS PARA ENCONTRAR FILTROS ÓPTIMOS
    # ============================================================
    
    print("\n" + "="*80)
    print(" ANÁLISIS COMBINADOS - BUSCANDO FILTROS ÓPTIMOS")
    print("="*80)
    
    # Análisis: ¿Qué pasa si filtramos por dist_to_lower_ratio > X?
    print("\n--- FILTRO: Distance to Lower Ratio (dist_to_lower / ATR) ---")
    for threshold in [-0.5, 0, 0.25, 0.5, 0.75, 1.0]:
        filtered = [t for t in trades if t['dist_to_lower_ratio'] >= threshold]
        if len(filtered) > 20:
            wins = sum(1 for t in filtered if t['result'] == 'WIN')
            gp = sum(t['pnl'] for t in filtered if t['result'] == 'WIN')
            gl = sum(abs(t['pnl']) for t in filtered if t['result'] == 'LOSS')
            pf = gp/gl if gl > 0 else 999
            wr = wins/len(filtered)*100
            net = gp - gl
            print(f"  ratio >= {threshold:>5.2f}: {len(filtered):>4} trades, WR {wr:>5.1f}%, PF {pf:.2f}, Net ${net:,.0f}")
    
    # Análisis: ¿Qué pasa si filtramos por dist_to_ema_ratio?
    print("\n--- FILTRO: Distance to EMA Ratio (dist_to_ema / ATR) ---")
    for threshold in [-2.5, -2.0, -1.5, -1.25, -1.0, -0.75]:
        filtered = [t for t in trades if t['dist_to_ema_ratio'] <= threshold]
        if len(filtered) > 20:
            wins = sum(1 for t in filtered if t['result'] == 'WIN')
            gp = sum(t['pnl'] for t in filtered if t['result'] == 'WIN')
            gl = sum(abs(t['pnl']) for t in filtered if t['result'] == 'LOSS')
            pf = gp/gl if gl > 0 else 999
            wr = wins/len(filtered)*100
            net = gp - gl
            print(f"  ratio <= {threshold:>5.2f}: {len(filtered):>4} trades, WR {wr:>5.1f}%, PF {pf:.2f}, Net ${net:,.0f}")
    
    # Análisis: ¿Qué pasa con Z-Score más profundo?
    print("\n--- FILTRO: Z-Score máximo ---")
    for zscore_max in [-1.0, -1.2, -1.3, -1.4, -1.5, -1.6]:
        filtered = [t for t in trades if t['zscore'] <= zscore_max]
        if len(filtered) > 20:
            wins = sum(1 for t in filtered if t['result'] == 'WIN')
            gp = sum(t['pnl'] for t in filtered if t['result'] == 'WIN')
            gl = sum(abs(t['pnl']) for t in filtered if t['result'] == 'LOSS')
            pf = gp/gl if gl > 0 else 999
            wr = wins/len(filtered)*100
            net = gp - gl
            print(f"  zscore <= {zscore_max:>5.2f}: {len(filtered):>4} trades, WR {wr:>5.1f}%, PF {pf:.2f}, Net ${net:,.0f}")
    
    # Análisis: Candles in oversold mínimo
    print("\n--- FILTRO: Candles in Oversold mínimo ---")
    for min_candles in [6, 7, 8, 9, 10]:
        filtered = [t for t in trades if t['candles_oversold'] >= min_candles]
        if len(filtered) > 20:
            wins = sum(1 for t in filtered if t['result'] == 'WIN')
            gp = sum(t['pnl'] for t in filtered if t['result'] == 'WIN')
            gl = sum(abs(t['pnl']) for t in filtered if t['result'] == 'LOSS')
            pf = gp/gl if gl > 0 else 999
            wr = wins/len(filtered)*100
            net = gp - gl
            print(f"  candles >= {min_candles:>2}: {len(filtered):>4} trades, WR {wr:>5.1f}%, PF {pf:.2f}, Net ${net:,.0f}")
    
    # Análisis: ATR mínimo (volatilidad mínima)
    print("\n--- FILTRO: ATR mínimo ---")
    for min_atr in [0.0001, 0.00015, 0.0002, 0.00025, 0.0003]:
        filtered = [t for t in trades if t['atr'] >= min_atr]
        if len(filtered) > 20:
            wins = sum(1 for t in filtered if t['result'] == 'WIN')
            gp = sum(t['pnl'] for t in filtered if t['result'] == 'WIN')
            gl = sum(abs(t['pnl']) for t in filtered if t['result'] == 'LOSS')
            pf = gp/gl if gl > 0 else 999
            wr = wins/len(filtered)*100
            net = gp - gl
            print(f"  ATR >= {min_atr:.5f}: {len(filtered):>4} trades, WR {wr:>5.1f}%, PF {pf:.2f}, Net ${net:,.0f}")
    
    # Análisis: ATR máximo
    print("\n--- FILTRO: ATR máximo ---")
    for max_atr in [0.0006, 0.0005, 0.00045, 0.0004, 0.00035]:
        filtered = [t for t in trades if t['atr'] <= max_atr]
        if len(filtered) > 20:
            wins = sum(1 for t in filtered if t['result'] == 'WIN')
            gp = sum(t['pnl'] for t in filtered if t['result'] == 'WIN')
            gl = sum(abs(t['pnl']) for t in filtered if t['result'] == 'LOSS')
            pf = gp/gl if gl > 0 else 999
            wr = wins/len(filtered)*100
            net = gp - gl
            print(f"  ATR <= {max_atr:.5f}: {len(filtered):>4} trades, WR {wr:>5.1f}%, PF {pf:.2f}, Net ${net:,.0f}")
    
    # Análisis: Horas a evitar
    print("\n--- FILTRO: Evitar horas específicas ---")
    problematic_hours = []
    for hour in range(24):
        hour_trades = [t for t in trades if t['hour'] == hour]
        if len(hour_trades) >= 10:
            wins = sum(1 for t in hour_trades if t['result'] == 'WIN')
            gp = sum(t['pnl'] for t in hour_trades if t['result'] == 'WIN')
            gl = sum(abs(t['pnl']) for t in hour_trades if t['result'] == 'LOSS')
            pf = gp/gl if gl > 0 else 999
            if pf < 1.0:
                problematic_hours.append((hour, len(hour_trades), pf))
    
    print(f"  Horas con PF < 1.0: {problematic_hours}")
    
    if problematic_hours:
        hours_to_avoid = [h[0] for h in problematic_hours]
        filtered = [t for t in trades if t['hour'] not in hours_to_avoid]
        wins = sum(1 for t in filtered if t['result'] == 'WIN')
        gp = sum(t['pnl'] for t in filtered if t['result'] == 'WIN')
        gl = sum(abs(t['pnl']) for t in filtered if t['result'] == 'LOSS')
        pf = gp/gl if gl > 0 else 999
        wr = wins/len(filtered)*100
        net = gp - gl
        print(f"  Sin horas {hours_to_avoid}: {len(filtered):>4} trades, WR {wr:>5.1f}%, PF {pf:.2f}, Net ${net:,.0f}")
    
    # ============================================================
    # COMBINACIONES SIMPLES
    # ============================================================
    print("\n" + "="*80)
    print(" COMBINACIONES SIMPLES (1 filtro adicional)")
    print("="*80)
    
    baseline_trades = len(trades)
    baseline_pf = gross_profit / gross_loss
    
    # Probar filtros simples que no reduzcan mucho las entradas
    print(f"\n Baseline: {baseline_trades} trades, PF {baseline_pf:.2f}")
    print("-" * 60)
    
    filters_to_test = [
        ('dist_to_lower_ratio >= 0', lambda t: t['dist_to_lower_ratio'] >= 0),
        ('dist_to_lower_ratio >= 0.25', lambda t: t['dist_to_lower_ratio'] >= 0.25),
        ('dist_to_lower >= 0', lambda t: t['dist_to_lower'] >= 0),
        ('zscore <= -1.2', lambda t: t['zscore'] <= -1.2),
        ('zscore <= -1.3', lambda t: t['zscore'] <= -1.3),
        ('candles >= 7', lambda t: t['candles_oversold'] >= 7),
        ('candles >= 8', lambda t: t['candles_oversold'] >= 8),
        ('ATR >= 0.0002', lambda t: t['atr'] >= 0.0002),
        ('ATR <= 0.0005', lambda t: t['atr'] <= 0.0005),
        ('hour not in [0,1,2,3,4,5]', lambda t: t['hour'] not in [0,1,2,3,4,5]),
    ]
    
    for name, filter_func in filters_to_test:
        filtered = [t for t in trades if filter_func(t)]
        if len(filtered) >= 100:  # Al menos 100 trades
            wins = sum(1 for t in filtered if t['result'] == 'WIN')
            gp = sum(t['pnl'] for t in filtered if t['result'] == 'WIN')
            gl = sum(abs(t['pnl']) for t in filtered if t['result'] == 'LOSS')
            pf = gp/gl if gl > 0 else 999
            wr = wins/len(filtered)*100
            net = gp - gl
            reduction = (1 - len(filtered)/baseline_trades) * 100
            pf_gain = ((pf/baseline_pf) - 1) * 100
            print(f"  {name:<30}: {len(filtered):>4} trades (-{reduction:>4.1f}%), PF {pf:.2f} ({pf_gain:+.1f}%), Net ${net:,.0f}")


if __name__ == "__main__":
    main()
