# Polar Flow Analyzer

Herramienta para sincronizar datos de Polar Accesslink (actividad, entrenamientos y métricas físicas) y transformarlos en CSVs limpios para análisis posterior.

## Estado actual

- ✅ Configuración (`src/config.py`) y autenticación OAuth2 (`src/auth/`) implementadas.
- ⏳ Cliente de red, almacenamiento crudo y procesadores: esqueleto SRP listo, lógica pendiente de fase 2.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.template .env
```

Rellena `.env` con tu `POLAR_CLIENT_ID` y `POLAR_CLIENT_SECRET` (app registrada en https://admin.polaraccesslink.com/), y `REDIRECT_URI` debe coincidir exactamente con la registrada (`http://localhost:5000/oauth2_callback`).

## Uso

```bash
python main.py
```

En la primera ejecución se abrirá el navegador para autorizar la app. El token se guarda en `.polar_tokens.json` (no se versiona) y se refresca automáticamente en ejecuciones posteriores.

## Estructura

```
src/
├── config.py           # Validación de variables de entorno (Pydantic)
├── auth/                # OAuth2: servidor de callback local + persistencia de tokens
├── client/              # Cliente HTTP hacia Polar Accesslink (fase 2)
├── storage/             # Escritura de datos crudos en data/raw/ (fase 2)
└── processors/          # Transformación de crudo -> CSV en data/processed/ (fase 2)
```
