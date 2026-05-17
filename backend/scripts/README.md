# backend/scripts

Local development helpers. All scripts refuse to run when
`settings.environment == "production"`.

Run from `backend/` so that `python -m scripts.X` resolves the `app.*` package.

## seed_dev

Idempotent seed: creates a default user, one project, one context, three tasks,
and two local schedule events. Safe to re-run.

```
python -m scripts.seed_dev
```

What it creates:

- User `damien@bctone.kr` (name=`damien`)
- Project `Home Agent`
- Context `@home`
- Tasks `Inbox 정리`, `주간 회고`, `독서 30분`
- Events `오늘 일정 샘플`, `내일 일정 샘플` (source=local, external_id=`seed:dev:N`)

## reset_db

Destructive: runs alembic downgrade to base, upgrade to head, then seed.
Requires explicit `--yes`.

```
python -m scripts.reset_db --yes
```

Uses `alembic.command` programmatically (no subprocess) so it works the same on
Windows PowerShell, WSL, and macOS/Linux shells.

## Notes

- These scripts use the regular `DATABASE_URL` from your `.env`. Make sure your
  local Postgres / docker compose stack is up first.
- `reset_db` calls `seed_dev` after migrations. Run `seed_dev` standalone if you
  only want to top up missing rows without dropping the schema.
