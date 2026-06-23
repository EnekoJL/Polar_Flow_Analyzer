import json

from src.processors.training import TrainingSessionsProcessor


def _write(raw_dir, identifier: str, record: dict) -> None:
    target_dir = raw_dir / "exercise" / "2026-06-23"
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / f"{identifier}.json").write_text(json.dumps(record))


def test_extract_computes_pace_and_speed_for_running(tmp_path):
    raw_dir = tmp_path / "raw"
    _write(
        raw_dir,
        "e1",
        {
            "start-time": "2026-06-20T07:00:00.000",
            "detailed-sport-info": "RUNNING",
            "duration": "PT30M",
            "distance": 5000.0,
            "calories": 350,
            "heart-rate": {"average": 150, "maximum": 175},
            "training-load": 80.5,
        },
    )

    processor = TrainingSessionsProcessor(raw_dir, tmp_path / "processed")
    df = processor.extract()

    assert len(df) == 1
    row = df.iloc[0]
    assert row["date"] == "2026-06-20"
    assert row["sport"] == "RUNNING"
    assert row["duration_min"] == 30.0
    assert row["distance_km"] == 5.0
    assert row["avg_heart_rate"] == 150
    assert row["max_heart_rate"] == 175
    assert row["training_load"] == 80.5
    assert row["pace_min_per_km"] == 6.0
    assert row["speed_kmh"] == 10.0
    assert row["calories"] == 350


def test_extract_falls_back_to_sport_field_when_no_detailed_info(tmp_path):
    raw_dir = tmp_path / "raw"
    _write(raw_dir, "e1", {"start-time": "2026-06-20T07:00:00.000", "sport": "CYCLING", "duration": "PT1H"})

    processor = TrainingSessionsProcessor(raw_dir, tmp_path / "processed")
    df = processor.extract()

    assert df.iloc[0]["sport"] == "CYCLING"


def test_extract_reads_training_load_from_nested_pro_field(tmp_path):
    raw_dir = tmp_path / "raw"
    _write(
        raw_dir,
        "e1",
        {
            "start-time": "2026-06-20T07:00:00.000",
            "sport": "RUNNING",
            "training-load-pro": {"training-load-val": 95.0},
        },
    )

    processor = TrainingSessionsProcessor(raw_dir, tmp_path / "processed")
    df = processor.extract()

    assert df.iloc[0]["training_load"] == 95.0


def test_extract_pace_and_speed_are_none_without_distance(tmp_path):
    raw_dir = tmp_path / "raw"
    _write(raw_dir, "e1", {"start-time": "2026-06-20T07:00:00.000", "sport": "STRENGTH_TRAINING", "duration": "PT45M"})

    processor = TrainingSessionsProcessor(raw_dir, tmp_path / "processed")
    df = processor.extract()

    row = df.iloc[0]
    assert row["pace_min_per_km"] is None or _is_nan(row["pace_min_per_km"])
    assert row["speed_kmh"] is None or _is_nan(row["speed_kmh"])


def test_extract_returns_expected_columns_when_empty(tmp_path):
    processor = TrainingSessionsProcessor(tmp_path / "raw", tmp_path / "processed")
    df = processor.extract()

    assert list(df.columns) == [
        "date",
        "sport",
        "duration_min",
        "distance_km",
        "avg_heart_rate",
        "max_heart_rate",
        "training_load",
        "pace_min_per_km",
        "speed_kmh",
        "calories",
    ]
    assert df.empty


def _is_nan(value) -> bool:
    import pandas as pd

    return pd.isna(value)
