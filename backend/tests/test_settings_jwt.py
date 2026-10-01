import pytest
from pydantic import ValidationError

from backend.config import Settings


def test_settings_fails_without_jwt_secret(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_accepts_jwt_secret_when_present(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 40)

    settings = Settings(_env_file=None)

    assert settings.jwt_secret_key == "x" * 40
