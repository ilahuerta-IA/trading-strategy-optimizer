"""
COMPREHENSIVE LOG ANALYZER FOR OGLE STRATEGY
============================================
Analyzes trade logs to find optimal parameter combinations for:
- Entry angles
- ATR values and increments
- Entry hours
- Other patterns

Run: python analyze_all_logs.py
"""

import os
import re
from datetime import datetime
from collections import defaultdict
import statistics

# Configuration
LOG_DIR = "temp_reports"
# Use most recent BestPnL log file
LOG_FILE = "EURUSD_trades_20251219_080543.txt"  # BestPnL baseline (376 trades)


def parse_trade_log(filepath):
    """Parse a trade log file and extract all trade data."""
    trades = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by trade entries
    trade_blocks = re.split(r'ENTRY #\d+', content)[1:]  # Skip header
    
    for i, block in enumerate(trade_blocks, 1):
        trade = {'entry_num': i}
        
        # Parse entry time
        time_match = re.search(r'Time: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', block)
        if time_match:
            dt = datetime.strptime(time_match.group(1), '%Y-%m-%d %H:%M:%S')
            trade['entry_time'] = dt
            trade['entry_hour'] = dt.hour
            trade['entry_minute'] = dt.minute
            trade['entry_weekday'] = dt.weekday()  # 0=Mon, 6=Sun
            trade['entry_year'] = dt.year
        
        # Parse ATR Current
        atr_match = re.search(r'ATR Current: ([\d.]+)', block)
        if atr_match:
            trade['atr_current'] = float(atr_match.group(1))
        
        # Parse ATR Increment/Decrement (handle both formats)
        inc_match = re.search(r'ATR (?:Increment|Change): ([+-]?[\d.e-]+)', block)
        if inc_match:
            trade['atr_change'] = float(inc_match.group(1))
        
        # Parse Angle Current
        angle_match = re.search(r'Angle Current: ([+-]?[\d.]+)', block)
        if angle_match:
            trade['angle'] = float(angle_match.group(1))
        
        # Parse Bars to Entry
        bars_match = re.search(r'Bars to Entry: (\d+)', block)
        if bars_match:
            trade['bars_to_entry'] = int(bars_match.group(1))
        
        # Parse Exit info
        exit_match = re.search(r'Exit Reason: (\w+)', block)
        if exit_match:
            trade['exit_reason'] = exit_match.group(1)
        
        # Parse P&L
        pnl_match = re.search(r'P&L: ([+-]?[\d.]+)', block)
        if pnl_match:
            trade['pnl'] = float(pnl_match.group(1))
        
        # Parse Pips
        pips_match = re.search(r'Pips: ([+-]?[\d.]+)', block)
        if pips_match:
            trade['pips'] = float(pips_match.group(1))
        
        # Parse Duration
        duration_match = re.search(r'Duration: (\d+) bars', block)
        if duration_match:
            trade['duration_bars'] = int(duration_match.group(1))
        
        trades.append(trade)
    
    return trades


def analyze_by_range(trades, field, ranges, min_trades=20):
    """Analyze trades grouped by value ranges."""
    results = {}
    
    for range_name, (min_val, max_val) in ranges.items():
        range_trades = [t for t in trades 
                       if field in t and min_val <= t[field] < max_val]
        
        if len(range_trades) < min_trades:
            continue
        
        wins = [t for t in range_trades if t.get('pnl', 0) > 0]
        losses = [t for t in range_trades if t.get('pnl', 0) <= 0]
        
        total_pnl = sum(t.get('pnl', 0) for t in range_trades)
        gross_profit = sum(t.get('pnl', 0) for t in wins)
        gross_loss = abs(sum(t.get('pnl', 0) for t in losses))
        
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        wr = len(wins) / len(range_trades) * 100 if range_trades else 0
        
        results[range_name] = {
            'trades': len(range_trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': wr,
            'profit_factor': pf,
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / len(range_trades) if range_trades else 0
        }
    
    return results


def analyze_by_hour(trades, min_trades=10):
    """Analyze trades grouped by entry hour."""
    results = {}
    
    for hour in range(24):
        hour_trades = [t for t in trades if t.get('entry_hour') == hour]
        
        if len(hour_trades) < min_trades:
            continue
        
        wins = [t for t in hour_trades if t.get('pnl', 0) > 0]
        losses = [t for t in hour_trades if t.get('pnl', 0) <= 0]
        
        total_pnl = sum(t.get('pnl', 0) for t in hour_trades)
        gross_profit = sum(t.get('pnl', 0) for t in wins)
        gross_loss = abs(sum(t.get('pnl', 0) for t in losses))
        
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        wr = len(wins) / len(hour_trades) * 100 if hour_trades else 0
        
        results[hour] = {
            'trades': len(hour_trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': wr,
            'profit_factor': pf,
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / len(hour_trades) if hour_trades else 0
        }
    
    return results


def analyze_by_weekday(trades, min_trades=30):
    """Analyze trades grouped by weekday."""
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    results = {}
    
    for day in range(7):
        day_trades = [t for t in trades if t.get('entry_weekday') == day]
        
        if len(day_trades) < min_trades:
            continue
        
        wins = [t for t in day_trades if t.get('pnl', 0) > 0]
        losses = [t for t in day_trades if t.get('pnl', 0) <= 0]
        
        total_pnl = sum(t.get('pnl', 0) for t in day_trades)
        gross_profit = sum(t.get('pnl', 0) for t in wins)
        gross_loss = abs(sum(t.get('pnl', 0) for t in losses))
        
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        wr = len(wins) / len(day_trades) * 100 if day_trades else 0
        
        results[day_names[day]] = {
            'trades': len(day_trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': wr,
            'profit_factor': pf,
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / len(day_trades) if day_trades else 0
        }
    
    return results


def analyze_winners_vs_losers(trades):
    """Compare characteristics of winning vs losing trades."""
    winners = [t for t in trades if t.get('pnl', 0) > 0]
    losers = [t for t in trades if t.get('pnl', 0) <= 0]
    
    analysis = {}
    
    # Angle analysis
    winner_angles = [t['angle'] for t in winners if 'angle' in t]
    loser_angles = [t['angle'] for t in losers if 'angle' in t]
    
    if winner_angles and loser_angles:
        analysis['angle'] = {
            'winners_mean': statistics.mean(winner_angles),
            'winners_median': statistics.median(winner_angles),
            'winners_stdev': statistics.stdev(winner_angles) if len(winner_angles) > 1 else 0,
            'losers_mean': statistics.mean(loser_angles),
            'losers_median': statistics.median(loser_angles),
            'losers_stdev': statistics.stdev(loser_angles) if len(loser_angles) > 1 else 0,
        }
    
    # ATR analysis
    winner_atrs = [t['atr_current'] for t in winners if 'atr_current' in t]
    loser_atrs = [t['atr_current'] for t in losers if 'atr_current' in t]
    
    if winner_atrs and loser_atrs:
        analysis['atr'] = {
            'winners_mean': statistics.mean(winner_atrs),
            'winners_median': statistics.median(winner_atrs),
            'losers_mean': statistics.mean(loser_atrs),
            'losers_median': statistics.median(loser_atrs),
        }
    
    # ATR change analysis
    winner_changes = [t['atr_change'] for t in winners if 'atr_change' in t]
    loser_changes = [t['atr_change'] for t in losers if 'atr_change' in t]
    
    if winner_changes and loser_changes:
        analysis['atr_change'] = {
            'winners_mean': statistics.mean(winner_changes),
            'winners_median': statistics.median(winner_changes),
            'losers_mean': statistics.mean(loser_changes),
            'losers_median': statistics.median(loser_changes),
        }
    
    # Hour distribution
    winner_hours = [t['entry_hour'] for t in winners if 'entry_hour' in t]
    loser_hours = [t['entry_hour'] for t in losers if 'entry_hour' in t]
    
    if winner_hours and loser_hours:
        analysis['hour'] = {
            'winners_mean': statistics.mean(winner_hours),
            'winners_median': statistics.median(winner_hours),
            'losers_mean': statistics.mean(loser_hours),
            'losers_median': statistics.median(loser_hours),
        }
    
    return analysis


def print_results_table(title, results, sort_by='profit_factor'):
    """Print results in a formatted table."""
    print(f"\n{'='*70}")
    print(f" {title}")
    print(f"{'='*70}")
    
    if not results:
        print("  No results with sufficient trades")
        return
    
    # Sort results
    sorted_results = sorted(results.items(), 
                           key=lambda x: x[1].get(sort_by, 0), 
                           reverse=True)
    
    print(f"{'Range':<25} {'Trades':>7} {'WR%':>7} {'PF':>7} {'Total PnL':>12} {'Avg PnL':>10}")
    print("-" * 70)
    
    for name, data in sorted_results:
        print(f"{str(name):<25} {data['trades']:>7} {data['win_rate']:>6.1f}% "
              f"{data['profit_factor']:>7.2f} ${data['total_pnl']:>11,.0f} ${data['avg_pnl']:>9,.0f}")


def generate_phase8_recommendations(trades):
    """Generate recommendations for Phase 8 based on analysis."""
    print("\n" + "="*70)
    print(" PHASE 8 RECOMMENDATIONS - ANGLE FILTER OPTIMIZATION")
    print("="*70)
    
    # Analyze by angle ranges (finer granularity)
    angle_ranges = {
        '0-20°': (0, 20),
        '20-40°': (20, 40),
        '40-60°': (40, 60),
        '60-80°': (60, 80),
        '80-90°': (80, 90),
    }
    
    angle_results = analyze_by_range(trades, 'angle', angle_ranges, min_trades=15)
    
    # Also check negative angles
    neg_angle_ranges = {
        '-90 to -60°': (-90, -60),
        '-60 to -40°': (-60, -40),
        '-40 to -20°': (-40, -20),
        '-20 to 0°': (-20, 0),
    }
    
    neg_results = analyze_by_range(trades, 'angle', neg_angle_ranges, min_trades=15)
    
    # Combined analysis
    all_results = {**angle_results, **neg_results}
    
    print("\nANGLE RANGE ANALYSIS:")
    print_results_table("Positive Angles", angle_results)
    print_results_table("Negative Angles", neg_results)
    
    # Find best angle ranges
    best_angles = [(k, v) for k, v in all_results.items() if v['profit_factor'] > 1.2]
    
    print("\n" + "-"*70)
    print("RECOMMENDED ANGLE RANGES (PF > 1.2):")
    for name, data in sorted(best_angles, key=lambda x: -x[1]['profit_factor']):
        print(f"  - {name}: PF={data['profit_factor']:.2f}, Trades={data['trades']}, WR={data['win_rate']:.1f}%")
    
    # ATR analysis for Phase 8
    atr_ranges = {
        '0.00015-0.00020': (0.000150, 0.000200),
        '0.00020-0.00025': (0.000200, 0.000250),
        '0.00025-0.00030': (0.000250, 0.000300),
        '0.00030-0.00035': (0.000300, 0.000350),
        '0.00035-0.00040': (0.000350, 0.000400),
        '0.00040-0.00045': (0.000400, 0.000450),
        '0.00045-0.00050': (0.000450, 0.000500),
    }
    
    print_results_table("ATR Range Analysis", analyze_by_range(trades, 'atr_current', atr_ranges))
    
    # ATR Change analysis
    atr_change_ranges = {
        'Strong Dec (<-0.00005)': (-0.001, -0.00005),
        'Mod Dec (-0.00005 to -0.00002)': (-0.00005, -0.00002),
        'Slight Dec (-0.00002 to 0)': (-0.00002, 0),
        'Slight Inc (0 to 0.00002)': (0, 0.00002),
        'Mod Inc (0.00002 to 0.00005)': (0.00002, 0.00005),
        'Strong Inc (>0.00005)': (0.00005, 0.001),
    }
    
    print_results_table("ATR Change Analysis", analyze_by_range(trades, 'atr_change', atr_change_ranges))
    
    # Hour analysis
    print_results_table("Entry Hour Analysis", analyze_by_hour(trades), sort_by='profit_factor')
    
    # Weekday analysis  
    print_results_table("Weekday Analysis", analyze_by_weekday(trades), sort_by='profit_factor')
    
    # Winner vs Loser comparison
    comparison = analyze_winners_vs_losers(trades)
    
    print("\n" + "="*70)
    print(" WINNER vs LOSER CHARACTERISTICS")
    print("="*70)
    
    if 'angle' in comparison:
        print(f"\nANGLE:")
        print(f"  Winners: mean={comparison['angle']['winners_mean']:.1f}°, median={comparison['angle']['winners_median']:.1f}°")
        print(f"  Losers:  mean={comparison['angle']['losers_mean']:.1f}°, median={comparison['angle']['losers_median']:.1f}°")
    
    if 'atr' in comparison:
        print(f"\nATR:")
        print(f"  Winners: mean={comparison['atr']['winners_mean']:.6f}, median={comparison['atr']['winners_median']:.6f}")
        print(f"  Losers:  mean={comparison['atr']['losers_mean']:.6f}, median={comparison['atr']['losers_median']:.6f}")
    
    if 'atr_change' in comparison:
        print(f"\nATR CHANGE:")
        print(f"  Winners: mean={comparison['atr_change']['winners_mean']:+.6f}, median={comparison['atr_change']['winners_median']:+.6f}")
        print(f"  Losers:  mean={comparison['atr_change']['losers_mean']:+.6f}, median={comparison['atr_change']['losers_median']:+.6f}")
    
    if 'hour' in comparison:
        print(f"\nENTRY HOUR:")
        print(f"  Winners: mean={comparison['hour']['winners_mean']:.1f}h, median={comparison['hour']['winners_median']:.0f}h")
        print(f"  Losers:  mean={comparison['hour']['losers_mean']:.1f}h, median={comparison['hour']['losers_median']:.0f}h")
    
    # Generate specific Phase 8 grid suggestion
    print("\n" + "="*70)
    print(" SUGGESTED PHASE 8 BACKTEST GRID")
    print("="*70)
    
    # Find best angle ranges
    best_pf_angles = [(k, v) for k, v in all_results.items() if v['profit_factor'] > 1.15]
    
    if best_pf_angles:
        print("\nBased on analysis, suggest testing these ANGLE combinations:")
        print("  PHASE8_GRID = {")
        print("      'long_use_angle_filter': [True],")
        # Extract actual min/max from best ranges
        best_min = min([v[0] for k, v in angle_ranges.items() if k in [x[0] for x in best_pf_angles]] + 
                      [v[0] for k, v in neg_angle_ranges.items() if k in [x[0] for x in best_pf_angles]])
        best_max = max([v[1] for k, v in angle_ranges.items() if k in [x[0] for x in best_pf_angles]] + 
                      [v[1] for k, v in neg_angle_ranges.items() if k in [x[0] for x in best_pf_angles]])
        print(f"      'long_min_angle': [0, 20, 30, 40],")
        print(f"      'long_max_angle': [60, 70, 80, 85],")
        print("  }")
    
    return all_results


def main():
    """Main analysis function."""
    filepath = os.path.join(LOG_DIR, LOG_FILE)
    
    if not os.path.exists(filepath):
        print(f"ERROR: Log file not found: {filepath}")
        print("Available files:")
        for f in os.listdir(LOG_DIR):
            if f.endswith('.txt'):
                print(f"  - {f}")
        return
    
    print("="*70)
    print(" COMPREHENSIVE LOG ANALYSIS - OGLE STRATEGY")
    print("="*70)
    print(f"Analyzing: {LOG_FILE}")
    
    trades = parse_trade_log(filepath)
    print(f"Total trades parsed: {len(trades)}")
    
    # Basic stats
    wins = [t for t in trades if t.get('pnl', 0) > 0]
    losses = [t for t in trades if t.get('pnl', 0) <= 0]
    total_pnl = sum(t.get('pnl', 0) for t in trades)
    
    print(f"Wins: {len(wins)} | Losses: {len(losses)} | Total PnL: ${total_pnl:,.2f}")
    
    # Run comprehensive analysis
    generate_phase8_recommendations(trades)
    
    print("\n" + "="*70)
    print(" ANALYSIS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
