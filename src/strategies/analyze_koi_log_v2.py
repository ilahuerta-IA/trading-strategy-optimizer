"""KOI Trade Log Analyzer v2
============================
Deep analysis of trade logs for fine-tuning filters.
Target: PF > 1.5, Trades > 120

USAGE:
    python analyze_koi_log_v2.py [log_file.txt]
"""

import sys
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime


def parse_trade_log(filepath):
    """Parse trade log file and extract all trade data."""
    trades = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match entry blocks
    entry_pattern = r'ENTRY #(\d+)\nTime: ([\d\-: ]+)\nEntry Price: ([\d.]+)\nStop Loss: ([\d.]+)\nTake Profit: ([\d.]+)\nSL Pips: ([\d.]+)\nATR: ([\d.]+)\nCCI: ([\d.\-]+)'
    
    # Pattern to match exit blocks  
    exit_pattern = r'EXIT #(\d+)\nTime: ([\d\-: ]+)\nExit Reason: (\w+)\nP&L: \$([\d.\-,]+)'
    
    entries = re.findall(entry_pattern, content)
    exits = re.findall(exit_pattern, content)
    
    for entry, exit_data in zip(entries, exits):
        trade_num, entry_time, entry_price, sl, tp, sl_pips, atr, cci = entry
        exit_num, exit_time, exit_reason, pnl = exit_data
        
        entry_dt = datetime.strptime(entry_time, '%Y-%m-%d %H:%M:%S')
        pnl_clean = float(pnl.replace(',', ''))
        
        trades.append({
            'num': int(trade_num),
            'entry_time': entry_dt,
            'hour': entry_dt.hour,
            'weekday': entry_dt.weekday(),  # 0=Monday
            'year': entry_dt.year,
            'entry_price': float(entry_price),
            'sl': float(sl),
            'tp': float(tp),
            'sl_pips': float(sl_pips),
            'atr': float(atr),
            'cci': float(cci),
            'exit_reason': exit_reason,
            'pnl': pnl_clean,
            'win': pnl_clean > 0,
        })
    
    return trades


def analyze_by_hour(trades):
    """Analyze performance by entry hour."""
    hourly = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0.0, 'gp': 0.0, 'gl': 0.0})
    
    for t in trades:
        h = t['hour']
        hourly[h]['trades'] += 1
        hourly[h]['pnl'] += t['pnl']
        if t['win']:
            hourly[h]['wins'] += 1
            hourly[h]['gp'] += t['pnl']
        else:
            hourly[h]['gl'] += abs(t['pnl'])
    
    print("\n" + "=" * 85)
    print("ANALYSIS BY HOUR (Server Time UTC)")
    print("=" * 85)
    print(f"{'Hour':<6} {'Trades':>7} {'Wins':>6} {'WR%':>7} {'PF':>6} {'PnL':>12} {'Status'}")
    print("-" * 85)
    
    profitable_hours = []
    losing_hours = []
    
    for hour in range(24):
        if hourly[hour]['trades'] == 0:
            continue
        data = hourly[hour]
        wr = data['wins'] / data['trades'] * 100 if data['trades'] > 0 else 0
        pf = data['gp'] / data['gl'] if data['gl'] > 0 else 0
        status = "✓ GOOD" if data['pnl'] > 0 else "✗ BAD"
        
        if data['pnl'] > 0:
            profitable_hours.append(hour)
        else:
            losing_hours.append(hour)
        
        print(f"{hour:02d}:00  {data['trades']:>7} {data['wins']:>6} {wr:>6.1f}% {pf:>6.2f} ${data['pnl']:>10,.0f} {status}")
    
    print("-" * 85)
    print(f"\n✓ PROFITABLE HOURS: {profitable_hours}")
    print(f"✗ LOSING HOURS: {losing_hours}")
    
    return profitable_hours, losing_hours, hourly


def analyze_by_weekday(trades):
    """Analyze performance by weekday."""
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    daily = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0.0, 'gp': 0.0, 'gl': 0.0})
    
    for t in trades:
        d = t['weekday']
        daily[d]['trades'] += 1
        daily[d]['pnl'] += t['pnl']
        if t['win']:
            daily[d]['wins'] += 1
            daily[d]['gp'] += t['pnl']
        else:
            daily[d]['gl'] += abs(t['pnl'])
    
    print("\n" + "=" * 85)
    print("ANALYSIS BY WEEKDAY")
    print("=" * 85)
    print(f"{'Day':<6} {'Trades':>7} {'Wins':>6} {'WR%':>7} {'PF':>6} {'PnL':>12} {'Status'}")
    print("-" * 85)
    
    for day in range(7):
        if daily[day]['trades'] > 0:
            data = daily[day]
            wr = data['wins'] / data['trades'] * 100
            pf = data['gp'] / data['gl'] if data['gl'] > 0 else 0
            status = "✓ GOOD" if data['pnl'] > 0 else "✗ BAD"
            print(f"{days[day]:<6} {data['trades']:>7} {data['wins']:>6} {wr:>6.1f}% {pf:>6.2f} ${data['pnl']:>10,.0f} {status}")


def analyze_by_sl_pips(trades):
    """Analyze performance by SL pips ranges."""
    ranges = [
        (8, 9), (9, 10), (10, 11), (11, 12), (12, 13), (13, 14)
    ]
    
    print("\n" + "=" * 85)
    print("ANALYSIS BY SL PIPS RANGE")
    print("=" * 85)
    print(f"{'Range':<12} {'Trades':>7} {'Wins':>6} {'WR%':>7} {'PF':>6} {'PnL':>12} {'Status'}")
    print("-" * 85)
    
    best_range = None
    best_pf = 0
    
    for low, high in ranges:
        filtered = [t for t in trades if low <= t['sl_pips'] < high]
        if not filtered:
            continue
        
        wins = [t for t in filtered if t['win']]
        losses = [t for t in filtered if not t['win']]
        gp = sum(t['pnl'] for t in wins)
        gl = abs(sum(t['pnl'] for t in losses))
        pnl = gp - gl
        wr = len(wins) / len(filtered) * 100
        pf = gp / gl if gl > 0 else 0
        status = "✓ GOOD" if pnl > 0 else "✗ BAD"
        
        if pf > best_pf and len(filtered) >= 20:
            best_pf = pf
            best_range = (low, high)
        
        print(f"{low}-{high} pips {len(filtered):>7} {len(wins):>6} {wr:>6.1f}% {pf:>6.2f} ${pnl:>10,.0f} {status}")
    
    if best_range:
        print(f"\nBEST SL RANGE: {best_range[0]}-{best_range[1]} pips (PF: {best_pf:.2f})")
    return best_range


def analyze_by_atr(trades):
    """Analyze performance by ATR ranges."""
    ranges = [
        (0.00050, 0.00055), (0.00055, 0.00060), (0.00060, 0.00065),
        (0.00065, 0.00070), (0.00070, 0.00080), (0.00080, 0.00100)
    ]
    
    print("\n" + "=" * 85)
    print("ANALYSIS BY ATR RANGE")
    print("=" * 85)
    print(f"{'Range':<18} {'Trades':>7} {'Wins':>6} {'WR%':>7} {'PF':>6} {'PnL':>12} {'Status'}")
    print("-" * 85)
    
    best_range = None
    best_pf = 0
    
    for low, high in ranges:
        filtered = [t for t in trades if low <= t['atr'] < high]
        if not filtered:
            continue
        
        wins = [t for t in filtered if t['win']]
        losses = [t for t in filtered if not t['win']]
        gp = sum(t['pnl'] for t in wins)
        gl = abs(sum(t['pnl'] for t in losses))
        pnl = gp - gl
        wr = len(wins) / len(filtered) * 100
        pf = gp / gl if gl > 0 else 0
        status = "✓ GOOD" if pnl > 0 else "✗ BAD"
        
        if pf > best_pf and len(filtered) >= 20:
            best_pf = pf
            best_range = (low, high)
        
        low_pips = int(low * 10000)
        high_pips = int(high * 10000)
        print(f"{low_pips}-{high_pips} pips     {len(filtered):>7} {len(wins):>6} {wr:>6.1f}% {pf:>6.2f} ${pnl:>10,.0f} {status}")
    
    if best_range:
        print(f"\nBEST ATR RANGE: {int(best_range[0]*10000)}-{int(best_range[1]*10000)} pips (PF: {best_pf:.2f})")
    return best_range


def analyze_by_cci(trades):
    """Analyze performance by CCI ranges."""
    ranges = [
        (100, 110), (110, 120), (120, 140), (140, 160), (160, 200), (200, 500)
    ]
    
    print("\n" + "=" * 85)
    print("ANALYSIS BY CCI RANGE")
    print("=" * 85)
    print(f"{'Range':<12} {'Trades':>7} {'Wins':>6} {'WR%':>7} {'PF':>6} {'PnL':>12} {'Status'}")
    print("-" * 85)
    
    best_range = None
    best_pf = 0
    
    for low, high in ranges:
        filtered = [t for t in trades if low <= t['cci'] < high]
        if not filtered:
            continue
        
        wins = [t for t in filtered if t['win']]
        losses = [t for t in filtered if not t['win']]
        gp = sum(t['pnl'] for t in wins)
        gl = abs(sum(t['pnl'] for t in losses))
        pnl = gp - gl
        wr = len(wins) / len(filtered) * 100
        pf = gp / gl if gl > 0 else 0
        status = "✓ GOOD" if pnl > 0 else "✗ BAD"
        
        if pf > best_pf and len(filtered) >= 20:
            best_pf = pf
            best_range = (low, high)
        
        print(f"CCI {low}-{high:<4} {len(filtered):>7} {len(wins):>6} {wr:>6.1f}% {pf:>6.2f} ${pnl:>10,.0f} {status}")
    
    if best_range:
        print(f"\nBEST CCI RANGE: {best_range[0]}+ (PF: {best_pf:.2f})")
    return best_range


def calculate_filtered_stats(trades, filters):
    """Calculate stats after applying filters."""
    filtered = trades
    
    if filters.get('hours'):
        filtered = [t for t in filtered if t['hour'] in filters['hours']]
    
    if filters.get('exclude_hours'):
        filtered = [t for t in filtered if t['hour'] not in filters['exclude_hours']]
    
    if filters.get('sl_min') is not None:
        filtered = [t for t in filtered if t['sl_pips'] >= filters['sl_min']]
    
    if filters.get('sl_max') is not None:
        filtered = [t for t in filtered if t['sl_pips'] <= filters['sl_max']]
    
    if filters.get('atr_min') is not None:
        filtered = [t for t in filtered if t['atr'] >= filters['atr_min']]
    
    if filters.get('atr_max') is not None:
        filtered = [t for t in filtered if t['atr'] <= filters['atr_max']]
    
    if filters.get('cci_min') is not None:
        filtered = [t for t in filtered if t['cci'] >= filters['cci_min']]
    
    if not filtered:
        return None
    
    wins = [t for t in filtered if t['win']]
    losses = [t for t in filtered if not t['win']]
    
    gross_profit = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))
    
    pf = gross_profit / gross_loss if gross_loss > 0 else 0
    wr = len(wins) / len(filtered) * 100
    net = gross_profit - gross_loss
    
    return {
        'trades': len(filtered),
        'wins': len(wins),
        'wr': wr,
        'pf': pf,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'net_pnl': net,
    }


def test_filter_combinations(trades, profitable_hours, losing_hours):
    """Test various filter combinations to find optimal config."""
    print("\n" + "=" * 95)
    print("FILTER COMBINATION TESTING - TARGET: PF > 1.5, Trades > 120")
    print("=" * 95)
    
    suggestions = [
        # Filter name, filter dict
        ("Current (baseline)", {}),
        ("Exclude worst hours (0,1,6,7,12,20)", {'exclude_hours': [0, 1, 6, 7, 12, 20]}),
        ("Profitable hours only", {'hours': profitable_hours}),
        ("Hours 2-5, 8-11, 13-19", {'hours': [2,3,4,5,8,9,10,11,13,14,15,16,17,18,19]}),
        ("Hours 8-18 (Main sessions)", {'hours': list(range(8, 19))}),
        ("Hours 13-22 (NY session)", {'hours': list(range(13, 23))}),
        ("SL 10-12 pips", {'sl_min': 10, 'sl_max': 12}),
        ("SL 11-13 pips", {'sl_min': 11, 'sl_max': 13}),
        ("SL 10-13 pips", {'sl_min': 10, 'sl_max': 13}),
        ("ATR 55-70 pips", {'atr_min': 0.00055, 'atr_max': 0.00070}),
        ("ATR 60-80 pips", {'atr_min': 0.00060, 'atr_max': 0.00080}),
        ("CCI > 110", {'cci_min': 110}),
        ("CCI > 120", {'cci_min': 120}),
        ("CCI > 140", {'cci_min': 140}),
        ("Combo: Excl bad hrs + SL 10-13", {'exclude_hours': [0,1,6,7,12,20], 'sl_min': 10, 'sl_max': 13}),
        ("Combo: Excl bad hrs + CCI>110", {'exclude_hours': [0,1,6,7,12,20], 'cci_min': 110}),
        ("Combo: Hrs 8-18 + SL 10-13", {'hours': list(range(8, 19)), 'sl_min': 10, 'sl_max': 13}),
        ("Combo: Hrs 8-18 + CCI>120", {'hours': list(range(8, 19)), 'cci_min': 120}),
        ("Combo: Prof hrs + SL 10-13", {'hours': profitable_hours, 'sl_min': 10, 'sl_max': 13}),
        ("Combo: Prof hrs + CCI>110", {'hours': profitable_hours, 'cci_min': 110}),
        ("Combo: Prof hrs + CCI>120", {'hours': profitable_hours, 'cci_min': 120}),
        ("Combo: SL 10-13 + CCI>110", {'sl_min': 10, 'sl_max': 13, 'cci_min': 110}),
        ("Combo: SL 10-13 + CCI>120", {'sl_min': 10, 'sl_max': 13, 'cci_min': 120}),
        ("FULL: Prof hrs + SL10-13 + CCI>110", {'hours': profitable_hours, 'sl_min': 10, 'sl_max': 13, 'cci_min': 110}),
    ]
    
    print(f"{'Filter':<40} {'Trades':>7} {'WR%':>6} {'PF':>6} {'PnL':>12} {'Target'}")
    print("-" * 95)
    
    results = []
    
    for name, filters in suggestions:
        result = calculate_filtered_stats(trades, filters)
        if not result:
            continue
        
        target = ""
        if result['trades'] >= 120 and result['pf'] >= 1.5:
            target = "✓✓ IDEAL"
        elif result['trades'] >= 120 and result['pf'] >= 1.3:
            target = "✓ GOOD"
        elif result['pf'] >= 1.5:
            target = "~PF OK"
        
        results.append((name, filters, result, target))
        
        print(f"{name:<40} {result['trades']:>7} {result['wr']:>5.1f}% {result['pf']:>6.2f} ${result['net_pnl']:>10,.0f} {target}")
    
    # Find best candidates
    print("\n" + "=" * 95)
    print("TOP CANDIDATES (sorted by PF with Trades >= 100)")
    print("=" * 95)
    
    valid = [r for r in results if r[2]['trades'] >= 100]
    valid.sort(key=lambda x: x[2]['pf'], reverse=True)
    
    for i, (name, filters, result, target) in enumerate(valid[:5], 1):
        print(f"\n{i}. {name}")
        print(f"   Trades: {result['trades']} | WR: {result['wr']:.1f}% | PF: {result['pf']:.2f} | PnL: ${result['net_pnl']:,.0f}")
        if filters:
            print(f"   Filters: {filters}")


def main():
    if len(sys.argv) < 2:
        # Default to latest log
        log_dir = Path(__file__).parent / 'temp_reports'
        logs = sorted(log_dir.glob('KOI_EURUSD_trades_*.txt'))
        if not logs:
            print("No log files found. Run koi_eurusd_pro.py first.")
            return
        filepath = logs[-1]
        print(f"Using latest log: {filepath.name}")
    else:
        filepath = Path(sys.argv[1])
    
    if not filepath.exists():
        print(f"File not found: {filepath}")
        return
    
    trades = parse_trade_log(filepath)
    print(f"\n{'='*85}")
    print(f"KOI EURUSD TRADE LOG ANALYSIS")
    print(f"{'='*85}")
    print(f"Log: {filepath.name}")
    print(f"Parsed {len(trades)} trades")
    
    # Overall stats
    wins = [t for t in trades if t['win']]
    losses = [t for t in trades if not t['win']]
    gross_profit = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))
    total_pnl = gross_profit - gross_loss
    current_pf = gross_profit / gross_loss if gross_loss > 0 else 0
    
    print(f"\nCURRENT PERFORMANCE (baseline):")
    print(f"  Trades: {len(trades)}")
    print(f"  Wins: {len(wins)} ({len(wins)/len(trades)*100:.1f}%)")
    print(f"  Profit Factor: {current_pf:.2f}")
    print(f"  Net PnL: ${total_pnl:,.0f}")
    print(f"\n  TARGET: PF > 1.5, Trades > 120")
    
    # Detailed analysis
    profitable_hours, losing_hours, hourly = analyze_by_hour(trades)
    analyze_by_weekday(trades)
    analyze_by_sl_pips(trades)
    analyze_by_atr(trades)
    analyze_by_cci(trades)
    
    # Filter testing
    test_filter_combinations(trades, profitable_hours, losing_hours)


if __name__ == "__main__":
    main()
