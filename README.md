# Polar Flow Analyzer

Herramienta para sincronizar datos de Polar Accesslink (actividad, entrenamientos y métricas físicas) y transformarlos en CSVs limpios para análisis posterior.

## Estado actual

- ✅ Configuración (`src/config.py`), autenticación OAuth2, cliente Polar, almacenamiento crudo y procesadores implementados.
- ✅ Dashboard Streamlit con pestaña "Objetivos" (progreso vs. peso/km semanales/sueño/pasos), Físico, Actividad y Entrenamientos.
- ⏳ Migración a arquitectura hexagonal en progreso — ver `CLAUDE.md`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.template .env
```

Rellena `.env` con tu `POLAR_CLIENT_ID` y `POLAR_CLIENT_SECRET` (app registrada en https://admin.polaraccesslink.com/), y `REDIRECT_URI` debe coincidir exactamente con la registrada (`http://localhost:5000/oauth2_callback`).

### Objetivos personales (pestaña "Objetivos" del dashboard)

Edita `.env` (mismo archivo) y añade los objetivos que quieras trackear. Cualquiera que dejes en blanco simplemente no aparece en la pestaña:

```
TARGET_WEIGHT_KG=75
TARGET_WEEKLY_KM=20
TARGET_SLEEP_HOURS=8
TARGET_DAILY_STEPS=10000
```

## Uso

```bash
python main.py
```

En la primera ejecución se abrirá el navegador para autorizar la app. El token se guarda en `.polar_tokens.json` (no se versiona) y se refresca automáticamente en ejecuciones posteriores.

## Estructura

```
src/
├── config.py           # Validación de variables de entorno (Pydantic), incluye objetivos
├── auth/                # OAuth2: servidor de callback local + persistencia de tokens
├── client/              # Cliente HTTP hacia Polar Accesslink
├── storage/             # Escritura de datos crudos en data/raw/
├── processors/          # Transformación de crudo -> CSV en data/processed/
├── domain/              # Modelos puros (Goal, ProgressSnapshot) — sin pandas/I-O
├── application/         # Casos de uso (evaluate_goal_progress) — orquesta domain + datos
└── dashboard/           # data_loader (CSV -> DataFrame) y charts (figuras Plotly)
```

Ver `CLAUDE.md` para el plan de arquitectura hexagonal completo (en progreso).
