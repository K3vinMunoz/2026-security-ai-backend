from fastapi import FastAPI

from app.core.config import settings
from app.modules.health.router import router as health_router


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )
    application.include_router(health_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
