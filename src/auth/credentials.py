"""Modelo y persistencia local de los tokens OAuth2 de Polar Accesslink.

Responsabilidad única: leer y escribir el archivo de credenciales en disco.
No conoce nada sobre el flujo OAuth2 (eso vive en oauth_client.py).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Margen de seguridad: refrescamos el token un poco antes de que caduque
# realmente, para evitar fallos por desajuste de reloj o latencia de red.
_EXPIRY_SAFETY_MARGIN = timedelta(minutes=2)


class TokenData(BaseModel):
    """Representa un token OAuth2 de Polar y sus metadatos asociados."""

    access_token: str
    # Polar Accesslink no siempre emite refresh_token: sus access tokens son
    # de muy larga duración (años) y se gestionan sin refresco explícito.
    refresh_token: str | None = None
    token_type: str = "bearer"
    x_user_id: int | None = Field(default=None, description="ID de usuario Polar asociado al token")
    expires_at: datetime

    @classmethod
    def from_token_response(cls, payload: dict) -> "TokenData":
        """Construye un TokenData a partir de la respuesta cruda del endpoint /oauth2/token."""
        expires_in_seconds = int(payload["expires_in"])
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
        return cls(
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token"),
            token_type=payload.get("token_type", "bearer"),
            x_user_id=payload.get("x_user_id"),
            expires_at=expires_at,
        )

    def is_expired(self) -> bool:
        """True si el token ya caducó (o está a punto de hacerlo)."""
        return datetime.now(timezone.utc) >= (self.expires_at - _EXPIRY_SAFETY_MARGIN)


class TokenStorage:
    """Lee y escribe TokenData en un archivo JSON local."""

    def __init__(self, storage_path: str | Path) -> None:
        self._path = Path(storage_path)

    def load(self) -> TokenData | None:
        """Devuelve el token guardado, o None si no existe o está corrupto."""
        if not self._path.exists():
            return None

        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return TokenData.model_validate(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Archivo de tokens corrupto o ilegible (%s): %s", self._path, exc)
            return None

    def save(self, token: TokenData) -> None:
        """Persiste el token en disco con permisos restringidos."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(token.model_dump_json(indent=2), encoding="utf-8")
        self._path.chmod(0o600)
        logger.info("Token guardado en %s", self._path)

    def clear(self) -> None:
        """Elimina el archivo de tokens, si existe (p.ej. tras un refresh fallido)."""
        if self._path.exists():
            self._path.unlink()
            logger.info("Token eliminado de %s", self._path)
