from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.logging import get_logger

log = get_logger("scheduler")


def build_scheduler() -> AsyncIOScheduler:
    return AsyncIOScheduler(timezone="Asia/Seoul")


def schedule_sync_job(
    scheduler: AsyncIOScheduler, *, interval_minutes: int = 15
) -> None:
    scheduler.add_job(
        _sync_all_users,
        "interval",
        minutes=interval_minutes,
        name="google_calendar_sync",
        id="google_calendar_sync",
        replace_existing=True,
    )


async def _sync_all_users() -> None:
    """For every user with a Google refresh token, sync their calendar."""
    from sqlalchemy import select

    from app.core.config import get_settings
    from app.db.models import User
    from app.db.session import get_session_factory
    from app.services.calendar_sync import sync_user_google_calendar
    from app.services.google_calendar import GoogleCalendarClient, exchange_refresh_token

    s = get_settings()
    factory = get_session_factory()
    async with factory() as session:
        users = (await session.execute(select(User))).scalars().all()
        for user in users:
            tokens = (user.external_tokens or {}).get("google") or {}
            refresh_token = tokens.get("refresh_token")
            if not refresh_token:
                continue
            try:
                access_token = await exchange_refresh_token(
                    refresh_token=refresh_token,
                    client_id=s.google_oauth_client_id,
                    client_secret=s.google_oauth_client_secret,
                )
                client = GoogleCalendarClient(access_token=access_token)
                count = await sync_user_google_calendar(
                    session,
                    user=user,
                    client=client,
                    calendar_id=s.google_calendar_id,
                )
                log.info("google.sync", user_id=str(user.id), count=count)
            except Exception as exc:  # noqa: BLE001
                log.error("google.sync.failed", user_id=str(user.id), error=str(exc))
