"""Quick analysis of KOI trade log"""
import re

# Read log
with open('temp_reports/KOI_USDCHF_trades_20251214_212113.txt', 'r') as f:
    content = f.read()

# Parse trades - simpler regex
trades = []
blocks = content.split('ENTRY #')[1:]  # Split by entries

for block in blocks:
    try:
        # Extract hour
        time_match = re.search(r'Time: \d{4}-\d{2}-\d{2} (\d{2}):', block)
        hour = int(time_match.group(1)) if time_match else 0
        
        # Extract SL pips
        sl_match = re.search(r'SL Pips: ([\d.]+)', block)
        sl_pips = float(sl_match.group(1)) if sl_match else 0
        
        # Extract ATR
        atr_match = re.search(r'ATR: ([\d.]+)', block)
        atr = float(atr_match.group(1)) if atr_match else 0
        
        # Extract CCI
        cci_match = re.search(r'CCI: ([\d.]+)', block)
        cci = float(cci_match.group(1)) if cci_match else 0
        
        # Extract PnL
        pnl_match = re.search(r'P&L: \$([-\d,.]+)', block)
        pnl = float(pnl_match.group(1).replace(',', '')) if pnl_match else 0
        
        trades.append({'hour': hour, 'sl_pips': sl_pips, 'atr': atr, 'cci': cci, 'pnl': pnl})
    except:
        pass

print(f'Total trades parsed: {len(trades)}')
print(f'Base: 336 trades, PF=1.33')

# Analyze by SL ranges
print('\n=== BY MIN SL PIPS ===')
for min_sl in [8, 10, 12, 15, 18, 20, 25]:
    filtered = [t for t in trades if t['sl_pips'] >= min_sl]
    if filtered:
        wins = sum(1 for t in filtered if t['pnl'] > 0)
        gross_p = sum(t['pnl'] for t in filtered if t['pnl'] > 0)
        gross_l = abs(sum(t['pnl'] for t in filtered if t['pnl'] < 0))
        pf = gross_p / gross_l if gross_l > 0 else 999
        print(f'SL >= {min_sl}: {len(filtered):3d} trades, WR={wins/len(filtered)*100:.1f}%, PF={pf:.2f}')

# Analyze by max SL
print('\n=== BY MAX SL PIPS ===')
for max_sl in [15, 20, 25, 30, 40]:
    filtered = [t for t in trades if t['sl_pips'] <= max_sl]
    if filtered:
        wins = sum(1 for t in filtered if t['pnl'] > 0)
        gross_p = sum(t['pnl'] for t in filtered if t['pnl'] > 0)
        gross_l = abs(sum(t['pnl'] for t in filtered if t['pnl'] < 0))
        pf = gross_p / gross_l if gross_l > 0 else 999
        print(f'SL <= {max_sl}: {len(filtered):3d} trades, WR={wins/len(filtered)*100:.1f}%, PF={pf:.2f}')

# Analyze by ATR ranges
print('\n=== BY MAX ATR ===')
for max_atr in [0.0003, 0.0004, 0.0005, 0.0006, 0.0008]:
    filtered = [t for t in trades if t['atr'] <= max_atr]
    if filtered and len(filtered) >= 50:
        wins = sum(1 for t in filtered if t['pnl'] > 0)
        gross_p = sum(t['pnl'] for t in filtered if t['pnl'] > 0)
        gross_l = abs(sum(t['pnl'] for t in filtered if t['pnl'] < 0))
        pf = gross_p / gross_l if gross_l > 0 else 999
        print(f'ATR <= {max_atr}: {len(filtered):3d} trades, WR={wins/len(filtered)*100:.1f}%, PF={pf:.2f}')

# Analyze by CCI ranges
print('\n=== BY MIN CCI ===')
for min_cci in [100, 120, 140, 160, 180, 200]:
    filtered = [t for t in trades if t['cci'] >= min_cci]
    if filtered and len(filtered) >= 50:
        wins = sum(1 for t in filtered if t['pnl'] > 0)
        gross_p = sum(t['pnl'] for t in filtered if t['pnl'] > 0)
        gross_l = abs(sum(t['pnl'] for t in filtered if t['pnl'] < 0))
        pf = gross_p / gross_l if gross_l > 0 else 999
        print(f'CCI >= {min_cci}: {len(filtered):3d} trades, WR={wins/len(filtered)*100:.1f}%, PF={pf:.2f}')
