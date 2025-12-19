# OPTIMIZATION GUIDE - Quant Bot Project
=========================================

## AXIOMAS DE DESARROLLO

### 1. SOLO CARACTERES ASCII EN CODIGO
**PROHIBIDO** usar emojis, iconos o caracteres unicode en archivos .py
- Causa errores de encoding en Windows (cp1252)
- Ejemplo: NO usar checkmarks, cruces, flechas unicode
- Usar texto plano: "OK", "ERROR", "->", etc.

### 2. NO MODIFICAR ESTRATEGIA BASE OGLE
Los filtros custom (horas, ATR change, etc.) van en el optimizador, NO en la estrategia.
La estrategia `sunrise_ogle_template.py` debe permanecer intacta.

### 3. VALIDAR CON SPLIT TEST ANTES DE IMPLEMENTAR
Todo filtro nuevo debe pasar Split Test (training vs validation).
Si mejora training pero empeora validation = OVERFITTING = DESCARTAR.

---

## Overview

Este documento estandariza el proceso de optimizacion para todas las estrategias.
**NO CREAR NUEVOS OPTIMIZADORES** - usar los universales existentes.

## Optimizadores Disponibles

| Estrategia | Archivo | Comando |
|------------|---------|---------|
| OGLE | `ogle_optimizer.py` | `python ogle_optimizer.py EURUSD` |
| KOI | `koi_optimizer.py` | `python koi_optimizer.py USDCHF` |

## Uso Rápido

### OGLE Strategy
```powershell
cd c:\Iván\Yosoybuendesarrollador\Python\Portafolio\quant_bot_project\src\strategies

# Optimización completa (5 años)
python ogle_optimizer.py EURUSD --phase 1    # SL/TP
python ogle_optimizer.py EURUSD --phase 2    # Entry Window
python ogle_optimizer.py EURUSD --phase 3    # EMAs
python ogle_optimizer.py EURUSD --phase 4    # ATR Filter
python ogle_optimizer.py EURUSD --phase 5    # Time Filter

# Todas las fases
python ogle_optimizer.py EURUSD --all

# Test rápido (1 año)
python ogle_optimizer.py EURUSD --quick
```

### KOI Strategy
```powershell
# Optimización completa (5 años)
python koi_optimizer.py USDCHF --phase 1     # SL/TP
python koi_optimizer.py USDCHF --phase 2     # CCI
python koi_optimizer.py USDCHF --phase 3     # EMAs
python koi_optimizer.py USDCHF --phase 4     # Breakout
python koi_optimizer.py USDCHF --phase 5     # SL Range Filter

# Todas las fases
python koi_optimizer.py USDCHF --all

# Test rápido (1 año)
python koi_optimizer.py USDCHF --quick
```

## Instrumentos Soportados

| Instrumento | OGLE | KOI | Data File |
|-------------|------|-----|-----------|
| EURUSD | ✅ | ✅ | `EURUSD_5m_5Yea.csv` |
| USDCHF | ✅ | ✅ | `USDCHF_5m_5Yea.csv` |
| USDJPY | ✅ | ✅ | `USDJPY_5m_5Yea.csv` |
| GBPUSD | ✅ | ✅ | `GBPUSD_5m_5Yea.csv` |
| AUDUSD | ✅ | ❌ | `AUDUSD_5m_5Yea.csv` |

## Fases de Optimización

### OGLE Phases
1. **Phase 1: SL/TP** - Risk:Reward ratio (1.5-3.0 SL, 8-15 TP)
2. **Phase 2: Entry Window** - Pullback candles + window periods
3. **Phase 3: EMAs** - Fast EMA + Filter EMA
4. **Phase 4: ATR Filter** - Min/Max ATR threshold
5. **Phase 5: Time Filter** - Trading hours (UTC)

### KOI Phases
1. **Phase 1: SL/TP** - Risk:Reward ratio
2. **Phase 2: CCI** - Period + Threshold
3. **Phase 3: EMAs** - 5 EMA periods
4. **Phase 4: Breakout** - Offset pips + candles
5. **Phase 5: SL Range** - Min/Max SL pips filter

## Errores Conocidos y Soluciones

### ❌ Error: `'DataFrame' object has no attribute 'upper'`
**Causa**: Usar `PandasData` en lugar de `GenericCSVData`
**Solución**: Los optimizadores ya usan `GenericCSVData`. NO CAMBIAR.

### ❌ Error: 0 trades con `use_forex_position_calc=False`
**Causa**: Position sizing breaks cuando forex_calc está desactivado
**Solución**: Mantener `use_forex_position_calc=True` (default en optimizadores)

### ❌ Error: Backtest muy lento
**Causa**: `print_signals=True` o `verbose_debug=True`
**Solución**: Los optimizadores fuerzan estos a `False` automáticamente

### ❌ Error: Out of memory
**Causa**: Demasiadas combinaciones o datos muy largos
**Solución**: 
- Usar `--quick` para tests iniciales
- Reducir el grid de parámetros
- Procesar por fases (no `--all`)

### ❌ Error: "time data '20200101' does not match format '%Y-%m-%d'"
**Causa**: Formato de fecha incorrecto para los datos CSV
**Solución CRÍTICA**: Usar el formato correcto:
```python
# Los CSV tienen fecha en formato YYYYMMDD (sin guiones)
dtformat='%Y%m%d'    # ✅ CORRECTO
tmformat='%H:%M:%S'  # Hora con dos puntos

# ❌ INCORRECTO:
dtformat='%Y-%m-%d'  # NO - los CSV no tienen guiones
```

### ❌ Error: ImportError ForexCommission
**Causa**: La clase ForexCommission está en `sunrise_ogle_template.py`
**Solución**: 
```python
from sunrise_ogle_template import ForexCommission
```

## Modificar Grids de Parámetros

Para cambiar los rangos de búsqueda, editar las constantes `PHASE*_GRID` en cada optimizador:

```python
# ogle_optimizer.py - Phase 1 example
PHASE1_GRID = {
    'long_atr_sl_multiplier': [1.5, 2.0, 2.5, 3.0],  # Agregar/quitar valores aquí
    'long_atr_tp_multiplier': [8.0, 10.0, 12.0, 15.0],
}
```

## Output

Cada optimización genera:
1. **Console**: Progreso + TOP 10 resultados
2. **JSON**: `{strategy}_optimization_{instrument}.json`

Ejemplo de output JSON:
```json
{
  "instrument": "EURUSD",
  "timestamp": "2025-12-16T10:30:00",
  "phases": {
    "phase_1": {
      "name": "Phase 1: SL/TP Multipliers",
      "top_results": [
        {
          "params": {"long_atr_sl_multiplier": 2.0, "long_atr_tp_multiplier": 10.0},
          "trades": 125,
          "profit_factor": 1.85,
          "win_rate": 42.5,
          "total_pnl": 15000.0,
          "max_drawdown": 8.5
        }
      ]
    }
  }
}
```

## Workflow Recomendado

1. **Test rápido** con `--quick` para verificar que funciona
2. **Phase 1** (SL/TP) - Establece el risk:reward base
3. **Phase 2** (Entry) - Ajusta timing de entrada
4. **Phase 3** (EMAs) - Calibra detección de tendencia
5. **Phase 4** (Filters) - Añade filtros de calidad
6. **Validación** - Ejecutar estrategia con mejores params en datos completos

---

## OGLE EURUSD - Resultados Optimizacion Completa (Diciembre 2025)

### RESUMEN DE TODAS LAS FASES

| Fase | Parametro | Valor Optimo | Trades | PF | PnL |
|------|-----------|--------------|--------|-----|-----|
| 1 | SL/TP | 3.0x / 15.0x | 690 | 0.96 | -$8,768 |
| 3 | EMAs | 24/24/24, Filter 60 | 500 | 1.09 | +$15,932 |
| 4 | ATR Min/Max | 0.00015/0.0005 | 376 | 1.16 | +$22,434 |
| 6 | Window | 1 periodo | 376 | 1.16 | +$22,434 |
| 7 | ATR Increment | 0.00005-0.00015 | 270 | 1.26 | +$25,659 |
| 8 | Angulo | 0-85 grados | 354 | 1.20 | +$26,765 |

### PHASE 9: ANALISIS DE LOGS (21/12/2025)

#### Analisis de Horas (NO IMPLEMENTADO - solo documentacion)

| Hora UTC | Trades | Win | Loss | PF | PnL |
|----------|--------|-----|------|-----|-----|
| 00 | 21 | 7 | 14 | 2.19 | +$7,298 |
| 01 | 22 | 5 | 17 | 1.87 | +$5,453 |
| 02 | 23 | 6 | 17 | 2.04 | +$7,046 |
| 03 | 18 | 3 | 15 | 1.54 | +$2,892 |
| 07 | 18 | 6 | 12 | 2.04 | +$7,066 |
| 11 | 10 | 3 | 7 | 1.69 | +$2,651 |
| 19 | 18 | 7 | 11 | 2.78 | +$11,679 |
| 22 | 21 | 5 | 16 | 1.67 | +$4,457 |
| 23 | 19 | 5 | 14 | 1.84 | +$4,862 |

**HORAS A EVITAR** (PF < 0.8):
| Hora | PF | PnL |
|------|-----|-----|
| 06 | 0.33 | -$5,266 |
| 09 | 0.56 | -$5,188 |
| 10 | 0.51 | -$8,124 |
| 12 | 0.61 | -$5,282 |
| 13 | 0.69 | -$3,430 |
| 17 | 0.72 | -$3,103 |
| 18 | 0.71 | -$3,180 |
| 20 | 0.76 | -$2,564 |

#### Analisis ATR Change (NO IMPLEMENTADO - solo documentacion)

| Categoria | Rango ATR Change | Trades | PF | PnL |
|-----------|------------------|--------|-----|-----|
| Decrement Fuerte | -0.0001 a -0.00005 | 29 | 3.71 | +$29,006 |
| Increment Fuerte | +0.00005 a +0.0001 | 31 | 2.34 | +$28,946 |
| Increment Medio | +0.00003 a +0.00005 | 36 | 1.61 | +$11,127 |
| Neutro | -0.00002 a +0.00002 | 113 | 1.08 | +$5,451 |
| Decrement Leve | -0.00002 a 0 | 54 | 0.93 | -$9,235 |

**NOTA**: Estos filtros NO se implementan en codigo.
Son datos de referencia para analisis manual.

### CONFIGURACION OPTIMA APLICADA EURUSD

```python
# === PARAMETROS OPTIMOS COMPILADOS ===
# Phase 3: EMAs
EMA_FAST_LENGTH = 24
EMA_MEDIUM_LENGTH = 24
EMA_SLOW_LENGTH = 24
EMA_FILTER_PRICE_LENGTH = 60

# Phase 1: SL/TP (baseline)
LONG_ATR_SL_MULTIPLIER = 3.0
LONG_ATR_TP_MULTIPLIER = 15.0

# Phase 4: ATR Filter (BestPnL - mas trades)
LONG_USE_ATR_FILTER = True
LONG_ATR_MIN_THRESHOLD = 0.000150  # BestPnL: mas permisivo
LONG_ATR_MAX_THRESHOLD = 0.000500

# Phase 6: Entry Window
LONG_ENTRY_WINDOW_PERIODS = 1      # OPTIMO

# Phase 7: ATR Increment - DESHABILITADO
LONG_USE_ATR_INCREMENT_FILTER = False  # Reduce trades sin mejorar validacion

# Phase 8: Angle Filter - DESHABILITADO (Split Test)
LONG_USE_ANGLE_FILTER = False      # Mejora training pero EMPEORA validation
```

### FILTRO DE ANGULO - DESCARTADO (Split Test 19/12/2025)

| Config | Training PF | Training PnL | Validation PF | Validation PnL |
|--------|-------------|--------------|---------------|----------------|
| CON Angulo 0-85 | 1.28 | +$24,652 | 1.03 | +$1,106 |
| SIN Angulo | 1.21 | +$19,736 | 1.08 | +$3,101 |

**CONCLUSION**: Angulo mejora training pero PERJUDICA validation.
El filtro de angulo causa OVERFITTING - NO USAR.

### Phase 7: ATR Increment - ANALISIS

| Rank | Increment Range | Trades | PF | PnL | Neg Years |
|------|-----------------|--------|-----|-----|-----------|
| 1 | 0.00005-0.00015 | 270 | 1.26 | +$25,659 | 3 |
| 2 | 0.00005-0.00010 | 268 | 1.25 | +$24,205 | 3 |
| 3 | 0.00003-0.00010 | 291 | 1.24 | +$25,407 | 2 |

**NOTA**: Mejora PF pero reduce trades. Evaluar en Split Test.

### FILTRO DE HORAS - PENDIENTE VALIDACION

De analisis de logs:
- Mejores horas: 0-3, 7-8, 19, 21-23 UTC (PF > 1.5)
- Evitar: 6, 9, 10, 12, 13, 17, 18, 20 UTC (PF < 0.8)

**IMPORTANTE**: Ejecutar Phase 5 (Time Filter) para validar.

### PROCESO DE OPTIMIZACION PASO A PASO

```powershell
# 1. Ejecutar cada fase secuencialmente
cd c:\Ivan\...\quant_bot_project\src\strategies

python ogle_optimizer_universal.py EURUSD --phase 1  # SL/TP
python ogle_optimizer_universal.py EURUSD --phase 3  # EMAs  
python ogle_optimizer_universal.py EURUSD --phase 4  # ATR Filter
python ogle_optimizer_universal.py EURUSD --phase 6  # Window
python ogle_optimizer_universal.py EURUSD --phase 7  # ATR Increment
python ogle_optimizer_universal.py EURUSD --phase 8  # Angle

# 2. Split Test del hibrido
python backtest_hybrid_eurusd.py --split

# 3. Habilitar logs para analisis
# En sunrise_ogle_eurusd_pro.py:
EXPORT_TRADE_REPORTS = True
TRADE_REPORT_ENABLED = True

# 4. Ejecutar backtest completo
python sunrise_ogle_eurusd_pro.py
```

### ANALISIS DE LOGS (Fine Tuning)

Los logs generan archivos en `temp_reports/EURUSD_trades_*.txt`:
- ATR Current: ATR en momento de entrada
- ATR Increment: Cambio de ATR desde senal a entrada
- Angle Current: Angulo EMA en momento de entrada
- Bars to Entry: Barras desde senal hasta entrada

Metricas a analizar:
1. Distribucion de ATR en trades ganadores vs perdedores
2. Horas con mejor/peor PF
3. Dias de semana optimos
4. Patrones de duracion de trades

### RESULTADOS BACKTEST COMPLETO (19/12/2025)

Configuracion Optima Aplicada:
```
EMAs: 24/24/24, Filter: 60
SL: 3.0x ATR, TP: 15.0x ATR
ATR Filter: 0.00015-0.0005 (ENABLED)
Window: 1
Angle Filter: DISABLED
```

Resultados:
| Metrica | Valor |
|---------|-------|
| Trades | 321 |
| Win Rate | 25.55% |
| PF | 1.24 |
| Total PnL | +$89,620 |
| Max DD | 21.15% |
| Avg Win | +$5,587 |
| Avg Loss | -$1,548 |
| Sharpe | 0.829 |

Analisis de Logs - Primeros Hallazgos:
- La mayoria de entradas tienen Bars to Entry: 1 (optimo)
- ATR en rango 0.00020-0.00050 consistente
- Angulos variados (30-82 grados) todos funcionan sin filtro
- Perdidas tipicas: ~$950-1000 (SL bien calibrado)
- Ganancias tipicas: $2,000-7,000 (TP efectivo)

### PROXIMOS PASOS PARA MEJORAR PF

Para alcanzar PF >= 1.5:

1. Phase 5: Time Filter - Ejecutar optimizacion de horas
   ```powershell
   python ogle_optimizer_universal.py EURUSD --phase 5
   ```

2. ATR Increment Filter - Re-evaluar con split test
   - Phase 7 mostro PF 1.26 con 270 trades
   - Necesita validacion out-of-sample

3. Ajuste SL/TP - Explorar ratios alternativos
   - SL 2.5x/TP 15x (mas trades, menor win rate)
   - SL 3.5x/TP 18x (menos trades, mayor win rate)

4. Combinar filtros selectivamente
   - Hour filter + ATR filter sin angle
   - Verificar que no "ahogue" entradas

---

## Archivos a NO Modificar

Los optimizadores importan de los templates. **NO MODIFICAR** durante optimización:
- `sunrise_ogle_template.py` - Template OGLE
- `koi_template.py` - Template KOI

## Archivos Deprecados (Borrar)

Los siguientes archivos son versiones antiguas y deben borrarse:
- `eris_optimizer.py`
- `eris_optimizer_v2.py`
- `ogle_optimizer_v2.py`
- `koi_full_optimizer.py`
- `koi_balanced_search.py`
- `koi_robustness_test.py`
- `ogle_robustness_tests.py`
- `optimize_ogle_eurusd.py`

## Contacto

Para dudas sobre optimización, revisar este documento primero.
Autor: Iván López | Fecha: Diciembre 2025
