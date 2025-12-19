"""
Analyze KOI EURUSD trade log for filter optimization.
"""
import re
from collections import defaultdict

LOG_FILE = 'temp_reports/KOI_EURUSD_trades_20251219_193043.txt'

def parse_trades(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Parse entries
    entry_pattern = r'ENTRY #(\d+)\nTime: (\d{4}-\d{2}-\d{2} (\d{2}):\d{2}:\d{2})\n.*?SL Pips: ([\d.]+)\nATR: ([\d.]+)\nCCI: ([\d.]+)'
    entries = re.findall(entry_pattern, content, re.DOTALL)
    
    # Parse exits - handle negative P&L with minus sign
    exit_pattern = r'EXIT #(\d+)\nTime: .*?\nExit Reason: (\w+)\nP&L: \$(-?[\d,.]+)'
    exits = re.findall(exit_pattern, content)
    
    trades = []
    for i, (num, time_full, hour, sl_pips, atr, cci) in enumerate(entries):
        if i < len(exits):
            exit_num, reason, pnl_str = exits[i]
            pnl = float(pnl_str.replace(',', ''))
            trades.append({
                'num': int(num),
                'time': time_full,
                'hour': int(hour),
                'sl_pips': float(sl_pips),
                'atr': float(atr),
                'cci': float(cci),
                'pnl': pnl,
                'win': pnl > 0,
                'reason': reason
            })
    return trades

def analyze_by_hour(trades):
    print("\n" + "="*70)
    print("HOURLY ANALYSIS")
    print("="*70)
    print(f"{'Hour':>4}  {'Trades':>6}  {'Wins':>5}  {'WR%':>6}  {'PnL':>12}  {'AvgPnL':>9}  Status")
    print("-"*70)
    
    hourly = defaultdict(lambda: {'t': 0, 'w': 0, 'pnl': 0.0})
    for t in trades:
        hourly[t['hour']]['t'] += 1
        hourly[t['hour']]['pnl'] += t['pnl']
        if t['win']: 
            hourly[t['hour']]['w'] += 1
    
    good_hours = []
    bad_hours = []
    
    for h in sorted(hourly.keys()):
        d = hourly[h]
        wr = d['w']/d['t']*100 if d['t'] > 0 else 0
        avg = d['pnl']/d['t'] if d['t'] > 0 else 0
        status = "✓ GOOD" if d['pnl'] > 0 else "✗ BAD"
        print(f"{h:>4}  {d['t']:>6}  {d['w']:>5}  {wr:>5.1f}%  ${d['pnl']:>10,.0f}  ${avg:>8,.0f}  {status}")
        
        if d['pnl'] > 0:
            good_hours.append(h)
        else:
            bad_hours.append(h)
    
    print("-"*70)
    print(f"Good hours: {good_hours}")
    print(f"Bad hours: {bad_hours}")
    return hourly

def analyze_by_sl_pips(trades):
    print("\n" + "="*70)
    print("SL PIPS ANALYSIS")
    print("="*70)
    
    # Define buckets
    buckets = [(0, 10), (10, 12), (12, 14), (14, 16), (16, 18), (18, 20), (20, 100)]
    
    print(f"{'SL Range':>12}  {'Trades':>6}  {'Wins':>5}  {'WR%':>6}  {'PnL':>12}  Status")
    print("-"*70)
    
    for low, high in buckets:
        bucket_trades = [t for t in trades if low <= t['sl_pips'] < high]
        if not bucket_trades:
            continue
        wins = sum(1 for t in bucket_trades if t['win'])
        pnl = sum(t['pnl'] for t in bucket_trades)
        wr = wins/len(bucket_trades)*100
        status = "✓" if pnl > 0 else "✗"
        print(f"{low:>5}-{high:<5}  {len(bucket_trades):>6}  {wins:>5}  {wr:>5.1f}%  ${pnl:>10,.0f}  {status}")

def analyze_by_atr(trades):
    print("\n" + "="*70)
    print("ATR ANALYSIS")
    print("="*70)
    
    # Define buckets in pips (ATR * 10000 for EURUSD)
    buckets = [(0, 0.00030), (0.00030, 0.00040), (0.00040, 0.00050), 
               (0.00050, 0.00060), (0.00060, 0.00080), (0.00080, 0.01)]
    
    print(f"{'ATR Range':>18}  {'Trades':>6}  {'Wins':>5}  {'WR%':>6}  {'PnL':>12}  Status")
    print("-"*70)
    
    for low, high in buckets:
        bucket_trades = [t for t in trades if low <= t['atr'] < high]
        if not bucket_trades:
            continue
        wins = sum(1 for t in bucket_trades if t['win'])
        pnl = sum(t['pnl'] for t in bucket_trades)
        wr = wins/len(bucket_trades)*100
        status = "✓" if pnl > 0 else "✗"
        print(f"{low:.5f}-{high:.5f}  {len(bucket_trades):>6}  {wins:>5}  {wr:>5.1f}%  ${pnl:>10,.0f}  {status}")

def analyze_by_cci(trades):
    print("\n" + "="*70)
    print("CCI ANALYSIS")
    print("="*70)
    
    buckets = [(100, 120), (120, 140), (140, 160), (160, 180), (180, 200), (200, 500)]
    
    print(f"{'CCI Range':>12}  {'Trades':>6}  {'Wins':>5}  {'WR%':>6}  {'PnL':>12}  Status")
    print("-"*70)
    
    for low, high in buckets:
        bucket_trades = [t for t in trades if low <= t['cci'] < high]
        if not bucket_trades:
            continue
        wins = sum(1 for t in bucket_trades if t['win'])
        pnl = sum(t['pnl'] for t in bucket_trades)
        wr = wins/len(bucket_trades)*100
        status = "✓" if pnl > 0 else "✗"
        print(f"{low:>5}-{high:<5}  {len(bucket_trades):>6}  {wins:>5}  {wr:>5.1f}%  ${pnl:>10,.0f}  {status}")

def simulate_filters(trades, good_hours=None, sl_min=None, sl_max=None, atr_min=None, atr_max=None, cci_min=None):
    """Simulate applying filters to see potential improvement."""
    filtered = trades.copy()
    
    if good_hours:
        filtered = [t for t in filtered if t['hour'] in good_hours]
    if sl_min:
        filtered = [t for t in filtered if t['sl_pips'] >= sl_min]
    if sl_max:
        filtered = [t for t in filtered if t['sl_pips'] <= sl_max]
    if atr_min:
        filtered = [t for t in filtered if t['atr'] >= atr_min]
    if atr_max:
        filtered = [t for t in filtered if t['atr'] <= atr_max]
    if cci_min:
        filtered = [t for t in filtered if t['cci'] >= cci_min]
    
    if not filtered:
        return None
    
    wins = sum(1 for t in filtered if t['win'])
    losses = len(filtered) - wins
    gross_profit = sum(t['pnl'] for t in filtered if t['win'])
    gross_loss = abs(sum(t['pnl'] for t in filtered if not t['win']))
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    wr = wins / len(filtered) * 100
    net_pnl = sum(t['pnl'] for t in filtered)
    
    return {
        'trades': len(filtered),
        'wins': wins,
        'losses': losses,
        'wr': wr,
        'pf': pf,
        'net_pnl': net_pnl,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss
    }

def main():
    trades = parse_trades(LOG_FILE)
    
    print("="*70)
    print("KOI EURUSD TRADE LOG ANALYSIS")
    print("="*70)
    print(f"Total Trades: {len(trades)}")
    print(f"Winners: {sum(1 for t in trades if t['win'])}")
    print(f"Losers: {sum(1 for t in trades if not t['win'])}")
    print(f"Win Rate: {sum(1 for t in trades if t['win'])/len(trades)*100:.1f}%")
    gross_profit = sum(t['pnl'] for t in trades if t['win'])
    gross_loss = abs(sum(t['pnl'] for t in trades if not t['win']))
    print(f"Gross Profit: ${gross_profit:,.0f}")
    print(f"Gross Loss: ${gross_loss:,.0f}")
    print(f"Profit Factor: {gross_profit/gross_loss:.2f}" if gross_loss > 0 else "N/A")
    print(f"Net P&L: ${sum(t['pnl'] for t in trades):,.0f}")
    
    analyze_by_hour(trades)
    analyze_by_sl_pips(trades)
    analyze_by_atr(trades)
    analyze_by_cci(trades)
    
    # Test filter combinations
    print("\n" + "="*70)
    print("FILTER SIMULATIONS")
    print("="*70)
    
    # Base case
    base = simulate_filters(trades)
    print(f"\nBASELINE (no filters):")
    print(f"  Trades: {base['trades']} | WR: {base['wr']:.1f}% | PF: {base['pf']:.2f} | PnL: ${base['net_pnl']:,.0f}")
    
    # Test various filter combinations
    tests = [
        ("Hours 7-16 only", {'good_hours': list(range(7, 17))}),
        ("Hours 8-14 only", {'good_hours': list(range(8, 15))}),
        ("Hours 9-13 only", {'good_hours': list(range(9, 14))}),
        ("SL 12-18 pips", {'sl_min': 12, 'sl_max': 18}),
        ("SL 14-20 pips", {'sl_min': 14, 'sl_max': 20}),
        ("ATR 0.0004-0.0006", {'atr_min': 0.0004, 'atr_max': 0.0006}),
        ("ATR 0.0005-0.0008", {'atr_min': 0.0005, 'atr_max': 0.0008}),
        ("CCI > 140", {'cci_min': 140}),
        ("CCI > 160", {'cci_min': 160}),
        ("Hours 8-14 + SL 12-18", {'good_hours': list(range(8, 15)), 'sl_min': 12, 'sl_max': 18}),
        ("Hours 8-14 + ATR 0.0004-0.0006", {'good_hours': list(range(8, 15)), 'atr_min': 0.0004, 'atr_max': 0.0006}),
        ("Hours 8-14 + CCI > 140", {'good_hours': list(range(8, 15)), 'cci_min': 140}),
        ("Best combo: H8-14, SL12-18, CCI>140", {'good_hours': list(range(8, 15)), 'sl_min': 12, 'sl_max': 18, 'cci_min': 140}),
    ]
    
    print(f"\n{'Filter':<40} {'Trades':>7} {'WR%':>6} {'PF':>6} {'PnL':>12}")
    print("-"*75)
    
    for name, params in tests:
        result = simulate_filters(trades, **params)
        if result and result['trades'] >= 50:  # Minimum trades for validity
            print(f"{name:<40} {result['trades']:>7} {result['wr']:>5.1f}% {result['pf']:>6.2f} ${result['net_pnl']:>10,.0f}")
        elif result:
            print(f"{name:<40} {result['trades']:>7} {result['wr']:>5.1f}% {result['pf']:>6.2f} ${result['net_pnl']:>10,.0f} (low trades)")

if __name__ == '__main__':
    main()
