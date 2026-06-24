"""Caso de uso: evaluar progreso hacia los objetivos configurados por el usuario.

Traduce DataFrames procesados (peso, actividad, entrenamientos) + Settings en
ProgressSnapshot de dominio. No conoce Streamlit; el dashboard solo renderiza
lo que esta función devuelve.
"""

from __future__ import annotations

import pandas as pd

from src.config import Settings
from src.domain.models import Goal, GoalDirection, ProgressSnapshot


def _latest_value(df: pd.DataFrame, column: str) -> float | None:
    if df.empty or column not in df or df[column].dropna().empty:
        return None
    return float(df.sort_values("date")[column].dropna().iloc[-1])


def _first_value(df: pd.DataFrame, column: str) -> float | None:
    if df.empty or column not in df or df[column].dropna().empty:
        return None
    return float(df.sort_values("date")[column].dropna().iloc[0])


def _last_n_days_mean(df: pd.DataFrame, column: str, days: int = 7) -> float | None:
    if df.empty or column not in df or "date" not in df:
        return None
    cutoff = df["date"].max() - pd.Timedelta(days=days - 1)
    window = df.loc[df["date"] >= cutoff, column].dropna()
    return float(window.mean()) if not window.empty else None


def _last_week_distance_km(training_df: pd.DataFrame) -> float | None:
    if training_df.empty or "distance_km" not in training_df or "date" not in training_df:
        return None
    cutoff = training_df["date"].max() - pd.Timedelta(days=6)
    window = training_df.loc[training_df["date"] >= cutoff, "distance_km"].dropna()
    return float(window.sum()) if not window.empty else None


def evaluate_goal_progress(
    physical_df: pd.DataFrame,
    activity_df: pd.DataFrame,
    training_df: pd.DataFrame,
    settings: Settings,
) -> dict[str, ProgressSnapshot]:
    """Compara las métricas más recientes contra cada objetivo configurado.

    Un objetivo sin valor en Settings (target_* es None) no aparece en el
    resultado: ausencia de objetivo no es lo mismo que "fuera de objetivo".
    """
    snapshots: dict[str, ProgressSnapshot] = {}

    if settings.target_weight_kg is not None:
        goal = Goal(
            name="weight",
            target=settings.target_weight_kg,
            direction=GoalDirection.AT_MOST,
            unit="kg",
            baseline=_first_value(physical_df, "weight_kg"),
        )
        snapshots["weight"] = ProgressSnapshot(goal, _latest_value(physical_df, "weight_kg"))

    if settings.target_weekly_km is not None:
        goal = Goal(
            name="weekly_distance",
            target=settings.target_weekly_km,
            direction=GoalDirection.AT_LEAST,
            unit="km",
        )
        snapshots["weekly_distance"] = ProgressSnapshot(goal, _last_week_distance_km(training_df))

    if settings.target_sleep_hours is not None:
        goal = Goal(
            name="sleep",
            target=settings.target_sleep_hours,
            direction=GoalDirection.AT_LEAST,
            unit="h",
        )
        avg_minutes = _last_n_days_mean(activity_df, "sleep_minutes")
        current_hours = avg_minutes / 60 if avg_minutes is not None else None
        snapshots["sleep"] = ProgressSnapshot(goal, current_hours)

    if settings.target_daily_steps is not None:
        goal = Goal(
            name="steps",
            target=settings.target_daily_steps,
            direction=GoalDirection.AT_LEAST,
            unit="steps",
        )
        snapshots["steps"] = ProgressSnapshot(goal, _last_n_days_mean(activity_df, "steps"))

    return snapshots
