"""
Analyze ERIS trade report to find optimal parameter ranges.
Extracts patterns from WIN vs LOSS trades.
"""
import re
from collections import defaultdict
from datetime import datetime

def parse_trade_report(filepath):
    """Parse the trade report and extract all trades with their data."""
    trades = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by ENTRY markers
    entries = re.split(r'ENTRY #(\d+)', content)
    
    for i in range(1, len(entries), 2):
        if i+1 >= len(entries):
            break
            
        trade_num = int(entries[i])
        trade_block = entries[i+1]
        
        trade = {'num': trade_num}
        
        # Extract entry data
        time_match = re.search(r'Time: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', trade_block)
        if time_match:
            trade['entry_time'] = datetime.strptime(time_match.group(1), '%Y-%m-%d %H:%M:%S')
            trade['hour'] = trade['entry_time'].hour
            trade['year'] = trade['entry_time'].year
        
        entry_price_match = re.search(r'Entry Price: ([\d.]+)', trade_block)
        if entry_price_match:
            trade['entry_price'] = float(entry_price_match.group(1))
        
        atr_match = re.search(r'ATR at Entry: ([\d.]+)', trade_block)
        if not atr_match:
            atr_match = re.search(r'Entry ATR: ([\d.]+)', trade_block)
        if not atr_match:
            atr_match = re.search(r'ATR: ([\d.]+)', trade_block)
        if atr_match:
            trade['atr'] = float(atr_match.group(1))
        
        # Z-Score - try multiple formats
        zscore_match = re.search(r'Z-Score at Entry: ([-\d.]+)', trade_block)
        if not zscore_match:
            zscore_match = re.search(r'Entry Z-Score: ([-\d.]+)', trade_block)
        if not zscore_match:
            zscore_match = re.search(r'Z-Score: ([-\d.]+)', trade_block)
        if zscore_match:
            trade['zscore'] = float(zscore_match.group(1))
        
        # Extract exit data
        result_match = re.search(r'Result: (WIN|LOSS)', trade_block)
        if result_match:
            trade['result'] = result_match.group(1)
        else:
            exit_reason_match = re.search(r'Exit Reason: (\w+)', trade_block)
            if exit_reason_match:
                trade['exit_reason'] = exit_reason_match.group(1)
                trade['result'] = 'WIN' if trade['exit_reason'] == 'TAKE_PROFIT' else 'LOSS'
        
        pnl_match = re.search(r'P&L: ([-\d.]+)', trade_block)
        if pnl_match:
            trade['pnl'] = float(pnl_match.group(1))
        
        if 'atr' in trade and 'result' in trade:
            trades.append(trade)
    
    return trades


def analyze_by_atr(trades):
    """Analyze win rate by ATR ranges - auto-detect ranges."""
    print("\n" + "="*80)
    print("ANALYSIS BY ATR RANGE")
    print("="*80)
    
    atr_trades = [t for t in trades if 'atr' in t]
    if not atr_trades:
        print("No ATR data found")
        return
    
    # Get ATR percentiles to create dynamic ranges
    atrs = sorted([t['atr'] for t in atr_trades])
    p10 = atrs[int(len(atrs)*0.1)]
    p25 = atrs[int(len(atrs)*0.25)]
    p50 = atrs[int(len(atrs)*0.5)]
    p75 = atrs[int(len(atrs)*0.75)]
    p90 = atrs[int(len(atrs)*0.9)]
    
    # Define ranges based on percentiles
    ranges = [
        (0, p10, f"0-{p10:.3f} (P0-10)"),
        (p10, p25, f"{p10:.3f}-{p25:.3f} (P10-25)"),
        (p25, p50, f"{p25:.3f}-{p50:.3f} (P25-50)"),
        (p50, p75, f"{p50:.3f}-{p75:.3f} (P50-75)"),
        (p75, p90, f"{p75:.3f}-{p90:.3f} (P75-90)"),
        (p90, 999, f">{p90:.3f} (P90+)"),
    ]
    
    results = []
    for min_atr, max_atr, label in ranges:
        filtered = [t for t in atr_trades if min_atr <= t['atr'] < max_atr]
        if filtered:
            wins = sum(1 for t in filtered if t['result'] == 'WIN')
            losses = len(filtered) - wins
            total = len(filtered)
            win_rate = wins / total * 100
            total_pnl = sum(t['pnl'] for t in filtered)
            gross_win = sum(t['pnl'] for t in filtered if t['result'] == 'WIN')
            gross_loss = sum(abs(t['pnl']) for t in filtered if t['result'] == 'LOSS')
            pf = gross_win / gross_loss if gross_loss > 0 else 0
            results.append((label, total, wins, win_rate, total_pnl, pf))
    
    print(f"\n{'ATR Range':<30} {'Trades':>7} {'Wins':>6} {'WR%':>7} {'Net PnL':>12} {'PF':>6}  Status")
    print("-" * 85)
    for label, total, wins, win_rate, total_pnl, pf in results:
        status = "*** EXCELENTE" if pf >= 1.3 else "++ Buena" if pf >= 1.15 else "X EVITAR" if pf < 1.0 else ""
        print(f"{label:<30} {total:>7} {wins:>6} {win_rate:>6.1f}% {total_pnl:>11.0f} {pf:>6.2f}  {status}")


def analyze_by_hour(trades):
    """Analyze win rate by entry hour."""
    print("\n" + "="*80)
    print("ANALYSIS BY ENTRY HOUR (UTC)")
    print("="*80)
    
    by_hour = defaultdict(list)
    for t in trades:
        if 'hour' in t:
            by_hour[t['hour']].append(t)
    
    results = []
    for hour in sorted(by_hour.keys()):
        filtered = by_hour[hour]
        wins = sum(1 for t in filtered if t['result'] == 'WIN')
        total = len(filtered)
        win_rate = wins / total * 100
        total_pnl = sum(t['pnl'] for t in filtered)
        gross_win = sum(t['pnl'] for t in filtered if t['result'] == 'WIN')
        gross_loss = sum(abs(t['pnl']) for t in filtered if t['result'] == 'LOSS')
        pf = gross_win / gross_loss if gross_loss > 0 else 0
        results.append((hour, total, wins, win_rate, total_pnl, pf))
    
    print(f"\n{'Hour':>6} {'Trades':>7} {'Wins':>6} {'WR%':>7} {'Net PnL':>12} {'PF':>6}  Status")
    print("-" * 65)
    for hour, total, wins, win_rate, total_pnl, pf in results:
        status = "*** EXCELENTE" if pf >= 1.3 else "++ Buena" if pf >= 1.15 else "X EVITAR" if pf < 1.0 else ""
        print(f"{hour:>6} {total:>7} {wins:>6} {win_rate:>6.1f}% {total_pnl:>11.0f} {pf:>6.2f}  {status}")
    
    # Best and worst hours by PF
    best_hours = sorted(results, key=lambda x: x[5], reverse=True)[:5]
    worst_hours = sorted(results, key=lambda x: x[5])[:5]
    
    print("\n--- BEST HOURS (by Profit Factor) ---")
    for hour, total, wins, win_rate, total_pnl, pf in best_hours:
        print(f"  Hour {hour:02d}:00 - Trades: {total}, WR: {win_rate:.1f}%, PF: {pf:.2f}, PnL: ${total_pnl:,.0f}")
    
    print("\n--- WORST HOURS (by Profit Factor) ---")
    for hour, total, wins, win_rate, total_pnl, pf in worst_hours:
        print(f"  Hour {hour:02d}:00 - Trades: {total}, WR: {win_rate:.1f}%, PF: {pf:.2f}, PnL: ${total_pnl:,.0f}")


def analyze_by_zscore(trades):
    """Analyze win rate by Z-Score ranges."""
    print("\n" + "="*80)
    print("ANALYSIS BY Z-SCORE RANGE")
    print("="*80)
    
    zscore_trades = [t for t in trades if 'zscore' in t]
    if not zscore_trades:
        print("No Z-Score data found")
        return
    
    # Define Z-Score ranges
    ranges = [
        (-99, -2.0, "< -2.0 (Extremely Oversold)"),
        (-2.0, -1.5, "-2.0 to -1.5 (Very Oversold)"),
        (-1.5, -1.0, "-1.5 to -1.0 (Oversold)"),
        (-1.0, -0.5, "-1.0 to -0.5 (Slightly Oversold)"),
        (-0.5, 0.0, "-0.5 to 0.0 (Near Mean)"),
        (0.0, 0.5, "0.0 to 0.5 (Near Mean)"),
        (0.5, 1.0, "0.5 to 1.0 (Slightly Overbought)"),
        (1.0, 1.5, "1.0 to 1.5 (Overbought)"),
        (1.5, 2.0, "1.5 to 2.0 (Very Overbought)"),
        (2.0, 99, "> 2.0 (Extremely Overbought)"),
    ]
    
    results = []
    for min_z, max_z, label in ranges:
        filtered = [t for t in zscore_trades if min_z <= t['zscore'] < max_z]
        if filtered and len(filtered) >= 50:  # Min 50 trades for significance
            wins = sum(1 for t in filtered if t['result'] == 'WIN')
            total = len(filtered)
            win_rate = wins / total * 100
            total_pnl = sum(t['pnl'] for t in filtered)
            gross_win = sum(t['pnl'] for t in filtered if t['result'] == 'WIN')
            gross_loss = sum(abs(t['pnl']) for t in filtered if t['result'] == 'LOSS')
            pf = gross_win / gross_loss if gross_loss > 0 else 0
            results.append((label, total, wins, win_rate, total_pnl, pf, min_z, max_z))
    
    print(f"\n{'Z-Score Range':<32} {'Trades':>7} {'Wins':>6} {'WR%':>7} {'Net PnL':>12} {'PF':>6}  Status")
    print("-" * 90)
    for label, total, wins, win_rate, total_pnl, pf, _, _ in results:
        status = "*** EXCELENTE" if pf >= 1.3 else "++ Buena" if pf >= 1.15 else "X EVITAR" if pf < 1.0 else ""
        print(f"{label:<32} {total:>7} {wins:>6} {win_rate:>6.1f}% {total_pnl:>11.0f} {pf:>6.2f}  {status}")
    
    # Summary
    print("\n--- Z-SCORE RECOMMENDATIONS ---")
    good_zones = [r for r in results if r[5] >= 1.15]
    bad_zones = [r for r in results if r[5] < 1.0]
    
    if good_zones:
        print("PROFITABLE Z-Score zones (PF >= 1.15):")
        for label, total, wins, win_rate, total_pnl, pf, min_z, max_z in good_zones:
            print(f"  {label}: PF={pf:.2f}, Trades={total}, PnL=${total_pnl:,.0f}")
    
    if bad_zones:
        print("\nUNPROFITABLE Z-Score zones (PF < 1.0):")
        for label, total, wins, win_rate, total_pnl, pf, min_z, max_z in bad_zones:
            print(f"  {label}: PF={pf:.2f}, Trades={total}, PnL=${total_pnl:,.0f}")


def analyze_combined(trades):
    """Find optimal ATR + Hour combinations."""
    print("\n" + "="*60)
    print("OPTIMAL COMBINATIONS (ATR + Hour)")
    print("="*60)
    
    # Filter by best ATR ranges first
    good_atr_trades = [t for t in trades if 0.00015 <= t['atr'] <= 0.00035]
    
    if not good_atr_trades:
        print("No trades in good ATR range")
        return
    
    by_hour = defaultdict(list)
    for t in good_atr_trades:
        if 'hour' in t:
            by_hour[t['hour']].append(t)
    
    results = []
    for hour in sorted(by_hour.keys()):
        filtered = by_hour[hour]
        if len(filtered) >= 5:  # Minimum sample size
            wins = sum(1 for t in filtered if t['result'] == 'WIN')
            total = len(filtered)
            win_rate = wins / total * 100
            total_pnl = sum(t['pnl'] for t in filtered)
            avg_pnl = total_pnl / total
            results.append((hour, total, wins, win_rate, total_pnl, avg_pnl))
    
    print(f"\nWith ATR filter 0.00015-0.00035:")
    print(f"{'Hour':>6} {'Trades':>7} {'Wins':>6} {'WinRate':>8} {'Total PnL':>12} {'Avg PnL':>10}")
    print("-" * 60)
    for hour, total, wins, win_rate, total_pnl, avg_pnl in sorted(results, key=lambda x: x[5], reverse=True):
        wr_indicator = "***" if win_rate >= 50 else "**" if win_rate >= 45 else "*" if win_rate >= 40 else ""
        print(f"{hour:>6} {total:>7} {wins:>6} {win_rate:>7.1f}% {total_pnl:>11.2f} {avg_pnl:>9.2f} {wr_indicator}")


def summarize_recommendations(trades):
    """Provide actionable recommendations."""
    print("\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)
    
    # Calculate overall stats
    total = len(trades)
    wins = sum(1 for t in trades if t['result'] == 'WIN')
    total_pnl = sum(t['pnl'] for t in trades)
    
    print(f"\nCurrent: {total} trades, {wins/total*100:.1f}% WR, PnL: {total_pnl:.2f}")
    
    # Test ATR filter
    atr_filtered = [t for t in trades if 0.00015 <= t['atr'] <= 0.00035]
    if atr_filtered:
        wins_f = sum(1 for t in atr_filtered if t['result'] == 'WIN')
        pnl_f = sum(t['pnl'] for t in atr_filtered)
        print(f"\nWith ATR filter (0.00015-0.00035):")
        print(f"  {len(atr_filtered)} trades, {wins_f/len(atr_filtered)*100:.1f}% WR, PnL: {pnl_f:.2f}")
    
    # Find profitable hours
    by_hour = defaultdict(list)
    for t in trades:
        if 'hour' in t:
            by_hour[t['hour']].append(t)
    
    profitable_hours = []
    for hour, hour_trades in by_hour.items():
        avg_pnl = sum(t['pnl'] for t in hour_trades) / len(hour_trades)
        if avg_pnl > 0:
            profitable_hours.append(hour)
    
    if profitable_hours:
        hour_filtered = [t for t in trades if t.get('hour') in profitable_hours]
        wins_h = sum(1 for t in hour_filtered if t['result'] == 'WIN')
        pnl_h = sum(t['pnl'] for t in hour_filtered)
        print(f"\nWith profitable hours only ({sorted(profitable_hours)}):")
        print(f"  {len(hour_filtered)} trades, {wins_h/len(hour_filtered)*100:.1f}% WR, PnL: {pnl_h:.2f}")
    
    # Combined filter
    combined = [t for t in trades if 0.00015 <= t['atr'] <= 0.00035 and t.get('hour') in profitable_hours]
    if combined and len(combined) >= 10:
        wins_c = sum(1 for t in combined if t['result'] == 'WIN')
        pnl_c = sum(t['pnl'] for t in combined)
        print(f"\nCOMBINED (ATR + Hours):")
        print(f"  {len(combined)} trades, {wins_c/len(combined)*100:.1f}% WR, PnL: {pnl_c:.2f}")


if __name__ == '__main__':
    import sys
    from pathlib import Path
    
    # Find most recent report - try USDJPY first, then USDCHF
    report_dir = Path(__file__).parent / "temp_reports"
    
    # Try USDJPY first
    reports = list(report_dir.glob("ERIS_USDJPY_*.txt"))
    if not reports:
        reports = list(report_dir.glob("ERIS_USDCHF_*.txt"))
    if not reports:
        reports = list(report_dir.glob("ERIS_*.txt"))
    
    if not reports:
        print("No report files found")
        sys.exit(1)
    
    latest_report = max(reports, key=lambda p: p.stat().st_mtime)
    print(f"Analyzing: {latest_report.name}")
    
    trades = parse_trade_report(latest_report)
    print(f"Parsed {len(trades)} trades")
    
    if trades:
        analyze_by_atr(trades)
        analyze_by_hour(trades)
        analyze_by_zscore(trades)
        analyze_combined(trades)
        summarize_recommendations(trades)
    else:
        print("No trades parsed - check file format")
