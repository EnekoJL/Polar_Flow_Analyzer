"""Cliente HTTP centralizado para la API de Polar Accesslink.

Responsabilidad única: hablar con Accesslink (crear/listar/confirmar
transacciones, descargar cada recurso) y delegar el guardado de cada
payload crudo en RawFileManager. Reintenta automáticamente ante 429
(Too Many Requests) y errores 5xx transitorios.
"""

from __future__ import annotations

import json
import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.storage.file_manager import RawFileManager

logger = logging.getLogger(__name__)

BASE_URL = "https://www.polaraccesslink.com/v3"
_REQUEST_TIMEOUT_SECONDS = 30
_MAX_RETRIES = 5


class PolarApiError(RuntimeError):
    """Error de comunicación con la API de Polar Accesslink."""


class PolarApiClient:
    """Sincroniza actividad, entrenamientos y datos físicos desde Accesslink."""

    def __init__(self, access_token: str, user_id: int, raw_file_manager: RawFileManager) -> None:
        self._user_id = user_id
        self._raw = raw_file_manager
        self._session = self._build_session(access_token)

    @staticmethod
    def _build_session(access_token: str) -> requests.Session:
        session = requests.Session()
        session.headers.update(
            {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }
        )
        retry = Retry(
            total=_MAX_RETRIES,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            respect_retry_after_header=True,
            allowed_methods=frozenset({"GET", "POST", "PUT"}),
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        return session

    def sync_data(self) -> dict[str, int]:
        """Descarga todo lo pendiente. Devuelve el nº de elementos nuevos por categoría."""
        summary = {
            "activity": self._sync_transaction_resource(
                resource_path="activity-transactions", items_key="activity-log", category="activity"
            ),
            "exercise": self._sync_transaction_resource(
                resource_path="exercise-transactions", items_key="exercises", category="exercise"
            ),
            "physical": self._sync_transaction_resource(
                resource_path="physical-information-transactions",
                items_key="physical-informations",
                category="physical",
            ),
        }
        summary["sleep"] = self._sync_sleep()
        return summary

    def _sync_transaction_resource(self, resource_path: str, items_key: str, category: str) -> int:
        """Sincroniza un recurso basado en transacciones (activity/exercise/physical-information).

        Patrón Accesslink: POST crea transacción (204 si no hay nada nuevo),
        GET lista los recursos pendientes, y PUT confirma (commit) la
        transacción para que Polar no los vuelva a devolver.
        """
        create_url = f"{BASE_URL}/users/{self._user_id}/{resource_path}"

        response = self._session.post(create_url, timeout=_REQUEST_TIMEOUT_SECONDS)
        if response.status_code == 204:
            logger.info("Sin datos nuevos de '%s'.", category)
            return 0
        if response.status_code >= 400:
            raise PolarApiError(
                f"No se pudo crear transacción de '{category}' ({response.status_code}): {response.text}"
            )

        transaction_id = response.json()["transaction-id"]
        list_url = f"{create_url}/{transaction_id}"

        list_response = self._session.get(list_url, timeout=_REQUEST_TIMEOUT_SECONDS)
        if list_response.status_code >= 400:
            raise PolarApiError(
                f"No se pudo listar transacción de '{category}' ({list_response.status_code}): {list_response.text}"
            )

        item_urls = list_response.json().get(items_key, [])
        for item_url in item_urls:
            self._fetch_and_store(item_url, category)

        commit_response = self._session.put(list_url, timeout=_REQUEST_TIMEOUT_SECONDS)
        if commit_response.status_code >= 400:
            logger.warning(
                "No se pudo confirmar (commit) la transacción de '%s': %s", category, commit_response.text
            )

        logger.info("'%s': %d elementos sincronizados.", category, len(item_urls))
        return len(item_urls)

    def _fetch_and_store(self, item_url: str, category: str) -> None:
        response = self._session.get(item_url, timeout=_REQUEST_TIMEOUT_SECONDS)
        if response.status_code >= 400:
            logger.warning("No se pudo descargar %s: %s", item_url, response.text)
            return
        identifier = item_url.rstrip("/").split("/")[-1]
        self._raw.save(category, identifier, response.text)

    def _sync_sleep(self) -> int:
        """Sincroniza datos de sueño (best-effort).

        El scope 'Sleep' de Accesslink es opcional y no todas las apps/cuentas
        lo tienen habilitado. Si el endpoint no está disponible, se registra
        y se continúa sin bloquear el resto de la sincronización.
        """
        url = f"{BASE_URL}/users/{self._user_id}/sleep"
        response = self._session.get(url, timeout=_REQUEST_TIMEOUT_SECONDS)
        if response.status_code >= 400:
            logger.info("Datos de sueño no disponibles (HTTP %s). Continuando sin ellos.", response.status_code)
            return 0

        payload = response.json()
        nights = payload if isinstance(payload, list) else payload.get("nights", [])
        for night in nights:
            identifier = night.get("date", "unknown")
            self._raw.save("sleep", identifier, json.dumps(night))

        logger.info("'sleep': %d noches sincronizadas.", len(nights))
        return len(nights)
