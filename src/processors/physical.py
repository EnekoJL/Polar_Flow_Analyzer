"""Procesador de métricas físicas: peso, IMC y frecuencia cardíaca en reposo."""

from __future__ import annotations

import pandas as pd

from src.processors.base import BaseProcessor

_COLUMNS = ["date", "weight_kg", "height_m", "bmi", "resting_heart_rate"]


class PhysicalMetricsProcessor(BaseProcessor):
    """Extrae peso, IMC calculado y FC en reposo a partir de los datos crudos."""

    output_filename = "physical_metrics.csv"

    def __init__(
        self,
        raw_data_dir,
        processed_data_dir,
        user_height_m: float | None = None,
    ) -> None:
        super().__init__(raw_data_dir, processed_data_dir)
        self._user_height_m = user_height_m

    def extract(self) -> pd.DataFrame:
        records = self._read_raw_records("physical")
        rows = []

        for record in records:
            weight_kg = record.get("weight")
            height_cm = record.get("height")
            # Si Polar no informa la altura en este registro, se usa la
            # altura configurada manualmente en Settings (USER_HEIGHT_M).
            height_m = (height_cm / 100) if height_cm else self._user_height_m
            bmi = (weight_kg / (height_m**2)) if (weight_kg and height_m) else None

            rows.append(
                {
                    "date": (record.get("created") or "")[:10] or None,
                    "weight_kg": weight_kg,
                    "height_m": height_m,
                    "bmi": round(bmi, 1) if bmi is not None else None,
                    "resting_heart_rate": record.get("resting-heart-rate"),
                }
            )

        df = pd.DataFrame(rows, columns=_COLUMNS)
        if not df.empty:
            df = df.sort_values("date").drop_duplicates(subset="date", keep="last").reset_index(drop=True)
        return df
