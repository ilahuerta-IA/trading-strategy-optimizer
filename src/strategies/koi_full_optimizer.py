"""
KOI STRATEGY - OPTIMIZACIÓN COMPLETA CON BREAKOUT WINDOW
=========================================================
4 Fases de optimización (SIN filtros):
1. EMAs (mejores combinaciones sin EMA 144)
2. CCI (period y threshold)
3. SL/TP ratio
4. Breakout offset (pips)

Después: Analizar log para encontrar filtros específicos
"""

import subprocess
import re
import json
from datetime import datetime

def modify_and_run(params):
    """Modifica template y ejecuta backtest"""
    
    template_path = "koi_template.py"
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # EMAs
    if 'emas' in params:
        content = re.sub(r'EMA_1_PERIOD = \d+', f'EMA_1_PERIOD = {params["emas"][0]}', content)
        content = re.sub(r'EMA_2_PERIOD = \d+', f'EMA_2_PERIOD = {params["emas"][1]}', content)
        content = re.sub(r'EMA_3_PERIOD = \d+', f'EMA_3_PERIOD = {params["emas"][2]}', content)
        content = re.sub(r'EMA_4_PERIOD = \d+', f'EMA_4_PERIOD = {params["emas"][3]}', content)
        content = re.sub(r'EMA_5_PERIOD = \d+', f'EMA_5_PERIOD = {params["emas"][4]}', content)
    
    # CCI
    if 'cci_period' in params:
        content = re.sub(r'CCI_PERIOD = \d+', f'CCI_PERIOD = {params["cci_period"]}', content)
    if 'cci_threshold' in params:
        content = re.sub(r'CCI_THRESHOLD = \d+', f'CCI_THRESHOLD = {params["cci_threshold"]}', content)
    
    # SL/TP
    if 'sl_mult' in params:
        content = re.sub(r'ATR_SL_MULTIPLIER = [\d.]+', f'ATR_SL_MULTIPLIER = {params["sl_mult"]}', content)
    if 'tp_mult' in params:
        content = re.sub(r'ATR_TP_MULTIPLIER = [\d.]+', f'ATR_TP_MULTIPLIER = {params["tp_mult"]}', content)
    
    # Breakout offset
    if 'breakout_offset' in params:
        content = re.sub(r'BREAKOUT_LEVEL_OFFSET_PIPS = [\d.]+', 
                        f'BREAKOUT_LEVEL_OFFSET_PIPS = {params["breakout_offset"]}', content)
    
    # Breakout window candles
    if 'breakout_candles' in params:
        content = re.sub(r'BREAKOUT_WINDOW_CANDLES = \d+', 
                        f'BREAKOUT_WINDOW_CANDLES = {params["breakout_candles"]}', content)
    
    # Asegurar filtros desactivados
    content = re.sub(r'USE_SESSION_FILTER = True', 'USE_SESSION_FILTER = False', content)
    content = re.sub(r'USE_MIN_SL_FILTER = True', 'USE_MIN_SL_FILTER = False', content)
    content = re.sub(r'USE_ATR_FILTER = True', 'USE_ATR_FILTER = False', content)
    
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    try:
        result = subprocess.run(['python', template_path], capture_output=True, text=True, timeout=180)
        output = result.stdout + result.stderr
        return parse_metrics(output)
    finally:
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(original)


def parse_metrics(output):
    """Extrae métricas del output"""
    metrics = {'pf': 0, 'dd': 100, 'trades': 0, 'wr': 0, 'pnl': 0}
    
    pf_match = re.search(r'Profit Factor:\s*([\d.]+)', output)
    if pf_match:
        metrics['pf'] = float(pf_match.group(1))
    
    dd_match = re.search(r'Max Drawdown:\s*([\d.]+)%', output)
    if dd_match:
        metrics['dd'] = float(dd_match.group(1))
    
    trades_match = re.search(r'Total Trades:\s*(\d+)', output)
    if trades_match:
        metrics['trades'] = int(trades_match.group(1))
    
    wr_match = re.search(r'Win Rate:\s*([\d.]+)%', output)
    if wr_match:
        metrics['wr'] = float(wr_match.group(1))
    
    pnl_match = re.search(r'Net P&L:\s*\$?([-\d,.]+)', output)
    if pnl_match:
        metrics['pnl'] = float(pnl_match.group(1).replace(',', ''))
    
    return metrics


def fase_1_emas():
    """Fase 1: Optimizar EMAs"""
    print("\n" + "=" * 70)
    print("FASE 1: OPTIMIZACIÓN DE EMAs")
    print("=" * 70)
    
    # Combinaciones basadas en resultados anteriores (sin EMA 144)
    ema_combos = [
        (9, 18, 36, 72, 100),    # Ganadora anterior ajustada
        (10, 20, 40, 80, 120),   # Progresión x2
        (7, 14, 28, 56, 100),    # Rápidas
        (8, 16, 32, 64, 100),    # Geométrica
        (5, 10, 20, 40, 80),     # Muy rápidas
        (12, 24, 48, 96, 120),   # Más lentas
    ]
    
    results = []
    for emas in ema_combos:
        print(f"  EMAs {emas}...", end=" ", flush=True)
        m = modify_and_run({'emas': emas})
        results.append({'emas': emas, **m})
        status = "✓" if m['pf'] > 0.9 else "✗"
        print(f"{status} PF={m['pf']:.2f} | {m['trades']} trades | DD={m['dd']:.1f}%")
    
    results.sort(key=lambda x: x['pf'], reverse=True)
    winner = results[0]
    print(f"\n  → GANADOR: EMAs {winner['emas']} (PF={winner['pf']:.2f})")
    return winner['emas'], results


def fase_2_cci(best_emas):
    """Fase 2: Optimizar CCI"""
    print("\n" + "=" * 70)
    print("FASE 2: OPTIMIZACIÓN DE CCI")
    print("=" * 70)
    
    cci_combos = [
        (14, 50), (14, 70), (14, 100),
        (20, 50), (20, 70), (20, 100), (20, 120),
        (25, 70), (25, 100),
    ]
    
    results = []
    for cci_p, cci_t in cci_combos:
        print(f"  CCI({cci_p}, {cci_t})...", end=" ", flush=True)
        m = modify_and_run({'emas': best_emas, 'cci_period': cci_p, 'cci_threshold': cci_t})
        results.append({'cci_period': cci_p, 'cci_threshold': cci_t, **m})
        status = "✓" if m['pf'] > 0.9 else "✗"
        print(f"{status} PF={m['pf']:.2f} | {m['trades']} trades")
    
    results.sort(key=lambda x: x['pf'], reverse=True)
    winner = results[0]
    print(f"\n  → GANADOR: CCI({winner['cci_period']}, {winner['cci_threshold']}) (PF={winner['pf']:.2f})")
    return (winner['cci_period'], winner['cci_threshold']), results


def fase_3_sltp(best_emas, best_cci):
    """Fase 3: Optimizar SL/TP"""
    print("\n" + "=" * 70)
    print("FASE 3: OPTIMIZACIÓN DE SL/TP")
    print("=" * 70)
    
    sltp_combos = [
        (2.0, 8.0),   # 1:4
        (2.0, 10.0),  # 1:5
        (2.5, 10.0),  # 1:4
        (2.5, 12.5),  # 1:5
        (3.0, 12.0),  # 1:4
        (3.0, 15.0),  # 1:5
        (3.5, 14.0),  # 1:4
        (3.5, 17.5),  # 1:5
    ]
    
    results = []
    for sl, tp in sltp_combos:
        ratio = tp / sl
        print(f"  SL={sl}x TP={tp}x (1:{ratio:.1f})...", end=" ", flush=True)
        m = modify_and_run({
            'emas': best_emas, 
            'cci_period': best_cci[0], 
            'cci_threshold': best_cci[1],
            'sl_mult': sl,
            'tp_mult': tp
        })
        results.append({'sl_mult': sl, 'tp_mult': tp, 'ratio': ratio, **m})
        status = "✓" if m['pf'] > 0.9 else "✗"
        print(f"{status} PF={m['pf']:.2f} | {m['trades']} trades | DD={m['dd']:.1f}%")
    
    results.sort(key=lambda x: x['pf'], reverse=True)
    winner = results[0]
    print(f"\n  → GANADOR: SL={winner['sl_mult']}x TP={winner['tp_mult']}x (PF={winner['pf']:.2f})")
    return (winner['sl_mult'], winner['tp_mult']), results


def fase_4_breakout(best_emas, best_cci, best_sltp):
    """Fase 4: Optimizar Breakout offset y ventana"""
    print("\n" + "=" * 70)
    print("FASE 4: OPTIMIZACIÓN DE BREAKOUT WINDOW")
    print("=" * 70)
    
    # Combinaciones de offset (pips) y ventana (candles)
    breakout_combos = [
        (0, 3), (0, 5), (0, 7),      # Sin offset
        (3, 3), (3, 5), (3, 7),      # 3 pips
        (5, 3), (5, 5), (5, 7),      # 5 pips
        (7, 5), (7, 7),              # 7 pips
        (10, 5), (10, 7),            # 10 pips
    ]
    
    results = []
    for offset, candles in breakout_combos:
        print(f"  Offset={offset}pips, Window={candles}bars...", end=" ", flush=True)
        m = modify_and_run({
            'emas': best_emas, 
            'cci_period': best_cci[0], 
            'cci_threshold': best_cci[1],
            'sl_mult': best_sltp[0],
            'tp_mult': best_sltp[1],
            'breakout_offset': offset,
            'breakout_candles': candles
        })
        results.append({'offset': offset, 'candles': candles, **m})
        status = "✓" if m['pf'] > 0.9 else "✗"
        print(f"{status} PF={m['pf']:.2f} | {m['trades']} trades | DD={m['dd']:.1f}%")
    
    results.sort(key=lambda x: x['pf'], reverse=True)
    winner = results[0]
    print(f"\n  → GANADOR: Offset={winner['offset']}pips, Window={winner['candles']}bars (PF={winner['pf']:.2f})")
    return (winner['offset'], winner['candles']), results


def main():
    print("=" * 70)
    print("KOI STRATEGY - OPTIMIZACIÓN COMPLETA CON BREAKOUT WINDOW")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("SIN FILTROS - Optimización de parámetros base")
    
    # FASE 1: EMAs
    best_emas, emas_results = fase_1_emas()
    
    # FASE 2: CCI
    best_cci, cci_results = fase_2_cci(best_emas)
    
    # FASE 3: SL/TP
    best_sltp, sltp_results = fase_3_sltp(best_emas, best_cci)
    
    # FASE 4: Breakout
    best_breakout, breakout_results = fase_4_breakout(best_emas, best_cci, best_sltp)
    
    # RESUMEN FINAL
    print("\n" + "=" * 70)
    print("RESUMEN: PARÁMETROS ÓPTIMOS")
    print("=" * 70)
    print(f"EMAs: {best_emas}")
    print(f"CCI: Period={best_cci[0]}, Threshold={best_cci[1]}")
    print(f"SL/TP: {best_sltp[0]}x / {best_sltp[1]}x (ratio 1:{best_sltp[1]/best_sltp[0]:.1f})")
    print(f"Breakout: Offset={best_breakout[0]}pips, Window={best_breakout[1]}bars")
    
    # Ejecutar final con todos los parámetros
    print("\n" + "=" * 70)
    print("TEST FINAL CON PARÁMETROS ÓPTIMOS")
    print("=" * 70)
    
    final = modify_and_run({
        'emas': best_emas, 
        'cci_period': best_cci[0], 
        'cci_threshold': best_cci[1],
        'sl_mult': best_sltp[0],
        'tp_mult': best_sltp[1],
        'breakout_offset': best_breakout[0],
        'breakout_candles': best_breakout[1]
    })
    
    print(f"PF: {final['pf']:.2f}")
    print(f"Win Rate: {final['wr']:.1f}%")
    print(f"Max DD: {final['dd']:.1f}%")
    print(f"Trades: {final['trades']}")
    print(f"Net P&L: ${final['pnl']:,.0f}")
    
    # Guardar resultados
    all_results = {
        'best_params': {
            'emas': best_emas,
            'cci': best_cci,
            'sltp': best_sltp,
            'breakout': best_breakout
        },
        'final_metrics': final,
        'phase_results': {
            'emas': emas_results,
            'cci': cci_results,
            'sltp': sltp_results,
            'breakout': breakout_results
        }
    }
    
    with open('koi_optimization_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n✓ Resultados guardados en koi_optimization_results.json")
    print("\n>>> PRÓXIMO PASO: Ejecutar análisis de filtros sobre el log generado")


if __name__ == "__main__":
    main()
