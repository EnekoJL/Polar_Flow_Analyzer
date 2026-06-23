"""Procesador del historial de entrenamientos: distancia, ritmo, intensidad."""

from __future__ import annotations

import pandas as pd

from src.processors.base import BaseProcessor

_COLUMNS = [
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


class TrainingSessionsProcessor(BaseProcessor):
    """Extrae métricas de entrenamiento a partir de las sesiones crudas."""

    output_filename = "training_sessions.csv"

    def extract(self) -> pd.DataFrame:
        records = self._read_raw_records("exercise")
        rows = []

        for record in records:
            duration_min = self._parse_iso8601_duration_minutes(record.get("duration"))
            distance_m = record.get("distance")
            distance_km = (distance_m / 1000) if distance_m is not None else None

            heart_rate = record.get("heart-rate") or {}
            avg_heart_rate = heart_rate.get("average")
            max_heart_rate = heart_rate.get("maximum")

            training_load = record.get("training-load")
            if training_load is None:
                training_load = (record.get("training-load-pro") or {}).get("training-load-val")

            pace_min_per_km = (
                duration_min / distance_km if duration_min and distance_km else None
            )
            speed_kmh = (
                distance_km / (duration_min / 60) if duration_min and distance_km else None
            )

            rows.append(
                {
                    "date": (record.get("start-time") or "")[:10] or None,
                    "sport": record.get("detailed-sport-info") or record.get("sport"),
                    "duration_min": duration_min,
                    "distance_km": distance_km,
                    "avg_heart_rate": avg_heart_rate,
                    "max_heart_rate": max_heart_rate,
                    "training_load": training_load,
                    "pace_min_per_km": round(pace_min_per_km, 2) if pace_min_per_km else None,
                    "speed_kmh": round(speed_kmh, 2) if speed_kmh else None,
                    "calories": record.get("calories"),
                }
            )

        df = pd.DataFrame(rows, columns=_COLUMNS)
        if not df.empty:
            df = df.sort_values("date").reset_index(drop=True)
        return df
