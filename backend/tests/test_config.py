import pytest
from pydantic import ValidationError

from uptime_watch.config import Settings


def test_settings_read_database_url_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/x")

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+psycopg://u:p@localhost/x"


def test_settings_require_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_defaults_for_worker_and_scheduler(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/x")
    for name in ("REDIS_URL", "SCHEDULER_TICK_SECONDS", "CHECK_TIMEOUT_SECONDS"):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.scheduler_tick_seconds == 5
    assert settings.check_timeout_seconds == 10


def test_settings_reject_a_tick_of_zero(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/x")
    monkeypatch.setenv("SCHEDULER_TICK_SECONDS", "0")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
