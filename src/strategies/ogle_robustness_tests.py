"""OGLE Robustness Testing - Multiple Date Ranges
================================================
Tests the strategy across different time periods to validate
that performance is not dependent on specific market conditions.

Tests:
1. Full period: 2019-07-01 to 2025-07-01 (6 years)
2. Recent 4Y: 2021-07-01 to 2025-07-01
3. Recent 3Y: 2022-07-01 to 2025-07-01
4. Middle period: 2020-01-01 to 2024-01-01
5. Pre-2024: 2019-07-01 to 2024-01-01
6. Post-COVID: 2021-01-01 to 2025-01-01
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the strategy module dynamically
import importlib.util

def run_backtest(fromdate: str, todate: str, test_name: str):
    """Run a single backtest with specified dates."""
    
    # We need to modify the module's global variables before importing
    import sunrise_ogle_template as ogle
    
    # Store original values
    orig_fromdate = ogle.FROMDATE
    orig_todate = ogle.TODATE
    orig_verbose = ogle.VERBOSE_DEBUG
    orig_plot = ogle.ENABLE_PLOT
    orig_export = ogle.EXPORT_TRADE_REPORTS
    
    # Set new values
    ogle.FROMDATE = fromdate
    ogle.TODATE = todate
    ogle.VERBOSE_DEBUG = False
    ogle.ENABLE_PLOT = False
    ogle.EXPORT_TRADE_REPORTS = False
    
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"Period: {fromdate} to {todate}")
    print(f"{'='*70}")
    
    try:
        # Run the backtest
        import backtrader as bt
        from datetime import datetime
        
        cerebro = bt.Cerebro()
        cerebro.addstrategy(ogle.SunriseOgle)
        
        # Load data
        data_path = ogle.find_data_file(ogle.DATA_FILENAME)
        if not data_path:
            print(f"ERROR: Data file not found")
            return None
            
        data = bt.feeds.GenericCSVData(
            dataname=data_path,
            dtformat='%Y-%m-%d %H:%M:%S',
            datetime=0, open=1, high=2, low=3, close=4, volume=5,
            fromdate=datetime.strptime(fromdate, '%Y-%m-%d'),
            todate=datetime.strptime(todate, '%Y-%m-%d'),
            timeframe=bt.TimeFrame.Minutes,
            compression=5
        )
        cerebro.adddata(data)
        
        # Broker settings
        cerebro.broker.setcash(ogle.STARTING_CASH)
        
        if ogle.USE_FIXED_COMMISSION:
            is_jpy = 'JPY' in ogle.FOREX_INSTRUMENT
            commission = ogle.ForexCommission(
                commission=ogle.COMMISSION_PER_LOT_PER_ORDER,
                is_jpy_pair=is_jpy,
                jpy_rate=150.0 if is_jpy else 1.0
            )
            cerebro.broker.addcommissioninfo(commission)
        
        # Analyzers
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        
        # Run
        results = cerebro.run()
        strat = results[0]
        
        # Extract metrics
        trade_analysis = strat.analyzers.trades.get_analysis()
        dd_analysis = strat.analyzers.drawdown.get_analysis()
        
        total_trades = trade_analysis.get('total', {}).get('total', 0)
        won = trade_analysis.get('won', {}).get('total', 0)
        lost = trade_analysis.get('lost', {}).get('total', 0)
        
        gross_profit = trade_analysis.get('won', {}).get('pnl', {}).get('total', 0)
        gross_loss = abs(trade_analysis.get('lost', {}).get('pnl', {}).get('total', 0))
        
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        wr = (won / total_trades * 100) if total_trades > 0 else 0
        net_pnl = gross_profit - gross_loss
        max_dd = dd_analysis.get('max', {}).get('drawdown', 0)
        
        final_value = cerebro.broker.getvalue()
        
        result = {
            'test_name': test_name,
            'period': f"{fromdate} to {todate}",
            'trades': total_trades,
            'wins': won,
            'losses': lost,
            'win_rate': wr,
            'profit_factor': pf,
            'net_pnl': net_pnl,
            'max_dd': max_dd,
            'final_value': final_value
        }
        
        print(f"Trades: {total_trades} | WR: {wr:.1f}% | PF: {pf:.2f} | PnL: ${net_pnl:,.0f} | MaxDD: {max_dd:.2f}%")
        
        return result
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Restore original values
        ogle.FROMDATE = orig_fromdate
        ogle.TODATE = orig_todate
        ogle.VERBOSE_DEBUG = orig_verbose
        ogle.ENABLE_PLOT = orig_plot
        ogle.EXPORT_TRADE_REPORTS = orig_export


def main():
    """Run all robustness tests."""
    
    print("="*70)
    print("OGLE ROBUSTNESS TESTING - MULTIPLE DATE RANGES")
    print("="*70)
    
    # Define test configurations
    tests = [
        ('2019-07-01', '2025-07-01', '6Y Full Period'),
        ('2021-07-01', '2025-07-01', '4Y Recent'),
        ('2022-07-01', '2025-07-01', '3Y Recent'),
        ('2020-01-01', '2024-01-01', '4Y Middle (2020-2024)'),
        ('2019-07-01', '2024-01-01', '4.5Y Pre-2024'),
        ('2021-01-01', '2025-01-01', '4Y Post-COVID'),
    ]
    
    results = []
    
    for fromdate, todate, test_name in tests:
        result = run_backtest(fromdate, todate, test_name)
        if result:
            results.append(result)
    
    # Summary table
    print("\n" + "="*70)
    print("ROBUSTNESS SUMMARY")
    print("="*70)
    print(f"{'Test':<25} {'Trades':>7} {'WR%':>7} {'PF':>7} {'PnL':>12} {'MaxDD':>8}")
    print("-"*70)
    
    for r in results:
        print(f"{r['test_name']:<25} {r['trades']:>7} {r['win_rate']:>6.1f}% {r['profit_factor']:>7.2f} ${r['net_pnl']:>10,.0f} {r['max_dd']:>7.2f}%")
    
    # Statistics
    if results:
        pfs = [r['profit_factor'] for r in results]
        wrs = [r['win_rate'] for r in results]
        dds = [r['max_dd'] for r in results]
        
        print("-"*70)
        print(f"{'AVERAGE':<25} {'':<7} {sum(wrs)/len(wrs):>6.1f}% {sum(pfs)/len(pfs):>7.2f} {'':<12} {sum(dds)/len(dds):>7.2f}%")
        print(f"{'MIN':<25} {'':<7} {min(wrs):>6.1f}% {min(pfs):>7.2f} {'':<12} {min(dds):>7.2f}%")
        print(f"{'MAX':<25} {'':<7} {max(wrs):>6.1f}% {max(pfs):>7.2f} {'':<12} {max(dds):>7.2f}%")
        
        # Robustness score
        all_profitable = all(r['profit_factor'] > 1.0 for r in results)
        all_pf_above_1_3 = all(r['profit_factor'] > 1.3 for r in results)
        avg_pf = sum(pfs) / len(pfs)
        max_dd_below_10 = all(r['max_dd'] < 10 for r in results)
        
        print("\n" + "="*70)
        print("ROBUSTNESS VERDICT")
        print("="*70)
        print(f"✓ All periods profitable (PF > 1.0): {'YES ✅' if all_profitable else 'NO ❌'}")
        print(f"✓ All periods PF > 1.3: {'YES ✅' if all_pf_above_1_3 else 'NO ❌'}")
        print(f"✓ Average PF: {avg_pf:.2f} {'✅' if avg_pf > 1.4 else '⚠️'}")
        print(f"✓ Max DD < 10% all periods: {'YES ✅' if max_dd_below_10 else 'NO ❌'}")
        
        if all_profitable and avg_pf > 1.4 and max_dd_below_10:
            print("\n🏆 STRATEGY IS ROBUST - Ready for live testing!")
        elif all_profitable and avg_pf > 1.2:
            print("\n✅ STRATEGY SHOWS GOOD ROBUSTNESS")
        else:
            print("\n⚠️ STRATEGY MAY BE OVERFIT - Review parameters")


if __name__ == '__main__':
    main()
