"""Carga de los CSV procesados para el dashboard.

Responsabilidad única: leer data/processed/*.csv a DataFrames listos para
graficar. No depende de Streamlit ni sabe nada de gráficas.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def _load_csv(processed_dir: str | Path, filename: str, date_column: str = "date") -> pd.DataFrame:
    path = Path(processed_dir) / filename
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path)
    if date_column in df.columns and not df.empty:
        df[date_column] = pd.to_datetime(df[date_column])
    return df


def load_physical_metrics(processed_dir: str | Path) -> pd.DataFrame:
    return _load_csv(processed_dir, "physical_metrics.csv")


def load_daily_activity(processed_dir: str | Path) -> pd.DataFrame:
    return _load_csv(processed_dir, "daily_activity.csv")


def load_training_sessions(processed_dir: str | Path) -> pd.DataFrame:
    return _load_csv(processed_dir, "training_sessions.csv")
