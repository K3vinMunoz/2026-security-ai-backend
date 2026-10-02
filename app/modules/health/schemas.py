from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response contract for the liveness endpoint."""

    status: str
    service: str
    version: str
