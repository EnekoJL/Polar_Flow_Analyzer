import pandas as pd

from src.dashboard import data_loader


def test_load_physical_metrics_returns_empty_df_when_file_missing(tmp_path):
    df = data_loader.load_physical_metrics(tmp_path)
    assert df.empty


def test_load_physical_metrics_parses_date_column(tmp_path):
    csv_path = tmp_path / "physical_metrics.csv"
    csv_path.write_text("date,weight_kg,height_m,bmi,resting_heart_rate\n2026-06-20,72.0,1.8,22.2,55\n")

    df = data_loader.load_physical_metrics(tmp_path)

    assert len(df) == 1
    assert pd.api.types.is_datetime64_any_dtype(df["date"])
    assert df.iloc[0]["weight_kg"] == 72.0


def test_load_daily_activity_returns_empty_df_when_file_missing(tmp_path):
    assert data_loader.load_daily_activity(tmp_path).empty


def test_load_training_sessions_returns_empty_df_when_file_missing(tmp_path):
    assert data_loader.load_training_sessions(tmp_path).empty
