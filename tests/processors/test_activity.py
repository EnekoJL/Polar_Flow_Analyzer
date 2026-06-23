import json

import pandas as pd

from src.processors.activity import DailyActivityProcessor


def _write(raw_dir, category: str, identifier: str, record: dict) -> None:
    target_dir = raw_dir / category / "2026-06-23"
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / f"{identifier}.json").write_text(json.dumps(record))


def test_extract_computes_basal_calories_and_active_minutes(tmp_path):
    raw_dir = tmp_path / "raw"
    _write(
        raw_dir,
        "activity",
        "a1",
        {
            "date": "2026-06-20",
            "calories": 2400,
            "active-calories": 600,
            "active-steps": 8500,
            "duration": "PT1H30M",
        },
    )

    processor = DailyActivityProcessor(raw_dir, tmp_path / "processed")
    df = processor.extract()

    assert len(df) == 1
    row = df.iloc[0]
    assert row["date"] == "2026-06-20"
    assert row["steps"] == 8500
    assert row["calories_total"] == 2400
    assert row["calories_active"] == 600
    assert row["calories_basal_estimated"] == 1800
    assert row["active_time_min"] == 90.0


def test_extract_joins_sleep_data_by_date(tmp_path):
    raw_dir = tmp_path / "raw"
    _write(raw_dir, "activity", "a1", {"date": "2026-06-20", "calories": 2000, "active-calories": 400})
    _write(raw_dir, "sleep", "s1", {"date": "2026-06-20", "total-sleep-duration": 420, "sleep-score": 85})

    processor = DailyActivityProcessor(raw_dir, tmp_path / "processed")
    df = processor.extract()

    row = df.iloc[0]
    assert row["sleep_minutes"] == 420
    assert row["sleep_score"] == 85


def test_extract_leaves_sleep_columns_empty_when_no_sleep_data(tmp_path):
    raw_dir = tmp_path / "raw"
    _write(raw_dir, "activity", "a1", {"date": "2026-06-20", "calories": 2000, "active-calories": 400})

    processor = DailyActivityProcessor(raw_dir, tmp_path / "processed")
    df = processor.extract()

    row = df.iloc[0]
    assert pd.isna(row["sleep_minutes"])
    assert pd.isna(row["sleep_score"])


def test_extract_deduplicates_same_date_keeping_last(tmp_path):
    raw_dir = tmp_path / "raw"
    _write(raw_dir, "activity", "a1", {"date": "2026-06-20", "calories": 2000, "active-calories": 400})
    _write(raw_dir, "activity", "a2", {"date": "2026-06-20", "calories": 2200, "active-calories": 500})

    processor = DailyActivityProcessor(raw_dir, tmp_path / "processed")
    df = processor.extract()

    assert len(df) == 1
    assert df.iloc[0]["calories_total"] == 2200


def test_extract_returns_expected_columns_when_empty(tmp_path):
    processor = DailyActivityProcessor(tmp_path / "raw", tmp_path / "processed")
    df = processor.extract()

    assert list(df.columns) == [
        "date",
        "steps",
        "calories_total",
        "calories_active",
        "calories_basal_estimated",
        "active_time_min",
        "sleep_minutes",
        "sleep_score",
    ]
    assert df.empty
