from fastapi import APIRouter

from app.core.config import settings
from app.modules.health.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness probe.

    Reports that the process is up and serving requests. It deliberately
    performs no I/O against the database, cache, filesystem, LLM or network.
    """
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
    )
