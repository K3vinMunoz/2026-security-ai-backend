# Architecture

This document describes the **actual** architecture of `2026-security-ai-backend` and the
conventions that govern how new code is added. It is deliberately explicit about what is
**implemented today** versus what is **planned**, so the two are never confused.

> Legend: **[implemented]** = code that exists and runs today.
> **[future]** = a convention or plan, with no code yet.

---

## A. Purpose of the backend

`2026-security-ai-backend` is the backend of an **on-premise** AI platform for a private
security company. It is designed to process enterprise PDF documents, extract information
(using OCR when necessary), store structured data in PostgreSQL, and answer queries through
SQL, RAG, or a combination of both.

The platform runs entirely on customer infrastructure. Its normal operation **must not
depend on external AI services**; models (embeddings, LLMs) will run locally in [future]
stages. At this point the project is an incremental skeleton: the plumbing for HTTP,
persistence and asynchronous work exists, but no document-processing feature is implemented.

---

## B. Current architecture **[implemented]**

| Component | Role |
| --------- | ---- |
| **FastAPI** | HTTP API, dependency injection, application lifecycle. |
| **Pydantic v2 / pydantic-settings** | Request/response schemas and centralized configuration. |
| **SQLAlchemy 2 (async)** | ORM and connection pooling for PostgreSQL. |
| **psycopg 3** | Native async PostgreSQL driver (`postgresql+psycopg://`). |
| **PostgreSQL 17 + pgvector** | Structured persistence and vector storage (`vector` extension enabled). |
| **Alembic** | Exclusive owner of the database schema (migrations). |
| **Redis 8** | Message broker for Celery (internal only). |
| **Celery 5.6** | Asynchronous task execution in a standalone worker. |
| **Docker / Docker Compose** | Packaging and orchestration of `backend`, `worker`, `redis`, `postgres`. |

```
                         CLIENT (HTTP)
                              │
                              ▼
                        ┌───────────┐        ┌──────────────┐
                        │  FastAPI  │───────▶│ PostgreSQL   │
                        │ (backend) │        │ + pgvector   │
                        └─────┬─────┘        └──────────────┘
                              │ publishes
                              ▼
                        ┌───────────┐
                        │   Redis   │  (broker, no host port)
                        └─────┬─────┘
                              │ delivers
                              ▼
                        ┌───────────┐
                        │  Celery   │
                        │  worker   │
                        └───────────┘
```

---

## C. Responsibilities of each directory

| Path | Responsibility | Layer kind |
| ---- | -------------- | ---------- |
| `app/main.py` | FastAPI app creation, lifespan, registration of routers. | Composition root |
| `app/core/` | Cross-cutting infrastructure: configuration (`config.py`) and the Celery instance (`celery_app.py`). | Shared infrastructure |
| `app/db/` | Shared SQLAlchemy infrastructure: declarative `Base` (`base.py`) and async engine/session (`session.py`). | Shared infrastructure |
| `app/modules/` | Business domains and features. Each domain is self-contained. | Domain |
| `app/tasks/` | Celery task definitions (async entry points). | Async entry points |
| `alembic/` | Database migrations and migration environment. | Persistence tooling |
| `tests/` | Automated tests, organized mirroring `app/`. | Verification |

Notes:

- `app/core/` holds only things that are genuinely **shared** across domains. It must not
  contain business logic.
- `app/db/` is shared persistence infrastructure. Domain-specific models live with their
  domain, not here.
- Code in `app/main.py` is the only place that wires modules into the application.

---

## D. Module conventions

A business capability lives under `app/modules/<domain>/`. A module owns everything it
needs and is the unit of cohesion.

```
app/modules/
├── health/            # [implemented]
│   ├── __init__.py
│   ├── router.py
│   └── schemas.py
│
├── <domain>/          # [future] one directory per business capability
│   ├── __init__.py
│   ├── router.py      # HTTP interface
│   ├── schemas.py     # request/response contracts (Pydantic)
│   ├── models.py      # SQLAlchemy ORM models (only if it persists data)
│   ├── service.py     # use-case orchestration (only if it has business logic)
│   └── repository.py  # data access (only if it queries the database)
```

Use each file **only when the module needs it**:

| File | Use it when… | Do not use it when… |
| ---- | ------------ | ------------------- |
| `router.py` | The domain exposes HTTP endpoints. | — |
| `schemas.py` | The domain has request/response bodies to validate. | Endpoints return only primitive/simple data. |
| `models.py` | The domain owns persistent tables. | The domain is stateless. |
| `service.py` | There is real use-case logic to coordinate (multiple steps, multiple repositories, transactions, invariants). | The endpoint is a trivial pass-through. |
| `repository.py` | Queries against the database are non-trivial or reused. | There is no persistence. |

Rules:

- **No circular dependencies.** A module may depend on `app/core/` and `app/db/`; a module
  must not import another module's internals. Cross-domain collaboration, when it appears,
  happens through a service exposed by the owning module.
- **Routers stay thin.** A router defines endpoints, validates input via schemas, declares
  FastAPI dependencies, and translates results/errors to HTTP. It must not embed business
  logic or reach into infrastructure *when a service should own that logic*.
- **Do not impose layers on simple modules.** `health/` has no business logic, so it has no
  `service.py` or `repository.py`. Adding them would be speculative.
- Do **not** create placeholder/empty modules for future domains.

### Adding a new module (checklist)

1. Create `app/modules/<domain>/__init__.py` and the files the domain actually needs.
2. Register its router explicitly in `app/main.py` with
   `application.include_router(<domain>_router, prefix=settings.api_v1_prefix)`.
3. If it persists data, define `models.py` and follow the model-registration convention in
   section I.
4. Add tests under `tests/modules/<domain>/` (create that path only when the first test
   exists).

### Service/Repository convention

`app/modules/health/` is intentionally thin: it is infrastructure health, not a business
domain, so it has no service or repository. The convention applies to business modules.

| Layer | Responsible for |
| ----- | --------------- |
| **Router** | Defining endpoints, validating inputs via schemas, declaring FastAPI dependencies, translating results/errors into HTTP responses. |
| **Service** | Coordinating use cases, applying business rules, owning the transaction boundary, calling repositories and ports. |
| **Repository** | Encapsulating SQLAlchemy queries; the only layer that talks to the session for domain data. |

Guidelines:

- Do not add a service/repository for trivial pass-through work; add them when the module has
  real logic.
- No generic base classes for all services/repositories.
- No generic unit-of-work abstraction in this stage.
- The database session is injected with FastAPI's `Depends(get_db_session)`; services and
  repositories receive it, the router never manipulates it directly for domain logic.

---

## E. Ports/Adapters conventions **[future]**

External technologies — OCR engines, embedding models, LLMs, object storage — will not be
called directly from domain logic. They will be reached through **ports** (interfaces owned
by the domain) with **adapters** (concrete implementations) in infrastructure.

```
Domain Service ──uses──▶ Port (Protocol/ABC)
                              ▲
                              │ implements
                        Adapter (e.g. Tesseract, pgvector store, local LLM)
```

- A **port** is a small interface expressed in the language of the domain (e.g.
  `extract_text(pdf_bytes) -> str`).
- An **adapter** implements the port against a concrete technology.
- The domain depends on the port, never on the adapter. Adapters are **wired at a composition
  root**, not necessarily at `app/main.py`.

### Composition roots (HTTP and async are different entry points)

There is **no single composition root**. The backend has more than one way to enter the
application, and each one must be able to build the adapters/services it needs:

- **HTTP entry point** — FastAPI resolves adapters through `Depends(...)`. This is the natural
  composition root for request handling.
- **Async entry point** — the **Celery worker is an independent process** that starts from
  `app/core/celery_app.py`. It does **not** run through FastAPI, so `Depends()` is not
  available there. The worker must build its own adapters/services explicitly (e.g. a small
  factory invoked before a task delegates to a domain service).

Consequences:

- Domain services must be **constructible without FastAPI**: their dependencies are received
  as arguments, not fetched from `Depends()` internally.
- Do **not** tie service/adapter construction to `Depends()` or to `app/main.py` alone.
- Adapters are chosen per entry point; the shared `settings` object is what keeps their
  configuration consistent across HTTP and worker.

Do **not** define ports/adapters in advance. Introduce a port only when a real use case needs
it. Today **no** port or adapter exists; OCR, embeddings, RAG and LLM are **[future]**.

---

## F. HTTP flow

The canonical flow, when a use case needs the full stack:

```
HTTP Request
     │
     ▼
FastAPI Router        (validate input, declare dependencies)
     │
     ▼
Service               (use-case logic, transaction boundary)   ← optional
     │
     ▼
Repository            (SQLAlchemy queries)                     ← optional
     │
     ▼
PostgreSQL
```

**Service and Repository are introduced only when the use case requires them.** A simple
read-only endpoint may legitimately go from router straight to the database session, as the
`/ready` probe does today with a single `SELECT 1`.

### HTTP error convention

Three clearly separated categories:

| Category | Origin | Handling |
| -------- | ------ | -------- |
| Validation errors | Pydantic/FastAPI | `422`, handled by FastAPI automatically. |
| Business errors | Domain/service logic | Raised by the service, mapped to an `HTTPException` with the appropriate status. |
| Infrastructure errors | PostgreSQL/Redis/Celery | Caught at the boundary, logged with technical detail **server-side only**, returned to the client as a generic `5xx`/`503` message. |

Rules:

- Do not expose PostgreSQL, Redis or Celery internals (DSNs, credentials, stack traces) in
  HTTP responses. Today `/ready` catches `SQLAlchemyError` and returns a controlled
  `{"detail": "database unavailable"}` with `503`.
- Do **not** build an extensive exception hierarchy before real use cases exist.

---

## G. Asynchronous flow

```
Producer (FastAPI endpoint or Python process)
     │  task.delay(...)
     ▼
Redis (broker)
     │
     ▼
Celery Worker
     │
     ▼
Task (thin async entry point)
     │
     ▼
Future Domain Service   ← [future]
```

Conventions:

- There is a **single** Celery instance in `app/core/celery_app.py` **[implemented]**; both the
  FastAPI producer and the worker import it, so broker config and task names cannot diverge.
- Tasks are registered with **explicit, stable names** (e.g. `app.tasks.smoke.ping`) and the
  module is listed in the `include` list of the Celery app.
- A **task is a thin entry point**: it validates its arguments (JSON-serializable only) and
  delegates to a domain service. Business logic does not live inside the task body.
- Serialization is **JSON only**; results are ignored in this stage (`task_ignore_result`,
  no result backend). Redis is used only as a broker.
- No Celery Beat, Flower, extra queues or routing until a real use case requires them.

### Database access from the worker **[future]**

This subsection is a **convention / plan**; no worker task queries the database yet. It exists
to state, before any such code is written, how the worker is *not* like a request.

- **`Depends(get_db_session)` does not exist in the worker.** That dependency is a FastAPI
  mechanism scoped to the HTTP request lifecycle. A Celery task is an independent process/thread
  with no request scope; the worker must obtain and manage its own session explicitly.
- **A session must not be shared across tasks or reused as a module-level global.** Each task
  that touches the database opens its own session and closes it deterministically (e.g. an
  `async with` block around the unit of work), independently of any HTTP request.
- **The async engine and event loop need an explicit lifecycle.** The worker is a separate
  process from the API, so:
  - SQLAlchemy's async engine cannot assume FastAPI's running loop; engines/pools tied to a
    loop are not safe to move across loops.
  - With prefork workers (`--concurrency > 1`), code that runs at import time in a parent may
    be forked, and an engine created there must **not** be reused by children. Engines should
    be created/owned where they are used.
  - The worker must define how tasks run under asyncio: either an async task model that shares
    one loop per worker process, or a per-task `asyncio.run`, in which case the engine must be
    created **inside** that loop (e.g. `NullPool`, a fresh engine per run) and disposed at the
    end. This choice is to be made when the first DB-backed task is introduced.

Consequences to keep in mind when that code is written:

- The DSN still comes from the shared `settings`; only the *session/engine lifecycle* differs
  from HTTP.
- No new global engine is added to `app/db/session.py` for the worker before this is needed.

Do **not** implement worker database access in this stage.

---

## H. Dependency management (uv)

- **uv** is the single tool for dependencies; `requirements.txt` is not used.
- `pyproject.toml` declares direct dependencies; `uv.lock` is committed and is the source of
  truth for reproducible installs.
- Runtime dependencies go in `[project].dependencies`; developer-only tools (`pytest`,
  `httpx`, `ruff`) go in `[dependency-groups].dev`.
- The Docker image installs with `uv sync --locked --no-dev`, so the image never contains dev
  tooling and never rewrites the lockfile at build time.
- Add a dependency only when a real need exists, and verify compatibility with **Python 3.14**
  before pinning.

---

## I. Migrations (SQLAlchemy + Alembic)

- The schema is owned **exclusively** by Alembic. There is no `create_all` anywhere.
- `app/db/base.py` defines the single declarative `Base`.
- `alembic/env.py` reads the database URL from `app.core.config.settings` (a
  `sqlalchemy.engine.URL`, so special characters and credentials are handled safely) and sets
  `target_metadata = Base.metadata`.
- Migrations run explicitly (`alembic upgrade head`); they are **never** applied automatically
  on application startup.
- The current migration `bc58338bbcfc` enables the `vector` extension **[implemented]**.

### Convention for registering future models

Alembic autogenerate only sees tables that have been imported (and therefore registered on
`Base.metadata`) before migrations run.

1. A domain that persists data defines `app/modules/<domain>/models.py`, importing `Base`
   from `app.db.base` and subclassing it.
- When the **first** model is added, make it visible to Alembic by importing it before
  `Base.metadata` is used. The agreed approach is a single explicit import point — either
  directly in `alembic/env.py`, or through a small aggregator module that `alembic/env.py`
  imports — **not** automatic reflection or dynamic magic.

Do **not** create placeholder `models.py` files or empty modules in advance.

### Creating and applying a migration (workflow)

A migration is created against a **running, up-to-date** database: Alembic autogenerate
compares `Base.metadata` with the schema currently in PostgreSQL, so the database must be
reachable and already migrated to the latest revision. If it is not, autogenerate inspects the
wrong state and produces a diff with spurious or missing operations.

1. **Start the stack** (PostgreSQL must be healthy before Alembic runs):
   `docker compose up -d postgres`.
2. **Confirm the database is at the current head** — this is a prerequisite for a correct
   autogenerate diff:
   `docker compose run --rm backend alembic current`
   and, if needed, `docker compose run --rm backend alembic upgrade head`.
3. **Create the migration** (only after `models.py` exists and is imported so it is registered
   on `Base.metadata` — see the convention above):
   `docker compose run --rm backend alembic revision --autogenerate -m "short description"`.
4. **Review the generated file** in `alembic/versions/` before applying it: autogenerate is a
   draft, not a source of truth. Check that the operations match the intended model change and
   edit/correct the revision when necessary (types, nullability, indexes, server defaults,
   data migrations).
5. **Apply it:** `docker compose run --rm backend alembic upgrade head`.
6. **Verify:** `docker compose run --rm backend alembic current` shows the new revision as head.

Never apply migrations automatically on application startup, and never edit a migration that has
already been applied to a shared database — create a new revision instead.

---

## J. Design principles

- **Separation of responsibilities** — each component has one clear job (see section C).
- **Low coupling** — modules depend on `core`/`db`, never on each other's internals.
- **High cohesion** — a module owns everything that belongs to its capability.
- **Centralized configuration** — all environment access goes through `app/core/config.py`
  and the single `settings` object; no scattered `os.getenv`.
- **Testable code** — unit tests run without PostgreSQL or Redis.
- **Avoid premature abstractions** — services, repositories, ports and adapters are added only
  when a real use case needs them.
- **Python 3.14 compatibility** — the project targets `>=3.14,<3.15`.
- **No external services for normal operation** — the platform runs fully on-premise.

---

## Implemented vs. future (summary)

| Concern | Status |
| ------- | ------ |
| FastAPI app, lifespan, `/health`, `/ready` | **[implemented]** |
| PostgreSQL + pgvector + Alembic | **[implemented]** |
| SQLAlchemy async engine/session | **[implemented]** |
| Redis broker + Celery worker + smoke task | **[implemented]** |
| Docker Compose (backend, worker, redis, postgres) | **[implemented]** |
| Service/Repository convention | **[implemented as convention]** (no business module needs it yet) |
| Ports/Adapters, OCR, document ingestion, embeddings, RAG, LLM | **[future]** |
| Auth, users, roles | **[future]** |
| Celery Beat, Flower, extra queues | **[future]** |
