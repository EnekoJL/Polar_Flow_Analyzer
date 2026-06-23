import json

import pandas as pd
import pytest

from src.processors.base import BaseProcessor


class _DummyProcessor(BaseProcessor):
    """Subclase mínima para poder instanciar BaseProcessor en los tests."""

    output_filename = "dummy.csv"

    def extract(self) -> pd.DataFrame:
        return pd.DataFrame()


@pytest.fixture
def processor(tmp_path):
    return _DummyProcessor(tmp_path / "raw", tmp_path / "processed")


@pytest.mark.parametrize(
    "duration, expected",
    [
        ("PT1H30M", 90.0),
        ("PT45M30S", 45.5),
        ("PT2H", 120.0),
        ("PT30S", 0.5),
        (None, None),
        ("", None),
        ("not-a-duration", None),
    ],
)
def test_parse_iso8601_duration_minutes(processor, duration, expected):
    assert processor._parse_iso8601_duration_minutes(duration) == expected


def test_read_raw_records_returns_empty_list_when_category_dir_missing(processor):
    assert processor._read_raw_records("activity") == []


def test_read_raw_records_parses_all_json_files_recursively(tmp_path, processor):
    category_dir = tmp_path / "raw" / "activity" / "2026-06-20"
    category_dir.mkdir(parents=True)
    (category_dir / "a.json").write_text(json.dumps({"date": "2026-06-20", "calories": 2000}))
    (category_dir / "b.json").write_text(json.dumps({"date": "2026-06-19", "calories": 1900}))

    records = processor._read_raw_records("activity")

    assert len(records) == 2
    assert {r["date"] for r in records} == {"2026-06-19", "2026-06-20"}


def test_read_raw_records_skips_malformed_json(tmp_path, processor):
    category_dir = tmp_path / "raw" / "activity" / "2026-06-20"
    category_dir.mkdir(parents=True)
    (category_dir / "good.json").write_text(json.dumps({"date": "2026-06-20"}))
    (category_dir / "bad.json").write_text("{not valid json")

    records = processor._read_raw_records("activity")

    assert len(records) == 1
    assert records[0]["date"] == "2026-06-20"


def test_run_writes_csv_with_extracted_dataframe(tmp_path):
    class _OneRowProcessor(BaseProcessor):
        output_filename = "one_row.csv"

        def extract(self) -> pd.DataFrame:
            return pd.DataFrame([{"a": 1, "b": 2}])

    proc = _OneRowProcessor(tmp_path / "raw", tmp_path / "processed")
    output_path = proc.run()

    assert output_path.exists()
    df = pd.read_csv(output_path)
    assert df.to_dict(orient="records") == [{"a": 1, "b": 2}]
