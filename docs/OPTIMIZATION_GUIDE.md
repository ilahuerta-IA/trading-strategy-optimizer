# 🎯 OGLE Strategy Optimization Guide

## Performance Targets

| Metric | Minimum Target | Ideal |
|--------|----------------|-------|
| Sharpe Ratio | > 0.8 | ~1.0 |
| Profit Factor | > 1.5 | > 2.0 |
| Max Drawdown | < 10% | < 8% |
| Number of Trades | > 120 (5 years) | > 200 |
| Win Rate | > 35% | > 40% |

---

## 🚨 CRITICAL LESSONS LEARNED (Dec 2025)

### ⚠️ Log Analysis vs Real Backtest - MUST READ

**Problem discovered**: Log analysis showed PF 1.56, real backtest showed PF 1.25

**Root cause**: Log analysis did NOT account for:
- Commission: $2.50/lot/order (Darwinex Zero)
- Both entry AND exit commissions
- Impact scales with trade count and position size

**Solution implemented**:
1. Log analysis is ONLY for pattern discovery (hours, ATR ranges, etc.)
2. ALL final validations MUST use real backtest with commission
3. `ForexCommission` class is now mandatory in all backtests

```python
# MANDATORY in all backtest functions:
cerebro.broker.addcommissioninfo(ForexCommission())

# ForexCommission applies:
# - $2.50 per lot per order (Darwinex Zero rates)
# - Applied on OPEN and CLOSE (both sides)
# - For 1 lot: $5.00 per round trip
```

### Validation Before Production

**NEVER** trust log analysis alone. Always run:
```powershell
python validate_eurusd.py  # Or similar validation script
```

Output should show:
```
Commission: $2.50/lot/order (Darwinex Zero)
Total commission: $X,XXX.XX | Avg per trade: $XX.XX
```

---

## Optimization Process (2 Phases)

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: BATCH BACKTESTING (optstrategy)                       │
│  ─────────────────────────────────────────                      │
│  Parameters IMPOSSIBLE to optimize by logs:                     │
│  • EMAs (fast, medium, slow, filter)                            │
│  • ATR multipliers (SL, TP)                                     │
│                                                                 │
│  Filters: MINIMAL (only proven ones)                            │
│  Method: cerebro.optstrategy() with reduced ranges              │
│  Metric: Sharpe × √trades                                       │
│  ⚠️ MUST include ForexCommission()                              │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: LOG ANALYSIS (Pattern Discovery Only)                 │
│  ─────────────────────────────────────────────                  │
│  With TOP 3-5 results from Phase 1, generate logs and identify: │
│  • Entry hours distribution                                     │
│  • ATR thresholds (min/max in winners vs losers)                │
│  • EMA angles (optimal slope)                                   │
│  • Window periods / pullback depth                              │
│                                                                 │
│  Method: EXPORT_TRADE_REPORTS = True + manual analysis          │
│  ⚠️ THEN validate with real backtest + commission!              │
└─────────────────────────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: VALIDATION (Mandatory)                                │
│  ─────────────────────────────────                              │
│  Run real backtest with proposed filters + commission           │
│  Compare against Phase 1 results                                │
│  If improvement confirmed → Apply to production                 │
│  If NOT improved → Discard filter, try alternatives             │
└─────────────────────────────────────────────────────────────────┘
```

---

## PHASE 1: Batch Backtesting

### 1.1 Standard Parameter Ranges

**EMAs (choose 2-3 based on strategy complexity):**
```python
EMA_FAST_RANGE = [9, 12, 16, 18, 21]           # ~5 values
EMA_MEDIUM_RANGE = [18, 21, 26, 28, 34]        # ~5 values (if used)
EMA_SLOW_RANGE = [26, 34, 42, 50]              # ~4 values
EMA_FILTER_RANGE = [40, 50, 70, 80, 100]       # ~5 values
```

**ATR Risk Management:**
```python
ATR_SL_MULT_RANGE = [1.0, 1.5, 2.0, 2.5]       # 4 values
ATR_TP_MULT_RANGE = [8.0, 9.0, 10.0, 11.0]     # 4 values
```

### 1.2 Combination Count

Keep between **100-500 combinations** maximum:

| Configuration | EMAs | SL | TP | Total |
|---------------|------|----|----|-------|
| 2 EMAs | 5 × 5 = 25 | 4 | 4 | **400** |
| 2 EMAs reduced | 4 × 4 = 16 | 3 | 3 | **144** |
| 3 EMAs | 5 × 5 × 4 = 100 | 4 | 4 | **1600** ❌ |
| 3 EMAs reduced | 4 × 3 × 3 = 36 | 3 | 3 | **324** |

### 1.3 Filters During Optimization

**ENABLE only proven filters:**
```python
# Typically work well:
USE_PRICE_FILTER_EMA = True          # close > filter EMA
PULLBACK_MAX_CANDLES = 2             # 2 candle pullback
USE_PULLBACK_ENTRY = True            # Pullback system

# DISABLE for maximum signals:
USE_ATR_FILTER = False
USE_ANGLE_FILTER = False
USE_TIME_RANGE_FILTER = False
USE_EMA_ORDER_CONDITION = False
USE_CANDLE_DIRECTION_FILTER = False
```

### 1.4 optstrategy Code

```python
cerebro = bt.Cerebro(optreturn=False)  # optreturn=False to access analyzers

# ⚠️ MANDATORY: Add commission
cerebro.broker.addcommissioninfo(ForexCommission())

cerebro.optstrategy(
    MyStrategy,
    ema_fast_length=[12, 16, 18, 21],
    ema_filter_length=[50, 70, 100],
    atr_sl_multiplier=[1.5, 2.0, 2.5],
    atr_tp_multiplier=[8.0, 10.0, 12.0],
)

cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

results = cerebro.run(maxcpus=1)  # maxcpus=N to parallelize
```

### 1.5 Ranking Metric

```python
# Sharpe × √trades - Balances profitability with consistency
score = sharpe_ratio * math.sqrt(num_trades)

# Alternative: PF × Sharpe
score = profit_factor * sharpe_ratio
```

### 1.6 TOP Results Selection

Sort by score and select TOP 3-5 that meet:
- Trades > 100
- Sharpe > 0.5
- PF > 1.3
- Max DD < 12%

---

## PHASE 2: Log Analysis

### 2.1 Generate Logs

Run each TOP configuration with:
```python
EXPORT_TRADE_REPORTS = True
VERBOSE_DEBUG = False  # Keep False
```

Generates files in `temp_reports/`:
```
ASSET_trades_YYYYMMDD_HHMMSS.txt
```

### 2.2 Hourly Distribution Analysis

Extract hour from each trade and calculate:

| Hour UTC | Trades | Wins | WinRate | Avg P&L |
|----------|--------|------|---------|---------|
| 07:00 | 45 | 22 | 48.9% | +$12.30 |
| 08:00 | 38 | 18 | 47.4% | +$8.50 |
| 14:00 | 12 | 3 | 25.0% | -$15.20 ← **Filter** |

**Action:** Define `ENTRY_START_HOUR` and `ENTRY_END_HOUR`

### 2.3 ATR Analysis

Extract ATR at entry time:

| ATR Range | Trades | WinRate | Avg P&L |
|-----------|--------|---------|---------|
| < 0.00030 | 28 | 25.0% | -$8.50 ← **ATR_MIN** |
| 0.00030-0.00060 | 156 | 42.3% | +$15.20 ✓ |
| 0.00060-0.00090 | 45 | 38.5% | +$5.30 |
| > 0.00090 | 16 | 18.8% | -$22.10 ← **ATR_MAX** |

**Action:** Define `ATR_MIN_THRESHOLD` and `ATR_MAX_THRESHOLD`

### 2.4 Quick Analysis Script

```python
import pandas as pd

# Parse log (adjust based on format)
trades = []
with open('temp_reports/ASSET_trades.txt', 'r') as f:
    # Parse entries and exits
    pass

df = pd.DataFrame(trades)

# Analysis by hour
print(df.groupby(df['entry_time'].dt.hour).agg({
    'pnl': ['count', 'sum', 'mean'],
    'is_win': 'mean'
}))

# Analysis by ATR
df['atr_bucket'] = pd.cut(df['entry_atr'], bins=[0, 0.0003, 0.0006, 0.0009, 1])
print(df.groupby('atr_bucket')['pnl'].agg(['count', 'sum', 'mean']))
```

---

## PHASE 3: Validation (CRITICAL)

### ⚠️ Never Skip This Phase

Log analysis can be **MISLEADING** because:
1. Does not account for commissions
2. Does not account for spread
3. Filtering trades post-hoc ≠ filtering in real backtest

### Validation Process

```python
# 1. Create validation script (see validate_eurusd.py)
# 2. Test configurations with and without proposed filters
# 3. Compare REAL PF vs LOG PF

# Example from EURUSD Dec 2025:
# Log analysis: PF 1.56 with 6h-16h filter
# Real backtest: PF 1.25 with 6h-16h filter
# Delta: -0.31 PF points lost to commission!
```

### Validation Checklist

- [ ] Real backtest includes `ForexCommission()`
- [ ] Commission line visible in output
- [ ] Compare PF with and without filter
- [ ] Check trade count impact
- [ ] If improvement < 10%, probably not worth it

---

## CSV Format Solution (Date/Time Separated)

### Common Problem
Historical data CSV files have separate `Date` and `Time` columns:

```csv
Date,Time,Open,High,Low,Close,Volume
20200101,22:00:00,1.12136,1.12139,1.12120,1.12125,47600000
```

### ⚠️ Problem with GenericCSVData (Dec 19, 2025)

**Issue discovered**: When using `bt.feeds.GenericCSVData` with separate Date/Time columns (`datetime=0, time=1`), backtrader does NOT properly combine them. All times show `23:59:59` regardless of actual time.

**Root cause**: GenericCSVData's internal parsing doesn't properly handle the time column when separate from date.

**Evidence**:
```python
# This configuration does NOT work correctly:
data = bt.feeds.GenericCSVData(
    dataname=str(data_path),
    dtformat='%Y%m%d',
    tmformat='%H:%M:%S',
    datetime=0,
    time=1,  # This is IGNORED internally!
    ...
)
# All bt.num2date() and self.data.datetime.datetime(0) return 23:59:59
```

### Solution: ForexCSVData Custom Feed

Created `ForexCSVData` class that properly parses and combines Date/Time columns:

```python
class ForexCSVData(bt.feeds.GenericCSVData):
    """
    Custom CSV Data Feed that correctly handles separate Date and Time columns.
    """
    def _loadline(self, linetokens):
        dt_str = linetokens[0]  # '20200101'
        tm_str = linetokens[1]  # '22:00:00'
        
        try:
            dt = datetime.strptime(f"{dt_str} {tm_str}", '%Y%m%d %H:%M:%S')
        except ValueError:
            return False
        
        if self.p.fromdate and dt < self.p.fromdate:
            return False
        if self.p.todate and dt > self.p.todate:
            return False
        
        self.lines.datetime[0] = bt.date2num(dt)
        self.lines.open[0] = float(linetokens[2])
        self.lines.high[0] = float(linetokens[3])
        self.lines.low[0] = float(linetokens[4])
        self.lines.close[0] = float(linetokens[5])
        self.lines.volume[0] = float(linetokens[6])
        self.lines.openinterest[0] = 0.0
        
        return True
```

**Usage:**
```python
# CORRECT - Use ForexCSVData
data = ForexCSVData(
    dataname=str(data_path),
    fromdate=datetime.strptime(FROMDATE, '%Y-%m-%d'),
    todate=datetime.strptime(TODATE, '%Y-%m-%d'),
)

# Helper method in strategy for datetime access:
def _get_datetime(self, offset=0):
    dt_date = self.data.datetime.date(offset)
    dt_time = self.data.datetime.time(offset)
    return datetime.combine(dt_date, dt_time)
```

**Files updated (Dec 19, 2025)**:
- `koi_eurusd_pro.py` - Added ForexCSVData class and _get_datetime() helper
- `koi_template.py` - Added ForexCSVData class and _get_datetime() helper

### Alternative: Preprocess CSV with Pandas
```python
def load_data(csv_path):
    df = pd.read_csv(csv_path)
    
    # Handle Date + Time columns format (YYYYMMDD + HH:MM:SS)
    if 'Date' in df.columns and 'Time' in df.columns:
        df['datetime'] = pd.to_datetime(
            df['Date'].astype(str) + ' ' + df['Time'], 
            format='%Y%m%d %H:%M:%S'
        )
        df.set_index('datetime', inplace=True)
        df.drop(columns=['Date', 'Time'], inplace=True)
    
    df.columns = [c.lower() for c in df.columns]
    return df
```

---

## Final Validation Checklist

- [ ] Sharpe Ratio > 0.8 (ideally ~1.0)
- [ ] Profit Factor > 1.5
- [ ] Max Drawdown < 10%
- [ ] Trades > 120 in 5-year period
- [ ] Win Rate > 35%
- [ ] Consistency between years (±10% in metrics)
- [ ] No overfitting (works in different periods)
- [ ] **Commission included in all backtests** ✅

---

## PHASE 4: Robustness Testing

### Purpose
After optimization, validate strategy across multiple time periods to ensure:
- Results aren't period-specific (overfitting)
- Strategy performs consistently across different market conditions
- Parameters are robust, not optimized for one specific window

### Test Matrix (10 periods)
| Test # | Period | Duration | Purpose |
|--------|--------|----------|---------|
| BASELINE | Full dataset | ~5 years | Reference |
| 1-5 | Individual years | 1 year each | Year stability |
| 6-7 | 2-year periods | 2 years | Medium term |
| 8 | Recent 1.5Y | 1.5 years | Recent performance |
| 9 | Alternative 3Y | 3 years | Different window |
| 10 | Latest 6 months | 6 months | Most recent |

### Robustness Criteria
| Metric | Pass Criteria |
|--------|---------------|
| Profit Factor | > 1.2 in 70%+ of tests |
| Win Rate | > 25% in all tests |
| No Catastrophic Loss | Max DD < 25% in all tests |
| Positive PnL | Positive in 60%+ of tests |

### Robustness Script Usage
```powershell
# KOI EURUSD
python koi_eurusd_robustness.py

# Output shows all 10 tests + summary
# PASS if 70%+ tests have PF > 1.2
```

### Example Results (KOI EURUSD Dec 2025)
```
Valid tests: 10/10
  PASSED (PF >= 1.2): 9 (90%)
  MARGINAL (PF 1.0-1.2): 1 (10%)
  FAILED (PF < 1.0): 0 (0%)

VERDICT: EXCELLENT ROBUSTNESS (4/4 criteria)
```

---

## Quick Commands

```powershell
# Run batch optimization
python ogle_optimizer_universal.py ASSET PHASE

# Run with detailed logs
# Edit: EXPORT_TRADE_REPORTS = True
python sunrise_ogle_ASSET_pro.py

# View first lines of log
Get-Content temp_reports/ASSET_trades*.txt -Head 50

# Validate with commission
python validate_eurusd.py

# Robustness test
python koi_eurusd_robustness.py
```

---

## Important Notes

1. **Logs for patterns, Backtest for validation** - Log analysis reveals patterns, but backtest confirms actual performance
2. **Maintain sufficient trades** - More than 120 in 5 years for statistical validity
3. **Don't over-optimize** - If a parameter changes metrics dramatically, it's a sign of overfitting
4. **Consistency > Maximum return** - Prefer stable configurations between periods
5. **2 EMAs is usually enough** - fast + filter/slow, avoid unnecessary complexity
6. **Commission matters** - $2.50/lot/order significantly impacts PF, especially with many trades
7. **Robustness testing is mandatory** - Never deploy without passing 70%+ period tests
8. **NEVER change RISK_PERCENT** - Always 0.005 (0.5%) for comparable results

---

## 🚫 AXIOM: Original Strategy Parameters

**NEVER modify these during optimization:**

| Parameter | Fixed Value | Reason |
|-----------|-------------|--------|
| `RISK_PERCENT` | 0.005 (0.5%) | Dynamic position sizing |
| Commission | $2.50/lot/order | Darwinex Zero standard |
| `use_forex_position_calc` | True | Correct lot calculation |

```python
# ✅ ALWAYS
RISK_PERCENT = 0.005  # 0.5% risk per trade

# ❌ NEVER (breaks comparability)
RISK_PERCENT = 0.00   # Fixed 1 lot - WRONG!
RISK_PERCENT = 0.01   # 1% - different risk profile
```

**Related guides:**
- `docs/JPY_PNL_GUIDE.md` - JPY pairs P&L calculation
- `docs/OGLE_OPTIMIZATION_HOWTO.md` - Complete optimization process

---

## ForexCommission Class Reference

```python
class ForexCommission(bt.CommInfoBase):
    """
    Darwinex Zero commission structure:
    - $2.50 per lot per order
    - Applied on OPEN and CLOSE
    - For 1 lot round trip: $5.00
    """
    params = (
        ('commission', 2.50),      # $ per lot per order
        ('mult', 100000),          # Standard lot = 100,000 units
        ('margin', 1000),          # Margin per lot
        ('stocklike', False),
        ('leverage', 100.0),
    )
    
    def _getcommission(self, size, price, pseudoexec):
        lots = abs(size) / self.p.mult
        return lots * self.p.commission
```

---

## PHASE 5: OGLE-KOI Dual Strategy Fusion

After both strategies are optimized and validated for an asset, create a combined portfolio:

### Quick Reference
```powershell
# Template files
src/strategies/oglekoi_usdchf.py   # Reference template
src/strategies/oglekoi_eurusd.py   # EURUSD dual
src/strategies/oglekoi_usdcad.py   # USDCAD dual
```

### Key Points
1. **Portfolio allocation**: 50% KOI + 50% OGLE
2. **Embed KOI class**: Don't import from koi_ASSET_pro.py (causes 0 trades)
3. **Import OGLE**: `from sunrise_ogle_ASSET_pro import SunriseOgle`
4. **Sharpe/Sortino**: Use √(trades_per_year), NOT √252

### Expected Benefits
- Diversification from different entry logic
- Smoother equity curve
- Combined PF typically between individual strategies
- Lower correlation = better risk-adjusted returns

See `OGLE_OPTIMIZATION_HOWTO.md` Phase 7 for detailed instructions.

---

*Last updated: December 23, 2025*
