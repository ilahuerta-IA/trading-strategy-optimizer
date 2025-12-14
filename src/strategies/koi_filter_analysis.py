"""
KOI - ANÁLISIS DE FILTROS PARA PARÁMETROS ÓPTIMOS
=================================================
Analiza el log de trades para encontrar filtros específicos
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime

def parse_txt_report(txt_path):
    """Parsea el archivo .txt de trades"""
    trades = []
    current_entry = {}
    
    with open(txt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.strip()
        
        if line.startswith("ENTRY #"):
            current_entry = {'trade_num': int(line.split('#')[1])}
        elif line.startswith("Time:") and 'entry_time' not in current_entry:
            current_entry['entry_time'] = line.replace("Time:", "").strip()
        elif line.startswith("Entry Price:"):
            current_entry['entry_price'] = float(line.replace("Entry Price:", "").strip())
        elif line.startswith("SL Pips:"):
            current_entry['sl_pips'] = float(line.replace("SL Pips:", "").strip())
        elif line.startswith("ATR:"):
            current_entry['atr_value'] = float(line.replace("ATR:", "").strip())
        elif line.startswith("CCI:"):
            current_entry['cci_value'] = float(line.replace("CCI:", "").strip())
        elif line.startswith("Exit Reason:"):
            current_entry['exit_reason'] = line.replace("Exit Reason:", "").strip()
        elif line.startswith("P&L:"):
            pnl_str = line.replace("P&L:", "").replace("$", "").strip()
            current_entry['pnl'] = float(pnl_str)
        elif line.startswith("Duration:"):
            match = re.search(r'(\d+) bars', line)
            if match:
                current_entry['duration_bars'] = int(match.group(1))
        elif line.startswith("=") and 'pnl' in current_entry:
            if len(current_entry) > 3:
                trades.append(current_entry)
            current_entry = {}
    
    return pd.DataFrame(trades)


def analyze_filters(df):
    """Analiza el DataFrame para encontrar filtros óptimos"""
    
    print(f"\nTotal trades: {len(df)}")
    
    # Extraer hora
    df['hour'] = pd.to_datetime(df['entry_time']).dt.hour
    
    # Métricas base
    wins = df[df['pnl'] > 0]
    losses = df[df['pnl'] <= 0]
    gross_profit = wins['pnl'].sum() if len(wins) > 0 else 0
    gross_loss = abs(losses['pnl'].sum()) if len(losses) > 0 else 0.01
    base_pf = gross_profit / gross_loss
    base_wr = len(wins) / len(df) * 100
    
    print(f"Base: WR={base_wr:.1f}%, PF={base_pf:.2f}")
    
    # ========== ANÁLISIS POR HORA ==========
    print("\n" + "=" * 60)
    print("ANÁLISIS POR HORA")
    print("=" * 60)
    
    for hour in range(24):
        h_df = df[df['hour'] == hour]
        if len(h_df) >= 5:
            w = h_df[h_df['pnl'] > 0]
            l = h_df[h_df['pnl'] <= 0]
            p = w['pnl'].sum() if len(w) > 0 else 0
            lo = abs(l['pnl'].sum()) if len(l) > 0 else 0.01
            pf = p / lo
            print(f"  {hour:02d}:00 - {len(h_df):3d} trades, PF={pf:.2f}")
    
    # Mejores rangos horarios
    print("\nMejores rangos horarios:")
    best_sessions = []
    for start_h in range(0, 20, 2):
        for duration in [4, 6, 8]:
            end_h = (start_h + duration) % 24
            if start_h < end_h:
                mask = (df['hour'] >= start_h) & (df['hour'] < end_h)
            else:
                mask = (df['hour'] >= start_h) | (df['hour'] < end_h)
            sub = df[mask]
            if len(sub) >= 20:
                w = sub[sub['pnl'] > 0]
                l = sub[sub['pnl'] <= 0]
                p = w['pnl'].sum() if len(w) > 0 else 0
                lo = abs(l['pnl'].sum()) if len(l) > 0 else 0.01
                pf = p / lo
                if pf > 1.0:
                    best_sessions.append((start_h, end_h, len(sub), pf))
    
    best_sessions.sort(key=lambda x: x[3], reverse=True)
    for s in best_sessions[:5]:
        print(f"  {s[0]:02d}:00-{s[1]:02d}:00: {s[2]} trades, PF={s[3]:.2f}")
    
    # ========== ANÁLISIS POR SL PIPS ==========
    print("\n" + "=" * 60)
    print("ANÁLISIS POR SL PIPS MÍNIMO")
    print("=" * 60)
    
    for min_sl in [8, 10, 12, 15, 18, 20, 25]:
        sub = df[df['sl_pips'] >= min_sl]
        if len(sub) >= 15:
            w = sub[sub['pnl'] > 0]
            l = sub[sub['pnl'] <= 0]
            p = w['pnl'].sum() if len(w) > 0 else 0
            lo = abs(l['pnl'].sum()) if len(l) > 0 else 0.01
            pf = p / lo
            status = "★" if pf > 1.0 else " "
            print(f"  {status} SL >= {min_sl:2d} pips: {len(sub):3d} trades, PF={pf:.2f}")
    
    # ========== ANÁLISIS POR ATR ==========
    print("\n" + "=" * 60)
    print("ANÁLISIS POR ATR (CUARTILES)")
    print("=" * 60)
    
    q1, q2, q3 = df['atr_value'].quantile([0.25, 0.5, 0.75])
    print(f"  Q1={q1:.5f}, Q2={q2:.5f}, Q3={q3:.5f}")
    
    atr_ranges = [
        (0, q1, "Q1 bajo"),
        (q1, q2, "Q2"),
        (q2, q3, "Q3"),
        (q3, df['atr_value'].max() * 1.1, "Q4 alto"),
    ]
    
    for amin, amax, label in atr_ranges:
        sub = df[(df['atr_value'] >= amin) & (df['atr_value'] < amax)]
        if len(sub) >= 15:
            w = sub[sub['pnl'] > 0]
            l = sub[sub['pnl'] <= 0]
            p = w['pnl'].sum() if len(w) > 0 else 0
            lo = abs(l['pnl'].sum()) if len(l) > 0 else 0.01
            pf = p / lo
            status = "★" if pf > 1.0 else " "
            print(f"  {status} ATR {label}: {len(sub):3d} trades, PF={pf:.2f}")
    
    # ========== ANÁLISIS POR CCI ==========
    print("\n" + "=" * 60)
    print("ANÁLISIS POR CCI")
    print("=" * 60)
    
    cci_ranges = [(100, 120), (120, 150), (150, 200), (200, 300), (300, 1000)]
    for cmin, cmax in cci_ranges:
        sub = df[(df['cci_value'] >= cmin) & (df['cci_value'] < cmax)]
        if len(sub) >= 10:
            w = sub[sub['pnl'] > 0]
            l = sub[sub['pnl'] <= 0]
            p = w['pnl'].sum() if len(w) > 0 else 0
            lo = abs(l['pnl'].sum()) if len(l) > 0 else 0.01
            pf = p / lo
            status = "★" if pf > 1.0 else " "
            print(f"  {status} CCI {cmin}-{cmax}: {len(sub):3d} trades, PF={pf:.2f}")
    
    # ========== COMBINACIONES ==========
    print("\n" + "=" * 60)
    print("TEST DE COMBINACIONES DE FILTROS")
    print("=" * 60)
    
    # Probar mejores combinaciones
    test_combos = [
        # (session_start, session_end, min_sl)
        (6, 12, 15),
        (8, 12, 15),
        (8, 14, 18),
        (6, 14, 12),
        (10, 14, 15),
        (6, 10, 18),
    ]
    
    for start_h, end_h, min_sl in test_combos:
        if start_h < end_h:
            mask = (df['hour'] >= start_h) & (df['hour'] < end_h)
        else:
            mask = (df['hour'] >= start_h) | (df['hour'] < end_h)
        
        sub = df[mask & (df['sl_pips'] >= min_sl)]
        
        if len(sub) >= 10:
            w = sub[sub['pnl'] > 0]
            l = sub[sub['pnl'] <= 0]
            p = w['pnl'].sum() if len(w) > 0 else 0
            lo = abs(l['pnl'].sum()) if len(l) > 0 else 0.01
            pf = p / lo
            wr = len(w) / len(sub) * 100
            status = "★" if pf > 1.0 else " "
            print(f"  {status} {start_h:02d}-{end_h:02d}h + SL>={min_sl}: {len(sub):3d} trades, WR={wr:.1f}%, PF={pf:.2f}")


def main():
    print("=" * 60)
    print("KOI - ANÁLISIS DE FILTROS")
    print("=" * 60)
    print(f"Parámetros óptimos sin filtros:")
    print("  EMAs: (10, 20, 40, 80, 120)")
    print("  CCI: 20/100")
    print("  SL/TP: 3.0x/12.0x")
    print("  Breakout: 5pips offset, 3 bars window")
    
    # Buscar último reporte
    report_dir = Path("temp_reports")
    txt_files = list(report_dir.glob("KOI_*.txt"))
    txt_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not txt_files:
        print("No se encontraron reportes!")
        return
    
    latest = txt_files[0]
    print(f"\nAnalizando: {latest.name}")
    
    df = parse_txt_report(latest)
    
    if df.empty:
        print("No se pudieron parsear trades!")
        return
    
    analyze_filters(df)


if __name__ == "__main__":
    main()
