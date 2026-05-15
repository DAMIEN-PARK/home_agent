from app.scheduler import build_scheduler, schedule_sync_job


def test_scheduler_registers_sync_job():
    scheduler = build_scheduler()
    schedule_sync_job(scheduler, interval_minutes=15)
    jobs = scheduler.get_jobs()
    assert any(j.name == "google_calendar_sync" for j in jobs)


def test_scheduler_replace_existing_is_idempotent():
    scheduler = build_scheduler()
    schedule_sync_job(scheduler, interval_minutes=15)
    schedule_sync_job(scheduler, interval_minutes=20)
    jobs = [j for j in scheduler.get_jobs() if j.name == "google_calendar_sync"]
    assert len(jobs) == 1
