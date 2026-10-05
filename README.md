# 2026-security-ai-backend

On-premise AI backend for processing and querying enterprise documentation.

This project is an **incremental** build. Only the features documented here currently exist.
Everything described under [Roadmap](#roadmap) is planned, not implemented.

---

## Architecture

**Modular Monolith** organized by domain, applying **Service/Repository** where a feature
needs business logic and persistence, and **Ports/Adapters** for external integrations.

- Each business capability lives in its own module under `app/modules/<domain>/`.
- Modules own their routers, schemas and (when needed) services and repositories.
- Cross-cutting concerns that are genuinely shared — currently only configuration — live in
  `app/core/`.
- External technologies (LLM, OCR, embeddings, storage) will be reached through ports so the
  domain logic never depends on a concrete implementation.

No microservices. Ports, adapters and abstractions are introduced **only** when a feature
actually requires them, to avoid speculative architecture.

---

## Current Stack

| Component        | Version                    |
| ---------------- | -------------------------- |
| Python           | `>=3.14,<3.15`             |
| FastAPI          | `0.142.2`                  |
| Uvicorn          | `0.54.0`                   |
| Pydantic         | `2.13.5`                   |
| pydantic-settings| `2.15.0`                   |
| pytest           | `9.1.1` (dev)              |
| httpx            | `0.28.1` (dev)             |
| Ruff             | `0.16.9` (dev)             |

Dependency management is handled entirely by **uv**; `uv.lock` is committed to guarantee
reproducible installs.

---

## Requirements

### Local development

- **Python 3.14** (`>=3.14,<3.15`)
- **uv** — <https://docs.astral.sh/uv/>

### Containers

- **Docker** with the **Compose** plugin (`docker compose`)

---

## Installation

```bash
uv sync
```

This creates the virtual environment and installs runtime plus development dependencies.

---

## Running the server

### Locally

```bash
uv run uvicorn app.main:app --reload
```

The API is then available at <http://127.0.0.1:8000>, with interactive docs at
<http://127.0.0.1:8000/docs>.

### With Docker

```bash
docker compose up --build
```

Then verify the service:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

```json
{
  "status": "ok",
  "service": "security-ai-backend",
  "version": "0.1.0"
}
```

To run it in the background, add `-d`. To stop and remove the stack:

```bash
docker compose down
```

Notes:

- The image is built from `Dockerfile` on `python:3.14-slim-bookworm` and installs only
  runtime dependencies with `uv sync --locked --no-dev`, so `uv.lock` is never modified
  during the build and `pytest` / `ruff` are not present in the image.
- The container listens on `0.0.0.0:8000` and is published on `127.0.0.1:8000` only.
- It runs as the unprivileged user `app` (UID 10001), never as `root`.
- `HEALTHCHECK` reuses the existing `/api/v1/health` endpoint via the Python standard
  library; no extra endpoint or tool (`curl`, `wget`) is added to the image.
- `.env` is **not** copied into the image. If a `.env` file exists locally it is loaded at
  runtime by Compose; otherwise the defaults in `app/core/config.py` apply.

---

## Running the tests

```bash
uv run pytest
```

---

## Running Ruff

```bash
uv run ruff check .
```

---

## Endpoints

### `GET /api/v1/health`

Liveness probe. It returns success when the process is up and serving requests, and performs
**no** I/O against a database, cache, filesystem, LLM or network.

```json
{
  "status": "ok",
  "service": "security-ai-backend",
  "version": "0.1.0"
}
```

Intended for Docker healthchecks and monitoring.

---

## Configuration

Configuration is centralized in `app/core/config.py` via `pydantic-settings` and consumed
through the single `settings` object. No scattered `os.getenv(...)` calls.

| Variable         | Default              | Description                    |
| ---------------- | -------------------- | ------------------------------ |
| `APP_NAME`       | `security-ai-backend`| Service name reported by health |
| `APP_VERSION`    | `0.1.0`              | Service version                 |
| `APP_ENV`        | `development`        | Deployment environment name     |
| `DEBUG`          | `true`               | FastAPI debug mode              |
| `API_V1_PREFIX`  | `/api/v1`            | Prefix for versioned routes     |

Copy `.env.example` to `.env` for local overrides. `.env` is git-ignored and must never be
committed.

---

## Security Notice

This repository is intended to be public. It must never contain real or confidential data.
Specifically, the following are excluded by design and must never be committed:

- Real corporate documents or employee PDFs
- Real OCR output or extracted personal data
- Database exports, backups or dumps
- Secrets, tokens or credentials

Any dataset added later must be entirely fictional or anonymized.

---

## Roadmap

Not implemented yet. Listed only to show intended direction:

- Document ingestion and OCR
- Information extraction and normalization
- PostgreSQL structured storage
- Embeddings with pgvector
- RAG querying
- Controlled structured SQL querying
- Local LLM execution (e.g. Ollama, vLLM)
- Asynchronous processing with Celery and Redis
