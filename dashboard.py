"""Dashboard interactivo de Polar Flow Analyzer.

Lee los CSVs procesados en data/processed/ y los visualiza con Streamlit.

Uso:
    streamlit run dashboard.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import get_settings
from src.dashboard import charts, data_loader

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


def main() -> None:
    settings = get_settings()
    st.title("Polar Flow Analyzer")

    physical_df = _load_physical(settings.processed_data_dir)
    activity_df = _load_activity(settings.processed_data_dir)
    training_df = _load_training(settings.processed_data_dir)

    tab_physical, tab_activity, tab_training = st.tabs(["Físico", "Actividad", "Entrenamientos"])
    with tab_physical:
        render_physical_tab(physical_df)
    with tab_activity:
        render_activity_tab(activity_df)
    with tab_training:
        render_training_tab(training_df)


main()
