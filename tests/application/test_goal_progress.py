import pandas as pd

from src.application.goal_progress import evaluate_goal_progress
from src.config import Settings


def _settings(**overrides) -> Settings:
    base = dict(
        polar_client_id="id",
        polar_client_secret="secret",
        target_weight_kg=None,
        target_weekly_km=None,
        target_sleep_hours=None,
        target_daily_steps=None,
    )
    base.update(overrides)
    return Settings(**base)


def test_no_snapshots_when_no_goals_configured():
    snapshots = evaluate_goal_progress(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), _settings())
    assert snapshots == {}


def test_weight_snapshot_uses_latest_value_and_first_as_baseline():
    physical_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-06-01", "2026-06-10", "2026-06-20"]),
            "weight_kg": [80.0, 78.0, 77.0],
        }
    )
    settings = _settings(target_weight_kg=75.0)

    snapshots = evaluate_goal_progress(physical_df, pd.DataFrame(), pd.DataFrame(), settings)

    weight = snapshots["weight"]
    assert weight.current == 77.0
    assert weight.goal.baseline == 80.0
    assert weight.on_track is False
    assert round(weight.progress_ratio, 3) == round(3 / 5, 3)


def test_weekly_distance_snapshot_sums_last_seven_days():
    training_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-06-18", "2026-06-19", "2026-06-01"]),
            "distance_km": [5.0, 3.0, 100.0],  # el de junio 1 queda fuera de la ventana
        }
    )
    settings = _settings(target_weekly_km=10.0)

    snapshots = evaluate_goal_progress(pd.DataFrame(), pd.DataFrame(), training_df, settings)

    weekly = snapshots["weekly_distance"]
    assert weekly.current == 8.0
    assert weekly.on_track is False


def test_sleep_snapshot_converts_minutes_mean_to_hours():
    activity_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-06-19", "2026-06-20"]),
            "sleep_minutes": [420.0, 480.0],
        }
    )
    settings = _settings(target_sleep_hours=8.0)

    snapshots = evaluate_goal_progress(pd.DataFrame(), activity_df, pd.DataFrame(), settings)

    sleep = snapshots["sleep"]
    assert sleep.current == 7.5
    assert sleep.on_track is False


def test_steps_snapshot_missing_data_returns_none_current():
    activity_df = pd.DataFrame({"date": pd.to_datetime(["2026-06-20"]), "steps": [None]})
    settings = _settings(target_daily_steps=10000.0)

    snapshots = evaluate_goal_progress(pd.DataFrame(), activity_df, pd.DataFrame(), settings)

    steps = snapshots["steps"]
    assert steps.current is None
    assert steps.on_track is None
