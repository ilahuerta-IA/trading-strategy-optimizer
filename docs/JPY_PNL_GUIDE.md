# JPY Pairs P&L Calculation Guide for Backtrader

## Overview
This guide explains the correct approach for calculating P&L for JPY pairs (USDJPY, EURJPY, GBPJPY) in Backtrader strategies.

## The Problem
Backtrader's default P&L calculation doesn't account for JPY quote currency conversion:

```python
# Standard forex P&L (WRONG for JPY pairs):
pnl = size * (exit_price - entry_price)
# For USDJPY at 150.00, this gives P&L in JPY, not USD!
```

**Example of incorrect calculation:**
- Entry: 150.00, Exit: 151.00, Size: 100,000
- Wrong P&L: 100,000 * (151 - 150) = 100,000 JPY ≈ $667 USD
- But Backtrader treats this as $100,000!

## The ERIS Solution (Validated)

The solution has two parts that work together:

### 1. Position Size Adjustment
Divide `bt_size` by `forex_jpy_rate` (~150):

```python
# In strategy, when calculating position size:
real_contracts = contracts * self.p.contract_size  # Normal calculation
if self.p.forex_jpy_rate > 1.0:  # JPY pair detected
    bt_size = int(real_contracts / self.p.forex_jpy_rate)
else:
    bt_size = real_contracts
```

### 2. P&L Compensation
Multiply P&L by `JPY_RATE_COMPENSATION` (150.0) in ForexCommission:

```python
class ForexCommission(bt.CommInfoBase):
    params = (
        ('is_jpy_pair', False),
        ('jpy_rate', 150.0),
        # ... other params
    )
    
    def profitandloss(self, size, price, newprice):
        if self.p.is_jpy_pair:
            # ERIS approach: compensate for shrunk position size
            JPY_RATE_COMPENSATION = 150.0
            pnl_jpy = size * JPY_RATE_COMPENSATION * (newprice - price)
            if newprice > 0:
                return pnl_jpy / newprice
            return pnl_jpy
        else:
            # Standard forex P&L
            pnl_quote = size * (newprice - price)
            if newprice > 0:
                return pnl_quote / newprice
            return pnl_quote
```

### 3. Commission Setup
Configure cerebro with JPY-aware commission:

```python
if USE_FIXED_COMMISSION:
    is_jpy = 'JPY' in FOREX_INSTRUMENT
    cerebro.broker.addcommissioninfo(
        ForexCommission(
            commission=COMMISSION_PER_LOT_PER_ORDER,
            is_jpy_pair=is_jpy,
            jpy_rate=150.0 if is_jpy else 1.0
        )
    )
```

## Why This Works

| Step | Effect |
|------|--------|
| Position shrunk by 150x | Backtrader sees smaller position |
| P&L multiplied by 150x | Compensates for smaller position |
| Commission: size × 150 | Restores actual lot size for fees |
| Divide by newprice | Converts JPY → USD |
| **Result** | Correct USD P&L and commissions |

## Implementation Checklist

When creating a new JPY pair strategy:

- [ ] Add `forex_jpy_rate=150.0` to strategy params
- [ ] In position sizing: `bt_size = real_contracts / forex_jpy_rate`
- [ ] In ForexCommission: set `is_jpy_pair=True`
- [ ] ForexCommission.profitandloss() uses `JPY_RATE_COMPENSATION = 150.0`
- [ ] ForexCommission._getcommission() restores `actual_size = size * jpy_rate`
- [ ] cashadjust() calls profitandloss()

## Strategy Params Template

```python
params = dict(
    # ... other params ...
    
    # === FOREX SETTINGS ===
    forex_instrument='USDJPY',
    forex_pip_value=0.01,  # JPY pairs use 0.01
    forex_pip_decimal_places=3,
    forex_lot_size=100000,
    forex_jpy_rate=150.0,  # CRITICAL: JPY conversion rate
    
    # ... other params ...
)
```

## Reference Implementations

| File | Description |
|------|-------------|
| `eris_usdjpy.py` | Original ERIS implementation (validated) |
| `sunrise_ogle_usdjpy_pro.py` | OGLE strategy for USDJPY |
| `sunrise_ogle_template.py` | Template with JPY support built-in |

## Testing Your Implementation

Run a backtest and verify:
1. Individual trade P&L values are reasonable (not $50,000+ per trade)
2. Annual returns are realistic (not 1000%+)
3. Compare with known working implementation (eris_usdjpy.py)

## Common Mistakes

❌ **Wrong:** Multiplying P&L by jpy_rate without shrinking position
```python
# This gives ~22,500x amplified P&L!
pnl = size * jpy_rate * (newprice - price)
```

❌ **Wrong:** Only dividing by jpy_rate without compensation
```python
# This gives ~1/150 of correct P&L
pnl = size * (newprice - price) / jpy_rate
```

✅ **Correct:** ERIS approach - shrink position, compensate P&L
```python
# Position shrunk by 150, P&L multiplied by 150, then convert to USD
bt_size = real_contracts / 150
pnl = size * 150 * (newprice - price) / newprice
```

---
*Guide created: December 2025*
*Validated with: USDJPY 5Y backtest (2020-2025)*
