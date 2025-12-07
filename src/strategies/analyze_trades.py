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
        
        entry_price_match = re.search(r'Entry Price: ([\d.]+)', trade_block)
        if entry_price_match:
            trade['entry_price'] = float(entry_price_match.group(1))
        
        atr_match = re.search(r'ATR: ([\d.]+)', trade_block)
        if atr_match:
            trade['atr'] = float(atr_match.group(1))
        
        # Extract exit data
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
    """Analyze win rate by ATR ranges."""
    print("\n" + "="*60)
    print("ANALYSIS BY ATR RANGE")
    print("="*60)
    
    # Define ATR ranges
    ranges = [
        (0.0001, 0.00015, "0.0001-0.00015"),
        (0.00015, 0.0002, "0.00015-0.0002"),
        (0.0002, 0.00025, "0.0002-0.00025"),
        (0.00025, 0.0003, "0.00025-0.0003"),
        (0.0003, 0.00035, "0.0003-0.00035"),
        (0.00035, 0.0004, "0.00035-0.0004"),
        (0.0004, 0.00045, "0.0004-0.00045"),
        (0.00045, 0.0005, "0.00045-0.0005"),
        (0.0005, 0.001, "0.0005+"),
    ]
    
    results = []
    for min_atr, max_atr, label in ranges:
        filtered = [t for t in trades if min_atr <= t['atr'] < max_atr]
        if filtered:
            wins = sum(1 for t in filtered if t['result'] == 'WIN')
            total = len(filtered)
            win_rate = wins / total * 100
            total_pnl = sum(t['pnl'] for t in filtered)
            avg_pnl = total_pnl / total
            results.append((label, total, wins, win_rate, total_pnl, avg_pnl))
    
    print(f"\n{'ATR Range':<18} {'Trades':>7} {'Wins':>6} {'WinRate':>8} {'Total PnL':>12} {'Avg PnL':>10}")
    print("-" * 70)
    for label, total, wins, win_rate, total_pnl, avg_pnl in results:
        wr_indicator = "***" if win_rate >= 45 else "**" if win_rate >= 40 else "*" if win_rate >= 35 else ""
        print(f"{label:<18} {total:>7} {wins:>6} {win_rate:>7.1f}% {total_pnl:>11.2f} {avg_pnl:>9.2f} {wr_indicator}")


def analyze_by_hour(trades):
    """Analyze win rate by entry hour."""
    print("\n" + "="*60)
    print("ANALYSIS BY ENTRY HOUR (UTC)")
    print("="*60)
    
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
        avg_pnl = total_pnl / total
        results.append((hour, total, wins, win_rate, total_pnl, avg_pnl))
    
    print(f"\n{'Hour':>6} {'Trades':>7} {'Wins':>6} {'WinRate':>8} {'Total PnL':>12} {'Avg PnL':>10}")
    print("-" * 60)
    for hour, total, wins, win_rate, total_pnl, avg_pnl in results:
        wr_indicator = "***" if win_rate >= 50 else "**" if win_rate >= 45 else "*" if win_rate >= 40 else ""
        pnl_indicator = "+++" if avg_pnl >= 50 else "++" if avg_pnl >= 25 else "+" if avg_pnl >= 0 else ""
        print(f"{hour:>6} {total:>7} {wins:>6} {win_rate:>7.1f}% {total_pnl:>11.2f} {avg_pnl:>9.2f} {wr_indicator} {pnl_indicator}")
    
    # Best and worst hours
    best_hours = sorted(results, key=lambda x: x[5], reverse=True)[:5]
    worst_hours = sorted(results, key=lambda x: x[5])[:5]
    
    print("\n--- BEST HOURS (by Avg PnL) ---")
    for hour, total, wins, win_rate, total_pnl, avg_pnl in best_hours:
        print(f"  Hour {hour:02d}:00 - Trades: {total}, WR: {win_rate:.1f}%, Avg PnL: {avg_pnl:.2f}")
    
    print("\n--- WORST HOURS (by Avg PnL) ---")
    for hour, total, wins, win_rate, total_pnl, avg_pnl in worst_hours:
        print(f"  Hour {hour:02d}:00 - Trades: {total}, WR: {win_rate:.1f}%, Avg PnL: {avg_pnl:.2f}")


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
    
    # Find most recent report
    report_dir = Path(__file__).parent / "temp_reports"
    reports = list(report_dir.glob("ERIS_USDCHF_*.txt"))
    
    if not reports:
        print("No report files found")
        sys.exit(1)
    
    latest_report = max(reports, key=lambda p: p.stat().st_mtime)
    print(f"Analyzing: {latest_report.name}")
    
    trades = parse_trade_report(latest_report)
    print(f"Parsed {len(trades)} trades")
    
    analyze_by_atr(trades)
    analyze_by_hour(trades)
    analyze_combined(trades)
    summarize_recommendations(trades)
