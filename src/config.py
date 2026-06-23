"""Carga y validación de la configuración del proyecto a partir de variables de entorno."""

from __future__ import annotations

from functools import lru_cache

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variables de entorno requeridas y opcionales para Polar Flow Analyzer.

    Pydantic valida tipos y obligatoriedad al instanciar la clase: si falta
    una variable requerida en el .env, la aplicación falla rápido y con un
    mensaje claro en lugar de fallar más adelante con un error críptico.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    polar_client_id: str = Field(..., description="Client ID de la app registrada en Polar Accesslink")
    polar_client_secret: str = Field(..., description="Client Secret de la app registrada en Polar Accesslink")
    redirect_uri: AnyHttpUrl = Field(
        default="http://localhost:5000/oauth2_callback",
        description="URI de callback registrada en Polar Accesslink",
    )

    user_height_m: float | None = Field(
        default=None,
        description="Altura del usuario en metros, usada para calcular el IMC",
    )

    token_storage_path: str = Field(
        default=".polar_tokens.json",
        description="Ruta del archivo local donde se persisten los tokens OAuth2",
    )

    raw_data_dir: str = Field(default="data/raw", description="Directorio de datos crudos descargados de Polar")
    processed_data_dir: str = Field(
        default="data/processed", description="Directorio de datos procesados (CSV limpios)"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve una instancia cacheada de Settings (singleton de facto).

    Cachear evita releer y revalidar el .env en cada módulo que lo necesite.
    """
    return Settings()  # type: ignore[call-arg]
