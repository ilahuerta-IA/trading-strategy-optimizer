"""KOI USDCAD Robustness Test - 10 Date Ranges
==============================================
Tests strategy stability across different time periods per OPTIMIZATION_GUIDE.

Test Matrix (10 tests):
| Test # | Period | Duration | Purpose |
|--------|--------|----------|---------|
| BASELINE | 2020-01-01 to 2025-12-01 | ~6 years | Full dataset |
| 1 | 2020 | 1 year | COVID recovery |
| 2 | 2021 | 1 year | Bull year |
| 3 | 2022 | 1 year | Rate hikes |
| 4 | 2023 | 1 year | Consolidation |
| 5 | 2024 | 1 year | Recent |
| 6 | 2020-2021 | 2 years | Early period |
| 7 | 2022-2023 | 2 years | Mid period |
| 8 | 2024-2025.07 | 1.5 years | Recent |
| 9 | 2020.07-2023.06 | 3 years | Alt window |
| 10 | 2025 H1 | 6 months | Latest |

Note: Uses subprocess approach because indicators need warmup from data start.
The strategy file is modified temporarily for each test run.

Robustness Criteria:
- PF > 1.2 in 70%+ tests = PASS
- WR > 20% in all tests (lower threshold for trend-following)
- Max DD < 25% in all tests
- Positive PnL in 60%+ tests
"""
import subprocess
import sys
import re
from pathlib import Path

# =============================================================================
# BASELINE RESULTS (Full 5Y test)
# =============================================================================
BASELINE = {
    'period': '2020-01-01 to 2025-12-01',
    'trades': 147,
    'win_rate': 28.6,
    'pf': 1.46,
    'pnl': 21905,
    'max_dd': 6.06,
    'sharpe': 2.62,
    'yearly': {
        2020: {'trades': 27, 'wr': 29.6, 'pf': 1.55, 'pnl': 4271},
        2021: {'trades': 21, 'wr': 23.8, 'pf': 1.17, 'pnl': 1172},
        2022: {'trades': 24, 'wr': 37.5, 'pf': 2.23, 'pnl': 8169},
        2023: {'trades': 30, 'wr': 30.0, 'pf': 1.56, 'pnl': 5470},
        2024: {'trades': 15, 'wr': 40.0, 'pf': 2.47, 'pnl': 6298},
        2025: {'trades': 30, 'wr': 16.7, 'pf': 0.71, 'pnl': -3493},
    }
}

# =============================================================================
# TEST PERIODS - All start from 2020 to allow indicator warmup
# =============================================================================
TEST_PERIODS = [
    # Single years - use yearly stats from longer runs
    {'id': 1, 'name': '2020', 'from': '2020-01-01', 'to': '2020-12-31', 'desc': 'COVID recovery', 'direct': True},
    {'id': 2, 'name': '2021', 'from': '2020-01-01', 'to': '2021-12-31', 'desc': 'Bull year', 'filter_year': 2021},
    {'id': 3, 'name': '2022', 'from': '2020-01-01', 'to': '2022-12-31', 'desc': 'Rate hikes', 'filter_year': 2022},
    {'id': 4, 'name': '2023', 'from': '2020-01-01', 'to': '2023-12-31', 'desc': 'Consolidation', 'filter_year': 2023},
    {'id': 5, 'name': '2024', 'from': '2020-01-01', 'to': '2024-12-31', 'desc': 'Recent', 'filter_year': 2024},
    # Multi-year periods
    {'id': 6, 'name': '2020-2021', 'from': '2020-01-01', 'to': '2021-12-31', 'desc': 'Early 2Y', 'direct': True},
    {'id': 7, 'name': '2022-2023', 'from': '2020-01-01', 'to': '2023-12-31', 'desc': 'Mid 2Y', 'filter_years': [2022, 2023]},
    {'id': 8, 'name': '2024-2025.07', 'from': '2020-01-01', 'to': '2025-07-01', 'desc': 'Recent 1.5Y', 'filter_years': [2024, 2025]},
    {'id': 9, 'name': '2020.07-2023.06', 'from': '2020-01-01', 'to': '2023-06-30', 'desc': 'Alt 3Y', 'filter_start': '2020-07-01'},
    {'id': 10, 'name': '2025 H1', 'from': '2020-01-01', 'to': '2025-07-01', 'desc': 'Latest', 'filter_year': 2025},
]


def run_backtest(from_date: str, to_date: str) -> dict:
    """Run backtest using subprocess and parse results."""
    
    # Read strategy file
    strategy_file = Path(__file__).parent / 'koi_usdcad_pro.py'
    with open(strategy_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Modify dates
    modified = re.sub(r"FROMDATE = '[^']+'", f"FROMDATE = '{from_date}'", content)
    modified = re.sub(r"TODATE = '[^']+'", f"TODATE = '{to_date}'", modified)
    modified = re.sub(r"EXPORT_TRADE_REPORTS = True", "EXPORT_TRADE_REPORTS = False", modified)
    modified = re.sub(r"ENABLE_PLOT = True", "ENABLE_PLOT = False", modified)
    
    # Write temp file
    temp_file = Path(__file__).parent / '_temp_robustness_usdcad.py'
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(modified)
    
    try:
        result = subprocess.run(
            [sys.executable, str(temp_file)],
            capture_output=True,
            text=True,
            timeout=180
        )
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return {'error': 'Timeout'}
    except Exception as e:
        return {'error': str(e)}
    finally:
        temp_file.unlink(missing_ok=True)
    
    return parse_output(output)


def parse_output(output: str) -> dict:
    """Parse backtest output for metrics."""
    result = {
        'trades': 0, 'win_rate': 0.0, 'pf': 0.0,
        'pnl': 0.0, 'max_dd': 0.0, 'yearly': {}
    }
    
    # Total Trades
    match = re.search(r'Total Trades:\s*(\d+)', output)
    if match:
        result['trades'] = int(match.group(1))
    
    # Win Rate
    match = re.search(r'Win Rate:\s*([\d.]+)%', output)
    if match:
        result['win_rate'] = float(match.group(1))
    
    # Profit Factor
    match = re.search(r'Profit Factor:\s*([\d.]+)', output)
    if match:
        result['pf'] = float(match.group(1))
    
    # Net P&L
    match = re.search(r'Net P&L:\s*\$([\d,.-]+)', output)
    if match:
        result['pnl'] = float(match.group(1).replace(',', ''))
    
    # Max Drawdown
    match = re.search(r'Max Drawdown:\s*([\d.]+)%', output)
    if match:
        result['max_dd'] = float(match.group(1))
    
    # Parse yearly stats
    year_pattern = r'(\d{4})\s+(\d+)\s+([\d.]+)%\s+([\d.]+)\s+\$\s*([\d,.-]+)'
    for match in re.finditer(year_pattern, output):
        year = int(match.group(1))
        result['yearly'][year] = {
            'trades': int(match.group(2)),
            'wr': float(match.group(3)),
            'pf': float(match.group(4)),
            'pnl': float(match.group(5).replace(',', ''))
        }
    
    return result


def get_status(pf: float, trades: int) -> str:
    """Determine pass/fail status."""
    if trades < 5:
        return '⚠️ LOW'
    elif pf >= 1.2:
        return '✅ PASS'
    elif pf >= 1.0:
        return '⚠️ MARG'
    else:
        return '❌ FAIL'


def main():
    print("=" * 100)
    print("KOI USDCAD ROBUSTNESS TEST - 10 Date Ranges")
    print("=" * 100)
    
    print(f"\n📊 BASELINE (Full 5Y): {BASELINE['period']}")
    print(f"   Trades: {BASELINE['trades']} | WR: {BASELINE['win_rate']:.1f}% | "
          f"PF: {BASELINE['pf']:.2f} | PnL: ${BASELINE['pnl']:,} | DD: {BASELINE['max_dd']:.2f}%")
    
    print("\n" + "-" * 100)
    print("YEARLY BREAKDOWN (from Baseline)")
    print("-" * 100)
    print(f"{'Year':<6} {'Trades':>7} {'WR%':>7} {'PF':>7} {'PnL':>12}")
    for year, stats in sorted(BASELINE['yearly'].items()):
        print(f"{year:<6} {stats['trades']:>7} {stats['wr']:>6.1f}% {stats['pf']:>7.2f} ${stats['pnl']:>10,}")
    
    print("\n" + "=" * 100)
    print("ROBUSTNESS TESTS (10 Periods)")
    print("=" * 100)
    print(f"{'#':<3} {'Period':<18} {'Desc':<15} {'T':>5} {'WR%':>7} {'PF':>7} "
          f"{'PnL':>12} {'DD%':>7} {'Status':<10}")
    print("-" * 100)
    
    results = []
    
    for period in TEST_PERIODS:
        print(f"Testing {period['name']}...", end='', flush=True)
        
        try:
            raw = run_backtest(period['from'], period['to'])
            
            if raw.get('error'):
                print(f"\r{period['id']:<3} {period['name']:<18} ERROR: {raw['error'][:30]}")
                results.append({'id': period['id'], 'name': period['name'], 'status': '❌ ERR', 'pf': 0, 'trades': 0})
                continue
            
            # Extract relevant period data
            if period.get('direct'):
                # Use full run stats
                result = {
                    'trades': raw['trades'],
                    'win_rate': raw['win_rate'],
                    'pf': raw['pf'],
                    'pnl': raw['pnl'],
                    'max_dd': raw['max_dd'],
                }
            elif period.get('filter_year'):
                # Extract single year from yearly stats
                year = period['filter_year']
                if year in raw['yearly']:
                    y = raw['yearly'][year]
                    result = {
                        'trades': y['trades'],
                        'win_rate': y['wr'],
                        'pf': y['pf'],
                        'pnl': y['pnl'],
                        'max_dd': raw['max_dd'],  # Use overall DD
                    }
                else:
                    result = {'trades': 0, 'win_rate': 0, 'pf': 0, 'pnl': 0, 'max_dd': 0}
            elif period.get('filter_years'):
                # Sum multiple years
                years = period['filter_years']
                trades = sum(raw['yearly'].get(y, {}).get('trades', 0) for y in years)
                pnl = sum(raw['yearly'].get(y, {}).get('pnl', 0) for y in years)
                # Approximate PF from yearly
                gross_p = sum(raw['yearly'].get(y, {}).get('pnl', 0) for y in years if raw['yearly'].get(y, {}).get('pnl', 0) > 0)
                gross_l = abs(sum(raw['yearly'].get(y, {}).get('pnl', 0) for y in years if raw['yearly'].get(y, {}).get('pnl', 0) < 0))
                pf = (gross_p / gross_l) if gross_l > 0 else raw['pf']
                wr = sum(raw['yearly'].get(y, {}).get('wr', 0) * raw['yearly'].get(y, {}).get('trades', 0) for y in years)
                wr = wr / trades if trades > 0 else 0
                result = {
                    'trades': trades,
                    'win_rate': wr,
                    'pf': pf if pf < 99 else raw['pf'],
                    'pnl': pnl,
                    'max_dd': raw['max_dd'],
                }
            elif period.get('filter_start'):
                # Use overall stats (approximation for mid-year start)
                result = {
                    'trades': raw['trades'] - BASELINE['yearly'].get(2020, {}).get('trades', 0) // 2,
                    'win_rate': raw['win_rate'],
                    'pf': raw['pf'],
                    'pnl': raw['pnl'],
                    'max_dd': raw['max_dd'],
                }
            else:
                result = raw
            
            result['id'] = period['id']
            result['name'] = period['name']
            result['desc'] = period['desc']
            result['status'] = get_status(result['pf'], result['trades'])
            results.append(result)
            
            print(f"\r{period['id']:<3} {period['name']:<18} {period['desc']:<15} "
                  f"{result['trades']:>5} {result['win_rate']:>6.1f}% {result['pf']:>7.2f} "
                  f"${result['pnl']:>10,.0f} {result['max_dd']:>6.2f}% {result['status']:<10}")
            
        except Exception as e:
            print(f"\r{period['id']:<3} {period['name']:<18} ERROR: {str(e)[:30]}")
            results.append({'id': period['id'], 'name': period['name'], 'status': '❌ ERR', 'pf': 0, 'trades': 0})
    
    # Summary
    print("\n" + "=" * 100)
    print("ROBUSTNESS ANALYSIS SUMMARY")
    print("=" * 100)
    
    valid = [r for r in results if r.get('trades', 0) >= 5]
    passed = [r for r in valid if '✅' in r['status']]
    marginal = [r for r in valid if 'MARG' in r['status']]
    failed = [r for r in valid if '❌' in r['status'] and 'ERR' not in r['status']]
    
    print(f"\nValid tests: {len(valid)}/10")
    print(f"  ✅ PASSED (PF >= 1.2): {len(passed)} ({len(passed)/max(1,len(valid))*100:.0f}%)")
    print(f"  ⚠️ MARGINAL (PF 1.0-1.2): {len(marginal)} ({len(marginal)/max(1,len(valid))*100:.0f}%)")
    print(f"  ❌ FAILED (PF < 1.0): {len(failed)} ({len(failed)/max(1,len(valid))*100:.0f}%)")
    
    # Criteria check
    print("\n" + "-" * 60)
    print("CRITERIA CHECK")
    print("-" * 60)
    
    # 1. PF > 1.2 in 70%+ tests
    pf_pass_rate = len(passed) / max(1, len(valid)) * 100
    pf_check = "✅" if pf_pass_rate >= 70 else "❌"
    print(f"{pf_check} PF > 1.2 in 70%+ tests: {pf_pass_rate:.0f}%")
    
    # 2. WR > 20% in all tests (lower for trend-following)
    wr_all_pass = all(r.get('win_rate', 0) > 20 for r in valid)
    wr_check = "✅" if wr_all_pass else "❌"
    print(f"{wr_check} WR > 20% in all tests: {'YES' if wr_all_pass else 'NO'}")
    
    # 3. Max DD < 25% in all tests
    dd_all_pass = all(r.get('max_dd', 100) < 25 for r in valid)
    dd_check = "✅" if dd_all_pass else "❌"
    print(f"{dd_check} Max DD < 25% in all tests: {'YES' if dd_all_pass else 'NO'}")
    
    # 4. Positive PnL in 60%+ tests
    positive_pnl = [r for r in valid if r.get('pnl', 0) > 0]
    pnl_rate = len(positive_pnl) / max(1, len(valid)) * 100
    pnl_check = "✅" if pnl_rate >= 60 else "❌"
    print(f"{pnl_check} Positive PnL in 60%+ tests: {pnl_rate:.0f}%")
    
    # Final verdict
    checks_passed = sum([pf_pass_rate >= 70, wr_all_pass, dd_all_pass, pnl_rate >= 60])
    
    print("\n" + "=" * 60)
    if checks_passed >= 4:
        print("🏆 VERDICT: EXCELLENT ROBUSTNESS (4/4 criteria)")
    elif checks_passed >= 3:
        print("✅ VERDICT: GOOD ROBUSTNESS (3/4 criteria)")
    elif checks_passed >= 2:
        print("⚠️ VERDICT: MARGINAL ROBUSTNESS (2/4 criteria)")
    else:
        print("❌ VERDICT: POOR ROBUSTNESS - May be overfit")
    print("=" * 60)
    
    # Key findings
    if valid:
        best = max(valid, key=lambda x: x.get('pf', 0))
        worst = min(valid, key=lambda x: x.get('pf', 99))
        print(f"\nBest period:  {best['name']} (PF {best['pf']:.2f})")
        print(f"Worst period: {worst['name']} (PF {worst['pf']:.2f})")


if __name__ == '__main__':
    main()
