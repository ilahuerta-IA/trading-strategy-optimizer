"""KOI Strategy - Robustness Test with Different Date Ranges
============================================================
Tests the strategy with multiple start/end date combinations
to verify stability and avoid overfitting.
"""
import subprocess
import re

# Different date ranges to test
DATE_RANGES = [
    # Original
    ("2020-01-01", "2025-12-01", "Full 5Y"),
    # Skip 2020 (problematic year)
    ("2021-01-01", "2025-12-01", "2021-2025 (4Y)"),
    # Different start months
    ("2020-03-01", "2025-12-01", "Mar 2020 start"),
    ("2020-06-01", "2025-12-01", "Jun 2020 start"),
    # Different end dates
    ("2020-01-01", "2024-12-01", "End 2024"),
    ("2020-01-01", "2025-06-01", "End Jun 2025"),
    # Shorter periods
    ("2021-01-01", "2024-12-01", "2021-2024 (4Y)"),
    ("2022-01-01", "2025-12-01", "2022-2025 (4Y)"),
    # Walk-forward windows
    ("2020-01-01", "2022-12-31", "2020-2022 (3Y)"),
    ("2022-01-01", "2024-12-31", "2022-2024 (3Y)"),
]

def run_backtest(fromdate, todate):
    """Run koi_template.py with modified dates and capture output."""
    # Read the template
    with open('koi_template.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Modify dates
    modified = re.sub(r"FROMDATE = '[^']+'", f"FROMDATE = '{fromdate}'", content)
    modified = re.sub(r"TODATE = '[^']+'", f"TODATE = '{todate}'", modified)
    
    # Write temp file
    with open('_koi_temp_test.py', 'w', encoding='utf-8') as f:
        f.write(modified)
    
    # Run and capture output
    result = subprocess.run(
        ['python', '_koi_temp_test.py'],
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    
    return result.stdout + result.stderr

def parse_results(output):
    """Extract key metrics from output."""
    metrics = {}
    
    # Trades
    m = re.search(r'Total Trades: (\d+)', output)
    metrics['trades'] = int(m.group(1)) if m else 0
    
    # Win Rate
    m = re.search(r'Win Rate: ([\d.]+)%', output)
    metrics['wr'] = float(m.group(1)) if m else 0
    
    # Profit Factor
    m = re.search(r'Profit Factor: ([\d.]+)', output)
    metrics['pf'] = float(m.group(1)) if m else 0
    
    # Net P&L
    m = re.search(r'Net P&L: \$([\d,.-]+)', output)
    if m:
        metrics['pnl'] = float(m.group(1).replace(',', ''))
    else:
        metrics['pnl'] = 0
    
    # Sharpe (Daily)
    m = re.search(r'Sharpe Ratio \(Daily\):\s+([\d.-]+)', output)
    metrics['sharpe'] = float(m.group(1)) if m else 0
    
    # Sortino (Daily)
    m = re.search(r'Sortino Ratio \(Daily\):\s+([\d.-]+)', output)
    metrics['sortino'] = float(m.group(1)) if m else 0
    
    # Max DD
    m = re.search(r'Max Drawdown:\s+([\d.]+)%', output)
    metrics['max_dd'] = float(m.group(1)) if m else 0
    
    # CAGR
    m = re.search(r'CAGR:\s+([\d.-]+)%', output)
    metrics['cagr'] = float(m.group(1)) if m else 0
    
    # Calmar
    m = re.search(r'Calmar Ratio:\s+([\d.-]+)', output)
    metrics['calmar'] = float(m.group(1)) if m else 0
    
    return metrics

def main():
    print("=" * 90)
    print("KOI STRATEGY - ROBUSTNESS TEST")
    print("=" * 90)
    print()
    
    results = []
    
    for fromdate, todate, label in DATE_RANGES:
        print(f"Testing: {label} ({fromdate} to {todate})...", end=" ", flush=True)
        output = run_backtest(fromdate, todate)
        metrics = parse_results(output)
        metrics['label'] = label
        metrics['from'] = fromdate
        metrics['to'] = todate
        results.append(metrics)
        print(f"Done. Trades={metrics['trades']}, PF={metrics['pf']:.2f}")
    
    # Print summary table
    print()
    print("=" * 90)
    print("ROBUSTNESS TEST RESULTS")
    print("=" * 90)
    print(f"{'Period':<20} {'Trades':>7} {'WR%':>6} {'PF':>6} {'P&L':>10} {'Sharpe':>7} {'Sortino':>8} {'MaxDD':>7} {'CAGR':>7}")
    print("-" * 90)
    
    for r in results:
        print(f"{r['label']:<20} {r['trades']:>7} {r['wr']:>5.1f}% {r['pf']:>6.2f} ${r['pnl']:>9,.0f} {r['sharpe']:>7.2f} {r['sortino']:>8.2f} {r['max_dd']:>6.1f}% {r['cagr']:>6.1f}%")
    
    print("-" * 90)
    
    # Statistics
    pfs = [r['pf'] for r in results if r['pf'] > 0]
    sharpes = [r['sharpe'] for r in results]
    dds = [r['max_dd'] for r in results if r['max_dd'] > 0]
    
    print(f"\nSTABILITY METRICS:")
    print(f"  PF Range: {min(pfs):.2f} - {max(pfs):.2f} (Avg: {sum(pfs)/len(pfs):.2f})")
    print(f"  Sharpe Range: {min(sharpes):.2f} - {max(sharpes):.2f} (Avg: {sum(sharpes)/len(sharpes):.2f})")
    print(f"  MaxDD Range: {min(dds):.1f}% - {max(dds):.1f}% (Avg: {sum(dds)/len(dds):.1f}%)")
    
    # Count how many pass minimum criteria
    passing = sum(1 for r in results if r['pf'] >= 1.5 and r['trades'] >= 30)
    print(f"\n  Tests passing (PF>=1.5, Trades>=30): {passing}/{len(results)} ({passing/len(results)*100:.0f}%)")
    
    # Cleanup
    import os
    try:
        os.remove('_koi_temp_test.py')
    except:
        pass
    
    print()
    print("=" * 90)

if __name__ == '__main__':
    main()
