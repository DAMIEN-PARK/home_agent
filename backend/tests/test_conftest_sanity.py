import pytest


@pytest.mark.asyncio
async def test_db_session_works(db_session):
    from sqlalchemy import text
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_user_fixture(test_user):
    assert test_user.name == "test_user"
