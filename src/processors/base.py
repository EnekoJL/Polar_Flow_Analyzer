"""Clase base abstracta para los procesadores de datos crudos -> CSV limpio."""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_ISO8601_DURATION_RE = re.compile(
    r"PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?"
)


class BaseProcessor(ABC):
    """Contrato común para todo procesador de datos de Polar.

    Cada subclase tiene una única responsabilidad: convertir un tipo de
    dato crudo (actividad, entrenamiento, físico...) en un DataFrame limpio.
    La lectura del directorio crudo y la escritura del CSV final son
    comunes y viven aquí para no duplicarlas en cada subclase concreta.
    """

    def __init__(self, raw_data_dir: str | Path, processed_data_dir: str | Path) -> None:
        self._raw_dir = Path(raw_data_dir)
        self._processed_dir = Path(processed_data_dir)

    @property
    @abstractmethod
    def output_filename(self) -> str:
        """Nombre del CSV de salida, p.ej. 'daily_activity.csv'."""

    @abstractmethod
    def extract(self) -> pd.DataFrame:
        """Lee los datos crudos relevantes y devuelve un DataFrame limpio."""

    def run(self) -> Path:
        """Ejecuta la extracción y persiste el resultado en data/processed/."""
        df = self.extract()
        self._processed_dir.mkdir(parents=True, exist_ok=True)
        output_path = self._processed_dir / self.output_filename
        df.to_csv(output_path, index=False)
        logger.info("Procesado guardado en %s (%d filas)", output_path, len(df))
        return output_path

    def _read_raw_records(self, category: str) -> list[dict]:
        """Lee y parsea todos los JSON crudos descargados para una categoría.

        Recorre data/raw/<category>/**/*.json (todas las fechas de
        sincronización), ya que un mismo CSV procesado agrega histórico.
        """
        records: list[dict] = []
        category_dir = self._raw_dir / category
        if not category_dir.exists():
            logger.warning("No hay datos crudos para '%s' en %s", category, category_dir)
            return records

        for json_path in sorted(category_dir.rglob("*.json")):
            try:
                records.append(json.loads(json_path.read_text(encoding="utf-8")))
            except json.JSONDecodeError as exc:
                logger.warning("JSON inválido en %s: %s", json_path, exc)
        return records

    @staticmethod
    def _parse_iso8601_duration_minutes(duration: str | None) -> float | None:
        """Convierte una duración ISO8601 ('PT1H30M') a minutos decimales."""
        if not duration:
            return None
        match = _ISO8601_DURATION_RE.fullmatch(duration)
        if not match:
            return None
        hours = float(match.group("hours") or 0)
        minutes = float(match.group("minutes") or 0)
        seconds = float(match.group("seconds") or 0)
        return hours * 60 + minutes + seconds / 60
