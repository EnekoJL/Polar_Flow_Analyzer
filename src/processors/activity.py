"""Procesador de actividad diaria: pasos, calorías, tiempo activo y sueño."""

from __future__ import annotations

import pandas as pd

from src.processors.base import BaseProcessor

_COLUMNS = [
    "date",
    "steps",
    "calories_total",
    "calories_active",
    "calories_basal_estimated",
    "active_time_min",
    "sleep_minutes",
    "sleep_score",
]


class DailyActivityProcessor(BaseProcessor):
    """Extrae pasos, calorías, tiempo activo y sueño a partir de los datos crudos."""

    output_filename = "daily_activity.csv"

    def extract(self) -> pd.DataFrame:
        records = self._read_raw_records("activity")
        sleep_by_date = {
            record.get("date"): record for record in self._read_raw_records("sleep")
        }

        rows = []
        for record in records:
            date = record.get("date")
            calories_total = record.get("calories")
            calories_active = record.get("active-calories")
            # Accesslink no expone calorías basales directamente: se estiman
            # como el resto entre el total diario y las activas.
            calories_basal = (
                calories_total - calories_active
                if calories_total is not None and calories_active is not None
                else None
            )

            sleep = sleep_by_date.get(date, {})

            rows.append(
                {
                    "date": date,
                    "steps": record.get("active-steps"),
                    "calories_total": calories_total,
                    "calories_active": calories_active,
                    "calories_basal_estimated": calories_basal,
                    "active_time_min": self._parse_iso8601_duration_minutes(record.get("duration")),
                    "sleep_minutes": sleep.get("total-sleep-duration"),
                    "sleep_score": sleep.get("sleep-score"),
                }
            )

        df = pd.DataFrame(rows, columns=_COLUMNS)
        if not df.empty:
            df = df.sort_values("date").drop_duplicates(subset="date", keep="last").reset_index(drop=True)
        return df
