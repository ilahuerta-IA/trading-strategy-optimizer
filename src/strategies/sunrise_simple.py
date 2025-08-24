"""Simplified Sunrise Strategy
=================================


ENTRY (long only)
-----------------
1. Confirmation EMA crosses ABOVE ANY of fast / medium / slow (first bullish momentum sign).
2. Previous candle bullish (close[1] > open[1]).
3. Optional ordering filter (confirmation EMA above all other EMAs).
4. Optional price filter (close > filter EMA).
5. Optional angle filte        # Use stored exit reason from notify_order
        exit_reason = getattr(self, 'last_exit_reason', "UNKNOWN")
6. Optional SECURITY WINDOW: forbid a *new* entry for N bars AFTER THE LAST EXIT.
7. Optional entry price filter: during next `entry_price_filter_window` bars after an entry require close > last_entry_price.

EXIT
----
1. Initial ATR based stop & take profit:
         stop  = entry_bar_low  - ATR * atr_sl_multiplier
         take  = entry_bar_high + ATR * atr_tp_multiplier
2. Optional bar-count exit (close after N bars in position).
3. Optional EMA crossover exit (exit EMA crossing above confirm EMA).

IMPLEMENTATION NOTES
--------------------
* Manual independent stop & limit orders (no bracket).
* No re-entry / ROLL logic – explicitly removed per request.
* Minimal state: only what's strictly needed for the logic.
* Extensive inline comments explaining every critical step.

CONFIGURATION
-------------
Parameters live in the Strategy (so you can still pass overrides when adding
the strategy).  The __main__ block below uses SIMPLE FLAGS (no argparse)

DISCLAIMER
----------
Educational example ONLY. Not investment advice. Markets involve risk; past
performance does not guarantee future results. Validate logic & data quality
before using in any live or simulated trading environment.
"""
from __future__ import annotations
import math
from pathlib import Path
import backtrader as bt

# =============================================================
# CONFIGURATION PARAMETERS - EASILY EDITABLE AT TOP OF FILE
# =============================================================

# === EASY INSTRUMENT SELECTION ===
# Uncomment ONE line below to test different forex instruments:
DATA_FILENAME = 'XAUUSD_5m_5Yea.csv'     # Gold vs USD (PF=1.09)
#DATA_FILENAME = 'XAGUSD_5m_5Yea.csv'     # Silver vs USD (PF=0.89) 
#DATA_FILENAME = 'EURUSD_5m_5Yea.csv'       # Euro vs USD (PF=1.21)
#DATA_FILENAME = 'USDCHF_5m_5Yea.csv'       # USD vs Swiss Franc (PF=1.03)
#DATA_FILENAME = 'AUDUSD_5m_5Yea.csv'       # Australian Dollar vs USD (PF=1.10)
#DATA_FILENAME = 'GBPUSD_5m_5Yea.csv'       # British Pound vs USD (PF=1.02)

# === GENERAL SETTINGS ===
FROMDATE = '2022-07-10'               # Extended test period
TODATE = '2025-07-25'                 # Extended test period
STARTING_CASH = 100000.0
QUICK_TEST = False                    # If True: auto-reduce to last 10 days
LIMIT_BARS = 0                        # >0 = stop after N bars processed
ENABLE_PLOT = True                    # Plot final result (if matplotlib available)

# === FOREX CONFIGURATION ===
ENABLE_FOREX_CALC = True              # Enable forex position calculations (AUTO-DETECTS INSTRUMENT)
FOREX_INSTRUMENT = 'AUTO'             # AUTO, XAUUSD, XAGUSD, EURUSD, USDCHF, AUDUSD, GBPUSD
TEST_FOREX_MODE = False               # If True: Quick test with forex calculations


class SunriseSimple(bt.Strategy):
    params = dict(
        # Indicator lengths
        ema_fast_length=14,
        ema_medium_length=18,
        ema_slow_length=24,
        ema_confirm_length=1,
        ema_filter_price_length=50, #¡¡
        ema_exit_length=25, #??
        # ATR / targets 
        atr_length=10,
        atr_sl_multiplier=2.5,
        atr_tp_multiplier=12.0,
        # Filters / angles 
        use_ema_order_condition=False,
        use_price_filter_ema=True,
        use_angle_filter=True,
        min_angle=75.0,
        angle_scale_factor=10000.0,
        # Security window after exit
        use_security_window=True,
        security_window_bars=60,  
        # Pullback entry system
        use_pullback_entry=True,  # Restore pullback mode
        pullback_max_candles=1,  # Balanced - original 3 red candles
        entry_window_periods=10,  # Balanced - original 5 periods
        entry_pip_offset=2.0,  # Balanced - original 1.0 pips
        # EXITS 5
        use_bar_count_exit=False, #¡¡ # Test different exit methods
        bar_count_exit=5,  
        use_ema_crossover_exit=False, #??
        # Sizing / logging
        size=1,
        enable_risk_sizing=True, #¡¡
        risk_percent=0.01,  # Reduced from 0.01 (1%) to 0.005 (0.5%) for safer forex trading
        contract_size=100000,
        print_signals=True,
        # Forex-specific settings for multiple instruments
        use_forex_position_calc=True,    # Enable forex-specific calculations
        forex_instrument='AUTO',          # Instrument type: AUTO, XAUUSD, XAGUSD, EURUSD, USDCHF, AUDUSD, GBPUSD
        forex_base_currency='AUTO',       # Base currency (auto-detected from instrument)
        forex_quote_currency='AUTO',      # Quote currency (auto-detected from instrument)
        forex_pip_value=0.0001,           # Standard pip value
        forex_pip_decimal_places=4,       # Standard decimal places
        forex_lot_size=100000,            # Standard lot size (100,000 units of base currency)
        forex_micro_lot_size=0.01,        # Micro lot size (0.01 standard lots)
        forex_spread_pips=2.0,            # Typical spread in pips
        forex_margin_required=3.33,       # Margin requirement as percentage (3.33% = 30:1 leverage)
        # Account settings for forex calculations
        account_currency='USD',           # Account denomination
        account_leverage=30.0,            # Account leverage (matches broker setting)
        # Plotting
        plot_result=True,
        buy_sell_plotdist=0.0005,
        plot_sltp_lines=True,
        pip_value=0.0001,
    )

    def _init_debug_logging(self):
        """Initialize comprehensive debug logging to file"""
        from datetime import datetime
        import os
        
        # Create debug directory if it doesn't exist
        debug_dir = Path(__file__).resolve().parent.parent.parent / 'debug'
        debug_dir.mkdir(exist_ok=True)
        
        # Create timestamped debug file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_filename = f"entry_debug_{timestamp}.log"
        debug_path = debug_dir / debug_filename
        
        try:
            self.debug_file = open(debug_path, 'w', encoding='utf-8')
            self.debug_file.write(f"=== SUNRISE ENTRY DEBUG LOG ===\n")
            self.debug_file.write(f"Started: {datetime.now()}\n")
            self.debug_file.write(f"Data File: {self._data_filename}\n")
            self.debug_file.write(f"Forex Mode: {self.p.use_forex_position_calc}\n")
            self.debug_file.write(f"Pullback Mode: {self.p.use_pullback_entry}\n")
            self.debug_file.write("=" * 50 + "\n\n")
            self.debug_file.flush()
            print(f"📝 DEBUG LOGGING: {debug_path}")
        except Exception as e:
            print(f"WARNING: Could not create debug file: {e}")
            self.debug_file = None
    
    def _log_debug(self, message):
        """Log debug message to file and console"""
        if self.debug_file:
            try:
                self.debug_file.write(f"{message}\n")
                self.debug_file.flush()
            except:
                pass
        if self.p.print_signals:
            print(f"DEBUG: {message}")
    
    def _close_debug_logging(self):
        """Close debug file"""
        if self.debug_file:
            try:
                self.debug_file.write(f"\n=== DEBUG SESSION ENDED ===\n")
                self.debug_file.write(f"Total Signals: {self.entry_signal_count}\n")
                self.debug_file.write(f"Blocked: {self.blocked_entry_count}\n")
                self.debug_file.write(f"Successful: {self.successful_entry_count}\n")
                self.debug_file.close()
            except:
                pass
            self.debug_file = None

    @staticmethod
    def _cross_above(a, b):
        """Return True if `a` crossed above `b` on the current bar.
        
        Pine Script ta.crossover() equivalent:
        - Current bar: a[0] > b[0] 
        - Previous bar: a[-1] <= b[-1]
        - Must be EXACT crossover (not just above)
        """
        try:
            current_a = float(a[0])
            current_b = float(b[0])
            previous_a = float(a[-1])
            previous_b = float(b[-1])
            
            # Pine Script crossover logic: current > AND previous <=
            crossover = (current_a > current_b) and (previous_a <= previous_b)
            
            return crossover
        except (IndexError, ValueError, TypeError):
            return False

    def _angle(self):
        """Compute instantaneous angle (degrees) of the confirm EMA slope.

        Equivalent to Pine's math.atan(rise/run) * 180 / pi with run=1.
        The rise gets magnified by `angle_scale_factor` for sensitivity.
        """
        try:
            current_ema = float(self.ema_confirm[0])
            previous_ema = float(self.ema_confirm[-1])
            
            # Pine Script: math.atan((ema_confirm - ema_confirm[1]) * factor_escala_angulo) * 180 / math.pi
            rise = (current_ema - previous_ema) * self.p.angle_scale_factor
            angle_radians = math.atan(rise)  # run = 1 (1 bar)
            angle_degrees = math.degrees(angle_radians)
            
            return angle_degrees
        except (IndexError, ValueError, TypeError, ZeroDivisionError):
            return float('nan')
    
    def _calculate_forex_position_size(self, entry_price, stop_loss_price):
        """Calculate optimal position size for forex trading with proper risk management.
        
        Args:
            entry_price: Entry price level
            stop_loss_price: Stop loss price level
            
        Returns:
            tuple: (lot_size, contracts, margin_required, pip_risk, position_value)
        """
        if not self.p.use_forex_position_calc:
            return None, None, None, None, None
            
        # Calculate risk in pips
        price_difference = abs(entry_price - stop_loss_price)
        pip_risk = price_difference / self.p.forex_pip_value
        
        # Account equity and risk amount
        account_equity = self.broker.get_value()
        risk_amount = account_equity * self.p.risk_percent
        
        # Calculate value per pip for different lot sizes
        # For most pairs: 1 standard lot (100,000 units) = $10 per pip (0.0001 price move)
        # For precious metals (gold/silver): calculate based on lot size and pip value
        
        if self.p.forex_instrument.startswith(('XAU', 'XAG')):
            value_per_pip_per_lot = self.p.forex_lot_size * self.p.forex_pip_value  # Precious metals specific
        else:
            if self.p.forex_quote_currency == 'USD':
                value_per_pip_per_lot = (self.p.forex_pip_value * self.p.forex_lot_size)
            else:
                value_per_pip_per_lot = 10.0  # Cross currency pairs
        
        # Calculate optimal lot size
        if pip_risk > 0:
            optimal_lots = risk_amount / (pip_risk * value_per_pip_per_lot)
            optimal_lots = max(self.p.forex_micro_lot_size, 
                             round(optimal_lots / self.p.forex_micro_lot_size) * self.p.forex_micro_lot_size)
        else:
            return None, None, None, None, None
        
        # REMOVE RESTRICTIVE LIMITS: Let user control their own risk
        # Only apply absolute minimum safety to prevent system errors
        
        # Minimum position size check (very minimal)
        min_lots = 0.01  # Minimum 0.01 lots
        if optimal_lots < min_lots:
            optimal_lots = min_lots
            
        # Maximum absolute limit (very high - 500 lots)
        max_absolute_lots = 500.0
        if optimal_lots > max_absolute_lots:
            optimal_lots = max_absolute_lots
            
        # Calculate position value and margin required
        position_value = optimal_lots * self.p.forex_lot_size * entry_price
        margin_required = position_value * (self.p.forex_margin_required / 100.0)
        
        # Convert to Backtrader contracts (Use lot size directly, not underlying units)
        if self.p.forex_instrument.startswith(('XAU', 'XAG')):
            # For precious metals: Use lot size directly (1 contract = 1 lot)
            contracts = max(1, int(optimal_lots * 100))  # Scale lots to reasonable contract size
            print(f"DEBUG_POSITION_SIZE: optimal_lots={optimal_lots:.2f}, contracts={contracts}")
        else:
            # For forex pairs: Use lot size directly 
            contracts = max(1, int(optimal_lots * 100))  # Scale lots to reasonable contract size
            print(f"DEBUG_POSITION_SIZE: optimal_lots={optimal_lots:.2f}, contracts={contracts}")
        
        return optimal_lots, contracts, margin_required, pip_risk, position_value
    
    def _format_forex_trade_info(self, entry_price, stop_loss, take_profit, lot_size, pip_risk, position_value, margin_required):
        """Format comprehensive forex trade information for logging.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            lot_size: Position size in lots
            pip_risk: Risk in pips
            position_value: Total position value
            margin_required: Margin requirement
            
        Returns:
            str: Formatted trade information
        """
        if not self.p.use_forex_position_calc:
            return ""
            
        # Calculate potential profit in pips
        if take_profit and entry_price:
            profit_pips = abs(take_profit - entry_price) / self.p.forex_pip_value
            risk_reward = profit_pips / pip_risk if pip_risk > 0 else 0
        else:
            profit_pips = 0
            risk_reward = 0
            
        # Calculate monetary values based on instrument type
        if self.p.forex_instrument.startswith(('XAU', 'XAG')):
            # Precious metals: pip value from configuration
            pip_value_per_lot = self.p.forex_lot_size * self.p.forex_pip_value
        else:
            # Standard USD pairs: $10 per pip for standard lot
            pip_value_per_lot = 10.0
            
        risk_amount = pip_risk * lot_size * pip_value_per_lot
        profit_potential = profit_pips * lot_size * pip_value_per_lot
        spread_cost = self.p.forex_spread_pips * lot_size * pip_value_per_lot
        
        # Format units based on instrument
        if self.p.forex_instrument.startswith(('XAU', 'XAG')):
            units_desc = f"{lot_size * self.p.forex_lot_size:.0f} oz"
        else:
            units_desc = f"{lot_size * self.p.forex_lot_size:,.0f} {self.p.forex_base_currency}"
        
        # Format prices based on decimal places
        price_format = f"{{:.{self.p.forex_pip_decimal_places}f}}"
        
        return (f"\n--- FOREX TRADE DETAILS ({self.p.forex_instrument}) ---\n"
                f"Position Size: {lot_size:.2f} lots ({units_desc})\n"
                f"Position Value: ${position_value:,.2f}\n"
                f"Margin Required: ${margin_required:,.2f} ({self.p.forex_margin_required}%)\n"
                f"Entry: {price_format.format(entry_price)} | SL: {price_format.format(stop_loss)} | TP: {price_format.format(take_profit)}\n"
                f"Risk: {pip_risk:.1f} pips (${risk_amount:.2f}) | Profit: {profit_pips:.1f} pips (${profit_potential:.2f})\n"
                f"Risk/Reward: 1:{risk_reward:.2f} | Spread Cost: ${spread_cost:.2f}\n"
                f"Account Leverage: {self.p.account_leverage:.0f}:1 | Account: {self.p.account_currency}")
    
    def _validate_forex_setup(self):
        """Validate forex configuration against data file.
        
        Returns:
            bool: True if configuration is valid for current data
        """
        if not self.p.use_forex_position_calc:
            return True
            
        # Check if data filename matches instrument setting
        data_filename = getattr(self, '_data_filename', '')
        if 'XAUUSD' not in data_filename.upper() and self.p.forex_instrument == 'XAUUSD':
            print(f"WARNING: Forex instrument set to {self.p.forex_instrument} but data file is {data_filename}")
        if 'XAGUSD' not in data_filename.upper() and self.p.forex_instrument == 'XAGUSD':
            print(f"WARNING: Forex instrument set to {self.p.forex_instrument} but data file is {data_filename}")
            
        # Validate price ranges for precious metals
        if hasattr(self.data, 'close') and len(self.data.close) > 0:
            current_price = float(self.data.close[0])
            if self.p.forex_instrument == 'XAUUSD' and (current_price < 500 or current_price > 5000):
                print(f"WARNING: Price {current_price} seems unusual for XAUUSD")
            elif self.p.forex_instrument == 'XAGUSD' and (current_price < 10 or current_price > 100):
                print(f"WARNING: Price {current_price} seems unusual for XAGUSD")
                
        # Check pip value consistency for precious metals
        if self.p.forex_instrument == 'XAUUSD' and self.p.forex_pip_value != 0.01:
            print(f"INFO: XAUUSD typically uses pip value of 0.01, current setting: {self.p.forex_pip_value}")
        elif self.p.forex_instrument == 'XAGUSD' and self.p.forex_pip_value != 0.001:
            print(f"INFO: XAGUSD typically uses pip value of 0.001, current setting: {self.p.forex_pip_value}")
            
        return True
    
    def _get_forex_instrument_config(self, instrument_name=None):
        """Get forex configuration for specific instrument.
        
        Args:
            instrument_name: Override instrument name, otherwise use data filename
            
        Returns:
            dict: Configuration dictionary for the instrument
        """
        # Auto-detect instrument from data filename if not specified
        if instrument_name is None or instrument_name == 'AUTO':
            data_filename = getattr(self, '_data_filename', '').upper()
            
            # Try to detect instrument from filename
            if 'XAUUSD' in data_filename:
                instrument_name = 'XAUUSD'
            elif 'XAGUSD' in data_filename:
                instrument_name = 'XAGUSD'
            elif 'EURUSD' in data_filename:
                instrument_name = 'EURUSD'
            elif 'USDCHF' in data_filename:
                instrument_name = 'USDCHF'
            elif 'AUDUSD' in data_filename:
                instrument_name = 'AUDUSD'
            elif 'GBPUSD' in data_filename:
                instrument_name = 'GBPUSD'
            else:
                instrument_name = 'DEFAULT'
        
        # Forex instrument configurations
        configs = {
            'XAUUSD': {  # Gold vs USD
                'base_currency': 'XAU',
                'quote_currency': 'USD',
                'pip_value': 0.01,           # 1 pip = $0.01 for gold
                'pip_decimal_places': 2,
                'lot_size': 100,             # 100 oz
                'margin_required': 0.5,      # 0.5% (higher margin for commodities)
                'typical_spread': 2.0
            },
            'XAGUSD': {  # Silver vs USD
                'base_currency': 'XAG',
                'quote_currency': 'USD',
                'pip_value': 0.001,          # 1 pip = $0.001 for silver
                'pip_decimal_places': 3,
                'lot_size': 5000,            # 5,000 oz (standard silver contract)
                'margin_required': 1.0,      # 1.0% (higher margin for commodities)
                'typical_spread': 3.0
            },
            'EURUSD': {  # Euro vs USD
                'base_currency': 'EUR',
                'quote_currency': 'USD',
                'pip_value': 0.0001,         # 1 pip = $0.0001
                'pip_decimal_places': 4,
                'lot_size': 100000,          # 100,000 EUR
                'margin_required': 3.33,     # 3.33% (30:1 leverage)
                'typical_spread': 1.5
            },
            'USDCHF': {  # USD vs Swiss Franc
                'base_currency': 'USD',
                'quote_currency': 'CHF',
                'pip_value': 0.0001,         # 1 pip = $0.0001
                'pip_decimal_places': 4,
                'lot_size': 100000,          # 100,000 USD
                'margin_required': 3.33,     # 3.33% (30:1 leverage)
                'typical_spread': 2.2
            },
            'AUDUSD': {  # Australian Dollar vs USD
                'base_currency': 'AUD',
                'quote_currency': 'USD',
                'pip_value': 0.0001,         # 1 pip = $0.0001
                'pip_decimal_places': 4,
                'lot_size': 100000,          # 100,000 AUD
                'margin_required': 3.33,     # 3.33% (30:1 leverage)
                'typical_spread': 1.9
            },
            'GBPUSD': {  # British Pound vs USD
                'base_currency': 'GBP',
                'quote_currency': 'USD',
                'pip_value': 0.0001,         # 1 pip = $0.0001
                'pip_decimal_places': 4,
                'lot_size': 100000,          # 100,000 GBP
                'margin_required': 3.33,     # 3.33% (30:1 leverage)
                'typical_spread': 2.0
            },
            'DEFAULT': {  # Default configuration
                'base_currency': 'BASE',
                'quote_currency': 'QUOTE',
                'pip_value': 0.0001,
                'pip_decimal_places': 4,
                'lot_size': 100000,
                'margin_required': 3.33,
                'typical_spread': 2.0
            }
        }
        
        return configs.get(instrument_name, configs['DEFAULT'])
    
    def _apply_forex_config(self):
        """Apply forex configuration based on instrument detection."""
        if not self.p.use_forex_position_calc:
            return
            
        # Get configuration for detected/specified instrument
        config = self._get_forex_instrument_config(self.p.forex_instrument)
        
        # Update parameters with detected configuration
        if self.p.forex_base_currency == 'AUTO':
            self.p.forex_base_currency = config['base_currency']
        if self.p.forex_quote_currency == 'AUTO':
            self.p.forex_quote_currency = config['quote_currency']
        
        # Store detected instrument for logging
        self._detected_instrument = 'DEFAULT'
        data_filename = getattr(self, '_data_filename', '').upper()
        for instrument in ['XAUUSD', 'EURUSD', 'USDCHF', 'AUDUSD', 'GBPUSD']:
            if instrument in data_filename:
                self._detected_instrument = instrument
                break
                
        # Apply detected configuration (override defaults if AUTO)
        if self.p.forex_instrument == 'AUTO':
            self.p.forex_pip_value = config['pip_value']
            self.p.forex_pip_decimal_places = config['pip_decimal_places']
            self.p.forex_lot_size = config['lot_size']
            self.p.forex_margin_required = config['margin_required']
            self.p.forex_spread_pips = config['typical_spread']
            # Update the instrument parameter with detected value
            self.p.forex_instrument = self._detected_instrument
                
        # Log forex configuration
        if self.p.forex_instrument == 'AUTO':
            print(f"🔍 AUTO-DETECTED: {self._detected_instrument} from filename: {data_filename}")
        else:
            print(f"🎯 MANUAL CONFIG: {self.p.forex_instrument}")
            
        print(f"💱 Forex Config: {self.p.forex_base_currency}/{self.p.forex_quote_currency}")
        print(f"📏 Pip Value: {self.p.forex_pip_value} | Lot Size: {self.p.forex_lot_size:,} | Margin: {self.p.forex_margin_required}%")

    def __init__(self):
            d = self.data
            # Indicators
            self.ema_fast = bt.ind.EMA(d.close, period=self.p.ema_fast_length)
            self.ema_medium = bt.ind.EMA(d.close, period=self.p.ema_medium_length)
            self.ema_slow = bt.ind.EMA(d.close, period=self.p.ema_slow_length)
            self.ema_confirm = bt.ind.EMA(d.close, period=self.p.ema_confirm_length)
            self.ema_filter_price = bt.ind.EMA(d.close, period=self.p.ema_filter_price_length)
            self.ema_exit = bt.ind.EMA(d.close, period=self.p.ema_exit_length)
            self.atr = bt.ind.ATR(d, period=self.p.atr_length)

            # MANUAL ORDER MANAGEMENT - Replace buy_bracket with simple orders
            self.order = None  # Track current pending order
            self.stop_order = None  # Track stop loss order
            self.limit_order = None  # Track take profit order
            self.pending_close = False  # Flag to prevent new entries while closing position
            
            # Current protective price levels (float) for plotting / decisions
            self.stop_level = None
            self.take_level = None
            # Book-keeping for filters
            self.last_entry_bar = None
            self.last_exit_bar = None
            self.last_entry_price = None
            # Track initial stop level
            self.initial_stop_level = None
            
            # Track trade history for ta.barssince() logic
            self.trade_exit_bars = []  # Store bars where trades closed (ta.barssince equivalent)
            
            # Prevent entry and exit on same bar
            self.exit_this_bar = False  # Flag to prevent entry on exit bar
            self.last_exit_bar_current = None  # Track if we exited this specific bar #3
            
            # PULLBACK ENTRY STATE MACHINE
            self.pullback_state = "NORMAL"  # States: NORMAL, WAITING_PULLBACK, WAITING_BREAKOUT
            self.pullback_red_count = 0  # Count of consecutive red candles
            self.first_red_high = None  # High of first red candle in pullback
            self.entry_window_start = None  # Bar when entry window opened
            self.breakout_target = None  # Price target for entry breakout

            # Basic stats
            self.trades = 0
            self.wins = 0
            self.losses = 0
            self.gross_profit = 0.0
            self.gross_loss = 0.0
            
            # Track exit reason for notify_trade
            self.last_exit_reason = "UNKNOWN"
            
            # EXHAUSTIVE DEBUGGING - Track all entry signals and blocking reasons
            self.debug_file = None
            self.entry_signal_count = 0
            self.blocked_entry_count = 0
            self.successful_entry_count = 0
            
            # Store data filename for forex validation
            self._data_filename = getattr(self.data._dataname, 'name', 
                                        getattr(self.data, '_dataname', ''))
            if isinstance(self._data_filename, str):
                self._data_filename = Path(self._data_filename).name
            
            # Apply forex configuration based on instrument detection
            if self.p.use_forex_position_calc:
                self._apply_forex_config()
                self.p.contract_size = self.p.forex_lot_size  # Sync the contract size with the detected lot size
                self._validate_forex_setup()
                
            # Initialize debug logging
            self._init_debug_logging()

    def next(self):
        # RESET exit flag at start of each new bar
        self.exit_this_bar = False
        
        # CHECK for pending close operation - skip all logic if waiting for close
        if hasattr(self, 'pending_close') and self.pending_close:
            if not self.position:
                # Position closed successfully, clear flag
                self.pending_close = False
                print("DEBUG: Close operation completed, clearing pending_close flag")
            else:
                # Still waiting for close to complete
                return
        
        # EXHAUSTIVE DEBUG LOGGING - Track every bar
        dt = bt.num2date(self.data.datetime[0])
        current_bar = len(self)
        current_close = float(self.data.close[0])
        
        # DISABLED: Log basic bar info every 100 bars or when position changes
        # if current_bar % 100 == 0 or (self.position and not hasattr(self, '_was_in_position')) or (not self.position and hasattr(self, '_was_in_position')):
        #     position_status = f"POSITION: {self.position.size} lots" if self.position else "NO_POSITION"
        #     self._log_debug(f"Bar {current_bar} | {dt:%Y-%m-%d %H:%M} | Close: {current_close:.5f} | {position_status}")
        
        # Track position state changes
        if self.position:
            self._was_in_position = True
        elif hasattr(self, '_was_in_position'):
            delattr(self, '_was_in_position')
        
        # CANCEL ALL PENDING ORDERS when we have no position (cleanup phantom orders)
        if not self.position:
            orders_canceled = 0
            if self.order:
                try:
                    self.cancel(self.order)
                    orders_canceled += 1
                    self._log_debug(f"CANCELED pending entry order: {self.order.ref}")
                except:
                    pass
                self.order = None
                    
            if self.stop_order:
                try:
                    self.cancel(self.stop_order)
                    orders_canceled += 1
                    self._log_debug(f"CANCELED stop order: {self.stop_order.ref}")
                except:
                    pass
                self.stop_order = None
                    
            if self.limit_order:
                try:
                    self.cancel(self.limit_order)
                    orders_canceled += 1
                    self._log_debug(f"CANCELED limit order: {self.limit_order.ref}")
                except:
                    pass
                self.limit_order = None
                    
            if orders_canceled > 0:
                self._log_debug(f"CLEANUP: Canceled {orders_canceled} phantom orders at bar {current_bar}")
                if self.p.print_signals:
                    print(f"CLEANUP: Canceled {orders_canceled} phantom orders")
            
            # Reset pullback state when no position (fresh start)
            if self.p.use_pullback_entry and orders_canceled > 0:
                self._reset_pullback_state()

        # Check if we have pending ENTRY orders (but allow protective orders)
        if self.order:
            self._log_debug(f"SKIP: Pending entry order {self.order.ref} at bar {current_bar}")
            return  # Wait for entry order to complete before doing anything else

        dt = bt.num2date(self.data.datetime[0])

        # POSITION MANAGEMENT
        if self.position:
            # Check exit conditions
            bars_since_entry = len(self) - self.last_entry_bar if self.last_entry_bar is not None else 0
            
            # Timed exit (Pine Script logic: barsSinceEntry >= barras_salida)
            if self.p.use_bar_count_exit and bars_since_entry >= self.p.bar_count_exit and not self.exit_this_bar:
                print(f"BAR_EXIT at {dt:%Y-%m-%d %H:%M} after {bars_since_entry} bars (target: {self.p.bar_count_exit})")
                self.order = self.close()
                self.exit_this_bar = True  # Mark exit action taken
                return

            # EMA crossover exit
            if self.p.use_ema_crossover_exit and self._cross_above(self.ema_exit, self.ema_confirm) and not self.exit_this_bar:
                print(f"EMA_EXIT at {dt:%Y-%m-%d %H:%M}")
                self.order = self.close()
                self.exit_this_bar = True  # Mark exit action taken
                return

            # Continue holding - no new entry logic when in position
            return

        # ENTRY LOGIC (only when no position and no pending orders)
        
        # Pine Script prevention: No entry if exit was taken on same bar
        if self.exit_this_bar:
            self._log_debug(f"BLOCK_EXIT_SAME_BAR: Exit action already taken this bar {current_bar}")
            if self.p.print_signals:
                print(f"SKIP entry: exit action already taken this bar")
            return
        
        # Security window check (Pine Script ta.barssince equivalent)
        # Pine Script: ta.barssince(strategy.closedtrades.exit_time changed)
        if self.p.use_security_window and self.trade_exit_bars:
            bars_since_last_exit = current_bar - self.trade_exit_bars[-1]
            if bars_since_last_exit < int(self.p.security_window_bars):
                # Silent debug logging to avoid terminal spam - only log to file
                if self.debug_file:
                    try:
                        self.debug_file.write(f"BLOCK_SECURITY_WINDOW: {bars_since_last_exit} < {self.p.security_window_bars} bars since last exit\n")
                        self.debug_file.flush()
                    except:
                        pass
                return

        # DETAILED ENTRY SIGNAL ANALYSIS
        self.entry_signal_count += 1
        entry_result = self._full_entry_signal_with_debug(current_bar, dt)
        
        if not entry_result:
            self.blocked_entry_count += 1
            return

        # Calculate position size and create buy order
        atr_now = float(self.atr[0]) if not math.isnan(float(self.atr[0])) else 0.0
        if atr_now <= 0:
            return

        entry_price = float(self.data.close[0])
        bar_low = float(self.data.low[0])
        bar_high = float(self.data.high[0])
        self.stop_level = bar_low - atr_now * self.p.atr_sl_multiplier
        self.take_level = bar_high + atr_now * self.p.atr_tp_multiplier
        self.initial_stop_level = self.stop_level

        # Position sizing (Pine Script equivalent calculation)
        if self.p.enable_risk_sizing:
            raw_risk = entry_price - self.stop_level
            if raw_risk <= 0:
                return
            equity = self.broker.get_value()
            risk_val = equity * self.p.risk_percent
            risk_per_contract = raw_risk * self.p.contract_size
            if risk_per_contract <= 0:
                return
            contracts = max(int(risk_val / risk_per_contract), 1)
        else:
            contracts = int(self.p.size)
        
        if contracts <= 0:
            return
            
        bt_size = contracts * self.p.contract_size

        # Always recalculate bt_size before placing the order
        bt_size = contracts * self.p.contract_size

        # CRITICAL FIX: Ensure clean state before new entry
        if self.position:
            print(f"WARNING: Existing position detected (size={self.position.size}) - closing before new entry")
            # Cancel all pending orders and close position
            self._cancel_all_pending_orders()
            self.order = self.close()
            self.pending_close = True  # Flag to prevent new entries until close completes
            return  # Wait for position to close before entering new trade

        # 1. Place market buy order
        self.order = self.buy(size=bt_size)

        # Only print the entry message AFTER the buy order has been submitted
        if self.p.print_signals:
            rr = (self.take_level - entry_price) / (entry_price - self.stop_level) if (entry_price - self.stop_level) > 0 else float('nan')
            print(f"ENTRY PLACED {dt:%Y-%m-%d %H:%M} price={entry_price:.5f} size={bt_size} SL={self.stop_level:.5f} TP={self.take_level:.5f} RR={rr:.2f}")

        self.last_entry_price = entry_price
        self.last_entry_bar = current_bar

    def _full_entry_signal_with_debug(self, current_bar, dt):
        """Detailed entry signal analysis with comprehensive debug logging.
        
        This method performs the same logic as _full_entry_signal() but with
        exhaustive debug logging to identify exactly why entries are blocked.
        """
        # PULLBACK ENTRY SYSTEM STATE MACHINE
        if self.p.use_pullback_entry:
            result = self._handle_pullback_entry(dt)
            if not result:
                # self._log_debug(f"BLOCK_PULLBACK: Pullback entry system rejected signal at bar {current_bar}")
                pass
            return result
        
        # STANDARD ENTRY LOGIC (when pullback is disabled)
        self._log_debug(f"EVALUATING_ENTRY: Bar {current_bar} | {dt:%Y-%m-%d %H:%M}")
        
        # 1. Previous candle bullish check
        try:
            prev_close = self.data.close[-1]
            prev_open = self.data.open[-1]
            prev_bull = prev_close > prev_open
            self._log_debug(f"  1. PREV_BULL: {prev_bull} (close[-1]={prev_close:.5f} > open[-1]={prev_open:.5f})")
        except IndexError:
            self._log_debug(f"  1. PREV_BULL: FALSE (IndexError - not enough data)")
            return False

        # 2. EMA crossover check (ANY of the three)
        cross_fast = self._cross_above(self.ema_confirm, self.ema_fast)
        cross_medium = self._cross_above(self.ema_confirm, self.ema_medium) 
        cross_slow = self._cross_above(self.ema_confirm, self.ema_slow)
        cross_any = cross_fast or cross_medium or cross_slow
        
        self._log_debug(f"  2. EMA_CROSS: fast={cross_fast}, medium={cross_medium}, slow={cross_slow}, any={cross_any}")
        if cross_any:
            cross_type = []
            if cross_fast: cross_type.append("FAST")
            if cross_medium: cross_type.append("MEDIUM") 
            if cross_slow: cross_type.append("SLOW")
            self._log_debug(f"     Cross types: {', '.join(cross_type)}")
        
        if not (prev_bull and cross_any):
            self._log_debug(f"  BLOCK_BASIC: prev_bull={prev_bull} AND cross_any={cross_any} = {prev_bull and cross_any}")
            return False

        # 3. EMA order condition
        if self.p.use_ema_order_condition:
            confirm_val = self.ema_confirm[0]
            fast_val = self.ema_fast[0]
            medium_val = self.ema_medium[0]
            slow_val = self.ema_slow[0]
            
            ema_order_ok = (confirm_val > fast_val and confirm_val > medium_val and confirm_val > slow_val)
            self._log_debug(f"  3. EMA_ORDER: {ema_order_ok} (confirm={confirm_val:.5f} > fast={fast_val:.5f} & medium={medium_val:.5f} & slow={slow_val:.5f})")
            
            if not ema_order_ok:
                self._log_debug(f"  BLOCK_EMA_ORDER: Failed order condition")
                return False
        else:
            self._log_debug(f"  3. EMA_ORDER: DISABLED")

        # 4. Price filter EMA
        if self.p.use_price_filter_ema:
            current_close = self.data.close[0]
            filter_val = self.ema_filter_price[0]
            price_above_filter = current_close > filter_val
            self._log_debug(f"  4. PRICE_FILTER: {price_above_filter} (close={current_close:.5f} > filter_ema={filter_val:.5f})")
            
            if not price_above_filter:
                self._log_debug(f"  BLOCK_PRICE_FILTER: Price below filter EMA")
                return False
        else:
            self._log_debug(f"  4. PRICE_FILTER: DISABLED")

        # 5. Angle filter
        if self.p.use_angle_filter:
            current_angle = self._angle()
            angle_ok = current_angle > self.p.min_angle
            self._log_debug(f"  5. ANGLE_FILTER: {angle_ok} (angle={current_angle:.2f} > min={self.p.min_angle})")
            
            if not angle_ok:
                self._log_debug(f"  BLOCK_ANGLE_FILTER: Angle too low")
                return False
        else:
            self._log_debug(f"  5. ANGLE_FILTER: DISABLED")

        # All filters passed
        self._log_debug(f"  SUCCESS_ALL_FILTERS: All entry conditions satisfied at bar {current_bar}")
        return True

    def _full_entry_signal(self):
        """Return True if ALL *full* entry constraints pass.

        Mirrors the Pine Script required + optional filters.
        Includes optional pullback entry logic.
        """
        dt = bt.num2date(self.data.datetime[0])
        
        # PULLBACK ENTRY SYSTEM STATE MACHINE
        if self.p.use_pullback_entry:
            return self._handle_pullback_entry(dt)
        
        # STANDARD ENTRY LOGIC (when pullback is disabled)
        return self._standard_entry_signal(dt)
    
    def _standard_entry_signal(self, dt):
        """Standard entry logic without pullback system"""
        # 1. Previous candle bullish check
        try:
            prev_bull = self.data.close[-1] > self.data.open[-1]
        except IndexError:
            return False

        # 2. EMA crossover check (ANY of the three)
        cross_fast = self._cross_above(self.ema_confirm, self.ema_fast)
        cross_medium = self._cross_above(self.ema_confirm, self.ema_medium) 
        cross_slow = self._cross_above(self.ema_confirm, self.ema_slow)
        cross_any = cross_fast or cross_medium or cross_slow
        
        if cross_any:
            cross_type = []
            if cross_fast: cross_type.append("FAST")
            if cross_medium: cross_type.append("MEDIUM") 
            if cross_slow: cross_type.append("SLOW")
        
        if not (prev_bull and cross_any):
            return False

        # 3. EMA order condition
        if self.p.use_ema_order_condition:
            ema_order_ok = (
                self.ema_confirm[0] > self.ema_fast[0] and
                self.ema_confirm[0] > self.ema_medium[0] and
                self.ema_confirm[0] > self.ema_slow[0]
            )
            if not ema_order_ok:
                return False

        # 4. Price filter EMA
        if self.p.use_price_filter_ema:
            price_above_filter = self.data.close[0] > self.ema_filter_price[0]
            if not price_above_filter:
                return False

        # 5. Angle filter
        if self.p.use_angle_filter:
            current_angle = self._angle()
            angle_ok = current_angle > self.p.min_angle
            if not angle_ok:
                return False

        # All filters passed
        return True
    
    def _handle_pullback_entry(self, dt):
        """Pullback entry state machine logic"""
        current_bar = len(self)
        current_close = float(self.data.close[0])
        current_open = float(self.data.open[0])
        current_high = float(self.data.high[0])
        
        # Check if current candle is red (bearish)
        is_red_candle = current_close < current_open
        
        # STATE MACHINE LOGIC
        if self.pullback_state == "NORMAL":
            # Check for initial entry conditions (1 & 2)
            if self._basic_entry_conditions():
                self.pullback_state = "WAITING_PULLBACK"
                self.pullback_red_count = 0
                self.first_red_high = None
                return False  # Don't enter yet, wait for pullback
            return False
            
        elif self.pullback_state == "WAITING_PULLBACK":
            if is_red_candle:
                self.pullback_red_count += 1
                
                # Store high of first red candle
                if self.pullback_red_count == 1:
                    self.first_red_high = current_high
                
                # Check if we exceeded max red candles
                if self.pullback_red_count > self.p.pullback_max_candles:
                    self._reset_pullback_state()
                    return False
                    
            else:  # Green candle - pullback ended
                if self.pullback_red_count > 0:
                    # Pullback phase complete, start entry window
                    self.pullback_state = "WAITING_BREAKOUT"
                    self.entry_window_start = current_bar
                    self.breakout_target = self.first_red_high + (self.p.entry_pip_offset * self.p.pip_value)
                else:
                    # No pullback occurred, reset
                    self._reset_pullback_state()
            return False
            
        elif self.pullback_state == "WAITING_BREAKOUT":
            # Check if entry window expired
            bars_in_window = current_bar - self.entry_window_start
            if bars_in_window >= self.p.entry_window_periods:
                self._reset_pullback_state()
                return False
            
            # Check for breakout above target
            if current_high >= self.breakout_target:
                # Breakout detected! Check all other entry conditions
                if self._validate_all_entry_filters():
                    if self.p.print_signals:
                        print(f"BREAKOUT ENTRY! High={current_high:.5f} >= target={self.breakout_target:.5f}")
                    self._reset_pullback_state()  # Reset for next setup
                    return True
            return False
        
        return False
    
    def _basic_entry_conditions(self):
        """Check basic entry conditions 1 & 2 for pullback system"""
        # 1. Previous candle bullish check
        try:
            prev_bull = self.data.close[-1] > self.data.open[-1]
        except IndexError:
            return False

        # 2. EMA crossover check (ANY of the three)
        cross_fast = self._cross_above(self.ema_confirm, self.ema_fast)
        cross_medium = self._cross_above(self.ema_confirm, self.ema_medium) 
        cross_slow = self._cross_above(self.ema_confirm, self.ema_slow)
        cross_any = cross_fast or cross_medium or cross_slow
        
        return prev_bull and cross_any
    
    def _validate_all_entry_filters(self):
        """Validate all entry filters (3-6) for pullback entry"""
        # 3. EMA order condition
        if self.p.use_ema_order_condition:
            ema_order_ok = (
                self.ema_confirm[0] > self.ema_fast[0] and
                self.ema_confirm[0] > self.ema_medium[0] and
                self.ema_confirm[0] > self.ema_slow[0]
            )
            if not ema_order_ok:
                return False

        # 4. Price filter EMA
        if self.p.use_price_filter_ema:
            price_above_filter = self.data.close[0] > self.ema_filter_price[0]
            if not price_above_filter:
                return False

        # 5. Angle filter
        if self.p.use_angle_filter:
            current_angle = self._angle()
            angle_ok = current_angle > self.p.min_angle
            if not angle_ok:
                return False

        return True
    
    def _reset_pullback_state(self):
        """Reset pullback state machine to initial state"""
        self.pullback_state = "NORMAL"
        self.pullback_red_count = 0
        self.first_red_high = None
        self.entry_window_start = None
        self.breakout_target = None

    def notify_order(self, order):
        """Enhanced order notification with robust OCA group for SL/TP."""
        dt = bt.num2date(self.data.datetime[0])

        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status == order.Completed:
            if order.isbuy():
                # BUY order completed - this is our entry
                self.last_entry_price = order.executed.price
                self.last_entry_bar = len(self)
                if self.p.print_signals:
                    print(f"BUY EXECUTED at {order.executed.price:.5f} size={order.executed.size}")

                # --- THE DEFINITIVE FIX: USE AN OCA (ONE-CANCELS-ALL) GROUP ---
                if self.stop_level and self.take_level:
                    # Place the stop and limit sell orders as an OCA group
                    # This ensures that if one is executed, the broker automatically cancels the other.
                    # This is the industry-standard way to prevent phantom positions.
                    self.stop_order = self.sell(
                        size=order.executed.size,
                        exectype=bt.Order.Stop,
                        price=self.stop_level,
                        oco=self.limit_order  # Link to the other order
                    )
                    self.limit_order = self.sell(
                        size=order.executed.size,
                        exectype=bt.Order.Limit,
                        price=self.take_level,
                        oco=self.stop_order # Link to the other order
                    )
                    if self.p.print_signals:
                        print(f"PROTECTIVE OCA ORDERS: SL={self.stop_level:.5f} TP={self.take_level:.5f}")
                
                self.order = None

            else:  # SELL order completed - this is an EXIT
                # With OCA, we only expect one of these to ever complete.
                # The other will be automatically Canceled.
                exit_price = order.executed.price
                
                exit_reason = "UNKNOWN"
                if order.exectype == bt.Order.Stop:
                    exit_reason = "STOP_LOSS"
                elif order.exectype == bt.Order.Limit:
                    exit_reason = "TAKE_PROFIT"
                else:
                    exit_reason = "MANUAL_CLOSE"
                
                self.last_exit_reason = exit_reason
                
                if self.p.print_signals:
                    print(f"SELL EXECUTED at {exit_price:.5f} size={order.executed.size} reason={exit_reason}")

                # Reset all state variables to ensure a clean slate for the next trade
                self.stop_order = None
                self.limit_order = None
                self.order = None
                self.stop_level = None
                self.take_level = None
                self.initial_stop_level = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # With OCA, one of the two protective orders will always be canceled
            # when the other one executes. This is normal and expected.
            # We only need to log if it's unexpected.
            is_expected_cancel = (self.stop_order and self.limit_order)
            if not is_expected_cancel and self.p.print_signals:
                print(f"Order {order.getstatusname()}: {order.ref}")
            
            # Clean up references
            if self.order and order.ref == self.order.ref: self.order = None
            if self.stop_order and order.ref == self.stop_order.ref: self.stop_order = None
            if self.limit_order and order.ref == self.limit_order.ref: self.limit_order = None

    def notify_trade(self, trade):
        """Use Backtrader's proper trade notification for accurate PnL tracking"""
        
        if not trade.isclosed:
            return

        dt = bt.num2date(self.data.datetime[0])
        
        # Get accurate PnL from Backtrader
        pnl = trade.pnlcomm
        
        # Calculate entry and exit prices from PnL and trade data
        # PnL = (exit_price - entry_price) * size - commission
        # For long trades: exit_price = entry_price + (pnl / size)
        
        entry_price = self.last_entry_price if self.last_entry_price else 0
        if entry_price > 0 and trade.size != 0:
            # Calculate exit price from PnL: exit = entry + (pnl / size)
            exit_price = entry_price + (pnl / trade.size)
        else:
            # Fallback to trade.price (might be average or exit price)
            exit_price = trade.price
            if exit_price == entry_price:
                # Last resort: estimate from current data
                exit_price = float(self.data.close[0])
        
        # Use stored exit reason from notify_order (more reliable than price comparison)
        exit_reason = getattr(self, 'last_exit_reason', 'UNKNOWN')
        
        # Fallback: If no stored reason, try price comparison
        if exit_reason == 'UNKNOWN':
            if self.stop_level and abs(exit_price - self.stop_level) < 0.0002:
                exit_reason = "STOP_LOSS"
            elif self.take_level and abs(exit_price - self.take_level) < 0.0002:
                exit_reason = "TAKE_PROFIT"
            else:
                exit_reason = "MANUAL_CLOSE"
        
        # Update statistics
        self.trades += 1
        if pnl > 0:
            self.wins += 1
            self.gross_profit += pnl
        else:
            self.losses += 1
            self.gross_loss += abs(pnl)

        # PINE SCRIPT EQUIVALENT: Record exit bar for ta.barssince() logic
        current_bar = len(self)
        self.trade_exit_bars.append(current_bar)
        
        # Mark that exit action occurred on this bar (Pine Script sequential processing)
        self.exit_this_bar = True
        
        # Keep only recent exit bars (last 100 to avoid memory bloat)
        if len(self.trade_exit_bars) > 100:
            self.trade_exit_bars = self.trade_exit_bars[-100:]

        # Mark last exit bar for legacy compatibility
        self.last_exit_bar = current_bar

        if self.p.print_signals:
            pips = (exit_price - entry_price) / self.p.pip_value if self.p.pip_value and entry_price > 0 else 0
            print(f"TRADE CLOSED {dt:%Y-%m-%d %H:%M} reason={exit_reason} PnL={pnl:.2f} Pips={pips:.1f}")
            print(f"  Entry: {entry_price:.5f} -> Exit: {exit_price:.5f} | Size: {trade.size}")

        # Reset levels
        self.stop_level = None
        self.take_level = None
        self.initial_stop_level = None
        
        # Reset pullback state after trade completion
        if self.p.use_pullback_entry:
            self._reset_pullback_state()

    def stop(self):
        # Close debug logging before final summary
        self._close_debug_logging()
        
        # Close any open positions at strategy end and manually process the trade
        if self.position:
            current_price = self.data.close[0]
            entry_price = self.position.price
            position_size = self.position.size
            
            # Calculate unrealized PnL correctly (position.size is already in currency units)
            price_diff = current_price - entry_price
            unrealized_pnl = position_size * price_diff
            
            if self.p.print_signals:
                print(f"STRATEGY END: Closing open position.")
                print(f"  Size: {position_size}, Entry: {entry_price:.5f}, Current: {current_price:.5f}")
                print(f"  Unrealized PnL: {unrealized_pnl:+.2f}")
            
            # Manually update statistics for the open trade before closing
            self.trades += 1
            if unrealized_pnl > 0:
                self.wins += 1
                self.gross_profit += unrealized_pnl
            else:
                self.losses += 1
                self.gross_loss += abs(unrealized_pnl)
            
            # Close the position
            self.order = self.close()
            
            # Cancel any remaining protective orders
            if self.stop_order:
                self.cancel(self.stop_order)
                self.stop_order = None
            if self.limit_order:
                self.cancel(self.limit_order)
                self.limit_order = None
        
        # Enhanced summary calculation with debug stats
        print("=== SUNRISE SIMPLE SUMMARY ===")
        
        # Calculate metrics
        wr = (self.wins / self.trades * 100.0) if self.trades else 0.0
        pf = (self.gross_profit / self.gross_loss) if self.gross_loss > 0 else float('inf')
        
        # Backtrader portfolio value
        final_value = self.broker.get_value()
        starting_cash = 100000.0  # Known starting value
        total_pnl = final_value - starting_cash
        
        print(f"Trades: {self.trades} Wins: {self.wins} Losses: {self.losses} WinRate: {wr:.2f}% PF: {pf:.2f}")
        print(f"Final Value: {final_value:,.2f} | Total PnL: {total_pnl:+,.2f}")
        
        # DEBUG STATISTICS
        print(f"\n=== ENTRY SIGNAL DEBUG STATS ===")
        print(f"Total Entry Signals Evaluated: {self.entry_signal_count}")
        print(f"Blocked Entries: {self.blocked_entry_count}")
        print(f"Successful Entries: {self.successful_entry_count}")
        if self.entry_signal_count > 0:
            block_rate = (self.blocked_entry_count / self.entry_signal_count) * 100
            success_rate = (self.successful_entry_count / self.entry_signal_count) * 100
            print(f"Block Rate: {block_rate:.1f}% | Success Rate: {success_rate:.1f}%")
        
        # Validation
        calculated_pnl = self.gross_profit - self.gross_loss
        pnl_diff = abs(calculated_pnl - total_pnl)
        if pnl_diff > 10.0:  # Allow for small rounding/fee differences
            print(f"INFO: PnL difference: {pnl_diff:.2f} (calculated: {calculated_pnl:+.2f})")

        if self.p.use_pullback_entry:
            self._reset_pullback_state()
    
    def _cancel_all_pending_orders(self):
        """Cancel all pending orders to ensure clean state"""
        try:
            if self.order:
                self.broker.cancel(self.order)
                self.order = None
            if self.stop_order:
                self.broker.cancel(self.stop_order)
                self.stop_order = None
            if self.limit_order:
                self.broker.cancel(self.limit_order)
                self.limit_order = None
            print("DEBUG: All pending orders cancelled")
        except Exception as e:
            print(f"Error cancelling orders: {e}")


if __name__ == '__main__':
    from datetime import datetime, timedelta

    if QUICK_TEST:
        try:
            td_obj = datetime.strptime(TODATE, '%Y-%m-%d')
            FROMDATE = (td_obj - timedelta(days=10)).strftime('%Y-%m-%d')
        except Exception:
            pass

    class SLTPObserver(bt.Observer):
        lines = ('sl','tp',); plotinfo = dict(plot=True, subplot=False)
        plotlines = dict(sl=dict(color='red', ls='--'), tp=dict(color='green', ls='--'))
        def next(self):
            strat = self._owner
            if strat.position:
                self.lines.sl[0] = strat.stop_level if strat.stop_level else float('nan')
                self.lines.tp[0] = strat.take_level if strat.take_level else float('nan')
            else:
                self.lines.sl[0] = float('nan'); self.lines.tp[0] = float('nan')
    BASE = Path(__file__).resolve().parent.parent.parent
    DATA_FILE = BASE / 'data' / DATA_FILENAME
    STRAT_KWARGS = dict(
        plot_result=ENABLE_PLOT,
        use_forex_position_calc=ENABLE_FOREX_CALC,
        forex_instrument=FOREX_INSTRUMENT
    )
    
    if TEST_FOREX_MODE:
        # Quick test with forex calculations - reduce time period
        try:
            td_obj = datetime.strptime(TODATE, '%Y-%m-%d')
            FROMDATE = (td_obj - timedelta(days=30)).strftime('%Y-%m-%d')
            print(f"FOREX TEST MODE: Testing period reduced to {FROMDATE} - {TODATE}")
        except Exception:
            pass

    def parse_date(s):
        if not s: return None
        try: return datetime.strptime(s, '%Y-%m-%d')
        except Exception: return None

    if not DATA_FILE.exists():
        print(f"Data file not found: {DATA_FILE}"); raise SystemExit(1)

    feed_kwargs = dict(dataname=str(DATA_FILE), dtformat='%Y%m%d', tmformat='%H:%M:%S',
                       datetime=0, time=1, open=2, high=3, low=4, close=5, volume=6,
                       timeframe=bt.TimeFrame.Minutes, compression=5)
    fd = parse_date(FROMDATE); td = parse_date(TODATE)
    if fd: feed_kwargs['fromdate'] = fd
    if td: feed_kwargs['todate'] = td
    data = bt.feeds.GenericCSVData(**feed_kwargs)

    cerebro = bt.Cerebro(stdstats=False)
    cerebro.adddata(data)
    cerebro.broker.setcash(STARTING_CASH)
    cerebro.broker.setcommission(leverage=30.0)
    cerebro.addstrategy(SunriseSimple, **STRAT_KWARGS)
    try: cerebro.addobserver(bt.observers.BuySell, barplot=False, plotdist=SunriseSimple.params.buy_sell_plotdist)
    except Exception: pass
    if SunriseSimple.params.plot_sltp_lines:
        try: cerebro.addobserver(SLTPObserver)
        except Exception: pass
    try: cerebro.addobserver(bt.observers.Value)
    except Exception: pass

    if LIMIT_BARS > 0:
        # Monkey-patch next() to stop early after LIMIT_BARS bars for quick experimentation.
        orig_next = SunriseSimple.next
        def limited_next(self):
            if len(self.data) >= LIMIT_BARS:
                self.env.runstop(); return
            orig_next(self)
        SunriseSimple.next = limited_next

    print(f"=== SUNRISE SIMPLE === (from {FROMDATE} to {TODATE})")
    if ENABLE_FOREX_CALC:
        print(f"📊 FOREX MODE ENABLED - Data: {DATA_FILENAME}")
        print(f"🎯 Instrument Detection: {FOREX_INSTRUMENT} (AUTO-DETECT from filename)")
    else:
        print(f"📈 STANDARD MODE - Data: {DATA_FILENAME}")
    
    results = cerebro.run()
    print(f"Final Value: {cerebro.broker.getvalue():,.2f}")
    if results and getattr(results[0].p, 'plot_result', False) and ENABLE_PLOT:
        try: cerebro.plot(style='candlestick')
        except Exception as e: print(f"Plot error: {e}")