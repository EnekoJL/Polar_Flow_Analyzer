import pandas as pd
import plotly.graph_objects as go

from src.dashboard import charts


def test_physical_overview_figure_handles_empty_df():
    fig = charts.physical_overview_figure(pd.DataFrame())
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0  # solo la anotación de "sin datos"


def test_physical_overview_figure_plots_weight_and_bmi():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-06-20", "2026-06-21"]),
            "weight_kg": [72.0, 71.5],
            "bmi": [22.2, 22.0],
        }
    )
    fig = charts.physical_overview_figure(df)
    assert len(fig.data) == 2


def test_steps_figure_handles_empty_df():
    fig = charts.steps_figure(pd.DataFrame())
    assert isinstance(fig, go.Figure)


def test_steps_figure_plots_bars():
    df = pd.DataFrame({"date": pd.to_datetime(["2026-06-20"]), "steps": [8500]})
    fig = charts.steps_figure(df)
    assert len(fig.data) == 1


def test_weekly_distance_figure_aggregates_by_week():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-06-15", "2026-06-16", "2026-06-22"]),
            "distance_km": [5.0, 3.0, 10.0],
        }
    )
    fig = charts.weekly_distance_figure(df)
    assert len(fig.data) == 1
    assert fig.data[0].y.sum() == 18.0


def test_sport_distribution_figure_counts_sessions_per_sport():
    df = pd.DataFrame({"sport": ["RUNNING", "RUNNING", "CYCLING"]})
    fig = charts.sport_distribution_figure(df)
    assert isinstance(fig, go.Figure)
    assert set(fig.data[0].labels) == {"RUNNING", "CYCLING"}


def test_pace_trend_figure_handles_missing_column():
    fig = charts.pace_trend_figure(pd.DataFrame({"date": pd.to_datetime(["2026-06-20"])}))
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0
