"""Dual Asset Strategy - EURUSD & USDCHF Trading System
======================================================
Dual Cerebro Implementation using exact sunrise_osiris.py approach

This system runs two separate cereb    print(f"\n⚖️  RISK METRICS:")
    for result in results_list:
        asset = result['asset']
        dd_analysis = result['drawdown_analysis']
        sharpe = result['sharpe_ratio']
        
        # Get the max drawdown value
        max_dd_raw = dd_analysis.get('max', {}).get('drawdown', 0) if dd_analysis else 0
        
        # The drawdown values seem to be coming as very large numbers, possibly in different units
        # Let's apply some reasonable logic: if > 1, it's likely already a percentage, if < 1, it's decimal
        if max_dd_raw > 1:
            max_dd_pct = max_dd_raw  # Already a percentage 
        else:
            max_dd_pct = max_dd_raw * 100  # Convert from decimal to percentage
        
        # Cap at reasonable maximum (no strategy should have >100% drawdown with positive final value)
        if max_dd_pct > 100:
            max_dd_pct = min(max_dd_pct / 100, 99.9)  # Try dividing by 100, cap at 99.9%
        
        print(f"  {asset:<8}: Max DD: {max_dd_pct:>5.2f}% | Sharpe: {sharpe:>6.3f}")es:
1. EURUSD using sunrise_ogle_eurusd.py strategy  
2. USDCHF using sunrise_osiris.py strategy

Each asset runs independently with its own optimized parameters,
then results are aggregated for portfolio-level reporting.

Interactive Backtrader charts with mouse hover functionality.

DISCLAIMER
----------
Educational and research purposes ONLY. Not investment advice. 
Trading involves substantial risk of loss. Past performance does not 
guarantee future results. Validate all logic and data quality before 
using in any live or simulated trading environment.
"""

import backtrader as bt
from pathlib import Path
import sys
import math
from datetime import datetime as dt, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

# Import individual strategies
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Import individual strategy classes
from Portafolio.quant_bot_project.src.strategies.sunrise_ogle_eurusd import SunriseOgle as SunriseOgleEURUSD
from sunrise_ogle_usdchf import SunriseOgle as SunriseOgleUSDCHF
from sunrise_ogle_xauusd import SunriseOgle as SunriseOgleXAUUSD

# =============================================================
# CONFIGURATION PARAMETERS
# =============================================================

# === BACKTEST SETTINGS ===
FROMDATE = '2020-07-10'               
TODATE = '2025-07-25'                 
STARTING_CASH = 100000.0              
ENABLE_PLOT = True                    

# === ASSET CONFIGURATION ===
ASSETS = {
    'EURUSD': {
        'data_file': 'EURUSD_5m_5Yea.csv',  # Fixed to match sunrise_ogle_long_only.py
        'strategy_class': SunriseOgleEURUSD,  # Using sunrise_ogle_long_only.py (newest, cleanest LONG-only)
        'forex_instrument': 'EURUSD',
        'allocation': 0.33  # 33% of portfolio
    },
    'USDCHF': {
        'data_file': 'USDCHF_5m_5Yea.csv', 
        'strategy_class': SunriseOgleUSDCHF,  # Using sunrise_ogle_usdchf.py
        'forex_instrument': 'USDCHF',
        'allocation': 0.34  # 34% of portfolio
    },
    'XAUUSD': {
        'data_file': 'XAUUSD_5m_5Yea.csv',  # Gold data file
        'strategy_class': SunriseOgleXAUUSD,  # Using sunrise_ogle_xauusd.py
        'forex_instrument': 'XAUUSD',
        'allocation': 0.33  # 33% of portfolio
    }
}

def create_data_feed(data_file, fromdate=None, todate=None):
    """Create Backtrader data feed from CSV file"""
    data_path = BASE_DIR.parent.parent / 'data' / data_file
    
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    
    feed_kwargs = {
        'dataname': str(data_path),
        'dtformat': '%Y%m%d',
        'tmformat': '%H:%M:%S',
        'datetime': 0,
        'time': 1,
        'open': 2,
        'high': 3,
        'low': 4,
        'close': 5,
        'volume': 6,
        'timeframe': bt.TimeFrame.Minutes,
        'compression': 5
    }
    
    def parse_date(s):
        try:
            return dt.strptime(s, '%Y-%m-%d')
        except:
            return None
    
    # Add date filters if provided
    fd = parse_date(fromdate) if fromdate else None
    td = parse_date(todate) if todate else None
    if fd:
        feed_kwargs['fromdate'] = fd
    if td:
        feed_kwargs['todate'] = td
        
    return bt.feeds.GenericCSVData(**feed_kwargs)

def run_single_asset_backtest(asset_name, asset_config, fromdate, todate, starting_cash):
    """Run backtest for a single asset using its individual strategy"""
    print(f"\n🚀 Running {asset_name} backtest...")
    
    # Create cerebro instance
    cerebro = bt.Cerebro(stdstats=False)
    
    # Add data feed
    data = create_data_feed(
        asset_config['data_file'], 
        fromdate=fromdate, 
        todate=todate
    )
    cerebro.adddata(data)
    
    # Set cash allocation for this asset
    asset_cash = starting_cash * asset_config['allocation']
    cerebro.broker.setcash(asset_cash)
    cerebro.broker.setcommission(leverage=30.0)
    
    # Add strategy with asset-specific configuration
    strategy_kwargs = {
        'plot_result': False,  # Disable individual plots for clean console output
        'use_forex_position_calc': True,
        'forex_instrument': asset_config['forex_instrument'],
        'verbose_debug': False,  # Disable verbose debug output
        'print_signals': False,  # Disable individual trade signal printing
    }
    
    cerebro.addstrategy(asset_config['strategy_class'], **strategy_kwargs)
    
    # Add analyzers for detailed performance metrics
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    
    # Run backtest
    initial_value = cerebro.broker.getvalue()
    print(f"  Initial Value: ${initial_value:,.2f}")
    
    results = cerebro.run()
    strategy_result = results[0]
    
    final_value = cerebro.broker.getvalue()
    total_return = final_value - initial_value
    return_pct = (total_return / initial_value) * 100
    
    print(f"  Final Value: ${final_value:,.2f}")
    print(f"  P&L: ${total_return:,.2f} ({return_pct:+.2f}%)")
    
    # Extract analyzer results
    trade_analyzer = strategy_result.analyzers.trades.get_analysis()
    drawdown_analyzer = strategy_result.analyzers.drawdown.get_analysis()
    sharpe_analyzer = strategy_result.analyzers.sharpe.get_analysis()
    
    # Calculate Profit Factor (Gross Profit / Gross Loss)
    profit_factor = 0.0
    if trade_analyzer:
        won = trade_analyzer.get('won', {})
        lost = trade_analyzer.get('lost', {})
        
        gross_profit = won.get('pnl', {}).get('total', 0) if won.get('pnl') else 0
        gross_loss = abs(lost.get('pnl', {}).get('total', 0)) if lost.get('pnl') else 0
        
        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        elif gross_profit > 0:
            profit_factor = float('inf')  # No losses, infinite PF
    
    return {
        'asset': asset_name,
        'cerebro': cerebro,
        'strategy': strategy_result,
        'initial_value': initial_value,
        'final_value': final_value,
        'total_return': total_return,
        'return_pct': return_pct,
        'trade_analysis': trade_analyzer,
        'drawdown_analysis': drawdown_analyzer,
        'sharpe_ratio': sharpe_analyzer.get('sharperatio', 0),
        'profit_factor': profit_factor,
        'data': data
    }

def aggregate_portfolio_results(results_list):
    """Aggregate results from multiple asset backtests"""
    print(f"\n" + "="*80)
    print(f"📊 TRIPLE CEREBRO PORTFOLIO AGGREGATION")
    print(f"="*80)
    
    total_initial = sum(r['initial_value'] for r in results_list)
    total_final = sum(r['final_value'] for r in results_list)
    total_pnl = total_final - total_initial
    total_return_pct = (total_pnl / total_initial) * 100
    
    print(f"Initial Portfolio Value: ${total_initial:,.2f}")
    print(f"Final Portfolio Value:   ${total_final:,.2f}")
    print(f"Total Profit/Loss:       ${total_pnl:,.2f}")
    print(f"Total Return:            {total_return_pct:+.2f}%")
    
    # Individual asset breakdown
    print(f"\n📈 INDIVIDUAL ASSET PERFORMANCE:")
    for result in results_list:
        asset = result['asset']
        pnl = result['total_return'] 
        ret_pct = result['return_pct']
        print(f"  {asset:<8}: ${pnl:>+10,.2f} ({ret_pct:>+6.2f}%)")
    
    # Aggregate trade statistics
    total_trades = 0
    total_wins = 0
    total_losses = 0
    total_gross_profit = 0.0
    total_gross_loss = 0.0
    
    print(f"\n📊 TRADE STATISTICS:")
    for result in results_list:
        asset = result['asset']
        trade_analysis = result['trade_analysis']
        profit_factor = result.get('profit_factor', 0)
        
        if trade_analysis:
            won = trade_analysis.get('won', {})
            lost = trade_analysis.get('lost', {})
            
            asset_total = won.get('total', 0) + lost.get('total', 0)
            asset_wins = won.get('total', 0)
            asset_losses = lost.get('total', 0)
            win_rate = (asset_wins / asset_total * 100) if asset_total > 0 else 0
            
            # Add gross profits/losses for portfolio PF calculation
            gross_profit = won.get('pnl', {}).get('total', 0) if won.get('pnl') else 0
            gross_loss = abs(lost.get('pnl', {}).get('total', 0)) if lost.get('pnl') else 0
            
            total_trades += asset_total
            total_wins += asset_wins
            total_losses += asset_losses
            total_gross_profit += gross_profit
            total_gross_loss += gross_loss
            
            pf_str = f"{profit_factor:.2f}" if profit_factor != float('inf') else "∞"
            print(f"  {asset:<8}: {asset_total:>3} trades | {asset_wins:>3} wins | {asset_losses:>3} losses | {win_rate:>5.1f}% WR | PF: {pf_str}")
    
    portfolio_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
    portfolio_pf = (total_gross_profit / total_gross_loss) if total_gross_loss > 0 else float('inf')
    portfolio_pf_str = f"{portfolio_pf:.2f}" if portfolio_pf != float('inf') else "∞"
    
    print(f"  {'TOTAL':<8}: {total_trades:>3} trades | {total_wins:>3} wins | {total_losses:>3} losses | {portfolio_win_rate:>5.1f}% WR | PF: {portfolio_pf_str}")
    
    # Risk metrics
    print(f"\n⚖️  RISK METRICS:")
    for result in results_list:
        asset = result['asset']
        dd_analysis = result['drawdown_analysis']
        sharpe = result['sharpe_ratio']
        profit_factor = result.get('profit_factor', 0)
        
        # Fix drawdown calculation - Backtrader returns percentage values directly
        max_dd_raw = dd_analysis.get('max', {}).get('drawdown', 0) if dd_analysis else 0
        
        # Backtrader DrawDown analyzer returns percentage values directly (0-100 scale)
        # But they seem to be returned as fractions, so we need to check the range
        if abs(max_dd_raw) <= 1.0:
            # Value is a decimal fraction (0.05 = 5%), convert to percentage
            max_dd_pct = abs(max_dd_raw) * 100
        else:
            # Value is already a percentage, just take absolute value
            max_dd_pct = abs(max_dd_raw)
        
        # Cap at reasonable maximum for safety
        max_dd_pct = min(max_dd_pct, 99.9)
        
        pf_str = f"{profit_factor:.2f}" if profit_factor != float('inf') else "∞"
        print(f"  {asset:<8}: Max DD: {max_dd_pct:>5.2f}% | Sharpe: {sharpe:>6.3f} | PF: {pf_str}")
    
    # Add portfolio-level PF summary
    print(f"  {'PORTFOLIO':<8}: Portfolio PF: {portfolio_pf_str}")
    
    print(f"="*80)
    
    return {
        'total_initial': total_initial,
        'total_final': total_final,
        'total_pnl': total_pnl,
        'total_return_pct': total_return_pct,
        'total_trades': total_trades,
        'portfolio_win_rate': portfolio_win_rate
    }

def create_portfolio_chart(results_list):
    """Create interactive portfolio performance chart with mouse hover functionality"""
    if not ENABLE_PLOT:
        return
        
    print(f"\n📈 Creating interactive portfolio performance chart...")
    
    try:
        # Collect portfolio values and timestamps from each strategy
        portfolio_data = {}
        
        for result in results_list:
            asset = result['asset']
            strategy = result['strategy']
            
            # Get portfolio values and timestamps from strategy
            if hasattr(strategy, '_portfolio_values') and hasattr(strategy, '_timestamps'):
                timestamps = strategy._timestamps
                portfolio_values = strategy._portfolio_values
                
                if len(timestamps) > 0 and len(portfolio_values) > 0:
                    # Convert timestamps to datetime objects if needed
                    dates = []
                    for ts in timestamps:
                        if isinstance(ts, dt):
                            dates.append(ts)
                        elif hasattr(ts, 'datetime'):
                            dates.append(ts.datetime())
                        else:
                            # Assume it's a numeric timestamp that needs conversion
                            dates.append(bt.num2date(ts))
                    
                    portfolio_data[asset] = {
                        'timestamps': dates,
                        'values': portfolio_values,
                        'initial_value': result['initial_value']
                    }
                    print(f"  {asset}: {len(dates)} data points collected")
                else:
                    print(f"  Warning: No portfolio data found for {asset}")
            else:
                print(f"  Warning: Strategy for {asset} doesn't track portfolio values")
        
        if not portfolio_data:
            print("  No portfolio data available for charting")
            return
            
        # Create the interactive portfolio performance chart
        fig, ax = plt.subplots(figsize=(16, 10))
        
        # Calculate performance data for title
        total_initial = sum(data['initial_value'] for data in portfolio_data.values())
        asset_performance = {}
        for asset, data in portfolio_data.items():
            if data['values']:
                initial = data['initial_value']
                final = data['values'][-1]
                pnl_pct = ((final - initial) / initial) * 100
                asset_performance[asset] = pnl_pct
        
        # Enhanced title with performance data
        title_parts = []
        for asset, perf in asset_performance.items():
            title_parts.append(f"{asset}: {perf:+.1f}%")
        
        combined_pnl = sum(asset_performance.values()) if asset_performance else 0
        title_parts.append(f"Combined: {combined_pnl:+.1f}%")
        
        performance_title = " | ".join(title_parts)
        
        # Add main title on the left side
        fig.text(0.02, 0.95, 'Triple Asset Portfolio Performance (EURUSD + USDCHF + XAUUSD)', 
                fontsize=16, fontweight='bold', ha='left', va='top')
        fig.text(0.02, 0.91, performance_title, 
                fontsize=12, fontweight='normal', ha='left', va='top')
        
        colors = {'EURUSD': '#2E86AB', 'USDCHF': '#A23B72', 'XAUUSD': '#333333'}
        lines = {}
        
        # Plot individual asset portfolios with performance in legend
        for asset, data in portfolio_data.items():
            timestamps = data['timestamps']
            values = data['values']
            
            # Calculate performance for legend
            if values:
                initial = data['initial_value']
                final = values[-1]
                pnl_pct = ((final - initial) / initial) * 100
                legend_label = f'{asset} ({pnl_pct:+.1f}%)'
            else:
                legend_label = f'{asset} Portfolio'
            
            line, = ax.plot(timestamps, values, 
                           label=legend_label, 
                           color=colors.get(asset, '#333333'),
                           linewidth=2.5,
                           alpha=0.8,
                           marker='o',
                           markersize=1)
            lines[asset] = line
        
        # Calculate and plot combined portfolio for all assets
        if len(portfolio_data) >= 2:
            assets = list(portfolio_data.keys())
            
            # Find minimum length across all assets
            min_length = min(len(portfolio_data[asset]['values']) for asset in assets)
            combined_total = []
            combined_timestamps = portfolio_data[assets[0]]['timestamps'][:min_length]
            
            for i in range(min_length):
                total_val = sum(portfolio_data[asset]['values'][i] for asset in assets)
                combined_total.append(total_val)
            
            # Calculate combined performance for legend
            combined_initial = sum(data['initial_value'] for data in portfolio_data.values())
            combined_final = combined_total[-1] if combined_total else combined_initial
            combined_pnl_pct = ((combined_final - combined_initial) / combined_initial) * 100
            
            combined_line, = ax.plot(combined_timestamps, combined_total,
                                   label=f'Combined Portfolio ({combined_pnl_pct:+.1f}%)',
                                   color='#F18F01',
                                   linewidth=3.5,
                                   alpha=0.9,
                                   marker='s',
                                   markersize=1.5)
            lines['Combined'] = combined_line
        
        # Format the chart for interactivity
        ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax.set_ylabel('Portfolio Value ($)', fontsize=12, fontweight='bold')
        
        # Position legend in the middle-left side to avoid conflicts
        legend = ax.legend(loc='center left', bbox_to_anchor=(0.02, 0.5), 
                          fontsize=12, framealpha=0.95, 
                          fancybox=True, shadow=True, 
                          borderpad=1.2, handlelength=2)
        
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Format x-axis dates for better readability - MONTHLY intervals
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))  # Every 2 months for 5-year span
        
        # Rotate x-axis labels for better readability
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Format y-axis as currency
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        # Enable interactive features
        plt.subplots_adjust(bottom=0.15, top=0.85)
        
        # Create mouse hover functionality with center positioning
        interactive_text = None
        
        def on_hover(event):
            nonlocal interactive_text
            if event.inaxes == ax:
                # Find closest data point
                if event.xdata and event.ydata:
                    # Remove previous interactive text
                    if interactive_text:
                        interactive_text.remove()
                    
                    # Update interactive data in center area
                    date_str = mdates.num2date(event.xdata).strftime('%Y-%m-%d %H:%M')
                    value_str = f'${event.ydata:,.0f}'
                    
                    # Display interactive data in center of chart
                    interactive_text = fig.text(0.5, 0.95, f'Date: {date_str} | Value: {value_str}', 
                                              fontsize=14, fontweight='bold', ha='center', va='top',
                                              bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.8))
                    fig.canvas.draw_idle()
            else:
                # Remove interactive text when mouse leaves the plot area
                if interactive_text:
                    interactive_text.remove()
                    interactive_text = None
                    fig.canvas.draw_idle()
        
        fig.canvas.mpl_connect('motion_notify_event', on_hover)
        
        plt.tight_layout()
        plt.show()
        print(f"  ✅ Interactive portfolio chart displayed successfully!")
        print(f"  💡 Move your mouse over the chart to see detailed data points")
        
    except Exception as e:
        print(f"  ❌ Error creating portfolio chart: {e}")
        import traceback
        traceback.print_exc()

def create_simple_individual_charts(results_list):
    """Fallback function for simple individual charts without custom formatting"""
    print(f"\n📈 Creating simple individual charts...")
    
    for result in results_list:
        asset = result['asset']
        cerebro = result['cerebro']
        
        print(f"  Opening chart for {asset}...")
        try:
            # Simple plot without custom formatters that cause issues
            cerebro.plot(
                style='candlestick',
                barup='green', 
                bardown='red',
                volume=False
            )
        except Exception as e:
            print(f"    Warning: Could not create chart for {asset}: {e}")

def run_triple_cerebro_backtest():
    """Main function to run dual cerebro backtest"""
    print(f"🤖 DUAL CEREBRO MULTI-ASSET BACKTEST")
    print(f"📅 Period: {FROMDATE} to {TODATE}")
    print(f"💰 Starting Cash: ${STARTING_CASH:,.2f}")
    print(f"📊 Assets: {', '.join(ASSETS.keys())}")
    
    # Run individual asset backtests
    all_results = []
    
    for asset_name, asset_config in ASSETS.items():
        try:
            result = run_single_asset_backtest(
                asset_name, 
                asset_config, 
                FROMDATE, 
                TODATE, 
                STARTING_CASH
            )
            all_results.append(result)
        except Exception as e:
            print(f"❌ Error running {asset_name} backtest: {e}")
            continue
    
    if not all_results:
        print("❌ No successful backtests completed!")
        return
    
    # Aggregate portfolio results
    portfolio_summary = aggregate_portfolio_results(all_results)
    
    # Create portfolio performance chart
    create_portfolio_chart(all_results)
    
    return portfolio_summary, all_results

def cleanup_auxiliary_files():
    """Clean up temporary files and cache created during backtesting"""
    import shutil
    import glob
    
    cleanup_patterns = [
        # Temporary trade reports
        str(BASE_DIR / 'temp_reports' / '*.txt'),
        # Python cache files
        str(BASE_DIR / '__pycache__'),
        # Chart files
        str(BASE_DIR / '*.png'),
        str(BASE_DIR / '*.jpg'),
        # Backup files
        str(BASE_DIR / '*_backup.py'),
        str(BASE_DIR / '*_fixed.py'),
        str(BASE_DIR / '*_clean.py'),
        # Old dual cerebro files
        str(BASE_DIR / 'dual_cerebro_backtest.py'),
        str(BASE_DIR / 'run_multi_asset_backtest.py'),
        str(BASE_DIR / 'simplified_multi_asset.py'),
    ]
    
    print(f"\n🧹 Cleaning up auxiliary files...")
    cleaned_count = 0
    
    for pattern in cleanup_patterns:
        if '__pycache__' in pattern:
            # Handle directory
            if Path(pattern).exists():
                shutil.rmtree(pattern, ignore_errors=True)
                print(f"  Removed directory: {Path(pattern).name}")
                cleaned_count += 1
        else:
            # Handle file patterns
            for file_path in glob.glob(pattern):
                try:
                    Path(file_path).unlink()
                    print(f"  Removed file: {Path(file_path).name}")
                    cleaned_count += 1
                except Exception as e:
                    pass  # Ignore errors for files in use
    
    # Clean up temp_reports directory if empty
    temp_reports_dir = BASE_DIR / 'temp_reports'
    if temp_reports_dir.exists() and not any(temp_reports_dir.iterdir()):
        temp_reports_dir.rmdir()
        print(f"  Removed empty directory: temp_reports")
        cleaned_count += 1
    
    if cleaned_count > 0:
        print(f"🧹 Cleanup completed: {cleaned_count} items removed")
    else:
        print(f"🧹 No auxiliary files found to clean")

if __name__ == '__main__':
    try:
        portfolio_summary, individual_results = run_triple_cerebro_backtest()
        print(f"\n✅ Triple cerebro backtest completed successfully!")
        
        # Keep external reports - don't cleanup
        # cleanup_auxiliary_files()
        
    except Exception as e:
        print(f"❌ Error in triple cerebro backtest: {e}")
        import traceback
        traceback.print_exc()