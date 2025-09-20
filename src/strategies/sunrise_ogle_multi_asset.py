"""Hexa Asset Strategy - Multi-Asset Trading Portfolio System
==========================================================
Hexa Cerebro Implementation using SunriseOgle strategies

This system runs six separate cerebro instances with the following assets:
1. EURUSD using sunrise_ogle_eurusd.py strategy  
2. USDCHF using sunrise_ogle_usdchf.py strategy
3. XAUUSD using sunrise_ogle_xauusd.py strategy
4. XAGUSD using sunrise_ogle_xagusd.py strategy
5. GBPUSD using sunrise_ogle_gbpusd.py strategy
6. AUDUSD using sunrise_ogle_audusd.py strategy

Each asset runs independently with its own optimized parameters,
with equal 16.67% portfolio allocation per asset, then results are 
aggregated for comprehensive portfolio-level reporting.

Features:
- Multi-asset diversification across major forex pairs, gold, and silver
- Independent strategy optimization for each asset
- Portfolio-level risk and performance aggregation
- Interactive Backtrader charts with mouse hover functionality
- Comprehensive trade reporting and analytics

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
from sunrise_ogle_eurusd import SunriseOgle as SunriseOgleEURUSD
from sunrise_ogle_usdchf import SunriseOgle as SunriseOgleUSDCHF
from sunrise_ogle_xauusd import SunriseOgle as SunriseOgleXAUUSD
from sunrise_ogle_xagusd import SunriseOgle as SunriseOgleXAGUSD
from sunrise_ogle_gbpusd import SunriseOgle as SunriseOgleGBPUSD
from sunrise_ogle_audusd import SunriseOgle as SunriseOgleAUDUSD

# =============================================================
# CONFIGURATION PARAMETERS
# =============================================================

# === BACKTEST SETTINGS ===
FROMDATE = '2020-07-10'               
TODATE = '2025-07-25'                 
STARTING_CASH = 100000  # Adjusted for 6 assets at 16.67% each to achieve $100K total
ENABLE_PLOT = True                    

# === ASSET ALLOCATION ===
# Optimized for Ray Dalio's 4 Economic Environments
# Enhanced allocation to deflation-hedge assets (USDCHF, XAUUSD)
DEFAULT_ALLOCATION = 0.1667  # Base allocation for balanced assets

# Enhanced allocations for economic environment coverage (Total = 100%):
DEFLATION_HEDGE_ALLOCATION = 0.20    # Higher allocation for USD/CHF (deflation hedge)
INFLATION_HEDGE_ALLOCATION = 0.18    # Solid allocation for Gold (inflation hedge) 
STANDARD_ALLOCATION = 0.16          # Standard allocation for major forex pairs
COMMODITY_ALLOCATION = 0.15         # Moderate allocation for commodity-sensitive assets

# === TEMP REPORTS DIRECTORY ===
TEMP_REPORTS_DIR = BASE_DIR.parent.parent / 'temp_reports'

# === ASSET CONFIGURATION ===
ASSETS = {
    'EURUSD': {
        'data_file': 'EURUSD_5m_5Yea.csv',  # Fixed to match sunrise_ogle_long_only.py
        'strategy_class': SunriseOgleEURUSD,  # Using sunrise_ogle_long_only.py (newest, cleanest LONG-only)
        'forex_instrument': 'EURUSD',
        'allocation': STANDARD_ALLOCATION  # 16% - Balanced developed market exposure
    },
    'USDCHF': {
        'data_file': 'USDCHF_5m_5Yea.csv', 
        'strategy_class': SunriseOgleUSDCHF,  # Using sunrise_ogle_usdchf.py
        'forex_instrument': 'USDCHF',
        'allocation': DEFLATION_HEDGE_ALLOCATION  # 20% - Enhanced deflation protection (CHF safe haven)
    },
    'XAUUSD': {
        'data_file': 'XAUUSD_5m_5Yea.csv',  # Gold data file
        'strategy_class': SunriseOgleXAUUSD,  # Using sunrise_ogle_xauusd.py
        'forex_instrument': 'XAUUSD',
        'allocation': INFLATION_HEDGE_ALLOCATION  # 18% - Strong inflation hedge
    },
    'XAGUSD': {
        'data_file': 'XAGUSD_5m_5Yea.csv',  # Silver data file
        'strategy_class': SunriseOgleXAGUSD,  # Using sunrise_ogle_xagusd.py
        'forex_instrument': 'XAGUSD',
        'allocation': COMMODITY_ALLOCATION  # 15% - Moderate commodity exposure
    },
    'GBPUSD': {
        'data_file': 'GBPUSD_5m_5Yea.csv',  # British Pound data file
        'strategy_class': SunriseOgleGBPUSD,  # Using sunrise_ogle_gbpusd.py
        'forex_instrument': 'GBPUSD',
        'allocation': STANDARD_ALLOCATION  # 16% - Balanced developed market exposure
    },
    'AUDUSD': {
        'data_file': 'AUDUSD_5m_5Yea.csv',  # Australian Dollar data file
        'strategy_class': SunriseOgleAUDUSD,  # Using sunrise_ogle_audusd.py
        'forex_instrument': 'AUDUSD',
        'allocation': COMMODITY_ALLOCATION  # 15% - Moderate commodity currency exposure
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
    
    # Calculate custom Sharpe ratio using the same method as individual strategy
    custom_sharpe = 0.0
    if hasattr(strategy_result, '_portfolio_values') and len(strategy_result._portfolio_values) > 10:
        import numpy as np
        returns = []
        for i in range(1, len(strategy_result._portfolio_values)):
            ret = (strategy_result._portfolio_values[i] - strategy_result._portfolio_values[i-1]) / strategy_result._portfolio_values[i-1]
            returns.append(ret)
        
        if len(returns) > 0:
            returns_array = np.array(returns)
            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array)
            # Annualized Sharpe (assuming 5-minute data, 252 trading days)
            periods_per_year = 252 * 24 * 12  # 5-minute periods per year
            custom_sharpe = (mean_return * periods_per_year) / (std_return * np.sqrt(periods_per_year)) if std_return > 0 else 0.0
    
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
        'sharpe_ratio': custom_sharpe,  # Use custom calculation like individual strategy
        'backtrader_sharpe': sharpe_analyzer.get('sharperatio', 0),  # Keep for reference
        'profit_factor': profit_factor,
        'data': data
    }

def aggregate_portfolio_results(results_list):
    """Aggregate results from multiple asset backtests"""
    print(f"\n" + "="*80)
    print(f"📊 HEXA CEREBRO PORTFOLIO AGGREGATION")
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
    """Create two separate interactive portfolio performance charts with mouse hover functionality"""
    if not ENABLE_PLOT:
        return
        
    print(f"\n📈 Creating interactive portfolio performance charts...")
    
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
        
        # Calculate combined portfolio data
        combined_total = []
        combined_timestamps = []
        if len(portfolio_data) >= 2:
            assets = list(portfolio_data.keys())
            min_length = min(len(portfolio_data[asset]['values']) for asset in assets)
            combined_timestamps = portfolio_data[assets[0]]['timestamps'][:min_length]
            
            for i in range(min_length):
                total_val = sum(portfolio_data[asset]['values'][i] for asset in assets)
                combined_total.append(total_val)
        
        colors = {'EURUSD': '#2E86AB', 'USDCHF': '#A23B72', 'XAUUSD': '#F18F01', 'XAGUSD': '#C73E1D', 'GBPUSD': '#5A7C3E'}
        
        # =================================================================
        # CHART 1: COMBINED PORTFOLIO PERFORMANCE ONLY
        # =================================================================
        print(f"  📊 Chart 1: Combined Portfolio Performance")
        fig1, ax1 = plt.subplots(figsize=(16, 8))
        
        if combined_total and combined_timestamps:
            # Calculate combined performance for title
            combined_initial = sum(data['initial_value'] for data in portfolio_data.values())
            combined_final = combined_total[-1] if combined_total else combined_initial
            combined_pnl_pct = ((combined_final - combined_initial) / combined_initial) * 100
            
            # Plot combined portfolio
            combined_line, = ax1.plot(combined_timestamps, combined_total,
                                     label=f'Combined Portfolio ({combined_pnl_pct:+.1f}%)',
                                     color='#1f77b4',  # Professional blue
                                     linewidth=4,
                                     alpha=0.9,
                                     marker='o',
                                     markersize=2)
            
            # Set titles and formatting for Chart 1
            fig1.suptitle('Combined Multi-Asset Portfolio Performance', 
                         fontsize=18, fontweight='bold', y=0.95)
            ax1.set_title(f'Total Return: {combined_pnl_pct:+.2f}% | Initial: ${combined_initial:,.0f} | Final: ${combined_final:,.0f}', 
                         fontsize=14, pad=20)
            
            # Format Chart 1
            ax1.set_xlabel('Date', fontsize=12, fontweight='bold')
            ax1.set_ylabel('Portfolio Value ($)', fontsize=12, fontweight='bold')
            ax1.legend(loc='upper left', fontsize=12, framealpha=0.95)
            ax1.grid(True, alpha=0.3, linestyle='--')
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
            ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
            
            # Interactive hover for Chart 1
            interactive_text1 = None
            def on_hover1(event):
                nonlocal interactive_text1
                if event.inaxes == ax1:
                    if event.xdata and event.ydata:
                        if interactive_text1:
                            interactive_text1.remove()
                        date_str = mdates.num2date(event.xdata).strftime('%Y-%m-%d %H:%M')
                        value_str = f'${event.ydata:,.0f}'
                        interactive_text1 = fig1.text(0.5, 0.85, f'Date: {date_str} | Value: {value_str}', 
                                                     fontsize=14, fontweight='bold', ha='center', va='top',
                                                     bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.8))
                        fig1.canvas.draw_idle()
                else:
                    if interactive_text1:
                        interactive_text1.remove()
                        interactive_text1 = None
                        fig1.canvas.draw_idle()
            
            fig1.canvas.mpl_connect('motion_notify_event', on_hover1)
            plt.tight_layout()
        
        # =================================================================
        # CHART 2: ALL INDIVIDUAL ASSET PORTFOLIOS
        # =================================================================
        print(f"  📊 Chart 2: Individual Asset Portfolios")
        fig2, ax2 = plt.subplots(figsize=(16, 10))
        
        # Calculate performance data for title
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
        performance_title = " | ".join(title_parts)
        
        # Set titles for Chart 2
        fig2.suptitle('Individual Asset Portfolio Performance', 
                     fontsize=18, fontweight='bold', y=0.95)
        ax2.set_title(performance_title, fontsize=12, pad=20)
        
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
            
            line, = ax2.plot(timestamps, values, 
                           label=legend_label, 
                           color=colors.get(asset, '#333333'),
                           linewidth=2.5,
                           alpha=0.8,
                           marker='o',
                           markersize=1)
            lines[asset] = line
        
        # Format Chart 2 for interactivity
        ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Portfolio Value ($)', fontsize=12, fontweight='bold')
        
        # Position legend in the upper left
        legend = ax2.legend(loc='upper left', fontsize=12, framealpha=0.95, 
                          fancybox=True, shadow=True, 
                          borderpad=1.2, handlelength=2)
        
        ax2.grid(True, alpha=0.3, linestyle='--')
        
        # Format x-axis dates for better readability - MONTHLY intervals
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))  # Every 2 months for 5-year span
        
        # Rotate x-axis labels for better readability
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Format y-axis as currency
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        # Enable interactive features for Chart 2
        plt.subplots_adjust(bottom=0.15, top=0.85)
        
        # Create mouse hover functionality for Chart 2
        interactive_text2 = None
        
        def on_hover2(event):
            nonlocal interactive_text2
            if event.inaxes == ax2:
                # Find closest data point
                if event.xdata and event.ydata:
                    # Remove previous interactive text
                    if interactive_text2:
                        interactive_text2.remove()
                    
                    # Update interactive data
                    date_str = mdates.num2date(event.xdata).strftime('%Y-%m-%d %H:%M')
                    value_str = f'${event.ydata:,.0f}'
                    
                    # Display interactive data
                    interactive_text2 = fig2.text(0.5, 0.85, f'Date: {date_str} | Value: {value_str}', 
                                              fontsize=14, fontweight='bold', ha='center', va='top',
                                              bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.8))
                    fig2.canvas.draw_idle()
            else:
                # Remove interactive text when mouse leaves the plot area
                if interactive_text2:
                    interactive_text2.remove()
                    interactive_text2 = None
                    fig2.canvas.draw_idle()
        
        fig2.canvas.mpl_connect('motion_notify_event', on_hover2)
        
        plt.tight_layout()
        plt.show()
        print(f"  ✅ Two interactive portfolio charts displayed successfully!")
        print(f"  � Chart 1: Combined portfolio performance only")
        print(f"  📊 Chart 2: Individual asset portfolios comparison")
        print(f"  �💡 Move your mouse over the charts to see detailed data points")
        
    except Exception as e:
        print(f"  ❌ Error creating portfolio charts: {e}")
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
    print(f"🤖 HEXA CEREBRO MULTI-ASSET BACKTEST")
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
        # Temporary trade reports - use global TEMP_REPORTS_DIR
        str(TEMP_REPORTS_DIR / '*.txt'),
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
    if TEMP_REPORTS_DIR.exists() and not any(TEMP_REPORTS_DIR.iterdir()):
        TEMP_REPORTS_DIR.rmdir()
        print(f"  Removed empty directory: {TEMP_REPORTS_DIR.name}")
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