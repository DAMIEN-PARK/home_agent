from uuid import uuid4

import pytest

from app.db.models import Session
from app.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_get_or_create_scoped_session_updates_device_name(
    db_session, test_user
):
    """Existing session with stale device_name gets refreshed on re-fetch.

    Covers the non-trivial branch at chat_service.py
    `get_or_create_scoped_session` where an existing session's device_name
    is replaced with the new value.
    """
    device_id = uuid4()
    sess = Session(
        user_id=test_user.id,
        scope="orchestrator",
        device_id=device_id,
        device_name="old-laptop",
    )
    db_session.add(sess)
    await db_session.commit()

    svc = ChatService(db_session, test_user)
    refreshed = await svc.get_or_create_scoped_session(
        scope="orchestrator",
        device_id=device_id,
        device_name="new-laptop",
    )
    assert refreshed.id == sess.id
    assert refreshed.device_name == "new-laptop"
