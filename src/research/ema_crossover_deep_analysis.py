"""Deep Research Analysis for Triemahl2 Research Strategy

Steps implemented:
1. Load trade-level dataset (ema_crossover_analysis.csv)
2. Load underlying OHLC data (GBPUSD_5m_8Yea.csv) and compute ATR(14)
3. Merge ATR at entry timestamps into trade dataset
4. Engineer additional features (normalized pre EMA diff, ATR regime)
5. Segment performance by ATR regime (low/mid/high terciles)
6. Train time-ordered logistic regression to predict Result_Binary using only pre-entry features + ATR
7. Output model metrics (accuracy, ROC AUC, confusion matrix, coefficients standardized)
8. Save enriched dataset ema_crossover_analysis_enriched.csv

Notes:
- Uses only pre-entry features for prediction to avoid look-ahead bias.
- Post-exit metrics retained but excluded from model feature set.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List

try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, roc_auc_score, confusion_matrix
    from sklearn.preprocessing import StandardScaler
except ImportError as e:  # pragma: no cover
    raise SystemExit("scikit-learn required. Install with: pip install scikit-learn") from e


# Configuration
DATA_FILE = 'GBPUSD_5m_8Yea.csv'
TRADES_FILE = 'ema_crossover_analysis.csv'
ENRICHED_FILE = 'ema_crossover_analysis_enriched.csv'
ATR_PERIOD = 14
PIP_VALUE = 0.0001  # For normalization


def compute_atr(df: pd.DataFrame, period: int) -> pd.Series:
    high = df['high']
    low = df['low']
    close = df['close']
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=period).mean()
    return atr


def load_price_data(project_root: Path) -> pd.DataFrame:
    data_path = project_root / 'data' / DATA_FILE
    if not data_path.exists():
        raise FileNotFoundError(f"Underlying data file not found: {data_path}")
    # Original format per strategy loader: date, time, open, high, low, close, volume
    cols = ['date', 'time', 'open', 'high', 'low', 'close', 'volume']
    df = pd.read_csv(data_path, names=cols, header=0)
    # Parse datetime
    df['Date_Time'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['time'].astype(str), format='%Y%m%d %H:%M:%S')
    df.sort_values('Date_Time', inplace=True)
    df.set_index('Date_Time', inplace=True)
    return df


def enrich_trades_with_atr(trades: pd.DataFrame, price: pd.DataFrame) -> pd.DataFrame:
    price = price.copy()
    price['ATR14'] = compute_atr(price, ATR_PERIOD)
    # Forward fill ATR for robustness
    price['ATR14'].ffill(inplace=True)

    # Merge: trades have Date_Time_Entry as datetime
    trades = trades.copy()
    trades['Date_Time_Entry'] = pd.to_datetime(trades['Date_Time_Entry'])
    trades.set_index('Date_Time_Entry', inplace=True)
    # Align ATR by exact timestamp; if some timestamps missing (rare), reindex using nearest previous bar
    if not trades.index.isin(price.index).all():
        # Reindex price to minute resolution maybe; simpler: merge_asof
        price_reset = price.reset_index().rename(columns={'Date_Time': 'ts'})
        trades_reset = trades.reset_index().rename(columns={'Date_Time_Entry': 'ts'})
        merged = pd.merge_asof(trades_reset.sort_values('ts'), price_reset[['ts', 'ATR14']].sort_values('ts'), on='ts', direction='backward')
        trades = merged.set_index('ts')
    else:
        trades = trades.join(price[['ATR14']], how='left')
    trades.rename_axis('Date_Time_Entry', inplace=True)
    return trades


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Normalized pre EMA max difference by ATR (convert ATR to pips scale first)
    df['PreDiff_Normalized'] = df['Max_Diferencia_EMAs_PreCruce'] / (df['ATR14'] + 1e-9)
    # ATR in pips
    df['ATR14_pips'] = df['ATR14'] / PIP_VALUE
    # ATR regime terciles
    valid_atr = df['ATR14'].dropna()
    if not valid_atr.empty:
        t1, t2 = valid_atr.quantile([1/3, 2/3])
        def regime(a):
            if pd.isna(a):
                return 'NA'
            if a <= t1:
                return 'Low'
            if a <= t2:
                return 'Mid'
            return 'High'
        df['ATR_Regime'] = df['ATR14'].apply(regime)
    else:
        df['ATR_Regime'] = 'NA'
    return df


def segment_performance(df: pd.DataFrame) -> pd.DataFrame:
    seg = df.groupby('ATR_Regime').agg(
        trades=('Pips_Result', 'count'),
        win_rate=('Result_Binary', 'mean'),
        avg_pips=('Pips_Result', 'mean'),
        median_pips=('Pips_Result', 'median'),
        pips_std=('Pips_Result', 'std')
    ).sort_values('avg_pips', ascending=False)
    return seg


def train_logistic(df: pd.DataFrame):
    # Use only rows with all required features
    feature_cols: List[str] = [
        'Max_Diferencia_EMAs_PreCruce',
        'Tasa_Conver_PreCruce',
        'Periodo_Max_Conver_PreCruce',
        'Angulo_Medio_EMA_Slow_PreCruce',
        'ATR14',
        'PreDiff_Normalized'
    ]
    model_df = df.dropna(subset=feature_cols + ['Result_Binary']).copy()
    if model_df.empty:
        raise ValueError("No data available for modeling after dropping NaNs.")
    # Chronological split 70/30
    split_idx = int(len(model_df) * 0.7)
    train = model_df.iloc[:split_idx]
    test = model_df.iloc[split_idx:]
    X_train = train[feature_cols].values
    y_train = train['Result_Binary'].values
    X_test = test[feature_cols].values
    y_test = test['Result_Binary'].values

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    clf = LogisticRegression(max_iter=200, n_jobs=None if hasattr(LogisticRegression, 'n_jobs') else None)
    clf.fit(X_train_s, y_train)
    y_prob = clf.predict_proba(X_test_s)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)

    metrics = {
        'train_size': len(train),
        'test_size': len(test),
        'test_accuracy': accuracy_score(y_test, y_pred),
        'test_roc_auc': roc_auc_score(y_test, y_prob),
        'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
    }
    # Standardized coefficients
    coef = clf.coef_[0]
    coef_df = pd.DataFrame({'feature': feature_cols, 'std_coef': coef}).sort_values('std_coef', key=lambda s: s.abs(), ascending=False)
    return clf, scaler, metrics, coef_df


def main():  # noqa: D401
    project_root = Path(__file__).resolve().parent.parent.parent
    trades_path = project_root / TRADES_FILE
    if not trades_path.exists():
        raise FileNotFoundError(f"Trade dataset not found: {trades_path}")
    trades = pd.read_csv(trades_path)
    price = load_price_data(project_root)
    enriched = enrich_trades_with_atr(trades, price)
    enriched = add_engineered_features(enriched)

    # Segment analysis
    seg = segment_performance(enriched)

    # Train logistic model
    clf, scaler, metrics, coef_df = train_logistic(enriched)

    # Persist enriched dataset
    enriched.reset_index().to_csv(project_root / ENRICHED_FILE, index=False)

    # Output concise report
    print("=== ATR Regime Performance (Pre-Entry Features Only) ===")
    print(seg)
    print("\n=== Logistic Model Metrics ===")
    for k, v in metrics.items():
        print(f"{k}: {v}")
    print("\n=== Standardized Coefficients (Importance) ===")
    print(coef_df)
    print("\nTop Drivers (abs coef):")
    print(coef_df.head(3))


if __name__ == '__main__':  # pragma: no cover
    main()
