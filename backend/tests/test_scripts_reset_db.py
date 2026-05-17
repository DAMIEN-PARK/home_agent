"""Unit tests for scripts/reset_db.py prod-guard.

These tests must NOT touch the database or alembic. They exercise the guard
only — the actual reset flow is covered manually in dev.
"""

from __future__ import annotations

import pytest

from app.core import config
from scripts import reset_db


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


def test_reset_db_refuses_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")

    with pytest.raises(SystemExit) as exc:
        reset_db._guard_production()
    assert "production" in str(exc.value)


def test_reset_db_allows_non_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "dev")

    reset_db._guard_production()
