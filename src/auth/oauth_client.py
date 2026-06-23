"""Cliente OAuth2 para Polar Accesslink.

Responsabilidad única: obtener y mantener válido un access_token.
- Si no hay token local, lanza el flujo de autorización completo (navegador
  + servidor HTTP local efímero para capturar el callback).
- Si hay token pero está caducado, lo refresca con el refresh_token.
- Expone get_valid_token() como único punto de entrada para el resto de la app.
"""

from __future__ import annotations

import base64
import logging
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from src.auth.credentials import TokenData, TokenStorage
from src.config import Settings

logger = logging.getLogger(__name__)

AUTHORIZATION_URL = "https://flow.polar.com/oauth2/authorization"
TOKEN_URL = "https://polarremote.com/v2/oauth2/token"
ACCESSLINK_USERS_URL = "https://www.polaraccesslink.com/v3/users"

_REQUEST_TIMEOUT_SECONDS = 15


class OAuthError(RuntimeError):
    """Error durante el flujo de autorización o intercambio de tokens."""


class _CallbackServer(HTTPServer):
    """HTTPServer con dos slots para el resultado del callback de Polar."""

    def __init__(self, *args, redirect_path: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.redirect_path = redirect_path
        self.auth_code: str | None = None
        self.auth_error: str | None = None


class _CallbackHandler(BaseHTTPRequestHandler):
    """Maneja la única petición GET que Polar hace al redirect_uri."""

    server: _CallbackServer  # anotación para el type-checker

    def do_GET(self) -> None:  # noqa: N802 (nombre impuesto por BaseHTTPRequestHandler)
        parsed = urlparse(self.path)
        if parsed.path != self.server.redirect_path:
            self.send_error(404, "Ruta de callback inesperada")
            return

        params = parse_qs(parsed.query)
        if "code" in params:
            self.server.auth_code = params["code"][0]
            self._respond(200, "Autorización completada. Ya puedes cerrar esta ventana.")
        else:
            error = params.get("error_description", params.get("error", ["Error desconocido"]))[0]
            self.server.auth_error = error
            self._respond(400, f"Error de autorización: {error}")

    def _respond(self, status: int, message: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"<html><body><h2>{message}</h2></body></html>".encode("utf-8"))

    def log_message(self, format: str, *args) -> None:  # noqa: A002 (firma impuesta por la clase base)
        logger.debug("Callback HTTP: " + format, *args)


class PolarOAuthClient:
    """Gestiona el ciclo de vida completo de la autenticación OAuth2 con Polar."""

    def __init__(self, settings: Settings, token_storage: TokenStorage | None = None) -> None:
        self._settings = settings
        self._storage = token_storage or TokenStorage(settings.token_storage_path)

    def get_valid_token(self) -> TokenData:
        """Devuelve un token válido, refrescando o re-autorizando si es necesario."""
        token = self._storage.load()

        if token is None:
            logger.info("No hay token local. Iniciando flujo de autorización OAuth2.")
            token = self._run_authorization_flow()
            self._storage.save(token)
            return token

        if token.is_expired():
            if token.refresh_token is None:
                logger.info("Token caducado y sin refresh_token disponible. Relanzando autorización completa.")
                self._storage.clear()
                token = self._run_authorization_flow()
            else:
                logger.info("Token caducado. Refrescando con refresh_token.")
                try:
                    token = self._refresh_token(token)
                except OAuthError:
                    logger.warning("Refresh fallido. Relanzando flujo de autorización completo.")
                    self._storage.clear()
                    token = self._run_authorization_flow()
            self._storage.save(token)

        return token

    def _run_authorization_flow(self) -> TokenData:
        """Abre el navegador, espera el callback local y canjea el code por un token."""
        redirect_uri = str(self._settings.redirect_uri)
        parsed_redirect = urlparse(redirect_uri)
        host = parsed_redirect.hostname or "localhost"
        port = parsed_redirect.port or 80

        auth_url = self._build_authorization_url(redirect_uri)

        server = _CallbackServer((host, port), _CallbackHandler, redirect_path=parsed_redirect.path)
        try:
            logger.info("Abriendo navegador para autorizar la aplicación...")
            webbrowser.open(auth_url)
            logger.info("Esperando callback en %s ...", redirect_uri)
            while server.auth_code is None and server.auth_error is None:
                server.handle_request()
        finally:
            server.server_close()

        if server.auth_error:
            raise OAuthError(f"Polar denegó la autorización: {server.auth_error}")

        assert server.auth_code is not None  # garantizado por el bucle anterior
        return self._exchange_code_for_token(server.auth_code, redirect_uri)

    def _build_authorization_url(self, redirect_uri: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self._settings.polar_client_id,
            "redirect_uri": redirect_uri,
        }
        return f"{AUTHORIZATION_URL}?{urlencode(params)}"

    def _exchange_code_for_token(self, code: str, redirect_uri: str) -> TokenData:
        response = requests.post(
            TOKEN_URL,
            headers=self._basic_auth_headers(),
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        self._raise_for_oauth_error(response)
        token = TokenData.from_token_response(response.json())
        self._register_user_if_needed(token)
        return token

    def _refresh_token(self, token: TokenData) -> TokenData:
        response = requests.post(
            TOKEN_URL,
            headers=self._basic_auth_headers(),
            data={
                "grant_type": "refresh_token",
                "refresh_token": token.refresh_token,
            },
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code >= 400:
            raise OAuthError(f"Refresh token rechazado por Polar ({response.status_code}): {response.text}")
        new_token = TokenData.from_token_response(response.json())
        new_token.x_user_id = new_token.x_user_id or token.x_user_id
        return new_token

    def _register_user_if_needed(self, token: TokenData) -> None:
        """Registra al usuario en Accesslink (requerido una vez por client_id).

        Polar exige este paso tras la primera autorización; si el usuario ya
        está registrado, la API devuelve 409 Conflict, que se ignora.
        """
        response = requests.post(
            ACCESSLINK_USERS_URL,
            headers={
                "Authorization": f"Bearer {token.access_token}",
                "Content-Type": "application/json",
            },
            json={"member-id": str(token.x_user_id)},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code == 409:
            logger.debug("Usuario ya registrado en Accesslink (409 Conflict esperado).")
        elif response.status_code >= 400:
            logger.warning(
                "No se pudo registrar el usuario en Accesslink (%s): %s",
                response.status_code,
                response.text,
            )

    def _basic_auth_headers(self) -> dict[str, str]:
        credentials = f"{self._settings.polar_client_id}:{self._settings.polar_client_secret}"
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    @staticmethod
    def _raise_for_oauth_error(response: requests.Response) -> None:
        if response.status_code >= 400:
            raise OAuthError(
                f"Polar rechazó el intercambio de código ({response.status_code}): {response.text}"
            )
