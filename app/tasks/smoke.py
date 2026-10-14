import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.smoke.ping", ignore_result=True)
def ping() -> None:
    """Minimal smoke task to validate the async pipeline end to end.

    It only logs a message so execution can be confirmed in the worker logs.
    It deliberately performs no I/O: no database, no OCR, no files, no AI
    models, no outbound network calls. Safe to run repeatedly.
    """
    logger.info("smoke task executed: app.tasks.smoke.ping")
