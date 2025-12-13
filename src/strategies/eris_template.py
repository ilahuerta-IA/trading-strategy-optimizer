"""ERIS Strategy - Simplified Pullback Breakout System (Long-Only)
================================================================
ERIS (Expert Robotic Investment System) - A lean, simplified strategy
based on lessons learned from Sunrise Ogle, following SOLID principles.

ASSET: USDCHF 5M
STATUS: ⚠️ NO APTO PARA TRADING REAL (Dic 2024)
PRÓXIMO PASO: Considerar fusión con OGLE → "OGLERIS"

ROBUSTNESS ANALYSIS (2020-07-01 to 2025-07-01, $100k)
=====================================================
⚠️ AMBAS CONFIGURACIONES FALLAN CRITERIOS DE ROBUSTEZ:

CONFIGURACIÓN ORIGINAL (Current) - Z-Score [-3.0, -1.0]:
- Trades: 263 | PF: 1.11 | Sharpe: 0.23 | Sortino: 0.04
- CAGR: 2.62% | Max DD: 13.75% | MC95% DD: 23.55%
- Años: 2020(-), 2021(+), 2022(-), 2023(+), 2024(+), 2025(+)
- Net P&L: $13,741 | ❌ 2 años negativos, Sharpe muy bajo

CONFIGURACIÓN CONSERVADORA (Alternativa) - Z-Score [-2.5, -1.5]:
- Trades: 138 | PF: 1.46 | Sharpe: 0.43 | Sortino: 0.05
- CAGR: 5.07% | Max DD: 12.08% | MC95% DD: 12.46%
- Años: 2020(-), 2021(+), 2022(-), 2023(+), 2024(+), 2025(+)
- Net P&L: $27,923 | ❌ 2 años negativos, Sharpe < 1.0

CRITERIOS REQUERIDOS PARA TRADING REAL (Portfolio Dalio 10%):
- Sharpe > 1.0 ❌
- PF > 1.5 ❌  
- 5+/6 años positivos ❌
- MC95% DD < 15% ✅ (solo conservadora)

CONCLUSIÓN: Estrategia NO ROBUSTA para cuenta real.
Mantener para estudio académico y posible fusión con OGLE.

PATTERN DESCRIPTION
-------------------
1. Bullish candle (close > open) - marked as candle "1"
2. Exactly N bearish pullback candles (close < open) - candles "2", "3", etc.
3. Entry on breakout above the HIGH of candle "1"
4. Optional: require N green candles BEFORE the bullish candle "1"

CONFIGURABLE PARAMETERS
-----------------------
- LONG_PULLBACK_NUM_CANDLES: Exact number of bearish candles required (default: 2)
- LONG_BREAKOUT_DELAY: Enable/disable delay after pullback (default: True)
- LONG_BREAKOUT_DELAY_CANDLES: Number of candles to ignore after pullback (default: 1)
- LONG_ENTRY_MAX_CANDLES: Maximum candles to wait for breakout (default: 7)
- LONG_BEFORE_CANDLES: Enable requirement for green candles before pattern (default: False)
- LONG_BEFORE_NUM_CANDLES: Number of green candles required before pattern (default: 1)

EXIT SYSTEM
-----------
ATR-based Stop Loss and Take Profit (OCA orders):
- Stop Loss = entry_price - (ATR x long_atr_sl_multiplier)
- Take Profit = entry_price + (ATR x long_atr_tp_multiplier)

DISCLAIMER
----------
Educational and research purposes ONLY. Not investment advice.
Trading involves substantial risk of loss. Past performance does not
guarantee future results.
"""
from __future__ import annotations
import math
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import calendar
import backtrader as bt
import numpy as np


# =============================================================================
# CONFIGURATION PARAMETERS
# =============================================================================

# === INSTRUMENT SELECTION ===
# Template para USD/CHF - copiar y modificar para otros pares
DATA_FILENAME = 'USDCHF_5m_5Yea.csv'

# === BACKTEST SETTINGS ===
FROMDATE = '2020-07-01'
TODATE = '2025-07-01'
STARTING_CASH = 100000.0
ENABLE_PLOT = True

# === TIMEFRAME RESAMPLING ===
# Resample 5M data to higher timeframes for testing
# Options: 5 (original), 15, 30, 60 (1H), 240 (4H)
# Higher TF = larger ATR = larger SL = less trades
RESAMPLE_MINUTES = 5  # Change this to test different timeframes (5, 15, 30, 60)

# === FOREX CONFIGURATION ===
FOREX_INSTRUMENT = 'USDCHF'
PIP_VALUE = 0.0001  # Standard for CHF pairs (0.01 for JPY pairs)

# === COMMISSION SETTINGS (Darwinex Zero USDCHF) ===
# From broker specs:
# - Spread: 0.7 pips (already in price, not simulated separately)
# - Margin: 3.33% (30:1 leverage)
# - Commission: $2.50 per lot per order (entry + exit)
# Note: Backtrader calls _getcommission on EACH order (entry + exit)
USE_FIXED_COMMISSION = True      # Disable commission for testing
COMMISSION_PER_LOT_PER_ORDER = 2.50  # USD per lot per order
SPREAD_PIPS = 0.7                 # Broker spread for cost calculation
MARGIN_PERCENT = 3.33             # 3.33% margin = 30:1 leverage

# === TRADE REPORTING ===
EXPORT_TRADE_REPORTS = True

# === VISUAL SETTINGS ===
PLOT_SLTP_LINES = True  # Show SL/TP lines on chart (red/green dashed)

# =============================================================================
# ERIS PATTERN PARAMETERS
# =============================================================================

# Exact number of bearish pullback candles required after bullish candle
LONG_PULLBACK_NUM_CANDLES = 1  # OPTIMIZED: Reduced from 2 to 1

# Breakout delay - ignore N candles after pullback before allowing entry
LONG_BREAKOUT_DELAY = False
LONG_BREAKOUT_DELAY_CANDLES = 1

# Maximum candles to wait for breakout after pullback (expiry)
LONG_ENTRY_MAX_CANDLES = 5  # OPTIMIZED: Reduced from 7 to 5

# Require N green candles before the bullish trigger candle
# USDCHF OPTIMIZED: Require 1 green candle before trigger for confirmation
LONG_BEFORE_CANDLES = True  # ENABLED for USDCHF
LONG_BEFORE_NUM_CANDLES = 1

# =============================================================================
# TIME FILTER PARAMETERS
# =============================================================================

# Enable time range filter (best performing hours)
# Analysis: [14:00-22:00) has PF 1.51 with 239 trades
USE_TIME_RANGE_FILTER = False  # OPTIMIZED: Enabled for better quality entries
TRADING_START_HOUR = 14   # Start trading at 14:00 (US session overlap)
TRADING_END_HOUR = 22     # Stop trading at 22:00

# =============================================================================
# ATR FILTER PARAMETERS  
# =============================================================================

# Filter trades by ATR range (avoid extreme volatility)
# USDCHF: típico 0.00025 - 0.00045
USE_ATR_FILTER = False
ATR_MIN_THRESHOLD = 0.00025
ATR_MAX_THRESHOLD = 0.00040

# =============================================================================
# HOURS TO AVOID FILTER PARAMETERS
# =============================================================================

# Enable filter to avoid specific hours with poor performance
# USDCHF Analysis: These hours have PF < 1.0
# Hour 3: PF 0.93 | Hour 6: PF 0.89 | Hour 7: PF 0.88 | Hour 10: PF 0.77
# Hour 13: PF 0.71 | Hour 20: PF 0.38
USE_HOURS_TO_AVOID_FILTER = False  # DISABLED by default - enable after analysis

# Hours to avoid (UTC) - based on analysis showing PF < 1.0
# Hour 3: PF 0.93 | Hour 6: PF 0.89 | Hour 7: PF 0.88 | Hour 10: PF 0.77
# Hour 13: PF 0.71 | Hour 20: PF 0.38
HOURS_TO_AVOID = [3, 6, 7, 10, 13, 20]

# =============================================================================
# RISK MANAGEMENT PARAMETERS
# =============================================================================

# ATR settings for SL/TP calculation (USDCHF OPTIMIZED: R:R = 1:5)
ATR_LENGTH = 10
LONG_ATR_SL_MULTIPLIER = 1.0  # SL = ATR x 1.0
LONG_ATR_TP_MULTIPLIER = 5.0  # TP = ATR x 5.0 -> R:R = 1:5

# =============================================================================
# SL RANGE FILTER - Optimal range found via analysis
# =============================================================================
# Rule: Only take trades where SL is between MIN and MAX pips
# Too tight = high spread cost relative to risk
# Too wide = lower quality setups, may indicate high volatility
USE_MIN_SL_FILTER = False           # Enable SL range filter
MIN_SL_PIPS = 3.0                   # Minimum SL distance in pips (spread 0.7 = 14% cost)
MAX_SL_PIPS = 250.0                  # Maximum SL distance in pips

# Position sizing
RISK_PERCENT = 0.005  # 0.5% risk per trade
MARGIN_PERCENT = 3.33  # 3.33% margin = 30:1 leverage (Darwinex Zero)

# =============================================================================
# MEAN REVERSION INDICATOR PARAMETERS (Ernest P. Chan)
# =============================================================================

# Enable Mean Reversion visualization indicator
USE_MEAN_REVERSION_INDICATOR = True

# EMA period for the mean (center line)
MEAN_REVERSION_EMA_PERIOD = 90

# ATR period for deviation calculation
MEAN_REVERSION_ATR_PERIOD = 10

# Deviation multiplier (how many ATRs from mean to draw bands)
MEAN_REVERSION_DEVIATION_MULT = 2.0

# Z-Score thresholds for overbought/oversold zones
MEAN_REVERSION_ZSCORE_UPPER = 2.0   # Above this = overbought
MEAN_REVERSION_ZSCORE_LOWER = -2.0  # Below this = oversold

# =============================================================================
# MEAN REVERSION ENTRY FILTER PARAMETERS
# =============================================================================

# Enable Mean Reversion as entry filter (only enter when price is in oversold zone)
# USDCHF OPTIMIZED: Z-Score [-3.0, -1.0] filters for oversold entries
USE_MEAN_REVERSION_ENTRY_FILTER = True  # ENABLED for USDCHF

# Z-Score range for valid entries (only enter when Z-Score is within this range)
# Analysis: Z-Score -3.0 to -1.0 captures oversold bounce opportunities
# 
# ALTERNATIVA CONSERVADORA: MR_ENTRY_ZSCORE_MIN = -2.5, MR_ENTRY_ZSCORE_MAX = -1.5
# (138 trades, PF 1.46, Sharpe 0.43, MC95% DD 12.46%)
# Ver docstring superior para análisis completo de robustez
#
MR_ENTRY_ZSCORE_MIN = -3.0   # Minimum Z-Score (deep oversold limit)
MR_ENTRY_ZSCORE_MAX = -1.0   # Maximum Z-Score (must be in oversold zone)

# =============================================================================
# OVERSOLD DURATION FILTER PARAMETERS
# =============================================================================

# Enable filter based on how long price has been in oversold zone
# Filters out quick bounces (too few candles) and strong downtrends (too many)
# USDCHF OPTIMIZED: Duration 6-11 candles is sweet spot
USE_OVERSOLD_DURATION_FILTER = True  # ENABLED for USDCHF

# Minimum candles price must be in oversold zone (Z-Score < threshold) before entry
# Too few = likely noise/quick bounce, not real reversal
# USDCHF Analysis: 6-11 candles gives best quality entries
OVERSOLD_MIN_CANDLES = 6  # Min candles in oversold before entry

# Maximum candles price can be in oversold zone before entry
# Too many = likely strong downtrend, may not revert
OVERSOLD_MAX_CANDLES = 11  # Max candles in oversold

# Z-Score threshold to consider price in oversold zone for duration counting
# Usually same as MR_ENTRY_ZSCORE_MAX or MEAN_REVERSION_ZSCORE_LOWER
OVERSOLD_ZSCORE_THRESHOLD = -1.0


# =============================================================================
# INSTRUMENT CONFIGURATION - Auto-detect JPY pairs vs Standard pairs
# =============================================================================
# Configuration per instrument type:
# - JPY pairs: pip_value=0.01, 3 decimal places, need P&L conversion
# - Standard pairs: pip_value=0.0001, 5 decimal places, direct USD P&L

INSTRUMENT_CONFIGS = {
    'USDJPY': {'pip_value': 0.01, 'pip_decimal_places': 3, 'lot_size': 100000, 'atr_scale': 100.0, 'is_jpy': True},
    'EURJPY': {'pip_value': 0.01, 'pip_decimal_places': 3, 'lot_size': 100000, 'atr_scale': 100.0, 'is_jpy': True},
    'GBPJPY': {'pip_value': 0.01, 'pip_decimal_places': 3, 'lot_size': 100000, 'atr_scale': 100.0, 'is_jpy': True},
    'USDCHF': {'pip_value': 0.0001, 'pip_decimal_places': 5, 'lot_size': 100000, 'atr_scale': 1.0, 'is_jpy': False},
    'EURUSD': {'pip_value': 0.0001, 'pip_decimal_places': 5, 'lot_size': 100000, 'atr_scale': 1.0, 'is_jpy': False},
    'GBPUSD': {'pip_value': 0.0001, 'pip_decimal_places': 5, 'lot_size': 100000, 'atr_scale': 1.0, 'is_jpy': False},
    'XAUUSD': {'pip_value': 0.01, 'pip_decimal_places': 2, 'lot_size': 100, 'atr_scale': 1.0, 'is_jpy': False},
}

# Get config for current instrument (default to USDCHF-like if not found)
_CURRENT_CONFIG = INSTRUMENT_CONFIGS.get(FOREX_INSTRUMENT, {
    'pip_value': PIP_VALUE,
    'pip_decimal_places': 5,
    'lot_size': 100000,
    'atr_scale': 1.0,
    'is_jpy': 'JPY' in FOREX_INSTRUMENT
})


# =============================================================================
# COMMISSION CLASS - Supports both JPY and Standard pairs
# =============================================================================
class ForexCommission(bt.CommInfoBase):
    """
    Commission scheme for Forex pairs with fixed commission per lot.
    Supports both JPY pairs (P&L conversion) and standard pairs.
    
    Darwinex Zero specs (USDCHF):
    - Commission: $2.50 per lot per order
    - Spread: 0.7 pips (in price)
    - Margin: 3.33% (30:1 leverage)
    """
    params = (
        ('stocklike', False),
        ('commtype', bt.CommInfoBase.COMM_FIXED),
        ('percabs', True),
        ('leverage', 500.0),  # High leverage for backtest (margin enforced in sizing)
        ('automargin', True),
        ('commission', 2.50),  # $2.50 per order
        ('is_jpy_pair', False),  # Set True for JPY pairs
        ('jpy_rate', 150.0),  # Approximate USDJPY rate for P&L conversion
    )
    
    # Debug counters (class-level)
    commission_calls = 0
    total_commission = 0.0
    total_lots = 0.0

    def _getcommission(self, size, price, pseudoexec):
        """Return commission based on lot size."""
        if USE_FIXED_COMMISSION:
            lots = abs(size) / 100000.0
            comm = lots * COMMISSION_PER_LOT_PER_ORDER
            
            if not pseudoexec:
                ForexCommission.commission_calls += 1
                ForexCommission.total_commission += comm
                ForexCommission.total_lots += lots
            
            return comm
        return 0.0

    def profitandloss(self, size, price, newprice):
        """Calculate P&L - convert from quote currency to USD if needed.
        
        For USDXXX pairs (USD is base):
        - P&L is in quote currency (CHF, JPY, CAD, etc.)
        - Must divide by exit price to get USD
        
        For XXXUSD pairs (USD is quote):
        - P&L is directly in USD
        """
        pnl_quote = size * (newprice - price)
        
        if self.p.is_jpy_pair:
            # JPY pairs: size was normalized, compensate
            pnl_quote = pnl_quote * self.p.jpy_rate
        
        # Convert quote currency P&L to USD by dividing by price
        # This works for USDCHF, USDJPY, USDCAD, etc.
        if newprice > 0:
            return pnl_quote / newprice
        return pnl_quote

    def cashadjust(self, size, price, newprice):
        """Adjust cash for non-stocklike instruments."""
        if not self._stocklike:
            return self.profitandloss(size, price, newprice)
        return 0.0


# =============================================================================
# CUSTOM INDICATORS FOR MEAN REVERSION
# =============================================================================

class MeanReversionBands(bt.Indicator):
    """
    Mean Reversion Bands Indicator (Ernest P. Chan)
    
    Plots:
    - Central EMA (mean)
    - Upper band: EMA + (multiplier x ATR)
    - Lower band: EMA - (multiplier x ATR)
    """
    lines = ('mean', 'upper', 'lower',)
    
    params = (
        ('ema_period', 70),
        ('atr_period', 14),
        ('deviation_mult', 2.0),
    )
    
    plotinfo = dict(
        plot=True,
        subplot=False,  # Plot on main price chart
    )
    
    plotlines = dict(
        mean=dict(color='blue', linewidth=1.0),
        upper=dict(color='red', linestyle='--', linewidth=0.8),
        lower=dict(color='green', linestyle='--', linewidth=0.8),
    )
    
    def __init__(self):
        self.ema = bt.ind.EMA(self.data.close, period=self.p.ema_period)
        self.atr = bt.ind.ATR(self.data, period=self.p.atr_period)
        
        self.lines.mean = self.ema
        self.lines.upper = self.ema + (self.atr * self.p.deviation_mult)
        self.lines.lower = self.ema - (self.atr * self.p.deviation_mult)


class ZScoreIndicator(bt.Indicator):
    """
    Z-Score Oscillator: (Price - EMA) / ATR
    
    Shows how many ATRs the price has deviated from the mean.
    """
    lines = ('zscore',)
    
    params = (
        ('ema_period', 70),
        ('atr_period', 14),
        ('upper_threshold', 2.0),
        ('lower_threshold', -2.0),
    )
    
    plotinfo = dict(
        plot=True,
        subplot=True,  # Separate subplot
        plotname='Z-Score',
    )
    
    plotlines = dict(
        zscore=dict(color='purple', linewidth=1.0),
    )
    
    def __init__(self):
        self.ema = bt.ind.EMA(self.data.close, period=self.p.ema_period)
        self.atr = bt.ind.ATR(self.data, period=self.p.atr_period)
        
        self.lines.zscore = (self.data.close - self.ema) / self.atr
        
        # Add horizontal lines for thresholds
        self.plotinfo.plotyhlines = [
            self.p.upper_threshold,
            0,
            self.p.lower_threshold
        ]


class Eris(bt.Strategy):
    """
    ERIS Strategy - Simplified Pullback Breakout System
    
    State Machine:
    - SCANNING: Looking for bullish candle (candle 1)
    - PULLBACK: Counting bearish candles
    - WAITING: Delay period after pullback (if enabled)
    - BREAKOUT: Monitoring for price to break above candle 1 high
    """
    
    params = dict(
        # Pattern parameters
        long_pullback_num_candles=LONG_PULLBACK_NUM_CANDLES,
        long_breakout_delay=LONG_BREAKOUT_DELAY,
        long_breakout_delay_candles=LONG_BREAKOUT_DELAY_CANDLES,
        long_entry_max_candles=LONG_ENTRY_MAX_CANDLES,
        long_before_candles=LONG_BEFORE_CANDLES,
        long_before_num_candles=LONG_BEFORE_NUM_CANDLES,
        
        # Time filter
        use_time_filter=USE_TIME_RANGE_FILTER,
        trading_start_hour=TRADING_START_HOUR,
        trading_end_hour=TRADING_END_HOUR,
        
        # ATR filter
        use_atr_filter=USE_ATR_FILTER,
        atr_min_threshold=ATR_MIN_THRESHOLD,
        atr_max_threshold=ATR_MAX_THRESHOLD,
        
        # Hours to avoid filter
        use_hours_to_avoid_filter=USE_HOURS_TO_AVOID_FILTER,
        hours_to_avoid=HOURS_TO_AVOID,
        
        # ATR settings
        atr_length=ATR_LENGTH,
        long_atr_sl_multiplier=LONG_ATR_SL_MULTIPLIER,
        long_atr_tp_multiplier=LONG_ATR_TP_MULTIPLIER,
        
        # SL Range filter
        use_min_sl_filter=USE_MIN_SL_FILTER,
        min_sl_pips=MIN_SL_PIPS,
        max_sl_pips=MAX_SL_PIPS,
        spread_pips=SPREAD_PIPS,
        
        # Position sizing
        risk_percent=RISK_PERCENT,
        margin_pct=MARGIN_PERCENT,
        contract_size=100000,
        
        # Forex settings (auto-configured from instrument)
        forex_instrument=FOREX_INSTRUMENT,
        forex_pip_value=_CURRENT_CONFIG['pip_value'],
        forex_pip_decimal_places=_CURRENT_CONFIG['pip_decimal_places'],
        forex_lot_size=_CURRENT_CONFIG['lot_size'],
        forex_atr_scale=_CURRENT_CONFIG['atr_scale'],
        
        # Display settings
        print_signals=True,
        
        # Mean Reversion Indicator parameters
        use_mean_reversion_indicator=USE_MEAN_REVERSION_INDICATOR,
        mean_reversion_ema_period=MEAN_REVERSION_EMA_PERIOD,
        mean_reversion_atr_period=MEAN_REVERSION_ATR_PERIOD,
        mean_reversion_deviation_mult=MEAN_REVERSION_DEVIATION_MULT,
        mean_reversion_zscore_upper=MEAN_REVERSION_ZSCORE_UPPER,
        mean_reversion_zscore_lower=MEAN_REVERSION_ZSCORE_LOWER,
        
        # Mean Reversion Entry Filter parameters
        use_mean_reversion_entry_filter=USE_MEAN_REVERSION_ENTRY_FILTER,
        mr_entry_zscore_min=MR_ENTRY_ZSCORE_MIN,
        mr_entry_zscore_max=MR_ENTRY_ZSCORE_MAX,
        
        # Oversold Duration Filter parameters
        use_oversold_duration_filter=USE_OVERSOLD_DURATION_FILTER,
        oversold_min_candles=OVERSOLD_MIN_CANDLES,
        oversold_max_candles=OVERSOLD_MAX_CANDLES,
        oversold_zscore_threshold=OVERSOLD_ZSCORE_THRESHOLD,
        
        # Visual settings
        plot_sltp_lines=PLOT_SLTP_LINES,
        buy_sell_plotdist=0.0001,  # Distance for buy/sell markers
    )

    def __init__(self):
        """Initialize strategy indicators and state variables."""
        # ATR indicator for SL/TP calculation
        self.atr = bt.ind.ATR(self.data, period=self.p.atr_length)
        
        # =================================================================
        # MEAN REVERSION INDICATOR (Ernest P. Chan)
        # =================================================================
        if self.p.use_mean_reversion_indicator:
            # Mean Reversion Bands (EMA + Upper/Lower bands)
            self.mr_bands = MeanReversionBands(
                self.data,
                ema_period=self.p.mean_reversion_ema_period,
                atr_period=self.p.mean_reversion_atr_period,
                deviation_mult=self.p.mean_reversion_deviation_mult,
            )
            
            # Z-Score Oscillator (separate subplot)
            self.mr_zscore = ZScoreIndicator(
                self.data,
                ema_period=self.p.mean_reversion_ema_period,
                atr_period=self.p.mean_reversion_atr_period,
                upper_threshold=self.p.mean_reversion_zscore_upper,
                lower_threshold=self.p.mean_reversion_zscore_lower,
            )
        
        # Order management
        self.order = None
        self.stop_order = None
        self.limit_order = None
        self.exit_this_bar = False  # Flag to prevent entry on same bar as exit
        
        # Price levels
        self.stop_level = None
        self.take_level = None
        self.last_exit_price = None  # Store actual exit price for pips calculation
        
        # State machine variables
        self.state = "SCANNING"
        self.trigger_candle_high = None  # High of candle 1
        self.trigger_candle_bar = None   # Bar number of candle 1
        
        # Oversold duration tracking
        self.candles_in_oversold = 0  # Counter for consecutive candles in oversold zone
        self.pullback_count = 0          # Count of bearish candles
        self.pullback_complete_bar = None  # Bar when pullback completed
        self.delay_count = 0             # Count of delay candles
        self.breakout_start_bar = None   # Bar when breakout monitoring started
        
        # Trade tracking
        self.last_entry_bar = None
        self.last_entry_price = None
        self.last_exit_reason = "UNKNOWN"
        self.trades = 0
        self.wins = 0
        self.losses = 0
        self.gross_profit = 0.0
        self.gross_loss = 0.0
        
        # Trade reporting
        self.trade_reports = []
        self.trade_report_file = None
        self._init_trade_reporting()
        
        # Portfolio tracking for advanced metrics (Drawdown, Sharpe)
        self._portfolio_values = []
        self._trade_pnls = []  # Store PnL and dates for yearly stats
        
        # Store data filename
        self._data_filename = getattr(self.data._dataname, 'name',
                                      getattr(self.data, '_dataname', ''))
        if isinstance(self._data_filename, str):
            self._data_filename = Path(self._data_filename).name

    def _init_trade_reporting(self):
        """Initialize trade reporting file."""
        if not EXPORT_TRADE_REPORTS:
            return
            
        try:
            report_dir = Path(__file__).parent / "temp_reports"
            report_dir.mkdir(exist_ok=True)
            
            asset_name = FOREX_INSTRUMENT
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"ERIS_{asset_name}_{timestamp}.txt"
            report_path = report_dir / report_filename
            
            self.trade_report_file = open(report_path, 'w', encoding='utf-8')
            
            # Write header
            self.trade_report_file.write("=== ERIS STRATEGY TRADE REPORT ===\n")
            self.trade_report_file.write(f"Asset: {asset_name}\n")
            self.trade_report_file.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Configuration
            self.trade_report_file.write("CONFIGURATION:\n")
            self.trade_report_file.write("-" * 40 + "\n")
            self.trade_report_file.write(f"Pullback Candles: {self.p.long_pullback_num_candles}\n")
            self.trade_report_file.write(f"Breakout Delay: {self.p.long_breakout_delay} ({self.p.long_breakout_delay_candles} candles)\n")
            self.trade_report_file.write(f"Max Entry Candles: {self.p.long_entry_max_candles}\n")
            self.trade_report_file.write(f"Before Candles Filter: {self.p.long_before_candles} ({self.p.long_before_num_candles})\n")
            self.trade_report_file.write(f"Time Filter: {self.p.use_time_filter} ({self.p.trading_start_hour}:00-{self.p.trading_end_hour}:00)\n")
            self.trade_report_file.write(f"ATR Filter: {self.p.use_atr_filter} (min={self.p.atr_min_threshold}, max={self.p.atr_max_threshold})\n")
            self.trade_report_file.write(f"Hours to Avoid Filter: {self.p.use_hours_to_avoid_filter} (Hours: {list(self.p.hours_to_avoid)})\n")
            self.trade_report_file.write(f"ATR Length: {self.p.atr_length}\n")
            self.trade_report_file.write(f"SL Multiplier: {self.p.long_atr_sl_multiplier}\n")
            self.trade_report_file.write(f"TP Multiplier: {self.p.long_atr_tp_multiplier}\n")
            self.trade_report_file.write(f"Risk Percent: {self.p.risk_percent * 100:.1f}%\n")
            self.trade_report_file.write(f"Mean Reversion Entry Filter: {self.p.use_mean_reversion_entry_filter} (Z-Score: [{self.p.mr_entry_zscore_min}, {self.p.mr_entry_zscore_max}])\n")
            self.trade_report_file.write(f"Oversold Duration Filter: {self.p.use_oversold_duration_filter} (Candles: [{self.p.oversold_min_candles}, {self.p.oversold_max_candles}], Threshold: {self.p.oversold_zscore_threshold})\n")
            self.trade_report_file.write("\n" + "=" * 60 + "\n")
            self.trade_report_file.write("TRADE DETAILS\n")
            self.trade_report_file.write("=" * 60 + "\n\n")
            self.trade_report_file.flush()
            
            print(f"Trade report: {report_path}")
            
        except Exception as e:
            print(f"Trade reporting init error: {e}")
            self.trade_report_file = None

    def _is_bullish_candle(self, offset=0):
        """Check if candle at offset is bullish (close > open)."""
        try:
            return self.data.close[offset] > self.data.open[offset]
        except IndexError:
            return False

    def _is_bearish_candle(self, offset=0):
        """Check if candle at offset is bearish (close < open)."""
        try:
            return self.data.close[offset] < self.data.open[offset]
        except IndexError:
            return False

    def _check_before_candles(self):
        """Check if required number of green candles exist before trigger."""
        if not self.p.long_before_candles:
            return True
            
        required = self.p.long_before_num_candles
        for i in range(1, required + 1):
            offset = -i - 1  # Go back from the candle before current
            if not self._is_bullish_candle(offset):
                return False
        return True

    def _reset_state(self):
        """Reset state machine to scanning mode."""
        self.state = "SCANNING"
        self.trigger_candle_high = None
        self.trigger_candle_bar = None
        self.pullback_count = 0
        self.pullback_complete_bar = None
        self.delay_count = 0
        self.breakout_start_bar = None

    def prenext(self):
        """Called before minimum period - track portfolio value."""
        self._portfolio_values.append(self.broker.get_value())

    def next(self):
        """Main strategy logic - executed on each bar close."""
        # Track portfolio value for Sharpe/Drawdown calculation
        self._portfolio_values.append(self.broker.get_value())
        
        current_bar = len(self)
        dt = self.data.datetime.datetime(0)
        
        # Cancel phantom orders when no position
        if not self.position:
            if self.order:
                self.cancel(self.order)
                self.order = None
            if self.stop_order:
                self.cancel(self.stop_order)
                self.stop_order = None
            if self.limit_order:
                self.cancel(self.limit_order)
                self.limit_order = None
        
        # Skip if waiting for order execution
        if self.order:
            return
        
        # Skip entry logic if in position OR if we have pending SL/TP orders
        if self.position or self.stop_order or self.limit_order:
            return
        
        # =================================================================
        # FILTER CHECKS (OPTIMIZED)
        # =================================================================
        
        # Update oversold duration counter (must be called every bar)
        self._update_oversold_duration()
        
        # TIME FILTER: Only trade during specified hours
        if self.p.use_time_filter:
            current_hour = dt.hour
            if current_hour < self.p.trading_start_hour or current_hour >= self.p.trading_end_hour:
                # Reset state if outside trading hours
                if self.state != "SCANNING":
                    self._reset_state()
                return
        
        # ATR FILTER: Check volatility is within range
        if self.p.use_atr_filter:
            current_atr = float(self.atr[0])
            if math.isnan(current_atr):
                return
            if current_atr < self.p.atr_min_threshold or current_atr > self.p.atr_max_threshold:
                # Reset state if ATR out of range
                if self.state != "SCANNING":
                    self._reset_state()
                return
        
        # HOURS TO AVOID FILTER: Skip specific hours with poor performance
        if self.p.use_hours_to_avoid_filter:
            current_hour = dt.hour
            if current_hour in self.p.hours_to_avoid:
                # Reset state if in bad hour
                if self.state != "SCANNING":
                    self._reset_state()
                return
        
        # =================================================================
        # STATE MACHINE
        # =================================================================
        
        if self.state == "SCANNING":
            # Look for bullish candle (candle 1)
            # Check previous candle (index -1) as potential trigger
            if self._is_bullish_candle(-1):
                # Check before candles requirement if enabled
                if self._check_before_candles():
                    # Found potential trigger candle
                    self.trigger_candle_high = float(self.data.high[-1])
                    self.trigger_candle_bar = current_bar - 1
                    self.pullback_count = 0
                    self.state = "PULLBACK"
                    
                    if self.p.print_signals:
                        print(f"ERIS SIGNAL: Bullish candle detected at {dt}")
                        print(f"   Trigger High: {self.trigger_candle_high:.5f}")
        
        elif self.state == "PULLBACK":
            # Count bearish pullback candles (check CURRENT candle)
            # NOTE: Removed restriction that pullback highs must be below trigger level
            # to allow more flexible entries (especially with Mean Reversion filter)
            
            if self._is_bearish_candle(0):
                self.pullback_count += 1
                
                if self.p.print_signals:
                    print(f"ERIS PULLBACK: Bearish candle {self.pullback_count}/{self.p.long_pullback_num_candles}")
                
                # Check if pullback complete
                if self.pullback_count >= self.p.long_pullback_num_candles:
                    self.pullback_complete_bar = current_bar
                    
                    if self.p.long_breakout_delay:
                        self.state = "WAITING"
                        self.delay_count = 0
                        if self.p.print_signals:
                            print(f"ERIS: Pullback complete, entering delay period")
                        return  # Wait for next bar
                    else:
                        self.state = "BREAKOUT"
                        self.breakout_start_bar = current_bar
                        if self.p.print_signals:
                            print(f"ERIS: Pullback complete, monitoring for breakout")
                        return  # Wait for next bar to check breakout
            else:
                # Current candle is NOT bearish
                # Check if we already have enough pullback candles - if so, transition to BREAKOUT
                if self.pullback_count >= self.p.long_pullback_num_candles:
                    # Pullback was complete, now this non-bearish candle can be checked for breakout
                    if self.pullback_complete_bar is None:
                        self.pullback_complete_bar = current_bar - 1
                    self.state = "BREAKOUT"
                    self.breakout_start_bar = current_bar
                    # Fall through to BREAKOUT check below
                else:
                    # Not enough pullback candles and got a non-bearish candle - invalidate
                    if self.p.print_signals:
                        print(f"ERIS INVALIDATED: Non-bearish candle during pullback (count={self.pullback_count})")
                    self._reset_state()
                    return
        
        elif self.state == "WAITING":
            # Count delay candles
            self.delay_count += 1
            
            if self.delay_count >= self.p.long_breakout_delay_candles:
                self.state = "BREAKOUT"
                self.breakout_start_bar = current_bar
                if self.p.print_signals:
                    print(f"ERIS: Delay complete, monitoring for breakout")
                return  # IMPORTANT: Wait for next bar before checking breakout
        
        # Check BREAKOUT state (can be reached from PULLBACK transition in same bar)
        if self.state == "BREAKOUT":
            # Check for expiry
            candles_since_pullback = current_bar - self.pullback_complete_bar
            if candles_since_pullback > self.p.long_entry_max_candles:
                if self.p.print_signals:
                    print(f"ERIS EXPIRED: No breakout within {self.p.long_entry_max_candles} candles")
                self._reset_state()
                return
            
            # Check for breakout above trigger candle high
            current_high = float(self.data.high[0])
            
            if self.p.print_signals:
                print(f"ERIS BREAKOUT CHECK: Current High={current_high:.5f} vs Trigger={self.trigger_candle_high:.5f}")
            
            if current_high > self.trigger_candle_high:  # Changed >= to > (must BREAK above, not just touch)
                # BREAKOUT DETECTED - CHECK ALL ENTRY FILTERS
                mr_filter_ok = self._check_mean_reversion_entry_filter()
                duration_filter_ok = self._check_oversold_duration_filter()
                
                if mr_filter_ok and duration_filter_ok:
                    self._execute_entry(dt, current_bar)
                else:
                    if self.p.print_signals:
                        print(f"ERIS FILTERED: Entry rejected by filters")
                    self._reset_state()
        
    def _update_oversold_duration(self):
        """Update the counter for consecutive candles in oversold zone.
        
        Called on each bar to track how long price has been in oversold territory.
        Resets to 0 when price exits oversold zone.
        """
        if not self.p.use_oversold_duration_filter:
            return
        
        if not self.p.use_mean_reversion_indicator:
            return
        
        try:
            current_zscore = float(self.mr_zscore.zscore[0])
            if math.isnan(current_zscore):
                return
        except (AttributeError, IndexError):
            return
        
        # Check if currently in oversold zone
        if current_zscore < self.p.oversold_zscore_threshold:
            self.candles_in_oversold += 1
        else:
            # Exited oversold zone, reset counter
            self.candles_in_oversold = 0
    
    def _check_oversold_duration_filter(self):
        """Check if oversold duration is within valid range for entry.
        
        Returns True if:
        - Filter is disabled
        - Duration is between min and max candles
        
        Rationale:
        - Too few candles (< min): Quick bounce, likely noise
        - Too many candles (> max): Strong downtrend, may not revert
        """
        if not self.p.use_oversold_duration_filter:
            return True  # Filter disabled
        
        duration = self.candles_in_oversold
        is_valid = self.p.oversold_min_candles <= duration <= self.p.oversold_max_candles
        
        if self.p.print_signals:
            status = "VALID" if is_valid else "REJECTED"
            print(f"ERIS OVERSOLD DURATION: {duration} candles Range=[{self.p.oversold_min_candles}, {self.p.oversold_max_candles}] -> {status}")
        
        return is_valid
    
    def _check_mean_reversion_entry_filter(self):
        """Check if current price is in valid Mean Reversion zone for entry.
        
        Returns True if:
        - Filter is disabled (use_mean_reversion_entry_filter = False)
        - Filter is enabled AND Z-Score is within the valid range
        """
        if not self.p.use_mean_reversion_entry_filter:
            return True  # Filter disabled, allow all entries
        
        # Check if Mean Reversion indicator is available
        if not self.p.use_mean_reversion_indicator:
            if self.p.print_signals:
                print(f"WARNING: Mean Reversion entry filter enabled but indicator disabled")
            return True  # Can't filter without indicator
        
        # Get current Z-Score
        try:
            current_zscore = float(self.mr_zscore.zscore[0])
            if math.isnan(current_zscore):
                return True  # Allow entry if Z-Score not available yet
        except (AttributeError, IndexError):
            return True  # Allow entry if indicator not ready
        
        # Check if Z-Score is within valid range for entry
        is_valid = self.p.mr_entry_zscore_min <= current_zscore <= self.p.mr_entry_zscore_max
        
        if self.p.print_signals:
            status = "VALID" if is_valid else "REJECTED"
            print(f"ERIS MR FILTER: Z-Score={current_zscore:.2f} Range=[{self.p.mr_entry_zscore_min}, {self.p.mr_entry_zscore_max}] -> {status}")
        
        return is_valid
        
    def _execute_entry(self, dt, current_bar):
        """Execute long entry order with proper position sizing and SL range filter."""
        # Get ATR for SL/TP calculation
        atr_value = float(self.atr[0])
        if math.isnan(atr_value) or atr_value <= 0:
            if self.p.print_signals:
                print(f"ERIS BLOCKED: Invalid ATR value")
            self._reset_state()
            return
        
        entry_price = float(self.data.close[0])
        
        # Calculate SL/TP from entry price
        self.stop_level = entry_price - (atr_value * self.p.long_atr_sl_multiplier)
        self.take_level = entry_price + (atr_value * self.p.long_atr_tp_multiplier)
        
        # Position sizing
        risk_distance = entry_price - self.stop_level
        if risk_distance <= 0:
            self._reset_state()
            return
        
        # Risk calculation
        equity = self.broker.get_value()
        risk_amount = equity * self.p.risk_percent  # e.g., $1000 for 1% of $100k
        
        # Calculate pip risk (distance in pips)
        pip_risk = risk_distance / self.p.forex_pip_value  # Convert to pips
        
        # =================================================================
        # SL RANGE FILTER - Only take trades with SL in optimal range
        # =================================================================
        if self.p.use_min_sl_filter:
            # Check minimum SL (too tight = high spread cost)
            if pip_risk < self.p.min_sl_pips:
                spread_ratio = (self.p.spread_pips / pip_risk) * 100 if pip_risk > 0 else 100
                if self.p.print_signals:
                    print(f"   SKIPPED: SL too tight ({pip_risk:.1f} pips < {self.p.min_sl_pips:.1f} min) | Spread would be {spread_ratio:.0f}% of risk")
                self._reset_state()
                return
            
            # Check maximum SL (too wide = lower quality setups)
            if pip_risk > self.p.max_sl_pips:
                if self.p.print_signals:
                    print(f"   SKIPPED: SL too wide ({pip_risk:.1f} pips > {self.p.max_sl_pips:.1f} max) | Outside optimal range")
                self._reset_state()
                return
        
        # =================================================================
        # PIP VALUE CALCULATION (CORRECTED FOR QUOTE CURRENCY)
        # =================================================================
        # For 1 standard lot (100,000 units):
        #
        # JPY pairs (USDJPY, EURJPY, etc.):
        #   - 1 pip = 0.01 price change
        #   - P&L is in JPY, must convert to USD
        #   - pip_value = 100,000 * 0.01 = 1,000 JPY per pip
        #   - In USD: 1,000 / USDJPY_rate = ~$6.67 per pip per lot
        #
        # USDXXX pairs (USDCHF, USDCAD, etc.):
        #   - 1 pip = 0.0001 price change
        #   - P&L is in QUOTE currency (CHF, CAD), must convert to USD
        #   - pip_value = 100,000 * 0.0001 = 10 CHF per pip
        #   - In USD: 10 / USDCHF_rate = ~$10.30 per pip per lot
        #
        # XXXUSD pairs (EURUSD, GBPUSD, etc.):
        #   - 1 pip = 0.0001 price change
        #   - P&L is directly in USD
        #   - pip_value = 100,000 * 0.0001 = $10 per pip per lot
        # =================================================================
        
        if 'JPY' in self.p.forex_instrument:
            # JPY pairs: pip value in JPY, convert to USD
            pip_value_in_jpy = self.p.forex_lot_size * self.p.forex_pip_value  # 1000 JPY
            value_per_pip_per_lot = pip_value_in_jpy / entry_price  # Convert to USD
        elif self.p.forex_instrument.startswith('USD'):
            # USDXXX pairs: pip value in quote currency, convert to USD
            pip_value_in_quote = self.p.forex_lot_size * self.p.forex_pip_value  # 10 CHF
            value_per_pip_per_lot = pip_value_in_quote / entry_price  # Convert to USD
        else:
            # XXXUSD pairs: pip value directly in USD
            value_per_pip_per_lot = self.p.forex_lot_size * self.p.forex_pip_value  # $10
        
        # Calculate optimal lot size: lots = risk_amount / (pips * pip_value_per_lot)
        if pip_risk > 0 and value_per_pip_per_lot > 0:
            optimal_lots = risk_amount / (pip_risk * value_per_pip_per_lot)
        else:
            self._reset_state()
            return
        
        # =====================================================================
        # MARGIN CHECK - Limit lots based on available margin
        # =====================================================================
        # For Forex: 1 lot = $100,000 notional value
        # Margin required per lot = $100,000 * margin_pct%
        # Darwinex Zero: 3.33% margin = 30:1 leverage
        # Note: With small SL and high risk%, margin may limit position size
        margin_per_lot = self.p.forex_lot_size * (self.p.margin_pct / 100.0)
        available_margin = equity  # Use 100% of equity for margin calculation
        max_lots_by_margin = available_margin / margin_per_lot
        
        margin_limited = False
        if optimal_lots > max_lots_by_margin:
            margin_limited = True
            if self.p.print_signals:
                actual_risk_pct = (max_lots_by_margin * pip_risk * value_per_pip_per_lot / equity) * 100
                print(f"   MARGIN LIMIT: {optimal_lots:.2f} -> {max_lots_by_margin:.2f} lots (actual risk: {actual_risk_pct:.2f}%)")
            optimal_lots = max_lots_by_margin
        
        # Round to standard lot sizes (min 0.01)
        optimal_lots = max(0.01, round(optimal_lots, 2))
        
        # Convert to Backtrader size
        bt_size = int(optimal_lots * self.p.forex_lot_size)
        
        # Minimum size check
        if bt_size < 1000:
            bt_size = 1000  # Minimum micro lot
        
        # Calculate ACTUAL risk (after lot size limits applied)
        actual_risk = optimal_lots * pip_risk * value_per_pip_per_lot
        
        if self.p.print_signals:
            print(f"   Position: {optimal_lots:.2f} lots ({bt_size:,} units) | Target Risk: ${risk_amount:.0f} | Actual Risk: ${actual_risk:.0f} | Pips to SL: {pip_risk:.1f}")
        
        # Place buy order
        self.order = self.buy(size=bt_size)
        
        # Calculate R:R
        rr = (self.take_level - entry_price) / risk_distance if risk_distance > 0 else 0
        
        if self.p.print_signals:
            print(f"ERIS ENTRY: LONG BUY at {dt}")
            print(f"   Price: {entry_price:.5f} | SL: {self.stop_level:.5f} | TP: {self.take_level:.5f}")
            print(f"   ATR: {atr_value:.6f} | R:R = 1:{rr:.2f}")
        
        # Record entry
        self._record_entry(dt, entry_price, bt_size, atr_value)
        
        self.last_entry_price = entry_price
        self.last_entry_bar = current_bar
        
        # DO NOT reset state here - will be reset in notify_order when order completes

    def _record_entry(self, dt, entry_price, size, atr_value):
        """Record trade entry for reporting with all indicator values."""
        if not self.trade_report_file:
            return
        
        # Gather all indicator values for analysis
        zscore_value = None
        ema_value = None
        upper_band = None
        lower_band = None
        
        if self.p.use_mean_reversion_indicator:
            try:
                zscore_value = float(self.mr_zscore.zscore[0])
                ema_value = float(self.mr_bands.mean[0])
                upper_band = float(self.mr_bands.upper[0])
                lower_band = float(self.mr_bands.lower[0])
            except (AttributeError, IndexError):
                pass
        
        # Calculate distance from bands (for analysis)
        dist_to_ema = entry_price - ema_value if ema_value else None
        dist_to_lower = entry_price - lower_band if lower_band else None
        dist_to_upper = upper_band - entry_price if upper_band else None
            
        try:
            self.trade_reports.append({
                'entry_time': dt,
                'entry_price': entry_price,
                'size': size,
                'atr': atr_value,
                'stop_level': self.stop_level,
                'take_level': self.take_level,
                'zscore': zscore_value,
                'candles_in_oversold': self.candles_in_oversold,
                'ema': ema_value,
                'upper_band': upper_band,
                'lower_band': lower_band
            })
            
            self.trade_report_file.write(f"ENTRY #{len(self.trade_reports)}\n")
            self.trade_report_file.write(f"Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.trade_report_file.write(f"Direction: LONG\n")
            self.trade_report_file.write(f"Entry Price: {entry_price:.5f}\n")
            self.trade_report_file.write(f"Stop Loss: {self.stop_level:.5f}\n")
            self.trade_report_file.write(f"Take Profit: {self.take_level:.5f}\n")
            self.trade_report_file.write(f"ATR: {atr_value:.6f}\n")
            
            # Mean Reversion indicator values
            if zscore_value is not None:
                self.trade_report_file.write(f"Z-Score: {zscore_value:.3f}\n")
            if self.p.use_oversold_duration_filter:
                self.trade_report_file.write(f"Candles in Oversold: {self.candles_in_oversold}\n")
            if ema_value is not None:
                self.trade_report_file.write(f"EMA({self.p.mean_reversion_ema_period}): {ema_value:.5f}\n")
            if upper_band is not None:
                self.trade_report_file.write(f"Upper Band: {upper_band:.5f}\n")
            if lower_band is not None:
                self.trade_report_file.write(f"Lower Band: {lower_band:.5f}\n")
            if dist_to_ema is not None:
                self.trade_report_file.write(f"Distance to EMA: {dist_to_ema:.5f}\n")
            if dist_to_lower is not None:
                self.trade_report_file.write(f"Distance to Lower: {dist_to_lower:.5f}\n")
            
            self.trade_report_file.write("-" * 40 + "\n\n")
            self.trade_report_file.flush()
            
        except Exception as e:
            print(f"Entry recording error: {e}")

    def _record_exit(self, dt, exit_price, pnl, exit_reason):
        """Record trade exit for reporting."""
        if not self.trade_report_file or not self.trade_reports:
            return
            
        try:
            last_trade = self.trade_reports[-1]
            entry_price = last_trade.get('entry_price', 0)
            pips = (exit_price - entry_price) / self.p.forex_pip_value if entry_price > 0 else 0
            result = "WIN" if pnl > 0 else "LOSS"
            
            # Add result to trade record for analysis
            last_trade['exit_price'] = exit_price
            last_trade['pnl'] = pnl
            last_trade['result'] = result
            last_trade['exit_reason'] = exit_reason
            
            self.trade_report_file.write(f"EXIT #{len(self.trade_reports)}\n")
            self.trade_report_file.write(f"Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.trade_report_file.write(f"Exit Price: {exit_price:.5f}\n")
            self.trade_report_file.write(f"Exit Reason: {exit_reason}\n")
            self.trade_report_file.write(f"Result: {result}\n")
            self.trade_report_file.write(f"P&L: {pnl:.2f}\n")
            self.trade_report_file.write(f"Pips: {pips:.1f}\n")
            
            # Include entry indicator values for correlation analysis
            if 'zscore' in last_trade and last_trade['zscore'] is not None:
                self.trade_report_file.write(f"Entry Z-Score: {last_trade['zscore']:.3f}\n")
            if 'candles_in_oversold' in last_trade:
                self.trade_report_file.write(f"Entry Candles in Oversold: {last_trade['candles_in_oversold']}\n")
            if 'atr' in last_trade:
                self.trade_report_file.write(f"Entry ATR: {last_trade['atr']:.6f}\n")
            
            self.trade_report_file.write("=" * 60 + "\n\n")
            self.trade_report_file.flush()
            
        except Exception as e:
            print(f"Exit recording error: {e}")

    def notify_order(self, order):
        """Handle order notifications with OCA orders (same as Ogle)."""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status == order.Completed:
            if order == self.order:
                # Entry order completed
                self.last_entry_price = order.executed.price
                self.last_entry_bar = len(self)
                
                if self.p.print_signals:
                    print(f"ERIS: LONG BUY EXECUTED at {order.executed.price:.5f} size={order.executed.size}")
                
                # Place protective OCA orders (linked together)
                if self.stop_level and self.take_level:
                    self.stop_order = self.sell(
                        size=order.executed.size,
                        exectype=bt.Order.Stop,
                        price=self.stop_level,
                        oco=self.limit_order  # Link to TP order
                    )
                    self.limit_order = self.sell(
                        size=order.executed.size,
                        exectype=bt.Order.Limit,
                        price=self.take_level,
                        oco=self.stop_order  # Link to SL order
                    )
                    if self.p.print_signals:
                        print(f"ERIS: OCA ORDERS PLACED - SL={self.stop_level:.5f} TP={self.take_level:.5f}")
                
                self.order = None
                # Reset state AFTER order completes successfully
                self._reset_state()
                
            else:
                # Exit order completed (SL or TP)
                exit_price = order.executed.price
                
                # Determine exit reason
                if order.exectype == bt.Order.Stop:
                    exit_reason = "STOP_LOSS"
                elif order.exectype == bt.Order.Limit:
                    exit_reason = "TAKE_PROFIT"
                else:
                    exit_reason = "MANUAL_CLOSE"
                
                self.last_exit_reason = exit_reason
                self.last_exit_price = exit_price  # Store for notify_trade pips calculation
                
                if self.p.print_signals:
                    print(f"ERIS: EXIT at {exit_price:.5f} reason={exit_reason}")
                
                # Clean up - OCA should auto-cancel the other order
                self.stop_order = None
                self.limit_order = None
                self.order = None
                self.stop_level = None
                self.take_level = None
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # With OCA, one order is canceled when the other executes - this is expected
            is_expected_cancel = (self.stop_order and self.limit_order)
            if not is_expected_cancel and self.p.print_signals:
                print(f"Order {order.getstatusname()}: {order.ref}")
            
            # Clean up references
            if self.order and order.ref == self.order.ref:
                self.order = None
                self._reset_state()
            if self.stop_order and order.ref == self.stop_order.ref:
                self.stop_order = None
            if self.limit_order and order.ref == self.limit_order.ref:
                self.limit_order = None
            if order == self.stop_order:
                self.stop_order = None
            if order == self.limit_order:
                self.limit_order = None

    def notify_trade(self, trade):
        """Handle trade notifications - use stored exit price for correct pips calculation."""
        if not trade.isclosed:
            return
        
        dt = self.data.datetime.datetime(0)
        pnl = trade.pnlcomm
        
        # Get entry and exit prices from stored values (set in notify_order)
        entry_price = self.last_entry_price if self.last_entry_price else 0
        exit_price = getattr(self, 'last_exit_price', 0)
        
        # Use stored exit reason from notify_order
        exit_reason = getattr(self, 'last_exit_reason', 'UNKNOWN')
        
        # Update statistics
        self.trades += 1
        if pnl > 0:
            self.wins += 1
            self.gross_profit += pnl
        else:
            self.losses += 1
            self.gross_loss += abs(pnl)
        
        # Store trade for yearly stats
        self._trade_pnls.append({
            'date': dt,
            'year': dt.year,
            'month': dt.month,
            'pnl': pnl,
            'is_winner': pnl > 0
        })
        
        if self.p.print_signals:
            pips = (exit_price - entry_price) / self.p.forex_pip_value if entry_price > 0 and exit_price > 0 and self.p.forex_pip_value > 0 else 0
            print(f"ERIS TRADE CLOSED: Entry={entry_price:.5f} Exit={exit_price:.5f} P&L={pnl:.2f} Pips={pips:.1f} ({exit_reason})")
        
        # Record exit
        self._record_exit(dt, exit_price, pnl, exit_reason)
        
        # Mark that exit occurred this bar (prevents re-entry same bar)
        self.exit_this_bar = True
        
        # Reset levels after trade close
        self.stop_level = None
        self.take_level = None

    def stop(self):
        """Strategy end - print summary and close reporting."""
        # Close any open position
        if self.position:
            self.close()
        
        # Calculate basic metrics
        win_rate = (self.wins / self.trades * 100) if self.trades > 0 else 0
        profit_factor = (self.gross_profit / self.gross_loss) if self.gross_loss > 0 else float('inf')
        
        final_value = self.broker.get_value()
        total_pnl = final_value - STARTING_CASH
        
        # =================================================================
        # ADVANCED METRICS: Drawdown, Sharpe Ratio
        # =================================================================
        max_drawdown_pct = 0.0
        sharpe_ratio = 0.0
        
        # Calculate Max Drawdown
        if len(self._portfolio_values) > 1:
            peak = self._portfolio_values[0]
            for value in self._portfolio_values:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak * 100.0
                if drawdown > max_drawdown_pct:
                    max_drawdown_pct = drawdown
        
        # Calculate Sharpe Ratio
        if len(self._portfolio_values) > 10:
            returns = []
            for i in range(1, len(self._portfolio_values)):
                ret = (self._portfolio_values[i] - self._portfolio_values[i-1]) / self._portfolio_values[i-1]
                returns.append(ret)
            
            if len(returns) > 0:
                returns_array = np.array(returns)
                mean_return = np.mean(returns_array)
                std_return = np.std(returns_array)
                # Annualized Sharpe (assuming 5-minute data, 252 trading days)
                periods_per_year = 252 * 24 * 12  # 5-minute periods per year
                if std_return > 0:
                    sharpe_ratio = (mean_return * periods_per_year) / (std_return * np.sqrt(periods_per_year))
        
        # =================================================================
        # ADVANCED METRICS: CAGR, Sortino, Calmar, Monte Carlo
        # =================================================================
        cagr = 0.0
        sortino_ratio = 0.0
        calmar_ratio = 0.0
        monte_carlo_dd_95 = 0.0
        monte_carlo_dd_99 = 0.0
        
        # Calculate CAGR
        if len(self._portfolio_values) > 1 and STARTING_CASH > 0:
            total_return = final_value / STARTING_CASH
            # Calculate years from actual trading period
            if self._trade_pnls:
                first_date = self._trade_pnls[0]['date']
                last_date = self._trade_pnls[-1]['date']
                days = (last_date - first_date).days
                years = max(days / 365.25, 0.1)
            else:
                years = len(self._portfolio_values) / (252 * 24 * 12)
                years = max(years, 0.1)
            
            if total_return > 0:
                cagr = (pow(total_return, 1.0 / years) - 1.0) * 100.0
        
        # Calculate Sortino Ratio (uses downside deviation)
        if len(self._portfolio_values) > 10:
            returns = []
            for i in range(1, len(self._portfolio_values)):
                ret = (self._portfolio_values[i] - self._portfolio_values[i-1]) / self._portfolio_values[i-1]
                returns.append(ret)
            
            if len(returns) > 0:
                returns_array = np.array(returns)
                mean_return = np.mean(returns_array)
                
                # Downside deviation: std of negative returns only
                negative_returns = returns_array[returns_array < 0]
                if len(negative_returns) > 0:
                    downside_dev = np.std(negative_returns)
                    periods_per_year = 252 * 24 * 12
                    if downside_dev > 0:
                        sortino_ratio = (mean_return * periods_per_year) / (downside_dev * np.sqrt(periods_per_year))
        
        # Calculate Calmar Ratio (CAGR / Max Drawdown)
        if max_drawdown_pct > 0:
            calmar_ratio = cagr / max_drawdown_pct
        
        # Monte Carlo Simulation
        if len(self._trade_pnls) >= 20:
            n_simulations = 10000
            pnl_list = [t['pnl'] for t in self._trade_pnls]
            mc_max_drawdowns = []
            
            for _ in range(n_simulations):
                shuffled_pnl = np.random.permutation(pnl_list)
                equity = STARTING_CASH
                peak = equity
                max_dd = 0.0
                
                for pnl in shuffled_pnl:
                    equity += pnl
                    if equity > peak:
                        peak = equity
                    dd = (peak - equity) / peak * 100.0 if peak > 0 else 0.0
                    if dd > max_dd:
                        max_dd = dd
                
                mc_max_drawdowns.append(max_dd)
            
            mc_max_drawdowns = np.array(mc_max_drawdowns)
            monte_carlo_dd_95 = np.percentile(mc_max_drawdowns, 95)
            monte_carlo_dd_99 = np.percentile(mc_max_drawdowns, 99)
        
        # =================================================================
        # YEARLY STATISTICS WITH SHARPE/SORTINO
        # =================================================================
        yearly_stats = defaultdict(lambda: {
            'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0,
            'gross_profit': 0.0, 'gross_loss': 0.0, 'pnls': []
        })
        
        for trade in self._trade_pnls:
            year = trade['year']
            yearly_stats[year]['trades'] += 1
            yearly_stats[year]['pnl'] += trade['pnl']
            yearly_stats[year]['pnls'].append(trade['pnl'])
            if trade['is_winner']:
                yearly_stats[year]['wins'] += 1
                yearly_stats[year]['gross_profit'] += trade['pnl']
            else:
                yearly_stats[year]['losses'] += 1
                yearly_stats[year]['gross_loss'] += abs(trade['pnl'])
        
        # Calculate yearly Sharpe and Sortino
        for year in yearly_stats:
            pnls = yearly_stats[year]['pnls']
            if len(pnls) > 1:
                pnl_array = np.array(pnls)
                mean_pnl = np.mean(pnl_array)
                std_pnl = np.std(pnl_array)
                
                if std_pnl > 0:
                    yearly_stats[year]['sharpe'] = (mean_pnl / std_pnl) * np.sqrt(len(pnls))
                else:
                    yearly_stats[year]['sharpe'] = 0.0
                
                neg_pnls = pnl_array[pnl_array < 0]
                if len(neg_pnls) > 0:
                    downside_std = np.std(neg_pnls)
                    if downside_std > 0:
                        yearly_stats[year]['sortino'] = (mean_pnl / downside_std) * np.sqrt(len(pnls))
                    else:
                        yearly_stats[year]['sortino'] = 0.0
                else:
                    yearly_stats[year]['sortino'] = float('inf') if mean_pnl > 0 else 0.0
            else:
                yearly_stats[year]['sharpe'] = 0.0
                yearly_stats[year]['sortino'] = 0.0
        
        # =================================================================
        # PRINT SUMMARY
        # =================================================================
        print("\n" + "=" * 70)
        print("=== ERIS STRATEGY SUMMARY ===")
        print("=" * 70)
        
        # Commission info
        if USE_FIXED_COMMISSION:
            real_calls = ForexCommission.commission_calls
            real_total = ForexCommission.total_commission
            total_lots = ForexCommission.total_lots
            avg_lots_per_order = total_lots / real_calls if real_calls > 0 else 0
            avg_commission_per_trade = real_total / self.trades if self.trades > 0 else 0
            print(f"Commission: ${COMMISSION_PER_LOT_PER_ORDER:.2f}/lot/order (Darwinex Zero)")
            print(f"Total commission: ${real_total:,.2f} | Avg per trade: ${avg_commission_per_trade:.2f}")
        else:
            print("Commission: DISABLED")
        
        print(f"Total Trades: {self.trades}")
        print(f"Wins: {self.wins} | Losses: {self.losses}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Profit Factor: {profit_factor:.2f}")
        print(f"Gross Profit: {self.gross_profit:,.2f}")
        print(f"Gross Loss: {self.gross_loss:,.2f}")
        print(f"Net P&L: {total_pnl:,.2f}")
        print(f"Final Value: {final_value:,.2f}")
        
        # Advanced Metrics with quality indicators
        print(f"\n{'='*70}")
        print("ADVANCED RISK METRICS")
        print(f"{'='*70}")
        
        sharpe_status = "Poor" if sharpe_ratio < 0.5 else "Marginal" if sharpe_ratio < 1.0 else "Good" if sharpe_ratio < 2.0 else "Excellent"
        print(f"Sharpe Ratio:    {sharpe_ratio:>8.2f}  [{sharpe_status}]")
        
        sortino_status = "Poor" if sortino_ratio < 0.5 else "Marginal" if sortino_ratio < 1.0 else "Good" if sortino_ratio < 2.0 else "Excellent"
        print(f"Sortino Ratio:   {sortino_ratio:>8.2f}  [{sortino_status}]")
        
        cagr_status = "Below Market" if cagr < 8 else "Market-level" if cagr < 12 else "Good" if cagr < 20 else "Exceptional"
        print(f"CAGR:            {cagr:>7.2f}%  [{cagr_status}]")
        
        dd_status = "Excellent" if max_drawdown_pct < 10 else "Acceptable" if max_drawdown_pct < 20 else "High" if max_drawdown_pct < 30 else "Dangerous"
        print(f"Max Drawdown:    {max_drawdown_pct:>7.2f}%  [{dd_status}]")
        
        calmar_status = "Poor" if calmar_ratio < 0.5 else "Acceptable" if calmar_ratio < 1.0 else "Good" if calmar_ratio < 2.0 else "Excellent"
        print(f"Calmar Ratio:    {calmar_ratio:>8.2f}  [{calmar_status}]")
        
        if monte_carlo_dd_95 > 0:
            mc_ratio = monte_carlo_dd_95 / max_drawdown_pct if max_drawdown_pct > 0 else 0
            mc_status = "Good" if mc_ratio < 1.5 else "Caution" if mc_ratio < 2.0 else "Warning"
            print(f"\nMonte Carlo Analysis (10,000 simulations):")
            print(f"  95th Percentile DD: {monte_carlo_dd_95:>6.2f}%  [{mc_status}]")
            print(f"  99th Percentile DD: {monte_carlo_dd_99:>6.2f}%")
            print(f"  Historical vs MC95: {mc_ratio:.2f}x")
        
        print(f"{'='*70}")
        
        # Yearly Statistics
        if yearly_stats:
            print(f"\n{'='*70}")
            print("YEARLY STATISTICS")
            print(f"{'='*70}")
            print(f"{'Year':<6} {'Trades':>7} {'WR%':>7} {'PF':>7} {'PnL':>12} {'Sharpe':>8} {'Sortino':>8}")
            print(f"{'-'*70}")
            
            for year in sorted(yearly_stats.keys()):
                stats = yearly_stats[year]
                wr = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
                year_pf = (stats['gross_profit'] / stats['gross_loss']) if stats['gross_loss'] > 0 else float('inf')
                year_sharpe = stats.get('sharpe', 0.0)
                year_sortino = stats.get('sortino', 0.0)
                
                sortino_str = f"{year_sortino:>7.2f}" if year_sortino != float('inf') else "    inf"
                
                print(f"{year:<6} {stats['trades']:>7} {wr:>6.1f}% {year_pf:>7.2f} ${stats['pnl']:>10,.0f} {year_sharpe:>8.2f} {sortino_str}")
            
            print(f"{'='*70}")
        
        # Close trade report
        if self.trade_report_file:
            try:
                self.trade_report_file.write("\n" + "=" * 70 + "\n")
                self.trade_report_file.write("SUMMARY\n")
                self.trade_report_file.write("=" * 70 + "\n")
                self.trade_report_file.write(f"Total Trades: {self.trades}\n")
                self.trade_report_file.write(f"Wins: {self.wins} | Losses: {self.losses}\n")
                self.trade_report_file.write(f"Win Rate: {win_rate:.1f}%\n")
                self.trade_report_file.write(f"Profit Factor: {profit_factor:.2f}\n")
                self.trade_report_file.write(f"Max Drawdown: {max_drawdown_pct:.2f}%\n")
                self.trade_report_file.write(f"Sharpe Ratio: {sharpe_ratio:.2f}\n")
                self.trade_report_file.write(f"Sortino Ratio: {sortino_ratio:.2f}\n")
                self.trade_report_file.write(f"CAGR: {cagr:.2f}%\n")
                self.trade_report_file.write(f"Calmar Ratio: {calmar_ratio:.2f}\n")
                if monte_carlo_dd_95 > 0:
                    self.trade_report_file.write(f"Monte Carlo DD 95%: {monte_carlo_dd_95:.2f}%\n")
                    self.trade_report_file.write(f"Monte Carlo DD 99%: {monte_carlo_dd_99:.2f}%\n")
                self.trade_report_file.write(f"Net P&L: {total_pnl:,.2f}\n")
                self.trade_report_file.write(f"Final Value: {final_value:,.2f}\n")
                self.trade_report_file.close()
            except Exception as e:
                print(f"Report close error: {e}")


# =============================================================================
# SL/TP OBSERVER FOR VISUAL PLOTTING
# =============================================================================

class SLTPObserver(bt.Observer):
    """Stop Loss and Take Profit Observer for plotting SL/TP levels on chart."""
    lines = ('sl', 'tp',)
    plotinfo = dict(plot=True, subplot=False)
    plotlines = dict(
        sl=dict(color='red', ls='--', linewidth=1.0),
        tp=dict(color='green', ls='--', linewidth=1.0)
    )
    
    def next(self):
        strat = self._owner
        if strat.position:
            self.lines.sl[0] = strat.stop_level if strat.stop_level else float('nan')
            self.lines.tp[0] = strat.take_level if strat.take_level else float('nan')
        else:
            self.lines.sl[0] = float('nan')
            self.lines.tp[0] = float('nan')


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == '__main__':
    # Data path
    BASE = Path(__file__).resolve().parent.parent.parent
    DATA_FILE = BASE / 'data' / DATA_FILENAME
    
    if not DATA_FILE.exists():
        print(f"Data file not found: {DATA_FILE}")
        raise SystemExit(1)
    
    # Parse dates
    def parse_date(s):
        try:
            return datetime.strptime(s, '%Y-%m-%d')
        except Exception:
            return None
    
    # Create data feed
    feed_kwargs = dict(
        dataname=str(DATA_FILE),
        dtformat='%Y%m%d',
        tmformat='%H:%M:%S',
        datetime=0,
        time=1,
        open=2,
        high=3,
        low=4,
        close=5,
        volume=6,
        timeframe=bt.TimeFrame.Minutes,
        compression=5
    )
    
    fd = parse_date(FROMDATE)
    td = parse_date(TODATE)
    if fd:
        feed_kwargs['fromdate'] = fd
    if td:
        feed_kwargs['todate'] = td
    
    data = bt.feeds.GenericCSVData(**feed_kwargs)
    
    # Create cerebro
    cerebro = bt.Cerebro(stdstats=False)
    
    # =========================================================================
    # TIMEFRAME RESAMPLING - Convert 5M to higher timeframes if configured
    # =========================================================================
    if RESAMPLE_MINUTES > 5:
        # Use resampledata ONLY (not adddata) - it handles everything
        cerebro.resampledata(
            data,
            timeframe=bt.TimeFrame.Minutes,
            compression=RESAMPLE_MINUTES,
            name=FOREX_INSTRUMENT
        )
        print(f"Resampling: 5M -> {RESAMPLE_MINUTES}M")
    else:
        cerebro.adddata(data, name=FOREX_INSTRUMENT)
    cerebro.broker.setcash(STARTING_CASH)
    
    # Forex broker configuration - use ForexCommission for all pairs
    is_jpy = _CURRENT_CONFIG.get('is_jpy', 'JPY' in FOREX_INSTRUMENT)
    commission_info = ForexCommission(
        is_jpy_pair=is_jpy,
        jpy_rate=150.0  # Approximate rate for JPY P&L conversion
    )
    cerebro.broker.addcommissioninfo(commission_info, name=FOREX_INSTRUMENT)
    
    cerebro.addstrategy(Eris)
    
    # Add observers
    try:
        cerebro.addobserver(bt.observers.BuySell, barplot=False, plotdist=Eris.params.buy_sell_plotdist)
    except Exception:
        cerebro.addobserver(bt.observers.BuySell, barplot=False)
    
    # Add SL/TP lines observer if enabled
    if PLOT_SLTP_LINES:
        try:
            cerebro.addobserver(SLTPObserver)
        except Exception as e:
            print(f"Warning: Could not add SLTP observer: {e}")
    
    cerebro.addobserver(bt.observers.Value)
    
    print(f"=== ERIS STRATEGY === ({FROMDATE} to {TODATE})")
    print(f"Data: {DATA_FILENAME}")
    print(f"Timeframe: {RESAMPLE_MINUTES}M")
    print(f"Instrument: {FOREX_INSTRUMENT} (Pip Value: {_CURRENT_CONFIG['pip_value']})")
    print(f"Pullback Candles: {LONG_PULLBACK_NUM_CANDLES}")
    print(f"Breakout Delay: {LONG_BREAKOUT_DELAY} ({LONG_BREAKOUT_DELAY_CANDLES} candles)")
    print(f"Max Entry Candles: {LONG_ENTRY_MAX_CANDLES}")
    print(f"Before Candles: {LONG_BEFORE_CANDLES} ({LONG_BEFORE_NUM_CANDLES})")
    print(f"MR Filter: {USE_MEAN_REVERSION_ENTRY_FILTER} (Z: [{MR_ENTRY_ZSCORE_MIN}, {MR_ENTRY_ZSCORE_MAX}])")
    print(f"Oversold Duration: {USE_OVERSOLD_DURATION_FILTER} ({OVERSOLD_MIN_CANDLES}-{OVERSOLD_MAX_CANDLES} candles)")
    print(f"R:R = 1:{LONG_ATR_TP_MULTIPLIER/LONG_ATR_SL_MULTIPLIER:.0f}")
    print()
    
    # Run backtest
    results = cerebro.run()
    final_value = cerebro.broker.getvalue()
    
    print(f"\nFinal Portfolio Value: {final_value:,.2f}")
    
    # Plot if enabled
    if ENABLE_PLOT:
        try:
            cerebro.plot(style='candlestick')
        except Exception as e:
            print(f"Plot error: {e}")
