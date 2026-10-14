import logging

from app.core.celery_app import celery_app
from app.tasks.smoke import ping


def test_smoke_task_registered_under_stable_name() -> None:
    assert "app.tasks.smoke.ping" in celery_app.tasks
    assert celery_app.tasks["app.tasks.smoke.ping"].name == "app.tasks.smoke.ping"


def test_smoke_task_executes_eagerly_without_broker(caplog) -> None:
    with caplog.at_level(logging.INFO):
        result = ping.apply()

    assert result.successful()
    assert result.get() is None
    assert "app.tasks.smoke.ping" in caplog.text
