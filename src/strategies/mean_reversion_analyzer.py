"""Mean Reversion Analyzer - Statistical Analysis of Lower Band Crosses
=====================================================================
Analyzes the behavior when price crosses below the lower mean reversion band:
- How many candles until price returns above the lower band
- Distribution of reversion times
- Success rate of reversions
- Patterns by hour of day

Output: Exports detailed CSV and summary report to temp_reports folder.

Author: ERIS Research
"""
from __future__ import annotations
import csv
import math
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import backtrader as bt


# =============================================================================
# CONFIGURATION
# =============================================================================

DATA_FILENAME = 'USDCHF_5m_5Yea.csv'
FROMDATE = '2024-09-01'
TODATE = '2025-11-01'

# Mean Reversion Parameters (same as eris_template)
EMA_PERIOD = 70
ATR_PERIOD = 14
DEVIATION_MULT = 2.0

# Analysis parameters
MAX_CANDLES_TO_TRACK = 100  # Max candles to wait for reversion before "failed"

# Export folder
EXPORT_DIR = Path(__file__).parent / "temp_reports"


# =============================================================================
# ANALYZER STRATEGY
# =============================================================================

class MeanReversionAnalyzer(bt.Strategy):
    """
    Analyzer that tracks lower band crosses and measures reversion behavior.
    
    Tracks:
    1. When price crosses BELOW lower band (entry into oversold)
    2. How many candles until price crosses BACK ABOVE lower band
    3. Maximum deviation (lowest Z-Score reached)
    4. Hour of day patterns
    """
    
    params = dict(
        ema_period=EMA_PERIOD,
        atr_period=ATR_PERIOD,
        deviation_mult=DEVIATION_MULT,
        max_candles=MAX_CANDLES_TO_TRACK,
    )
    
    def __init__(self):
        # Indicators
        self.ema = bt.ind.EMA(self.data.close, period=self.p.ema_period)
        self.atr = bt.ind.ATR(self.data, period=self.p.atr_period)
        
        # Calculated bands
        self.lower_band = None  # Will calculate each bar
        self.upper_band = None
        
        # Tracking state
        self.in_oversold = False
        self.cross_bar = None
        self.cross_datetime = None
        self.cross_hour = None
        self.cross_price = None
        self.cross_zscore = None
        self.min_zscore_in_cross = None  # Track lowest Z-Score during cross
        self.candles_in_cross = 0
        
        # Results storage
        self.cross_events = []  # List of all cross events with details
        
        # Summary statistics
        self.total_crosses = 0
        self.successful_reversions = 0
        self.failed_reversions = 0  # Didn't return within max_candles
        
    def next(self):
        """Track each bar for lower band crosses."""
        # Skip if not enough data for EMA/ATR
        if len(self) < max(self.p.ema_period, self.p.atr_period) + 1:
            return
        
        # Calculate current bands and Z-Score
        current_ema = float(self.ema[0])
        current_atr = float(self.atr[0])
        
        if math.isnan(current_ema) or math.isnan(current_atr) or current_atr == 0:
            return
        
        self.lower_band = current_ema - (self.p.deviation_mult * current_atr)
        self.upper_band = current_ema + (self.p.deviation_mult * current_atr)
        
        current_price = float(self.data.close[0])
        current_zscore = (current_price - current_ema) / current_atr
        
        # Get datetime - use num2date for proper time parsing
        dt = bt.num2date(self.data.datetime[0])
        current_hour = dt.hour
        
        # STATE: Not in oversold - check for new cross below lower band
        if not self.in_oversold:
            if current_price < self.lower_band:
                # New cross below lower band!
                self.in_oversold = True
                self.cross_bar = len(self)
                self.cross_datetime = dt
                self.cross_hour = current_hour
                self.cross_price = current_price
                self.cross_zscore = current_zscore
                self.min_zscore_in_cross = current_zscore
                self.candles_in_cross = 1
                self.total_crosses += 1
        
        # STATE: In oversold - track until price returns above lower band
        else:
            self.candles_in_cross += 1
            
            # Track minimum Z-Score (most oversold)
            if current_zscore < self.min_zscore_in_cross:
                self.min_zscore_in_cross = current_zscore
            
            # Check for successful reversion (price back above lower band)
            if current_price >= self.lower_band:
                # Successful reversion!
                self.successful_reversions += 1
                
                event = {
                    'cross_datetime': self.cross_datetime.strftime('%Y-%m-%d %H:%M'),
                    'cross_hour': self.cross_hour,
                    'cross_price': self.cross_price,
                    'cross_zscore': self.cross_zscore,
                    'min_zscore': self.min_zscore_in_cross,
                    'reversion_datetime': dt.strftime('%Y-%m-%d %H:%M'),
                    'reversion_price': current_price,
                    'reversion_zscore': current_zscore,
                    'candles_to_revert': self.candles_in_cross,
                    'success': True,
                    'lower_band_at_cross': self.cross_price,  # Price was below this
                    'ema_at_cross': current_ema - (self.p.deviation_mult * current_atr) + (self.p.deviation_mult * current_atr),
                }
                self.cross_events.append(event)
                
                # Reset state
                self.in_oversold = False
                self.cross_bar = None
            
            # Check for failed reversion (took too long)
            elif self.candles_in_cross >= self.p.max_candles:
                self.failed_reversions += 1
                
                event = {
                    'cross_datetime': self.cross_datetime.strftime('%Y-%m-%d %H:%M'),
                    'cross_hour': self.cross_hour,
                    'cross_price': self.cross_price,
                    'cross_zscore': self.cross_zscore,
                    'min_zscore': self.min_zscore_in_cross,
                    'reversion_datetime': dt.strftime('%Y-%m-%d %H:%M'),
                    'reversion_price': current_price,
                    'reversion_zscore': current_zscore,
                    'candles_to_revert': self.candles_in_cross,
                    'success': False,  # Failed - took too long
                    'lower_band_at_cross': self.cross_price,
                    'ema_at_cross': current_ema,
                }
                self.cross_events.append(event)
                
                # Reset state
                self.in_oversold = False
                self.cross_bar = None
    
    def stop(self):
        """Generate reports when backtest ends."""
        self._export_detailed_csv()
        self._export_summary_report()
        self._print_summary()
    
    def _export_detailed_csv(self):
        """Export all cross events to CSV."""
        EXPORT_DIR.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = EXPORT_DIR / f"mean_reversion_crosses_{timestamp}.csv"
        
        fieldnames = [
            'cross_datetime', 'cross_hour', 'cross_price', 'cross_zscore',
            'min_zscore', 'reversion_datetime', 'reversion_price', 
            'reversion_zscore', 'candles_to_revert', 'success'
        ]
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for event in self.cross_events:
                row = {k: event.get(k, '') for k in fieldnames}
                writer.writerow(row)
        
        print(f"\nDetailed CSV: {csv_path}")
    
    def _export_summary_report(self):
        """Export summary statistics to text file."""
        EXPORT_DIR.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = EXPORT_DIR / f"mean_reversion_summary_{timestamp}.txt"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("MEAN REVERSION ANALYSIS - LOWER BAND CROSSES\n")
            f.write("=" * 70 + "\n\n")
            
            f.write(f"Data: {DATA_FILENAME}\n")
            f.write(f"Period: {FROMDATE} to {TODATE}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("PARAMETERS:\n")
            f.write("-" * 40 + "\n")
            f.write(f"EMA Period: {self.p.ema_period}\n")
            f.write(f"ATR Period: {self.p.atr_period}\n")
            f.write(f"Deviation Multiplier: {self.p.deviation_mult}\n")
            f.write(f"Max Candles to Track: {self.p.max_candles}\n\n")
            
            f.write("=" * 70 + "\n")
            f.write("OVERALL STATISTICS\n")
            f.write("=" * 70 + "\n\n")
            
            f.write(f"Total Lower Band Crosses: {self.total_crosses}\n")
            f.write(f"Successful Reversions: {self.successful_reversions}\n")
            f.write(f"Failed Reversions (>{self.p.max_candles} candles): {self.failed_reversions}\n")
            
            if self.total_crosses > 0:
                success_rate = (self.successful_reversions / self.total_crosses) * 100
                f.write(f"Success Rate: {success_rate:.1f}%\n\n")
            
            # Calculate reversion time statistics (only successful)
            successful_events = [e for e in self.cross_events if e['success']]
            
            if successful_events:
                candle_times = [e['candles_to_revert'] for e in successful_events]
                
                f.write("=" * 70 + "\n")
                f.write("REVERSION TIME STATISTICS (Successful Only)\n")
                f.write("=" * 70 + "\n\n")
                
                avg_candles = sum(candle_times) / len(candle_times)
                min_candles = min(candle_times)
                max_candles = max(candle_times)
                
                # Median
                sorted_times = sorted(candle_times)
                mid = len(sorted_times) // 2
                if len(sorted_times) % 2 == 0:
                    median_candles = (sorted_times[mid-1] + sorted_times[mid]) / 2
                else:
                    median_candles = sorted_times[mid]
                
                f.write(f"Average Candles to Revert: {avg_candles:.1f}\n")
                f.write(f"Median Candles to Revert: {median_candles:.1f}\n")
                f.write(f"Min Candles: {min_candles}\n")
                f.write(f"Max Candles: {max_candles}\n\n")
                
                # Distribution histogram
                f.write("DISTRIBUTION (Candles to Revert):\n")
                f.write("-" * 40 + "\n")
                
                # Create buckets
                buckets = defaultdict(int)
                for t in candle_times:
                    if t <= 5:
                        buckets['1-5'] += 1
                    elif t <= 10:
                        buckets['6-10'] += 1
                    elif t <= 15:
                        buckets['11-15'] += 1
                    elif t <= 20:
                        buckets['16-20'] += 1
                    elif t <= 30:
                        buckets['21-30'] += 1
                    elif t <= 50:
                        buckets['31-50'] += 1
                    else:
                        buckets['51+'] += 1
                
                bucket_order = ['1-5', '6-10', '11-15', '16-20', '21-30', '31-50', '51+']
                for bucket in bucket_order:
                    count = buckets.get(bucket, 0)
                    pct = (count / len(candle_times)) * 100 if candle_times else 0
                    bar = '█' * int(pct / 2)
                    f.write(f"{bucket:>8} candles: {count:>4} ({pct:>5.1f}%) {bar}\n")
                
                # Z-Score analysis
                f.write("\n" + "=" * 70 + "\n")
                f.write("Z-SCORE DEPTH ANALYSIS\n")
                f.write("=" * 70 + "\n\n")
                
                min_zscores = [e['min_zscore'] for e in successful_events]
                avg_min_zscore = sum(min_zscores) / len(min_zscores)
                deepest_zscore = min(min_zscores)
                
                f.write(f"Average Min Z-Score Reached: {avg_min_zscore:.2f}\n")
                f.write(f"Deepest Z-Score: {deepest_zscore:.2f}\n\n")
                
                # Correlation: deeper Z-Score vs candles to revert
                f.write("Z-Score Depth vs Reversion Time:\n")
                f.write("-" * 40 + "\n")
                
                # Group by Z-Score depth
                zscore_groups = {
                    'Z < -3.0 (very deep)': [],
                    '-3.0 <= Z < -2.5': [],
                    '-2.5 <= Z < -2.0': [],
                    'Z >= -2.0 (shallow)': [],
                }
                
                for e in successful_events:
                    z = e['min_zscore']
                    if z < -3.0:
                        zscore_groups['Z < -3.0 (very deep)'].append(e['candles_to_revert'])
                    elif z < -2.5:
                        zscore_groups['-3.0 <= Z < -2.5'].append(e['candles_to_revert'])
                    elif z < -2.0:
                        zscore_groups['-2.5 <= Z < -2.0'].append(e['candles_to_revert'])
                    else:
                        zscore_groups['Z >= -2.0 (shallow)'].append(e['candles_to_revert'])
                
                for group_name, times in zscore_groups.items():
                    if times:
                        avg = sum(times) / len(times)
                        f.write(f"{group_name}: {len(times)} events, avg {avg:.1f} candles\n")
                    else:
                        f.write(f"{group_name}: 0 events\n")
                
                # Hour of day analysis
                f.write("\n" + "=" * 70 + "\n")
                f.write("HOUR OF DAY ANALYSIS\n")
                f.write("=" * 70 + "\n\n")
                
                hour_stats = defaultdict(lambda: {'count': 0, 'candles': [], 'success': 0})
                
                for e in self.cross_events:
                    hour = e['cross_hour']
                    hour_stats[hour]['count'] += 1
                    if e['success']:
                        hour_stats[hour]['success'] += 1
                        hour_stats[hour]['candles'].append(e['candles_to_revert'])
                
                f.write("Hour | Crosses | Success% | Avg Candles\n")
                f.write("-" * 45 + "\n")
                
                for hour in range(24):
                    stats = hour_stats.get(hour, {'count': 0, 'success': 0, 'candles': []})
                    count = stats['count']
                    if count > 0:
                        success_pct = (stats['success'] / count) * 100
                        avg_candles = sum(stats['candles']) / len(stats['candles']) if stats['candles'] else 0
                        f.write(f"{hour:02d}:00 | {count:>7} | {success_pct:>7.1f}% | {avg_candles:>11.1f}\n")
        
        print(f"Summary Report: {report_path}")
    
    def _print_summary(self):
        """Print quick summary to console."""
        print("\n" + "=" * 60)
        print("MEAN REVERSION ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"Total Lower Band Crosses: {self.total_crosses}")
        print(f"Successful Reversions: {self.successful_reversions}")
        print(f"Failed Reversions: {self.failed_reversions}")
        
        if self.total_crosses > 0:
            success_rate = (self.successful_reversions / self.total_crosses) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        successful_events = [e for e in self.cross_events if e['success']]
        if successful_events:
            candle_times = [e['candles_to_revert'] for e in successful_events]
            avg_candles = sum(candle_times) / len(candle_times)
            print(f"Average Candles to Revert: {avg_candles:.1f}")
        
        print("=" * 60)


# =============================================================================
# CUSTOM DATA FEED FOR PROPER TIME PARSING
# =============================================================================

class CustomCSVData(bt.feeds.GenericCSVData):
    """Custom data feed that properly combines Date and Time columns."""
    
    params = (
        ('dtformat', '%Y%m%d %H:%M:%S'),
        ('datetime', 0),
        ('time', -1),  # Disable separate time column
        ('open', 1),
        ('high', 2),
        ('low', 3),
        ('close', 4),
        ('volume', 5),
        ('openinterest', -1),
    )
    
    def _loadline(self, linetokens):
        # Combine Date (col 0) and Time (col 1) into single datetime string
        if len(linetokens) >= 7:
            combined_dt = f"{linetokens[0]} {linetokens[1]}"
            # New tokens: [datetime, open, high, low, close, volume]
            linetokens = [combined_dt, linetokens[2], linetokens[3], 
                         linetokens[4], linetokens[5], linetokens[6]]
        return super()._loadline(linetokens)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == '__main__':
    # Setup Cerebro
    cerebro = bt.Cerebro()
    
    # Add strategy
    cerebro.addstrategy(MeanReversionAnalyzer)
    
    # Load data
    data_dir = Path(__file__).parent.parent.parent / "data"
    data_path = data_dir / DATA_FILENAME
    
    if not data_path.exists():
        print(f"ERROR: Data file not found: {data_path}")
        exit(1)
    
    print(f"Loading data: {data_path}")
    
    # Parse dates
    from_date = datetime.strptime(FROMDATE, '%Y-%m-%d')
    to_date = datetime.strptime(TODATE, '%Y-%m-%d')
    
    # Create data feed with custom parser
    data = CustomCSVData(
        dataname=data_path,
        fromdate=from_date,
        todate=to_date,
        nullvalue=0.0,
    )
    
    cerebro.adddata(data)
    
    # Initial capital
    cerebro.broker.setcash(100000.0)
    
    print(f"\nRunning Mean Reversion Analysis...")
    print(f"Period: {FROMDATE} to {TODATE}")
    print(f"EMA Period: {EMA_PERIOD}, ATR Period: {ATR_PERIOD}")
    print(f"Deviation Multiplier: {DEVIATION_MULT}")
    
    # Run analysis
    cerebro.run()
    
    print("\nAnalysis complete! Check temp_reports folder for detailed results.")
