#!/usr/bin/env python3
"""
================================================================================
OGLE OPTIMIZER UNIVERSAL - Multi-Asset Grid Search
================================================================================
SINGLE FILE to optimize OGLE on ANY forex asset.

USAGE:
    python ogle_optimizer_universal.py EURUSD 1      # Phase 1 for EURUSD
    python ogle_optimizer_universal.py USDCHF 3     # Phase 3 for USDCHF
    python ogle_optimizer_universal.py EURUSD all   # All phases 1-4
    python ogle_optimizer_universal.py EURUSD quick # Quick test (1 year)

OPTIMIZATION PHASES:
    1 = SL/TP Multipliers (25 combinations)
    2 = Entry Window + Pullback (18 combinations)
    3 = EMAs (144 combinations) <- MOST IMPORTANT
    4 = ATR Filter (16 combinations)
    5 = FINAL COMBINATIONS (generates LOGS for analysis)
    
    === NEW PHASES (Dec 2025) - Starting from BestPnL baseline ===
    6 = Entry Window Extended (10 combinations) - Tests window 1-10
    7 = ATR Increment/Decrement Filter (based on log patterns)
    
    ⚠️ REFINEMENT PHASE (POST-OPTIMIZATION):
    - NOT optimized by backtesting
    - Analyze trade LOGS to identify:
      * Best entry hours
      * Winning/losing candle patterns
      * Optimal ATR ranges
      * Effective trend angles
    - Filters are applied based on LOG EVIDENCE

CORRECT PROCESS (DO NOT SKIP STEPS):
    1. Run phase 1 -> Record best SL/TP
    2. Run phase 2 -> Record best Window/Pullback  
    3. Run phase 3 -> Record best EMAs
    4. Run phase 4 -> Record best ATR thresholds
    5. Run phase 5 -> FINAL COMBINATIONS with best params
       → Generates detailed LOGS for analysis
    6. Run phase 6 -> Entry Window 1-10 (from BestPnL baseline)
    7. Run phase 7 -> ATR Increment/Decrement filter
    8. REFINEMENT BY LOGS (manual):
       - Analyze winning vs losing trade hours
       - Analyze real ATR at entry moments
       - Analyze candle patterns
       - Apply filters based on evidence
    9. Copy optimal values to sunrise_ogle_{ASSET}_pro.py

KNOWN ERRORS (DO NOT REPEAT):
    ❌ DataFrame.upper() -> Cause: PandasData. Solution: Use GenericCSVData
    ❌ 0 trades -> Cause: use_forex_position_calc=False. Solution: Keep True
    ❌ No progress -> Cause: Output buffering. Solution: flush=True in prints
    ❌ Log PF ≠ Backtest PF -> Cause: Commission not in logs. Solution: Always validate

REQUIRED FILES:
    - data/{ASSET}_5m_5Yea.csv (historical data)
    - sunrise_ogle_template.py (base strategy)

OUTPUT:
    - Console: Progress and TOP 10 results
    - JSON: ogle_results_{ASSET}_phase{N}.json

COMMISSION:
    - $2.50/lot/order (Darwinex Zero rates)
    - Applied via ForexCommission class
    - ALWAYS included in all backtests

Author: Iván Lahuerta
Date: December 2025
================================================================================
"""

import sys
import json
import math
from pathlib import Path
from datetime import datetime
from itertools import product
from collections import defaultdict

# Add project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).parent))

import backtrader as bt

# Import strategy and commission from template
from sunrise_ogle_template import SunriseOgle, ForexCommission, INSTRUMENT_CONFIGS


# =============================================================================
# CONFIGURACIÓN DE INSTRUMENTOS
# =============================================================================
INSTRUMENT_DATA = {
    'EURUSD': {
        'data_file': 'EURUSD_5m_5Yea.csv',
        'pip_value': 0.0001,
        'pip_decimal_places': 5,
        'spread': 0.6,
        # Horarios por defecto (London/NY overlap) - SE OPTIMIZAN EN FASE 5
        'time_start': 7,
        'time_end': 16,
    },
    'USDCHF': {
        'data_file': 'USDCHF_5m_5Yea.csv',
        'pip_value': 0.0001,
        'pip_decimal_places': 5,
        'spread': 0.7,
        # Horarios optimizados para USDCHF
        'time_start': 7,
        'time_end': 13,
    },
    'USDJPY': {
        'data_file': 'USDJPY_5m_5Yea.csv',
        'pip_value': 0.01,
        'pip_decimal_places': 3,
        'spread': 1.0,
        'time_start': 0,
        'time_end': 8,
    },
    'GBPUSD': {
        'data_file': 'GBPUSD_5m_5Yea.csv',
        'pip_value': 0.0001,
        'pip_decimal_places': 5,
        'spread': 0.9,
        'time_start': 7,
        'time_end': 16,
    },
    'AUDUSD': {
        'data_file': 'AUDUSD_5m_5Yea.csv',
        'pip_value': 0.0001,
        'pip_decimal_places': 5,
        'spread': 0.8,
        'time_start': 0,
        'time_end': 8,
    },
    'USDCAD': {
        'data_file': 'USDCAD_5m_5Yea.csv',
        'pip_value': 0.0001,
        'pip_decimal_places': 5,
        'spread': 0.8,
        'time_start': 7,
        'time_end': 16,
    },
}


# =============================================================================
# GRIDS DE OPTIMIZACIÓN POR FASE
# =============================================================================

# Fase 1: SL/TP (Risk:Reward) - 25 combinaciones
PHASE1_GRID = {
    'long_atr_sl_multiplier': [1.5, 2.0, 2.5, 3.0, 3.5],
    'long_atr_tp_multiplier': [6.0, 8.0, 10.0, 12.0, 15.0],
}

# Fase 2: Entry Window + Pullback - 18 combinaciones
PHASE2_GRID = {
    'long_entry_window_periods': [1, 2, 3, 5, 7, 10],
    'long_pullback_max_candles': [1, 2, 3],
}

# Fase 3: EMAs - 144 combinaciones (LA MÁS IMPORTANTE)
PHASE3_GRID = {
    'ema_fast_length': [12, 18, 24],
    'ema_medium_length': [18, 24, 30],
    'ema_slow_length': [18, 24, 30, 36],
    'ema_filter_price_length': [40, 50, 60, 70],
}

# Fase 4: ATR Filter - 16 combinaciones (standard pairs: 0.0001 pip value)
PHASE4_GRID = {
    'long_atr_min_threshold': [0.000150, 0.000200, 0.000250, 0.000300],
    'long_atr_max_threshold': [0.000500, 0.000700, 0.000900, 0.001100],
}

# Fase 4 JPY: ATR Filter for JPY pairs - values 100x larger (0.01 pip value)
PHASE4_GRID_JPY = {
    'long_atr_min_threshold': [0.015, 0.020, 0.025, 0.030],
    'long_atr_max_threshold': [0.050, 0.070, 0.090, 0.110],
}

# =============================================================================
# NEW PHASES (Dec 2025) - Starting from BestPnL baseline
# =============================================================================
# BestPnL baseline: ATR 0.00015-0.0005, 376 trades, PF 1.16, $22,434 PnL, DD 11.4%, 1 neg year

# Phase 6: Entry Window Extended (1-10) - 10 combinations
# Testing if different entry windows improve PF from BestPnL baseline
PHASE6_GRID = {
    'long_entry_window_periods': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
}

# Phase 7: ATR Increment/Decrement Filter - Based on log analysis patterns
# Tests filtering by ATR change between candles (momentum indicator)
PHASE7_GRID = {
    # ATR Increment filter (volatility increasing)
    'long_use_atr_increment_filter': [True, False],
    'long_atr_increment_min_threshold': [0.000020, 0.000030, 0.000050],
    'long_atr_increment_max_threshold': [0.000080, 0.000100, 0.000150],
}

# Phase 7b: ATR Decrement filter (volatility decreasing)
PHASE7B_GRID = {
    'long_use_atr_decrement_filter': [True, False],
    'long_atr_decrement_min_threshold': [-0.000050, -0.000030, -0.000020],
    'long_atr_decrement_max_threshold': [-0.000010, -0.000005, -0.000001],
}

# =============================================================================
# Phase 8: ANGLE + HOUR + ATR Combined Filter (Dec 2025)
# Based on comprehensive LOG ANALYSIS showing:
#   - Best angles: 0-60° (PF 1.20-1.96), worst: 60-80° (PF 0.90)
#   - Best hours: 0-3, 7-8, 21-23 (PF 1.3-4.3), worst: 12-13, 17-18, 20 (PF 0.0-0.5)
#   - Best ATR: 0.00020-0.00025, 0.00030-0.00035 (PF 1.54-1.72)
#   - Best ATR change: Strong Inc >0.00005 (PF 1.77), Mod Dec (PF 1.46)
# =============================================================================
PHASE8_GRID = {
    # Angle filter (based on log analysis: 0-60° much better than 60-80°)
    'long_use_angle_filter': [True, False],
    'long_min_angle': [0, 20, 40],  # Best PF ranges: 0-20, 20-40, 40-60, 80-90
    'long_max_angle': [60, 80, 85],  # Avoid 60-80 alone (worst PF)
}

# Phase 8b: Hour filter combinations (optimal hours from log analysis)
PHASE8B_GRID = {
    # Time filter (best hours: 21-03, 07-08, avoid 12-13, 17-20)
    'use_time_range_filter': [True],
    'entry_start_hour': [0, 7, 21],
    'entry_end_hour': [8, 11, 3],  # Note: 21-03 crosses midnight
}

# Phase 8c: Combined ATR range refinement
PHASE8C_GRID = {
    # Refined ATR based on log analysis
    'long_atr_min_threshold': [0.000200, 0.000250, 0.000300],
    'long_atr_max_threshold': [0.000350, 0.000400, 0.000450],
}

# Fase 5: COMBINACIONES FINALES - Prueba mejores configs de F4 con print_signals=True
# Genera LOGS detallados para análisis posterior de:
#   - Horarios óptimos (por análisis de trades)
#   - ATR real en momentos de entry
#   - Patrones de velas
#   - Ángulos de tendencia
PHASE5_COMBINATIONS = {
    'EURUSD': [
        # Combo 1: Mejor PF (1.21)
        {'name': 'BestPF', 'long_atr_min_threshold': 0.000250, 'long_atr_max_threshold': 0.000500},
        # Combo 2: Mejor PnL (+$22,434) y solo 1 año negativo
        {'name': 'BestPnL', 'long_atr_min_threshold': 0.000150, 'long_atr_max_threshold': 0.000500},
        # Combo 3: Menor DD (10.6%)
        {'name': 'BestDD', 'long_atr_min_threshold': 0.000200, 'long_atr_max_threshold': 0.000500},
    ],
    'USDCAD': [
        # Phase 3 Best: EMAs 24/30/36/40, PF=1.01, +$1,195
        {'name': 'Phase3_Best', 'ema_fast_length': 24, 'ema_medium_length': 30, 'ema_slow_length': 36, 'ema_filter_price_length': 40},
    ],
    'USDJPY': [
        # Phase 1-4 Best: SL=1.5, TP=15.0, Window=1, Pullback=1, EMAs 12/24/24/50, ATR 0.015-0.05
        {'name': 'Phase4_Best', 
         'long_atr_sl_multiplier': 1.5, 'long_atr_tp_multiplier': 15.0,
         'long_entry_window_periods': 1, 'long_pullback_max_candles': 1,
         'ema_fast_length': 12, 'ema_medium_length': 24, 'ema_slow_length': 24, 'ema_filter_price_length': 50,
         'long_use_atr_filter': True, 'long_atr_min_threshold': 0.015, 'long_atr_max_threshold': 0.05},
    ],
}

# DEPRECATED - Time Filter por backtesting (genera overfitting)
# Los horarios se determinan por ANÁLISIS DE LOGS, no por grid search
PHASE5_GRID_DEPRECATED = {
    'entry_start_hour': [0, 6, 7, 8, 21],
    'entry_end_hour': [3, 8, 13, 16, 18],
}

# =============================================================================
# USDCAD SPECIFIC PHASES (Dec 22, 2025) - Based on Log Analysis
# =============================================================================
# BASELINE: EMAs 24/30/36/40, PF=1.01, 312 trades, +$1,195 (Phase 3)
# 
# LOG ANALYSIS FINDINGS (temp_reports/USDCAD_trades_20251222_084850.txt):
#   - Ángulos negativos: WR 0%, -$5,877 → EXCLUIR
#   - Mejor rango ángulo: 55-75 (logs: PF 1.32) → VALIDAR CON BACKTEST
#   - ATR < 0.0003: WR 29.9%, PF 1.56 (logs) → VALIDAR
#   - ATR < 0.0004: WR 23.3%, PF 1.11 (logs) → VALIDAR  
#   - Viernes: WR 7.8%, -$11,548 → NO SE PUEDE FILTRAR EN OGLE
#   - Horas rentables: 0,1,3,7,10,18,21,22 (scattered)
#   - Peores horas: 4,8,11,12 (WR 0-8%)
#
# CRITERIOS MÍNIMOS (GUÍA):
#   - 5 años completos (2020-2025) ✓
#   - Mínimo 120 trades
#   - PF > 1.5
#
# PROCESO SECUENCIAL:
#   1. Phase 6A: Filtro ÁNGULO (probar rangos)
#   2. Phase 6B: Filtro HORAS (usando mejor ángulo de 6A)
#   3. Phase 6C: Filtro ATR (usando mejor ángulo+horas)
# =============================================================================

# PHASE 6A: ANGLE FILTER - First optimization (9 combinations)
# Baseline: SIN filtro de ángulo (312 trades, PF 1.01)
# Log analysis sugiere 55-75 tiene mejor PF, pero necesitamos ≥120 trades
USDCAD_PHASE6A_ANGLE = {
    'long_use_angle_filter': [True],
    'long_min_angle': [35, 40, 45, 50, 55],    # Test lower bounds
    'long_max_angle': [70, 75, 80, 85],        # Test upper bounds  
}  # 5x4 = 20 combinations

# PHASE 6B: HOUR FILTER - After best angle (needs to be updated with 6A results)
# OGLE only allows RANGE (start-end), testing logical ranges
# NOTE: Using best angle from 6A: 45-75 (145 trades, PF 1.51, $19,185)
USDCAD_PHASE6B_HOURS = {
    # ANGLE FROM 6A BEST
    'long_use_angle_filter': [True],
    'long_min_angle': [45],
    'long_max_angle': [75],
    # HOUR RANGE FILTER
    'use_time_range_filter': [True],
    # Testing ranges based on log analysis:
    # - Night session: 21-03 (profitable hours: 0,1,21,22)
    # - Morning: 7-11 (profitable hour: 7,10 but 8,11 are worst)
    # - Evening: 18-22 (profitable hours: 18,21,22)
    # - Full session: 0-23 (baseline), 0-12 (morning), 12-23 (afternoon)
    'entry_start_hour': [0, 7, 18, 21],
    'entry_end_hour': [4, 8, 12, 23],
}  # 4x4 = 16 combinations

# PHASE 6C: ATR FILTER REFINEMENT - After angle+hours
# Log analysis: ATR < 0.0003 → PF 1.56 (67 trades, need more)
#               ATR < 0.0004 → PF 1.11 (210 trades, acceptable)
# USING BEST FROM 6A+6B: Angle 45-75, Hours 18-12
USDCAD_PHASE6C_ATR = {
    # FROM 6A BEST
    'long_use_angle_filter': [True],
    'long_min_angle': [45],
    'long_max_angle': [75],
    # FROM 6B BEST
    'use_time_range_filter': [True],
    'entry_start_hour': [18],
    'entry_end_hour': [12],
    # ATR FILTER OPTIMIZATION
    'long_use_atr_filter': [True],
    'long_atr_min_threshold': [0.000150, 0.000200, 0.000250],
    'long_atr_max_threshold': [0.000300, 0.000350, 0.000400, 0.000450],
}  # 3x4 = 12 combinations (per angle+hour config)


# =============================================================================
# BASELINE PARAMETERS (starting point for optimization)
# =============================================================================
def get_baseline_params(instrument: str) -> dict:
    """Get baseline parameters for an instrument."""
    config = INSTRUMENT_DATA.get(instrument, INSTRUMENT_DATA['EURUSD'])
    inst_config = INSTRUMENT_CONFIGS.get(instrument, INSTRUMENT_CONFIGS['EURUSD'])
    
    # INSTRUMENT-SPECIFIC EMAs based on Phase 3 optimization
    if instrument == 'USDCAD':
        # USDCAD Phase 3 Best: PF=1.01, +$1,195
        ema_fast = 24
        ema_medium = 30
        ema_slow = 36
        ema_filter = 40
        # USDCAD Phase 1 defaults
        sl_mult = 3.0
        tp_mult = 15.0
        # USDCAD Phase 4 - ATR filter OFF by default (Phase 4 results were worse)
        use_atr_filter = False
        atr_min = 0.000250
        atr_max = 0.000500
    elif instrument == 'USDJPY':
        # USDJPY defaults - ATR values 100x larger for JPY pairs
        ema_fast = 24
        ema_medium = 24
        ema_slow = 24
        ema_filter = 60
        sl_mult = 3.0
        tp_mult = 15.0
        use_atr_filter = True
        atr_min = 0.025  # 100x larger for JPY
        atr_max = 0.050  # 100x larger for JPY
    else:
        # EURUSD defaults (or other instruments)
        ema_fast = 24
        ema_medium = 24
        ema_slow = 24
        ema_filter = 60
        sl_mult = 3.0
        tp_mult = 15.0
        use_atr_filter = True
        atr_min = 0.000250
        atr_max = 0.000500
    
    return {
        # EMAs (INSTRUMENT-SPECIFIC from Phase 3)
        'ema_fast_length': ema_fast,
        'ema_medium_length': ema_medium,
        'ema_slow_length': ema_slow,
        'ema_confirm_length': 1,
        'ema_filter_price_length': ema_filter,
        'ema_exit_length': 25,
        
        # ATR Risk Management (OPTIMIZED Phase 1)
        'atr_length': 10,
        'long_atr_sl_multiplier': sl_mult,
        'long_atr_tp_multiplier': tp_mult,
        
        # Direction (Long-Only)
        'enable_long_trades': True,
        'enable_short_trades': False,
        
        # ATR Volatility Filter - INSTRUMENT-SPECIFIC
        'long_use_atr_filter': use_atr_filter,
        'long_atr_min_threshold': atr_min,
        'long_atr_max_threshold': atr_max,
        
        # ATR Increment/Decrement (disabled by default)
        'long_use_atr_increment_filter': False,
        'long_atr_increment_min_threshold': 0.000050,
        'long_atr_increment_max_threshold': 0.000080,
        'long_use_atr_decrement_filter': False,
        'long_atr_decrement_min_threshold': -0.000030,
        'long_atr_decrement_max_threshold': -0.000001,
        
        # Entry Filters
        'long_use_ema_order_condition': False,
        'long_use_price_filter_ema': True,
        'long_use_candle_direction_filter': False,
        'long_use_angle_filter': False,
        'long_min_angle': 35.0,
        'long_max_angle': 85.0,
        'long_angle_scale_factor': 10000.0,
        'long_use_ema_below_price_filter': False,
        
        # Pullback Entry System (OPTIMIZED Phase 2)
        'long_use_pullback_entry': True,
        'long_pullback_max_candles': 2,  # Phase 2: best PnL
        'long_entry_window_periods': 1,  # Phase 2: best PnL
        'window_offset_multiplier': 1.0,
        'use_window_time_offset': False,
        'window_price_offset_multiplier': 0.01,
        
        # Time Range Filter - DISABLED during optimization
        # Hours determined by LOG ANALYSIS, not backtesting
        'use_time_range_filter': False,
        'entry_start_hour': config['time_start'],
        'entry_start_minute': 0,
        'entry_end_hour': config['time_end'],
        'entry_end_minute': 0,
        
        # Position Sizing
        'size': 1,
        'enable_risk_sizing': True,
        'risk_percent': 0.005,
        'margin_pct': 3.33,
        'contract_size': 100000,
        
        # Forex Settings (auto-configured from INSTRUMENT_CONFIGS)
        'forex_instrument': instrument,
        'forex_pip_value': inst_config['pip_value'],
        'forex_pip_decimal_places': inst_config['pip_decimal_places'],
        'forex_lot_size': inst_config['lot_size'],
        'forex_atr_scale': inst_config['atr_scale'],
        'spread_pips': config['spread'],
        'use_forex_position_calc': True,  # ⚠️ CRITICAL: ALWAYS True
        
        # Display (disabled for optimization - CRITICAL for speed)
        'print_signals': False,
        'verbose_debug': False,
        'plot_result': False,
        'buy_sell_plotdist': 0.0005,
        'plot_sltp_lines': False,
    }


def get_bestpnl_baseline_params(instrument: str) -> dict:
    """
    Get BestPnL baseline parameters for new phases (6, 7).
    
    BestPnL Config (Dec 2025):
    - 376 trades (49% more than best PF)
    - $22,434 PnL (best total PnL)
    - Only 1 negative year (best consistency)
    - PF 1.16 (only 0.05 less than best)
    - DD 11.4% (better than best PF config)
    """
    baseline = get_baseline_params(instrument)
    
    # Override with BestPnL ATR settings
    baseline.update({
        'long_atr_min_threshold': 0.000150,  # BestPnL: more trades
        'long_atr_max_threshold': 0.000500,
    })
    
    return baseline


# =============================================================================
# BACKTEST RUNNER
# =============================================================================
def run_single_backtest(
    instrument: str,
    params_override: dict,
    fromdate: str = '2020-01-01',
    todate: str = '2025-12-01',
    starting_cash: float = 100000.0,
    use_bestpnl_baseline: bool = False,
) -> dict:
    """
    Run a single backtest with specific parameters.
    
    ⚠️ CRITICAL: Uses GenericCSVData (NOT PandasData) to avoid DataFrame.upper() error.
    ⚠️ CRITICAL: Always includes ForexCommission ($2.50/lot/order)
    
    Args:
        use_bestpnl_baseline: If True, uses BestPnL config as baseline (for phases 6, 7)
    """
    cerebro = bt.Cerebro()
    
    # Get instrument configuration
    config = INSTRUMENT_DATA.get(instrument)
    if not config:
        raise ValueError(f"Unknown instrument: {instrument}. Available: {list(INSTRUMENT_DATA.keys())}")
    
    # Load data with GenericCSVData (NOT PandasData)
    data_dir = PROJECT_ROOT / "data"
    data_path = data_dir / config['data_file']
    
    if not data_path.exists():
        raise FileNotFoundError(f"Archivo de datos no encontrado: {data_path}")
    
    # Formato CSV: Date,Time,Open,High,Low,Close,Volume
    # Date: 20200101, Time: 22:00:00
    data = bt.feeds.GenericCSVData(
        dataname=str(data_path),
        fromdate=datetime.strptime(fromdate, '%Y-%m-%d'),
        todate=datetime.strptime(todate, '%Y-%m-%d'),
        dtformat='%Y%m%d',
        tmformat='%H:%M:%S',
        datetime=0,
        time=1,
        open=2,
        high=3,
        low=4,
        close=5,
        volume=6,
        openinterest=-1,
        timeframe=bt.TimeFrame.Minutes,
        compression=5,
    )
    
    cerebro.adddata(data)
    cerebro.broker.set_cash(starting_cash)
    cerebro.broker.addcommissioninfo(ForexCommission())  # ⚠️ ALWAYS include commission
    
    # Combine baseline with overrides
    if use_bestpnl_baseline:
        baseline = get_bestpnl_baseline_params(instrument)
    else:
        baseline = get_baseline_params(instrument)
    final_params = {**baseline, **params_override}
    
    # Force silent mode
    final_params['print_signals'] = False
    final_params['verbose_debug'] = False
    final_params['plot_result'] = False
    final_params['plot_sltp_lines'] = False
    
    cerebro.addstrategy(SunriseOgle, **final_params)
    
    results = cerebro.run()
    strat = results[0]
    
    # Calcular métricas
    final_value = cerebro.broker.get_value()
    total_pnl = final_value - starting_cash
    
    # Obtener estadísticas de trades
    trades = getattr(strat, 'trades', 0)
    wins = getattr(strat, 'wins', 0)
    losses = getattr(strat, 'losses', 0)
    gross_profit = getattr(strat, 'gross_profit', 0.0)
    gross_loss = getattr(strat, 'gross_loss', 0.0)
    
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
    win_rate = (wins / trades * 100) if trades > 0 else 0
    
    # Max Drawdown
    max_dd = 0.0
    portfolio_values = getattr(strat, '_portfolio_values', [])
    if len(portfolio_values) > 1:
        peak = portfolio_values[0]
        for value in portfolio_values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100.0
            if dd > max_dd:
                max_dd = dd
    
    # Desglose anual
    yearly_pnl = defaultdict(float)
    trade_pnls = getattr(strat, '_trade_pnls', [])
    for t in trade_pnls:
        yearly_pnl[t['year']] += t['pnl']
    
    # Contar años negativos
    negative_years = sum(1 for pnl in yearly_pnl.values() if pnl < 0)
    
    return {
        'trades': trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_pnl': total_pnl,
        'max_drawdown': max_dd,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'yearly_pnl': dict(yearly_pnl),
        'negative_years': negative_years,
        'final_value': final_value,
    }


# =============================================================================
# OPTIMIZATION RUNNER
# =============================================================================
def run_optimization(
    instrument: str,
    param_grid: dict,
    phase_name: str = "",
    fromdate: str = '2020-01-01',
    todate: str = '2025-12-01',
    min_trades: int = 30,
    use_bestpnl_baseline: bool = False,
) -> list:
    """Run optimization over parameter grid.
    
    Args:
        use_bestpnl_baseline: If True, uses BestPnL config as baseline (for phases 6, 7)
    """
    
    print(f"\n{'='*70}", flush=True)
    print(f"OGLE OPTIMIZER - {instrument} - {phase_name}", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"Data range: {fromdate} to {todate}", flush=True)
    if use_bestpnl_baseline:
        print(f"⭐ Using BestPnL baseline (ATR 0.00015-0.0005, 376 trades)", flush=True)
    
    # Generate all combinations
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(product(*param_values))
    
    print(f"Parameters: {param_names}", flush=True)
    print(f"Total combinations: {len(combinations)}", flush=True)
    print(f"{'='*70}\n", flush=True)
    
    results = []
    
    for i, combo in enumerate(combinations, 1):
        params_override = dict(zip(param_names, combo))
        
        # Progress
        param_str = " | ".join([f"{k}={v}" for k, v in params_override.items()])
        print(f"[{i}/{len(combinations)}] {param_str}", end=" ", flush=True)
        
        try:
            result = run_single_backtest(
                instrument=instrument,
                params_override=params_override,
                fromdate=fromdate,
                todate=todate,
                use_bestpnl_baseline=use_bestpnl_baseline,
            )
            result['params'] = params_override
            results.append(result)
            
            # Quick summary
            print(f"-> T:{result['trades']} PF:{result['profit_factor']:.2f} "
                  f"WR:{result['win_rate']:.1f}% DD:{result['max_drawdown']:.1f}%", flush=True)
            
        except Exception as e:
            print(f"-> ERROR: {e}", flush=True)
    
    # Sort by Profit Factor (with minimum trades filter)
    valid_results = [r for r in results if r['trades'] >= min_trades]
    valid_results.sort(key=lambda x: x['profit_factor'], reverse=True)
    
    # Print top results
    print(f"\n{'='*70}", flush=True)
    print(f"TOP 10 RESULTS (min {min_trades} trades) - Sorted by Profit Factor", flush=True)
    print(f"{'='*70}", flush=True)
    
    for i, r in enumerate(valid_results[:10], 1):
        param_str = " | ".join([f"{k}={v}" for k, v in r['params'].items()])
        print(f"\n{i}. {param_str}", flush=True)
        print(f"   Trades: {r['trades']} | Wins: {r['wins']} | Losses: {r['losses']}", flush=True)
        print(f"   Win Rate: {r['win_rate']:.1f}% | Profit Factor: {r['profit_factor']:.2f}", flush=True)
        print(f"   Total PnL: ${r['total_pnl']:,.0f} | Max DD: {r['max_drawdown']:.1f}%", flush=True)
        if r['yearly_pnl']:
            print(f"   Negative Years: {r['negative_years']} | Yearly: {r['yearly_pnl']}", flush=True)
    
    # Best by different metrics
    if valid_results:
        print(f"\n{'='*70}", flush=True)
        print("BEST BY METRIC:", flush=True)
        print(f"{'='*70}", flush=True)
        
        best_pf = max(valid_results, key=lambda x: x['profit_factor'])
        best_pnl = max(valid_results, key=lambda x: x['total_pnl'])
        lowest_dd = min(valid_results, key=lambda x: x['max_drawdown'])
        
        print(f"\n  Best PF: {best_pf['profit_factor']:.2f} -> {best_pf['params']}", flush=True)
        print(f"  Best PnL: ${best_pnl['total_pnl']:,.0f} -> {best_pnl['params']}", flush=True)
        print(f"  Lowest DD: {lowest_dd['max_drawdown']:.1f}% -> {lowest_dd['params']}", flush=True)
    
    return valid_results


# =============================================================================
# GUARDAR RESULTADOS
# =============================================================================
def save_results(instrument: str, phase: str, results: list, fromdate: str, todate: str):
    """Guarda resultados en JSON para referencia futura."""
    output_file = Path(__file__).parent / f'ogle_results_{instrument}_phase{phase}.json'
    
    json_results = {
        'instrument': instrument,
        'phase': phase,
        'timestamp': datetime.now().isoformat(),
        'date_range': {'from': fromdate, 'to': todate},
        'top_results': [
            {
                'rank': i + 1,
                'params': r['params'],
                'trades': r['trades'],
                'profit_factor': round(r['profit_factor'], 3),
                'win_rate': round(r['win_rate'], 2),
                'total_pnl': round(r['total_pnl'], 2),
                'max_drawdown': round(r['max_drawdown'], 2),
                'negative_years': r['negative_years'],
                'yearly_pnl': {str(k): round(v, 2) for k, v in r['yearly_pnl'].items()},
            }
            for i, r in enumerate(results[:10])
        ]
    }
    
    with open(output_file, 'w') as f:
        json.dump(json_results, f, indent=2)
    
    print(f"\n✅ Resultados guardados en: {output_file}", flush=True)
    return output_file


# =============================================================================
# MAIN
# =============================================================================
def print_usage():
    """Print script usage."""
    print("""
================================================================================
USAGE: python ogle_optimizer_universal.py <INSTRUMENT> <PHASE>
================================================================================

AVAILABLE INSTRUMENTS:
    EURUSD, USDCHF, USDJPY, GBPUSD, AUDUSD

OPTIMIZATION PHASES:
    1     = SL/TP Multipliers (25 combinations)
    2     = Entry Window + Pullback (18 combinations)
    3     = EMAs (144 combinations) <- MOST IMPORTANT
    4     = ATR Filter (16 combinations)
    5     = FINAL COMBINATIONS (generates LOGS for analysis)
    
    === NEW PHASES (from BestPnL baseline) ===
    6     = Entry Window Extended 1-10 (10 combinations)
    7     = ATR Increment Filter (18 combinations)
    7b    = ATR Decrement Filter (18 combinations)
    
    all   = Phases 1-4 sequentially
    quick = Quick test with 1 year of data

REFINEMENT PHASE (POST-OPTIMIZATION):
    After Phase 5, analyze LOGS manually to:
    - Identify optimal entry hours
    - Validate effective ATR ranges
    - Detect winning candle patterns
    - Calculate useful trend angles

EXAMPLES:
    python ogle_optimizer_universal.py EURUSD 1     # Phase 1
    python ogle_optimizer_universal.py EURUSD 5     # Final combinations
    python ogle_optimizer_universal.py EURUSD 6     # Entry Window (from BestPnL)
    python ogle_optimizer_universal.py EURUSD 7     # ATR Increment filter
    python ogle_optimizer_universal.py EURUSD all   # Phases 1-4

COMPLETE PROCESS:
    1. Phases 1-4: Optimization by grid search
    2. Phase 5: Generate LOGS with best combinations
    3. Analyze LOGS → Identify additional filters
    4. Phases 6-7: Test from BestPnL baseline
    5. Apply filters based on LOG EVIDENCE
    6. Copy final values to sunrise_ogle_{ASSET}_pro.py
    
COMMISSION:
    All backtests include $2.50/lot/order (Darwinex Zero)
================================================================================
""")


def run_phase5_combinations(instrument: str, fromdate: str, todate: str):
    """
    Fase 5: Ejecuta las mejores combinaciones de F1-F4 con LOGS detallados.
    
    Genera archivos de log para análisis posterior de:
    - Horarios de trades ganadores vs perdedores
    - ATR real en momento de entrada
    - Patrones de velas
    - Información para refinamiento manual
    """
    print(f"\n{'='*70}", flush=True)
    print(f"FASE 5: COMBINACIONES FINALES - {instrument}", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"Objetivo: Generar LOGS detallados para análisis de refinamiento", flush=True)
    print(f"Rango: {fromdate} a {todate}", flush=True)
    
    # Obtener combinaciones para este instrumento
    combinations = PHASE5_COMBINATIONS.get(instrument, [])
    if not combinations:
        print(f"⚠️ No hay combinaciones definidas para {instrument}", flush=True)
        print(f"   Define PHASE5_COMBINATIONS['{instrument}'] primero", flush=True)
        return []
    
    print(f"Combinaciones a probar: {len(combinations)}", flush=True)
    print(f"{'='*70}\n", flush=True)
    
    results = []
    
    for i, combo in enumerate(combinations, 1):
        combo_name = combo.pop('name', f'Combo{i}')
        
        print(f"\n[{i}/{len(combinations)}] {combo_name}", flush=True)
        print(f"   Params: {combo}", flush=True)
        
        # Ejecutar con print_signals=True para generar logs
        params_override = {
            **combo,
            'print_signals': True,  # ⚠️ CRÍTICO: Genera logs detallados
        }
        
        try:
            result = run_single_backtest(
                instrument=instrument,
                params_override=params_override,
                fromdate=fromdate,
                todate=todate,
            )
            result['params'] = combo
            result['name'] = combo_name
            results.append(result)
            
            print(f"   → Trades: {result['trades']} | PF: {result['profit_factor']:.2f} | "
                  f"PnL: ${result['total_pnl']:,.0f} | DD: {result['max_drawdown']:.1f}%", flush=True)
            print(f"   → Años negativos: {result['negative_years']}", flush=True)
            
        except Exception as e:
            print(f"   → ERROR: {e}", flush=True)
        
        # Restaurar name para próxima iteración
        combo['name'] = combo_name
    
    # Resumen
    print(f"\n{'='*70}", flush=True)
    print("RESUMEN FASE 5 - COMBINACIONES FINALES", flush=True)
    print(f"{'='*70}", flush=True)
    
    for r in results:
        print(f"\n{r['name']}:", flush=True)
        print(f"   PF: {r['profit_factor']:.2f} | PnL: ${r['total_pnl']:,.0f} | DD: {r['max_drawdown']:.1f}%", flush=True)
        print(f"   Trades: {r['trades']} | WR: {r['win_rate']:.1f}% | Años -: {r['negative_years']}", flush=True)
    
    print(f"\n{'='*70}", flush=True)
    print("PRÓXIMO PASO: ANÁLISIS DE LOGS", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"\nRevisa los archivos en temp_reports/ para analizar:", flush=True)
    print(f"  1. Horas de trades ganadores vs perdedores", flush=True)
    print(f"  2. ATR en momento de entrada", flush=True)
    print(f"  3. Patrones de velas (entry_atr_increment)", flush=True)
    print(f"  4. Usar esta info para aplicar filtros adicionales", flush=True)
    
    return results


def main():
    # Parse arguments
    if len(sys.argv) < 3:
        print_usage()
        return
    
    instrument = sys.argv[1].upper()
    phase = sys.argv[2].lower()
    
    # Validate instrument
    if instrument not in INSTRUMENT_DATA:
        print(f"❌ Unknown instrument: {instrument}")
        print(f"   Available: {list(INSTRUMENT_DATA.keys())}")
        return
    
    # Configure dates
    fromdate = '2020-01-01'
    todate = '2025-12-01'
    min_trades = 30
    
    # Quick mode
    if phase == 'quick':
        fromdate = '2024-01-01'
        todate = '2025-01-01'
        min_trades = 10
        phase = '3'  # Phase 3 (EMAs) by default in quick
    
    print("=" * 70, flush=True)
    print(f"OGLE OPTIMIZER UNIVERSAL - {instrument}", flush=True)
    print("=" * 70, flush=True)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"Data range: {fromdate} to {todate}", flush=True)
    print(f"Commission: $2.50/lot/order (Darwinex Zero)", flush=True)
    
    # Phase 5 special: Final combinations with logs
    if phase == '5':
        results = run_phase5_combinations(instrument, fromdate, todate)
        if results:
            save_results(instrument, '5_combinations', results, fromdate, todate)
        return
    
    # Define optimization phases (1-4)
    # Use JPY-specific ATR grid for JPY pairs
    is_jpy_pair = 'JPY' in instrument
    phase4_grid = PHASE4_GRID_JPY if is_jpy_pair else PHASE4_GRID
    
    phases = {
        '1': ('Phase 1: SL/TP Multipliers', PHASE1_GRID, False),
        '2': ('Phase 2: Entry Window + Pullback', PHASE2_GRID, False),
        '3': ('Phase 3: EMAs', PHASE3_GRID, False),
        '4': ('Phase 4: ATR Filter', phase4_grid, False),
        # NEW PHASES (from BestPnL baseline)
        '6': ('Phase 6: Entry Window Extended (BestPnL baseline)', PHASE6_GRID, True),
        '7': ('Phase 7: ATR Increment Filter (BestPnL baseline)', PHASE7_GRID, True),
        '7b': ('Phase 7b: ATR Decrement Filter (BestPnL baseline)', PHASE7B_GRID, True),
        # PHASE 8: Based on LOG ANALYSIS
        '8': ('Phase 8: Angle Filter (avoid 60-80°)', PHASE8_GRID, True),
        '8b': ('Phase 8b: Hour Filter (best hours 0-3,7-8,21-23)', PHASE8B_GRID, True),
        '8c': ('Phase 8c: Refined ATR (0.00020-0.00035)', PHASE8C_GRID, True),
        # USDCAD SPECIFIC PHASES (Dec 22, 2025)
        '6a': ('Phase 6A: USDCAD Angle Filter (55-75 range)', USDCAD_PHASE6A_ANGLE, False),
        '6b': ('Phase 6B: USDCAD Hour Filter (range)', USDCAD_PHASE6B_HOURS, False),
        '6c': ('Phase 6C: USDCAD ATR Refinement', USDCAD_PHASE6C_ATR, False),
    }
    
    # Execute selected phases
    if phase == 'all':
        phases_to_run = ['1', '2', '3', '4']  # Does NOT include 5 (is manual)
    elif phase in phases:
        phases_to_run = [phase]
    else:
        print(f"❌ Unknown phase: {phase}")
        print(f"   Available: 1, 2, 3, 4, 5, 6, 7, 7b, 8, 8b, 8c, all, quick")
        return
    
    for phase_num in phases_to_run:
        phase_name, param_grid, use_bestpnl = phases[phase_num]
        
        results = run_optimization(
            instrument=instrument,
            param_grid=param_grid,
            phase_name=phase_name,
            fromdate=fromdate,
            todate=todate,
            min_trades=min_trades,
            use_bestpnl_baseline=use_bestpnl,
        )
        
        if results:
            save_results(instrument, phase_num, results, fromdate, todate)
    
    print(f"\n{'='*70}", flush=True)
    print("OPTIMIZATION COMPLETED", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"\nNEXT STEPS:", flush=True)
    print(f"  1. Review generated JSON files", flush=True)
    print(f"  2. Run Phase 5 to generate LOGS: python {Path(__file__).name} {instrument} 5", flush=True)
    print(f"  3. Analyze LOGS for refinement (hours, ATR, candles)", flush=True)
    print(f"  4. Run Phases 6-7 from BestPnL baseline if needed", flush=True)
    print(f"  5. Copy final values to sunrise_ogle_{instrument.lower()}_pro.py", flush=True)


if __name__ == "__main__":
    main()
