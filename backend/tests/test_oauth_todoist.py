import pytest
from httpx import AsyncClient
from pytest_httpx import HTTPXMock

from app.services.oauth_todoist import TodoistOAuthService


@pytest.mark.asyncio
async def test_callback_persists_three_key_dict(
    db_session, test_user, httpx_mock: HTTPXMock
):
    """MA-1 contract: existing['todoist'] = {access_token, refresh_token: None, scope}."""
    httpx_mock.add_response(
        url="https://todoist.com/oauth/access_token",
        json={
            "access_token": "fake_todoist_token",
            "token_type": "Bearer",
            "scope": "data:read_write",
        },
    )

    svc = TodoistOAuthService()
    result = await svc.handle_callback(
        db_session, code="fake_code", state=str(test_user.id)
    )

    assert result.ok
    await db_session.refresh(test_user)
    todoist = (test_user.external_tokens or {}).get("todoist")
    assert todoist is not None
    assert set(todoist.keys()) == {"access_token", "refresh_token", "scope"}
    assert todoist["access_token"] == "fake_todoist_token"
    assert todoist["refresh_token"] is None
    assert todoist["scope"] == "data:read_write"


@pytest.mark.asyncio
async def test_sync_endpoint_returns_422_without_token(
    app_client: AsyncClient, test_user
):
    """POST /todoist/sync without external_tokens['todoist'] -> 422."""
    resp = await app_client.post(f"/todoist/sync?user_id={test_user.id}")
    assert resp.status_code == 422
    assert "Todoist token not configured" in resp.json().get("detail", "")
