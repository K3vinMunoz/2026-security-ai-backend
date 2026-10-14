import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db_session
from app.modules.health.schemas import HealthResponse, ReadinessResponse

logger = logging.getLogger(__name__)

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


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
async def readiness(db: AsyncSession = Depends(get_db_session)) -> ReadinessResponse:
    """Readiness probe.

    Verifies PostgreSQL connectivity with a lightweight ``SELECT 1``. Does not
    touch business tables and never exposes credentials or connection details.
    """
    try:
        await db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.error("readiness: database check failed (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from exc
    return ReadinessResponse(status="ready", database="ok")