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
