"""Dashboard interactivo de Polar Flow Analyzer.

Lee los CSVs procesados en data/processed/ y los visualiza con Streamlit.

Uso:
    streamlit run dashboard.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.application.goal_progress import evaluate_goal_progress
from src.config import get_settings
from src.dashboard import charts, data_loader
from src.domain.models import GoalDirection, ProgressSnapshot

st.set_page_config(page_title="Polar Flow Analyzer", layout="wide")


@st.cache_data
def _load_physical(processed_dir: str) -> pd.DataFrame:
    return data_loader.load_physical_metrics(processed_dir)


@st.cache_data
def _load_activity(processed_dir: str) -> pd.DataFrame:
    return data_loader.load_daily_activity(processed_dir)


@st.cache_data
def _load_training(processed_dir: str) -> pd.DataFrame:
    return data_loader.load_training_sessions(processed_dir)


def render_physical_tab(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("Sin datos físicos todavía. Ejecuta `python main.py` para sincronizar.")
        return
    col1, col2 = st.columns(2)
    col1.plotly_chart(charts.physical_overview_figure(df), use_container_width=True)
    col2.plotly_chart(charts.resting_heart_rate_figure(df), use_container_width=True)


def render_activity_tab(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("Sin datos de actividad todavía. Ejecuta `python main.py` para sincronizar.")
        return
    col1, col2 = st.columns(2)
    col1.plotly_chart(charts.steps_figure(df), use_container_width=True)
    col2.plotly_chart(charts.calories_breakdown_figure(df), use_container_width=True)
    col1.plotly_chart(charts.active_time_figure(df), use_container_width=True)
    col2.plotly_chart(charts.sleep_figure(df), use_container_width=True)


def render_training_tab(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("Sin entrenamientos todavía. Ejecuta `python main.py` para sincronizar.")
        return

    sports = sorted(df["sport"].dropna().unique())
    selected_sports = st.multiselect("Deporte", sports, default=sports)
    filtered = df[df["sport"].isin(selected_sports)] if selected_sports else df

    col1, col2 = st.columns(2)
    col1.plotly_chart(charts.weekly_distance_figure(filtered), use_container_width=True)
    col2.plotly_chart(charts.sport_distribution_figure(df), use_container_width=True)
    col1.plotly_chart(charts.training_load_figure(filtered), use_container_width=True)
    col2.plotly_chart(charts.pace_trend_figure(filtered), use_container_width=True)


def render_goals_tab(snapshots: dict[str, ProgressSnapshot]) -> None:
    if not snapshots:
        st.info(
            "Sin objetivos configurados. Define TARGET_WEIGHT_KG, TARGET_WEEKLY_KM, "
            "TARGET_SLEEP_HOURS o TARGET_DAILY_STEPS en tu `.env` para activar esta pestaña."
        )
        return

    cols = st.columns(len(snapshots))
    for col, snapshot in zip(cols, snapshots.values()):
        goal = snapshot.goal
        label = {
            "weight": "Peso",
            "weekly_distance": "Km esta semana",
            "sleep": "Sueño (media 7d)",
            "steps": "Pasos (media 7d)",
        }.get(goal.name, goal.name)

        if snapshot.current is None:
            col.metric(label, "sin datos")
            continue

        delta = snapshot.delta
        # En AT_MOST (peso) bajar es bueno -> delta negativo se muestra normal,
        # en AT_LEAST subir es bueno -> invertir el color sería confuso, así
        # que se deja el signo natural y se confía en la flecha de Streamlit.
        delta_color = "inverse" if goal.direction is GoalDirection.AT_MOST else "normal"
        col.metric(
            label,
            f"{snapshot.current:.1f} {goal.unit}",
            delta=f"{delta:+.1f} {goal.unit} vs objetivo" if delta is not None else None,
            delta_color=delta_color,
        )
        ratio = snapshot.progress_ratio
        if ratio is not None:
            col.progress(min(max(ratio, 0.0), 1.0))
        status = "En objetivo" if snapshot.on_track else "Fuera de objetivo"
        col.caption(f"Objetivo: {goal.target:.1f} {goal.unit} · {status}")


def main() -> None:
    settings = get_settings()
    st.title("Polar Flow Analyzer")

    physical_df = _load_physical(settings.processed_data_dir)
    activity_df = _load_activity(settings.processed_data_dir)
    training_df = _load_training(settings.processed_data_dir)
    goal_snapshots = evaluate_goal_progress(physical_df, activity_df, training_df, settings)

    tab_goals, tab_physical, tab_activity, tab_training = st.tabs(
        ["Objetivos", "Físico", "Actividad", "Entrenamientos"]
    )
    with tab_goals:
        render_goals_tab(goal_snapshots)
    with tab_physical:
        render_physical_tab(physical_df)
    with tab_activity:
        render_activity_tab(activity_df)
    with tab_training:
        render_training_tab(training_df)


main()
