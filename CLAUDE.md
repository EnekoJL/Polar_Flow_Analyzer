# Polar Flow Analyzer — CLAUDE.md

## What this is

Personal tool. Pulls Polar Accesslink data (sleep, daily activity, training sessions, physical metrics/weight) into clean CSVs, then visualizes them in a Streamlit dashboard. Purpose: track progress toward personal health/fitness goals (weight trend, training load, sleep, steps) — not a general-purpose product. Single user, local-first, no server/db.

## Current state (as of this revision)

```
main.py          → orchestration script: auth → sync raw → run processors → print summary
dashboard.py      → Streamlit UI: loads processed CSVs, renders charts
src/
├── config.py     # Pydantic Settings from .env
├── auth/         # OAuth2 flow (local callback server) + token persistence
├── client/       # HTTP client to Polar Accesslink API
├── storage/      # Raw JSON file writer (data/raw/)
├── processors/   # BaseProcessor (ABC) → extract() raw JSON → DataFrame → CSV
└── dashboard/    # data_loader (CSV → DataFrame) + charts (Plotly figures)
```

Each processor (`activity.py`, `physical.py`, `training.py`) already follows SRP at the file level — one processor, one raw-data category, one output CSV. `BaseProcessor` correctly centralizes shared mechanics (read raw JSON, write CSV, ISO8601 duration parsing). This is a decent flat/layered start. It is **not** hexagonal yet: there's no explicit domain model, no ports (interfaces), and business rules are inline inside pandas transformations and `main.py`.

Known gaps:
- No domain entities (e.g. `SleepSession`, `TrainingSession`, `BodyMetric`) — everything is a DataFrame row, so "what is a valid training session" lives implicitly in pandas code, not in a checkable type.
- No port/interface boundary between processors and storage — processors read straight from `Path` / raw JSON, no abstraction a test or future data source (DB, API v2) could substitute.
- `main.py` mixes orchestration with business logic (`build_summary_metrics` computes weekly km and last weight directly — that's a use case, not wiring).
- Goal-tracking is not modeled at all yet (no concept of "target weight", "target weekly km", progress-vs-goal). This is the actual point of the app per your ask — currently the dashboard only shows raw history, no goal deltas.
- Client/`src/client/polar_api.py` not yet reviewed for sync logic — check before extending.

## Target architecture: hexagonal (ports & adapters) + SRP

Goal: business rules (what a "good week" looks like, how progress toward a goal is computed) live in a **domain** layer that knows nothing about Polar's API shape, pandas, CSV files, or Streamlit. Everything else is a swappable adapter.

```
src/
├── domain/                  # Pure Python. No I/O, no pandas, no requests, no streamlit.
│   ├── models.py            #   dataclasses/Pydantic models: TrainingSession, SleepRecord,
│   │                        #   BodyMetric, Goal, ProgressSnapshot
│   └── services.py          #   pure functions/classes: compute_weekly_distance(),
│                             #   progress_toward_goal(), training_load(), trend()
│
├── application/             # Use cases. Orchestrate domain + ports. No knowledge of
│   │                        # *which* adapter is plugged in.
│   ├── ports.py             #   Protocols/ABCs: RawDataSource, RawDataSink, MetricsRepository
│   └── use_cases.py         #   SyncPolarData, BuildDailySummary, EvaluateGoalProgress
│
├── adapters/                 # Concrete I/O implementations of the ports above.
│   ├── polar_api/            #   (current src/client + src/auth) — HTTP + OAuth2
│   ├── csv_storage/          #   (current src/storage + src/processors persistence half)
│   └── streamlit_ui/         #   (current dashboard.py + src/dashboard)
│
└── config.py                 # stays as-is — composition root reads it, builds adapters,
                               # injects into use cases.
```

Dependency rule: arrows point inward only. `domain` depends on nothing in this project. `application` depends on `domain` + its own `ports` (interfaces it defines, doesn't implement). `adapters` depend on `application.ports` (they implement the interface) and `domain` (they translate raw shapes into domain models). Nothing in `domain` or `application` imports `requests`, `pandas`, `streamlit`, or `pathlib` I/O directly — that's an adapter's job to translate at the boundary.

Why this matters for *this* project specifically: Polar's raw JSON shape, pandas, and Streamlit are all things that could plausibly change (Polar API v2, a different chart lib, a future mobile view) — but "what counts as progress toward your weight goal" should not have to be rewritten when any of those change.

## SRP rules of thumb (apply to all new code, not just hexagonal layers)

- One class/function = one reason to change. If you're editing a processor for both "parse this new field" and "fix the chart that displays it," that's two changes in two files, not one.
- `extract()` parses raw → domain shape. Persistence (`run()` in `BaseProcessor`) is separate and already is — keep that split when migrating to `adapters/csv_storage/`.
- Orchestration scripts (`main.py`) only wire dependencies and call use cases. No business math in `main.py` — `build_summary_metrics` is a use case (`EvaluateGoalProgress` or similar) waiting to be extracted.
- Adapters never contain decisions, only translation (raw JSON → domain object, domain object → CSV row, domain object → Plotly figure).

## Migration approach (incremental, not a rewrite)

Don't do a big-bang restructure. Suggested order, each step independently shippable and testable:

1. Introduce `src/domain/models.py` with typed entities for what processors currently emit as DataFrame rows. Processors start returning `list[DomainModel]` internally before converting to DataFrame at the CSV-write boundary.
2. Introduce `Goal` model + `src/domain/services.py::progress_toward_goal()`. This is the actual feature gap — wire it into the dashboard as a new tab/section once it exists.
3. Extract `build_summary_metrics` out of `main.py` into an `application/use_cases.py::EvaluateGoalProgress`, taking processed data + goals as input, no file I/O inside it (pass in already-loaded DataFrames or domain objects).
4. Define `application/ports.py::RawDataSource` Protocol; have `PolarApiClient` implement it. Only do this once a second data source is plausible or tests need a fake — don't introduce the interface speculatively before it earns its keep.
5. Rename/regroup directories last, after behavior is already decomposed correctly. Renaming `src/client` → `src/adapters/polar_api` is mechanical and should be its own commit, never mixed with logic changes.

## Conventions already in place — keep these

- Pydantic `Settings` (`src/config.py`) as the single source of env config, cached via `lru_cache`. Don't read `os.environ` elsewhere.
- `BaseProcessor` ABC pattern for processors — keep `extract()` abstract, `run()` shared.
- Tests mirror `src/` structure 1:1 under `tests/` (`tests/processors/test_activity.py`, etc.). Keep this for any new module.
- Logging via `logging.getLogger(__name__)`, structured format already set in `main.py::configure_logging`. Don't use `print()` for diagnostics — `st.info`/`st.error` is fine for dashboard user-facing messages.
- Type hints everywhere, `from __future__ import annotations` at top of modules — keep doing this.

## Testing

`pytest`, config in `pytest.ini` (`testpaths = tests`). Domain layer (once introduced) should be the easiest thing in this repo to unit test — pure functions, no mocking of pandas/requests needed. Adapter tests need fixtures/mocks for the boundary (HTTP responses, filesystem). Don't test pandas internals — test that `extract()` produces correct domain values from a given raw JSON fixture.

## Don't

- Don't add a database, message queue, or web framework speculatively. Single user, local CSVs, Streamlit — this is appropriately small. Hexagonal here is about isolating business rules for testability and clarity, not about scaling infrastructure.
- Don't put goal/progress logic inside `src/dashboard/charts.py` — charts render, they don't decide what "on track" means.
- Don't translate Polar's raw field names (camelCase, API-specific keys) past the adapter boundary — domain models use your own naming.
