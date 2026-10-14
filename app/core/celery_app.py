from celery import Celery

from app.core.config import settings

# Single, centralized Celery instance for the whole application. Both the
# FastAPI producer and the standalone worker import this same object, so task
# names and broker configuration can never diverge between processes.
celery_app = Celery(
    "security_ai_backend",
    broker=settings.celery_broker_url,
    include=["app.tasks.smoke"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Redis acts only as a broker in this stage: task results are discarded
    # instead of being stored, and no result backend is configured.
    task_ignore_result=True,
    result_backend=None,
)
