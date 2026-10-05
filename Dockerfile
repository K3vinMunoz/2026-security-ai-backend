# syntax=docker/dockerfile:1

# Imagen oficial de uv (Astral), fijada a la misma version usada en el proyecto.
# Se versiona de forma explicita para evitar un tag `latest` ambiguo.
FROM ghcr.io/astral-sh/uv:0.12.21 AS uv

# ---------------------------------------------------------------------------
# Stage 1: builder
# Resuelve e instala SOLO las dependencias de runtime desde uv.lock.
# ---------------------------------------------------------------------------
FROM python:3.14-slim-bookworm AS builder

COPY --from=uv /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Se copian primero el manifiesto y el lockfile para que la resolucion de
# dependencias quede cacheada y solo se reevalue si alguno de los dos cambia.
COPY pyproject.toml uv.lock ./

# --locked : falla si uv.lock esta desactualizado; jamas lo reescribe.
# --no-dev : excluye pytest, httpx y ruff de la imagen de runtime.
RUN uv sync --locked --no-dev --no-install-project

# ---------------------------------------------------------------------------
# Stage 2: final (runtime)
# Solo contiene el venv de runtime y el codigo de la aplicacion.
# ---------------------------------------------------------------------------
FROM python:3.14-slim-bookworm AS final

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Usuario de sistema sin privilegios (UID/GID fijos, sin shell interactivo).
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app app ./app

USER app

EXPOSE 8000

# contextlib.suppress evita tracebacks en los logs: si FastAPI deja de
# responder, el script cae en sys.exit(1) -> contenedor "unhealthy".
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
    CMD ["python", "-c", "import contextlib, sys, urllib.request\nurl = 'http://127.0.0.1:8000/api/v1/health'\nwith contextlib.suppress(Exception):\n    sys.exit(0 if urllib.request.urlopen(url, timeout=3).status == 200 else 1)\nsys.exit(1)"]

# Forma exec: uvicorn es PID 1 y recibe SIGTERM directamente.
# Sin --reload: es configuracion de runtime, no de desarrollo.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
