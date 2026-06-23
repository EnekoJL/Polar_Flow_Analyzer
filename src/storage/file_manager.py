"""Persistencia ordenada de los datos crudos descargados de Polar.

Responsabilidad única: escribir payloads crudos en disco, organizados por
categoría y fecha de sincronización. No sabe nada de HTTP ni de la forma
de los datos (eso vive en src/client/polar_api.py).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class RawFileManager:
    """Escribe payloads crudos de Polar en data/raw/<categoria>/<fecha-sync>/."""

    def __init__(self, raw_data_dir: str | Path) -> None:
        self._raw_dir = Path(raw_data_dir)

    def save(self, category: str, identifier: str, payload: str | bytes) -> Path:
        """Guarda un payload crudo bajo data/raw/<categoria>/<fecha-sync>/<identifier>.json."""
        sync_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        target_dir = self._raw_dir / category / sync_date
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_identifier = identifier.replace("/", "_").replace(":", "_")
        output_path = target_dir / f"{safe_identifier}.json"

        if isinstance(payload, bytes):
            output_path.write_bytes(payload)
        else:
            output_path.write_text(payload, encoding="utf-8")

        logger.debug("Crudo guardado en %s", output_path)
        return output_path
