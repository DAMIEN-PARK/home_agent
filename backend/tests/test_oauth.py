import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_oauth_start_redirects_to_google(app_client: AsyncClient, monkeypatch):
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "fake_id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "fake_secret")
    # Rebuild settings cache so the env override takes effect.
    from app.core import config

    config.get_settings.cache_clear()

    resp = await app_client.get("/oauth/google/start", follow_redirects=False)
    assert resp.status_code in (302, 307)
    location = resp.headers["location"]
    assert "accounts.google.com" in location
    assert "fake_id" in location


@pytest.mark.asyncio
async def test_oauth_start_500_when_client_id_missing(
    app_client: AsyncClient, monkeypatch
):
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
    from app.core import config

    config.get_settings.cache_clear()

    resp = await app_client.get("/oauth/google/start", follow_redirects=False)
    assert resp.status_code == 500
