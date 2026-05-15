from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.services.schedule_service import create_local_event


@pytest.mark.asyncio
async def test_get_events_returns_in_range(
    app_client: AsyncClient, db_session, test_user
):
    now = datetime.now(timezone.utc)
    await create_local_event(db_session, user_id=test_user.id, title="A", start_at=now)
    await create_local_event(
        db_session,
        user_id=test_user.id,
        title="B",
        start_at=now + timedelta(days=60),
    )

    resp = await app_client.get(
        "/events",
        params={
            "user_id": str(test_user.id),
            "from": (now - timedelta(hours=1)).isoformat(),
            "to": (now + timedelta(days=1)).isoformat(),
        },
    )
    assert resp.status_code == 200
    titles = [e["title"] for e in resp.json()["events"]]
    assert "A" in titles
    assert "B" not in titles
