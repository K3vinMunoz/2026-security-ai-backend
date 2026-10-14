import asyncio

import httpx
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import get_db_session
from app.main import create_app


class _SimulatedDatabaseDown(SQLAlchemyError):
    """Controlled error standing in for an unreachable PostgreSQL."""


class _HealthySession:
    async def execute(self, *args, **kwargs):
        return None


class _UnhealthySession:
    async def execute(self, *args, **kwargs):
        raise _SimulatedDatabaseDown()


async def _session_healthy():
    yield _HealthySession()


async def _session_unhealthy():
    yield _UnhealthySession()


def _get_ready(override) -> httpx.Response:
    async def request() -> httpx.Response:
        app = create_app()
        app.dependency_overrides[get_db_session] = override
        transport = ASGITransport(app=app)
        try:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.get(f"{settings.api_v1_prefix}/ready")
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(request())


def test_ready_returns_200_when_database_available() -> None:
    response = _get_ready(_session_healthy)

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_ready_returns_503_when_database_unavailable() -> None:
    response = _get_ready(_session_unhealthy)

    assert response.status_code == 503
    assert response.json() == {"detail": "database unavailable"}