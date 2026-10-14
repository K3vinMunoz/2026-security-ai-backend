from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings


def _settings_with_special_password() -> Settings:
    return Settings(
        postgres_host="db.internal",
        postgres_port=6543,
        postgres_db="security_ai",
        postgres_user="app@user",
        postgres_password="p@ss:w/rd%25#!",
    )


def test_database_url_preserves_special_characters() -> None:
    url = _settings_with_special_password().sqlalchemy_database_url

    assert isinstance(url, URL)
    assert url.drivername == "postgresql+psycopg"
    assert url.username == "app@user"
    assert url.password == "p@ss:w/rd%25#!"
    assert url.host == "db.internal"
    assert url.port == 6543
    assert url.database == "security_ai"


def test_database_url_escapes_reserved_characters() -> None:
    url = _settings_with_special_password().sqlalchemy_database_url

    rendered = url.render_as_string(hide_password=False)

    assert "%40" in rendered
    assert "%3A" in rendered
    assert "%2F" in rendered
    assert "p@ss:w/rd" not in rendered


def test_database_url_round_trips_through_string() -> None:
    url = _settings_with_special_password().sqlalchemy_database_url

    reparsed = make_url(url.render_as_string(hide_password=False))

    assert reparsed == url
    assert reparsed.password == "p@ss:w/rd%25#!"


def test_engine_accepts_constructed_url() -> None:
    url = _settings_with_special_password().sqlalchemy_database_url

    engine = create_async_engine(url)

    assert engine.url.password == "p@ss:w/rd%25#!"
    assert engine.dialect.driver == "psycopg"


def test_url_repr_masks_password() -> None:
    url = _settings_with_special_password().sqlalchemy_database_url

    assert "p@ss:w/rd%25#!" not in repr(url)
    assert "***" in repr(url)
