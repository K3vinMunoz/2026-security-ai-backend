import asyncio

import httpx
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import create_app


def _get(path: str) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = ASGITransport(app=create_app())
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path)

    return asyncio.run(request())


def test_health_returns_ok() -> None:
    response = _get(f"{settings.api_v1_prefix}/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }
