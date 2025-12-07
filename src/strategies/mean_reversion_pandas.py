"""Mean Reversion Analyzer - Pandas Version
===========================================
Faster and more accurate analysis using pandas directly.
Analyzes lower band crosses and reversion behavior.

Output: CSV and TXT reports in temp_reports folder.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from collections import defaultdict


# =============================================================================
# CONFIGURATION
# =============================================================================

DATA_FILENAME = 'USDCHF_5m_5Yea.csv'
FROMDATE = '2024-09-01'
TODATE = '2025-11-01'

# Mean Reversion Parameters
EMA_PERIOD = 70
ATR_PERIOD = 14
DEVIATION_MULT = 2.0

# Analysis parameters
MAX_CANDLES_TO_TRACK = 100

# Paths
DATA_DIR = Path(__file__).parent.parent.parent / "data"
EXPORT_DIR = Path(__file__).parent / "temp_reports"


def calculate_atr(df, period=14):
    """Calculate Average True Range."""
    high = df['High']
    low = df['Low']
    close = df['Close'].shift(1)
    
    tr1 = high - low
    tr2 = abs(high - close)
    tr3 = abs(low - close)
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


def analyze_lower_band_crosses(df):
    """
    Analyze all crosses below the lower mean reversion band.
    
    Returns list of cross events with:
    - cross_datetime, cross_hour
    - cross_price, cross_zscore
    - min_zscore (deepest during cross)
    - reversion_datetime, candles_to_revert
    - success (True/False)
    """
    # Calculate indicators
    df = df.copy()
    df['EMA'] = df['Close'].ewm(span=EMA_PERIOD, adjust=False).mean()
    df['ATR'] = calculate_atr(df, ATR_PERIOD)
    df['LowerBand'] = df['EMA'] - (DEVIATION_MULT * df['ATR'])
    df['UpperBand'] = df['EMA'] + (DEVIATION_MULT * df['ATR'])
    df['ZScore'] = (df['Close'] - df['EMA']) / df['ATR']
    
    # Remove NaN rows
    df = df.dropna().reset_index(drop=True)
    
    events = []
    i = 0
    
    while i < len(df) - 1:
        # Check for cross below lower band
        if df.loc[i, 'Close'] < df.loc[i, 'LowerBand']:
            cross_idx = i
            cross_dt = df.loc[i, 'Datetime']
            cross_hour = cross_dt.hour
            cross_price = df.loc[i, 'Close']
            cross_zscore = df.loc[i, 'ZScore']
            min_zscore = cross_zscore
            
            # Track until price returns above lower band or max candles
            candles = 1
            j = i + 1
            
            while j < len(df):
                current_zscore = df.loc[j, 'ZScore']
                if current_zscore < min_zscore:
                    min_zscore = current_zscore
                
                candles += 1
                
                # Check for reversion (price back above lower band)
                if df.loc[j, 'Close'] >= df.loc[j, 'LowerBand']:
                    events.append({
                        'cross_datetime': cross_dt.strftime('%Y-%m-%d %H:%M'),
                        'cross_hour': cross_hour,
                        'cross_price': cross_price,
                        'cross_zscore': cross_zscore,
                        'min_zscore': min_zscore,
                        'reversion_datetime': df.loc[j, 'Datetime'].strftime('%Y-%m-%d %H:%M'),
                        'reversion_price': df.loc[j, 'Close'],
                        'reversion_zscore': current_zscore,
                        'candles_to_revert': candles,
                        'success': True
                    })
                    i = j  # Continue from reversion point
                    break
                
                # Check for timeout
                if candles >= MAX_CANDLES_TO_TRACK:
                    events.append({
                        'cross_datetime': cross_dt.strftime('%Y-%m-%d %H:%M'),
                        'cross_hour': cross_hour,
                        'cross_price': cross_price,
                        'cross_zscore': cross_zscore,
                        'min_zscore': min_zscore,
                        'reversion_datetime': df.loc[j, 'Datetime'].strftime('%Y-%m-%d %H:%M'),
                        'reversion_price': df.loc[j, 'Close'],
                        'reversion_zscore': current_zscore,
                        'candles_to_revert': candles,
                        'success': False
                    })
                    i = j
                    break
                
                j += 1
            else:
                # End of data reached
                i = j
        
        i += 1
    
    return events


def generate_reports(events):
    """Generate CSV and summary reports."""
    EXPORT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # === CSV Export ===
    csv_path = EXPORT_DIR / f"mean_reversion_pandas_{timestamp}.csv"
    df_events = pd.DataFrame(events)
    df_events.to_csv(csv_path, index=False)
    print(f"\nDetailed CSV: {csv_path}")
    
    # === Summary Report ===
    report_path = EXPORT_DIR / f"mean_reversion_summary_pandas_{timestamp}.txt"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("MEAN REVERSION ANALYSIS - LOWER BAND CROSSES (Pandas)\n")
        f.write("=" * 70 + "\n\n")
        
        f.write(f"Data: {DATA_FILENAME}\n")
        f.write(f"Period: {FROMDATE} to {TODATE}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("PARAMETERS:\n")
        f.write("-" * 40 + "\n")
        f.write(f"EMA Period: {EMA_PERIOD}\n")
        f.write(f"ATR Period: {ATR_PERIOD}\n")
        f.write(f"Deviation Multiplier: {DEVIATION_MULT}\n")
        f.write(f"Max Candles to Track: {MAX_CANDLES_TO_TRACK}\n\n")
        
        # Overall statistics
        total = len(events)
        successful = sum(1 for e in events if e['success'])
        failed = total - successful
        success_rate = (successful / total * 100) if total > 0 else 0
        
        f.write("=" * 70 + "\n")
        f.write("OVERALL STATISTICS\n")
        f.write("=" * 70 + "\n\n")
        
        f.write(f"Total Lower Band Crosses: {total}\n")
        f.write(f"Successful Reversions: {successful}\n")
        f.write(f"Failed Reversions (>{MAX_CANDLES_TO_TRACK} candles): {failed}\n")
        f.write(f"Success Rate: {success_rate:.1f}%\n\n")
        
        # Reversion time statistics (successful only)
        successful_events = [e for e in events if e['success']]
        
        if successful_events:
            candle_times = [e['candles_to_revert'] for e in successful_events]
            
            f.write("=" * 70 + "\n")
            f.write("REVERSION TIME STATISTICS (Successful Only)\n")
            f.write("=" * 70 + "\n\n")
            
            avg_candles = np.mean(candle_times)
            median_candles = np.median(candle_times)
            min_candles = min(candle_times)
            max_candles = max(candle_times)
            
            f.write(f"Average Candles to Revert: {avg_candles:.1f}\n")
            f.write(f"Median Candles to Revert: {median_candles:.1f}\n")
            f.write(f"Min Candles: {min_candles}\n")
            f.write(f"Max Candles: {max_candles}\n\n")
            
            # Distribution
            f.write("DISTRIBUTION (Candles to Revert):\n")
            f.write("-" * 40 + "\n")
            
            buckets = {'1-5': 0, '6-10': 0, '11-15': 0, '16-20': 0, 
                      '21-30': 0, '31-50': 0, '51+': 0}
            
            for t in candle_times:
                if t <= 5: buckets['1-5'] += 1
                elif t <= 10: buckets['6-10'] += 1
                elif t <= 15: buckets['11-15'] += 1
                elif t <= 20: buckets['16-20'] += 1
                elif t <= 30: buckets['21-30'] += 1
                elif t <= 50: buckets['31-50'] += 1
                else: buckets['51+'] += 1
            
            for bucket, count in buckets.items():
                pct = (count / len(candle_times)) * 100
                bar = '█' * int(pct / 2)
                f.write(f"{bucket:>8} candles: {count:>4} ({pct:>5.1f}%) {bar}\n")
            
            # Z-Score analysis
            f.write("\n" + "=" * 70 + "\n")
            f.write("Z-SCORE DEPTH ANALYSIS\n")
            f.write("=" * 70 + "\n\n")
            
            min_zscores = [e['min_zscore'] for e in successful_events]
            f.write(f"Average Min Z-Score Reached: {np.mean(min_zscores):.2f}\n")
            f.write(f"Deepest Z-Score: {min(min_zscores):.2f}\n\n")
            
            f.write("Z-Score Depth vs Reversion Time:\n")
            f.write("-" * 40 + "\n")
            
            zscore_groups = {
                'Z < -3.0 (very deep)': [],
                '-3.0 <= Z < -2.5': [],
                '-2.5 <= Z < -2.0': [],
                'Z >= -2.0 (shallow)': [],
            }
            
            for e in successful_events:
                z = e['min_zscore']
                if z < -3.0: zscore_groups['Z < -3.0 (very deep)'].append(e['candles_to_revert'])
                elif z < -2.5: zscore_groups['-3.0 <= Z < -2.5'].append(e['candles_to_revert'])
                elif z < -2.0: zscore_groups['-2.5 <= Z < -2.0'].append(e['candles_to_revert'])
                else: zscore_groups['Z >= -2.0 (shallow)'].append(e['candles_to_revert'])
            
            for group_name, times in zscore_groups.items():
                if times:
                    f.write(f"{group_name}: {len(times)} events, avg {np.mean(times):.1f} candles\n")
                else:
                    f.write(f"{group_name}: 0 events\n")
        
        # HOUR OF DAY ANALYSIS
        f.write("\n" + "=" * 70 + "\n")
        f.write("HOUR OF DAY ANALYSIS\n")
        f.write("=" * 70 + "\n\n")
        
        hour_stats = defaultdict(lambda: {'count': 0, 'success': 0, 'candles': []})
        
        for e in events:
            hour = e['cross_hour']
            hour_stats[hour]['count'] += 1
            if e['success']:
                hour_stats[hour]['success'] += 1
                hour_stats[hour]['candles'].append(e['candles_to_revert'])
        
        f.write("Hour  | Crosses | Success% | Avg Candles | Best Hours\n")
        f.write("-" * 60 + "\n")
        
        hour_data = []
        for hour in range(24):
            stats = hour_stats.get(hour, {'count': 0, 'success': 0, 'candles': []})
            count = stats['count']
            if count > 0:
                success_pct = (stats['success'] / count) * 100
                avg_c = np.mean(stats['candles']) if stats['candles'] else 0
                hour_data.append((hour, count, success_pct, avg_c))
                
                # Mark best hours (fast reversion + high success)
                marker = ""
                if avg_c > 0 and avg_c < 7 and success_pct > 99:
                    marker = " ★★★"
                elif avg_c > 0 and avg_c < 10 and success_pct > 98:
                    marker = " ★★"
                elif avg_c > 0 and avg_c < 12:
                    marker = " ★"
                
                f.write(f"{hour:02d}:00 | {count:>7} | {success_pct:>7.1f}% | {avg_c:>11.1f} |{marker}\n")
        
        # Best hours summary
        if hour_data:
            f.write("\n" + "-" * 60 + "\n")
            f.write("BEST HOURS FOR LONG ENTRIES (fastest reversion):\n")
            # Sort by avg candles (lowest = fastest)
            sorted_hours = sorted([h for h in hour_data if h[3] > 0], key=lambda x: x[3])
            for h, cnt, suc, avg in sorted_hours[:5]:
                f.write(f"  {h:02d}:00 - Avg {avg:.1f} candles, {suc:.1f}% success ({cnt} events)\n")
            
            f.write("\nWORST HOURS (slowest reversion):\n")
            for h, cnt, suc, avg in sorted_hours[-5:]:
                f.write(f"  {h:02d}:00 - Avg {avg:.1f} candles, {suc:.1f}% success ({cnt} events)\n")
    
    print(f"Summary Report: {report_path}")
    return csv_path, report_path


def main():
    """Main execution."""
    data_path = DATA_DIR / DATA_FILENAME
    
    if not data_path.exists():
        print(f"ERROR: Data file not found: {data_path}")
        return
    
    print(f"Loading data: {data_path}")
    
    # Load CSV
    df = pd.read_csv(data_path)
    
    # Combine Date and Time columns
    df['Datetime'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'], 
                                     format='%Y%m%d %H:%M:%S')
    
    # Filter date range
    from_date = pd.to_datetime(FROMDATE)
    to_date = pd.to_datetime(TODATE)
    df = df[(df['Datetime'] >= from_date) & (df['Datetime'] <= to_date)].reset_index(drop=True)
    
    print(f"\nAnalyzing {len(df)} bars from {FROMDATE} to {TODATE}")
    print(f"EMA Period: {EMA_PERIOD}, ATR Period: {ATR_PERIOD}")
    print(f"Deviation Multiplier: {DEVIATION_MULT}")
    
    # Analyze
    events = analyze_lower_band_crosses(df)
    
    # Generate reports
    generate_reports(events)
    
    # Print summary
    total = len(events)
    successful = sum(1 for e in events if e['success'])
    success_rate = (successful / total * 100) if total > 0 else 0
    
    successful_events = [e for e in events if e['success']]
    avg_candles = np.mean([e['candles_to_revert'] for e in successful_events]) if successful_events else 0
    
    print("\n" + "=" * 60)
    print("MEAN REVERSION ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"Total Lower Band Crosses: {total}")
    print(f"Successful Reversions: {successful}")
    print(f"Failed Reversions: {total - successful}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Average Candles to Revert: {avg_candles:.1f}")
    print("=" * 60)


if __name__ == '__main__':
    main()
