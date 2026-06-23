"""Construcción de gráficas Plotly a partir de los DataFrames procesados.

Responsabilidad única: cada función recibe un DataFrame y devuelve una
figura. No conocen Streamlit ni el origen de los datos (eso vive en
dashboard.py / data_loader.py), lo que las hace testables de forma aislada.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def _empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font={"size": 16})
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


def physical_overview_figure(df: pd.DataFrame) -> go.Figure:
    """Peso (eje izquierdo) e IMC (eje derecho) a lo largo del tiempo."""
    if df.empty or "weight_kg" not in df or df["weight_kg"].dropna().empty:
        return _empty_figure("Sin datos de peso")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["weight_kg"], name="Peso (kg)", mode="lines+markers"))
    if "bmi" in df and not df["bmi"].dropna().empty:
        fig.add_trace(go.Scatter(x=df["date"], y=df["bmi"], name="IMC", mode="lines+markers", yaxis="y2"))
    fig.update_layout(
        title="Peso e IMC",
        yaxis={"title": "Peso (kg)"},
        yaxis2={"title": "IMC", "overlaying": "y", "side": "right"},
        legend={"orientation": "h"},
    )
    return fig


def resting_heart_rate_figure(df: pd.DataFrame) -> go.Figure:
    if df.empty or "resting_heart_rate" not in df or df["resting_heart_rate"].dropna().empty:
        return _empty_figure("Sin datos de FC en reposo")
    return px.line(df, x="date", y="resting_heart_rate", markers=True, title="Frecuencia cardíaca en reposo")


def steps_figure(df: pd.DataFrame) -> go.Figure:
    if df.empty or "steps" not in df or df["steps"].dropna().empty:
        return _empty_figure("Sin datos de pasos")
    return px.bar(df, x="date", y="steps", title="Pasos diarios")


def calories_breakdown_figure(df: pd.DataFrame) -> go.Figure:
    if df.empty or "calories_active" not in df or df["calories_active"].dropna().empty:
        return _empty_figure("Sin datos de calorías")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["date"], y=df["calories_basal_estimated"], name="Basales (estimadas)"))
    fig.add_trace(go.Bar(x=df["date"], y=df["calories_active"], name="Activas"))
    fig.update_layout(barmode="stack", title="Calorías: activas vs. basales")
    return fig


def active_time_figure(df: pd.DataFrame) -> go.Figure:
    if df.empty or "active_time_min" not in df or df["active_time_min"].dropna().empty:
        return _empty_figure("Sin datos de tiempo activo")
    return px.line(df, x="date", y="active_time_min", markers=True, title="Tiempo activo diario (min)")


def sleep_figure(df: pd.DataFrame) -> go.Figure:
    if df.empty or "sleep_minutes" not in df or df["sleep_minutes"].dropna().empty:
        return _empty_figure("Sin datos de sueño (scope no habilitado o dispositivo no compatible)")
    return px.bar(df, x="date", y="sleep_minutes", title="Minutos de sueño")


def weekly_distance_figure(df: pd.DataFrame) -> go.Figure:
    if df.empty or "distance_km" not in df or df["distance_km"].dropna().empty:
        return _empty_figure("Sin datos de distancia")
    weekly = (
        df.dropna(subset=["distance_km"])
        .set_index("date")
        .resample("W")["distance_km"]
        .sum()
        .reset_index()
    )
    return px.bar(weekly, x="date", y="distance_km", title="Km acumulados por semana")


def sport_distribution_figure(df: pd.DataFrame) -> go.Figure:
    if df.empty or "sport" not in df or df["sport"].dropna().empty:
        return _empty_figure("Sin entrenamientos")
    counts = df["sport"].value_counts().reset_index()
    counts.columns = ["sport", "sessions"]
    return px.pie(counts, names="sport", values="sessions", title="Distribución de sesiones por deporte")


def training_load_figure(df: pd.DataFrame) -> go.Figure:
    if df.empty or "training_load" not in df or df["training_load"].dropna().empty:
        return _empty_figure("Sin datos de carga de entrenamiento")
    return px.line(df, x="date", y="training_load", markers=True, title="Carga de entrenamiento (TRIMP)")


def pace_trend_figure(df: pd.DataFrame) -> go.Figure:
    if df.empty or "pace_min_per_km" not in df or df["pace_min_per_km"].dropna().empty:
        return _empty_figure("Sin datos de ritmo")
    fig = px.line(df, x="date", y="pace_min_per_km", color="sport", markers=True, title="Ritmo (min/km)")
    fig.update_yaxes(autorange="reversed")  # menor ritmo = mejor rendimiento
    return fig
