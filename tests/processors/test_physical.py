import json

from src.processors.physical import PhysicalMetricsProcessor


def _write_physical_record(raw_dir, identifier: str, record: dict) -> None:
    target_dir = raw_dir / "physical" / "2026-06-23"
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / f"{identifier}.json").write_text(json.dumps(record))


def test_bmi_calculated_from_height_in_record(tmp_path):
    raw_dir = tmp_path / "raw"
    _write_physical_record(
        raw_dir,
        "p1",
        {"created": "2026-06-23T08:00:00.000", "weight": 72.0, "height": 180, "resting-heart-rate": 55},
    )

    processor = PhysicalMetricsProcessor(raw_dir, tmp_path / "processed")
    df = processor.extract()

    assert len(df) == 1
    row = df.iloc[0]
    assert row["date"] == "2026-06-23"
    assert row["weight_kg"] == 72.0
    assert row["height_m"] == 1.8
    assert row["bmi"] == round(72.0 / (1.8**2), 1)
    assert row["resting_heart_rate"] == 55


def test_bmi_falls_back_to_configured_height_when_missing_in_record(tmp_path):
    raw_dir = tmp_path / "raw"
    _write_physical_record(raw_dir, "p1", {"created": "2026-06-23T08:00:00.000", "weight": 80.0})

    processor = PhysicalMetricsProcessor(raw_dir, tmp_path / "processed", user_height_m=1.75)
    df = processor.extract()

    row = df.iloc[0]
    assert row["height_m"] == 1.75
    assert row["bmi"] == round(80.0 / (1.75**2), 1)


def test_bmi_is_none_when_weight_missing(tmp_path):
    raw_dir = tmp_path / "raw"
    _write_physical_record(raw_dir, "p1", {"created": "2026-06-23T08:00:00.000", "height": 180})

    processor = PhysicalMetricsProcessor(raw_dir, tmp_path / "processed")
    df = processor.extract()

    row = df.iloc[0]
    assert row["weight_kg"] is None or pd_isna(row["weight_kg"])
    assert row["bmi"] is None or pd_isna(row["bmi"])


def test_duplicate_dates_keep_last_record(tmp_path):
    raw_dir = tmp_path / "raw"
    _write_physical_record(raw_dir, "p1", {"created": "2026-06-23T08:00:00.000", "weight": 70.0})
    _write_physical_record(raw_dir, "p2", {"created": "2026-06-23T20:00:00.000", "weight": 71.0})

    processor = PhysicalMetricsProcessor(raw_dir, tmp_path / "processed")
    df = processor.extract()

    assert len(df) == 1
    assert df.iloc[0]["weight_kg"] == 71.0


def test_extract_returns_expected_columns_when_empty(tmp_path):
    processor = PhysicalMetricsProcessor(tmp_path / "raw", tmp_path / "processed")
    df = processor.extract()

    assert list(df.columns) == ["date", "weight_kg", "height_m", "bmi", "resting_heart_rate"]
    assert df.empty


def pd_isna(value) -> bool:
    import pandas as pd

    return pd.isna(value)
