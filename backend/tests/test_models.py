from datetime import datetime, timezone

from app.db.models import Event, User


def test_event_required_fields():
    event = Event(
        user_id="00000000-0000-0000-0000-000000000001",
        title="Test",
        start_at=datetime.now(timezone.utc),
    )
    assert event.source == "local"  # default value
    assert event.external_id is None


def test_user_has_external_tokens():
    user = User(name="me", external_tokens={"google": {"refresh_token": "x"}})
    assert user.external_tokens["google"]["refresh_token"] == "x"
