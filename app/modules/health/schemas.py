from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response contract for the liveness endpoint."""

    status: str
    service: str
    version: str


class ReadinessResponse(BaseModel):
    """Response contract for the readiness endpoint."""

    status: str
    database: str