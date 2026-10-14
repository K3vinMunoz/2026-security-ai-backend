from app.core.celery_app import celery_app
from app.core.config import settings


def test_broker_url_derived_from_redis_components() -> None:
    assert settings.celery_broker_url == (
        f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
    )


def test_broker_configured_from_settings() -> None:
    assert celery_app.conf.broker_url == settings.celery_broker_url


def test_serialization_is_json_only() -> None:
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert list(celery_app.conf.accept_content) == ["json"]


def test_timezone_is_utc() -> None:
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.enable_utc is True


def test_results_are_disabled() -> None:
    assert celery_app.conf.task_ignore_result is True
    assert not celery_app.conf.result_backend
