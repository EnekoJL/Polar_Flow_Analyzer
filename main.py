"""Punto de entrada único de Polar Flow Analyzer.

Secuencia:
  1. Cargar configuración y verificar/renovar credenciales OAuth2.
  2. Sincronizar y descargar datos crudos desde Polar Accesslink (data/raw/).
  3. Ejecutar los procesadores (physical, activity, training) para generar
     los CSV limpios en data/processed/.
  4. Mostrar un resumen por terminal.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

from src.auth.credentials import TokenData, TokenStorage
from src.auth.oauth_client import OAuthError, PolarOAuthClient
from src.client.polar_api import PolarApiClient, PolarApiError
from src.config import Settings, get_settings
from src.processors.activity import DailyActivityProcessor
from src.processors.physical import PhysicalMetricsProcessor
from src.processors.training import TrainingSessionsProcessor
from src.storage.file_manager import RawFileManager

logger = logging.getLogger("polar_flow_analyzer")


def configure_logging() -> None:
    """Configura logging estructurado a consola (timestamp, nivel, módulo, mensaje)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def ensure_credentials(settings: Settings) -> TokenData:
    """Paso 1: obtiene un token OAuth2 válido (autoriza o refresca si hace falta)."""
    storage = TokenStorage(settings.token_storage_path)
    client = PolarOAuthClient(settings, storage)
    return client.get_valid_token()


def sync_raw_data(token: TokenData, settings: Settings) -> dict[str, int]:
    """Paso 2: descarga datos nuevos de Polar Accesslink a data/raw/."""
    raw_manager = RawFileManager(settings.raw_data_dir)
    api_client = PolarApiClient(token.access_token, token.x_user_id, raw_manager)
    return api_client.sync_data()


def run_processors(settings: Settings) -> dict[str, str]:
    """Paso 3: ejecuta cada procesador y devuelve un resumen {nombre: resultado}."""
    processors = {
        "physical": PhysicalMetricsProcessor(
            settings.raw_data_dir, settings.processed_data_dir, settings.user_height_m
        ),
        "activity": DailyActivityProcessor(settings.raw_data_dir, settings.processed_data_dir),
        "training": TrainingSessionsProcessor(settings.raw_data_dir, settings.processed_data_dir),
    }

    summary: dict[str, str] = {}
    for name, processor in processors.items():
        output_path = processor.run()
        summary[name] = f"OK -> {output_path}"
    return summary


def build_summary_metrics(settings: Settings) -> dict[str, str]:
    """Calcula las métricas rápidas para el resumen final (km semana, último peso)."""
    processed_dir = Path(settings.processed_data_dir)
    metrics: dict[str, str] = {}

    training_path = processed_dir / "training_sessions.csv"
    if training_path.exists():
        df = pd.read_csv(training_path)
        if not df.empty:
            dates = pd.to_datetime(df["date"])
            one_week_ago = pd.Timestamp.now().normalize() - pd.Timedelta(7, unit="D")
            weekly_km = df.loc[dates >= one_week_ago, "distance_km"].sum()
            metrics["km_ultima_semana"] = f"{weekly_km:.1f} km"
        else:
            metrics["km_ultima_semana"] = "sin datos"
    else:
        metrics["km_ultima_semana"] = "sin datos"

    physical_path = processed_dir / "physical_metrics.csv"
    if physical_path.exists():
        df = pd.read_csv(physical_path).dropna(subset=["weight_kg"])
        if not df.empty:
            last = df.sort_values("date").iloc[-1]
            metrics["ultimo_peso"] = f"{last['weight_kg']:.1f} kg ({last['date']})"
        else:
            metrics["ultimo_peso"] = "sin datos"
    else:
        metrics["ultimo_peso"] = "sin datos"

    return metrics


def print_summary(sync_summary: dict[str, int], processor_summary: dict[str, str], metrics: dict[str, str]) -> None:
    """Paso 4: resumen final por terminal."""
    logger.info("=== Resumen de sincronización ===")
    for category, count in sync_summary.items():
        logger.info("  - %s: %d elementos nuevos", category, count)

    logger.info("=== Resumen de procesado ===")
    for name, result in processor_summary.items():
        logger.info("  - %s: %s", name, result)

    logger.info("=== Métricas rápidas ===")
    logger.info("  - Km acumulados última semana: %s", metrics["km_ultima_semana"])
    logger.info("  - Último peso registrado: %s", metrics["ultimo_peso"])


def main() -> int:
    configure_logging()
    logger.info("Polar Flow Analyzer - iniciando")

    settings = get_settings()

    try:
        token = ensure_credentials(settings)
        logger.info("Credenciales OAuth2 válidas (x_user_id=%s)", token.x_user_id)
    except OAuthError as exc:
        logger.error("Fallo de autenticación con Polar: %s", exc)
        return 1

    sync_summary: dict[str, int] = {}
    try:
        sync_summary = sync_raw_data(token, settings)
        logger.info("Sincronización de datos crudos completada.")
    except PolarApiError as exc:
        logger.error("Fallo al sincronizar con Polar Accesslink: %s", exc)

    processor_summary = run_processors(settings)
    metrics = build_summary_metrics(settings)
    print_summary(sync_summary, processor_summary, metrics)

    logger.info("Polar Flow Analyzer - finalizado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
